"""오케스트레이터 그래프 — LangGraph Supervisor 패턴.

흐름:
  START → rag → supervisor ──Send()──> music
                                  └──> place   → moodboard → save → END
                                  └──> food
                                  └──> style
"""

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.agents.food.agent import food_agent_node
from app.agents.moodboard.agent import moodboard_agent_node
from app.agents.music.agent import music_agent_node
from app.agents.place.agent import place_agent_node
from app.agents.state import DailyState
from app.agents.style.agent import style_agent_node

# ── stub 노드들 ────────────────────────────────────────────────────


async def rag_node(state: DailyState) -> dict:
    """pgvector 취향 메모리 조회 — W5에서 실구현."""
    return {"rag_context": ""}


async def supervisor_node(state: DailyState) -> dict:
    """패스스루 노드 — 실제 fan-out은 route_to_agents 라우팅 함수가 담당한다."""
    return {}


def route_to_agents(state: DailyState) -> list[Send]:
    """4개 에이전트를 병렬로 발사한다 (conditional edge 라우팅).

    노드 반환값은 상태 업데이트(dict)여야 하므로, Send 리스트는
    노드가 아니라 conditional edge의 라우팅 함수에서 반환해야 한다.
    """
    return [
        Send("music_agent", state),
        Send("place_agent", state),
        Send("food_agent", state),
        Send("style_agent", state),
    ]


async def moodboard_node(state: DailyState) -> dict:
    return await moodboard_agent_node(state)


async def save_node(state: DailyState) -> dict:
    """DailyState를 PostgreSQL에 저장 + pgvector 임베딩 — W5에서 실구현."""
    return {}


# ── 그래프 조립 ────────────────────────────────────────────────────

_builder = StateGraph(DailyState)

_builder.add_node("rag", rag_node)
_builder.add_node("supervisor", supervisor_node)
_builder.add_node("music_agent", music_agent_node)
_builder.add_node("place_agent", place_agent_node)
_builder.add_node("food_agent", food_agent_node)
_builder.add_node("style_agent", style_agent_node)
_builder.add_node("moodboard", moodboard_node)
_builder.add_node("save", save_node)

# 직선 흐름
_builder.add_edge(START, "rag")
_builder.add_edge("rag", "supervisor")

# supervisor → 4개 병렬 (Send로 처리되므로 conditional_edges 사용)
_builder.add_conditional_edges(
    "supervisor",
    route_to_agents,
    ["music_agent", "place_agent", "food_agent", "style_agent"],
)

# 병렬 에이전트 4개 → 모두 moodboard로 수렴 (LangGraph가 자동 fan-in)
_builder.add_edge("music_agent", "moodboard")
_builder.add_edge("place_agent", "moodboard")
_builder.add_edge("food_agent", "moodboard")
_builder.add_edge("style_agent", "moodboard")

_builder.add_edge("moodboard", "save")
_builder.add_edge("save", END)

orchestrator = _builder.compile(
    # W5: checkpointer=AsyncPostgresSaver 로 교체 → interrupt 활성화
)
