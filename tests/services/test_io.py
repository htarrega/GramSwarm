import json
import pytest
from pathlib import Path
from gramswarm.services.io import RunManager
from gramswarm.core.models import ChunkTrace, RetentionTrace
from tests.conftest import VALID_CHUNK_TRACE_DATA, VALID_RETENTION_TRACE_DATA


class TestRunManager:
    def test_run_dir_is_created_on_init(self, tmp_path):
        manager = RunManager(base_dir=str(tmp_path), chapter_name="intro")
        assert manager.run_dir.is_dir()

    def test_run_dir_name_includes_chapter(self, tmp_path):
        manager = RunManager(base_dir=str(tmp_path), chapter_name="prologue")
        assert "prologue" in manager.run_dir.name

    def test_run_dir_name_without_chapter(self, tmp_path):
        manager = RunManager(base_dir=str(tmp_path))
        assert manager.run_dir.exists()

    def test_get_reader_dir_creates_path(self, tmp_path):
        manager = RunManager(base_dir=str(tmp_path))
        reader_dir = manager.get_reader_dir("Fantasy", "alice")
        assert reader_dir.is_dir()
        assert reader_dir.name == "alice"
        assert reader_dir.parent.name == "Fantasy"

    def test_save_meta_writes_json(self, tmp_path):
        manager = RunManager(base_dir=str(tmp_path))
        meta = {"chapter": "intro.txt", "chunk_size": 500}
        manager.save_meta(meta)
        meta_file = manager.run_dir / "run_meta.json"
        assert meta_file.exists()
        loaded = json.loads(meta_file.read_text(encoding="utf-8"))
        assert loaded["chapter"] == "intro.txt"
        assert loaded["chunk_size"] == 500

    def test_str_returns_run_dir_path(self, tmp_path):
        manager = RunManager(base_dir=str(tmp_path))
        assert str(manager) == str(manager.run_dir)

    def test_save_structured_writes_json(self, tmp_path):
        manager = RunManager(base_dir=str(tmp_path))
        trace = ChunkTrace.model_validate(VALID_CHUNK_TRACE_DATA)
        content = "some raw trace content"
        manager.save_structured("Fantasy", "alice", trace, 2, content)
        f = manager.run_dir / "Fantasy" / "alice" / "chunk_002.json"
        assert f.exists()
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data["continue_pressure"] == 5
        assert data["raw_content"] == content

    def test_save_retention_writes_retention_json(self, tmp_path):
        manager = RunManager(base_dir=str(tmp_path))
        trace = RetentionTrace.model_validate(VALID_RETENTION_TRACE_DATA)
        content = "some raw retention content"
        manager.save_retention("Fantasy", "alice", trace, content)
        f = manager.run_dir / "Fantasy" / "alice" / "retention.json"
        assert f.exists()
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data["summary_as_retained"] == "The hero discovered the secret room"
        assert data["raw_content"] == content
