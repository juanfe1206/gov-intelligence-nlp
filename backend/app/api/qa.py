"""Q&A endpoint for natural-language retrieval, aggregation, and LLM answer generation."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.qa import service as qa_service
from app.qa.answer import generate_answer
from app.qa.schemas import QARequest, QAResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=QAResponse)
async def ask_question(
    request: Request,
    body: QARequest,
    session: AsyncSession = Depends(get_db),
) -> QAResponse:
    """Retrieve relevant posts, aggregate metrics, and generate an LLM narrative summary."""
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")

    top_n = max(1, min(body.top_n, 50))  # clamp to [1, 50]
    taxonomy = request.app.state.taxonomy
    f = body.filters  # QAFilters | None

    qa_result = await qa_service.retrieve_and_aggregate(
        session=session,
        taxonomy=taxonomy,
        question=body.question.strip(),
        topic=f.topic if f else None,
        subtopic=f.subtopic if f else None,
        party=f.party if f else None,
        start_date=f.start_date if f else None,
        end_date=f.end_date if f else None,
        platform=f.platform if f else None,
        top_n=top_n,
    )

    if not qa_result.insufficient_data:
        summary, answer_error = await generate_answer(
            question=qa_result.question,
            retrieved_posts=qa_result.retrieved_posts,
            metrics=qa_result.metrics,
        )
        qa_result.summary = summary
        qa_result.answer_error = answer_error

    return qa_result
