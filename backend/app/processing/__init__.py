"""NLP Processing pipeline module for classification and embedding generation."""

from app.processing.schemas import ClassificationResult, ProcessingSummary
from app.processing.service import process_posts

__all__ = ["ClassificationResult", "ProcessingSummary", "process_posts"]
