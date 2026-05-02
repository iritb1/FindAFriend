import os
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from utils.singleton import Singleton

load_dotenv()


@Singleton
class LLMClient:
    """Shared LLM client - created once on first use, reused across all requests."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")

        self.client = ChatOpenAI(
            api_key=api_key,
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
        )

    def invoke(self, messages):
        return self.client.invoke(messages)

    def structured(self, schema: type) -> Any:
        """Returns a runnable that invokes with structured output bound to schema."""
        return self.client.with_structured_output(schema)