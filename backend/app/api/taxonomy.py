"""Taxonomy API endpoints."""

from fastapi import APIRouter, Request

from app.taxonomy.schemas import TaxonomyConfig

router = APIRouter()


@router.get("", response_model=TaxonomyConfig)
async def get_taxonomy(request: Request) -> TaxonomyConfig:
    """Return the full political taxonomy.

    Returns the complete taxonomy configuration including all topics,
    subtopics, and political targets (parties and leaders) that are
    used for NLP classification of posts.

    Returns:
        TaxonomyConfig: Complete taxonomy with topics and targets

    Example response:
        {
            "topics": [
                {
                    "name": "vivienda",
                    "label": "Vivienda",
                    "subtopics": [
                        {"name": "alquiler", "label": "Alquiler"}
                    ]
                }
            ],
            "targets": {
                "parties": [{"name": "pp", "label": "Partido Popular"}],
                "leaders": [{"name": "sanchez", "label": "Pedro Sánchez"}]
            }
        }
    """
    return request.app.state.taxonomy_config
