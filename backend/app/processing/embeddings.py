"""OpenAI embedding generation with vector normalization."""

import logging
from typing import Any

import numpy as np
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy initialization of OpenAI client
_ollama_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create the OpenAI async client."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _ollama_client


def normalize_vector(vector: list[float]) -> list[float]:
    """Normalize a vector to unit length for cosine similarity compatibility.

    Args:
        vector: Raw embedding vector from OpenAI

    Returns:
        Normalized vector with unit L2 norm
    """
    arr = np.array(vector, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return vector  # Return original if zero vector
    normalized = arr / norm
    return normalized.tolist()


async def generate_embeddings(
    texts: list[str],
    model: str | None = None,
) -> list[list[float] | None]:
    """Generate embeddings for a list of texts using OpenAI API.

    Args:
        texts: List of text strings to embed
        model: OpenAI embedding model to use (defaults to settings.OPENAI_EMBEDDING_MODEL)

    Returns:
        List of normalized embedding vectors, or None for texts that failed
    """
    if not texts:
        return []

    client = get_openai_client()
    model = model or settings.OPENAI_EMBEDDING_MODEL

    try:
        # OpenAI embeddings API supports up to 2048 texts per call
        response = await client.embeddings.create(
            model=model,
            input=texts,
        )

        embeddings = []
        for item in response.data:
            # Normalize the embedding vector
            normalized = normalize_vector(item.embedding)
            embeddings.append(normalized)

        return embeddings

    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        # Return None for all texts on complete failure
        return [None] * len(texts)


async def generate_single_embedding(
    text: str,
    model: str | None = None,
) -> list[float] | None:
    """Generate embedding for a single text.

    Args:
        text: Text string to embed
        model: OpenAI embedding model to use

    Returns:
        Normalized embedding vector, or None if failed
    """
    embeddings = await generate_embeddings([text], model)
    return embeddings[0] if embeddings else None
