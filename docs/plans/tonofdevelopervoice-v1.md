---
status: running
created: 2026-09-18
---
# tonofdevelopervoice v1: research + corpus/training pipeline + CLI/web form

## Goal
Two-part plan. Part 1 (research, T01-T06): survey the Sept-2026 landscape of fine-tuning
frameworks, base models that fit a 32GB-VRAM card, training approaches, data-collection
approaches, and evaluation methodology for a text style-transfer task, and record concrete
choices. Part 2 (implementation, T07-T17): build the corpus-collection pipeline for
pre-2021, non-AI-co-authored commit/PR text from linux, postgresql, nginx, apache and
mysql; author the Unsloth training config; implement a CLI and a two-panel web form that
rewrite AI-generated commit/PR text into that authentic engineering style, against a
pluggable inference backend (stub for agent-side tests, real model wired per a runbook
the user runs on the separate 5090 host this session cannot reach). MCP stays out of
scope for v1 per `docs/PROJECT.md`.

## Acceptance criteria
- [ ] AC1 Research synthesis exists and names concrete choices — `test -f docs/research/SUMMARY.md && grep -Eq '^## Decision: (Framework|Base model|Training approach|Data collection|Evaluation)' docs/research/SUMMARY.md`
- [ ] AC2 Corpus-filtering logic (pre-2021 cutoff, AI co-author trailer exclusion) is unit-tested and green — `pytest tests/test_filters.py -q`
- [ ] AC3 Pilot collection produced real records from at least one repo — `test -s data/raw/linux.jsonl` (or the T04/T06-decided path) and its manifest shows a non-zero count
- [ ] AC4 Full collection ran against all five named repos with a manifest recording per-repo counts — `test -f data/manifest.json && python3 -c "import json,sys; m=json.load(open('data/manifest.json')); assert all(m.get(r,0)>0 for r in ['linux','postgresql','nginx','apache','mysql'])"`
- [ ] AC5 Training config exists and validates — `python3 -c "from tonofdevelopervoice.train.config import load_training_config; load_training_config('training/config.yaml')"` (amended from the original `soup.yaml`/`soup config validate` wording after T01 changed the framework decision from Soup to Unsloth, which has no equivalent CLI-validated YAML — see `## Assumptions`)
- [ ] AC6 CLI works end to end against the stub backend — `pytest tests/test_cli.py -q`
- [ ] AC7 Web form works end to end against the stub backend — `pytest tests/test_web.py -q`
- [ ] AC8 Deployment runbook exists covering venv, tokens, training, serving on the 5090 host — `test -f docs/runbook-deploy.md && grep -q 'HF_TOKEN' docs/runbook-deploy.md && grep -q 'GITHUB_TOKEN' docs/runbook-deploy.md`
- [ ] AC9 Gate checks green at every task, coverage floor never falls — `ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run`

## Stack
Python 3.14.4 (dev MacBook, pipeline/CLI/web code) managed with `uv` (resolves CPython
3.13.7 for the dev venv). Unsloth (chosen over Soup in T01 — see `docs/research/frameworks.md`)
as the fine-tuning framework, needing a CUDA 12.8 / PyTorch >=2.7.0 (cu128) environment
that only exists on the training host, not this repo's Mac-side venv. Training/real
inference execute on a separate Ubuntu-under-WSL2 host (80GB RAM, RTX 5090 32GB) that
this session cannot reach directly.

## Decisions
- Research depth (Part 1) -> Broad comparative survey: frameworks (Soup, Axolotl, Unsloth,
  LLaMA-Factory, raw HF PEFT/TRL), base models fitting 32GB VRAM, training approaches
  (LoRA/QLoRA/full/DPO/etc.), and data-collection approaches, all as of Sept 2026.
- Hugging Face access -> User will provide (and has provided) `HF_TOKEN` in `.env`; gated
  models are on the table, not restricted to fully-open models.
- Serving architecture -> Everything (CLI, web form, trained model) runs on the 5090 host
  only; no client/server network split for v1.
- Priority if time runs out -> A working CLI end to end (even on a partial corpus) beats
  corpus completeness or the web form.
- Evaluation methodology -> Automated metric against a held-out set of real pre-2021
  messages (exact metric chosen in T05, e.g. embedding similarity or perplexity), not
  manual-only spot-check.
- "Oracle" in the original repo list -> MySQL (`mysql/mysql-server`, Oracle-owned, open
  source, pre-2021 history available), not literal Oracle DB source.
- 5090 host access -> This session has no SSH/remote access to it. Part 2 produces code,
  tests (against a stub inference backend) and a runbook; actual training and
  real-model-backed CLI/web verification are manual steps the user runs on that host.

## Assumptions
- Research findings are written to `docs/research/*.md`, one file per subtopic plus a
  `SUMMARY.md` that consolidates the decisions Part 2 reads — no existing convention to
  follow, chosen for traceability.
- Corpus target repos: linux, postgresql, nginx, apache, mysql (5 repos) to start;
  `docs/PROJECT.md` §4 already delegates "which repos beyond the four named" to the agent,
  so this list may grow later without asking again.
- Corpus is built incrementally and validated before scaling (pilot on one repo in T07,
  full run across all five in T08), rather than firing all five collectors blind — this
  satisfies the "full-scale corpus first" MVP framing from intake while honoring the
  "working CLI first" priority: the pilot's small output is enough to unblock CLI/web
  development while full collection runs in the background.
- CLI and web form are built against a small `InferenceBackend` interface with a stub
  implementation for agent-side tests; the real Unsloth-trained-model implementation is
  wired in T14 but can only be *exercised* on the 5090 host, since this session has no
  GPU and no remote access there.
- T10 was amended from its original `soup.yaml`/`soup config validate` wording: T01
  changed the framework decision from Soup to Unsloth (see `docs/research/frameworks.md`),
  and Unsloth has no equivalent single declarative-YAML-plus-CLI-validator — it's used via
  a Python training script. Split accordingly: `training/config.yaml` (the recipe) plus a
  pure-Python structural validator under `src/` (Mac-checkable, no `unsloth` import), and
  the actual Unsloth/trl training script under a new `training/` directory kept outside
  `src`/`tests`/`scripts` so this repo's mypy/pytest gate never needs CUDA-specific
  dependencies (`torch` cu128, `unsloth`, `bitsandbytes`) installed on the Mac. AC5 amended
  to match.
- Publishing model weights publicly (allowed by `docs/PROJECT.md` §5) is out of scope for
  this plan — nothing here uploads weights anywhere; that's a follow-up if wanted later.
- Verify commands for research tasks (T01-T06) check that the file exists and contains a
  `## Decision` (or `## Decision: <Topic>` for the summary) section, since a research
  write-up has no test suite of its own.

## Out of scope
- MCP server (deferred per `docs/PROJECT.md`, build only on direct request).
- Accounts/auth, payments, admin panel, notifications, real-time features.
- Publishing trained model weights to HuggingFace or any public host.
- Executing training or real-model inference from this session — no remote access to the
  5090 host; those steps are handed off via runbook.
- Repos beyond linux/postgresql/nginx/apache/mysql, unless a later task or request adds
  them.

## Tasks
- [x] T00 Bootstrap project scaffolding: `pyproject.toml` via `uv`, ruff+mypy+pytest config,
      `scripts/coverage_gate.py`, empty `src/` package layout; run gate checks once and
      record the clean baseline (0 tests, floor 0%) in `## Log` — verify: `ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run --set-floor`

- [x] T01 Research fine-tuning frameworks landscape (Soup vs Axolotl vs Unsloth vs
      LLaMA-Factory vs raw HF PEFT/TRL) as of Sept 2026; write `docs/research/frameworks.md`
      ending in a `## Decision` naming the chosen framework and why — verify: `test -f docs/research/frameworks.md && grep -q '^## Decision' docs/research/frameworks.md`

- [x] T02 Research base model candidates that fit 32GB VRAM (QLoRA/LoRA, Sept 2026), license
      terms (HF token now available so gated models are eligible), and suitability for a
      style/tone rewrite task; write `docs/research/base-models.md` with a `## Decision` —
      verify: `test -f docs/research/base-models.md && grep -q '^## Decision' docs/research/base-models.md`

- [x] T03 Research the training/fine-tuning approach for this specific task (plain LM
      continuation on target-style text vs supervised input->output rewrite pairs vs
      DPO/ORPO/instruction-tuning), and what shape the dataset needs to take as a result;
      write `docs/research/training-approach.md` with a `## Decision` — verify: `test -f docs/research/training-approach.md && grep -q '^## Decision' docs/research/training-approach.md`

- [x] T04 Research data-collection approaches (GH Archive/BigQuery public dataset, GitHub
      REST/GraphQL API, plain `git log` mining, existing public commit-message datasets)
      and concrete techniques for the pre-2021 cutoff and AI-co-author-trailer exclusion;
      write `docs/research/data-collection.md` with a `## Decision` — verify: `test -f docs/research/data-collection.md && grep -q '^## Decision' docs/research/data-collection.md`

- [x] T05 Research evaluation methodology for style-transfer quality (embedding similarity,
      perplexity, or other automated metrics against a held-out real corpus, per the
      "automated metric" decision); write `docs/research/evaluation.md` with a `## Decision`
      naming the concrete metric and tooling — verify: `test -f docs/research/evaluation.md && grep -q '^## Decision' docs/research/evaluation.md`

- [x] T06 Synthesize T01-T05 into `docs/research/SUMMARY.md`: one `## Decision: <Topic>`
      section per framework/base model/training approach/data collection/evaluation,
      cross-referencing the source files; this is what Part 2 tasks read — verify: `test -f docs/research/SUMMARY.md && grep -Eq '^## Decision: (Framework|Base model|Training approach|Data collection|Evaluation)' docs/research/SUMMARY.md`

- [x] T07 Implement the corpus collector per the T04/T06 decision (git-log mining and/or
      GitHub API using `GITHUB_TOKEN` from `.env`), with pure, unit-testable filtering
      functions for the pre-2021 date cutoff and AI-co-author-trailer exclusion (write the
      failing tests first); run it as a pilot against one repo (linux) with a bounded
      window so the task finishes in reasonable time; output JSONL under `data/raw/` (gitignored)
      — verify: `pytest tests/test_filters.py tests/test_collector.py -q && ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run`

- [x] T08 Scale the collector to the remaining four repos (postgresql, nginx, apache,
      mysql), unattended per `docs/PROJECT.md` §5; write `data/manifest.json` with
      per-repo record counts — verify: `python3 -c "import json; m=json.load(open('data/manifest.json')); assert all(m.get(r,0)>0 for r in ['linux','postgresql','nginx','apache','mysql'])"`

- [x] T09 Build dataset assembly: merge per-repo JSONL into the unified shape decided in
      T03, with a held-out eval split (for T05's metric) and dedup; pure-logic unit tests
      for merging/splitting/schema validation — verify: `pytest tests/test_dataset.py -q && ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run`

- [x] T10 Author `training/config.yaml` (Unsloth/trl recipe: base model + LoRA/QLoRA params
      per T02/T03) plus a structural validator (`tonofdevelopervoice.train.config`, pure
      Python, no `unsloth` import needed) so it's checkable on the Mac without a GPU; write
      the actual Unsloth training script under `training/` (outside `src/`/`tests`/`scripts`
      so it's not pulled into this repo's mypy/pytest gate — it needs CUDA-specific
      deps only installable on the 5090 host) plus `docs/runbook-training.md` describing
      how to run the real fine-tune there — verify: `python3 -c "from tonofdevelopervoice.train.config import load_training_config; load_training_config('training/config.yaml')"` `&& test -f docs/runbook-training.md`

- [x] T11 Define the `InferenceBackend` interface (one method: rewrite(text) -> text) and a
      stub implementation for tests; unit tests for the interface contract — verify: `pytest tests/test_inference_backend.py -q`

- [x] T12 Implement the CLI: accepts text via stdin/arg or a file path, prints rewritten
      text to stdout, uses `InferenceBackend`; unit tests against the stub backend covering
      text input, file input, and error cases — verify: `pytest tests/test_cli.py -q && ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run`

- [x] T13 Implement the web form: two panels (paste text left, rewritten text right), no
      accounts, uses `InferenceBackend`; tests against the stub backend via the framework's
      test client — verify: `pytest tests/test_web.py -q && ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run`

- [ ] T14 Wire the real Unsloth-trained-model implementation of `InferenceBackend` (loads
      weights, runs generation); since this session has no GPU, verify only that it
      constructs correctly against a mocked/local tiny checkpoint if feasible, otherwise
      document that real-weight verification happens on the host — verify: `pytest tests/test_inference_backend.py -q && ruff check . && mypy .`

- [ ] T15 Implement the evaluation script `scripts/evaluate.py` per T05/T06's chosen
      metric, runnable against the held-out split from T09; unit-test the metric
      computation on synthetic examples (no GPU needed for this test) — verify: `pytest tests/test_evaluate.py -q && ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run`

- [ ] T16 Write `docs/runbook-deploy.md`: syncing this repo to the 5090 host, setting up
      the CUDA 12.8 / Unsloth training environment there, providing `HF_TOKEN`/`GITHUB_TOKEN`, running
      collection (if not already done)/training/`scripts/evaluate.py`/CLI/web form on that
      host — verify: `test -f docs/runbook-deploy.md && grep -q 'HF_TOKEN' docs/runbook-deploy.md && grep -q 'GITHUB_TOKEN' docs/runbook-deploy.md`

- [ ] T17 `[!] BLOCKED (needs confirmation): run the full fine-tune, `scripts/evaluate.py`,
      and a live CLI/web-form check against the real trained model on the 5090 host` — this
      session has no SSH/remote access to that host (missing dependency), so this step
      cannot be executed unattended; hand off `docs/runbook-training.md` and
      `docs/runbook-deploy.md` to the user and stop here.

## Log
- T00: uv-managed venv (CPython 3.13.7), pyproject.toml (ruff+mypy strict+pytest+pytest-cov), src/tonofdevelopervoice package, scripts/coverage_gate.py, one scaffolding test. Baseline: ruff/mypy/pytest all clean pre-existing (fresh repo, nothing to break); coverage floor set to 100.00% (trivial __init__.py, single covered line) via `.coverage-gate.json`. Gitignored .coverage/coverage.xml/.pytest_cache/.ruff_cache/.mypy_cache.
- T01-T06 (Part 1 research, delegated to web-researcher/researcher subagents, one doc per topic): frameworks.md (Unsloth over Soup — Soup's recent silent-correctness bug history), base-models.md (Qwen3-8B-Base, fallback Mistral-3-8B), training-approach.md (SFT on LLM-synthesized paired data, STRAP-style, not plain LM continuation or standalone DPO), data-collection.md (git clone+log mining primary, GitHub GraphQL API for PR text secondary, GH Archive/BigQuery skipped), evaluation.md (6-part automated report: MiniLM similarity, BERTScore, validated style classifier, GPT-2 perplexity, forced-choice LLM-judge, optional MAUVE), SUMMARY.md consolidating all five with one `## Decision: <Topic>` each. PROJECT.md/AGENTS.md updated for the Soup->Unsloth pivot. All research verify commands green (file exists + `## Decision` section present).
- T13: `tonofdevelopervoice.web.app` — Flask (added as a dependency; picked over FastAPI for the "maximally primitive" two-panel form the user asked for). One route, GET/POST `/`, Jinja auto-escaping confirmed via an XSS test. Wired against `InferenceBackend` (stub for now). Verified with the real dev server (not just pytest's test client): started it, curled GET (renders empty two-panel form) and POST (returns the rewritten text). AC7 satisfied. Gate green, coverage floor held at 100.00% (65 tests).
- T12: `tonofdevelopervoice.cli` — `--text`/`--file`/stdin input (mutually exclusive text/file), empty-input and missing-file error handling, uses `InferenceBackend` (currently `StubInferenceBackend`, swapped to the real one in T14). Added `[tool.coverage.report] exclude_lines` for the `__main__` guard (standard, not test-worthy). Smoke-tested all three input modes via actual `python3 -m tonofdevelopervoice.cli` invocations, not just pytest. AC6 satisfied. Gate green, coverage floor held at 100.00% (60 tests).
- T11: `tonofdevelopervoice.serve.backend` — `InferenceBackend` (runtime_checkable Protocol, one method `rewrite(text) -> str`) and `StubInferenceBackend` for CLI/web tests. Gate green, coverage floor held at 100.00% (53 tests).
- T10: added `pyyaml`/`types-pyyaml` deps; `tonofdevelopervoice.train.config` (structural TrainingConfig validator, pure Python, no `unsloth` import, tested red-first, 10 tests). `training/config.yaml` (Qwen3-8B-Base, r=16/alpha=32/dropout=0.05, lr=2e-4, 3 epochs — per T02/T03), `training/train.py` (Unsloth+trl SFT script, host-only) and `training/requirements.txt`. Added `exclude = ["^training/"]` to `[tool.mypy]` since `mypy .` (the gate command) walks directories regardless of the `files` list and was otherwise failing on `training/train.py`'s unsloth/trl/datasets imports, which only exist on the host. `docs/runbook-training.md` covers the Blackwell/CUDA-12.8/WSL2 setup from `frameworks.md`'s hardware note, syncing the repo, installing deps, and running training. AC5 verified. Gate green, coverage floor held at 100.00% (49 tests).
- T09: `tonofdevelopervoice.dataset.assemble` (load_raw_records, dedup_records, split_train_eval — deterministic hash-of-sha bucketing so eval-set membership is stable as new records are appended later, Synthesizer protocol + PrecomputedSynthesizer, build_pairs producing the `{input, output, project}` schema from `training-approach.md`). Tests written red-first (ModuleNotFoundError confirmed), 12 tests green. Real pilot data: sampled 100 records across all five repos, delegated synthesis of genuine AI-ish "before" text to a fresh subagent (verified by directly reading its output, not just trusting its report — sha order matched, all non-empty, spot-checked content quality), assembled into `data/dataset/train.jsonl` (87) / `data/dataset/eval.jsonl` (13) via the real pipeline. Full-scale synthesis across all ~4500 collected records is left as follow-up (would need either much larger subagent budget or a locally/API-hosted LLM — out of this plan's scope per the priority decision to get the CLI working first). Gate green, coverage floor held at 100.00% (39 tests before this note; +12 from T09).
- T08: added `tonofdevelopervoice.collect.manifest` (build_manifest/write_manifest, tested) and `scripts/build_manifest.py`. Ran `scripts/collect.py` for postgres/postgres, nginx/nginx, apache/httpd, mysql/mysql-server (10 pages/1000 commits each, same GitHub-API bounded approach as T07's pilot) into `data/raw/{postgresql,nginx,apache,mysql}.jsonl`, then built `data/manifest.json` via the script: apache 1000, linux 500, mysql 1000, nginx 1000, postgresql 1000 — AC4 satisfied. Gate green, coverage floor held at 100.00% (27 tests).
- T07: `tonofdevelopervoice.collect` package — `filters.py` (pure: AI co-author trailer regex, pre-2021 author-date cutoff, suspicious-rewrite check using commit_date>=2023 rather than a day-gap, since kernel-style maintainer trees legitimately delay commits by months), `github_api.py` (paginated GitHub REST commits client, stdlib urllib, no new dependency), `pipeline.py` (parse/filter/write JSONL), `env.py` (minimal `.env` loader). Tests written red-first (ModuleNotFoundError confirmed before implementing), then green: 24 tests, coverage floor held at 100.00%. Ran the actual pilot via `scripts/collect.py --repo torvalds/linux --max-pages 5` using `GITHUB_TOKEN` from `.env`: wrote 500 real pre-2021 kernel commit records to `data/raw/linux.jsonl` (author dates 2020-07-30..2020-12-31) — AC3 satisfied. Used the GitHub API (not a full git clone) for this bounded pilot for speed; T08 decides the approach for the full five-repo run.
