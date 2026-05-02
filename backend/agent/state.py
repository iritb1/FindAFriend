from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from utils.models import AdoptionQuery, Animal, PartialMatch


class AgentState(TypedDict, total=False):
    """State shared across LangGraph nodes."""

    messages: Annotated[list[BaseMessage], add_messages]
    query: AdoptionQuery | None
    full_matches: list[Animal]
    partial_matches: list[PartialMatch]