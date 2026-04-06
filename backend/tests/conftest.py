"""Pytest configuration and fixtures for backend tests."""

import sys
from pathlib import Path

# Ensure backend package is importable when running tests from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for making HTTP requests."""
    return TestClient(app)
