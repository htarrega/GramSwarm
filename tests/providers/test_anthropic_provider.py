"""Tests for AnthropicProvider.generate_trace tool-use parsing."""
import pytest
from unittest.mock import MagicMock, patch
from gramswarm.providers.anthropic import AnthropicProvider
from gramswarm.core.models import ChunkTrace, RetentionTrace, TraceResponse
from tests.conftest import VALID_CHUNK_TRACE_DATA, VALID_RETENTION_TRACE_DATA


def _provider():
    provider = AnthropicProvider.__new__(AnthropicProvider)
    provider.model = "claude-haiku-4-5-20251001"
    return provider


def _mock_response(tool_name: str, tool_input: dict, narrative: str = "Some narrative."):
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = narrative

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = tool_input

    response = MagicMock()
    response.content = [text_block, tool_block]
    response.usage = MagicMock(input_tokens=100, output_tokens=200)
    return response


class TestGenerateTrace:
    def test_returns_chunk_trace(self):
        provider = _provider()
        provider.client = MagicMock()
        provider.client.messages.create.return_value = _mock_response(
            "record_chunk_trace", VALID_CHUNK_TRACE_DATA
        )
        result = provider.generate_trace("sys", [{"role": "user", "content": "chunk"}])
        assert isinstance(result, TraceResponse)
        assert isinstance(result.structured_data, ChunkTrace)
        assert result.structured_data.continue_pressure == 5

    def test_returns_retention_trace(self):
        provider = _provider()
        provider.client = MagicMock()
        provider.client.messages.create.return_value = _mock_response(
            "record_retention_trace", VALID_RETENTION_TRACE_DATA
        )
        result = provider.generate_trace(
            "sys", [{"role": "user", "content": "done"}], is_final=True
        )
        assert isinstance(result.structured_data, RetentionTrace)
        assert result.structured_data.summary_as_retained == "The hero discovered the secret room"

    def test_narrative_extracted_from_text_blocks(self):
        provider = _provider()
        provider.client = MagicMock()
        provider.client.messages.create.return_value = _mock_response(
            "record_chunk_trace", VALID_CHUNK_TRACE_DATA, narrative="My reaction here."
        )
        result = provider.generate_trace("sys", [{"role": "user", "content": "chunk"}])
        assert result.content == "My reaction here."

    def test_raises_when_no_tool_block(self):
        provider = _provider()
        provider.client = MagicMock()
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "just text"
        mock_resp = MagicMock()
        mock_resp.content = [text_block]
        mock_resp.usage = MagicMock(input_tokens=10, output_tokens=10)
        provider.client.messages.create.return_value = mock_resp
        with pytest.raises(ValueError, match="No tool_use block"):
            provider.generate_trace("sys", [{"role": "user", "content": "chunk"}])

    def test_raises_on_empty_response(self):
        provider = _provider()
        provider.client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = []
        provider.client.messages.create.return_value = mock_resp
        with pytest.raises(ValueError, match="Empty response"):
            provider.generate_trace("sys", [{"role": "user", "content": "chunk"}])

    def test_usage_captured(self):
        provider = _provider()
        provider.client = MagicMock()
        provider.client.messages.create.return_value = _mock_response(
            "record_chunk_trace", VALID_CHUNK_TRACE_DATA
        )
        result = provider.generate_trace("sys", [{"role": "user", "content": "chunk"}])
        assert result.usage["input_tokens"] == 100
        assert result.usage["output_tokens"] == 200

    def test_forces_correct_tool_for_chunk(self):
        provider = _provider()
        provider.client = MagicMock()
        provider.client.messages.create.return_value = _mock_response(
            "record_chunk_trace", VALID_CHUNK_TRACE_DATA
        )
        provider.generate_trace("sys", [{"role": "user", "content": "chunk"}])
        call_kwargs = provider.client.messages.create.call_args.kwargs
        assert call_kwargs["tool_choice"]["name"] == "record_chunk_trace"

    def test_forces_correct_tool_for_retention(self):
        provider = _provider()
        provider.client = MagicMock()
        provider.client.messages.create.return_value = _mock_response(
            "record_retention_trace", VALID_RETENTION_TRACE_DATA
        )
        provider.generate_trace("sys", [{"role": "user", "content": "done"}], is_final=True)
        call_kwargs = provider.client.messages.create.call_args.kwargs
        assert call_kwargs["tool_choice"]["name"] == "record_retention_trace"
