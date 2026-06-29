"""장소 에이전트 — W3에서 Google Maps MCP 연동 예정."""

from app.agents.state import DailyState


async def place_agent_node(state: DailyState) -> dict:
    # TODO: Google Maps MCP + OpenAI Agents SDK
    return {"place_picks": [], "llm_calls": ["place_agent:stub"]}
