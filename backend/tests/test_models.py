"""Tests for database models."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.db.session import async_session_maker
from app.models.raw_post import RawPost
from app.models.processed_post import ProcessedPost


@pytest.mark.asyncio
async def test_create_raw_post():
    """Test creating a raw post."""
    async with async_session_maker() as session:
        raw_post = RawPost(
            source="test_csv",
            platform="twitter",
            original_text="Test post content",
            author="test_user",
        )
        session.add(raw_post)
        await session.commit()
        await session.refresh(raw_post)

        assert raw_post.id is not None
        assert raw_post.platform == "twitter"
        assert raw_post.source == "test_csv"


@pytest.mark.asyncio
async def test_create_processed_post():
    """Test creating a processed post with embedding."""
    async with async_session_maker() as session:
        # First create a raw post
        raw_post = RawPost(
            source="test",
            platform="twitter",
            original_text="Test content",
        )
        session.add(raw_post)
        await session.commit()
        await session.refresh(raw_post)

        # Create processed post
        embedding = [0.1] * 1536  # Test embedding

        processed = ProcessedPost(
            raw_post_id=raw_post.id,
            topic="politics",
            subtopic="housing",
            sentiment="neutral",
            embedding=embedding,
        )
        session.add(processed)
        await session.commit()
        await session.refresh(processed)

        assert processed.id is not None
        assert processed.raw_post_id == raw_post.id
        assert processed.topic == "politics"


@pytest.mark.asyncio
async def test_foreign_key_constraint():
    """Test that foreign key constraint is enforced."""
    async with async_session_maker() as session:
        # Try to create processed post with non-existent raw_post_id
        processed = ProcessedPost(
            raw_post_id=uuid.uuid4(),  # Non-existent UUID
            topic="politics",
            sentiment="positive",
        )
        session.add(processed)

        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_raw_post_relationship():
    """Test relationship between RawPost and ProcessedPost."""
    async with async_session_maker() as session:
        # Create a raw post
        raw_post = RawPost(
            source="test",
            platform="reddit",
            original_text="Test post",
        )
        session.add(raw_post)
        await session.commit()
        await session.refresh(raw_post)

        # Create processed post for the raw post
        processed = ProcessedPost(
            raw_post_id=raw_post.id,
            topic="topic_0",
            sentiment="positive",
        )
        session.add(processed)
        await session.commit()

        # Query with eager loading to avoid implicit async lazy-load IO.
        result = await session.execute(
            select(RawPost)
            .options(selectinload(RawPost.processed_posts))
            .where(RawPost.id == raw_post.id)
        )
        loaded_raw_post = result.scalar_one()
        assert len(loaded_raw_post.processed_posts) == 1
