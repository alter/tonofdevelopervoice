# Training runbook (5090 host)

This session has no SSH/remote access to the training host (Ubuntu under WSL2, 80GB RAM,
RTX 5090 32GB) — everything below is run manually there, per the T09/T10 decision in
`docs/plans/tonofdevelopervoice-v1.md`.

## 1. Host environment (Blackwell/RTX 5090 specifics)

Per `docs/research/frameworks.md`'s hardware note, the 5090 (compute capability sm_120)
needs, in order:

1. NVIDIA driver >= 570 (open kernel module variant).
2. CUDA Toolkit 12.8 — **do not** let `apt install nvidia-cuda-toolkit` pull the distro
   default (CUDA 12.0, predates Blackwell). Install 12.8 from NVIDIA's own repo/installer.
3. PyTorch >= 2.7.0 with the `cu128` wheel — earlier stable PyTorch has no pre-built
   sm_120 binaries:
   ```
   pip install torch --index-url https://download.pytorch.org/whl/cu128
   ```
4. WSL2 >= 2.7.0 (2.6.3 does not expose Blackwell's native FP8 tensor cores to compute
   workloads and falls back to FP16 emulation; 2.7.0 also fixed CUDA graph capture on the
   5090). Check from Windows: `wsl --version`.

Unsloth documents native Blackwell/RTX-50-series support with a ready-made Docker image
(`docs/research/frameworks.md`) — using that image is the lowest-friction path and
sidesteps most of the manual driver/CUDA/PyTorch version-matching above; use it if
available instead of a bare-metal setup.

## 2. Sync this repository to the host

From the Mac: `rsync -avz --exclude .venv --exclude data --exclude '*.jsonl' <repo path>/
<host>:~/tonofdevelopervoice/` (or `git clone` the remote directly on the host, then
`git pull` to stay current — either works; `data/` is gitignored, so the corpus/dataset
must be copied separately, see step 4).

## 3. Install training dependencies

On the host, in a Python 3.10-3.12 virtualenv (Unsloth's supported range; do not use the
Mac's `.venv`, which targets a different Python and has no CUDA deps):

```
python3 -m venv .venv-train
source .venv-train/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r training/requirements.txt
```

`training/requirements.txt` pulls in `torchvision` from the plain PyPI index, which is
ABI-incompatible with the `cu128` `torch` wheel above (`operator torchvision::nms does
not exist`, then a `transformers` import chain failure). Reinstall it from the matching
index right after:

```
pip install torchvision --index-url https://download.pytorch.org/whl/cu128 --force-reinstall --no-deps
```

Also install `flask` into this venv (only listed as a dependency for the Mac-side venv
in `pyproject.toml`) — the web form's process needs both it and the real
`UnslothInferenceBackend` together: `pip install flask`.

Since this venv's Python (3.10, required by Unsloth) doesn't satisfy this repo's
`pyproject.toml` `requires-python = ">=3.11"`, `pip install -e .` fails here — don't try
it. Instead export `PYTHONPATH=src` (from the repo root) whenever running a `scripts/*.py`
entry point (`train.py` itself already inserts `src` onto `sys.path` at import time, so
it doesn't need this) under this venv.

## 4. Provide credentials and data

- Copy `.env` (or just `HF_TOKEN`/`GITHUB_TOKEN`) to the host — `training/train.py` and
  any re-run of the collection scripts read them the same way as on the Mac
  (`tonofdevelopervoice.env.load_dotenv`).
- Copy `data/dataset/train.jsonl` and `data/dataset/eval.jsonl` from the Mac (or re-run
  collection/assembly directly on the host — both work, since `data/` is gitignored and
  never synced by git). The pilot dataset committed to history only as *counts* (via
  `## Log` in the plan) is 87 train / 13 eval records — small by design (see
  `docs/plans/tonofdevelopervoice-v1.md` T09's log); scale it up before a real training
  run by generating more synthetic pairs per `docs/research/training-approach.md` and
  re-running `tonofdevelopervoice.dataset.assemble`.

## 5. Run training

```
source .venv-train/bin/activate
export HF_HUB_DISABLE_XET=1
export HF_HUB_ENABLE_HF_TRANSFER=0
python3 training/train.py
```

The two `HF_HUB_*` exports are not optional on this host: Unsloth's "fast download"
path (`unsloth_zoo.hf_xet_fallback`) silently stalls on multi-GB files partway through
— the socket stays `ESTAB` with zero bytes flowing and no exception is ever raised, so
it looks like the run is just slow rather than stuck. It happened three times in one
session (the base model twice, `roberta-large` once in step 6) before these two env
vars were set, each time costing ~15-40 minutes before a manual kill+retry. With them
set, `huggingface_hub` falls back to its plain, reliable HTTP downloader. If a download
ever does stall despite this, killing and re-running is safe — completed files are kept
and only the interrupted one restarts (occasionally from 0 if the internal downloader
can't verify a partial file, per its own "unsafe partial" log line, but that's still a
finite retry, not a hang).

Reads `training/config.yaml` (base model, LoRA hyperparameters, dataset paths, output
dir — validated structurally on the Mac by `tonofdevelopervoice.train.config`, see AC5).
Writes the fine-tuned adapter to `training/output/` (gitignored — see `models/` in
`.gitignore`; move or rename `training/output` if it needs to live under one of the
already-ignored ML-artifact paths). Also writes `unsloth_compiled_cache/` into the repo
root (generated trainer code) — gitignored and excluded from `mypy`, but a
`ruff check .`/`mypy .` run from a very old checkout without those exclusions would
otherwise choke on it.

## 6. After training

- Generate rewrites for every `input` in `data/dataset/eval.jsonl` with the real
  trained model, writing `{source, model_output, reference}` triples (where
  `source`/`reference` are the eval row's `input`/`output`) to a JSONL file:
  ```
  export HF_HUB_DISABLE_XET=1
  export HF_HUB_ENABLE_HF_TRANSFER=0
  PYTHONPATH=src python3 scripts/generate_eval_outputs.py \
    --eval-file data/dataset/eval.jsonl --model-dir training/output \
    --out data/dataset/eval_generated.jsonl
  ```
  A handful of eval rows can have an empty `output` (upstream collection artifact, not
  a training bug — see `docs/plans/tonofdevelopervoice-v1.md` T19's log) — filter those
  out of the generated triples before scoring rather than retraining:
  ```
  python3 -c "
  import json
  with open('data/dataset/eval_generated.jsonl') as f, \
       open('data/dataset/eval_generated_filtered.jsonl', 'w') as out:
      for line in f:
          if json.loads(line)['reference'].strip():
              out.write(line)
  "
  ```
- Run the automated evaluation report (T15, metrics from `docs/research/evaluation.md`):
  ```
  PYTHONPATH=src python3 scripts/evaluate.py \
    --eval-file data/dataset/eval_generated_filtered.jsonl \
    --train-file data/dataset/train.jsonl \
    --out data/dataset/eval_report.json
  ```
  Needs `scikit-learn`, `sentence-transformers`, `bert-score`, `transformers` (all in
  `training/requirements.txt`, installed alongside the training deps in step 3) plus the
  `HF_HUB_*` exports from step 5 (this step downloads `roberta-large` and `gpt2`, which
  hit the exact same stall without them). `PYTHONPATH=src` is needed for the same reason
  as step 3 — this venv's package isn't `pip install -e .`-able. The forced-choice
  LLM-judge metric (`judge_win_rate`) is intentionally left `null` — no LLM-judge API key
  is configured for this project; see `tonofdevelopervoice.evaluate.judge.UnavailableJudge`
  to wire a real one if wanted.
- Exercise the CLI/web form (T12/T13) against the real model — see
  `docs/runbook-deploy.md` §6 for the exact commands.
