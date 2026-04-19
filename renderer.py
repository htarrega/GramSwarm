"""Markdown and JSON rendering for reader traces."""

import json
from pathlib import Path

from engine import ReaderProfile


def render_reader_markdown(
    chunks_data: list[dict],
    chapter_end: dict,
    profile: ReaderProfile,
    chapter_name: str,
    meta: dict,
) -> str:
    cluster_label = f" [{profile.cluster}]" if profile.cluster else ""

    lines = [
        f"# Trace: {profile.name}{cluster_label} — {chapter_name}",
        f"",
        f"**Run:** {meta['timestamp']}  ",
        f"**Model:** {meta['model']}  ",
        f"**Profile v:** {meta.get('profile_version', '?')}  |  "
        f"**Chapter:** `{meta.get('chapter_hash', '')}`  ",
        f"**Chunks:** {meta['num_chunks']} × ~{meta['chunk_words']} words  ",
        f"**Tokens:** {meta['total_tokens']} (in: {meta['input_tokens']}, out: {meta['output_tokens']})",
        f"",
        f"---",
        f"",
    ]

    for cd in chunks_data:
        i = cd["chunk_index"]
        t = cd["trace"]
        preview = " ".join(cd["chunk_text"].split()[:12])
        abandon = t["would_abandon"] if isinstance(t["would_abandon"], dict) else {"abandon": False, "reason": str(t["would_abandon"])}
        reg = t["emotional_register"] if isinstance(t["emotional_register"], dict) else {"tone": str(t["emotional_register"]), "intensity": "?"}
        vmc = t["voice_match_check"] if isinstance(t["voice_match_check"], dict) else {"score": "?", "note": str(t["voice_match_check"])}

        lines += [
            f"## Chunk {i + 1}",
            f"",
            f"> *{preview}…*",
            f"",
            f"**Prediction:** {t['prediction_next_beat']}  ",
            f"**Confidence:** {t['prediction_confidence']}/5",
            f"",
        ]
        if t["open_questions"]:
            lines.append("**Open questions:**")
            lines += [f"- {q}" for q in t["open_questions"]]
            lines.append("")
        if t["active_expectations"]:
            lines.append("**Active expectations:**")
            lines += [f"- {e}" for e in t["active_expectations"]]
            lines.append("")
        if t["confusion_points"]:
            lines.append("**Confusion points:**")
            lines += [f'- *"{cp["quote"]}"* — {cp["why"]}' for cp in t["confusion_points"]]
            lines.append("")

        lines += [
            f"**Salience:** {t['salience_claim']}/5 | "
            f"**Register:** {reg['tone']} ({reg['intensity']}/5) | "
            f"**Continue pressure:** {t['continue_pressure']}/5",
            f"",
            f"**Would abandon:** {'YES — ' if abandon['abandon'] else 'No — '}{abandon['reason']}",
            f"",
            f"**Voice match:** {vmc['score']}/5 — {vmc['note']}",
            f"",
            f"---",
            f"",
        ]

    ce = chapter_end
    lines += [
        f"## End of Chapter",
        f"",
        f"**Summary as retained:**",
        f"",
        f"{ce['summary_as_retained']}",
        f"",
        f"**Salient sentences / scenes:**",
    ]
    lines += [f"- {s}" for s in ce["chapter_sentence_salience"]]
    lines += [
        f"",
        f"**Expectations carried forward:**",
    ]
    lines += [f"- {e}" for e in ce["expectations_carried_forward"]]
    lines += [
        f"",
        f"**Tension self-report:** {ce['tension_self_report']}",
        f"",
        f"**Comparables:**",
    ]
    lines += [f"- {c}" for c in ce["comparables"]]

    return "\n".join(lines)


def save_reader_run(
    run_dir: Path,
    result: dict,
    chapter_name: str,
    base_meta: dict,
) -> None:
    profile: ReaderProfile = result["profile"]
    reader_dir = run_dir / (profile.cluster or "unassigned") / profile.name
    reader_dir.mkdir(parents=True, exist_ok=True)

    usage = result["usage"]
    chunks_data = result["chunks_data"]
    meta = {
        **base_meta,
        "profile": str(profile.path),
        "cluster": profile.cluster,
        "profile_version": profile.profile_version,
        "num_chunks": len(chunks_data),
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "total_tokens": usage["total_tokens"],
    }

    (reader_dir / "trace.json").write_text(
        json.dumps(
            {"meta": meta, "chunks": chunks_data, "chapter_end": result["chapter_end"]},
            indent=2,
        )
    )
    (reader_dir / "trace.md").write_text(
        render_reader_markdown(chunks_data, result["chapter_end"], profile, chapter_name, meta)
    )


def save_run_meta(run_dir: Path, meta: dict, results: list[dict]) -> None:
    readers_meta = []
    for r in results:
        if "error" in r:
            readers_meta.append({"profile": r["profile"].name, "error": r["error"]})
        else:
            readers_meta.append({
                "profile": r["profile"].name,
                "cluster": r["profile"].cluster,
                **r["usage"],
            })

    (run_dir / "run_meta.json").write_text(
        json.dumps({"meta": meta, "readers": readers_meta}, indent=2)
    )
