---
intake: completed 2026-09-18
---
# PROJECT

Single source of truth for what this project is, what it contains, and what the agent may decide alone. `/plan` reads it before every task. Cells hold `_unanswered_` until asked, `n/a` when not applicable.

## 1. Identity

| Question | Answer |
|---|---|
| Name / slug | tonofdevelopervoice |
| Repository | git@github.com:alter/tonofdevelopervoice.git (public, empty at intake) |
| Other agents or people working in this repo | Roman Dolgov (owner) + other Claude Code agent sessions; no other humans |
| Stack (from the machine, with versions) | Python 3.14.4 (homebrew, `/opt/homebrew/bin/python3`) on the dev MacBook (M2, 24GB RAM, usually <8GB free); package manager `uv` 0.8.13 present; `uv sync` resolves a local dev venv on CPython 3.13.7. Training/fine-tuning uses **Unsloth** (chosen over Soup in `docs/research/frameworks.md` T01 — Soup's Aug-Sep 2026 releases show a run of silent-correctness bugs; raw Hugging Face transformers+peft+trl is the fallback), which needs a CUDA 12.8 / PyTorch >=2.7.0 (cu128) environment on the training host. Training/serving-scale runs execute on a separate Ubuntu-under-WSL2 host with 80GB RAM + RTX 5090 32GB VRAM (Blackwell, sm_120 — needs driver >=570, CUDA Toolkit 12.8, not the `apt` default). |

## 2. Goal

| Question | Answer |
|---|---|
| What must work end to end first | Full-scale corpus collection first: mine commit and PR text from major long-lived OSS repos (linux, postgresql, nginx, apache, oracle, and other large projects), restricted to content dated **before 2021**, with any entry containing an AI co-author trailer (`Co-authored-by: <AI agent name>` — Claude/Opus/Sonnet/GPT/ChatGPT/Grok/DeepSeek/etc.) excluded. Then fine-tune a model on that corpus (via Soup, on the RTX 5090 host) to rewrite AI-generated commit/PR text into terse, idiomatic, engineering-style prose — matching the vocabulary, tone and concision of real pre-2021 OSS commit/PR text. Ship both a CLI (accepts text or a file, prints rewritten text to stdout) and a primitive two-panel web form (paste text left, get rewritten text right, no accounts) in v1. |
| What the first version must NOT do | No MCP server yet (explicitly deferred to a later version — CLI + web form only for v1). No accounts/auth, no payments, no admin panel, no notifications. Do not widen the corpus beyond pre-2021, non-AI-co-authored commit/PR text without a direct request. |

## 3. Capability ledger

One state per row: `included` (present, expected to work) · `available` (partly there; note says what is missing) · `absent` (not part of this project; build only on request) · `removed` (deleted on purpose; restore only on request). No row means `absent`.

| Capability | State | Note |
|---|---|---|
| Accounts / sign-in | absent | No auth anywhere in v1 (CLI, web form) |
| Persistent storage | included | The collected corpus, filtered/cleaned datasets, and trained model artifacts must persist across sessions; kept out of git (large, binary/bulk) |
| File uploads | available | CLI accepts a local file path as input; the web form is paste-only text (no file upload) in v1 |
| Payments | absent | |
| Admin / roles | absent | |
| External integrations | included | GitHub (git clone + GitHub REST API using `GITHUB_TOKEN` from `.env` for PR metadata / co-author filtering); Soup (fine-tuning CLI/toolkit) for the training step; possibly HuggingFace Hub if/when weights are published |
| Background jobs / scheduling | included | Large-scale scraping and training runs are long-running, unattended jobs |
| Notifications (email, push, messaging) | absent | |
| Real-time | absent | |
| MCP server | absent (deferred) | Explicitly out of scope for v1; add on direct request in a later plan |

## 4. Decided by the agent — never asked

Defaults; extend per project. The agent makes these calls, records them under a plan's `## Assumptions`, and explains them in one line.

- File layout, naming, formatting, splitting files above 1400 lines.
- Library choice when the repo already uses one for the purpose; standard library over a new dependency.
- Test shape: unit for pure rules, integration through real boundaries for shared behavior, end-to-end only for the minimal happy path. Never test wording or layout.
- Local services via Docker Compose, never native installs.
- One service unless a measured limit says otherwise; no speculative layers, base classes, CQRS, event buses.
- Scope of validation for a change: the narrowest stable check that proves it, plus directly coupled risks.
- Which docs to update when behavior, contracts, setup or operations change.
- Exact corpus filtering heuristics (regex/parsing rules for date cutoff and AI co-author trailer exclusion), as long as the stated exclusion goal is met.
- Corpus storage format and on-disk layout (e.g. JSONL/Parquet, directory structure), as long as it is reproducible and excluded from git.
- Choice of base model and Soup training recipe details within the stated compute envelope (Mac for dev/pipeline, RTX 5090 host for real training runs).
- Which specific large OSS repos beyond the four named (linux, postgresql, nginx, apache) go into the corpus, as long as they are large, long-lived, and have pre-2021 history available.

## 5. Unattended policy

| May run alone | Must become `[!] BLOCKED` |
|---|---|
| tests, lint, type check, local builds | new paid cloud/GPU rental service account (e.g. spinning up a billed RunPod/Vast/Lambda instance) not already provisioned |
| large-scale scraping/cloning of the named public repos (git clone + GitHub API, using the provided `GITHUB_TOKEN`) | large-scale **re**-scraping or **deleting** the already-collected corpus (re-running collection from scratch, or discarding the built dataset) |
| commits on `main` | payments, money movement |
| reading docs and public web | sending email/messages to real users (n/a — no such capability) |
| kicking off a full training run on the RTX 5090 host | |
| deploying the CLI/web form publicly | |
| publishing trained model weights (e.g. to HuggingFace) | |

Note: the last three rows (training runs, public deployment, publishing weights) were explicitly authorized to run unattended in the intake interview — only re-scraping/deleting the corpus requires approval first.

## 6. Gate checks

Commands that must exit 0 before any task is marked `[x]`. `/plan` copies them into every verify line.

```
ruff check .
mypy .
pytest
python3 scripts/coverage_gate.py --run
```

Baseline accepted as-is (pre-existing failures tolerated): n/a — repo has no commits yet; baseline is clean by construction at T00.

Coverage: the command, its report format, and where the floor lives (`.coverage-gate.json`). The ratchet
(`python3 scripts/coverage_gate.py --run`) belongs in the list above per task, or runs at `T00` and at the
plan's finish when the suite is slow — say which. The floor rises on its own; lowering it is a decision
recorded here, with a date and a reason, and never a way to make a check pass.

| Question | Answer |
|---|---|
| Coverage command | `pytest --cov=. --cov-report=xml` |
| Report format (`coverage-py` / `json-summary` / `cobertura` / `lcov` / `go`) | coverage-py |
| Floor today (from the tool, not from memory) | 0% — no code yet; `scripts/coverage_gate.py --set-floor` runs at T00 once code exists |
| Ratchet per task or per plan | Per task |
| Areas deliberately left uncovered, and why | GPU-only training internals that only run on the RTX 5090 host (no GPU on the Mac dev machine) are exercised by that host's own test run rather than folded into the Mac-computed coverage floor — a coverage number computed without a GPU present would be meaningless for that code path |

## 7. Delivery

| Question | Answer |
|---|---|
| Commit per task or per plan | Commit per task |
| Branch policy | Work directly on `main` |
| Who reviews before merge | No formal review gate — solo owner (Roman Dolgov) + agent sessions, no external reviewer |

## 8. Disclosure required by the receiving repository

Read the target's `CONTRIBUTING.md` / `AGENTS.md` before filling this in; the answer belongs to them, not to us. `none` means the repository asks for nothing and nothing is volunteered. A wording means it is inserted verbatim into the pull-request body. `_unanswered_` blocks opening a pull request there.

| Target | What it requires | Wording to use |
|---|---|---|
| this repository (alter/tonofdevelopervoice) | none | none |

The source repos used for corpus collection (linux, postgresql, nginx, apache, oracle, etc.) are read-only data sources — this project never opens a pull request against them, so no disclosure row applies to them.

Whatever this says, a direct question from a person is answered by the owner, not by the session, and the session never writes in his voice outside this machine.

## 9. Owning docs

Read before working in the area. Prefer `.claude/rules/<area>.md` with `paths:` so this loads automatically.

| Area | Document |
|---|---|
| Repository conventions, stack, setup | `AGENTS.md` |
| Task list / execution plan | `docs/plans/<slug>.md` (created by `/plan`) |
