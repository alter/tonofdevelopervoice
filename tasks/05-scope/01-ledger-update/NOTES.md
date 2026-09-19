# NOTES — 05-scope/01-ledger-update

## Before (T00)

`grep -n "Soup" docs/PROJECT.md` before any edit:

```
15:| Stack (from the machine, with versions) | Python 3.14.4 (homebrew, `/opt/homebrew/bin/python3`) on the dev MacBook (M2, 24GB RAM, usually <8GB free); package manager `uv` 0.8.13 present; `uv sync` resolves a local dev venv on CPython 3.13.7. Training/fine-tuning uses **Unsloth** (chosen over Soup in `docs/research/frameworks.md` T01 — Soup's Aug-Sep 2026 releases show a run of silent-correctness bugs; raw Hugging Face transformers+peft+trl is the fallback), which needs a CUDA 12.8 / PyTorch >=2.7.0 (cu128) environment on the training host. Training/serving-scale runs execute on a separate Ubuntu-under-WSL2 host with 80GB RAM + RTX 5090 32GB VRAM (Blackwell, sm_120 — needs driver >=570, CUDA Toolkit 12.8, not the `apt` default). |
21:| What must work end to end first | Full-scale corpus collection first: mine commit and PR text from major long-lived OSS repos (linux, postgresql, nginx, apache, oracle, and other large projects), restricted to content dated **before 2021**, with any entry containing an AI co-author trailer (`Co-authored-by: <AI agent name>` — Claude/Opus/Sonnet/GPT/ChatGPT/Grok/DeepSeek/etc.) excluded. Then fine-tune a model on that corpus (via Soup, on the RTX 5090 host) to rewrite AI-generated commit/PR text into terse, idiomatic, engineering-style prose — matching the vocabulary, tone and concision of real pre-2021 OSS commit/PR text. Ship both a CLI (accepts text or a file, prints rewritten text to stdout) and a primitive two-panel web form (paste text left, get rewritten text right, no accounts) in v1. |
35:| External integrations | included | GitHub (git clone + GitHub REST API using `GITHUB_TOKEN` from `.env` for PR metadata / co-author filtering); Soup (fine-tuning CLI/toolkit) for the training step; possibly HuggingFace Hub if/when weights are published |
54:- Choice of base model and Soup training recipe details within the stated compute envelope (Mac for dev/pipeline, RTX 5090 host for real training runs).
```

4 hits. Line 15 (§1 Stack) already frames Soup as rejected ("chosen over Soup ... silent-correctness bugs") — this is the one hit expected to survive. Lines 21, 35, 54 are the instructional mentions T02/T01 replace.

## After (T05)

`python3 tasks/check.py`: `task directories: 28; gates: [...]; problems: 0`.

AC1 — `grep -c "Soup" docs/PROJECT.md` → `1`; the sole hit is line 15 (§1 Stack), unchanged
rejection sentence ("chosen over Soup ... silent-correctness bugs").

AC2 — `grep -n "PR text collection\|On-device inference\|AI-written" docs/PROJECT.md`:
```
40:| PR text collection | included | Merged PRs created before 2021, via the GitHub REST API (`tasks/20-corpus/02-pr-collector`) |
41:| On-device inference (Apple Silicon) | included | MLX 4-bit, loaded in process — no CUDA path on the Mac (`tasks/DECISIONS.md` D1) |
42:| AI-written commit/PR text collection | available | Evaluation inputs only; never enters a training file (`tasks/DECISIONS.md` D3) |
```

AC3 — `grep -n "2026-09-19" docs/PROJECT.md` shows the §5 note at lines 74-75.

AC4 — `ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run`: ruff
clean, mypy "no issues found in 55 source files", 115 passed, coverage 100.00% meets the
floor 100.00%. All four commands exit 0.
