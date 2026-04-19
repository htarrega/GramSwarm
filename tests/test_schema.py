from pathlib import Path
from models import TraceRecord


def test_trace_schema_valid():
    fixture = Path(__file__).parent / "fixtures" / "trace_fixture.json"
    TraceRecord.model_validate_json(fixture.read_text())
