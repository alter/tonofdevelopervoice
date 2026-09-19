# AGENTS.md

Shared instructions for every coding agent in this repository. `CLAUDE.md` imports this file (`@AGENTS.md`); do not duplicate rules there. The personal working contract in `~/.claude/CLAUDE.md` still applies on top.

## Stack & environment

- Pipeline/CLI/web code: Python on the dev MacBook (M2, 24GB RAM, usually <8GB free), system Python is 3.14.4 via homebrew, `uv` available for env/deps (`uv sync` currently resolves CPython 3.13.7 for the dev venv).
- Training framework: **Unsloth** (see `docs/research/frameworks.md` — chosen over Soup after Soup's Aug-Sep 2026 releases showed a run of silent-correctness bugs; raw Hugging Face transformers+peft+trl is the fallback if Unsloth's kernels ever misbehave).
- Real fine-tuning runs happen on a separate Ubuntu-under-WSL2 host (80GB RAM, RTX 5090 32GB VRAM), not the Mac — the Mac has no GPU worth training on. That host is Blackwell (sm_120): needs driver >=570, CUDA Toolkit 12.8 (not the `apt` default, which is CUDA 12.0), PyTorch >=2.7.0 cu128 wheel.
- `GITHUB_TOKEN` lives in `.env` (already gitignored) — used for GitHub API calls during corpus collection (PR metadata, filtering AI co-author trailers). Load it from `.env`, never hardcode or print it.
- Full scope, capability ledger and unattended-work policy for this project: `docs/PROJECT.md`.

## Source of truth

- `docs/PROJECT.md` owns scope, the capability ledger, decisions the agent makes alone, the unattended policy and the gate checks. Read it first. A capability with no ledger row is `absent`; dormant code or an old doc is not a requirement.
- `docs/plans/<slug>.md` owns the current task list. Work from it; update it; never delete tasks.
- Runbooks in `docs/` own setup and operations. Verify against code, scripts and runtime output rather than trusting a stale doc; update the doc when behavior, contracts, setup or operations change.
- New work lives in `tasks/` (goal, decisions and per-task work for the v2 rebuild —
  `tasks/README.md`, `PROTOCOL.md`, `GOAL.md`, `DECISIONS.md`); `docs/plans/tonofdevelopervoice-v1.md`
  is closed history, kept for its `## Log`.

## Engineering

- Fix the owning cause, not a symptom in a caller. A cross-layer bug may have a one-file fix; verify affected callers.
- Smallest coherent change with clear ownership. Small duplication beats the wrong shared abstraction. Remove workarounds when their cause is fixed.
- Match investigation to the change: contracts need producer, consumer, serializer and read/write checks; auth and routing need enforcement, guards and state; async work needs retries, idempotency, ordering, cancellation and failure visibility.
- Architecture rules live in checks, not prose: put layering and import boundaries into a script that exits non-zero (`import-linter` for Python) and list it under gate checks.
- Reproducible bug → failing regression test first, then the fix, then the original reproduction again.
- A behaviour change carries its test, and that test was seen failing before the change. Coverage may not fall: the floor in `.coverage-gate.json` rises by itself and is lowered only as a recorded decision. A check that has never been red does not count — break the code in a scratch copy once and keep the red output.

## Validation

- A check passes only when the behavior is correct and the command exits 0. Report failed or unavailable checks plainly; a task with broken primary behavior is not done.
- Run the baseline once before the first edit to separate pre-existing failures from new ones; record it in the plan's `## Log`.
- Narrowest stable check per change; the full gate list before a task is marked `[x]`; broad regression only for cross-cutting changes or release.
- End-to-end tests only for the minimal product-critical path; assert outcomes (persisted data, navigation), never wording or layout.

## Git and workspace

- Inspect `git status --short --branch` and `git remote -v` before any git operation. Work on the branch the plan names; never switch mid-run. Stage by path, never `git add -A` (submodule pointers, marker files).
- Never `git stash`, `reset --hard`, `clean`, or `checkout -- .` to make progress. If uncommitted user changes block you, stop that task with `[!] BLOCKED` and continue with others.
- Commit per finished task when `docs/PROJECT.md` says so; message `T##: <what changed>`. Never push unless asked.
- Scratch goes to `.claude/scratch/`, never the repo root. Remove your own scratch when done.
- Never stop or kill processes to free a port; use another port.
- Secrets, tokens, cookies, customer data and raw `.env` values never appear in logs, tests, fixtures or replies. Never weaken auth, validation, rate limits or auditability to pass a check.
- Generated files change through their generator (schema → migration), never by hand.

## Reporting

- What changed, why, which checks ran with their results, remaining risk or blocked items, suggested commit message. No headings for their own sake, no restating the task.
