"""맛집 에이전트 — Google Places MCP로 무드에 맞는 맛집을 큐레이션한다."""

import json
import logging
import os
import re
import sys

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from langsmith import traceable

from app.agents.state import DailyState, FoodPick

logger = logging.getLogger("food_agent")

_MCP_CMD = [sys.executable, "-m", "app.agents.maps.mcp_server"]

_SYSTEM_PROMPT = """\
당신은 사용자의 오늘 감정·날씨·에너지에 꼭 맞는 맛집을 큐레이션하는 전문가입니다.

## 지침
- search_restaurants 도구로 주변 맛집을 검색하세요.
- 무드와 에너지 수준에 맞는 음식 유형을 선택하세요.
  예) 에너지 낮음 + 우울 → 따뜻한 국물 요리, 에너지 높음 → 활기찬 분위기의 식당
- 다양한 음식 종류를 섞어 정확히 3곳을 추천하세요.
- 취향 컨텍스트(rag_context)가 있으면 적극 반영하세요.

## 출력 형식 (JSON 배열만, 다른 텍스트 없이)
[
  {
    "name": "식당명",
    "cuisine": "음식 종류 (예: 한식, 파스타, 라멘)",
    "address": "주소",
    "maps_url": "https://maps.google.com/...",
    "reason": "이 식당을 추천하는 이유 (1~2문장)"
  }
]
"""


def _user_message(state: DailyState) -> str:
    loc = state["location"]
    return (
        f"무드: {state['mood']}\n"
        f"날씨: {state['weather']}\n"
        f"에너지: {state['energy']}/5\n"
        f"위치: 위도 {loc['lat']}, 경도 {loc['lng']}\n"
        f"취향 컨텍스트:\n{state.get('rag_context') or '없음'}"
    )


def _parse_picks(raw: str) -> list[FoodPick]:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        items = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not match:
            logger.warning("food_agent: JSON 파싱 실패, 원문=%r", raw[:500])
            return []
        try:
            items = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("food_agent: JSON 파싱 실패, 원문=%r", raw[:500])
            return []
    if not isinstance(items, list):
        return []
    return [
        FoodPick(
            name=item.get("name", ""),
            cuisine=item.get("cuisine", ""),
            address=item.get("address", ""),
            maps_url=item.get("maps_url", ""),
            reason=item.get("reason", ""),
        )
        for item in items
        if isinstance(item, dict)
    ]


@traceable(name="food_agent")
async def food_agent_node(state: DailyState) -> dict:
    async with MCPServerStdio(
        params={
            "command": _MCP_CMD[0],
            "args": _MCP_CMD[1:],
            "env": {**os.environ, "GOOGLE_MAPS_API_KEY": os.environ.get("GOOGLE_MAPS_API_KEY", "")},
        },
        cache_tools_list=True,
        client_session_timeout_seconds=30,
    ) as mcp_server:
        agent = Agent(
            name="food-curator",
            instructions=_SYSTEM_PROMPT,
            mcp_servers=[mcp_server],
            model="gpt-4o-mini",
        )
        result = await Runner.run(agent, input=_user_message(state))

    return {
        "food_picks": _parse_picks(result.final_output),
        "llm_calls": [f"food_agent:{result.final_output[:80]}"],
    }
