"""스타일 에이전트 — LLM으로 코디 3개 생성 + 네이버 쇼핑 MCP로 상품 이미지·링크 보강."""

import json
import logging
import os
import re
import sys

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from langsmith import traceable

from app.agents.state import DailyState, StylePick

logger = logging.getLogger("style_agent")

_MCP_CMD = [sys.executable, "-m", "app.agents.style.mcp_server"]

_SYSTEM_PROMPT = """\
당신은 사용자의 오늘 감정·날씨·에너지에 꼭 맞는 코디를 큐레이션하는 패션 스타일리스트입니다.

## 지침
- 날씨와 에너지를 최우선으로 고려해 실용적인 코디를 제안하세요.
  예) 비 + 에너지 낮음 → 방수 소재 오버핏 + 슬리퍼, 에너지 높음 → 활동적인 스포티 룩
- 코디마다 search_product 도구로 핵심 아이템(예: "오버사이즈 후드 베이지")을 검색해
  첫 번째 결과의 image_url과 product_url을 출력에 포함하세요.
- 반드시 정확히 3가지 코디를 추천하세요.
- 취향 컨텍스트(rag_context)가 있으면 적극 반영하세요.

## 출력 형식 (JSON 배열만, 다른 텍스트 없이)
[
  {
    "description": "아이템 조합 + 색상 (예: 딥 그레이 오버사이즈 후드티 + 브라운 조거 팬츠 + 베이지 슬리퍼)",
    "reason": "코디 설명 및 추천 이유 (무드·날씨·에너지와 어떻게 어울리는지, 1~2문장)",
    "image_url": "search_product 결과의 image_url (없으면 빈 문자열)",
    "product_url": "search_product 결과의 product_url (없으면 빈 문자열)"
  }
]
"""


def _user_message(state: DailyState) -> str:
    return (
        f"무드: {state['mood']}\n"
        f"날씨: {state['weather']}\n"
        f"에너지: {state['energy']}/5\n"
        f"취향 컨텍스트:\n{state.get('rag_context') or '없음'}"
    )


def _parse_picks(raw: str) -> list[StylePick]:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        items = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not match:
            logger.warning("style_agent: JSON 파싱 실패, 원문=%r", raw[:500])
            return []
        try:
            items = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("style_agent: JSON 파싱 실패, 원문=%r", raw[:500])
            return []
    if not isinstance(items, list):
        return []
    return [
        StylePick(
            description=item.get("description", ""),
            reason=item.get("reason", ""),
            image_url=item.get("image_url", ""),
            product_url=item.get("product_url", ""),
        )
        for item in items
        if isinstance(item, dict)
    ]


@traceable(name="style_agent")
async def style_agent_node(state: DailyState) -> dict:
    async with MCPServerStdio(
        params={
            "command": _MCP_CMD[0],
            "args": _MCP_CMD[1:],
            "env": {
                **os.environ,
                "NAVER_CLIENT_ID": os.environ.get("NAVER_CLIENT_ID", ""),
                "NAVER_CLIENT_SECRET": os.environ.get("NAVER_CLIENT_SECRET", ""),
            },
        },
        cache_tools_list=True,
        client_session_timeout_seconds=30,
    ) as mcp_server:
        agent = Agent(
            name="style-curator",
            instructions=_SYSTEM_PROMPT,
            mcp_servers=[mcp_server],
            model="gpt-4o-mini",
        )
        result = await Runner.run(agent, input=_user_message(state))

    return {
        "style_picks": _parse_picks(result.final_output),
        "llm_calls": [f"style_agent:{result.final_output[:80]}"],
    }
