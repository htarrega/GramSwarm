import pytest
from gramswarm.core.models import ChunkTrace, RetentionTrace, TraceResponse, EmotionalRegister


VALID_CHUNK_TRACE_DATA = {
    "prediction_next_beat": "The hero will open the door",
    "prediction_confidence": 4,
    "open_questions": ["Who sent the letter?"],
    "active_expectations": ["A reveal is coming"],
    "confusion_points": [],
    "salience_claim": 3,
    "emotional_register": {"tone": "tense", "intensity": 4},
    "continue_pressure": 5,
    "would_abandon": False,
    "voice_match_check": 4,
}

VALID_RETENTION_TRACE_DATA = {
    "summary_as_retained": "The hero discovered the secret room",
    "chapter_sentence_salience": ["The door creaked open", "Nothing was ever the same"],
    "expectations_carried_forward": "The villain will strike back",
    "tension_self_report": "Steady tension building to a sharp spike",
    "comparables": ["The Name of the Wind"],
}

# Note: METRICS block uses indented YAML — the fixed regex preserves
# leading whitespace so textwrap.dedent can remove common indentation correctly.
CHUNK_METRICS_BLOCK = """\
Some internal monologue here.

---
METRICS:
  prediction_next_beat: "The hero will open the door"
  prediction_confidence: 4
  open_questions: ["Who sent the letter?"]
  active_expectations: ["A reveal is coming"]
  confusion_points: []
  salience_claim: 3
  emotional_register: {tone: "tense", intensity: 4}
  continue_pressure: 5
  would_abandon: false
  voice_match_check: 4
---
"""

RETENTION_METRICS_BLOCK = """\
End of chapter summary.

---
METRICS:
  summary_as_retained: "The hero discovered the secret room"
  chapter_sentence_salience: ["The door creaked open"]
  expectations_carried_forward: "The villain will strike back"
  tension_self_report: "Steady tension building to a sharp spike"
  comparables: ["The Name of the Wind"]
---
"""


@pytest.fixture
def valid_chunk_trace():
    return ChunkTrace.model_validate(VALID_CHUNK_TRACE_DATA)


@pytest.fixture
def valid_retention_trace():
    return RetentionTrace.model_validate(VALID_RETENTION_TRACE_DATA)
