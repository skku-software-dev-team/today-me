"""음악 에이전트 노드.

OpenAI Agents SDK + YouTube MCP로 음악을 큐레이션하고
LangGraph DailyState 업데이트를 반환한다.
"""

import json
import logging
import os
import re
import sys

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from langsmith import traceable

from app.agents.state import DailyState, MusicPick

logger = logging.getLogger("music_agent")

_MCP_CMD = [sys.executable, "-m", "app.agents.music.mcp_server"]

_SYSTEM_PROMPT = """\
당신은 사용자의 오늘 감정·날씨·에너지에 꼭 맞는 음악을 큐레이션하는 전문가입니다.

## 지침
- search_music 도구로 YouTube에서 실제 영상을 검색하세요.
- 장르·분위기·언어를 다양하게 섞어 정확히 3곡을 추천하세요.
- 취향 컨텍스트(rag_context)가 있으면 적극 반영하세요.

## 출력 형식 (JSON 배열만, 다른 텍스트 없이)
[
  {"title": "곡명", "artist": "아티스트/채널명", "youtube_url": "https://..."},
  ...
]
"""


def _user_message(state: DailyState) -> str:
    return (
        f"무드: {state['mood']}\n"
        f"날씨: {state['weather']}\n"
        f"에너지: {state['energy']}/5\n"
        f"취향 컨텍스트:\n{state.get('rag_context') or '없음'}"
    )


def _parse_picks(raw: str) -> list[MusicPick]:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        items = json.loads(cleaned)
    except json.JSONDecodeError:
        # 모델이 JSON 앞뒤로 설명 텍스트를 붙인 경우: 첫 '[' ~ 마지막 ']' 추출
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not match:
            logger.warning("music_agent: JSON 파싱 실패, 원문=%r", raw[:500])
            return []
        try:
            items = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("music_agent: JSON 파싱 실패, 원문=%r", raw[:500])
            return []
    if not isinstance(items, list):
        return []
    return [
        MusicPick(
            title=item.get("title", ""),
            artist=item.get("artist", ""),
            youtube_url=item.get("youtube_url", ""),
        )
        for item in items
        if isinstance(item, dict)
    ]


@traceable(name="music_agent")
async def music_agent_node(state: DailyState) -> dict:
    async with MCPServerStdio(
        params={
            "command": _MCP_CMD[0],
            "args": _MCP_CMD[1:],
            # MCP stdio는 기본적으로 부모 env를 상속하지 않으므로 명시 전달
            "env": {**os.environ, "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY", "")},
        },
        cache_tools_list=True,
    ) as mcp_server:
        agent = Agent(
            name="music-curator",
            instructions=_SYSTEM_PROMPT,
            mcp_servers=[mcp_server],
            model="gpt-4o-mini",
        )
        result = await Runner.run(agent, input=_user_message(state))

    return {
        "music_picks": _parse_picks(result.final_output),
        "llm_calls": [f"music_agent:{result.final_output[:80]}"],
    }
