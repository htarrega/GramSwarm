import json
import pytest
from pathlib import Path
from gramswarm.services.analyzer import RunAnalyzer
from gramswarm.core.models import ChunkTrace
from tests.conftest import VALID_CHUNK_TRACE_DATA


def _write_chunk_json(run_dir: Path, cluster: str, reader: str, chunk_index: int, data: dict):
    d = run_dir / cluster / reader
    d.mkdir(parents=True, exist_ok=True)
    (d / f"chunk_{chunk_index:03d}.json").write_text(json.dumps(data), encoding="utf-8")


class TestAnalyzePressure:
    def test_returns_empty_for_empty_run_dir(self, tmp_path):
        analyzer = RunAnalyzer(str(tmp_path))
        result = analyzer.analyze_pressure()
        assert result == {}

    def test_single_reader_single_chunk(self, tmp_path):
        _write_chunk_json(tmp_path, "Fantasy", "alice", 0, VALID_CHUNK_TRACE_DATA)
        analyzer = RunAnalyzer(str(tmp_path))
        result = analyzer.analyze_pressure()

        assert "Fantasy" in result
        assert len(result["Fantasy"]) == 1
        assert result["Fantasy"][0] == 5.0

    def test_mean_across_readers(self, tmp_path):
        data_pressure_3 = {**VALID_CHUNK_TRACE_DATA, "continue_pressure": 3}
        _write_chunk_json(tmp_path, "Fantasy", "alice", 0, VALID_CHUNK_TRACE_DATA)
        _write_chunk_json(tmp_path, "Fantasy", "bob", 0, data_pressure_3)
        analyzer = RunAnalyzer(str(tmp_path))
        result = analyzer.analyze_pressure()

        assert result["Fantasy"][0] == pytest.approx(4.0)

    def test_multiple_clusters(self, tmp_path):
        _write_chunk_json(tmp_path, "Fantasy", "alice", 0, VALID_CHUNK_TRACE_DATA)
        _write_chunk_json(tmp_path, "SciFi", "bob", 0, VALID_CHUNK_TRACE_DATA)
        analyzer = RunAnalyzer(str(tmp_path))
        result = analyzer.analyze_pressure()

        assert "Fantasy" in result
        assert "SciFi" in result

    def test_skips_malformed_chunks(self, tmp_path):
        _write_chunk_json(tmp_path, "Fantasy", "alice", 0, VALID_CHUNK_TRACE_DATA)
        d = tmp_path / "Fantasy" / "alice"
        (d / "chunk_001.json").write_text("not valid json {{{", encoding="utf-8")
        analyzer = RunAnalyzer(str(tmp_path))
        result = analyzer.analyze_pressure()

        assert result["Fantasy"] == [5.0]

    def test_multiple_chunks_per_reader(self, tmp_path):
        data_pressure_3 = {**VALID_CHUNK_TRACE_DATA, "continue_pressure": 3}
        _write_chunk_json(tmp_path, "Fantasy", "alice", 0, VALID_CHUNK_TRACE_DATA)
        _write_chunk_json(tmp_path, "Fantasy", "alice", 1, data_pressure_3)
        analyzer = RunAnalyzer(str(tmp_path))
        result = analyzer.analyze_pressure()

        assert result["Fantasy"] == [5.0, 3.0]

    def test_ragged_chunks_truncated_to_first_reader(self, tmp_path):
        """Documents current behavior: extra chunks in later readers are silently dropped."""
        data_p3 = {**VALID_CHUNK_TRACE_DATA, "continue_pressure": 3}
        _write_chunk_json(tmp_path, "Fantasy", "alice", 0, VALID_CHUNK_TRACE_DATA)
        _write_chunk_json(tmp_path, "Fantasy", "bob", 0, data_p3)
        _write_chunk_json(tmp_path, "Fantasy", "bob", 1, VALID_CHUNK_TRACE_DATA)

        analyzer = RunAnalyzer(str(tmp_path))
        result = analyzer.analyze_pressure()

        assert len(result["Fantasy"]) == 1


class TestRenderAsciiChart:
    def test_empty_data_prints_warning(self, capsys):
        analyzer = RunAnalyzer(".")
        analyzer.render_ascii_chart({})
        captured = capsys.readouterr()
        assert "No analysis data" in captured.out

    def test_renders_cluster_names(self, capsys):
        analyzer = RunAnalyzer(".")
        analyzer.render_ascii_chart({"Fantasy": [3.0, 4.0, 5.0]})
        captured = capsys.readouterr()
        assert "Fantasy" in captured.out

    def test_renders_bar_blocks(self, capsys):
        analyzer = RunAnalyzer(".")
        analyzer.render_ascii_chart({"SciFi": [5.0]})
        captured = capsys.readouterr()
        assert "█████" in captured.out
