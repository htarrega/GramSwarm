import pytest
from pathlib import Path
from engine import chunk_text, load_profile, ReaderProfile, read_chapter, run_readers
from unittest.mock import MagicMock

def test_chunk_text():
    text = "word " * 1200
    chunks = chunk_text(text, 500)
    assert len(chunks) == 3
    assert len(chunks[0].split()) == 500
    assert len(chunks[1].split()) == 500
    assert len(chunks[2].split()) == 200

def test_load_profile(tmp_path):
    profile_dir = tmp_path / "readers_profiles" / "cluster_a"
    profile_dir.mkdir(parents=True)
    profile_file = profile_dir / "reader_1.md"
    profile_file.write_text("Profile content")
    
    profile = load_profile(profile_file)
    assert profile.name == "reader_1"
    assert profile.cluster == "cluster_a"
    assert profile.text == "Profile content"

def test_read_chapter_mock(mocker):
    # Mock Anthropic Client
    mock_client = MagicMock()
    
    # Mock response for chunk trace and chapter end
    mock_response = MagicMock()
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 20
    mock_response.usage.cache_creation_input_tokens = 0
    mock_response.usage.cache_read_input_tokens = 0
    
    # Mock content blocks for tool_use
    block = MagicMock()
    block.type = "tool_use"
    block.input = {"prediction": "test"}
    mock_response.content = [block]
    
    mock_client.messages.create.return_value = mock_response
    
    profile = ReaderProfile(name="test", path=Path("test.md"), text="text", cluster="cluster")
    chunks = ["chunk1", "chunk2"]
    
    chunks_data, chapter_end, usage = read_chapter(mock_client, profile, chunks, "model")
    
    assert len(chunks_data) == 2
    assert chapter_end == {"prediction": "test"}
    assert usage["total_tokens"] == (10 + 20) * 3 # 2 chunks + 1 end
    assert mock_client.messages.create.call_count == 3

def test_run_readers_mock(mocker):
    # Mock Anthropic Client
    mocker.patch("anthropic.Anthropic", return_value=MagicMock())
    
    # Mock read_chapter to avoid API calls
    mocker.patch("engine.read_chapter", return_value=(
        [{"chunk_index": 0, "trace": {}}], 
        {"end": "test"}, 
        {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}
    ))
    
    profiles = [
        ReaderProfile(name="r1", path=Path("p1.md"), text="t1", cluster="c1"),
        ReaderProfile(name="r2", path=Path("p2.md"), text="t2", cluster="c2"),
    ]
    
    results = run_readers(profiles, "some chapter text", chunk_words=500)
    
    assert len(results) == 2
    assert results[0]["profile"].name == "r1"
    assert "chunks_data" in results[0]
