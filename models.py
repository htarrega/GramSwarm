"""Pydantic models for GramSwarm trace schema validation."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field, field_validator


class ConfusionPoint(BaseModel):
    quote: str
    why: str


class EmotionalRegister(BaseModel):
    tone: str
    intensity: int = Field(ge=1, le=5)


class WouldAbandon(BaseModel):
    abandon: bool
    reason: str


class VoiceMatchCheck(BaseModel):
    score: int = Field(ge=1, le=5)
    note: str


class ChunkTrace(BaseModel):
    prediction_next_beat: str
    prediction_confidence: int = Field(ge=1, le=5)
    open_questions: list[str]
    active_expectations: list[str]
    confusion_points: list[ConfusionPoint]
    salience_claim: int = Field(ge=1, le=5)
    emotional_register: EmotionalRegister
    continue_pressure: int = Field(ge=1, le=5)
    would_abandon: WouldAbandon
    voice_match_check: VoiceMatchCheck

    @field_validator(
        "emotional_register",
        "would_abandon",
        "voice_match_check",
        mode="before",
    )
    @classmethod
    def _parse_if_str(cls, v):
        if not isinstance(v, str):
            return v
        v = v.strip()
        try:
            return json.loads(v)
        except json.JSONDecodeError as e:
            if "Extra data" in str(e):
                # Extract the first balanced JSON object
                start = v.find('{')
                if start != -1:
                    bracket_count = 0
                    for i in range(start, len(v)):
                        if v[i] == '{':
                            bracket_count += 1
                        elif v[i] == '}':
                            bracket_count -= 1
                            if bracket_count == 0:
                                try:
                                    return json.loads(v[start : i + 1])
                                except json.JSONDecodeError:
                                    pass
            raise e


class ChapterEnd(BaseModel):
    summary_as_retained: str
    chapter_sentence_salience: list[str]
    expectations_carried_forward: list[str]
    tension_self_report: str
    comparables: list[str]


class ChunkUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    cost_usd: float = 0.0


class ChunkRecord(BaseModel):
    chunk_index: int
    chunk_text: str
    trace: ChunkTrace
    usage: ChunkUsage
    elapsed_seconds: float


class RunMeta(BaseModel):
    timestamp: str
    model: str
    chapter: str
    chapter_hash: str
    chunk_words: int
    profile: str
    cluster: str | None
    profile_version: str
    num_chunks: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    cost_usd: float = 0.0


class TraceRecord(BaseModel):
    meta: RunMeta
    chunks: list[ChunkRecord]
    chapter_end: ChapterEnd
