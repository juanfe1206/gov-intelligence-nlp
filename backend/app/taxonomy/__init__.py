"""Taxonomy package for political intelligence classification.

This package provides:
- Pydantic models for taxonomy configuration (schemas)
- YAML loading and validation (loader)

The taxonomy defines the allowed topics, subtopics, and political targets
used by the NLP pipeline to classify social media posts and news articles.
"""

from app.taxonomy.loader import load_taxonomy
from app.taxonomy.schemas import (
    TaxonomyConfig,
    TaxonomySubtopic,
    TaxonomyTarget,
    TaxonomyTargets,
    TaxonomyTopic,
)

__all__ = [
    "load_taxonomy",
    "TaxonomyConfig",
    "TaxonomyTopic",
    "TaxonomySubtopic",
    "TaxonomyTargets",
    "TaxonomyTarget",
]
