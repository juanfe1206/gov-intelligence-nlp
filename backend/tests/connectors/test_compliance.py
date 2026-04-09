"""Compliance and safety guardrails tests for connectors."""

import json
import re
import inspect
import logging
from pathlib import Path

import pytest
import yaml

from app.connectors.twitter_file import TwitterFileConnector
from app.connectors import service as connector_service
from app.api import connectors as connectors_api


class TestEnvExample:
    """Tests for .env.example file compliance."""

    def test_env_example_exists(self):
        """Verify .env.example is present and committed."""
        env_example = Path(__file__).parent.parent.parent / ".env.example"
        assert env_example.exists(), ".env.example not found — must be created for AC1"

    def test_env_example_contains_no_real_secrets(self):
        """Verify .env.example only contains placeholder values."""
        env_example = Path(__file__).parent.parent.parent / ".env.example"
        content = env_example.read_text()

        # Real Supabase URLs contain 'supabase.com'
        assert "supabase.com" not in content, "Real Supabase domain found in .env.example"

        # Real OpenAI keys match: sk-proj-[A-Za-z0-9]{20,}
        real_key_pattern = re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}")
        assert not real_key_pattern.search(content), "Real OpenAI key found in .env.example"

        # Database URLs must use placeholder values, not real hostnames
        for line in content.splitlines():
            if line.startswith("DATABASE_URL=") or line.startswith("DATABASE_SYNC_URL="):
                value = line.split("=", 1)[1].strip()
                # Must contain generic placeholder tokens, not real credentials
                assert "password" in value.lower() or "host" in value.lower(), \
                    f"Database URL appears to contain real credentials: {line}"

    def test_env_file_is_gitignored(self):
        """Verify .env is in .gitignore (critical safety check per Task 1)."""
        backend_dir = Path(__file__).parent.parent.parent
        gitignore_path = backend_dir / ".gitignore"
        root_gitignore_path = backend_dir.parent / ".gitignore"

        env_ignored = False

        for gitignore in [gitignore_path, root_gitignore_path]:
            if gitignore.exists():
                content = gitignore.read_text()
                if ".env" in content.splitlines():
                    env_ignored = True

        assert env_ignored, ".env not found in any .gitignore — secrets could be committed"


class TestConnectorMetadata:
    """Tests for connector metadata file compliance."""

    def test_twitter_metadata_file_exists(self):
        """Verify connector metadata file exists and has all required fields."""
        metadata_path = (
            Path(__file__).parent.parent.parent / "config" / "connectors" / "twitter-file.yaml"
        )
        assert metadata_path.exists(), "Connector metadata file not found"

        data = yaml.safe_load(metadata_path.read_text())
        assert data["connector_id"] == "twitter-file"
        assert "data_scope" in data
        assert "operational_limits" in data
        assert "credentials_required" in data
        assert "platform" in data, "Missing required field: platform"
        assert "collection_mode" in data, "Missing required field: collection_mode"
        assert "description" in data, "Missing required field: description"


class TestMaxRecordsLimit:
    """Tests for max_records operational limit enforcement."""

    def test_max_records_limit_enforced(self, tmp_path):
        """Verify fetch() respects max_records cap."""
        # Write 5 records to a temp JSONL file
        posts = [
            {
                "id": str(i),
                "full_text": f"post {i}",
                "user": {"screen_name": "user"},
                "created_at": "Thu Apr 01 12:00:00 +0000 2021",
                "lang": "es"
            }
            for i in range(5)
        ]
        jsonl_file = tmp_path / "posts.jsonl"
        jsonl_file.write_text("\n".join(json.dumps(p) for p in posts))

        connector = TwitterFileConnector(file_path=str(jsonl_file), max_records=3)
        records = connector.fetch()
        assert len(records) == 3, "max_records=3 should cap at 3 records"

    def test_max_records_zero_means_no_limit(self, tmp_path):
        """Verify max_records=0 returns all records."""
        posts = [
            {
                "id": str(i),
                "full_text": f"post {i}",
                "user": {"screen_name": "user"},
                "created_at": "Thu Apr 01 12:00:00 +0000 2021",
                "lang": "es"
            }
            for i in range(5)
        ]
        jsonl_file = tmp_path / "posts.jsonl"
        jsonl_file.write_text("\n".join(json.dumps(p) for p in posts))

        connector = TwitterFileConnector(file_path=str(jsonl_file), max_records=0)
        records = connector.fetch()
        assert len(records) == 5, "max_records=0 should return all records"

    def test_max_records_negative_raises_error(self, tmp_path):
        """Verify negative max_records raises ValueError."""
        jsonl_file = tmp_path / "posts.jsonl"
        jsonl_file.write_text('{"id": "1", "full_text": "test", "user": {"screen_name": "u"}, "created_at": "Thu Apr 01 12:00:00 +0000 2021", "lang": "es"}')

        with pytest.raises(ValueError, match="max_records must be >= 0"):
            TwitterFileConnector(file_path=str(jsonl_file), max_records=-1)


class TestNoSecretsInLogs:
    """Tests to verify no secrets are logged by connector code."""

    def test_no_secrets_in_connector_logs(self):
        """Verify connector log format strings contain no credential patterns."""
        secret_patterns = [
            re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}"),           # OpenAI keys
            re.compile(r"postgresql\+asyncpg://[^@]+:[^@]+@"),     # DB URL with credentials
            re.compile(r"Bearer [A-Za-z0-9_\-\.]{20,}"),           # Bearer tokens
        ]

        # Inspect actual source code of all audited modules
        audited_modules = [
            ("service", connector_service),
            ("api/connectors", connectors_api),
        ]

        for module_name, module in audited_modules:
            source = inspect.getsource(module)
            for pattern in secret_patterns:
                assert not pattern.search(source), \
                    f"Secret pattern found in {module_name} source: {pattern.pattern}"

    def test_twitter_file_connector_no_logger_calls(self):
        """Verify TwitterFileConnector has no logger calls that could leak secrets."""
        source = inspect.getsource(TwitterFileConnector)
        assert "logger" not in source, \
            "TwitterFileConnector should not have any logger calls (security per BaseConnector docstring)"