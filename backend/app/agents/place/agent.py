"""장소 에이전트 — Google Maps MCP로 무드에 맞는 장소를 큐레이션한다."""

import json
import logging
import os
import re
import sys

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from langsmith import traceable

from app.agents.state import DailyState, PlacePick

logger = logging.getLogger("place_agent")

_MCP_CMD = [sys.executable, "-m", "app.agents.maps.mcp_server"]

_SYSTEM_PROMPT = """\
당신은 사용자의 오늘 감정·날씨·에너지에 꼭 맞는 장소를 큐레이션하는 전문가입니다.

## 지침
- search_places 도구로 주변 장소를 검색하세요.
- 카페, 공원, 서점, 미술관, 산책로 등 다양한 유형을 고려하세요.
- 날씨가 나쁘면 실내 공간 위주로 추천하세요.
- 정확히 3곳을 추천하세요.
- 취향 컨텍스트(rag_context)가 있으면 적극 반영하세요.

## 출력 형식 (JSON 배열만, 다른 텍스트 없이)
[
  {
    "name": "장소명",
    "address": "주소",
    "maps_url": "https://maps.google.com/...",
    "reason": "이 장소를 추천하는 이유 (1~2문장)"
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


def _parse_picks(raw: str) -> list[PlacePick]:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        items = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not match:
            logger.warning("place_agent: JSON 파싱 실패, 원문=%r", raw[:500])
            return []
        try:
            items = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("place_agent: JSON 파싱 실패, 원문=%r", raw[:500])
            return []
    if not isinstance(items, list):
        return []
    return [
        PlacePick(
            name=item.get("name", ""),
            address=item.get("address", ""),
            maps_url=item.get("maps_url", ""),
            reason=item.get("reason", ""),
        )
        for item in items
        if isinstance(item, dict)
    ]


@traceable(name="place_agent")
async def place_agent_node(state: DailyState) -> dict:
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
            name="place-curator",
            instructions=_SYSTEM_PROMPT,
            mcp_servers=[mcp_server],
            model="gpt-4o-mini",
        )
        result = await Runner.run(agent, input=_user_message(state))

    return {
        "place_picks": _parse_picks(result.final_output),
        "llm_calls": [f"place_agent:{result.final_output[:80]}"],
    }
