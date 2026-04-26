# GramSwarm — Synthetic Alpha Readers

A tool that simulates a panel of alpha readers on a novel-in-progress using LLM agents distilled from real reader profiles.

Instead of asking "is this chapter good?", GramSwarm makes each reader predict what comes next. Tension, boredom, confusion, and abandonment risk are all derived from prediction patterns — not from ratings, which LLMs inflate by default.

## Quick Start

### Installation
GramSwarm uses `uv` for fast, reproducible dependency management.
```bash
# Install dependencies
uv sync
export ANTHROPIC_API_KEY=***
```
You dont need to export your anthropic key if you already have it in your .bashrc/.zshrc

### Running a Simulation
Place your chapter file under `chapters/` as plain text (UTF-8).
```bash
# Run simulation on a chapter or story
python -m gramswarm.main run chapters/<chapter>.txt

# Run with a custom chunk size
python -m gramswarm.main run chapters/<chapter>.txt --chunk-size 300
```
Loads all profiles from `readers_profiles/` automatically and runs them sequentially. Output goes to `runs/{timestamp}_{chapter}/`.

### Analyzing Results
GramSwarm separates **High-Level Analysis** (for quick diagnosis) from **Raw Trace Data** (for deep-dive editing).

#### 1. Analytical Reports (CLI)
Quickly eyeball pacing dips, abandonment clustering, and overall reader alignment:
```bash
python -m gramswarm.main analyze runs/<timestamp>_<chapter>
```
This generates:
- **Continuity Pressure Analysis**: Visual bar charts of mean `continue_pressure` per chunk, marking abandonment risks with `!!`.
- **Global Panel Cohesion Index (PCI)**: A visual gauge showing if the reader panel is in sync or polarized.

![GramSwarm Analysis Report](images/image.png)
*Example of the Continuity Pressure and Panel Cohesion analysis.*
#### 2. Raw Trace Data (JSON)
Every reader's internal monologue and precise metrics are saved as JSON files in the run directory. These are intended for the author to open and read to understand *why* a reader felt bored or confused.


## Architecture & Structure

GramSwarm is built as a professional Python package using a layered domain architecture.

```
src/gramswarm/
  core/           # Domain logic, Pydantic schemas, and Simulation Engine
  providers/      # AI Adapters (Anthropic, etc.) with prompt caching
  services/       # IO handlers, Analysis tools
  main.py         # CLI entry point
readers_profiles/ # Cluster-based reader personas (.md files)
chapters/         # Manuscript input
runs/             # Output artifacts (Git-ignored)
```

## Metrics Reference

### Visualized Metrics (High-Level Signals)
These metrics are aggregated and rendered in the CLI `analyze` report.

| Metric | Type | What it measures |
|---|---|---|
| `continue_pressure` | 1–5 | Honest urge to keep reading. Used for the Pressure Chart. |
| `would_abandon` | bool | Hard quit signal. Used to identify "leaks" in the narrative. |
| `Panel Cohesion (PCI)`| 0.0-1.0 | Global sync. Tells you if the experience is universal or polarizing. |

### Deep-Dive Metrics (Raw JSON)
These metrics are stored in the JSON traces for manual author review. In the future they will be added.

#### Per-chunk trace
| Metric | Type | What it measures |
|---|---|---|
| `raw_content` | text | The reader's internal monologue (the "Why"). |
| `prediction_next_beat` | text | What the reader expects to happen next. The primary signal. |
| `prediction_confidence` | 1–5 | How certain the reader is. |
| `open_questions` | list | Questions the reader is actively holding. |
| `active_expectations` | list | Promises the reader believes the author has made. |
| `confusion_points` | list | Specific sentences where the reader lost the thread. |
| `salience_claim` | 1–5 | How important this chunk feels for the story. |
| `emotional_register` | tone+int | What emotional note the scene is playing. |
| `voice_match_check` | score+note | How well this chunk fits the reader's taste. |

#### End-of-chapter trace
| Metric | What it measures |
|---|---|
| `summary_as_retained` | What the reader would tell a friend happened. |
| `chapter_sentence_salience` | Which specific sentences the summary draws from. |
| `expectations_carried_forward` | Predictions and promises still open at chapter's end. |
| `tension_self_report` | Where the reader felt pulled, where they drifted. |
| `comparables` | "This reminded me of X" or "This felt like Y trope." |

---

## To be solved

- **Lack of Persistent Memory & Evolution**: Each simulation currently treats the chapter in isolation. There is no memory across chapters, nor a mechanism for reader personas to evolve their opinions or emotional state as the story progresses.
- **Sequential Execution**: Readers are processed one by one, which can be slow for larger panels.
- **Context Window Bloat**: Every chunk and response is appended to the history; very long chapters will eventually exceed the LLM's context window.
- **Naive Chunking**: Text is split by word count and paragraphs rather than narrative beats or scene transitions.
- **Single Provider Dependency**: The CLI is currently hard-wired to Anthropic.

## Research Basis
The trace schema and agent design are grounded in:
- **Argyle et al. 2023** (Silicon sampling)
- **Arora et al. 2025** (Synthetic user validation)
- **NN/G 2025** (Abandonment underreporting)
- **Hullman et al. 2026** (Validation framework)
- **Attention Flows 2026** (Comprehension proxies)
- **Spoiler Alert 2026** (Tension as forecasting disagreement)
