"""Tests for the FastAPI endpoints. LLM and matcher are fully mocked."""
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from utils.models import Animal, AnimalType, Gender
from api.main import app

client = TestClient(app)

_BELLA = Animal.model_validate({
    "source": "test",
    "animal_type": AnimalType.dog,
    "name": "Bella",
    "gender": Gender.female,
    "breed": "Labrador",
    "color": "white",
    "age": "2 years",
    "profile_url": "https://example.com/bella",
    "raw_text": "Bella, female lab, 2 years",
})


def test_health_endpoint():
    """GET /health returns 200 with {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("agent.nodes.find_matches", return_value=([_BELLA], []))
@patch("agent.nodes.llm")
def test_chat_off_topic_returns_refusal(mock_llm, _mock_matches):
    """Off-topic request → polite refusal, no extract/match path runs."""
    mock_llm.invoke.return_value = AIMessage(content="off_topic")

    response = client.post("/chat", json={"message": "What is the weather?"})
    assert response.status_code == 200
    assert "adoption" in response.json()["answer"].lower()


def test_chat_rejects_empty_message():
    """Empty message → 422 (Pydantic min_length=1)."""
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_rejects_oversized_message():
    """Message over 1000 chars → 422 (Pydantic max_length=1000)."""
    response = client.post("/chat", json={"message": "x" * 1001})
    assert response.status_code == 422
