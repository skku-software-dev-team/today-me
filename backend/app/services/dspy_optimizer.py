"""DSPy 기반 에이전트 프롬프트 최적화.

흐름:
  1. DB에서 해당 에이전트의 좋아요 피드백이 있는 DailyReport 수집
  2. (입력 컨텍스트, 좋아했던 추천) 쌍을 DSPy 훈련 예시로 변환
  3. BootstrapFewShot으로 instruction + few-shot demos 최적화
  4. 결과를 OptimizedPrompt 테이블에 upsert
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Literal

import dspy
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.optimized_prompt import OptimizedPrompt
from app.models.report import DailyReport, ReportEmbedding

logger = logging.getLogger("dspy_optimizer")

AgentType = Literal["music", "place", "food", "style"]

MIN_EXAMPLES = 3  # 최적화 실행 최소 훈련 예시 수


# ── DSPy 시그니처 ──────────────────────────────────────────────────


class RecommendationSignature(dspy.Signature):
    """사용자의 오늘 감정·날씨·에너지·취향 컨텍스트를 바탕으로 최적의 추천을 JSON 배열로 생성합니다."""

    mood: str = dspy.InputField(desc="사용자의 현재 기분")
    weather: str = dspy.InputField(desc="현재 날씨")
    energy: str = dspy.InputField(desc="에너지 레벨 (1~5)")
    rag_context: str = dspy.InputField(desc="과거 취향 컨텍스트 (없으면 빈 문자열)")
    recommendations: str = dspy.OutputField(desc="JSON 배열 형태의 추천 결과")


class Recommender(dspy.Module):
    def __init__(self):
        self.generate = dspy.Predict(RecommendationSignature)

    def forward(self, mood: str, weather: str, energy: str, rag_context: str):
        return self.generate(mood=mood, weather=weather, energy=energy, rag_context=rag_context)


# ── 메트릭 ────────────────────────────────────────────────────────


def _recommendation_metric(example: dspy.Example, pred, trace=None) -> float:
    try:
        items = json.loads(pred.recommendations)
        return 1.0 if isinstance(items, list) and len(items) > 0 else 0.0
    except Exception:
        return 0.0


# ── 훈련 데이터 수집 ──────────────────────────────────────────────


def _extract_liked_picks(report: DailyReport, agent: AgentType) -> list[dict]:
    picks_map: dict[str, list] = {
        "music": report.music_picks or [],
        "place": report.place_picks or [],
        "food": report.food_picks or [],
        "style": report.style_picks or [],
    }
    picks = picks_map[agent]
    liked = []
    for key, fb in (report.feedback or {}).items():
        if not key.startswith(f"{agent}-"):
            continue
        try:
            idx = int(key.split("-", 1)[1])
        except ValueError:
            continue
        if fb.get("score", 0) > 0 and idx < len(picks):
            liked.append(picks[idx])
    return liked


async def _build_trainset(agent: AgentType) -> list[dspy.Example]:
    async with AsyncSessionLocal() as db:
        # 피드백이 있는 리포트만 조회
        result = await db.execute(
            select(DailyReport, ReportEmbedding.embed_text)
            .join(
                ReportEmbedding,
                ReportEmbedding.report_id == DailyReport.id,
                isouter=True,
            )
            .where(DailyReport.feedback != {})
        )
        rows = result.all()

    examples = []
    for report, embed_text in rows:
        liked = _extract_liked_picks(report, agent)
        if not liked:
            continue
        examples.append(
            dspy.Example(
                mood=report.mood,
                weather=report.weather or "",
                energy=str(report.energy),
                rag_context=embed_text or "",
                recommendations=json.dumps(liked, ensure_ascii=False),
            ).with_inputs("mood", "weather", "energy", "rag_context")
        )
    return examples


# ── OptimizedPrompt upsert ────────────────────────────────────────


async def _save_optimized(
    agent: AgentType,
    instruction: str,
    demos: list[dict],
    avg_score: float,
) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.get(OptimizedPrompt, agent)
        now = datetime.now(timezone.utc)
        if existing:
            existing.instruction = instruction
            existing.few_shot_demos = demos
            existing.avg_score = avg_score
            existing.updated_at = now
        else:
            db.add(
                OptimizedPrompt(
                    agent_type=agent,
                    instruction=instruction,
                    few_shot_demos=demos,
                    avg_score=avg_score,
                    created_at=now,
                    updated_at=now,
                )
            )
        await db.commit()


async def load_optimized_prompt(agent: AgentType) -> OptimizedPrompt | None:
    """에이전트 실행 시 최적화 프롬프트 로드. 없으면 None."""
    async with AsyncSessionLocal() as db:
        return await db.get(OptimizedPrompt, agent)


# ── 메인 최적화 함수 ──────────────────────────────────────────────


async def optimize_agent(agent: AgentType) -> bool:
    """DSPy BootstrapFewShot으로 에이전트 프롬프트 최적화.

    Returns:
        True if optimization succeeded, False if skipped (not enough data).
    """
    examples = await _build_trainset(agent)
    if len(examples) < MIN_EXAMPLES:
        logger.info(
            "dspy_optimizer: %s 에이전트 훈련 예시 부족 (%d < %d), 최적화 건너뜀",
            agent,
            len(examples),
            MIN_EXAMPLES,
        )
        return False

    logger.info("dspy_optimizer: %s 에이전트 최적화 시작 (예시 %d개)", agent, len(examples))

    lm = dspy.LM(
        "openai/gpt-4o-mini",
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        cache=False,
    )
    dspy.configure(lm=lm)

    split = max(1, len(examples) // 5)
    trainset = examples[split:]
    valset = examples[:split]

    optimizer = dspy.BootstrapFewShot(
        metric=_recommendation_metric,
        max_bootstrapped_demos=3,
        max_labeled_demos=4,
    )

    compiled: Recommender = optimizer.compile(
        Recommender(),
        trainset=trainset,
        valset=valset if valset else None,
    )

    # 최적화된 instruction 및 demos 추출
    instruction: str = compiled.generate.extended_signature.instructions
    demos: list[dict] = [
        {
            "mood": d.get("mood", ""),
            "weather": d.get("weather", ""),
            "energy": d.get("energy", ""),
            "rag_context": d.get("rag_context", ""),
            "recommendations": d.get("recommendations", "[]"),
        }
        for d in (compiled.generate.demos or [])
        if d.get("recommendations")
    ]

    # 검증 세트 기준 평균 점수 계산
    scores = []
    for ex in valset or examples[:2]:
        pred = compiled(
            mood=ex.mood,
            weather=ex.weather,
            energy=ex.energy,
            rag_context=ex.rag_context,
        )
        scores.append(_recommendation_metric(ex, pred))
    avg_score = sum(scores) / len(scores) if scores else 0.0

    await _save_optimized(agent, instruction, demos, avg_score)
    logger.info(
        "dspy_optimizer: %s 최적화 완료 — demos=%d, avg_score=%.2f",
        agent,
        len(demos),
        avg_score,
    )
    return True
