#!/usr/bin/env python3
"""Re-render trace.md from existing trace.json files in a run directory."""

import json
import sys
from pathlib import Path

from engine import ReaderProfile
from renderer import render_reader_markdown


def extract_run(run_dir: Path) -> None:
    trace_files = sorted(run_dir.rglob("trace.json"))
    if not trace_files:
        print(f"No trace.json files found in {run_dir}")
        sys.exit(1)

    for trace_path in trace_files:
        reader_dir = trace_path.parent
        md_path = reader_dir / "trace.md"
        print(f"  {trace_path.relative_to(run_dir)} ...", end=" ", flush=True)

        try:
            data = json.loads(trace_path.read_text())
            meta = data["meta"]
            profile = ReaderProfile(
                name=reader_dir.name,
                path=Path(meta["profile"]),
                text="",
                cluster=meta.get("cluster"),
            )
            md_path.write_text(
                render_reader_markdown(
                    data["chunks"],
                    data["chapter_end"],
                    profile,
                    Path(meta["chapter"]).name,
                    meta,
                )
            )
            print("ok")
        except Exception as exc:
            print(f"FAILED: {exc}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: extract.py <run_dir>")
        sys.exit(1)
    extract_run(Path(sys.argv[1]))
