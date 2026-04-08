"""LLM answer generation for Q&A responses."""

import logging

from openai import APIError, APITimeoutError

from app.config import settings
from app.processing.embeddings import get_openai_client
from app.qa.schemas import QAMetrics, QAPostItem

logger = logging.getLogger(__name__)

EVIDENCE_POST_LIMIT = 10  # top evidence posts included in prompt
DEGRADATION_MESSAGE = (
    "Answer generation temporarily unavailable — here are the retrieved posts and metrics"
)


async def generate_answer(
    question: str,
    retrieved_posts: list[QAPostItem],
    metrics: QAMetrics,
) -> tuple[str | None, str | None]:
    """Call OpenAI chat completion to generate a narrative summary.

    Returns:
        (summary, None) on success
        (None, error_message) on OpenAI failure
    """
    evidence = retrieved_posts[:EVIDENCE_POST_LIMIT]

    post_lines = "\n".join(
        (
            f"- [{p.sentiment.upper()}] ({p.platform}, {p.created_at}) "
            f"[subtopic: {p.subtopic_label or p.subtopic or 'n/a'}]: {p.original_text[:200]}"
        )
        for p in evidence
    )

    system_prompt = (
        "You are a political intelligence analyst. "
        "Your task is to synthesize social media data into concise, evidence-based insights. "
        "Be direct and factual. Provide sufficient detail to answer the question, but avoid unnecessary verbosity. "
        "Do not speculate beyond the data."
    )

    user_prompt = (
        f"Question: {question}\n\n"
        f"Retrieved {metrics.total_retrieved} posts. "
        f"Sentiment breakdown: {metrics.positive_count} positive, "
        f"{metrics.neutral_count} neutral, {metrics.negative_count} negative.\n\n"
        f"Top evidence posts:\n{post_lines}\n\n"
        "Write a concise narrative answer that directly addresses the question using the sentiment data "
        "and evidence above. Be succinct but thorough — use more detail when the evidence warrants it."
    )

    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=300,  # concise 2-4 sentence target
            temperature=0.3,
        )
        choices = response.choices or []
        summary = choices[0].message.content if choices else None
        if summary:
            summary = summary.strip()
        if not summary:
            return None, DEGRADATION_MESSAGE
        return summary, None
    except (APIError, APITimeoutError) as exc:
        logger.warning("OpenAI chat completion failed: %s", exc)
        return None, DEGRADATION_MESSAGE
    except Exception as exc:
        logger.error("Unexpected error during answer generation: %s", exc)
        return None, DEGRADATION_MESSAGE
