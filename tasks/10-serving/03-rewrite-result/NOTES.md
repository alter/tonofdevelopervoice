# NOTES — 10-serving/03-rewrite-result

Executed on MAC in the same session as `05-scope/01-ledger-update`, without a separate
`/plan` interview: `task.txt` SCOPE is fully prescriptive (exact dataclass fields, exact
caller list), and the owner asked to push everything doable on the Mac in one pass.

## What was built

- `serve/backend.py`: `RewriteResult` (frozen dataclass, `finish_reason: Literal["stop",
  "length", "input_too_long"]`); `InferenceBackend.rewrite()` now returns it;
  `StubInferenceBackend` reports whitespace token counts, `finish_reason="stop"`.
- `serve/generation.py` (new): `GenerationSettings`, `completion_budget()`.
- `serve/unsloth_backend.py` / `serve/peft_backend.py`: token budget from
  `completion_budget()` instead of a fixed `max_new_tokens=256`; refuse (`"input_too_long"`,
  empty text, no `generate()` call) when the prompt exceeds `max_prompt_tokens`; decode only
  the new token ids (`output_ids[0][prompt_tokens:]`) instead of slicing the decoded string.
- `cli.py`: prints `result.text`; exit code 2 and a stderr line when `finish_reason !=
  "stop"`.
- `web/app.py`: passes `finish_reason` to the template; a banner shows when it isn't
  `"stop"` (no wording assertion added for it — AGENTS.md: never assert wording/layout).
- `scripts/batch_rewrite.py`, `scripts/generate_eval_outputs.py`: adapted to `.text` only,
  as scoped (their real rework is `10-serving/05-batch-rewrite`).
- Tests: new `tests/test_generation.py`; `tests/test_inference_backend.py`,
  `tests/test_unsloth_backend.py`, `tests/test_peft_backend.py`, `tests/test_cli.py`,
  `tests/test_web.py` updated to the new contract (`.text`/`.finish_reason` instead of a
  bare string; `FakeEncoding` now holds real nested lists instead of `MagicMock`, so
  `len(inputs["input_ids"][0])` and slicing behave like a real tensor).

## Gate

`ruff check .` / `mypy .` / `pytest` / `coverage_gate.py --run`: all exit 0. 125 tests
(was 115 before this task), coverage 100.00% meets the floor 100.00%.

## OUTCOME check

`grep -rn "max_new_tokens: int = 256" src/` — no output.

## VERIFY

1. Gate green, coverage floor held (see above).
2. OUTCOME grep — empty, confirmed above.
3. `echo hello | uv run python -m tonofdevelopervoice.cli; echo $?`:
   ```
   WARNING: TONOFDEVELOPERVOICE_MODEL_DIR is not set — using StubInferenceBackend, ...
   [rewritten] hello
   exit=0
   ```
4. Reverse control (both executed against scratch copies in
   `.claude/scratch/rev-control-03/`, not the real source):
   - `generation_broken.py`: `completion_budget()` hard-coded to return `256`. Running the
     three `test_generation.py` assertions against it:
     ```
     test_completion_budget_adds_margin_to_input_length: FAILED (expected) -> expected 164, got 256
     test_completion_budget_caps_at_max_completion_tokens: FAILED (expected) -> expected 200, got 256
     test_completion_budget_uses_default_settings_when_none_given: FAILED (expected) -> expected 74, got 256
     ```
   - `cli_broken.py`: `run()` always `return 0`, no `finish_reason` check. Running the two
     new CLI exit-code tests' logic against it:
     ```
     exit-code test for length: FAILED (expected) -> got 0, wanted 2
     exit-code test for input_too_long: FAILED (expected) -> got 0, wanted 2
     ```
   Scratch copies removed after capture (`.claude/scratch/` is gitignored and not part of
   the commit regardless).

## Not done here (scoped out, per task.txt `−` lines)

- MLX backend, deleting `peft_backend.py`: `10-serving/04-mlx-backend`.
- `batch_rewrite.py` resume/timing/report behaviour: `10-serving/05-batch-rewrite`.
- Tuning temperature/repetition penalty: `40-evaluation/02-shipped-path-eval`.
