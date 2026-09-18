# Research summary (Sept 2026) — decisions Part 2 reads

Consolidates T01-T05. Each subsection links the source file; Part 2 implementation tasks
reference this file directly rather than re-deriving these choices.

## Decision: Framework

**Unsloth**, fallback raw Hugging Face (transformers+peft+trl). Chosen over Soup: Soup's
Aug-Sep 2026 releases show a run of silent-correctness bugs (wrong gradients with a
healthy-looking loss curve, silently-no-op config flags, a 2.6x memory-accounting bug),
and its headline "layer streaming" feature solves a VRAM problem this project doesn't
have (32GB already fits 8-13B QLoRA without it). Unsloth has explicit Blackwell/RTX-5090
support with a ready Docker path, is free for single-GPU use, and is the fastest current
single-GPU QLoRA option in public benchmarks. Full detail: `frameworks.md`.

## Decision: Base model

**Qwen3-8B-Base** (Apache 2.0, not gated), fallback **Mistral-3-8B** (dense, Apache 2.0);
next step up if 8B proves insufficiently expressive: Qwen3-14B or Gemma-4-12B-pt. A base
(not instruct) checkpoint is preferred so the SFT doesn't have to fight an already-learned
instruct "voice." Widest verified QLoRA tooling coverage of any Sept-2026 candidate
(Unsloth documents recipes specifically for Qwen3-8B). Full detail: `base-models.md`.

## Decision: Training approach

**SFT on synthetic paired data** (STRAP-style back-translation): synthesize the "AI-ish"
input side of each training pair by running authentic corpus text through an LLM prompted
to inflate it toward generic AI verbosity (across multiple LLMs/prompts/temperatures to
avoid overfitting to one generator's fingerprint), then SFT directly on
`{input: synthetic_AI_ish, output: authentic}` pairs. Plain LM continuation (no pairs) is
used only as an optional DAPT warm-up and as one evaluation ingredient, never as the
deliverable — it trains p(y), not p(y|x), so it can't teach "rewrite X into Y." DPO/ORPO
preference optimization is deferred to an optional post-SFT polish stage, out of scope
for v1. Dataset schema for T09: `{"input": ..., "output": ..., "project": ...}` JSONL
with a held-out split. Full detail: `training-approach.md`.

## Decision: Data collection

**Primary: local `git clone --mirror` + `git log` extraction** for commit messages across
linux, postgresql, nginx, apache, mysql — no API rate limits, most complete. Filter on
parsed author date (`%ad`) strictly before 2021-01-01 (not `git log --before`, whose
default date-field semantics weren't confirmed); cross-check commit date (`%cd`) for
history-rewrite signals. **Secondary: GitHub GraphQL API** (`GITHUB_TOKEN`) for PR
description text (`body` field, ~100 PRs/request), filtered client-side on
`createdAt < 2021-01-01` — check actual PR volume per repo first, since linux/postgresql/
apache review primarily off-GitHub and may have thin PR corpora. Skip GH Archive/BigQuery
as a primary source (event-stream sampling isn't equivalent to full git history, and the
BigQuery mirror's currency is in question as of 2026). Run the AI-co-author trailer regex
as a validation pass on all extracted text (expected zero matches on genuine pre-2021
data; any match means drop and investigate a rewrite). Full detail: `data-collection.md`.

## Decision: Evaluation

**A six-part automated report**, run as `scripts/evaluate.py` (T15), CPU-only: (1) MiniLM
embedding cosine similarity as a content-preservation floor, (2) BERTScore against the
real authentic reference (not sBLEU-against-source, which would penalize the intended
compression), (3) a validated authentic-vs-AI style classifier (TF-IDF + logistic
regression, shared with the optional Option-3 DPO polish stage), (4) GPT-2 perplexity as
a fluency sanity check, (5) forced-choice LLM-judge win rate vs. a 50% baseline, (6)
optional MAUVE if the held-out set is large enough. Report includes worst-scoring
examples for manual spot check — automated metrics alone are not trusted without periodic
human review. Full detail: `evaluation.md`.

## What this changes from the original plan/intake

- Framework pivoted from the intake-time default assumption (Soup) to Unsloth — `AGENTS.md`
  and `docs/PROJECT.md` §1 were updated accordingly at T01.
- Collection targets both commit messages (git log, all five repos) and PR description
  text (GitHub API, where repo PR volume justifies it) rather than commit messages alone.
- Dataset shape is paired SFT examples with a `project` field (for a possible future
  per-project conditioning), not a plain style corpus — this determines T09's schema.
