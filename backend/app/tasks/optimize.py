"""DSPy 프롬프트 개선 Celery 태스크."""

import asyncio
import logging
import uuid

from app.core.celery import celery_app
from app.core.database import engine

logger = logging.getLogger("tasks.optimize")

AGENT_TYPES = ["music", "place", "food", "style"]


@celery_app.task(
    name="tasks.optimize_prompts",
    soft_time_limit=600,  # 10분
    time_limit=660,
)
def optimize_prompts(user_id: str):
    """사용자의 네 에이전트 프롬프트를 개선한다. 한 에이전트가 실패해도 나머지는 계속한다."""
    from app.services.dspy_optimizer import optimize_agent  # 지연 임포트 (dspy 로딩 비용)

    uid = uuid.UUID(user_id)

    async def run():
        results = {}
        try:
            for agent in AGENT_TYPES:
                try:
                    ok = await optimize_agent(agent, uid)
                    results[agent] = "optimized" if ok else "skipped"
                except Exception as exc:
                    logger.exception("optimize_prompts: %s 실패, 기존 프롬프트 유지", agent)
                    results[agent] = f"error: {exc}"
        finally:
            # asyncio.run은 매번 새 루프를 만들므로 풀의 연결을 다음 태스크로 넘기지 않는다.
            await engine.dispose()
        return results

    results = asyncio.run(run())
    logger.info("optimize_prompts 완료: %s", results)
    return results
