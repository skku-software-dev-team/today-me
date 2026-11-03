"""피드백 개선 루프 테스트: 트리거 주기, 큐 설정, 데이터 부족, 검증, 실패 시 복귀."""

import asyncio
import json
import uuid

import dspy
import pytest
from dspy.utils import DummyLM

from app.agents import prompt_loader
from app.core.celery import celery_app
from app.models.report import DailyReport
from app.routers import feedback
from app.services import dspy_optimizer
from app.tasks import optimize

USER_ID = uuid.uuid4()


class CountingRedis:
    def __init__(self):
        self.value = 0

    async def incr(self, key):
        self.value += 1
        return self.value


def _example(i: int, disliked: list[str] | None = None) -> dspy.Example:
    return dspy.Example(
        mood=f"기분{i}",
        weather="비",
        energy="2",
        recommendations=json.dumps([{"title": f"곡{i}"}], ensure_ascii=False),
        disliked=json.dumps(disliked or [], ensure_ascii=False),
    ).with_inputs("mood", "weather", "energy")


@pytest.fixture
def optimizer(monkeypatch):
    """학습 데이터와 응답을 지정하면 optimize_agent를 실행하고 저장 내용을 돌려준다."""

    def run(examples, responses):
        saved = []

        async def fake_trainset(agent, user_id):
            return examples

        async def fake_save(agent, user_id, instruction, demos, score):
            saved.append({"agent": agent, "user_id": user_id, "demos": demos, "score": score})

        monkeypatch.setattr(dspy_optimizer, "_build_trainset", fake_trainset)
        monkeypatch.setattr(dspy_optimizer, "_save_optimized", fake_save)
        monkeypatch.setattr(dspy_optimizer.dspy, "LM", lambda *a, **k: DummyLM(responses))
        ok = asyncio.run(dspy_optimizer.optimize_agent("music", USER_ID))
        return ok, saved

    return run


def test_worker_consumes_the_queue_tasks_are_sent_to():
    celery_app.loader.import_default_modules()

    assert "tasks.optimize_prompts" in celery_app.tasks
    route = celery_app.amqp.router.route({}, "tasks.optimize_prompts")
    assert route["queue"].name == "default"


def test_triggers_exactly_on_every_tenth_feedback(monkeypatch):
    calls = []
    monkeypatch.setattr(
        optimize.optimize_prompts, "delay", lambda **kwargs: calls.append(kwargs["user_id"])
    )
    redis = CountingRedis()

    async def send(times):
        for _ in range(times):
            await feedback._count_and_trigger(redis, "user")

    asyncio.run(send(9))
    assert calls == []
    asyncio.run(send(1))
    assert calls == ["user"]
    asyncio.run(send(10))
    assert calls == ["user", "user"]


def test_broker_failure_does_not_break_feedback():
    class BrokenRedis:
        async def incr(self, key):
            raise ConnectionError("redis down")

    asyncio.run(feedback._count_and_trigger(BrokenRedis(), "user"))


def test_skips_when_examples_are_too_few(optimizer):
    ok, saved = optimizer([_example(1), _example(2)], [])

    assert ok is False
    assert saved == []


def test_saves_recent_liked_examples_as_demos(optimizer):
    examples = [_example(i) for i in range(7)]
    responses = [{"recommendations": '[{"title": "새 곡"}]'}] * 2

    ok, saved = optimizer(examples, responses)

    assert ok is True
    assert saved[0]["user_id"] == USER_ID
    # 앞의 1개는 검증용(7 // 5), 나머지 중 최신 4개가 예시가 된다.
    assert [d["mood"] for d in saved[0]["demos"]] == ["기분1", "기분2", "기분3", "기분4"]


def test_keeps_existing_prompt_when_candidate_scores_lower(optimizer):
    examples = [_example(0, disliked=["싫은 곡"]), _example(1), _example(2)]
    responses = [
        {"recommendations": '[{"title": "새 곡"}]'},  # 기본 프롬프트: 통과
        {"recommendations": '[{"title": "싫은 곡"}]'},  # 후보: 싫어한 추천을 다시 냄
    ]

    ok, saved = optimizer(examples, responses)

    assert ok is False
    assert saved == []


@pytest.mark.parametrize(
    ("text", "disliked", "expected"),
    [
        ('[{"title": "곡"}]', [], 1.0),
        ('[{"title": "싫은 곡"}]', ["싫은 곡"], 0.0),
        ("[]", [], 0.0),
        ("JSON 아님", [], 0.0),
    ],
)
def test_metric(text, disliked, expected):
    pred = dspy.Prediction(recommendations=text)

    assert dspy_optimizer._recommendation_metric(_example(0, disliked), pred) == expected


def test_split_feedback_separates_scores_and_ignores_invalid_keys():
    report = DailyReport(
        music_picks=[{"title": "좋은 곡"}, {"title": "싫은 곡"}],
        place_picks=[{"name": "장소"}],
        feedback={
            "music-0": {"score": 1},
            "music-1": {"score": -1},
            "music-99": {"score": 1},
            "music--1": {"score": 1},
            "place-0": {"score": 1},
        },
    )

    liked, disliked = dspy_optimizer._split_feedback(report, "music")

    assert liked == [{"title": "좋은 곡"}]
    assert disliked == [{"title": "싫은 곡"}]


def _session_returning(value):
    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, model, key):
            if isinstance(value, Exception):
                raise value
            return value

    return Session


def test_prompt_includes_likes_and_dislikes(monkeypatch):
    opt = type(
        "Opt",
        (),
        {
            "few_shot_demos": [
                {
                    "mood": "지침",
                    "weather": "비",
                    "energy": "2",
                    "recommendations": '[{"title": "좋은 곡"}]',
                    "disliked": '["싫은 곡"]',
                }
            ]
        },
    )
    monkeypatch.setattr(prompt_loader, "AsyncSessionLocal", _session_returning(opt))

    prompt = asyncio.run(prompt_loader.load_system_prompt("music", "BASE", str(USER_ID)))

    assert prompt.startswith("BASE")
    assert "좋은 곡" in prompt
    assert "싫어한 추천: 싫은 곡" in prompt


@pytest.mark.parametrize("stored", [None, RuntimeError("db down")])
def test_prompt_falls_back_to_base(monkeypatch, stored):
    monkeypatch.setattr(prompt_loader, "AsyncSessionLocal", _session_returning(stored))

    prompt = asyncio.run(prompt_loader.load_system_prompt("music", "BASE", str(USER_ID)))

    assert prompt == "BASE"
