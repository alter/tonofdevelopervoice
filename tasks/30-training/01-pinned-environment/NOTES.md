# NOTES — 30-training/01-pinned-environment

## 2026-09-19

**Truth read first** (SCOPE): `~/.venvs/tonofdevelopervoice-train/bin/pip freeze` on
HOST, saved verbatim as `training/requirements.lock` (114 packages — this venv also
carries `flask`/`huggingface_hub`/`hf_transfer`/`hf-xet` from earlier same-session work
on `training/export.py` and manual web-form checks; kept in the lock as an honest
snapshot rather than trimmed to a guess at "only what v1 training needed").

`training/requirements.txt` curated from that freeze: the packages SCOPE names (`torch`,
`torchvision`, `unsloth`, `unsloth_zoo`, `trl`, `peft`, `bitsandbytes`, `datasets`,
`tokenizers`, `accelerate`, `pyyaml`, the evaluation packages) plus `huggingface_hub`,
added beyond the literal SCOPE list because `training/export.py`
(`10-serving/01-merged-export`, same day) imports it directly (`HfApi`,
`model_info`) — pinning a package a real script under `training/` imports is the same
reasoning SCOPE already applies to the others, not a new category of dependency.

**VERIFY 1** — `grep -vc "==" training/requirements.txt` → `0`. Every line pinned.

**VERIFY 2** — `python3 training/check_env.py` on HOST:
```
environment OK
```
Exit 0.

**VERIFY 3 — reverse control.** Copied `requirements.txt` to
`.claude/scratch/requirements_bad.txt`, changed `torch==2.11.0+cu128` to
`torch==9.9.9+cu128`, ran against that copy:
```
$ python3 training/check_env.py .claude/scratch/requirements_bad.txt
FAIL: torch: installed 2.11.0+cu128, expected 9.9.9+cu128
```
Exit 1, names the exact package and both versions. Scratch file removed after.

**VERIFY 4** — `ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run`
exits 0 (see commit's gate run; `training/` stays excluded from mypy/coverage per
`pyproject.toml`, unchanged by this task).

**docs/runbook-training.md §3 updated**: installs `torch`/`torchvision` from the
`cu128` index at the exact pins now in `requirements.txt` *before*
`pip install -r training/requirements.txt`, so the earlier workaround (install plain
torchvision from PyPI, then force-reinstall it from `cu128`) is no longer needed — both
steps now request the identical pin, so the second install is a no-op instead of a
required fix. Added the `check_env.py` invocation as the final setup step.
