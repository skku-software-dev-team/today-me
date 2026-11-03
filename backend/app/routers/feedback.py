import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jwt import get_current_user_id
from app.core.redis import get_redis
from app.services.memory import apply_feedback

logger = logging.getLogger("feedback")
router = APIRouter(prefix="/v1", tags=["feedback"])

OPTIMIZE_EVERY = 10  # 사용자의 새 피드백 N개마다 프롬프트 개선


class FeedbackRequest(BaseModel):
    report_id: uuid.UUID
    agent: Literal["music", "place", "food", "style"]
    pick_index: int = Field(ge=0)
    score: Literal[1, -1]
    comment: str | None = None


async def _count_and_trigger(redis, user_id: str) -> None:
    """새 피드백을 세고 N번째마다 개선을 예약한다. 실패해도 피드백 요청은 성공시킨다."""
    try:
        # INCR은 원자적이라 동시 요청에도 N번째 요청이 정확히 하나만 나온다.
        count = await redis.incr(f"feedback_count:{user_id}")
        if count % OPTIMIZE_EVERY == 0:
            from app.tasks.optimize import optimize_prompts

            optimize_prompts.delay(user_id=user_id)
    except Exception:
        logger.exception("프롬프트 개선 예약 실패 user_id=%s", user_id)


@router.post("/feedback")
async def feedback(
    body: FeedbackRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    is_new = await apply_feedback(
        db=db,
        report_id=body.report_id,
        user_id=uuid.UUID(user_id),
        agent=body.agent,
        pick_index=body.pick_index,
        score=body.score,
        comment=body.comment,
    )

    if is_new:
        await _count_and_trigger(redis, user_id)

    return {"status": "ok"}
