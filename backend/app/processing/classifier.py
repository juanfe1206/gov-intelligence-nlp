"""OpenAI-based classification logic for NLP processing."""

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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


def _coerce_to_taxonomy(
    result: ClassificationResult,
    taxonomy: dict[str, Any],
) -> ClassificationResult | None:
    """Coerce classification result to valid taxonomy values.

    - Unknown topic: reject entirely (topic is required and drives everything else)
    - Unknown subtopic or target: set to None and keep the rest
    """
    topics = {str(item) for item in taxonomy.get("topics", [])}
    subtopics = {str(item) for item in taxonomy.get("subtopics", [])}
    targets = {str(item) for item in taxonomy.get("targets", [])}

    if topics and result.topic not in topics:
        logger.warning("Classification rejected: topic=%r not in taxonomy", result.topic)
        return None

    subtopic = result.subtopic
    if subtopic is not None and subtopics and subtopic not in subtopics:
        logger.warning("Dropping unknown subtopic=%r (not in taxonomy)", subtopic)
        subtopic = None

    target = result.target
    if target is not None and targets and target not in targets:
        logger.warning("Dropping unknown target=%r (not in taxonomy)", target)
        target = None

    return ClassificationResult(
        topic=result.topic,
        subtopic=subtopic,
        sentiment=result.sentiment,
        target=target,
        intensity=result.intensity,
    )


@retry(
    reraise=True,
    stop=stop_after_attempt(settings.PROCESSING_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(Exception),
)
async def _create_classification_completion(
    *,
    model: str,
    prompt: str,
) -> Any:
    """Call OpenAI classification API with retry/backoff."""
    client = get_openai_client()
    return await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a political text analysis assistant. Always respond with valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=500,
    )


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
    model = model or settings.OPENAI_CHAT_MODEL

    prompt = build_classification_prompt(text, taxonomy)

    try:
        response = await _create_classification_completion(model=model, prompt=prompt)

        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty response from OpenAI for classification")
            return None

        # Parse the JSON response
        data = json.loads(content)

        def _str_or_none(val: Any) -> str | None:
            """Normalize LLM null-like strings to Python None."""
            if val is None or (isinstance(val, str) and val.strip().lower() in ("null", "none", "")):
                return None
            return val

        # Validate and normalize the result
        result = ClassificationResult(
            topic=data.get("topic", ""),
            subtopic=_str_or_none(data.get("subtopic")),
            sentiment=data.get("sentiment", "neutral"),
            target=_str_or_none(data.get("target")),
            intensity=data.get("intensity"),
        )

        result = _coerce_to_taxonomy(result, taxonomy)

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
