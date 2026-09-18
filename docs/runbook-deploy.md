# Deployment runbook (5090 host)

End-to-end: get this repo, its data, and its trained model running on the 5090 host, then
serve the CLI and web form against the real model. This session has no SSH/remote access
to that host — every step below is manual, run by the owner.

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

The pilot dataset built by this session is small (87 train / 13 eval — see
`docs/plans/tonofdevelopervoice-v1.md` T09's `## Log`) and was chosen deliberately small
to prove the pipeline, not for a production-quality fine-tune. Scale it up (more real
records collected, more synthetic pairs generated per
`docs/research/training-approach.md`) before training the model this deployment serves.

## 4. Train

`docs/runbook-training.md` §5: `python3 training/train.py`, reading `training/config.yaml`,
writing the adapter to `training/output/`.

## 5. Evaluate (optional but recommended before serving)

`docs/runbook-training.md` §6: generate `{source, model_output, reference}` triples by
running the trained model over `data/dataset/eval.jsonl`'s inputs, then

```
python3 scripts/evaluate.py --eval-file <generated triples> \
  --train-file data/dataset/train.jsonl --out data/dataset/eval_report.json
```

## 6. Serve the CLI and web form against the real model

Set `TONOFDEVELOPERVOICE_MODEL_DIR` to the trained adapter's path
(`tonofdevelopervoice.serve.factory.default_backend` picks `UnslothInferenceBackend` over
the stub when this is set — no source change needed):

```
export TONOFDEVELOPERVOICE_MODEL_DIR=training/output
```

CLI:

```
python3 -m tonofdevelopervoice.cli --text "some AI-generated commit message"
python3 -m tonofdevelopervoice.cli --file some_file.txt
echo "some text" | python3 -m tonofdevelopervoice.cli
```

Web form (development server — `flask.Flask.run`'s default; for anything longer-lived
than an ad hoc check, put a production WSGI server, e.g. `gunicorn`, in front of
`tonofdevelopervoice.web.app:create_app()` instead, which is out of scope for this v1
plan):

```
python3 -m tonofdevelopervoice.web.app
```

Then open the printed URL (default `http://127.0.0.1:5000/`) — paste text on the left,
the rewritten output appears on the right after submitting.

## What this session could not do

Per `docs/plans/tonofdevelopervoice-v1.md` T17 (`[!] BLOCKED`): this session has no
SSH/remote access to the 5090 host, so it never actually ran steps 4-6 above — it wrote
the code, the config, and this runbook, and verified everything it could locally (unit
tests, mocked-import construction/generation logic, the CLI/web form running against the
stub backend). Running the real fine-tune, the real evaluation, and confirming the
real-model-backed CLI/web form work end to end are the parts only the owner can do here.
