# Deployment runbook (5090 host)

End-to-end: get this repo, its data, and its trained model running on the 5090 host, then
serve the CLI and web form against the real model. A session can also run directly on
that host itself (confirmed via `nvidia-smi`/`uname` — see
`docs/plans/tonofdevelopervoice-v1.md`'s 2026-09-18 log), in which case every step below
runs unattended instead of being handed off; it stays written as manual steps since that
won't always be true.

Steps 1-3 (sync, host environment, install training deps) and the training/evaluation
steps are the same as `docs/runbook-training.md` — this file adds what that one doesn't
cover: credentials for collection, running collection on the host if needed, and actually
serving the CLI/web form against the real model.

## 1. Sync and environment

Follow `docs/runbook-training.md` §1-3: Blackwell/CUDA-12.8/PyTorch-cu128 setup (or the
Unsloth Docker image), syncing the repo, and installing `training/requirements.txt` into
a Python 3.10-3.12 venv (`unsloth` requires it — do not reuse the Mac's `.venv`).

## 2. Credentials

Copy `.env` to the host (or set the variables directly in the host shell/systemd unit):

- `GITHUB_TOKEN` — used by `scripts/collect.py` and `tonofdevelopervoice.collect.github_api`
  for corpus collection (only needed if re-running or extending collection on this host;
  not needed just to train/serve an already-built dataset).
- `HF_TOKEN` — used implicitly by `transformers`/`unsloth` when downloading the base model
  (`Qwen/Qwen3-8B-Base` per `training/config.yaml`) and any Hugging Face Hub-hosted models
  in the evaluation metrics (MiniLM, GPT-2, BERTScore's default model).

`tonofdevelopervoice.env.load_dotenv()` reads `.env` the same way on the host as on the
Mac — no code changes needed, just make sure `.env` exists there.

## 3. Data

`data/` is gitignored and never synced by `git`. Either:
- copy `data/raw/*.jsonl`, `data/manifest.json`, `data/dataset/{train,eval}.jsonl` from
  the Mac to the host, or
- re-run collection directly on the host: `python3 scripts/collect.py --repo <owner/repo>
  --out data/raw/<name>.jsonl` per repo, `python3 scripts/build_manifest.py`, then
  `tonofdevelopervoice.dataset.assemble` to rebuild `data/dataset/{train,eval}.jsonl`.

The T09 pilot dataset (87 train / 13 eval, built on the Mac) was superseded on
2026-09-18 by a real-scale run directly on this host (T17): 5000 real commits collected
across all five repos, 600 synthesized pairs (550 train / 50 eval) via the host's local
`llama-server` OpenAI-compatible endpoint instead of subagent budget — see
`docs/plans/tonofdevelopervoice-v1.md` T17's `## Log`. 600 is still a first-pass scale,
not a production ceiling; growing it further (more of the ~4500 collected-but-unused
records synthesized) remains a valid follow-up.

## 4. Train

`docs/runbook-training.md` §5: `python3 training/train.py`, reading `training/config.yaml`,
writing the adapter to `training/output/`.

## 5. Evaluate (optional but recommended before serving)

`docs/runbook-training.md` §6, in full: generate `{source, model_output, reference}`
triples with `scripts/generate_eval_outputs.py`, filter the (usually rare) rows with an
empty `output`, then score with `scripts/evaluate.py`. The `HF_HUB_DISABLE_XET=1
HF_HUB_ENABLE_HF_TRANSFER=0` exports and `PYTHONPATH=src` prefix from that runbook's §5-6
apply here too — this venv's package can't be `pip install -e .`-ed (Python 3.10 vs.
`pyproject.toml`'s `requires-python = ">=3.11"`), and skipping the `HF_HUB_*` exports
risks the same silent-stall downloader bug documented there.

## 6. Serve the CLI and web form against the real model

Set `TONOFDEVELOPERVOICE_MODEL_DIR` to the trained adapter's path
(`tonofdevelopervoice.serve.factory.default_backend` picks `UnslothInferenceBackend` over
the stub when this is set — no source change needed). `flask` also needs installing into
this venv if training/evaluation deps only were installed per `runbook-training.md` §3 —
the web form's process needs both it and the real backend:

```
export TONOFDEVELOPERVOICE_MODEL_DIR=training/output
export HF_HUB_DISABLE_XET=1
export HF_HUB_ENABLE_HF_TRANSFER=0
pip install flask  # only if not already installed in this venv
```

CLI (`PYTHONPATH=src` needed for the same reason as step 5, since the CLI's own venv may
be the py3.10 training one rather than the Mac's installed-package venv):

```
PYTHONPATH=src python3 -m tonofdevelopervoice.cli --text "some AI-generated commit message"
PYTHONPATH=src python3 -m tonofdevelopervoice.cli --file some_file.txt
echo "some text" | PYTHONPATH=src python3 -m tonofdevelopervoice.cli
```

Web form (development server — `flask.Flask.run`'s default; for anything longer-lived
than an ad hoc check, put a production WSGI server, e.g. `gunicorn`, in front of
`tonofdevelopervoice.web.app:create_app()` instead, which is out of scope for this v1
plan):

```
PYTHONPATH=src python3 -m tonofdevelopervoice.web.app
```

Then open the printed URL (default `http://127.0.0.1:5000/`) — paste text on the left,
the rewritten output appears on the right after submitting. Confirmed end-to-end on
2026-09-18 (`docs/plans/tonofdevelopervoice-v1.md` T19's `## Log`): the CLI and web form
both rewrote verbose AI-style paragraphs into terse, target-style one-liners against the
real trained adapter.

If a `llama-server` (or similar) process was already running on this host and got
stopped to free VRAM for training (see T18/T19's log — this project's synthesis step in
T17 also depends on that same server being up), restart it with whatever command started
it originally before finishing up; this project doesn't own that process.
