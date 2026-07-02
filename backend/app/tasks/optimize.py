"""DSPy 프롬프트 최적화 Celery 태스크."""

import asyncio
import logging

from app.core.celery import celery_app

logger = logging.getLogger("tasks.optimize")

AGENT_TYPES = ["music", "place", "food", "style"]


@celery_app.task(
    name="tasks.optimize_prompts",
    bind=True,
    max_retries=2,
    soft_time_limit=600,  # 10분
    time_limit=660,
)
def optimize_prompts(self, agent: str | None = None):
    """DSPy BootstrapFewShot으로 에이전트 프롬프트 최적화.

    Args:
        agent: 특정 에이전트만 최적화. None이면 전체 실행.
    """
    from app.services.dspy_optimizer import (
        optimize_agent,  # 지연 임포트 (celery worker 메모리 절약)
    )

    targets = [agent] if agent else AGENT_TYPES

    async def run():
        results = {}
        for target in targets:
            try:
                ok = await optimize_agent(target)
                results[target] = "optimized" if ok else "skipped"
            except Exception as exc:
                logger.exception("optimize_prompts: %s 실패", target)
                results[target] = f"error: {exc}"
        return results

    results = asyncio.run(run())
    logger.info("optimize_prompts 완료: %s", results)
    return results
