"""Tests for guard_node - adoption-domain in/out-of-scope classification."""
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage

from agent.nodes import guard_node


@patch("agent.nodes.llm")
def test_guard_in_scope_adoption_query(mock_llm):
    """Adoption query → in_scope."""
    mock_llm.invoke.return_value = AIMessage(content="in_scope")
    state = {"messages": [HumanMessage(content="I'm looking for a young white dog")]}
    result = guard_node(state)
    assert result["messages"][0].content == "in_scope"


@patch("agent.nodes.llm")
def test_guard_off_topic_general_question(mock_llm):
    """General-knowledge question → off_topic."""
    mock_llm.invoke.return_value = AIMessage(content="off_topic")
    state = {"messages": [HumanMessage(content="What's the weather in Tel Aviv?")]}
    result = guard_node(state)
    assert result["messages"][0].content == "off_topic"


@patch("agent.nodes.llm")
def test_guard_unknown_response_defaults_to_off_topic(mock_llm):
    """LLM returning anything other than the two valid labels → off_topic."""
    mock_llm.invoke.return_value = AIMessage(content="maybe")
    state = {"messages": [HumanMessage(content="anything")]}
    result = guard_node(state)
    assert result["messages"][0].content == "off_topic"
