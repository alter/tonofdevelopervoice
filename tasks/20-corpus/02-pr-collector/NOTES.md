# NOTES — 20-corpus/02-pr-collector

Executed on MAC. Unblocked mid-session: `GITHUB_TOKEN` in `.env` was invalid earlier today
(see `tasks/05-scope/01-ledger-update` history and the memory note `env-token-shadowing`);
the owner replaced it. Re-verified via `load_dotenv()` + `GET /rate_limit` (never printed):
valid, 5000/5000 core, 30/30 search, authenticated as `alter`.

## What was built

- `collect/sources.py`: `PR_REPOS`, the 12 repos from `task.txt` SCOPE.
- `collect/http_retry.py` (new, shared with `20-corpus/04-ai-eval-inputs`):
  `fetch_with_retries()` — primary rate-limit sleep+retry, GitHub's *secondary* rate limit
  (found while building `04-ai-eval-inputs`, added here too since both modules share the
  function), 5xx retry+backoff, connection-level-error retry+backoff, and a
  `ThreadPoolExecutor` wall-clock cutoff independent of socket-level timeouts.
- `collect/sampling.py` (shared): `sample_by_year_and_author()` — equal quota per
  calendar year with redistribution of a thin year's unused quota, deterministic
  hash-of-id ordering within a year, a 2%-of-target author cap. `task.txt` says "same
  sampling rule as `20-corpus/01-git-history-collector`" and 01 doesn't exist yet — when
  it's built (on HOST), it should import this instead of re-implementing it.
- `collect/github_prs.py`: `fetch_pull_requests()` (pages `GET /repos/{repo}/pulls`
  ascending by `created_at`, stops at the first PR at/after the cutoff — mid-page, not
  only on a short page; retries via `http_retry`); `is_valid_pull_request()` /
  `parse_pull_request()` / `filter_pull_requests()` (merged, pre-2021, human, non-bot,
  non-AI-co-authored, non-empty body; reuses `collect.filters.{CUTOFF,has_ai_co_author}`).
- `scripts/collect_prs.py`: per-repo candidate collection to
  `data/raw_v2/prs/.candidates/<name>.jsonl` + `<name>.checkpoint.json` (append-only,
  resumable), then `sample_by_year_and_author()` down to `--target` (3000) into
  `data/raw_v2/prs/<name>.jsonl`; `MANIFEST.json` rewritten after every repo.
- Tests: `tests/test_http_retry.py`, `tests/test_sampling.py`, `tests/test_pr_collector.py`,
  `tests/test_collect_prs.py`.

## Four real bugs found by actually running this against GitHub, not by review

**1. `http.client.IncompleteRead` was not caught at all** (first smoke run). **2. A
socket-level `timeout=` does not bound total request time** against a slowly dribbling
response (first full run) — both fixed with `http_retry.fetch_with_retries`'s
`ThreadPoolExecutor` wall-clock cutoff, the same pattern already used in
`scripts/synthesize.py` and documented in `docs/plans/tonofdevelopervoice-v1.md` for the
identical symptom class. **3. `load_candidates` used `str.splitlines()` on JSONL
content** — breaks on a `U+2028` (LINE SEPARATOR) that `json.dumps(...,
ensure_ascii=False)` does not escape; one real `kubernetes/kubernetes` PR body contained
one, corrupting exactly one line into two invalid fragments once written and reloaded.
Fixed: split strictly on `"\n"`. All three documented in detail (root cause with
evidence, red-first tests, and the reverse control) in earlier revisions of this file —
see git history (`27b7eec`, `06a8788`, `fa0a6fc`) — kept short here since the fixes are
already in `src/` and covered by tests.

**4. The retry budget (3 attempts) was exhausted by a real, unlucky run of consecutive
`IncompleteRead`s** on `etcd-io/etcd`, mid-run, after 8 repos had already completed
cleanly:
```
RuntimeError: GitHub API request failed: IncompleteRead(1482434 bytes read, 37433 more expected)
```
This is not a bug — `fetch_with_retries` caught and retried it exactly as designed (3
attempts, exponential backoff) and correctly gave up and raised on the 4th. The checkpoint
(`data/raw_v2/prs/.candidates/etcd.checkpoint.json`, page 19, 1017 candidates) was intact;
restarting the same command resumed etcd from there and finished the remaining 4 repos
(etcd, cpython, pandas, salt) without further incident. No code change was needed — the
checkpoint/resume design this task built for exactly this scenario did its job. Left
`max_transient_attempts` at 3 (its default): raising it on the strength of one unlucky
streak would be tuning a check to a single data point, not evidence of it being
systematically too low.

## Gate

`ruff check .` / `mypy .` / `pytest` / `coverage_gate.py --run` (which measures `--cov=src`
only — `scripts/` is not gated, matching the existing precedent for
`scripts/batch_rewrite.py`'s untested `main()`): all exit 0. 208 tests, coverage 100.00%
meets the floor 100.00%.

## VERIFY

1. Gate green (above).
2. Recomputed from all 13 `data/raw_v2/prs/*.jsonl` files:
   - total records: **32709** (≥ 20000 required)
   - max `author_date`: **2020-12-31T17:28:16Z** (< 2021-01-01)
   - records with a `"[bot]"` login fragment surfacing in the stored text: **0**
   - per-repo counts and year histograms: `tasks/20-corpus/02-pr-collector/MANIFEST.json`
     (copied from `data/raw_v2/prs/MANIFEST.json`); every repo's `largest_author_share`
     is at or under the 2% cap.
3. `grep -rn "ghp_\|github_pat_" data/raw_v2 tasks/20-corpus` — the only hits are this
   check's own documentation (`task.txt:37,39`), never a real token.
4. Reverse control: in a scratch copy (`.claude/scratch/rev-control-02/`, removed after
   capture) with the `merged_at` check deleted from `is_valid_pull_request`:
   ```
   test_is_valid_pull_request_rejects_unmerged: FAILED (expected) -> got True, wanted False
   ```
5. From a clean scratch directory (`.claude/scratch/hub-verify-corpus/`, removed after
   capture): `hf download alterpub/tonofdevelopervoice-corpus-v2 --repo-type dataset
   --local-dir ...` then sha256 of all 13 downloaded files (12 repo `.jsonl` +
   `MANIFEST.json`) against the local copies in `data/raw_v2/prs/` — **all 13 matched
   exactly**, zero mismatches.

## Hub upload

Owner replaced `HF_TOKEN` with a write-scoped one (`tasks/DECISIONS.md` D9, resolved).
Re-verified via `load_dotenv()` + `GET /api/whoami-v2` (never trusting the shell):
`role: "write"`.

- `hf repo create alterpub/tonofdevelopervoice-corpus-v2 --type dataset --private --exist-ok`
  → `https://huggingface.co/datasets/alterpub/tonofdevelopervoice-corpus-v2`.
- Staged only the final sampled `data/raw_v2/prs/*.jsonl` + `MANIFEST.json` under a
  `prs/` subdirectory (never `.candidates/` — that pool is a local resume aid, not part
  of the artefact HOST needs, per `task.txt`'s `−` line) and uploaded: commit
  `d942dba0e10de26c27f8084daaedb0f8d7d2357a`.
- Verified from a clean download (VERIFY item 5 above).

To fetch on HOST for `20-corpus/03-text-cleaning`:
`hf download alterpub/tonofdevelopervoice-corpus-v2 --repo-type dataset --local-dir data/raw_v2`
(the repo's `prs/` subdirectory lands at `data/raw_v2/prs/` directly).

## Status

`labels.txt` set to `status:done`: `OUTCOME` fully exists — 32709 records across 12
`data/raw_v2/prs/*.jsonl` files (≥ 20000 required), `MANIFEST.json` copied into this task
directory, and the Hub dataset commit above, verified from a clean state.
`verify:passed` is left for `/verify` (another context), per `tasks/PROTOCOL.md` §5.
