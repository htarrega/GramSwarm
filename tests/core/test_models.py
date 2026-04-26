import pytest
from pydantic import ValidationError
from gramswarm.core.models import (
    ChunkTrace,
    RetentionTrace,
    TraceResponse,
    ConfusionPoint,
    EmotionalRegister,
)
from tests.conftest import VALID_CHUNK_TRACE_DATA, VALID_RETENTION_TRACE_DATA


class TestScore1to5:
    def test_boundary_min_valid(self):
        data = {**VALID_CHUNK_TRACE_DATA, "prediction_confidence": 1}
        ChunkTrace.model_validate(data)

    def test_boundary_max_valid(self):
        data = {**VALID_CHUNK_TRACE_DATA, "prediction_confidence": 5}
        ChunkTrace.model_validate(data)

    def test_below_min_raises(self):
        data = {**VALID_CHUNK_TRACE_DATA, "prediction_confidence": 0}
        with pytest.raises(ValidationError):
            ChunkTrace.model_validate(data)

    def test_above_max_raises(self):
        data = {**VALID_CHUNK_TRACE_DATA, "prediction_confidence": 6}
        with pytest.raises(ValidationError):
            ChunkTrace.model_validate(data)


class TestChunkTrace:
    def test_valid_creation(self):
        trace = ChunkTrace.model_validate(VALID_CHUNK_TRACE_DATA)
        assert trace.prediction_next_beat == "The hero will open the door"
        assert trace.prediction_confidence == 4
        assert trace.continue_pressure == 5
        assert trace.would_abandon is False

    def test_defaults_for_optional_lists(self):
        data = {**VALID_CHUNK_TRACE_DATA}
        data.pop("open_questions", None)
        data.pop("active_expectations", None)
        data.pop("confusion_points", None)
        trace = ChunkTrace.model_validate(data)
        assert trace.open_questions == []
        assert trace.active_expectations == []
        assert trace.confusion_points == []

    def test_optional_fields_none_by_default(self):
        trace = ChunkTrace.model_validate(VALID_CHUNK_TRACE_DATA)
        assert trace.abandon_reason is None
        assert trace.voice_match_note is None

    def test_frozen_prevents_mutation(self):
        trace = ChunkTrace.model_validate(VALID_CHUNK_TRACE_DATA)
        with pytest.raises(Exception):
            trace.continue_pressure = 1  # type: ignore[misc]

    def test_missing_required_field_raises(self):
        data = {k: v for k, v in VALID_CHUNK_TRACE_DATA.items() if k != "prediction_next_beat"}
        with pytest.raises(ValidationError):
            ChunkTrace.model_validate(data)

    def test_confusion_point_embedded(self):
        data = {
            **VALID_CHUNK_TRACE_DATA,
            "confusion_points": [{"quote": "The sky was red", "why": "No prior mention"}],
        }
        trace = ChunkTrace.model_validate(data)
        assert isinstance(trace.confusion_points[0], ConfusionPoint)
        assert trace.confusion_points[0].quote == "The sky was red"

    def test_emotional_register_embedded(self):
        trace = ChunkTrace.model_validate(VALID_CHUNK_TRACE_DATA)
        assert isinstance(trace.emotional_register, EmotionalRegister)
        assert trace.emotional_register.tone == "tense"
        assert trace.emotional_register.intensity == 4


class TestRetentionTrace:
    def test_valid_creation(self):
        trace = RetentionTrace.model_validate(VALID_RETENTION_TRACE_DATA)
        assert trace.summary_as_retained == "The hero discovered the secret room"
        assert len(trace.comparables) == 1

    def test_frozen_prevents_mutation(self):
        trace = RetentionTrace.model_validate(VALID_RETENTION_TRACE_DATA)
        with pytest.raises(Exception):
            trace.summary_as_retained = "changed"  # type: ignore[misc]

    def test_defaults_for_list_fields(self):
        data = {
            "summary_as_retained": "A summary",
            "tension_self_report": "mild",
        }
        trace = RetentionTrace.model_validate(data)
        assert trace.chapter_sentence_salience == []
        assert trace.comparables == []

    def test_missing_required_field_raises(self):
        data = {k: v for k, v in VALID_RETENTION_TRACE_DATA.items() if k != "summary_as_retained"}
        with pytest.raises(ValidationError):
            RetentionTrace.model_validate(data)


class TestTraceResponse:
    def test_valid_creation(self, valid_chunk_trace):
        response = TraceResponse(
            content="some markdown",
            structured_data=valid_chunk_trace,
            usage={"input_tokens": 10, "output_tokens": 20},
        )
        assert response.content == "some markdown"
        assert response.usage["input_tokens"] == 10

    def test_usage_defaults_to_empty_dict(self, valid_chunk_trace):
        response = TraceResponse(content="text", structured_data=valid_chunk_trace)
        assert response.usage == {}

    def test_accepts_retention_trace(self, valid_retention_trace):
        response = TraceResponse(content="text", structured_data=valid_retention_trace)
        assert isinstance(response.structured_data, RetentionTrace)
