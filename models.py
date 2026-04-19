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
        return json.loads(v) if isinstance(v, str) else v


class ChapterEnd(BaseModel):
    summary_as_retained: str
    chapter_sentence_salience: list[str]
    expectations_carried_forward: list[str]
    tension_self_report: str
    comparables: list[str]


class ChunkUsage(BaseModel):
    input_tokens: int
    output_tokens: int


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


class TraceRecord(BaseModel):
    meta: RunMeta
    chunks: list[ChunkRecord]
    chapter_end: ChapterEnd
