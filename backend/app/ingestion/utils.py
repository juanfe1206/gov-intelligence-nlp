"""Utility functions for CSV ingestion."""

import hashlib
import re


def normalize_text(text: str) -> str:
    """Normalize text for consistent hashing.

    - Converts to lowercase
    - Strips leading/trailing whitespace
    - Collapses multiple whitespace characters to single space
    """
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized text for deduplication.

    Args:
        text: Raw post text

    Returns:
        Hex digest of SHA-256 hash (64 characters)
    """
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
