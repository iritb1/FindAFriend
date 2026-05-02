"""LangGraph wiring for the adoption agent.

Flow:
    START → guard → (in_scope) → extract → match → answer → END
                  → (off_topic) → refusal → END

Multi-turn conversations are supported via `MemorySaver` keyed on `thread_id`
(passed by the API route in `config={"configurable": {"thread_id": ...}}`).
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes import answer_node, extract_node, guard_node, match_node, refusal_node
from agent.state import AgentState
from utils.logger import Logger

logger = Logger("graph")

NODES = [
    ("guard_node", guard_node),
    ("extract_node", extract_node),
    ("match_node", match_node),
    ("answer_node", answer_node),
    ("refusal_node", refusal_node),
]

EDGES = [
    ("extract_node", "match_node"),
    ("match_node", "answer_node"),
    ("answer_node", END),
    ("refusal_node", END),
]


def _route_after_guard(state: AgentState) -> str:
    """Conditional edge: routes the graph based on the guard node's output.

    Args:
        state: Current LangGraph state. Reads `state["messages"][-1].content`
            which the guard node sets to "in_scope" or "off_topic".

    Returns:
        "in_scope" if the guard classified the user message as adoption-related,
        "off_topic" otherwise (which sends the graph to `refusal_node`).
    """
    last = state["messages"][-1].content.strip().lower()

    return "in_scope" if last == "in_scope" else "off_topic"


def build_graph():
    """Builds and compiles the adoption-agent LangGraph.

    Wiring:
      - START: guard_node
      - guard_node to extract_node (in_scope) | refusal_node (off_topic)
      - extract_node to match_node to answer_node to END
      - refusal_node to END

    Returns:
        A compiled StateGraph with `MemorySaver` so conversations persist
        across turns within the same `thread_id`.
    """
    graph = StateGraph(AgentState)

    for name, func in NODES:
        graph.add_node(name, func)

    graph.add_edge(START, "guard_node")

    graph.add_conditional_edges(
        "guard_node",
        _route_after_guard,
        {
            "in_scope": "extract_node",
            "off_topic": "refusal_node",
        },
    )

    for source, target in EDGES:
        graph.add_edge(source, target)

    compiled = graph.compile(checkpointer=MemorySaver())

    logger.info("Adoption agent graph compiled")

    return compiled

adoption_agent = build_graph()