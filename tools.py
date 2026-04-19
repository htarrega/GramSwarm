"""Anthropic tool schemas for structured reader traces."""

CHUNK_TRACE_TOOL: dict = {
    "name": "chunk_trace",
    "description": "Structured reading response to a single chunk of text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "prediction_next_beat": {
                "type": "string",
                "description": "What you expect to happen next in the story.",
            },
            "prediction_confidence": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": "How sure you are. 1=wild guess, 5=certain.",
            },
            "open_questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Unresolved questions you are actively holding.",
            },
            "active_expectations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Promises you believe the author has made that haven't paid off yet.",
            },
            "confusion_points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "quote": {"type": "string"},
                        "why": {"type": "string"},
                    },
                    "required": ["quote", "why"],
                },
                "description": "Specific sentences where you lost the thread. Quote exactly.",
            },
            "salience_claim": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": "How important this chunk feels for the story. 1=filler, 5=essential.",
            },
            "emotional_register": {
                "type": "object",
                "properties": {
                    "tone": {
                        "type": "string",
                        "description": "What note the scene is playing (e.g. tense, melancholic, farcical).",
                    },
                    "intensity": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                    },
                },
                "required": ["tone", "intensity"],
            },
            "continue_pressure": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": "Urge to keep reading. 1=would stop here, 5=can't stop.",
            },
            "would_abandon": {
                "type": "object",
                "properties": {
                    "abandon": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["abandon", "reason"],
            },
            "voice_match_check": {
                "type": "object",
                "properties": {
                    "score": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "How well this chunk aligns with your taste.",
                    },
                    "note": {"type": "string"},
                },
                "required": ["score", "note"],
            },
        },
        "required": [
            "prediction_next_beat",
            "prediction_confidence",
            "open_questions",
            "active_expectations",
            "confusion_points",
            "salience_claim",
            "emotional_register",
            "continue_pressure",
            "would_abandon",
            "voice_match_check",
        ],
    },
}

CHAPTER_END_TOOL: dict = {
    "name": "chapter_end_trace",
    "description": "End-of-chapter structured record. NOT a review — a retention trace.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary_as_retained": {
                "type": "string",
                "description": "What you would tell a friend happened in this chapter.",
            },
            "chapter_sentence_salience": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The specific sentences or scenes your summary draws from.",
            },
            "expectations_carried_forward": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Predictions and promises still open. Fed to next chapter.",
            },
            "tension_self_report": {
                "type": "string",
                "description": "Where you felt pulled, where you drifted.",
            },
            "comparables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "'This reminded me of X' or 'This felt like Y trope'.",
            },
        },
        "required": [
            "summary_as_retained",
            "chapter_sentence_salience",
            "expectations_carried_forward",
            "tension_self_report",
            "comparables",
        ],
    },
}
