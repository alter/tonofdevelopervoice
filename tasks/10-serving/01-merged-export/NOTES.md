# NOTES — 10-serving/01-merged-export

## 2026-09-19 — CONTEXT correction: peft_backend.py was deleted

CONTEXT names `src/tonofdevelopervoice/serve/peft_backend.py:37-39` as "the load
sequence to reuse". That file no longer exists (deleted in `10-serving/04-mlx-backend`,
commit `35e0f6a`). Read it from git history instead: `git show
29827b3:src/tonofdevelopervoice/serve/peft_backend.py`. The load sequence
(`AutoModelForCausalLM.from_pretrained(base, dtype=...)` then
`PeftModel.from_pretrained(base, adapter_dir)`) is unchanged from that version and is
what `training/export.py` reuses.

## 2026-09-19 — bfloat16 fails this task's own self-check; switched to float16

**What happened.** The self-check SCOPE requires (loading the base at bfloat16, per the
literal SCOPE line): `max|adapter-merged| < 0.05`. The real run measured **0.250000** —
5x over the threshold — and correctly failed (`self-check failed: merged model differs
from base+adapter`, exit 1). This is not a bug in the check: the check's logic itself
is correct (verified separately, see the "self-check ordering bug" entry below).

**Diagnosis, not a guess — three dtypes measured on the same prompt (first row of
`data/dataset/eval.jsonl`, `torch.no_grad()`, CPU):**

| dtype used for base+merge | max\|adapter−merged\| | max\|base−merged\| | passes 0.05? |
|---|---|---|---|
| bfloat16 (as SCOPE literally says) | 0.250000 | 19.750000 | **no** |
| bfloat16, but merge computed in fp32 then cast back to bf16 | 0.250000 | 19.718750 | **no** (identical — ruled out the merge arithmetic itself as the cause) |
| float16 | 0.039062 | 19.738281 | **yes**, margin ~22% |
| float32 | 0.000021 | 19.699783 | yes, trivially |

**Root cause, stated precisely:** rounding `W + delta` to bfloat16 (7 mantissa bits)
loses more precision than bfloat16's own forward-pass arithmetic for the *unmerged*
adapter path (which never has to round a summed weight into 7 mantissa bits — it keeps
`W` untouched and adds the LoRA contribution as a separate term at inference time). This
is a property of bfloat16 itself, not of how `merge_and_unload()` computes the sum: the
"merge in fp32, round to bf16 at the end" variant gave the identical 0.250000, which
rules out the arithmetic path and pins the cause on the final rounding step alone.
float16's 10 mantissa bits (vs. bfloat16's 7) are enough to keep that same rounding
under the threshold, confirmed above.

**Decision (agent, per `docs/PROJECT.md` §4 "library/tooling choice that doesn't change
scope or behavior, needed to make an existing check pass without weakening it"):**
`training/export.py` loads and merges at **float16**, not the bfloat16 the SCOPE line
literally names. The self-check's logic and its 0.05 threshold are untouched — this is
the PROTOCOL.md §3 case of a stale implementation detail contradicted by a real
measurement, corrected here rather than weakening the check itself. If the owner wants
bfloat16 specifically (e.g. because a downstream step assumes it), that is a fresh
instruction, not a re-run of this diagnosis: the measurements above will not change.

**Reverse control performed separately (does not depend on this dtype choice):** see
the next entry.

## 2026-09-19 — self-check ordering bug, fixed before the diagnosis above

First real run raised `ValueError: No adapter layers found in the model` inside
`peft_model.disable_adapter()`. Cause: `merge_and_unload()` was called *before* the
self-check, and it mutates `peft_model` in place, stripping its adapter layers — so
`disable_adapter()` has nothing left to disable. Fixed by computing the (a) base and (b)
base+adapter logits *before* `merge_and_unload()` (`pre_merge_logits()`), then merging,
then computing (c) merged logits (`compare_logits()`). This reordering is why
`run_self_check()` became two functions.

## 2026-09-19 — reverse control (VERIFY item 4)

Ran the real self-check logic against a scratch copy of `training/output` with every
`lora_B` tensor zeroed (zero `lora_B` ⇒ the LoRA delta is exactly zero ⇒ merging changes
nothing ⇒ merged model must equal base). Expected outcome per VERIFY item 4: exits
non-zero with "merged model equals base".

Command and full red output:

```
$ python3 -c "<zero every lora_B tensor in a scratch copy of training/output>"
wrote zeroed adapter to <scratch>/zeroed_adapter/adapter_model.safetensors

$ python3 training/export.py --adapter <scratch>/zeroed_adapter --out <tmp> --manifest <tmp>/EXPORT.json
loading base 'Qwen/Qwen3-8B-Base' at float16 on cpu...
loading adapter '<scratch>/zeroed_adapter'...
computing pre-merge logits (base, base+adapter)...
merging...
max|adapter-merged| = 0.000000 (require < 0.05)
max|base-merged|    = 0.000000 (require > 0.05)
self-check failed: merged model equals base
```

Exit code 1. Matches VERIFY item 4 exactly: the check turns red for the right reason
(base == merged, because the adapter's own delta was zeroed), not for an unrelated
reason.

## 2026-09-19 — network: this HOST resets long-lived HTTPS transfers mid-file

Both `https://hf-mirror.com` (this host's `~/.bashrc` default, `HF_ENDPOINT`) and the
official `https://huggingface.co` reset the connection repeatedly while downloading
`Qwen/Qwen3-8B-Base`'s ~4 GB shards (`peer closed connection ...` / `read operation
timed out`, dozens of times across a ~32-minute download of ~16 GB). `huggingface_hub`'s
built-in resume handled it without intervention — no code change, just patience. Noting
this because it is the same class of host-level connection instability documented in
`docs/plans/tonofdevelopervoice-v1.md`'s T17/T18 log (there as silent stalls via xet; here
as resets via the plain HTTP path), so a future task hitting a stalled/reset HF download
on this host should not assume something is broken — check whether the transfer is
still making net progress across resets before treating it as stuck.

## Status: OUTCOME not closed — blocked on write-scoped HF_TOKEN

Everything up to `save_pretrained(out)` is done and verified (self-check passes at
float16, reverse control is red for the right reason, gate is green). The task's
OUTCOME requires `tasks/10-serving/01-merged-export/EXPORT.json` to name **a Hub repo
and commit** — that needs `--push <repo>`, which needs a write-scoped `HF_TOKEN`.

Checked the same way `GITHUB_TOKEN` and D9 were checked before trusting it — a real
`GET /api/whoami-v2` call, not an assumption: **`role: "read"`**, `user: alterpub`. D9
recorded this token as fixed to `role: "write"` earlier the same day and even names two
uploads (`20-corpus/02-pr-collector`, `20-corpus/04-ai-eval-inputs`) that used it
successfully — so it was write-scoped at some point today and is read-only now. Nothing
in this task's session touched `.env`.

Per `tasks/PROTOCOL.md` §6 this is exactly "a missing secret is needed" — stopping here,
not simulating a push or writing a placeholder Hub repo id into EXPORT.json. See
`BLOCKED.md`.
