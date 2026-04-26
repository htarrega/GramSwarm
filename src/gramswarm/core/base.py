from typing import Protocol, List, TypedDict
from .models import TraceResponse


class Message(TypedDict):
    role: str
    content: str


class LLMProvider(Protocol):

    def generate_trace(
        self,
        system_prompt: str,
        messages: List[Message],
        is_final: bool = False,
    ) -> TraceResponse:
        ...
