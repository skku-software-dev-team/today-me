"""맛집 에이전트 — W3에서 Places API MCP 연동 예정."""

from app.agents.state import DailyState


async def food_agent_node(state: DailyState) -> dict:
    # TODO: Places/리뷰 MCP + OpenAI Agents SDK
    return {"food_picks": [], "llm_calls": ["food_agent:stub"]}
