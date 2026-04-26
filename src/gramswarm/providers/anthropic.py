from typing import List
from anthropic import Anthropic, RateLimitError, APIConnectionError, APITimeoutError
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_random_exponential
from ..core.base import LLMProvider, Message
from ..core.models import TraceResponse, ChunkTrace, RetentionTrace

_CHUNK_TOOL = {
    "name": "record_chunk_trace",
    "description": "Record structured reading metrics for this chunk",
    "input_schema": {
        "type": "object",
        "properties": {
            "prediction_next_beat": {
                "type": "string",
                "description": "What you expect to happen next",
            },
            "prediction_confidence": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
            },
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "active_expectations": {"type": "array", "items": {"type": "string"}},
            "confusion_points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "quote": {"type": "string"},
                        "why": {"type": "string"},
                    },
                    "required": ["quote", "why"],
                },
            },
            "salience_claim": {"type": "integer", "minimum": 1, "maximum": 5},
            "emotional_register": {
                "type": "object",
                "properties": {
                    "tone": {"type": "string"},
                    "intensity": {"type": "integer", "minimum": 1, "maximum": 5},
                },
                "required": ["tone", "intensity"],
            },
            "continue_pressure": {"type": "integer", "minimum": 1, "maximum": 5},
            "would_abandon": {"type": "boolean"},
            "abandon_reason": {
                "type": "string",
                "description": "Omit if would_abandon is false",
            },
            "voice_match_check": {"type": "integer", "minimum": 1, "maximum": 5},
            "voice_match_note": {
                "type": "string",
                "description": "One short note about voice fit, optional",
            },
        },
        "required": [
            "prediction_next_beat",
            "prediction_confidence",
            "open_questions",
            "active_expectations",
            "confusion_points",
            "salience_claim",
            "emotional_register",
            "continue_pressure",
            "would_abandon",
            "voice_match_check",
        ],
    },
}

_RETENTION_TOOL = {
    "name": "record_retention_trace",
    "description": "Record what stayed with you after finishing the chapter",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary_as_retained": {"type": "string"},
            "chapter_sentence_salience": {
                "type": "array",
                "items": {"type": "string"},
            },
            "expectations_carried_forward": {
                "type": "string"
            },
            "tension_self_report": {"type": "string"},
            "comparables": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "summary_as_retained",
            "chapter_sentence_salience",
            "expectations_carried_forward",
            "tension_self_report",
            "comparables",
        ],
    },
}


class AnthropicProvider(LLMProvider):

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(min=1, max=60),
        retry=lambda e: isinstance(e, (RateLimitError, APIConnectionError, APITimeoutError)),
    )
    def generate_trace(
        self,
        system_prompt: str,
        messages: List[Message],
        is_final: bool = False,
    ) -> TraceResponse:
        tool = _RETENTION_TOOL if is_final else _CHUNK_TOOL
        model_class = RetentionTrace if is_final else ChunkTrace

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"], "disable_parallel_tool_use": True},
        )

        if not response.content:
            raise ValueError("Empty response from API")

        narrative = "\n\n".join(
            block.text for block in response.content if block.type == "text"
        )
        tool_block = next(
            (block for block in response.content if block.type == "tool_use"), None
        )
        if tool_block is None:
            raise ValueError("No tool_use block in response")

        structured = model_class.model_validate(tool_block.input)

        return TraceResponse(
            content=narrative,
            structured_data=structured,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )
