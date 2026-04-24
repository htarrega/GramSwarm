# GramSwarm — Synthetic Alpha Readers

A tool that simulates a panel of alpha readers on a novel-in-progress using LLM agents distilled from real reader profiles.

Instead of asking "is this chapter good?", GramSwarm makes each reader predict what comes next. Tension, boredom, confusion, and abandonment risk are all derived from prediction patterns — not from ratings, which LLMs inflate by default.

Each reader processes the chapter chunk by chunk (~500 words), carrying memory forward, and emits a structured trace per chunk:

- **Prediction** — what the reader expects to happen next, and how confident they are
- **Open questions** — unresolved questions they're actively holding
- **Active expectations** — promises they believe the author has made that haven't paid off
- **Confusion points** — specific quoted sentences where they lost the thread
- **Salience** — how important this chunk feels for the story
- **Emotional register** — what note the scene is playing (tense, melancholic, farcical…)
- **Continue pressure** — honest urge to keep reading, 1–5
- **Would abandon** — hard quit signal with reason

At the end of the chapter each reader produces a retention trace: what they'd tell a friend happened, which scenes they actually remember, and what expectations they're carrying forward.

Readers are grouped into clusters (folders under `readers_profiles/`). Each cluster represents a different reader archetype — Professional Readers, Casual Crossover, Genre Veterans, etc. Clusters are defined by the folder structure, not by any config file.

The output is raw traces per reader, saved as JSON and rendered markdown. No heatmap aggregation yet — that comes later. Right now the value is in reading the traces yourself and spotting where readers diverge.

---

## Usage

```bash
python run.py chapters/<chapter>.txt
```

Loads all profiles from `readers_profiles/` automatically and runs them sequentially. Output goes to `runs/{timestamp}_{chapter}/`.

```bash
python run.py chapters/<chapter>.txt --chunk-words 300
```

Place your chapter file under `chapters/` as plain text (UTF-8). Any filename works; the stem is used to name the run directory.

### Re-render markdown from a saved run

If a run crashes mid-save, recover with:

```bash
python extract.py runs/<timestamp>_<chapter>
```

### Quick look at continue-pressure across a run

```bash
python analyze_pressure.py runs/<timestamp>_<chapter>
```

Prints a per-cluster bar chart of mean `continue_pressure` per chunk, with `!` marking any chunk where at least one reader abandoned. Reads the rendered `trace.md` files — useful for eyeballing pacing dips and abandonment clustering before opening individual traces.

---

## Structure

```
readers_profiles/
  <ClusterName>/           # cluster = folder name
    <reader>.md
  <AnotherCluster>/
    <reader>.md
chapters/                  # manuscript chapters
runs/                      # output (gitignored)
  <timestamp>_<chapter>/
    <ClusterName>/
      <reader>/
        trace.json
        trace.md
    run_meta.json
```

### Adding a cluster

Create a folder under `readers_profiles/`.

### Adding a reader

Drop a `.md` profile file into the relevant cluster folder. The profile should be written in first person, anchored in the reader's actual taste and reading history. The more specific, the more differentiated the output.

---

## Metrics reference

### Per-chunk trace

| Metric | Type | What it measures |
|---|---|---|
| `prediction_next_beat` | free text | What the reader expects to happen next. The primary signal — tension is derived from disagreement across readers here, not from self-reported emotion. |
| `prediction_confidence` | 1–5 | How certain the reader is. High confidence + high disagreement across readers = productive tension. High confidence + agreement = predictable. Low confidence + disagreement = confusion. |
| `open_questions` | list | Questions the reader is actively holding. Accumulation signals good mystery-building; absence signals the text isn't making promises. |
| `active_expectations` | list | Promises the reader believes the author has made that haven't paid off yet. A proxy for narrative obligation load — too many unresolved = reader fatigue; too few = nothing at stake. |
| `confusion_points` | list of {quote, why} | Specific sentences where the reader lost the thread, quoted exactly. Distinct from surprise — confusion is a failure of clarity, surprise is intentional. |
| `salience_claim` | 1–5 | How important this chunk feels for the story. Low salience across all readers = filler. High variance across readers = contested importance (often a sign of subtext landing unevenly). |
| `emotional_register` | tone + intensity 1–5 | What emotional note the scene is playing, not what the reader personally feels. Avoids the fake-emotion trap — LLMs cannot feel, but they can identify register. |
| `continue_pressure` | 1–5 | Honest urge to keep reading. 1 = would stop here. 5 = can't stop. The most direct pacing signal. A chapter that drops below 3 for most readers at the same chunk has a structural problem there. |
| `would_abandon` | bool + reason | Hard quit signal, asked explicitly because LLMs underreport abandonment unless directly prompted (NN/G 2025). The reason is more useful than the boolean. |
| `voice_match_check` | score 1–5 + note | How well this chunk fits the reader's own taste, calibrated against their reading history. Lets you separate "this is confusing" from "this is not my genre." |

### End-of-chapter trace

| Metric | What it measures |
|---|---|
| `summary_as_retained` | What the reader would tell a friend happened. Summaries trace comprehension — gaps here reveal what didn't land structurally, not just emotionally (Attention Flows 2026). |
| `chapter_sentence_salience` | Which specific sentences or scenes the summary draws from. Cross-reference against your own sense of the chapter's key moments to find salience mismatches. |
| `expectations_carried_forward` | Predictions and promises still open at chapter's end. Feed into the next chapter's context. High load = readers are engaged but you owe them payoffs. |
| `tension_self_report` | Where the reader felt pulled, where they drifted. Soft signal, high noise — use only as a secondary check against `continue_pressure`. |
| `comparables` | "This reminded me of X" or "This felt like Y trope." Reveals the reader's mental model of what kind of book this is. Divergence across readers here is interesting data. |

### How to read the output

**Convergence** (all readers flag the same chunk) = structural signal, high confidence. Act on it.

**Divergence** (readers split on a chunk) = the text is doing something contested. Could be intentional subtext, could be a clarity failure. Investigate before changing.

**Abandonment clustering** = if multiple readers would abandon at the same chunk, that's your most urgent problem regardless of what else is working.

**Prediction accuracy in the next chunk** = if a reader's chunk N prediction is wildly wrong in a way that suggests misunderstanding (not surprise), chunk N has a clarity failure.

---

## Research basis

The trace schema and agent design are grounded in the following papers:

- **Argyle et al. 2023** — *Out of One, Many* — LLMs as silicon sampling of human subpopulations; basis for profile-anchored simulation and its limits.
- **Arora et al. 2025** — synthetic user validation methodology; calibration against real user variance.
- **NN/G 2025** — synthetic readers systematically underreport abandonment unless explicitly prompted; justifies the `would_abandon` hard-quit signal.
- **Hullman et al. 2026** — validation framework for LLM-simulated users; informs the three-phase calibration path (author gut-check → self-validation → human comparison).
- **Attention Flows 2026** — conceptual engagement via summaries; basis for `summary_as_retained` and `chapter_sentence_salience` as comprehension proxies.
- **Spoiler Alert 2026** — tension as forecasting disagreement; basis for making prediction the primary per-chunk signal instead of ratings.

---

## Cost & caching

Each reader runs as an accumulating conversation: chunk N's call re-sends the system prompt (reader profile + reading instructions) plus every prior chunk's user message and the model's trace for it. Without caching, the reader profile (~4–7k tokens for a detailed one) and the growing prefix are paid for at full input rate on every call.

GramSwarm uses Anthropic **prompt caching** with two ephemeral breakpoints per API call:

1. **The system prompt** — the reader's profile and the reading instructions. Re-used across every chunk for that reader.
2. **The last assistant turn** — caches the whole conversation prefix (system + every completed chunk + its trace) up through the most recent model response.

TTL is 5 minutes. Since chunks within a reader run sequentially, the cache stays warm across a reader's calls. Caches are per-reader — each profile is a different system prompt, so readers don't share cache.

**Observed effect on a typical reader run** (system + 4 chunks + end-of-chapter = 6 calls):
- Call 1: writes system to cache.
- Call 2: reads system; writes an extended prefix up through the first trace.
- Calls 3–6: read the growing prefix at ~10% of base input price; each writes a slightly longer prefix.

Run output now reports the real API-billed cost, broken down by category:

```
Tokens   : in=2100 cache_write=8840 cache_read=35200 out=6300  (cache hit 76.1% of input)
Cost     : $0.1234
```

- `in` = fresh input tokens (new user message in the call)
- `cache_write` = tokens written to cache this call (billed at 1.25× base)
- `cache_read` = tokens read from cache (billed at 0.1× base)
- `out` = output tokens

Pricing is hard-coded in `engine.PRICING_PER_MTOK` (currently `claude-sonnet-4-6`). Update it if you swap models.

---

## Requirements

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```
