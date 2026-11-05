"""오케스트레이터 그래프 — LangGraph Supervisor 패턴.

흐름:
  START → rag → supervisor ──Send()──> music
                                  └──> place   → save → END
                                  └──> food
                                  └──> style
  (moodboard는 curate API에서 BackgroundTask로 별도 실행)

에이전트 하나가 실패하면 그 분야만 빈 결과로 두고, 모든 분야가 비면 저장하지 않고 실패시킨다.
"""

import logging
from functools import wraps

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.agents.food.agent import food_agent_node
from app.agents.music.agent import music_agent_node
from app.agents.place.agent import place_agent_node
from app.agents.state import DailyState
from app.agents.style.agent import style_agent_node
from app.services.memory import get_agent_contexts, save_report

logger = logging.getLogger("graph")

# 노드 이름 → (결과 키, 노드 함수)
AGENT_NODES = {
    "music_agent": ("music_picks", music_agent_node),
    "place_agent": ("place_picks", place_agent_node),
    "food_agent": ("food_picks", food_agent_node),
    "style_agent": ("style_picks", style_agent_node),
}

# ── 노드 구현 ──────────────────────────────────────────────────────


async def rag_node(state: DailyState) -> dict:
    """pgvector 취향 메모리를 조회해 에이전트별 컨텍스트를 주입한다.

    조회에 실패해도 개인화만 빠질 뿐 추천은 계속되어야 하므로 빈 컨텍스트로 진행한다.
    """
    try:
        contexts = await get_agent_contexts(
            user_id=state["user_id"],
            mood=state["mood"],
            weather=state.get("weather", ""),
            energy=state["energy"],
            district=state.get("location", {}).get("district"),
        )
    except Exception:
        logger.exception("RAG 조회 실패, 컨텍스트 없이 진행")
        contexts = {}
    return {"rag_contexts": contexts}


async def supervisor_node(state: DailyState) -> dict:
    """패스스루 노드 — 실제 fan-out은 route_to_agents 라우팅 함수가 담당한다."""
    return {}


def route_to_agents(state: DailyState) -> list[Send]:
    return [Send(name, state) for name in AGENT_NODES]


def _isolated(name: str, picks_key: str, node):
    """에이전트 하나의 실패로 다른 분야의 결과까지 잃지 않도록 그 분야만 빈 결과로 둔다."""

    @wraps(node)
    async def wrapper(state: DailyState) -> dict:
        try:
            return await node(state)
        except Exception:
            logger.exception("%s 실패, 해당 분야를 빈 결과로 진행", name)
            return {picks_key: [], "llm_calls": [f"{name}:failed"]}

    return wrapper


async def save_node(state: DailyState) -> dict:
    """DailyState를 PostgreSQL에 저장하고 pgvector 임베딩 생성."""
    # 빈 리포트는 사용자에게 쓸모가 없고 취향 검색 데이터만 오염시키므로 저장하지 않는다.
    if not any(state.get(picks_key) for picks_key, _ in AGENT_NODES.values()):
        raise RuntimeError("모든 에이전트가 추천을 만들지 못했습니다")
    report = await save_report(state)
    return {"report_id": str(report.id)}


# ── 그래프 조립 ────────────────────────────────────────────────────


def build_orchestrator(agent_nodes: dict = AGENT_NODES):
    builder = StateGraph(DailyState)

    builder.add_node("rag", rag_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("save", save_node)

    builder.add_edge(START, "rag")
    builder.add_edge("rag", "supervisor")
    builder.add_conditional_edges("supervisor", route_to_agents, list(agent_nodes))

    # 병렬 에이전트 4개 → save로 수렴 (fan-in)
    for name, (picks_key, node) in agent_nodes.items():
        builder.add_node(name, _isolated(name, picks_key, node))
        builder.add_edge(name, "save")

    builder.add_edge("save", END)
    return builder.compile()


orchestrator = build_orchestrator()
