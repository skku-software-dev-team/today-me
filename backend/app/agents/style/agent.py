"""스타일 에이전트 — W3에서 날씨·무드 기반 추론 구현 예정."""

from app.agents.state import DailyState


async def style_agent_node(state: DailyState) -> dict:
    # TODO: Weather API MCP + OpenAI Agents SDK
    return {"style_picks": [], "llm_calls": ["style_agent:stub"]}
