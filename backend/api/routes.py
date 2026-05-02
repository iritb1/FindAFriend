from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage

from agent.graph import adoption_agent
from api.models import ChatRequest, ChatResponse, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
def health() -> HealthResponse:
    """
    Liveness check endpoint.

    Returns:
        HealthResponse: {"status": "ok"} if the service is running.
    """
    return HealthResponse(status="ok")


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest) -> ChatResponse:
    """
    Handles adoption-seeker questions.

    Passes the message through the LangGraph agent
    (guard -> extract -> match -> answer) and returns the agent's response.
    Each request is tracked by a thread_id for multi-turn refinement support.

    Args:
        request (ChatRequest): The user's message (1-1000 characters).

    Returns:
        ChatResponse: The agent's answer.

    Raises:
        HTTPException (500): If the agent fails to process the request.
    """
    try:
        result = adoption_agent.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config={"configurable": {"thread_id": request.thread_id}},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    return ChatResponse(
        answer=result["messages"][-1].content,
        thread_id=str(request.thread_id),
    )
