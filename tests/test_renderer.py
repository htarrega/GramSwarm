import pytest
from pathlib import Path
from engine import ReaderProfile
from renderer import render_reader_markdown

def test_render_reader_markdown():
    profile = ReaderProfile(name="TestReader", path=Path("p.md"), text="txt", cluster="TestCluster")
    chunks_data = [
        {
            "chunk_index": 0,
            "chunk_text": "This is a test chunk of text.",
            "trace": {
                "prediction_next_beat": "Something happens",
                "prediction_confidence": 3,
                "open_questions": ["Who is he?"],
                "active_expectations": ["Expect a twist"],
                "confusion_points": [{"quote": "text", "why": "confused"}],
                "salience_claim": 4,
                "emotional_register": {"tone": "tense", "intensity": 4},
                "continue_pressure": 5,
                "would_abandon": {"abandon": False, "reason": "Interesting"},
                "voice_match_check": {"score": 4, "note": "Good fit"}
            },
            "usage": {"input_tokens": 10, "output_tokens": 10}
        }
    ]
    chapter_end = {
        "summary_as_retained": "A test summary",
        "chapter_sentence_salience": ["Sentence 1"],
        "expectations_carried_forward": ["Exp 1"],
        "tension_self_report": "Tense",
        "comparables": ["Book X"]
    }
    meta = {
        "timestamp": "20260101",
        "model": "claude-3",
        "num_chunks": 1,
        "chunk_words": 500,
        "total_tokens": 20,
        "input_tokens": 10,
        "output_tokens": 10
    }
    
    md = render_reader_markdown(chunks_data, chapter_end, profile, "Chapter 1", meta)
    
    assert "# Trace: TestReader [TestCluster] — Chapter 1" in md
    assert "## Chunk 1" in md
    assert "**Prediction:** Something happens" in md
    assert "Summary as retained:" in md
    assert "A test summary" in md
    assert "Book X" in md
