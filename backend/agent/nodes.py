"""LangGraph node implementations for the adoption agent.

Each node is a pure function that reads the current AgentState and returns a
partial state update. The graph in `agent/graph.py` wires them together.
"""
from langchain_core.messages import AIMessage

from agent.llm_client import LLMClient
from agent.matcher import find_matches
from utils.models import AdoptionQuery
from agent.prompts import ANSWER_PROMPT, EXTRACT_PROMPT, GUARD_PROMPT, REFUSAL_MESSAGE
from agent.state import AgentState


llm = LLMClient()


def _last_user_text(state: AgentState) -> str:
    """Returns the content of the most recent message in the conversation.

    Args:
        state: Current LangGraph state.

    Returns:
        The raw text of message.
    """
    return state["messages"][-1].content


def _last_human_text(state: AgentState) -> str:
    """Returns the most recent human message, ignoring AI/tool messages.

    Used by guard/extract so they always read the user's actual request even
    if intermediate AI messages have been appended to state.

    Args:
        state: Current LangGraph state.

    Returns:
        The text of the latest human message, or the last message overall
        if no human message exists.
    """
    user_messages = [
        message.content
        for message in state["messages"]
        if getattr(message, "type", None) == "human"
    ]

    return user_messages[-1] if user_messages else _last_user_text(state)


def guard_node(state: AgentState) -> dict:
    """Classifies the user's message as adoption-related or off-topic.

    Sends the latest human message plus GUARD_PROMPT to the LLM and expects
    "in_scope" or "off_topic" back. Any other reply is treated as off_topic.

    Args:
        state: Current LangGraph state.

    Returns:
        State update with a single AIMessage whose content is "in_scope" or
        "off_topic".
    """
    user_text = _last_human_text(state)

    response = llm.invoke(
        [
            ("system", GUARD_PROMPT),
            ("user", user_text),
        ]
    )

    result = response.content.strip().lower()

    if result not in {"in_scope", "off_topic"}:
        result = "off_topic"

    return {
        "messages": [AIMessage(content=result)]
    }


def extract_node(state: AgentState) -> dict:
    """Parses the user's free-text request into a structured AdoptionQuery.

    Uses the LLM with structured-output enforcement so the result is a valid
    Pydantic AdoptionQuery (animal_type, gender, age_preference, breed, etc.).

    Args:
        state: Current LangGraph state.

    Returns:
        State update containing the parsed query (AdoptionQuery).
    """
    user_text = _last_human_text(state)

    structured_llm = llm.structured(AdoptionQuery)

    query = structured_llm.invoke(
        [
            ("system", EXTRACT_PROMPT),
            ("user", user_text),
        ]
    )

    return {
        "query": query
    }


def match_node(state: AgentState) -> dict:
    """Runs the matcher against the loaded animal catalog.

    Args:
        state: Current LangGraph state.

    Returns:
        State update with full_matches and
        partial_matches. Empty lists if no
        query is present.
    """
    query = state.get("query")

    if query is None:
        return {
            "full_matches": [],
            "partial_matches": [],
        }

    full_matches, partial_matches = find_matches(query=query, limit=5)

    return {
        "full_matches": full_matches,
        "partial_matches": partial_matches,
    }


def answer_node(state: AgentState) -> dict:
    """Composes the user-facing reply from the match results.

    If no partial matches were found, returns a fixed fallback message.
    Otherwise, sends the query and the matches to the LLM with ANSWER_PROMPT
    and lets it write a friendly recommendation (up to 5 animals).

    Args:
        state: Current LangGraph state.

    Returns:
        State update with a single AIMessage containing the final reply.
    """
    query = state.get("query")
    full_matches = state.get("full_matches", [])
    partial_matches = state.get("partial_matches", [])

    if not partial_matches:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I couldn't find a good match in the current adoption list. "
                        "Try widening the search, for example: younger/older, any gender, "
                        "or fewer personality requirements."
                    )
                )
            ]
        }

    matches_payload = [
        {
            "score": match.score,
            "reasons": match.reasons,
            "missing_or_uncertain": match.missing_or_uncertain,
            "animal": match.animal.model_dump(),
        }
        for match in partial_matches
    ]

    response = llm.invoke(
        [
            ("system", ANSWER_PROMPT),
            (
                "user",
                f"""
User query:
{query.model_dump() if query else None}

Full matches:
{[animal.model_dump() for animal in full_matches]}

Best partial matches:
{matches_payload}

Write a helpful answer. Recommend up to 5 animals.
""",
            ),
        ]
    )

    return {
        "messages": [AIMessage(content=response.content)]
    }


def refusal_node(state: AgentState) -> dict:
    """Emits the canned off-topic refusal message.

    Reached when the guard classifies the user message as off_topic.

    Args:
        state: Current LangGraph state.

    Returns:
        State update with a single AIMessage containing REFUSAL_MESSAGE.
    """
    return {
        "messages": [
            AIMessage(content=REFUSAL_MESSAGE)
        ]
    }