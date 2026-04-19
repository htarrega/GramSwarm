#!/usr/bin/env python3
"""GramSwarm — run all reader profiles on a chapter."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from version import __version__
from engine import DEFAULT_CHUNK_WORDS, DEFAULT_MODEL, load_profile, run_readers
from renderer import save_reader_run, save_run_meta

PROFILES_ROOT = Path("readers_profiles")


def load_all_profiles() -> list:
    paths = sorted(PROFILES_ROOT.rglob("*.md"))
    if not paths:
        print(f"Error: no profiles found in {PROFILES_ROOT}/", file=sys.stderr)
        sys.exit(1)
    return [load_profile(p) for p in paths]


def main() -> None:
    parser = argparse.ArgumentParser(description="GramSwarm — synthetic alpha readers.")
    parser.add_argument("--version", action="version", version=f"GramSwarm {__version__}")
    parser.add_argument("chapter", help="Chapter file to read")
    parser.add_argument("--chunk-words", type=int, default=DEFAULT_CHUNK_WORDS,
                        help=f"Words per chunk (default: {DEFAULT_CHUNK_WORDS})")
    args = parser.parse_args()

    chapter_path = Path(args.chapter)
    if not chapter_path.exists():
        print(f"Error: chapter not found: {chapter_path}", file=sys.stderr)
        sys.exit(1)

    profiles = load_all_profiles()
    chapter_text = chapter_path.read_text()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("runs") / f"{timestamp}_{chapter_path.stem}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Chapter  : {chapter_path.name}")
    print(f"Readers  : {len(profiles)} — {', '.join(p.name for p in profiles)}")
    print(f"Chunks   : ~{args.chunk_words} words  |  Model: {DEFAULT_MODEL}")
    print(f"Run dir  : {run_dir}")

    results = run_readers(profiles, chapter_text, chunk_words=args.chunk_words)

    base_meta = {
        "timestamp": timestamp,
        "model": DEFAULT_MODEL,
        "chapter": str(chapter_path),
        "chunk_words": args.chunk_words,
    }

    total_in = total_out = 0
    for result in results:
        if "error" in result:
            continue
        try:
            save_reader_run(run_dir, result, chapter_path.name, base_meta)
        except Exception as exc:
            print(f"  [{result['profile'].name}] save failed: {exc}", file=sys.stderr)
        total_in += result["usage"]["input_tokens"]
        total_out += result["usage"]["output_tokens"]

    save_run_meta(run_dir, base_meta, results)

    successful = sum(1 for r in results if "error" not in r)
    failed = len(results) - successful
    cost = (total_in * 3 + total_out * 15) / 1_000_000

    print(f"\nDone     : {successful} ok" + (f", {failed} failed" if failed else ""))
    print(f"Tokens   : {total_in + total_out}  |  Cost~: ${cost:.4f}")


if __name__ == "__main__":
    main()
