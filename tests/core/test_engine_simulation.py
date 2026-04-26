import pytest
from pathlib import Path
from unittest.mock import MagicMock
from gramswarm.core.engine import SimulationEngine
from gramswarm.core.models import TraceResponse, ChunkTrace, RetentionTrace
from gramswarm.core.reader import ReaderProfile
from gramswarm.services.io import RunManager
from tests.conftest import VALID_CHUNK_TRACE_DATA, VALID_RETENTION_TRACE_DATA


def _make_chunk_response() -> TraceResponse:
    trace = ChunkTrace.model_validate(VALID_CHUNK_TRACE_DATA)
    return TraceResponse(content="chunk md", structured_data=trace)


def _make_retention_response() -> TraceResponse:
    trace = RetentionTrace.model_validate(VALID_RETENTION_TRACE_DATA)
    return TraceResponse(content="retention md", structured_data=trace)


class FakeProvider:
    """Satisfies the LLMProvider protocol without hitting any API."""

    def __init__(self, responses=None):
        self._responses = list(responses or [])

    def generate_trace(self, system_prompt, messages, **kwargs):
        if self._responses:
            return self._responses.pop(0)
        return _make_chunk_response()


def _make_engine(provider, tmp_path, chunk_size=500):
    run_manager = RunManager(base_dir=str(tmp_path))
    return SimulationEngine(provider, run_manager, chunk_size=chunk_size), run_manager


def _make_reader():
    return ReaderProfile(name="alice", cluster="Fantasy", content="profile", path=Path("p.md"))


class TestChunkText:
    def _engine(self, chunk_size=500):
        e = SimulationEngine.__new__(SimulationEngine)
        e.chunk_size = chunk_size
        return e

    def test_single_paragraph_stays_intact(self):
        """Paragraph-preserving: a para that exceeds chunk_size is NOT split."""
        e = self._engine(chunk_size=500)
        text = " ".join(["word"] * 1000)  # one paragraph, 1000 words
        chunks = e._chunk_text(text)
        assert len(chunks) == 1

    def test_splits_across_paragraph_boundaries(self):
        """Two large paragraphs → each goes into its own chunk."""
        e = self._engine(chunk_size=500)
        para = " ".join(["word"] * 600)
        text = para + "\n\n" + para
        chunks = e._chunk_text(text)
        assert len(chunks) == 2

    def test_accumulates_small_paragraphs(self):
        """Multiple small paragraphs are batched until they exceed chunk_size."""
        e = self._engine(chunk_size=500)
        para = " ".join(["word"] * 200)  # 200 words each
        text = "\n\n".join([para] * 4)   # 4 paragraphs = 800 words total
        chunks = e._chunk_text(text)
        # First two fit in chunk 1 (400 words), last two in chunk 2 (400 words)
        assert len(chunks) == 2

    def test_empty_text_returns_one_empty_chunk(self):
        """Splitting empty string still produces one (empty) chunk."""
        e = self._engine(chunk_size=500)
        chunks = e._chunk_text("")
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_single_word(self):
        e = self._engine(chunk_size=500)
        chunks = e._chunk_text("hello")
        assert len(chunks) == 1
        assert chunks[0] == "hello"

    def test_respects_chunk_size_boundary(self):
        """Para that would push total over chunk_size triggers a flush first.

        para_a (200) fits → chunk 1.
        para_b (200): 200+200=400 > 300 → flush para_a, start chunk 2 with para_b.
        para_c (100): 200+100=300, NOT strictly > 300 → joins para_b in chunk 2.
        Result: 2 chunks.
        """
        e = self._engine(chunk_size=300)
        para_a = " ".join(["word"] * 200)
        para_b = " ".join(["word"] * 200)
        para_c = " ".join(["word"] * 100)
        text = f"{para_a}\n\n{para_b}\n\n{para_c}"
        chunks = e._chunk_text(text)
        assert len(chunks) == 2
        assert len(chunks[0].split()) == 200  # only para_a
        assert len(chunks[1].split()) == 300  # para_b + para_c


class TestSimulateReader:
    def test_calls_provider_per_chunk_plus_final(self, tmp_path):
        call_log = []

        class TrackingProvider:
            def generate_trace(self, system_prompt, messages, **kwargs):
                call_log.append(len(messages))
                return _make_chunk_response()

        run_manager = RunManager(base_dir=str(tmp_path))
        engine = SimulationEngine(TrackingProvider(), run_manager, chunk_size=500)

        engine.simulate_reader(_make_reader(), ["chunk1", "chunk2"])

        # 2 chunks + 1 final = 3 calls
        assert len(call_log) == 3

    def test_saves_trace_for_each_chunk_and_final(self, tmp_path):
        run_manager = RunManager(base_dir=str(tmp_path))
        responses = [
            _make_chunk_response(),
            _make_chunk_response(),
            _make_retention_response(),
        ]
        engine = SimulationEngine(FakeProvider(responses), run_manager, chunk_size=500)

        engine.simulate_reader(_make_reader(), ["chunk1", "chunk2"])

        reader_dir = run_manager.run_dir / "Fantasy" / "alice"
        chunks = list(reader_dir.glob("chunk_*.json"))
        retention = list(reader_dir.glob("retention.json"))
        # 2 chunks + 1 retention = 3 files
        assert len(chunks) == 2
        assert len(retention) == 1

    def test_continues_without_raising_on_provider_error(self, tmp_path):
        class ErrorProvider:
            def generate_trace(self, *args, **kwargs):
                raise RuntimeError("API down")

        run_manager = RunManager(base_dir=str(tmp_path))
        engine = SimulationEngine(ErrorProvider(), run_manager, chunk_size=500)

        # Should not propagate — engine prints error and breaks
        engine.simulate_reader(_make_reader(), ["chunk1", "chunk2"])

        # No traces should have been written
        reader_dir = run_manager.run_dir / "Fantasy" / "alice"
        assert not reader_dir.exists() or not list(reader_dir.glob("*.json"))

    def test_message_history_grows_per_chunk(self, tmp_path):
        message_counts = []

        class InspectProvider:
            def generate_trace(self, system_prompt, messages, **kwargs):
                message_counts.append(len(messages))
                return _make_chunk_response()

        run_manager = RunManager(base_dir=str(tmp_path))
        engine = SimulationEngine(InspectProvider(), run_manager, chunk_size=500)

        engine.simulate_reader(_make_reader(), ["c1", "c2"])

        # After chunk 0: [user(c1)] → 1 message sent, then [user(c1), assistant] added
        # After chunk 1: [user(c1), assistant, user(c2)] → 3 messages
        # Final: engine appends a "Chapter complete" cue before calling → 5 messages
        assert message_counts[0] == 1
        assert message_counts[1] == 3
        assert message_counts[2] == 5


class TestRun:
    def test_run_chunks_and_processes_chapter(self, tmp_path):
        chapter = tmp_path / "chapter.txt"
        # Two paragraphs each > 500 words → 2 chunks
        para = " ".join(["word"] * 600)
        chapter.write_text(para + "\n\n" + para, encoding="utf-8")

        calls = []

        class TrackingProvider:
            def generate_trace(self, system_prompt, messages, **kwargs):
                calls.append(1)
                return _make_chunk_response()

        run_manager = RunManager(base_dir=str(tmp_path / "runs"))
        engine = SimulationEngine(TrackingProvider(), run_manager, chunk_size=500)
        reader = ReaderProfile(name="bob", cluster="Thriller", content="p", path=Path("p.md"))

        engine.run(chapter, [reader])

        # 2 chunks + 1 final = 3 calls
        assert len(calls) == 3

    def test_run_processes_all_readers(self, tmp_path):
        chapter = tmp_path / "chapter.txt"
        chapter.write_text("word " * 100, encoding="utf-8")

        calls = []

        class TrackingProvider:
            def generate_trace(self, system_prompt, messages, **kwargs):
                calls.append(1)
                return _make_chunk_response()

        run_manager = RunManager(base_dir=str(tmp_path / "runs"))
        engine = SimulationEngine(TrackingProvider(), run_manager, chunk_size=500)
        readers = [
            ReaderProfile(name="r1", cluster="C1", content="p", path=Path("p1.md")),
            ReaderProfile(name="r2", cluster="C2", content="p", path=Path("p2.md")),
        ]

        engine.run(chapter, readers)

        # 2 readers × (1 chunk + 1 final) = 4 calls
        assert len(calls) == 4
