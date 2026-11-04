import logging
import uuid
from datetime import datetime, timezone

import openai
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.report import DailyReport, ReportEmbedding

logger = logging.getLogger("memory")

EMBEDDING_MODEL = "text-embedding-3-small"

AGENT_TYPES = ("music", "place", "food", "style")
RAG_CANDIDATES = 20  # 에이전트마다 평가 기록을 고를 수 있도록 넉넉히 조회한다
RAG_TOP_K = 5  # 에이전트별 최대 기록 수
RAG_MAX_DISTANCE = 0.7  # 코사인 거리 상한. 초기값이며 실제 데이터로 조정이 필요하다
MAX_CONTEXT_CHARS = 1500  # 에이전트별 컨텍스트 길이 상한
MAX_COMMENT_CHARS = 100


def picks_for(report: DailyReport, agent: str) -> list[dict]:
    picks_map = {
        "music": report.music_picks,
        "place": report.place_picks,
        "food": report.food_picks,
        "style": report.style_picks,
    }
    return picks_map.get(agent) or []


def pick_label(pick: dict) -> str:
    return pick.get("title") or pick.get("name") or pick.get("description", "")


def rated_picks(report: DailyReport, agent: str) -> list[tuple[dict, dict]]:
    """해당 에이전트에서 평가된 (추천, 피드백) 쌍을 반환한다. 잘못된 키는 건너뛴다."""
    picks = picks_for(report, agent)
    rated = []
    for key, fb in (report.feedback or {}).items():
        prefix, _, idx = key.rpartition("-")
        if prefix == agent and idx.isdigit() and int(idx) < len(picks):
            rated.append((picks[int(idx)], fb))
    return rated


def _serialize(report: DailyReport) -> str:
    """DailyReport → 임베딩용 텍스트 직렬화."""
    music = ", ".join(f"{p['title']} - {p['artist']}" for p in (report.music_picks or []))
    places = ", ".join(p["name"] for p in (report.place_picks or []))
    foods = ", ".join(p["name"] for p in (report.food_picks or []))
    style = report.style_picks[0]["description"] if report.style_picks else ""

    liked, disliked = [], []
    for key, fb in (report.feedback or {}).items():
        agent, idx = key.rsplit("-", 1)
        picks = picks_for(report, agent)
        # 검증 도입 전에 저장된 잘못된 키가 있어도 임베딩 갱신이 막히지 않게 건너뛴다.
        if int(idx) >= len(picks):
            continue
        (liked if fb["score"] > 0 else disliked).append(pick_label(picks[int(idx)]))

    lines = [
        f"기분: {report.mood}",
        f"날씨: {report.weather or '알 수 없음'}",
        f"에너지: {report.energy}/5",
        f"위치: {report.location_district or '알 수 없음'}",
        f"추천 음악: {music}",
        f"추천 장소: {places}",
        f"추천 맛집: {foods}",
        f"추천 스타일: {style}",
    ]
    if liked:
        lines.append(f"좋아요: {', '.join(liked)}")
    if disliked:
        lines.append(f"싫어요: {', '.join(disliked)}")

    return "\n".join(lines)


def _serialize_input(mood: str, weather: str, energy: int, district: str | None) -> str:
    """현재 입력 상태만 직렬화 (RAG 쿼리용)."""
    return "\n".join([
        f"기분: {mood}",
        f"날씨: {weather}",
        f"에너지: {energy}/5",
        f"위치: {district or '알 수 없음'}",
    ])


async def _embed(text: str) -> list[float]:
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return response.data[0].embedding


async def upsert_embedding(db: AsyncSession, report: DailyReport) -> None:
    """리포트 생성 또는 피드백 수신 후 임베딩 저장/갱신."""
    text = _serialize(report)
    vector = await _embed(text)

    existing = await db.get(ReportEmbedding, report.id)
    if existing:
        existing.embedding = vector
        existing.embed_text = text
        existing.updated_at = datetime.now(timezone.utc)
    else:
        db.add(ReportEmbedding(
            report_id=report.id,
            user_id=report.user_id,
            embedding=vector,
            embed_text=text,
        ))
    await db.commit()


async def save_report(state: dict) -> DailyReport:
    """DailyState 딕셔너리를 DB에 저장하고 임베딩까지 처리한다.

    LangGraph 노드에서 직접 호출 (FastAPI DI 없이 세션 직접 생성).
    """
    async with AsyncSessionLocal() as db:
        report = DailyReport(
            id=uuid.UUID(state["report_id"]),
            user_id=uuid.UUID(state["user_id"]),
            mood=state["mood"],
            weather=state.get("weather"),
            energy=state["energy"],
            location_district=state.get("location", {}).get("district"),
            music_picks=state.get("music_picks", []),
            place_picks=state.get("place_picks", []),
            food_picks=state.get("food_picks", []),
            style_picks=state.get("style_picks", []),
            moodboard_url=state.get("moodboard_url"),
            feedback={},
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        await upsert_embedding(db, report)
        return report


def _pick_with_comment(pick: dict, fb: dict) -> str:
    comment = (fb.get("comment") or "")[:MAX_COMMENT_CHARS]
    return f"{pick_label(pick)} ({comment})" if comment else pick_label(pick)


def _format_record(report: DailyReport, rated: list[tuple[dict, dict]]) -> str:
    lines = [
        f"[{report.created_at:%Y-%m-%d}] 기분: {report.mood}, "
        f"날씨: {report.weather or '알 수 없음'}, 에너지: {report.energy}/5"
    ]
    liked = [_pick_with_comment(pick, fb) for pick, fb in rated if fb.get("score", 0) > 0]
    disliked = [_pick_with_comment(pick, fb) for pick, fb in rated if fb.get("score", 0) < 0]
    if liked:
        lines.append(f"좋아요: {', '.join(liked)}")
    if disliked:
        lines.append(f"싫어요: {', '.join(disliked)}")
    return "\n".join(lines)


def _agent_context(reports: list[DailyReport], agent: str) -> str:
    """유사도 순 리포트에서 이 에이전트가 평가받은 기록만 골라 최신순 컨텍스트로 만든다."""
    selected = []
    used_chars = 0
    for report in reports:
        rated = rated_picks(report, agent)
        if not rated:
            continue
        record = _format_record(report, rated)
        if used_chars + len(record) > MAX_CONTEXT_CHARS:
            break
        selected.append((report.created_at, record))
        used_chars += len(record)
        if len(selected) == RAG_TOP_K:
            break

    selected.sort(key=lambda item: item[0], reverse=True)
    return "\n\n".join(record for _, record in selected)


def build_agent_contexts(rows: list[tuple[DailyReport, float]]) -> dict[str, str]:
    """(리포트, 코사인 거리) 목록을 에이전트별 컨텍스트로 나눈다. 관련 낮은 기록은 제외한다."""
    relevant = [report for report, distance in rows if distance <= RAG_MAX_DISTANCE]
    return {agent: _agent_context(relevant, agent) for agent in AGENT_TYPES}


async def get_agent_contexts(
    user_id: str,
    mood: str,
    weather: str,
    energy: int,
    district: str | None,
) -> dict[str, str]:
    """현재 입력과 유사한 이 사용자의 과거 평가를 찾아 에이전트별 컨텍스트로 반환한다."""
    query_vector = await _embed(_serialize_input(mood, weather, energy, district))
    distance = ReportEmbedding.embedding.cosine_distance(query_vector)

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(DailyReport, distance)
                .join(ReportEmbedding, ReportEmbedding.report_id == DailyReport.id)
                .where(ReportEmbedding.user_id == uuid.UUID(user_id))
                .order_by(distance)
                .limit(RAG_CANDIDATES)
            )
        ).all()

    contexts = build_agent_contexts([(report, dist) for report, dist in rows])
    logger.info(
        "RAG 컨텍스트: 후보 %d건, 길이 %s", len(rows), {a: len(c) for a, c in contexts.items()}
    )
    return contexts


async def apply_feedback(
    db: AsyncSession,
    report_id: uuid.UUID,
    user_id: uuid.UUID,
    agent: str,
    pick_index: int,
    score: int,
    comment: str | None,
) -> bool:
    """요청자 소유의 리포트와 실제 존재하는 추천인지 확인한 뒤 피드백을 저장하고 임베딩을 갱신한다.

    Returns:
        이 추천에 처음 남긴 피드백이면 True. 평가 변경이나 코멘트 추가는 False.
    """
    report = await db.get(DailyReport, report_id)
    # 남의 리포트도 '없음'과 같은 404로 응답해 존재 여부를 드러내지 않는다.
    if not report or report.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if pick_index >= len(picks_for(report, agent)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="pick_index out of range",
        )

    key = f"{agent}-{pick_index}"
    feedback = dict(report.feedback or {})
    is_new = key not in feedback
    feedback[key] = {"score": score, "comment": comment}
    report.feedback = feedback
    report.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(report)

    # 피드백은 이미 저장됐다. 임베딩 API 장애로 사용자 요청까지 실패시키지 않는다.
    try:
        await upsert_embedding(db, report)
    except Exception:
        logger.exception("임베딩 갱신 실패 report_id=%s", report.id)

    return is_new
