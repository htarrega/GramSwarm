import json
from typing import Annotated, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict, BeforeValidator

def _coerce_score(v):
    if isinstance(v, float):
        return int(round(v))
    return v

def _coerce_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                return [v]
        return [v]
    return [v]

Score1to5 = Annotated[int, BeforeValidator(_coerce_score), Field(ge=1, le=5)]
StringList = Annotated[List[str], BeforeValidator(_coerce_list)]

class ConfusionPoint(BaseModel):
    quote: str
    why: str

class EmotionalRegister(BaseModel):
    tone: str
    intensity: Score1to5

class ChunkTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_content: Optional[str] = Field(default=None, description="The original LLM response")
    prediction_next_beat: str = Field(description="What the reader expects to happen next")
    prediction_confidence: Score1to5 = Field(description="How certain the reader is")
    open_questions: StringList = Field(default_factory=list)
    active_expectations: StringList = Field(default_factory=list)
    confusion_points: List[ConfusionPoint] = Field(default_factory=list)
    salience_claim: Score1to5 = Field(description="How important this chunk feels")
    emotional_register: EmotionalRegister
    continue_pressure: Score1to5 = Field(description="Urge to keep reading")
    would_abandon: bool = Field(description="Hard quit signal")
    abandon_reason: Optional[str] = None
    voice_match_check: Score1to5 = Field(description="Fit with reader taste")
    voice_match_note: Optional[str] = None

class RetentionTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_content: Optional[str] = Field(default=None, description="The original LLM response")
    summary_as_retained: str = Field(description="What the reader remembers")
    chapter_sentence_salience: StringList = Field(default_factory=list)
    expectations_carried_forward: str = Field(default="", description="Expectations for the next chapter")
    tension_self_report: str = Field(description="Subjective tension report")
    comparables: StringList = Field(default_factory=list)

class TraceResponse(BaseModel):
    """The response wrapper from a provider"""
    content: str  # The full markdown response
    structured_data: Union[ChunkTrace, RetentionTrace]
    usage: dict = Field(default_factory=dict)
