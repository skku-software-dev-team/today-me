from operator import add
from typing import Annotated, TypedDict


class Location(TypedDict):
    lat: float
    lng: float
    district: str | None


class MusicPick(TypedDict):
    title: str
    artist: str
    youtube_url: str


class PlacePick(TypedDict):
    name: str
    address: str
    maps_url: str
    reason: str


class FoodPick(TypedDict):
    name: str
    cuisine: str
    address: str
    reason: str


class StylePick(TypedDict):
    description: str
    reason: str


class DailyState(TypedDict):
    # 입력
    user_id: str
    mood: str
    weather: str
    energy: int
    location: Location

    # 에이전트 결과 — Annotated[list, add] 로 병렬 머지
    music_picks: Annotated[list[MusicPick], add]
    place_picks: Annotated[list[PlacePick], add]
    food_picks: Annotated[list[FoodPick], add]
    style_picks: Annotated[list[StylePick], add]
    llm_calls: Annotated[list[str], add]

    # 단일값 (마지막 write 승리)
    moodboard_url: str | None
    rag_context: str
    messages: list[dict]
    report_id: str
