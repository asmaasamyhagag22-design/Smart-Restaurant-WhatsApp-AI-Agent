"""The LangGraph state machine (docs §06.1).

    intent → plan → tools → reflect ──(needs_replan & hops<max)──▶ plan
                                   └──────────────────────────────▶ respond → END
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.agent.nodes.intent import intent_node
from app.agent.nodes.plan import plan_node
from app.agent.nodes.reflect import reflect_node
from app.agent.nodes.respond import respond_node
from app.agent.nodes.tools import tools_node
from app.agent.state import ConvState
from app.config import settings


def _route_after_reflect(state: ConvState) -> str:
    if state.needs_replan and state.hops < settings.max_hops:
        return "plan"
    return "respond"


def build_agent():
    g = StateGraph(ConvState)

    g.add_node("intent", intent_node)
    g.add_node("plan", plan_node)
    g.add_node("tools", tools_node)
    g.add_node("reflect", reflect_node)
    g.add_node("respond", respond_node)

    g.set_entry_point("intent")
    g.add_edge("intent", "plan")
    g.add_edge("plan", "tools")
    g.add_edge("tools", "reflect")
    g.add_conditional_edges(
        "reflect",
        _route_after_reflect,
        {"plan": "plan", "respond": "respond"},
    )
    g.add_edge("respond", END)

    return g.compile()


@lru_cache
def get_agent():
    """Compiled graph singleton."""
    return build_agent()
