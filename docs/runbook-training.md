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
python3 training/train.py
```

Reads `training/config.yaml` (base model, LoRA hyperparameters, dataset paths, output
dir — validated structurally on the Mac by `tonofdevelopervoice.train.config`, see AC5).
Writes the fine-tuned adapter to `training/output/` (gitignored — see `models/` in
`.gitignore`; move or rename `training/output` if it needs to live under one of the
already-ignored ML-artifact paths).

## 6. After training

- Wire `UnslothInferenceBackend("training/output")` (T14) in place of the CLI/web form's
  default `StubInferenceBackend`, and generate rewrites for every `input` in
  `data/dataset/eval.jsonl`, writing `{source, model_output, reference}` triples (where
  `source`/`reference` are the eval row's `input`/`output`) to a JSONL file, e.g.
  `data/dataset/eval_generated.jsonl` — this is the one step this session cannot do
  itself (needs the real trained model on this host).
- Run the automated evaluation report (T15, metrics from `docs/research/evaluation.md`):
  ```
  python3 scripts/evaluate.py \
    --eval-file data/dataset/eval_generated.jsonl \
    --train-file data/dataset/train.jsonl \
    --out data/dataset/eval_report.json
  ```
  Needs `scikit-learn`, `sentence-transformers`, `bert-score`, `transformers` (all in
  `training/requirements.txt`, installed alongside the training deps in step 3). The
  forced-choice LLM-judge metric (`judge_win_rate`) is intentionally left `null` — no
  LLM-judge API key is configured for this project; see
  `tonofdevelopervoice.evaluate.judge.UnavailableJudge` to wire a real one if wanted.
- Exercise the CLI/web form (T12/T13) against the real model — this is the other part of
  the plan this session cannot verify itself (see plan T17, `[!] BLOCKED`).
