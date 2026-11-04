"""에이전트별 취향 컨텍스트 구성과 RAG 실패 시 동작 테스트."""

import asyncio
import uuid
from datetime import datetime, timezone

from app.agents import graph
from app.models.report import DailyReport
from app.services import memory


def _report(day: int, feedback: dict, mood: str = "지침") -> DailyReport:
    return DailyReport(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        mood=mood,
        weather="비",
        energy=2,
        music_picks=[{"title": f"곡{day}"}, {"title": f"싫은곡{day}"}],
        place_picks=[{"name": f"장소{day}"}],
        food_picks=[{"name": f"식당{day}"}],
        style_picks=[{"description": f"코디{day}"}],
        feedback=feedback,
        created_at=datetime(2026, 10, day, tzinfo=timezone.utc),
    )


def test_each_agent_receives_only_its_own_feedback():
    report = _report(1, {"music-0": {"score": 1}, "place-0": {"score": -1}})

    contexts = memory.build_agent_contexts([(report, 0.1)])

    assert "좋아요: 곡1" in contexts["music"]
    assert "장소1" not in contexts["music"]
    assert "싫어요: 장소1" in contexts["place"]
    assert "곡1" not in contexts["place"]
    assert contexts["food"] == ""
    assert contexts["style"] == ""


def test_unrated_picks_are_excluded():
    report = _report(1, {"music-0": {"score": 1}})

    assert "싫은곡1" not in memory.build_agent_contexts([(report, 0.1)])["music"]


def test_distant_records_are_excluded():
    near = _report(1, {"music-0": {"score": 1}})
    far = _report(2, {"music-0": {"score": 1}})

    context = memory.build_agent_contexts(
        [(near, memory.RAG_MAX_DISTANCE), (far, memory.RAG_MAX_DISTANCE + 0.01)]
    )["music"]

    assert "곡1" in context
    assert "곡2" not in context


def test_selects_by_similarity_then_shows_newest_first():
    rows = [
        (_report(day, {"music-0": {"score": 1}}), 0.1 + day / 100)
        for day in (2, 6, 1, 5, 3, 4)  # 유사도 순. 마지막 day=4는 상위 5개 밖
    ]

    context = memory.build_agent_contexts(rows)["music"]

    assert "곡4" not in context
    dates = [line[1:11] for line in context.splitlines() if line.startswith("[")]
    assert dates == sorted(dates, reverse=True)
    assert len(dates) == memory.RAG_TOP_K


def test_agent_with_feedback_outside_top_records_still_gets_context():
    rows = [(_report(day, {"place-0": {"score": 1}}), 0.1) for day in range(1, 7)]
    rows.append((_report(7, {"music-0": {"score": 1}}), 0.5))

    assert "곡7" in memory.build_agent_contexts(rows)["music"]


def test_comment_is_included_and_truncated():
    report = _report(1, {"music-0": {"score": 1, "comment": "가" * 300}})

    context = memory.build_agent_contexts([(report, 0.1)])["music"]

    assert f"곡1 ({'가' * memory.MAX_COMMENT_CHARS})" in context
    assert "가" * (memory.MAX_COMMENT_CHARS + 1) not in context


def test_context_length_is_limited():
    long_mood = "기" * 500
    rows = [(_report(day, {"music-0": {"score": 1}}, mood=long_mood), 0.1) for day in range(1, 6)]

    context = memory.build_agent_contexts(rows)["music"]

    assert 0 < len(context) <= memory.MAX_CONTEXT_CHARS + 2 * (memory.RAG_TOP_K - 1)


def test_invalid_feedback_keys_are_ignored():
    report = _report(1, {"music-99": {"score": 1}, "music--1": {"score": 1}})

    assert memory.build_agent_contexts([(report, 0.1)])["music"] == ""


def test_rag_failure_continues_without_context(monkeypatch):
    async def broken(**kwargs):
        raise ConnectionError("embedding api down")

    monkeypatch.setattr(graph, "get_agent_contexts", broken)
    state = {"user_id": str(uuid.uuid4()), "mood": "지침", "energy": 2}

    assert asyncio.run(graph.rag_node(state)) == {"rag_contexts": {}}
