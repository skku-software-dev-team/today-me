"""POST /v1/feedback의 소유권과 pick_index 검증 테스트.

DB와 임베딩 API는 가짜로 대체하고, 라우터와 apply_feedback의 판단만 검증한다.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.jwt import get_current_user_id
from app.core.redis import get_redis
from app.models.report import DailyReport
from app.routers import feedback
from app.services import memory

OWNER_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()
REPORT_ID = uuid.uuid4()


class FakeSession:
    def __init__(self, report: DailyReport):
        self.report = report

    async def get(self, model, key):
        return self.report if key == self.report.id else None

    async def commit(self):
        pass

    async def refresh(self, instance):
        pass


class FakeRedis:
    def __init__(self):
        self.count = 0

    async def incr(self, key):
        self.count += 1
        return self.count


def _report(feedback_data: dict | None = None) -> DailyReport:
    return DailyReport(
        id=REPORT_ID,
        user_id=OWNER_ID,
        mood="지침",
        weather="비",
        energy=2,
        music_picks=[{"title": "곡", "artist": "가수", "youtube_url": "https://example.com"}],
        place_picks=[],
        food_picks=[],
        style_picks=[],
        feedback=feedback_data if feedback_data is not None else {},
    )


@pytest.fixture
def api(monkeypatch):
    report = _report()
    embedded = []

    async def fake_upsert(db, target):
        embedded.append(target.id)

    monkeypatch.setattr(memory, "upsert_embedding", fake_upsert)

    app = FastAPI()
    app.include_router(feedback.router)

    async def fake_db():
        yield FakeSession(report)

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_redis] = FakeRedis

    def client_as(user_id: uuid.UUID) -> TestClient:
        app.dependency_overrides[get_current_user_id] = lambda: str(user_id)
        return TestClient(app)

    return client_as, report, embedded


def _body(**overrides) -> dict:
    return {
        "report_id": str(REPORT_ID),
        "agent": "music",
        "pick_index": 0,
        "score": 1,
        **overrides,
    }


def test_owner_can_save_feedback(api):
    client_as, report, embedded = api

    res = client_as(OWNER_ID).post("/v1/feedback", json=_body(comment="좋아요"))

    assert res.status_code == 200
    assert report.feedback == {"music-0": {"score": 1, "comment": "좋아요"}}
    assert embedded == [REPORT_ID]


def test_other_users_report_returns_404_and_is_unchanged(api):
    client_as, report, embedded = api

    res = client_as(OTHER_ID).post("/v1/feedback", json=_body())

    assert res.status_code == 404
    assert report.feedback == {}
    assert embedded == []


def test_missing_report_returns_same_404(api):
    client_as, report, _ = api

    missing = client_as(OWNER_ID).post("/v1/feedback", json=_body(report_id=str(uuid.uuid4())))
    forbidden = client_as(OTHER_ID).post("/v1/feedback", json=_body())

    # 응답으로 남의 리포트 존재 여부를 구분할 수 없어야 한다.
    assert missing.status_code == 404
    assert missing.json() == forbidden.json()


@pytest.mark.parametrize(
    ("agent", "pick_index"),
    [("music", 1), ("music", 99), ("music", -1), ("place", 0)],
)
def test_invalid_pick_index_returns_422_and_is_unchanged(api, agent, pick_index):
    client_as, report, embedded = api

    res = client_as(OWNER_ID).post("/v1/feedback", json=_body(agent=agent, pick_index=pick_index))

    assert res.status_code == 422
    assert report.feedback == {}
    assert embedded == []


def test_serialize_skips_existing_out_of_range_feedback():
    report = _report(
        {
            "music-0": {"score": 1, "comment": None},
            "music-99": {"score": 1, "comment": None},
            "music--1": {"score": -1, "comment": None},
        }
    )

    text = memory._serialize(report)

    assert "좋아요: 곡" in text
    assert "music-99" not in text
    assert "싫어요" not in text
