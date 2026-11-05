"""에이전트 일부가 실패해도 나머지 추천을 제공하는지 실제 LangGraph 흐름으로 검증한다."""

import asyncio
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from app.agents import graph
from app.core.jwt import get_current_user_id
from app.routers import curate

PICKS = {
    "music_agent": ("music_picks", {"title": "곡", "artist": "가수", "youtube_url": "u"}),
    "place_agent": ("place_picks", {"name": "곳", "address": "a", "maps_url": "u", "reason": "r"}),
    "food_agent": ("food_picks", {"name": "밥", "cuisine": "한식", "address": "a", "reason": "r"}),
    "style_agent": ("style_picks", {"description": "옷", "reason": "r"}),
}


def _nodes(failing: set[str] = frozenset(), empty: set[str] = frozenset()) -> dict:
    def make(name: str, key: str, pick: dict):
        async def node(state):
            if name in failing:
                raise ConnectionError(f"{name} down")
            return {key: [] if name in empty else [pick], "llm_calls": [name]}

        return key, node

    return {name: make(name, key, pick) for name, (key, pick) in PICKS.items()}


@pytest.fixture
def saved(monkeypatch):
    calls = []

    async def fake_contexts(**kwargs):
        return {}

    async def fake_save(state):
        calls.append(state)
        return SimpleNamespace(id=state["report_id"])

    monkeypatch.setattr(graph, "get_agent_contexts", fake_contexts)
    monkeypatch.setattr(graph, "save_report", fake_save)
    return calls


def _initial() -> dict:
    return {
        "user_id": str(uuid.uuid4()),
        "report_id": str(uuid.uuid4()),
        "mood": "지침",
        "weather": "비",
        "energy": 2,
        "location": {"lat": 0, "lng": 0, "district": None},
        "music_picks": [],
        "place_picks": [],
        "food_picks": [],
        "style_picks": [],
        "llm_calls": [],
    }


def test_one_failure_keeps_other_results_and_saves(saved):
    result = asyncio.run(
        graph.build_orchestrator(_nodes(failing={"music_agent"})).ainvoke(_initial())
    )

    assert result["music_picks"] == []
    assert result["place_picks"] and result["food_picks"] and result["style_picks"]
    assert "music_agent:failed" in result["llm_calls"]
    assert len(saved) == 1
    assert saved[0]["music_picks"] == [] and saved[0]["place_picks"]


def test_three_failures_still_return_remaining_result(saved):
    failing = {"music_agent", "place_agent", "food_agent"}

    result = asyncio.run(graph.build_orchestrator(_nodes(failing=failing)).ainvoke(_initial()))

    assert result["style_picks"]
    assert len(saved) == 1


def test_all_failures_raise_and_do_not_save(saved):
    with pytest.raises(RuntimeError):
        asyncio.run(graph.build_orchestrator(_nodes(failing=set(PICKS))).ainvoke(_initial()))

    assert saved == []


def test_all_empty_results_do_not_save(saved):
    with pytest.raises(RuntimeError):
        asyncio.run(graph.build_orchestrator(_nodes(empty=set(PICKS))).ainvoke(_initial()))

    assert saved == []


def test_cancellation_is_not_swallowed():
    async def cancelled(state):
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(graph._isolated("music_agent", "music_picks", cancelled)({}))


def _post_curate(monkeypatch, nodes: dict) -> httpx.Response:
    async def no_moodboard(report_id, state):
        return None

    monkeypatch.setattr(curate, "orchestrator", graph.build_orchestrator(nodes))
    monkeypatch.setattr(curate, "_generate_moodboard_bg", no_moodboard)

    app = FastAPI()
    app.include_router(curate.router)
    app.dependency_overrides[get_current_user_id] = lambda: str(uuid.uuid4())

    async def post():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            return await client.post(
                "/v1/curate",
                json={"mood": "지침", "weather": "비", "energy": 2, "location": {"lat": 0, "lng": 0}},
            )

    return asyncio.run(post())


def test_api_returns_200_with_empty_section(monkeypatch, saved):
    response = _post_curate(monkeypatch, _nodes(failing={"food_agent"}))

    assert response.status_code == 200
    body = response.json()
    assert body["food_picks"] == []
    assert body["music_picks"] and body["place_picks"] and body["style_picks"]


def test_api_returns_502_when_all_agents_fail(monkeypatch, saved):
    response = _post_curate(monkeypatch, _nodes(failing=set(PICKS)))

    assert response.status_code == 502
    assert saved == []
