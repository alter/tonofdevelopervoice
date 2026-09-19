# NOTES — 10-serving/04-mlx-backend

Executed on MAC, same session as `03-rewrite-result`. `DEPENDS` (`10-serving/03-rewrite-result`)
was `status:done`, so the precondition for starting was met. `task.txt` DEPENDS prose also
flags that VERIFY items 3-4 need `10-serving/02-mlx-conversion` (a real MLX model
directory), which is a **HOST** task (`10-serving/01-merged-export` runs on HOST first) —
per `tasks/PROTOCOL.md` §3, work that needs the other machine is not simulated here. What
follows is everything doable without that artefact.

## What was built

- `serve/mlx_backend.py` (new): `MlxInferenceBackend`. Verified the `mlx_lm` 0.31.3 API
  directly against the installed package on this Mac before writing code (not from memory):
  `mlx_lm.load`, `mlx_lm.stream_generate`, `mlx_lm.sample_utils.{make_sampler,
  make_logits_processors}`, `GenerationResponse` dataclass fields (`text, token, logprobs,
  from_draft, prompt_tokens, prompt_tps, generation_tokens, generation_tps, peak_memory,
  finish_reason`, the last one `str | None` — only non-`None` on the final chunk), and that
  `TokenizerWrapper` forwards `.encode()` to the underlying HF tokenizer (source of
  `mlx_lm.tokenizer_utils.TokenizerWrapper`). `peak_memory` is already GB (`mlx_lm`'s own
  CLI prints it as `f"{response.peak_memory:.3f} GB"` verbatim — confirmed by reading
  `mlx_lm/generate.py`), so no unit conversion is applied.
- `serve/factory.py`: rewritten. `model_dir` is sniffed by content — `config.json` with a
  `"quantization"` key → `MlxInferenceBackend`; `adapter_config.json` → Unsloth if CUDA is
  available, else `RuntimeError` naming `docs/runbook-deploy.md`. `TONOFDEVELOPERVOICE_BACKEND`
  now accepts `"unsloth"` or `"mlx"` (was `"unsloth"`/`"peft"`); an unrecognised directory
  (neither shape) raises `ValueError` rather than silently falling back to anything.
- Deleted `serve/peft_backend.py` and `tests/test_peft_backend.py` outright (the fp16 path
  that caused ~48 s/token, audit S1).
- `tests/test_mlx_backend.py` (new, fake `mlx_lm`/`mlx_lm.sample_utils` in `sys.modules`):
  construction from `load`; joins streamed `.text` pieces; reports the *last* response's
  counters; passes `"length"` through; handles an empty generation stream; refuses
  over-budget input without calling `stream_generate` at all; satisfies `InferenceBackend`.
- `tests/test_backend_factory.py`: rewritten for the new directory-sniffing contract
  (fixtures build a real `adapter_config.json` / quantised `config.json` in `tmp_path`);
  covers the MLX pick, the explicit `"mlx"` override, the CUDA-unavailable `RuntimeError`,
  the unrecognised-directory `ValueError`, and an unparsable `config.json`.

## Gate

`ruff check .` / `mypy .` / `pytest` / `coverage_gate.py --run`: all exit 0. 129 tests (was
125 after `03-rewrite-result`), coverage 100.00% meets the floor 100.00%.

## VERIFY

1. Gate green (above).
2. `test ! -e src/tonofdevelopervoice/serve/peft_backend.py` → file absent, confirmed.
3. **NOT DONE.** The OUTCOME command needs
   `models/tonofdevelopervoice-qwen3-8b-v1-mlx-q4/` on this Mac, which needs
   `10-serving/01-merged-export` (HOST, `status:todo`) and then
   `10-serving/02-mlx-conversion` (MAC, `status:todo`, itself blocked on the export).
   Neither exists yet. This is the one piece left for the Ubuntu/5090 session (or a later
   Mac session once the export lands on the Hub).
4. Reverse control, run for real (not a scratch copy — this is the actual shipped code
   path, exercising the CUDA-unavailable branch, which needs no MLX model):
   ```
   $ time (TONOFDEVELOPERVOICE_MODEL_DIR=training/output uv run python -m tonofdevelopervoice.cli --text x); echo "exit=$?"
   RuntimeError: 'training/output' is a LoRA adapter that needs a CUDA/bitsandbytes host
   to run via Unsloth; on a Mac, use the MLX 4-bit model instead — see
   docs/runbook-deploy.md
   ( ... )  0.03s user 0.01s system 92% cpu 0.044 total
   exit=1
   ```
   0.044s wall time, no download, no `Qwen/Qwen3-8B-Base` load attempted — despite the
   `task.txt` DEPENDS prose listing this item alongside item 3, it turned out to need no
   MLX model at all (it only exercises the adapter-directory + no-CUDA branch), so it was
   run for real here rather than left pending.
5. Reverse control (scratch copy `.claude/scratch/rev-control-04/mlx_backend_broken.py`,
   `finish_reason` hard-coded to `"stop"`, removed after capture):
   ```
   test_rewrite_passes_length_finish_reason_through: FAILED (expected) -> got 'stop', wanted 'length'
   ```

## Not done here (scoped out or blocked)

- Item 3 above — needs HOST's `10-serving/01-merged-export` then this Mac's own
  `10-serving/02-mlx-conversion`. **Continue with those next** (in that order); once the
  MLX model directory exists, re-run the OUTCOME command, time it, and append the wall
  time + tokens/second here before setting `status:done`.
- `10-serving/02-mlx-conversion` itself (conversion script, dependency group): a separate
  task, not started.
- `batch_rewrite.py` behaviour: `10-serving/05-batch-rewrite` — also blocked, since its own
  `DEPENDS` (`10-serving/04-mlx-backend`) requires *this* task at `status:done`, which it
  is not yet.
- Keeping the model resident between CLI calls: out of scope per `task.txt` (`−` line).
  Load time itself could not be measured for real either, for the same reason as item 3.

## Status

`labels.txt` set to `status:in_progress`, not `done`: `OUTCOME`'s artefact (a real timed
run against a real MLX model) does not exist yet, and `PROTOCOL.md` §5 is explicit that
`status:done` means the OUTCOME artefact exists, nothing less. Not `status:blocked` either
— `DEPENDS` (`10-serving/03-rewrite-result`) *is* `status:done`, so this was not stopped at
the door; four of five VERIFY items are done and the remaining code is finished and tested,
only the cross-machine artefact is missing.
