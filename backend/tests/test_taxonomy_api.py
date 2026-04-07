"""Tests for taxonomy API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.taxonomy.schemas import (
    TaxonomyConfig,
    TaxonomyTopic,
    TaxonomySubtopic,
    TaxonomyTarget,
    TaxonomyTargets,
)


class TestGetTaxonomy:
    """Tests for GET /taxonomy endpoint."""

    def test_get_taxonomy_returns_200_with_correct_structure(self, client: TestClient):
        """Test that GET /taxonomy returns 200 with proper taxonomy structure."""
        response = client.get("/taxonomy")

        assert response.status_code == 200

        data = response.json()

        # Verify top-level structure
        assert "topics" in data
        assert "targets" in data
        assert isinstance(data["topics"], list)
        assert isinstance(data["targets"], dict)

        # Verify topics structure
        for topic in data["topics"]:
            assert "name" in topic
            assert "label" in topic
            assert "subtopics" in topic
            assert isinstance(topic["subtopics"], list)

            for subtopic in topic["subtopics"]:
                assert "name" in subtopic
                assert "label" in subtopic

        # Verify targets structure
        assert "parties" in data["targets"]
        assert "leaders" in data["targets"]
        assert isinstance(data["targets"]["parties"], list)
        assert isinstance(data["targets"]["leaders"], list)

        for party in data["targets"]["parties"]:
            assert "name" in party
            assert "label" in party

        for leader in data["targets"]["leaders"]:
            assert "name" in leader
            assert "label" in leader

    def test_get_taxonomy_returns_expected_topics(self, client: TestClient):
        """Test that GET /taxonomy returns the expected topics from config."""
        response = client.get("/taxonomy")
        assert response.status_code == 200

        data = response.json()
        topic_names = [t["name"] for t in data["topics"]]

        # Verify at least 3 topics exist (per story requirements)
        assert len(topic_names) >= 3

        # Check for expected topics (from config/taxonomy.yaml)
        expected_topics = ["vivienda", "sanidad", "economia", "educacion"]
        for topic in expected_topics:
            assert topic in topic_names, f"Expected topic '{topic}' not found"

    def test_get_taxonomy_returns_expected_targets(self, client: TestClient):
        """Test that GET /taxonomy returns expected parties and leaders."""
        response = client.get("/taxonomy")
        assert response.status_code == 200

        data = response.json()
        party_names = [p["name"] for p in data["targets"]["parties"]]
        leader_names = [l["name"] for l in data["targets"]["leaders"]]

        # Verify at least 3 parties and 3 leaders (per story requirements)
        assert len(party_names) >= 3, f"Expected at least 3 parties, got {len(party_names)}"
        assert len(leader_names) >= 3, f"Expected at least 3 leaders, got {len(leader_names)}"

        # Check for expected parties
        expected_parties = ["pp", "psoe", "vox"]
        for party in expected_parties:
            assert party in party_names, f"Expected party '{party}' not found"

        # Check for expected leaders
        expected_leaders = ["sanchez", "feijoo", "abascal"]
        for leader in expected_leaders:
            assert leader in leader_names, f"Expected leader '{leader}' not found"

    def test_get_taxonomy_response_matches_schema(self, client: TestClient):
        """Test that the response can be validated against TaxonomyConfig schema."""
        response = client.get("/taxonomy")
        assert response.status_code == 200

        data = response.json()

        # This should not raise any validation errors
        config = TaxonomyConfig.model_validate(data)
        assert isinstance(config, TaxonomyConfig)
        assert len(config.topics) > 0

    def test_get_taxonomy_returns_utf8_labels(self, client: TestClient):
        """Test that the API returns proper UTF-8 Spanish labels."""
        response = client.get("/taxonomy")
        assert response.status_code == 200

        data = response.json()

        # Check for Spanish characters in labels
        labels = [t["label"] for t in data["topics"]]
        labels.extend([l["label"] for l in data["targets"]["leaders"]])

        # Verify UTF-8 encoding is preserved
        spanish_chars = ["á", "é", "í", "ó", "ú", "ñ", "Á", "É", "Í", "Ó", "Ú", "Ñ"]
        has_spanish_chars = any(
            any(char in label for char in spanish_chars)
            for label in labels
        )
        assert has_spanish_chars, "Expected Spanish characters in labels"


class TestTaxonomyContentValidation:
    """Tests for validating taxonomy content in response."""

    def test_topic_has_subtopics(self, client: TestClient):
        """Test that topics have the expected subtopics."""
        response = client.get("/taxonomy")
        assert response.status_code == 200

        data = response.json()

        # Find vivienda topic and check its subtopics
        vivienda = next((t for t in data["topics"] if t["name"] == "vivienda"), None)
        assert vivienda is not None
        assert len(vivienda["subtopics"]) >= 2

        subtopic_names = [s["name"] for s in vivienda["subtopics"]]
        assert "alquiler" in subtopic_names
        assert "hipotecas" in subtopic_names

    def test_targets_have_distinct_names(self, client: TestClient):
        """Test that all targets have unique machine identifiers."""
        response = client.get("/taxonomy")
        assert response.status_code == 200

        data = response.json()

        party_names = [p["name"] for p in data["targets"]["parties"]]
        leader_names = [l["name"] for l in data["targets"]["leaders"]]

        # Check uniqueness within parties
        assert len(party_names) == len(set(party_names)), "Duplicate party names found"

        # Check uniqueness within leaders
        assert len(leader_names) == len(set(leader_names)), "Duplicate leader names found"

    def test_subtopics_have_valid_structure(self, client: TestClient):
        """Test that all subtopics have valid name and label fields."""
        response = client.get("/taxonomy")
        assert response.status_code == 200

        data = response.json()

        for topic in data["topics"]:
            for subtopic in topic["subtopics"]:
                # Name should be snake_case, no spaces
                assert " " not in subtopic["name"], f"Subtopic name '{subtopic['name']}' contains spaces"
                assert subtopic["name"] == subtopic["name"].lower(), f"Subtopic name '{subtopic['name']}' is not lowercase"

                # Label should not be empty
                assert subtopic["label"], f"Subtopic '{subtopic['name']}' has empty label"

    def test_topics_have_valid_structure(self, client: TestClient):
        """Test that all topics have valid name and label fields."""
        response = client.get("/taxonomy")
        assert response.status_code == 200

        data = response.json()

        for topic in data["topics"]:
            # Name should be snake_case, no spaces
            assert " " not in topic["name"], f"Topic name '{topic['name']}' contains spaces"
            assert topic["name"] == topic["name"].lower(), f"Topic name '{topic['name']}' is not lowercase"

            # Label should not be empty
            assert topic["label"], f"Topic '{topic['name']}' has empty label"

            # Each topic should have subtopics
            assert len(topic["subtopics"]) >= 2, f"Topic '{topic['name']}' has fewer than 2 subtopics"
