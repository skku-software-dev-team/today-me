"""최적화 프롬프트 로더 — 에이전트 공통 유틸."""

import json
import logging
from typing import Literal

logger = logging.getLogger("prompt_loader")

AgentType = Literal["music", "place", "food", "style"]


async def load_system_prompt(agent: AgentType, base_prompt: str) -> str:
    """DB에 최적화 프롬프트가 있으면 few-shot 섹션을 base_prompt에 추가해 반환.

    최적화 프롬프트가 없거나 오류 발생 시 base_prompt 그대로 반환.
    """
    try:
        from app.services.dspy_optimizer import load_optimized_prompt

        opt = await load_optimized_prompt(agent)
        if not opt or not opt.few_shot_demos:
            return base_prompt

        demo_lines = []
        for i, demo in enumerate(opt.few_shot_demos, 1):
            try:
                picks = json.loads(demo.get("recommendations", "[]"))
                picks_str = json.dumps(picks, ensure_ascii=False)
            except Exception:
                picks_str = demo.get("recommendations", "")
            demo_lines.append(
                f"[예시 {i}]\n"
                f"무드: {demo.get('mood', '')}, 날씨: {demo.get('weather', '')}, "
                f"에너지: {demo.get('energy', '')}\n"
                f"추천: {picks_str}"
            )

        few_shot_section = "\n\n## 과거 선호 예시 (참고하되 그대로 복사하지 말 것)\n" + "\n\n".join(
            demo_lines
        )
        return base_prompt + few_shot_section

    except Exception:
        logger.warning("prompt_loader: %s 최적화 프롬프트 로드 실패, 기본값 사용", agent)
        return base_prompt
