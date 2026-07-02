import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jwt import get_current_user_id
from app.services.memory import apply_feedback

router = APIRouter(prefix="/api/v1", tags=["feedback"])


class FeedbackRequest(BaseModel):
    report_id: uuid.UUID
    agent: Literal["music", "place", "food", "style"]
    pick_index: int
    score: Literal[1, -1]
    comment: str | None = None


@router.post("/feedback")
async def feedback(
    body: FeedbackRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await apply_feedback(
        db=db,
        report_id=body.report_id,
        agent=body.agent,
        pick_index=body.pick_index,
        score=body.score,
        comment=body.comment,
    )
    return {"status": "ok"}
