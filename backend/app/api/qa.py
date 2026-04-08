"""Q&A endpoint for natural-language retrieval and aggregation."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.qa import service as qa_service
from app.qa.schemas import QARequest, QAResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=QAResponse)
async def ask_question(
    request: Request,
    body: QARequest,
    session: AsyncSession = Depends(get_db),
) -> QAResponse:
    """Retrieve relevant posts and aggregate metrics for a natural-language question.

    Performs vector similarity search over processed_posts.embedding,
    scoped to any provided filters. Returns retrieved posts + aggregated metrics.
    Story 3.2 extends this to generate an LLM narrative summary.
    """
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")

    top_n = max(1, min(body.top_n, 50))  # clamp to [1, 50]
    taxonomy = request.app.state.taxonomy
    f = body.filters  # QAFilters | None

    return await qa_service.retrieve_and_aggregate(
        session=session,
        taxonomy=taxonomy,
        question=body.question.strip(),
        topic=f.topic if f else None,
        party=f.party if f else None,
        start_date=f.start_date if f else None,
        end_date=f.end_date if f else None,
        platform=f.platform if f else None,
        top_n=top_n,
    )
