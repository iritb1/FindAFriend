"""Tests for extract_node - verifies AdoptionQuery is plumbed through correctly.

The LLM call itself is mocked; we verify (a) the right schema is requested
and (b) the LLM's structured output is placed into state.
"""
from unittest.mock import MagicMock, patch

from langchain_core.messages import HumanMessage

from utils.models import AdoptionQuery, AnimalType, Gender
from agent.nodes import extract_node


@patch("agent.nodes.llm")
def test_extract_returns_query_in_state(mock_llm):
    """Mocked structured output → state['query'] holds the AdoptionQuery."""
    structured = MagicMock()
    structured.invoke.return_value = AdoptionQuery(
        animal_type=AnimalType.dog,
        gender=Gender.female,
        breed="labrador",
        free_text="young white female lab",
    )
    mock_llm.structured.return_value = structured

    state = {"messages": [HumanMessage(content="young white female lab")]}
    result = extract_node(state)

    assert isinstance(result["query"], AdoptionQuery)
    assert result["query"].animal_type == AnimalType.dog
    assert result["query"].gender == Gender.female
    assert result["query"].breed == "labrador"


@patch("agent.nodes.llm")
def test_extract_requests_adoption_query_schema(mock_llm):
    """llm.structured is called with AdoptionQuery as the schema."""
    structured = MagicMock()
    structured.invoke.return_value = AdoptionQuery(free_text="anything")
    mock_llm.structured.return_value = structured

    extract_node({"messages": [HumanMessage(content="anything")]})

    mock_llm.structured.assert_called_once_with(AdoptionQuery)
