from uuid import uuid4

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        examples=["I'm looking for a young friendly female dog"],
        description="User message about adopting an animal (1-1000 characters).",
    )
    thread_id: str = Field(
        default_factory=uuid4,
        description="Send back a previous thread_id to continue a conversation. "
        "Omit to start a new one.",
    )


class ChatResponse(BaseModel):
    answer: str
    thread_id: str = Field(description="Use this to continue the conversation.")


class HealthResponse(BaseModel):
    status: str
