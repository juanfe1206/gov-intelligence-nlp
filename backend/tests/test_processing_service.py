"""Tests for NLP processing service."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import numpy as np
from sqlalchemy import select

from app.models.processed_post import ProcessedPost
from app.models.raw_post import RawPost
from app.processing.schemas import ClassificationResult, ProcessingSummary
from app.processing.embeddings import normalize_vector, generate_embeddings, generate_single_embedding
from app.processing.classifier import build_classification_prompt, classify_post, classify_batch
from app.processing.service import (
    get_unprocessed_posts,
    process_posts,
    _insert_processed_post,
    _insert_failed_post,
)


class TestVectorNormalization:
    """Tests for vector normalization utility."""

    def test_normalize_unit_vector(self):
        """Test that normalization produces unit length vectors."""
        vector = [3.0, 4.0, 0.0]  # Known length of 5
        normalized = normalize_vector(vector)

        # Check unit length
        length = np.linalg.norm(normalized)
        assert abs(length - 1.0) < 1e-6

        # Check direction preserved
        assert normalized[0] > 0  # Same direction as original
        assert normalized[1] > 0

    def test_normalize_zero_vector(self):
        """Test that zero vector is handled gracefully."""
        vector = [0.0, 0.0, 0.0]
        normalized = normalize_vector(vector)
        assert normalized == vector  # Returns original

    def test_normalize_already_unit(self):
        """Test that already unit vectors stay unit."""
        vector = [1.0, 0.0, 0.0]
        normalized = normalize_vector(vector)
        assert normalized == vector


class TestClassificationPromptBuilding:
    """Tests for classification prompt construction."""

    def test_prompt_includes_text(self):
        """Test that prompt includes the post text."""
        text = "Test post about politics"
        taxonomy = {"topics": ["economy"], "subtopics": ["inflation"], "targets": ["president"]}

        prompt = build_classification_prompt(text, taxonomy)

        assert text in prompt
        assert "economy" in prompt
        assert "inflation" in prompt
        assert "president" in prompt

    def test_prompt_without_taxonomy(self):
        """Test prompt generation with empty taxonomy."""
        text = "Test post"
        taxonomy = {}

        prompt = build_classification_prompt(text, taxonomy)

        assert text in prompt
        assert "json" in prompt.lower()


class TestClassificationResultValidation:
    """Tests for classification result validation."""

    def test_valid_sentiment_values(self):
        """Test that valid sentiment values pass."""
        result = ClassificationResult(
            topic="economy",
            sentiment="positive",
            intensity=7,
        )
        assert result.sentiment == "positive"

        result = ClassificationResult(
            topic="economy",
            sentiment="NEGATIVE",  # Should be normalized to lowercase
            intensity=5,
        )
        assert result.sentiment == "negative"

    def test_invalid_sentiment_raises_error(self):
        """Test that invalid sentiment values fail."""
        with pytest.raises(ValueError, match="sentiment must be one of"):
            ClassificationResult(
                topic="economy",
                sentiment="happy",  # Invalid
                intensity=5,
            )

    def test_intensity_range(self):
        """Test that intensity must be 1-10."""
        # Valid values
        ClassificationResult(topic="t", sentiment="positive", intensity=1)
        ClassificationResult(topic="t", sentiment="positive", intensity=10)
        ClassificationResult(topic="t", sentiment="positive", intensity=5.5)

        # Invalid values
        with pytest.raises(ValueError):
            ClassificationResult(topic="t", sentiment="positive", intensity=0)
        with pytest.raises(ValueError):
            ClassificationResult(topic="t", sentiment="positive", intensity=11)
        with pytest.raises(ValueError):
            ClassificationResult(topic="t", sentiment="positive", intensity=-1)


class TestProcessingSummary:
    """Tests for processing summary."""

    def test_duration_calculation(self):
        """Test that duration is calculated correctly."""
        now = datetime.now(timezone.utc)
        later = datetime.now(timezone.utc)

        summary = ProcessingSummary(
            status="completed",
            started_at=now,
            finished_at=later,
        )

        assert summary.duration_seconds >= 0

    def test_duration_none_when_not_finished(self):
        """Test that duration is None when not finished."""
        summary = ProcessingSummary(
            status="in_progress",
            started_at=datetime.now(timezone.utc),
            finished_at=None,
        )

        assert summary.duration_seconds is None


class TestGetUnprocessedPosts:
    """Tests for querying unprocessed posts."""

    @pytest.mark.asyncio
    async def test_returns_only_unprocessed(self, async_db_session):
        """Test that only unprocessed posts are returned."""
        # Create a raw post
        raw_post = RawPost(
            source="test",
            platform="twitter",
            original_text="Test content",
            content_hash="abc123",
        )
        async_db_session.add(raw_post)
        await async_db_session.commit()

        # Query unprocessed posts
        posts = await get_unprocessed_posts(async_db_session)

        assert len(posts) == 1
        assert posts[0].original_text == "Test content"

    @pytest.mark.asyncio
    async def test_excludes_already_processed(self, async_db_session):
        """Test that already processed posts are excluded."""
        # Create a raw post
        raw_post = RawPost(
            source="test",
            platform="twitter",
            original_text="Already processed",
            content_hash="def456",
        )
        async_db_session.add(raw_post)
        await async_db_session.flush()

        # Mark as processed
        processed = ProcessedPost(
            raw_post_id=raw_post.id,
            topic="economy",
            sentiment="positive",
        )
        async_db_session.add(processed)
        await async_db_session.commit()

        # Query unprocessed posts
        posts = await get_unprocessed_posts(async_db_session)

        assert len(posts) == 0

    @pytest.mark.asyncio
    async def test_respects_limit(self, async_db_session):
        """Test that limit parameter is respected."""
        # Create multiple posts
        for i in range(5):
            raw_post = RawPost(
                source="test",
                platform="twitter",
                original_text=f"Post {i}",
                content_hash=f"hash{i}",
            )
            async_db_session.add(raw_post)
        await async_db_session.commit()

        # Query with limit
        posts = await get_unprocessed_posts(async_db_session, limit=2)

        assert len(posts) == 2


@pytest.mark.asyncio
class TestProcessPosts:
    """Integration tests for processing service."""

    async def test_process_empty_batch(self, async_db_session):
        """Test processing when no unprocessed posts exist."""
        taxonomy = {"topics": ["economy"], "subtopics": ["inflation"], "targets": ["president"]}

        summary = await process_posts(async_db_session, taxonomy)

        assert summary.status == "completed"
        assert summary.processed == 0
        assert summary.succeeded == 0
        assert summary.failed == 0

    @patch("app.processing.service.classify_batch")
    @patch("app.processing.service.generate_embeddings")
    async def test_process_single_post_success(
        self, mock_embeddings, mock_classify, async_db_session
    ):
        """Test successful processing of a single post."""
        # Create a raw post
        raw_post = RawPost(
            source="test",
            platform="twitter",
            original_text="Test content for classification",
            content_hash="hash123",
        )
        async_db_session.add(raw_post)
        await async_db_session.commit()

        # Mock classification
        mock_classify.return_value = [
            ClassificationResult(
                topic="economy",
                subtopic="inflation",
                sentiment="negative",
                target="president",
                intensity=7,
            )
        ]

        # Mock embeddings
        mock_embeddings.return_value = [[0.1] * 1536]

        taxonomy = {"topics": ["economy"], "subtopics": ["inflation"], "targets": ["president"]}
        summary = await process_posts(async_db_session, taxonomy)

        assert summary.status == "completed"
        assert summary.processed == 1
        assert summary.succeeded == 1
        assert summary.failed == 0

        # Verify database state
        result = await async_db_session.execute(select(ProcessedPost))
        processed = result.scalars().all()
        assert len(processed) == 1
        assert processed[0].topic == "economy"
        assert processed[0].sentiment == "negative"

    @patch("app.processing.service.classify_batch")
    @patch("app.processing.service.generate_embeddings")
    async def test_process_with_classification_failure(
        self, mock_embeddings, mock_classify, async_db_session
    ):
        """Test handling of classification failure."""
        # Create a raw post
        raw_post = RawPost(
            source="test",
            platform="twitter",
            original_text="Test content",
            content_hash="hash456",
        )
        async_db_session.add(raw_post)
        await async_db_session.commit()

        # Mock classification failure
        mock_classify.return_value = [None]
        mock_embeddings.return_value = [[0.1] * 1536]

        taxonomy = {"topics": ["economy"]}
        summary = await process_posts(async_db_session, taxonomy)

        assert summary.failed == 1
        assert summary.succeeded == 0

        # Verify error was recorded
        result = await async_db_session.execute(select(ProcessedPost))
        processed = result.scalars().all()
        assert len(processed) == 1
        assert processed[0].error_status is True
        assert processed[0].error_message is not None

    @patch("app.processing.service.classify_batch")
    @patch("app.processing.service.generate_embeddings")
    async def test_process_with_embedding_failure(
        self, mock_embeddings, mock_classify, async_db_session
    ):
        """Test handling of embedding generation failure."""
        # Create a raw post
        raw_post = RawPost(
            source="test",
            platform="twitter",
            original_text="Test content",
            content_hash="hash789",
        )
        async_db_session.add(raw_post)
        await async_db_session.commit()

        # Mock success classification but embedding failure
        mock_classify.return_value = [
            ClassificationResult(topic="economy", sentiment="positive")
        ]
        mock_embeddings.return_value = [None]

        taxonomy = {"topics": ["economy"]}
        summary = await process_posts(async_db_session, taxonomy)

        assert summary.failed == 1
        assert summary.succeeded == 0

    @patch("app.processing.service.classify_batch")
    @patch("app.processing.service.generate_embeddings")
    async def test_process_respects_batch_size(
        self, mock_embeddings, mock_classify, async_db_session
    ):
        """Test that batch_size controls chunk size but processes all available posts."""
        # Create multiple posts
        for i in range(5):
            raw_post = RawPost(
                source="test",
                platform="twitter",
                original_text=f"Post {i}",
                content_hash=f"batch{i}",
            )
            async_db_session.add(raw_post)
        await async_db_session.commit()

        # Mock successful processing
        mock_classify.side_effect = [
            [ClassificationResult(topic="economy", sentiment="positive")] * 2,
            [ClassificationResult(topic="economy", sentiment="positive")] * 2,
            [ClassificationResult(topic="economy", sentiment="positive")] * 1,
        ]
        mock_embeddings.side_effect = [
            [[0.1] * 1536] * 2,
            [[0.1] * 1536] * 2,
            [[0.1] * 1536] * 1,
        ]

        taxonomy = {"topics": ["economy"]}
        summary = await process_posts(async_db_session, taxonomy, batch_size=2)

        assert summary.processed == 5
        assert mock_classify.call_count == 3


class TestEmbeddingsMock:
    """Tests for embedding generation with mocking."""

    @pytest.mark.asyncio
    @patch("app.processing.embeddings.get_openai_client")
    async def test_generate_embeddings_success(self, mock_get_client):
        """Test successful embedding generation."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[1.0, 2.0, 3.0]),
            MagicMock(embedding=[4.0, 5.0, 6.0]),
        ]

        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        texts = ["text1", "text2"]
        embeddings = await generate_embeddings(texts)

        assert len(embeddings) == 2
        # Verify they are normalized
        for emb in embeddings:
            length = np.linalg.norm(emb)
            assert abs(length - 1.0) < 1e-6

    @pytest.mark.asyncio
    @patch("app.processing.embeddings.get_openai_client")
    async def test_generate_embeddings_api_error(self, mock_get_client):
        """Test handling of API error."""
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(side_effect=Exception("API Error"))
        mock_get_client.return_value = mock_client

        texts = ["text1"]
        embeddings = await generate_embeddings(texts)

        # Should return None for all texts on failure
        assert embeddings == [None]


class TestClassifierMock:
    """Tests for classifier with mocking."""

    @pytest.mark.asyncio
    @patch("app.processing.classifier.get_openai_client")
    async def test_classify_post_success(self, mock_get_client):
        """Test successful classification."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"topic": "economy", "subtopic": "inflation", "sentiment": "negative", "target": "president", "intensity": 7}'
                )
            )
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        taxonomy = {"topics": ["economy"], "subtopics": ["inflation"], "targets": ["president"]}
        result = await classify_post("Test text about inflation", taxonomy)

        assert result is not None
        assert result.topic == "economy"
        assert result.sentiment == "negative"
        assert result.intensity == 7

    @pytest.mark.asyncio
    @patch("app.processing.classifier.get_openai_client")
    async def test_classify_post_empty_response(self, mock_get_client):
        """Test handling of empty response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=""))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        taxonomy = {"topics": ["economy"]}
        result = await classify_post("Test text", taxonomy)

        assert result is None

    @pytest.mark.asyncio
    @patch("app.processing.classifier.get_openai_client")
    async def test_classify_post_api_error(self, mock_get_client):
        """Test handling of API error."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        mock_get_client.return_value = mock_client

        taxonomy = {"topics": ["economy"]}
        result = await classify_post("Test text", taxonomy)

        assert result is None
