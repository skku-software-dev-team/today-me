import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jwt import get_current_user_id
from app.models.report import DailyReport

router = APIRouter(prefix="/v1", tags=["history"])


class HistoryReport(BaseModel):
    report_id: str
    mood: str
    weather: str
    energy: int
    moodboard_url: str | None
    created_at: str


class HistoryResponse(BaseModel):
    total: int
    reports: list[HistoryReport]


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user_id)

    total_result = await db.execute(
        select(func.count()).select_from(DailyReport).where(DailyReport.user_id == uid)
    )
    total = total_result.scalar_one()

    rows_result = await db.execute(
        select(DailyReport)
        .where(DailyReport.user_id == uid)
        .order_by(DailyReport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = rows_result.scalars().all()

    return HistoryResponse(
        total=total,
        reports=[
            HistoryReport(
                report_id=str(r.id),
                mood=r.mood,
                weather=r.weather or "",
                energy=r.energy,
                moodboard_url=r.moodboard_url,
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ],
    )
