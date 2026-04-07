"""Tests for ingestion API endpoints."""

import csv
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestPostIngest:
    """Tests for POST /ingest endpoint."""

    def test_post_ingest_returns_success_response(self, client: TestClient, monkeypatch):
        """Test that POST /ingest returns 200 with summary."""
        # Create temp CSV
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "author", "created_at"])
            writer.writeheader()
            writer.writerow({
                "text": "Test post for API",
                "platform": "twitter",
                "author": "testuser",
                "created_at": "2024-01-15T10:00:00",
            })
            temp_path = f.name

        # Patch the settings to use temp file
        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", temp_path)

        response = client.post("/ingest")

        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "completed"
        assert "processed" in data
        assert "inserted" in data
        assert data["processed"] >= 1

        # Cleanup
        Path(temp_path).unlink()

    def test_post_ingest_returns_summary_structure(self, client: TestClient, monkeypatch):
        """Test that response matches IngestionSummary schema."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Test post", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            temp_path = f.name

        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", temp_path)

        response = client.post("/ingest")
        assert response.status_code == 200

        data = response.json()

        # Verify all required fields exist
        required_fields = [
            "status",
            "source",
            "processed",
            "inserted",
            "skipped",
            "duplicates",
            "errors",
            "started_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Verify types
        assert isinstance(data["status"], str)
        assert isinstance(data["source"], str)
        assert isinstance(data["processed"], int)
        assert isinstance(data["inserted"], int)
        assert isinstance(data["skipped"], int)
        assert isinstance(data["duplicates"], int)
        assert isinstance(data["errors"], list)

        Path(temp_path).unlink()

    def test_post_ingest_handles_invalid_csv_gracefully(self, client: TestClient, monkeypatch):
        """Test that invalid CSV returns completed with errors, not 500."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})  # Empty text
            temp_path = f.name

        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", temp_path)

        response = client.post("/ingest")

        # Should return 200 even with skipped rows
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "completed"
        assert data["processed"] == 1
        assert data["skipped"] == 1
        assert len(data["errors"]) > 0

        Path(temp_path).unlink()

    def test_post_ingest_file_not_found_returns_failed_status(self, client: TestClient, monkeypatch):
        """Test that missing file returns failed status with error."""
        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", str(Path(tempfile.gettempdir()) / "missing-ingest.csv"))

        response = client.post("/ingest")

        # Should return 200 with failed status
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "failed"
        assert len(data["errors"]) > 0

    def test_post_ingest_idempotent_duplicate_detection(self, client: TestClient, monkeypatch):
        """Test that running same file twice detects duplicates."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Duplicate test post", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            temp_path = f.name

        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", temp_path)

        # First call
        response1 = client.post("/ingest")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["inserted"] == 1
        assert data1["duplicates"] == 0

        # Second call - should detect duplicate
        response2 = client.post("/ingest")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["inserted"] == 0
        assert data2["duplicates"] == 1

        Path(temp_path).unlink()

    def test_post_ingest_mixed_valid_invalid_rows(self, client: TestClient, monkeypatch):
        """Test mixed file with valid and invalid rows."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({
                "text": "Valid post",
                "platform": "twitter",
                "created_at": "2024-01-15T10:00:00",
            })
            writer.writerow({
                "text": "",
                "platform": "twitter",
                "created_at": "2024-01-15T10:00:00",
            })  # Invalid: empty text
            writer.writerow({
                "text": "Another valid",
                "platform": "facebook",
                "created_at": "invalid-timestamp",
            })  # Invalid: bad timestamp
            temp_path = f.name

        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", temp_path)

        response = client.post("/ingest")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "completed"
        assert data["processed"] == 3
        assert data["inserted"] == 1
        assert data["skipped"] == 2

        Path(temp_path).unlink()

    def test_post_ingest_with_metadata_columns(self, client: TestClient, monkeypatch):
        """Test that extra columns are stored as metadata."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at", "post_id", "likes"])
            writer.writeheader()
            writer.writerow({
                "text": "Post with metadata",
                "platform": "twitter",
                "created_at": "2024-01-15T10:00:00",
                "post_id": "12345",
                "likes": "100",
            })
            temp_path = f.name

        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", temp_path)

        response = client.post("/ingest")
        assert response.status_code == 200
        data = response.json()
        assert data["inserted"] == 1

        Path(temp_path).unlink()


class TestIngestionResponseValidation:
    """Tests for validating ingestion response content."""

    def test_response_timestamps_are_iso8601(self, client: TestClient, monkeypatch):
        """Test that timestamps are in ISO 8601 format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Test", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            temp_path = f.name

        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", temp_path)

        response = client.post("/ingest")
        data = response.json()

        # Verify timestamps are ISO 8601 strings
        if data.get("started_at"):
            assert "T" in data["started_at"]  # ISO 8601 marker
        if data.get("finished_at"):
            assert "T" in data["finished_at"]

        Path(temp_path).unlink()

    def test_response_source_matches_config(self, client: TestClient, monkeypatch):
        """Test that response source matches configured source name."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["text", "platform", "created_at"])
            writer.writeheader()
            writer.writerow({"text": "Test", "platform": "twitter", "created_at": "2024-01-15T10:00:00"})
            temp_path = f.name

        from app import config
        monkeypatch.setattr(config.settings, "INGESTION_CSV_PATH", temp_path)
        monkeypatch.setattr(config.settings, "INGESTION_SOURCE_NAME", "custom_source")

        response = client.post("/ingest")
        data = response.json()

        assert data["source"] == "custom_source"

        Path(temp_path).unlink()
