# NOTES — 20-corpus/02-pr-collector

Executed on MAC. Unblocked mid-session: `GITHUB_TOKEN` in `.env` was invalid earlier today
(see `tasks/05-scope/01-ledger-update` history and the memory note `env-token-shadowing`);
the owner replaced it. Re-verified via `load_dotenv()` + `GET /rate_limit` (never printed):
valid, 5000/5000 core, 30/30 search, authenticated as `alter`.

## What was built

- `collect/sources.py`: `PR_REPOS`, the 12 repos from `task.txt` SCOPE.
- `collect/http_retry.py` (new, shared): `fetch_with_retries()` — rate-limit sleep+retry,
  5xx retry+backoff, connection-level-error retry+backoff, and a `ThreadPoolExecutor`
  wall-clock cutoff independent of socket-level timeouts. Extracted out of
  `github_prs.py` once it became clear the same logic would be needed again for
  `collect/github_search.py`.
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
  resumable), then `sample_by_year_and_author()` down to `--target` (default 3000) into
  `data/raw_v2/prs/<name>.jsonl`; `MANIFEST.json` is rewritten after every repo, not only
  at the end, so a long multi-repo run leaves a valid partial manifest if interrupted.
- Tests: `tests/test_http_retry.py` (pure retry mechanics — mocks the `fetch` callable
  directly), `tests/test_sampling.py`, `tests/test_pr_collector.py` (PR-domain behaviour —
  mocks `urlopen`), `tests/test_collect_prs.py`.

## Three real bugs found by actually running this against GitHub, not by review

**1. `http.client.IncompleteRead` was not caught at all.** First real smoke run
(`--repos python/cpython --target 50`) died on `IncompleteRead(1418794 bytes read, 25700
more expected)` — a connection-level truncation, not an HTTP status, so it skipped past
`except urllib.error.HTTPError` entirely (confirmed:
`issubclass(http.client.IncompleteRead, urllib.error.URLError)` is `False`, same for
`OSError`). Fixed in `http_retry.fetch_with_retries`: also catches
`(urllib.error.URLError, http.client.HTTPException, TimeoutError)` with the same backoff.
Tests seen red before the fix.

**2. A socket-level `timeout=` does not bound total request time.** After fix 1, a real
full run stalled again: `lsof` showed one TCP connection `ESTABLISHED` to GitHub for 3+
minutes with the candidates file completely stopped advancing, despite
`urlopen(request, timeout=45)` being in place — the same symptom class already documented
in `docs/plans/tonofdevelopervoice-v1.md` (llama-server and Unsloth's `hf_xet` downloader
both hung on an ESTAB socket with a per-call timeout that never fired, because the data was
trickling in slowly enough to keep resetting the per-`recv()` timer without the *overall*
request ever finishing). Applied that plan log's own fix: "a hard wall-clock cutoff via
`ThreadPoolExecutor.result(timeout=...)`, independent of whatever urllib/socket-level
timeout misbehaved" — `http_retry.fetch_with_retries` submits the actual fetch to a
`ThreadPoolExecutor` and bounds it with `.result(timeout=request_timeout)` (default 60s)
regardless of what the socket is doing; `executor.shutdown(wait=False)` on generator close
so an abandoned slow thread never blocks the pipeline. Confirmed by running the real
collector against GitHub (not simulated) before and after.

**3. `load_candidates` used `str.splitlines()` on JSONL content — corrupts on a
Unicode line separator.** Discovered only after fixes 1-2 let a real run finish
`kubernetes/kubernetes` end to end (43575 candidates, 606 pages) and then crash in
`load_candidates` with `json.decoder.JSONDecodeError: Unterminated string`. Root-caused
with evidence, not guessed: `text.split("\n")` gave 43576 pieces, `text.splitlines()` gave
43577 — a diff of exactly one, and scanning the text for
`unicodedata.category(ch) in ("Zl", "Zp")` or NEL/FS/GS/RS control chars found exactly one
`U+2028` (LINE SEPARATOR), almost certainly pasted into a real PR body. `str.splitlines()`
breaks on `U+2028`/`U+2029`/NEL/etc. in addition to `\n`/`\r`; `json.dumps(...,
ensure_ascii=False)` does not escape those characters (the JSON spec only requires
escaping the ASCII control range plus `"`/`\`), so one PR's JSON line got cut into two
invalid fragments. Fixed: `load_candidates` now splits strictly on `"\n"`. Verified against
the real corrupted file after the fix: `load_candidates(".../kubernetes.jsonl")` →
43575/43575 records, all unique ids, zero errors. Test
(`test_load_candidates_survives_a_unicode_line_separator_inside_a_field`) seen red first,
reproducing the exact `JSONDecodeError` from the real file with a synthetic `U+2028`.
`grep -rn "\.splitlines()" src/ scripts/` shows one more occurrence
(`src/tonofdevelopervoice/env.py`, for `.env` `KEY=VALUE` lines) — lower risk (not JSONL,
values rarely contain exotic Unicode) and out of this task's scope; not touched.

## Gate

`ruff check .` / `mypy .` / `pytest` / `coverage_gate.py --run` (which measures `--cov=src`
only — `scripts/` is not gated, matching the existing precedent for
`scripts/batch_rewrite.py`'s untested `main()`): all exit 0. 173 tests, coverage 100.00%
meets the floor 100.00%.

## VERIFY

1. Gate green (above).
2. `grep -rn "ghp_\|github_pat_" data/raw_v2 tasks/20-corpus` — the only hit is
   `tasks/20-corpus/02-pr-collector/task.txt:37`, which is this very check's own
   documentation quoting the pattern, not a leaked token. No real token anywhere in
   `data/raw_v2` or `tasks/20-corpus`.
3. Reverse control: in a scratch copy (`.claude/scratch/rev-control-02/`, removed after
   capture) with the `merged_at` check deleted from `is_valid_pull_request`:
   ```
   test_is_valid_pull_request_rejects_unmerged: FAILED (expected) -> got True, wanted False
   ```
4. **NOT DONE (data collection still running).** Total-records and max-author_date checks
   from `task.txt` VERIFY item 2 need the finished `data/raw_v2/prs/*.jsonl` +
   `MANIFEST.json` for all 12 repos, which is a genuinely long-running job (see below).

## Real collection run — in progress, backgrounded

Launched detached (`nohup ... &`, `disown`) on MAC, relaunched twice more after fixes 2 and
3 (each earlier attempt's partial `.candidates/` progress was kept and resumed cleanly —
that's exactly what the checkpoint mechanism and the fix-3 dedup are for):
`uv run python scripts/collect_prs.py --out-dir data/raw_v2/prs --target 3000`, log at
`.claude/scratch/collect_prs_full_run.log`. `PR_REPOS` order starts with
`kubernetes/kubernetes` (fully collected: 43575 candidates, 606 pages — the biggest repo in
the list by far) then `rust-lang/rust`. `python/cpython` was smoke-tested earlier in
isolation and has a stale partial checkpoint (3464 candidates, page 50) that the full run
will resume correctly when it reaches cpython (10th in `PR_REPOS`).

**To check progress:** `cat data/raw_v2/prs/MANIFEST.json` for repos already finished
(written incrementally after each repo), or `wc -l data/raw_v2/prs/.candidates/*.jsonl` for
the repo currently in flight. `ps aux | grep collect_prs` to confirm it's still alive.

**To finish this task once the run completes:** re-run `task.txt` VERIFY item 2 (total
records ≥ 20000, max `author_date` < 2021-01-01, zero `[bot]`-login records — a one-line
Python command over `data/raw_v2/prs/*.jsonl`), append the numbers here under `## After`,
copy the final `MANIFEST.json` into this task directory, set `labels.txt` `status:done`.

## Status

`labels.txt` set to `status:in_progress`: code complete, tested, gate green, three real
bugs found and fixed with evidence from actually running it, reverse control done — but
`OUTCOME` (`data/raw_v2/prs/*.jsonl` + `MANIFEST.json`, ≥20000 records total) does not
exist yet because the collection run needs real wall-clock time against the live GitHub
API. Not `blocked`: nothing is missing, it is simply still running.
