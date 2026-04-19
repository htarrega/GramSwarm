"""Reading engine: chunk text, call API, accumulate traces."""

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import anthropic

from tools import CHAPTER_END_TOOL, CHUNK_TRACE_TOOL

DEFAULT_CHUNK_WORDS = 500
DEFAULT_MODEL = "claude-sonnet-4-6"


@dataclass
class ReaderProfile:
    name: str
    path: Path
    text: str
    cluster: str


def load_profile(path: Path) -> ReaderProfile:
    cluster = path.parent.name if path.parent.name != "readers_profiles" else None
    return ReaderProfile(name=path.stem, path=path, text=path.read_text(), cluster=cluster)


def chunk_text(text: str, words_per_chunk: int) -> list[str]:
    words = text.split()
    return [
        " ".join(words[i: i + words_per_chunk])
        for i in range(0, len(words), words_per_chunk)
    ]


def build_system(profile: ReaderProfile) -> str:
    cluster_note = f"\nREADER ARCHETYPE: {profile.cluster}\n" if profile.cluster else ""

    return f"""\
You are simulating a specific reader. You are NOT an AI assistant, critic, or reviewer.
You are this reader, experiencing a novel for the first time.

YOUR READER PROFILE:
{profile.text}
{cluster_note}
READING INSTRUCTIONS:
- Your PRIMARY task per chunk is PREDICTION: what do you expect to happen next?
- Do NOT rate or evaluate the writing quality directly.
- Do NOT default to being polite. If you would put the book down, say so.
- Emotional responses: describe what the scene REGISTERS as (tense, melancholic, farcical),
  not what you personally feel.
- Report confusion exactly where you find it — quote the specific text.
- `continue_pressure`: your honest urge to keep reading. 1 = would stop here. 5 = can't stop.
- `voice_match_check`: how well this fits your taste. Calibrate against your own reading history.

Stay fully in character as this reader throughout."""


def _call_tool(
    client: anthropic.Anthropic,
    system: str,
    messages: list[dict],
    tool: dict,
    model: str,
    max_retries: int = 3,
) -> tuple[dict, dict]:
    for attempt in range(max_retries):
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=messages,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input, {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                }
        if attempt < max_retries - 1:
            print(f"  [retry {attempt + 1}] no tool_use block", file=sys.stderr)
    raise RuntimeError(f"No structured output after {max_retries} attempts")


def read_chapter(
    client: anthropic.Anthropic,
    profile: ReaderProfile,
    chunks: list[str],
    model: str,
) -> tuple[list[dict], dict, dict]:
    system = build_system(profile)
    messages: list[dict] = []
    chunks_data: list[dict] = []
    total_in = total_out = 0

    for i, chunk in enumerate(chunks):
        print(f"  chunk {i + 1}/{len(chunks)} ...", end=" ", flush=True)
        t0 = time.time()

        messages.append({
            "role": "user",
            "content": (
                f"You are now reading chunk {i + 1} of {len(chunks)}:\n\n"
                f"---\n{chunk}\n---\n\n"
                f"Report your structured reading response."
            ),
        })

        trace, usage = _call_tool(client, system, messages, CHUNK_TRACE_TOOL, model)
        elapsed = time.time() - t0
        total_in += usage["input_tokens"]
        total_out += usage["output_tokens"]
        print(f"done ({elapsed:.1f}s | {usage['input_tokens']}+{usage['output_tokens']} tok)")

        messages.append({"role": "assistant", "content": json.dumps(trace, indent=2)})
        chunks_data.append({
            "chunk_index": i,
            "chunk_text": chunk,
            "trace": trace,
            "usage": usage,
            "elapsed_seconds": round(elapsed, 2),
        })

    print(f"  end-of-chapter ...", end=" ", flush=True)
    t0 = time.time()
    messages.append({
        "role": "user",
        "content": "You've finished the chapter. Now provide your end-of-chapter record.",
    })
    chapter_end, usage = _call_tool(client, system, messages, CHAPTER_END_TOOL, model)
    elapsed = time.time() - t0
    total_in += usage["input_tokens"]
    total_out += usage["output_tokens"]
    print(f"done ({elapsed:.1f}s | {usage['input_tokens']}+{usage['output_tokens']} tok)")

    return chunks_data, chapter_end, {
        "input_tokens": total_in,
        "output_tokens": total_out,
        "total_tokens": total_in + total_out,
    }


def run_readers(
    profiles: list[ReaderProfile],
    chapter_text: str,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
) -> list[dict]:
    client = anthropic.Anthropic()
    chunks = chunk_text(chapter_text, chunk_words)
    results = []

    for profile in profiles:
        print(f"\n[{profile.name}] ({profile.cluster or 'no cluster'})")
        try:
            chunks_data, chapter_end, usage = read_chapter(client, profile, chunks, DEFAULT_MODEL)
            results.append({
                "profile": profile,
                "chunks_data": chunks_data,
                "chapter_end": chapter_end,
                "usage": usage,
            })
        except Exception as exc:
            print(f"  FAILED: {exc}", file=sys.stderr)
            results.append({"profile": profile, "error": str(exc)})

    return results
