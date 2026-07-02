import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jwt import get_current_user_id
from app.models.report import DailyReport
from app.services.memory import apply_feedback

router = APIRouter(prefix="/v1", tags=["feedback"])

OPTIMIZE_EVERY = 10  # N번 피드백마다 최적화 트리거


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

    # 전체 피드백 수가 N의 배수일 때 해당 에이전트 최적화 트리거
    total = await db.scalar(
        select(func.count())
        .select_from(DailyReport)
        .where(
            DailyReport.user_id == uuid.UUID(user_id),
            DailyReport.feedback != {},
        )
    )
    if total and total % OPTIMIZE_EVERY == 0:
        from app.tasks.optimize import optimize_prompts

        optimize_prompts.delay(agent=body.agent)

    return {"status": "ok"}
