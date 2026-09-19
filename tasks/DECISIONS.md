# Decisions

Cross-cutting decisions that belong to no single task. Recorded so they stop
being re-argued, and so that revisiting one is a deliberate act with a reason
rather than a drift.

Every entry: what was decided, when, why, and what was rejected. Where a number
appears it carries its source. Markers: **[already in the project]** — built,
decided earlier; **[owner]** — decided by the owner; **[agent]** — decided by the agent
under `docs/PROJECT.md` §4; **[proposed]** — waiting for the owner; ~~struck through~~ —
cancelled, with a date and a reason.

---

## D1. On the Mac the model runs as MLX 4-bit, in process — 2026-09-19 [owner]

**Decided.** The deployable artefact is the LoRA merged into the bf16 base and converted
with `mlx_lm` (pinned `mlx-lm==0.31.3`, `mlx==0.32.2`, the versions installed on the Mac
on 2026-09-19) to 4-bit, loaded inside the Python process by a new `MlxInferenceBackend`.

**Why.** 8.2B parameters at fp16 = ~16 GB on a 24 GB machine with <8 GB free → swap,
~48 s/token (audit S1). At 4 bits the weights are ~4.6 GB and fit. MLX is a library, not a
service, so the `docs/PROJECT.md` §4 rule "local services via Docker Compose" is not
touched (Docker on macOS cannot reach Metal anyway).

**Rejected.** GGUF + `llama-server` (one artefact for both hosts, but a native service to
run; the owner chose MLX). Ollama (less control over raw completion and finish reason).
fp16 PEFT on MPS (the current path; the cause of the problem). Unsloth's MLX route (fails
to load a bitsandbytes-trained adapter, `src/tonofdevelopervoice/serve/factory.py:30`).

## D2. A new collection is approved; the old corpus is kept — 2026-09-19 [owner]

**Decided.** Collection runs again, into `data/raw_v2/`. `data/raw/` and `data/dataset/`
are not deleted or overwritten. This is the approval `docs/PROJECT.md` §5 requires.

**Why.** The v1 corpus is the newest 1000 commits per repository, all from one year, with
no PR text (audit D1, D2).

**Rejected.** Cleaning the existing 5000 records only: ~3000 usable commits of one year
and still no PR-shaped target.

## D3. Real AI-written commit/PR text is collected for evaluation only — 2026-09-19 [owner]

**Decided.** Commits and PRs dated 2023 or later that carry an AI co-author trailer are
collected into `data/eval_real/` and used as evaluation **inputs**. They never enter a
training file; dataset assembly refuses them by construction and a test proves it.

**Why.** The v1 evaluation used only text made by the training synthesis prompt and
missed that the model copies real inputs (audit E2).

**Rejected.** Owner-supplied files plus held-out synthetic styles only — kept as part of
the evaluation, but too few real inputs on their own.

## D4. The task tree is written in English — 2026-09-19 [owner]

**Decided.** `tasks/` is in English, like the rest of `docs/`.

## D5. Gates are measured on the Mac through the shipped artefact — 2026-09-19 [agent]

**Decided.** Gate evaluation generates outputs on MAC with `MlxInferenceBackend` and the
exact 4-bit model directory the owner uses. HOST-side generation through Unsloth stays
available for quick looks and never feeds a gate.

**Why.** v1 evaluated Unsloth/bnb-4bit on CUDA while the Mac ran unmerged LoRA on fp16;
the numbers described a different system (audit S4, E4). With D1 there is no backend
shared by both hosts, so the gate follows the user.

**Rejected.** Evaluating on HOST for speed: ~800 inputs at ~20 s each is ~4.5 hours on the
Mac, unattended, which is affordable.

## D6. Base model stays Qwen3-8B-Base unless gate 1 says otherwise — 2026-09-19 [agent]

**Decided.** Keep `Qwen/Qwen3-8B-Base`. If `10-serving/06-mac-speed-gate` fails on speed
or memory, training run v2 uses `Qwen/Qwen3-4B-Base` instead and the gate is re-measured.

**Why.** The choice is made by a measurement on the owner's machine, not by a guess.
Expected for 8B at 4 bits on M2 (100 GB/s memory bandwidth, ~4.6 GB of weights): roughly
15-20 tokens/s — an estimate, to be replaced by the gate's number.

**Rejected.** Switching to 4B now without a measurement.

## D7. Loss on the completion only, EOS appended by our code — 2026-09-19 [agent]

**Decided.** Training rows are `{"prompt", "completion"}`; the completion ends with the
tokenizer's EOS token appended by `training/train.py`; loss is masked on prompt tokens. A
batch inspector proves both on real collated batches before any run.

**Why.** Audit T1, T2.

**Rejected.** Relying on TRL/Unsloth defaults for EOS — version-dependent and unverified.

## D8. Every artefact that must cross hosts travels through the Hugging Face Hub — 2026-09-19 [agent]

**Decided.** Not only the merged bf16 model and the MLX 4-bit model (publishing weights is
authorised in `docs/PROJECT.md` §5) — the collected corpus (`data/raw_v2/`) and the
evaluation-only real-AI-text sets (`data/eval_real/`) travel the same way: a private Hub
**dataset** repo per artefact (`tonofdevelopervoice-corpus-v2`,
`tonofdevelopervoice-eval-sets`), uploaded from whichever host collected it, downloaded on
whichever host needs it next. The Mac downloads the MLX model from there. The v1 adapter
stays in Git LFS at `training/output/`; new runs write to `training/runs/<run-id>/`
(gitignored).

**Why.** `data/` and `models/` are not synchronised between hosts (`.gitignore` excludes
`data/` from git entirely, on purpose — corpus stays local, only the one already-published
adapter went through Git LFS, by direct owner request, and that is not a general pattern
for this project) and files this size do not belong in Git LFS as a rule. A manifest with
sha256 in the task directory ties each artefact to its run.

**Rejected.** Git LFS as the general transport (right for one already-published ~175 MB
adapter by direct request; wrong for a corpus that will only grow across re-runs — every
version stays in git history forever under LFS, which `.gitignore`'s own comment already
rules out for `data/`). `scp`/`rsync` between hosts (no SSH path exists between the agent's
Mac and HOST sessions, `docs/plans/tonofdevelopervoice-v1.md:325` — though the owner could
set this up by hand outside any task; not relied on here since it isn't in place).

## D9. `HF_TOKEN` in `.env` is read-only; every Hub upload is blocked until it is replaced — 2026-09-19 [agent, found, not decided]

**Found, not a decision to record and move past** — a live blocker for D8. Checked the same
way `GITHUB_TOKEN` was checked (`load_dotenv()` + a real API call, never trusting an
ambient shell export or assuming): `GET /api/whoami-v2` returns `"auth": {"accessToken":
{"displayName": "public_read", "role": "read"}}` — a token created for downloading public
models, not for writing. Every Hub upload D8 depends on (corpus, eval sets, trained
weights) fails with this token: `hf upload ...` needs `role: write` (or higher) on the
target repo.

**What is needed:** the owner creates a new Hub access token with **Write** scope
(huggingface.co → Settings → Access Tokens) and puts it in `.env` — either replacing
`HF_TOKEN` or as a second variable (e.g. `HF_TOKEN_WRITE`) if the read-only one is still
wanted for downloads elsewhere. Until then, any task whose OUTCOME needs a Hub upload
(`20-corpus/02-pr-collector`'s corpus transport, `20-corpus/04-ai-eval-inputs`'s Hub step,
`10-serving/01-merged-export`, `10-serving/02-mlx-conversion`) stops at that step with
`[!] BLOCKED: missing a write-scoped HF_TOKEN` — this is a missing credential per
`tasks/PROTOCOL.md` §6, not something to work around.
