from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jwt import get_current_user_id
from app.tasks.image import generate_moodboard

router = APIRouter(prefix="/v1/moodboard", tags=["moodboard"])


@router.post("/{report_id}/generate")
async def request_moodboard(
    report_id: str,
    mood: str,
    weather: str,
    energy: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT id FROM daily_states WHERE id = :id AND user_id = :uid"),
        {"id": report_id, "uid": user_id},
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    task = generate_moodboard.delay(report_id, mood, weather, energy)
    return {"task_id": task.id, "status": "queued"}


@router.get("/{report_id}")
async def get_moodboard(
    report_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT moodboard FROM daily_states WHERE id = :id AND user_id = :uid"),
        {"id": report_id, "uid": user_id},
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    moodboard_url = row[0]
    return {
        "report_id": report_id,
        "status": "completed" if moodboard_url else "pending",
        "moodboard_url": moodboard_url,
    }
