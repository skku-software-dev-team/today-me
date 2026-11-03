"""피드백 기반 사용자별 추천 프롬프트 개선 (DSPy).

흐름:
  1. 해당 사용자의 최근 리포트에서 에이전트별 좋아요/싫어요를 수집한다.
  2. 좋아요가 있는 리포트를 DSPy 예시로 바꾸고, 최근 예시로 few-shot 후보를 만든다.
  3. 가장 최근 예시로 기본 프롬프트와 후보를 LLM으로 비교한다.
  4. 후보가 기본보다 나쁘지 않을 때만 저장한다. 실패하거나 나쁘면 기존 프롬프트를 유지한다.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Literal

import dspy
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.optimized_prompt import OptimizedPrompt
from app.models.report import DailyReport
from app.services.memory import pick_label, picks_for

logger = logging.getLogger("dspy_optimizer")

AgentType = Literal["music", "place", "food", "style"]

MIN_EXAMPLES = 3  # 이보다 적으면 개선을 건너뛴다
RECENT_REPORTS = 30  # 오래된 취향이 계속 남지 않도록 최근 기록만 쓴다
MAX_DEMOS = 4


class RecommendationSignature(dspy.Signature):
    """사용자의 오늘 감정·날씨·에너지를 바탕으로 최적의 추천을 JSON 배열로 생성합니다."""

    mood: str = dspy.InputField(desc="사용자의 현재 기분")
    weather: str = dspy.InputField(desc="현재 날씨")
    energy: str = dspy.InputField(desc="에너지 레벨 (1~5)")
    recommendations: str = dspy.OutputField(desc="JSON 배열 형태의 추천 결과")


class Recommender(dspy.Module):
    def __init__(self):
        self.generate = dspy.Predict(RecommendationSignature)

    def forward(self, mood: str, weather: str, energy: str):
        return self.generate(mood=mood, weather=weather, energy=energy)


def _recommendation_metric(example: dspy.Example, pred, trace=None) -> float:
    """유효한 JSON 배열이고 사용자가 싫어한 추천을 다시 내지 않으면 1점."""
    try:
        items = json.loads(pred.recommendations)
    except (TypeError, ValueError):
        return 0.0
    if not isinstance(items, list) or not items:
        return 0.0
    disliked = json.loads(example.disliked)
    return 0.0 if any(label in pred.recommendations for label in disliked) else 1.0


def _split_feedback(report: DailyReport, agent: AgentType) -> tuple[list[dict], list[dict]]:
    """리포트의 피드백을 (좋아요한 추천, 싫어요한 추천)으로 나눈다."""
    picks = picks_for(report, agent)
    liked, disliked = [], []
    for key, fb in (report.feedback or {}).items():
        prefix, _, idx = key.rpartition("-")
        if prefix != agent or not idx.isdigit() or int(idx) >= len(picks):
            continue
        (liked if fb.get("score", 0) > 0 else disliked).append(picks[int(idx)])
    return liked, disliked


async def _build_trainset(agent: AgentType, user_id: uuid.UUID) -> list[dspy.Example]:
    """해당 사용자의 예시를 최신순으로 반환한다. 다른 사용자의 데이터는 쓰지 않는다."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DailyReport)
            .where(DailyReport.user_id == user_id, DailyReport.feedback != {})
            .order_by(DailyReport.created_at.desc())
            .limit(RECENT_REPORTS)
        )
        reports = result.scalars().all()

    examples = []
    for report in reports:
        liked, disliked = _split_feedback(report, agent)
        if not liked:
            continue
        examples.append(
            dspy.Example(
                mood=report.mood,
                weather=report.weather or "",
                energy=str(report.energy),
                recommendations=json.dumps(liked, ensure_ascii=False),
                disliked=json.dumps([pick_label(p) for p in disliked], ensure_ascii=False),
            ).with_inputs("mood", "weather", "energy")
        )
    return examples


async def _save_optimized(
    agent: AgentType,
    user_id: uuid.UUID,
    instruction: str,
    demos: list[dict],
    avg_score: float,
) -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.get(OptimizedPrompt, (user_id, agent))
        if existing:
            existing.instruction = instruction
            existing.few_shot_demos = demos
            existing.avg_score = avg_score
            existing.updated_at = datetime.now(timezone.utc)
        else:
            db.add(
                OptimizedPrompt(
                    user_id=user_id,
                    agent_type=agent,
                    instruction=instruction,
                    few_shot_demos=demos,
                    avg_score=avg_score,
                )
            )
        await db.commit()


def _evaluate(program: dspy.Module, examples: list[dspy.Example]) -> float:
    scores = [
        _recommendation_metric(
            example,
            program(mood=example.mood, weather=example.weather, energy=example.energy),
        )
        for example in examples
    ]
    return sum(scores) / len(scores)


async def optimize_agent(agent: AgentType, user_id: uuid.UUID) -> bool:
    """사용자의 피드백으로 에이전트 프롬프트를 개선한다.

    Returns:
        새 프롬프트를 저장하면 True, 데이터 부족이나 검증 미달로 건너뛰면 False.
    """
    examples = await _build_trainset(agent, user_id)
    if len(examples) < MIN_EXAMPLES:
        logger.info(
            "dspy_optimizer: %s 예시 부족 (%d < %d), 건너뜀", agent, len(examples), MIN_EXAMPLES
        )
        return False

    split = max(1, len(examples) // 5)
    valset, trainset = examples[:split], examples[split:]

    # sample=False: 최신순 trainset의 앞쪽, 즉 최근 취향을 예시로 고른다.
    compiled = dspy.LabeledFewShot(k=MAX_DEMOS).compile(
        Recommender(), trainset=trainset, sample=False
    )

    lm = dspy.LM("openai/gpt-4o-mini", api_key=os.environ.get("OPENAI_API_KEY", ""), cache=False)
    # dspy.configure는 비동기 작업마다 다시 호출할 수 없어 context를 쓴다.
    with dspy.context(lm=lm):
        base_score = _evaluate(Recommender(), valset)
        score = _evaluate(compiled, valset)

    if score < base_score:
        logger.info(
            "dspy_optimizer: %s 후보 점수 미달 (%.2f < %.2f), 기존 프롬프트 유지",
            agent,
            score,
            base_score,
        )
        return False

    demos = [
        {
            "mood": demo.get("mood", ""),
            "weather": demo.get("weather", ""),
            "energy": demo.get("energy", ""),
            "recommendations": demo.get("recommendations", "[]"),
            "disliked": demo.get("disliked", "[]"),
        }
        for demo in compiled.generate.demos
    ]
    await _save_optimized(agent, user_id, compiled.generate.signature.instructions, demos, score)
    logger.info("dspy_optimizer: %s 개선 완료, demos=%d, score=%.2f", agent, len(demos), score)
    return True
