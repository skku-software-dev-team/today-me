from fastapi import APIRouter, Depends

from app.core.jwt import get_current_user_id
from app.core.redis import get_redis

router = APIRouter(prefix="/v1/moodboard", tags=["moodboard"])


@router.get("/{report_id}")
async def get_moodboard(
    report_id: str,
    _: str = Depends(get_current_user_id),
):
    r = await get_redis()
    url = await r.get(f"moodboard:{report_id}")
    return {
        "report_id": report_id,
        "status": "completed" if url else "pending",
        "moodboard_url": url,
    }
