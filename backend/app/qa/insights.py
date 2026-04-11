"""Structured insight generation for Q&A responses."""

import json
import logging
from typing import Any

from openai import APIError, APITimeoutError

from app.config import settings
from app.processing.embeddings import get_openai_client
from app.qa.schemas import QAMetrics, QAPostItem, StructuredInsight

logger = logging.getLogger(__name__)

EVIDENCE_POST_LIMIT = 8  # top evidence posts included in prompt


async def generate_structured_insight(
    question: str,
    retrieved_posts: list[QAPostItem],
    metrics: QAMetrics,
) -> StructuredInsight | None:
    """Call OpenAI to generate structured insight data for visualizations.

    Returns:
        StructuredInsight on success, None on failure
    """
    evidence = retrieved_posts[:EVIDENCE_POST_LIMIT]

    post_lines = "\n".join(
        (
            f"- [{p.sentiment.upper()}] ({p.platform}, {p.created_at}) "
            f"[subtopic: {p.subtopic_label or p.subtopic or 'n/a'}]: {p.original_text[:150]}"
        )
        for p in evidence
    )

    # Calculate sentiment percentages
    total = metrics.total_retrieved or 1
    pos_pct = round((metrics.positive_count / total) * 100)
    neu_pct = round((metrics.neutral_count / total) * 100)
    neg_pct = round((metrics.negative_count / total) * 100)

    # Get top subtopics for trends
    top_subtopics = metrics.top_subtopics[:5]

    system_prompt = (
        "You are a political intelligence analyst generating structured insight data. "
        "Respond ONLY with valid JSON matching the requested schema. "
        "Be concise and data-driven. Focus on actionable intelligence."
    )

    user_prompt = f"""Question: {question}

Metrics:
- Total posts: {metrics.total_retrieved}
- Sentiment: {metrics.positive_count} positive ({pos_pct}%), {metrics.neutral_count} neutral ({neu_pct}%), {metrics.negative_count} negative ({neg_pct}%)
- Top subtopics: {', '.join([s.subtopic_label for s in top_subtopics]) if top_subtopics else 'N/A'}

Evidence posts:
{post_lines}

Generate a JSON response with this exact structure:
{{
  "headline": "One sentence summary of the key finding",
  "key_stats": [
    {{
      "label": "Stat name",
      "value": "value or number",
      "trend": "up|down|neutral|null",
      "trend_value": "+15% or similar (optional)",
      "context": "brief context"
    }}
  ],
  "sentiment_summary": {{
    "positive": "{pos_pct}%",
    "neutral": "{neu_pct}%",
    "negative": "{neg_pct}%",
    "interpretation": "brief interpretation"
  }},
  "trends": [
    {{
      "label": "Trending topic",
      "direction": "rising|falling|stable",
      "magnitude": "high|medium|low",
      "volume_change": "+45% or similar (optional)"
    }}
  ],
  "key_takeaways": [
    {{
      "type": "positive|negative|neutral|warning|opportunity",
      "text": "insight text"
    }}
  ],
  "recommended_actions": [
    {{
      "priority": "high|medium|low",
      "text": "action recommendation",
      "rationale": "why this matters (optional)"
    }}
  ]
}}

Guidelines:
- headline: 1 sentence, max 15 words, impactful
- key_stats: 2-4 stats that directly answer the question
- trends: 1-3 trending themes from the subtopics
- key_takeaways: 2-3 bullets, mix of insight types
- recommended_actions: 1-2 high-value actions
- Be specific and cite numbers from the evidence
- Focus on what a politician needs to know"""

    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=800,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        choices = response.choices or []
        content = choices[0].message.content if choices else None

        if not content:
            logger.warning("Empty LLM response for structured insight")
            return None

        # Parse JSON response
        data = json.loads(content)
        return StructuredInsight(**data)

    except (APIError, APITimeoutError) as exc:
        logger.warning("OpenAI structured insight generation failed: %s", exc)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse LLM JSON response: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error during structured insight generation: %s", exc)
        return None
