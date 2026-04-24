"""Reading engine: chunk text, call API, accumulate traces."""

import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from models import ChapterEnd, ChunkTrace
from tools import CHAPTER_END_TOOL, CHUNK_TRACE_TOOL

DEFAULT_CHUNK_WORDS = 500
DEFAULT_MODEL = "claude-sonnet-4-6"

PRICING_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input": 3.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
        "output": 15.00,
    },
}


def compute_cost_usd(usage: dict, model: str) -> float:
    p = PRICING_PER_MTOK.get(model)
    if not p:
        return 0.0
    return (
        usage.get("input_tokens", 0) * p["input"]
        + usage.get("cache_creation_input_tokens", 0) * p["cache_write"]
        + usage.get("cache_read_input_tokens", 0) * p["cache_read"]
        + usage.get("output_tokens", 0) * p["output"]
    ) / 1_000_000

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, text[m.end():]


@dataclass
class ReaderProfile:
    name: str
    path: Path
    text: str
    cluster: str
    profile_version: str = "unknown"


def load_profile(path: Path) -> ReaderProfile:
    cluster = path.parent.name if path.parent.name != "readers_profiles" else None
    raw = path.read_text()
    fm, body = _parse_frontmatter(raw)
    return ReaderProfile(
        name=path.stem,
        path=path,
        text=body,
        cluster=cluster,
        profile_version=fm.get("profile_version", "unknown"),
    )


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


def _save_call_log(
    log_ctx: dict,
    system: str,
    messages: list[dict],
    response: dict,
    usage: dict,
    elapsed: float,
) -> None:
    calls_dir: Path = log_ctx["calls_dir"]
    calls_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "call_name": log_ctx["call_name"],
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": log_ctx.get("model", DEFAULT_MODEL),
        "profile_version": log_ctx.get("profile_version", "unknown"),
        "chapter_hash": log_ctx.get("chapter_hash", ""),
        "system": system,
        "messages": messages,
        "response": response,
        "usage": usage,
        "elapsed_seconds": round(elapsed, 3),
    }
    (calls_dir / f"{log_ctx['call_name']}.json").write_text(json.dumps(record, indent=2))


def _apply_cache_control(messages: list[dict]) -> None:
    """Keep exactly one ephemeral cache breakpoint on the last assistant message.

    Combined with a cache breakpoint on the system prompt, this caches the full
    prefix (system + all completed chunk turns) on every call after the first.
    """
    last_asst = -1
    for i, msg in enumerate(messages):
        if msg["role"] != "assistant":
            continue
        content = msg["content"]
        if isinstance(content, str):
            msg["content"] = [{"type": "text", "text": content}]
        for block in msg["content"]:
            block.pop("cache_control", None)
        last_asst = i
    if last_asst >= 0:
        messages[last_asst]["content"][-1]["cache_control"] = {"type": "ephemeral"}


def _call_tool(
    client: anthropic.Anthropic,
    system: str,
    messages: list[dict],
    tool: dict,
    model: str,
    max_retries: int = 3,
    log_ctx: dict | None = None,
) -> tuple[dict, dict, float]:
    """Returns (tool_output, usage, elapsed_seconds)."""
    _apply_cache_control(messages)
    system_blocks = [
        {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
    ]
    t0 = time.time()
    for attempt in range(max_retries):
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_blocks,
            messages=messages,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
        )
        elapsed = time.time() - t0
        for block in response.content:
            if block.type == "tool_use":
                u = response.usage
                usage = {
                    "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens,
                    "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
                    "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
                }
                usage["cost_usd"] = round(compute_cost_usd(usage, model), 6)
                if log_ctx is not None:
                    _save_call_log(
                        log_ctx=log_ctx,
                        system=system,
                        messages=messages,
                        response=block.input,
                        usage=usage,
                        elapsed=elapsed,
                    )
                return block.input, usage, elapsed
        if attempt < max_retries - 1:
            print(f"  [retry {attempt + 1}] no tool_use block", file=sys.stderr)
    raise RuntimeError(f"No structured output after {max_retries} attempts")


def read_chapter(
    client: anthropic.Anthropic,
    profile: ReaderProfile,
    chunks: list[str],
    model: str,
    calls_dir: Path | None = None,
    chapter_hash: str = "",
    messages: list[dict] | None = None,
) -> tuple[list[dict], dict, dict, list[dict]]:
    system = build_system(profile)
    if messages is None:
        messages = []
    chunks_data: list[dict] = []
    total_in = total_out = total_cw = total_cr = 0

    for i, chunk in enumerate(chunks):
        print(f"  chunk {i + 1}/{len(chunks)} ...", end=" ", flush=True)

        messages.append({
            "role": "user",
            "content": (
                f"You are now reading chunk {i + 1} of {len(chunks)}:\n\n"
                f"---\n{chunk}\n---\n\n"
                f"Report your structured reading response."
            ),
        })

        log_ctx = None
        if calls_dir is not None:
            log_ctx = {
                "calls_dir": calls_dir,
                "call_name": f"chunk_{i}",
                "model": model,
                "profile_version": profile.profile_version,
                "chapter_hash": chapter_hash,
            }

        trace, usage, elapsed = _call_tool(
            client, system, messages, CHUNK_TRACE_TOOL, model, log_ctx=log_ctx
        )
        total_in += usage["input_tokens"]
        total_out += usage["output_tokens"]
        total_cw += usage["cache_creation_input_tokens"]
        total_cr += usage["cache_read_input_tokens"]
        print(
            f"done ({elapsed:.1f}s | in={usage['input_tokens']} "
            f"cw={usage['cache_creation_input_tokens']} "
            f"cr={usage['cache_read_input_tokens']} "
            f"out={usage['output_tokens']})"
        )

        try:
            ChunkTrace.model_validate(trace)
        except Exception as exc:
            print(f"  [warn] chunk {i} trace schema invalid: {exc}", file=sys.stderr)

        messages.append({"role": "assistant", "content": json.dumps(trace, indent=2)})
        chunks_data.append({
            "chunk_index": i,
            "chunk_text": chunk,
            "trace": trace,
            "usage": usage,
            "elapsed_seconds": round(elapsed, 2),
        })

    print(f"  end-of-chapter ...", end=" ", flush=True)
    messages.append({
        "role": "user",
        "content": "You've finished the chapter. Now provide your end-of-chapter record.",
    })

    log_ctx = None
    if calls_dir is not None:
        log_ctx = {
            "calls_dir": calls_dir,
            "call_name": "chapter_end",
            "model": model,
            "profile_version": profile.profile_version,
            "chapter_hash": chapter_hash,
        }

    chapter_end, usage, elapsed = _call_tool(
        client, system, messages, CHAPTER_END_TOOL, model, log_ctx=log_ctx
    )
    total_in += usage["input_tokens"]
    total_out += usage["output_tokens"]
    total_cw += usage["cache_creation_input_tokens"]
    total_cr += usage["cache_read_input_tokens"]
    print(
        f"done ({elapsed:.1f}s | in={usage['input_tokens']} "
        f"cw={usage['cache_creation_input_tokens']} "
        f"cr={usage['cache_read_input_tokens']} "
        f"out={usage['output_tokens']})"
    )

    try:
        ChapterEnd.model_validate(chapter_end)
    except Exception as exc:
        print(f"  [warn] chapter_end schema invalid: {exc}", file=sys.stderr)

    reader_usage = {
        "input_tokens": total_in,
        "output_tokens": total_out,
        "cache_creation_input_tokens": total_cw,
        "cache_read_input_tokens": total_cr,
        "total_tokens": total_in + total_out + total_cw + total_cr,
    }
    reader_usage["cost_usd"] = round(compute_cost_usd(reader_usage, model), 6)
    return chunks_data, chapter_end, reader_usage, messages


def run_readers(
    profiles: list[ReaderProfile],
    chapter_text: str,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    run_dir: Path | None = None,
) -> list[dict]:
    client = anthropic.Anthropic()
    chunks = chunk_text(chapter_text, chunk_words)
    chapter_hash = hashlib.sha256(chapter_text.encode()).hexdigest()[:12]
    results = []

    for profile in profiles:
        print(f"\n[{profile.name}] ({profile.cluster or 'no cluster'})")
        calls_dir = None
        if run_dir is not None:
            calls_dir = run_dir / (profile.cluster or "unassigned") / profile.name / "calls"

        try:
            chunks_data, chapter_end, usage = read_chapter(
                client, profile, chunks, DEFAULT_MODEL,
                calls_dir=calls_dir,
                chapter_hash=chapter_hash,
            )
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
