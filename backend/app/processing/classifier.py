"""OpenAI-based classification logic for NLP processing."""

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from app.processing.schemas import ClassificationResult

logger = logging.getLogger(__name__)

# Lazy initialization of OpenAI client
_openai_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create the OpenAI async client."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def build_classification_prompt(text: str, taxonomy: dict[str, Any]) -> str:
    """Build a prompt for classifying a political post.

    Args:
        text: The post text to classify
        taxonomy: Loaded taxonomy with topics, subtopics, and targets

    Returns:
        Formatted prompt string for the LLM
    """
    # Extract taxonomy values
    topics = taxonomy.get("topics", [])
    subtopics = taxonomy.get("subtopics", [])
    targets = taxonomy.get("targets", [])

    topics_str = ", ".join(topics) if topics else "various political topics"
    subtopics_str = ", ".join(subtopics) if subtopics else "relevant subtopics"
    targets_str = ", ".join(targets) if targets else "political figures and entities"

    prompt = f"""You are analyzing a political social media post. Classify it according to the following taxonomy.

Post text:
"{text}"

Available topics: {topics_str}
Available subtopics: {subtopics_str}
Available targets: {targets_str}

Classify this post and return ONLY a JSON object with this exact structure:
{{
    "topic": "the main topic from the available list (required)",
    "subtopic": "the relevant subtopic or null if none fits (string or null)",
    "sentiment": "positive, neutral, or negative (required)",
    "target": "the primary political target or null if none (string or null)",
    "intensity": "a number from 1-10 representing strength of sentiment/target relevance (number or null)"
}}

Rules:
- Topic must be from the available topics list
- Sentiment must be exactly: "positive", "neutral", or "negative"
- Intensity is 1-10 where 10 is extremely strong sentiment or highly relevant target
- Return null for fields where the value is unclear or not applicable
- Respond with ONLY the JSON object, no additional text"""

    return prompt


async def classify_post(
    text: str,
    taxonomy: dict[str, Any],
    model: str | None = None,
) -> ClassificationResult | None:
    """Classify a single post using OpenAI.

    Args:
        text: The post text to classify
        taxonomy: Loaded taxonomy configuration
        model: OpenAI model to use (defaults to settings.OPENAI_CHAT_MODEL)

    Returns:
        ClassificationResult or None if classification failed
    """
    client = get_openai_client()
    model = model or settings.OPENAI_CHAT_MODEL

    prompt = build_classification_prompt(text, taxonomy)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a political text analysis assistant. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # Lower temperature for more consistent outputs
            max_tokens=500,
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty response from OpenAI for classification")
            return None

        # Parse the JSON response
        data = json.loads(content)

        # Validate and normalize the result
        result = ClassificationResult(
            topic=data.get("topic", "unknown"),
            subtopic=data.get("subtopic"),
            sentiment=data.get("sentiment", "neutral"),
            target=data.get("target"),
            intensity=data.get("intensity"),
        )

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse classification response: {e}")
        return None
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return None


async def classify_batch(
    texts: list[str],
    taxonomy: dict[str, Any],
    model: str | None = None,
) -> list[ClassificationResult | None]:
    """Classify a batch of posts sequentially.

    Note: OpenAI doesn't support true batch classification for chat completions,
    so we process sequentially with error isolation.

    Args:
        texts: List of post texts to classify
        taxonomy: Loaded taxonomy configuration
        model: OpenAI model to use

    Returns:
        List of ClassificationResult or None for each text
    """
    results = []
    for text in texts:
        try:
            result = await classify_post(text, taxonomy, model)
            results.append(result)
        except Exception as e:
            logger.error(f"Batch classification error for text: {e}")
            results.append(None)
    return results
