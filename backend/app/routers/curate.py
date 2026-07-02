import logging
import traceback
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agents.graph import orchestrator
from app.agents.state import DailyState
from app.core.jwt import get_current_user_id

logger = logging.getLogger("curate")
router = APIRouter(prefix="/api/v1", tags=["curate"])


class LocationIn(BaseModel):
    lat: float
    lng: float


class CurateRequest(BaseModel):
    mood: str
    weather: str = ""
    energy: int
    location: LocationIn


# 프론트 types.ts 와 1:1 대응
class MusicPickOut(BaseModel):
    title: str
    artist: str
    youtube_url: str


class PlacePickOut(BaseModel):
    name: str
    address: str
    maps_url: str
    reason: str


class FoodPickOut(BaseModel):
    name: str
    cuisine: str
    address: str
    reason: str


class StylePickOut(BaseModel):
    description: str
    reason: str
    image_url: str = ""
    product_url: str = ""


class CurateResponse(BaseModel):
    report_id: str
    music_picks: list[MusicPickOut]
    place_picks: list[PlacePickOut]
    food_picks: list[FoodPickOut]
    style_picks: list[StylePickOut]
    moodboard_url: str | None
    created_at: str


@router.post("/curate", response_model=CurateResponse)
async def curate(body: CurateRequest, user_id: str = Depends(get_current_user_id)):
    report_id = str(uuid.uuid4())

    initial: DailyState = {
        "user_id": user_id,
        "mood": body.mood,
        "weather": body.weather,
        "energy": body.energy,
        "location": {
            "lat": body.location.lat,
            "lng": body.location.lng,
            "district": None,
        },
        "music_picks": [],
        "place_picks": [],
        "food_picks": [],
        "style_picks": [],
        "moodboard_url": None,
        "rag_context": "",
        "llm_calls": [],
        "messages": [],
        "report_id": report_id,
    }

    try:
        result: DailyState = await orchestrator.ainvoke(
            initial,
            config={"recursion_limit": 25},
        )
    except Exception as exc:
        logger.error("curate orchestration failed:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return CurateResponse(
        report_id=result.get("report_id") or report_id,
        music_picks=result.get("music_picks", []),
        place_picks=result.get("place_picks", []),
        food_picks=result.get("food_picks", []),
        style_picks=result.get("style_picks", []),
        moodboard_url=result.get("moodboard_url"),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
