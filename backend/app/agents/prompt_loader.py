"""사용자별 개선 프롬프트 로더 — 에이전트 공통 유틸."""

import json
import logging
import uuid
from typing import Literal

from app.core.database import AsyncSessionLocal
from app.models.optimized_prompt import OptimizedPrompt

logger = logging.getLogger("prompt_loader")

AgentType = Literal["music", "place", "food", "style"]


async def load_system_prompt(agent: AgentType, base_prompt: str, user_id: str) -> str:
    """사용자의 개선 프롬프트가 있으면 few-shot 섹션을 base_prompt에 추가해 반환한다.

    개선 프롬프트가 없거나 오류가 나면 추천이 막히지 않도록 base_prompt를 그대로 반환한다.
    """
    try:
        async with AsyncSessionLocal() as db:
            opt = await db.get(OptimizedPrompt, (uuid.UUID(user_id), agent))
        if not opt or not opt.few_shot_demos:
            return base_prompt

        demo_lines = []
        for i, demo in enumerate(opt.few_shot_demos, 1):
            lines = [
                f"[예시 {i}]",
                f"무드: {demo.get('mood', '')}, 날씨: {demo.get('weather', '')}, "
                f"에너지: {demo.get('energy', '')}",
                f"좋아한 추천: {demo.get('recommendations', '[]')}",
            ]
            disliked = json.loads(demo.get("disliked", "[]"))
            if disliked:
                lines.append(f"싫어한 추천: {', '.join(disliked)}")
            demo_lines.append("\n".join(lines))

        return (
            base_prompt
            + "\n\n## 이 사용자의 과거 선호 (참고하되 그대로 복사하지 말고, 싫어한 추천은 피할 것)\n"
            + "\n\n".join(demo_lines)
        )

    except Exception:
        logger.warning(
            "prompt_loader: %s 개선 프롬프트 로드 실패, 기본값 사용", agent, exc_info=True
        )
        return base_prompt
