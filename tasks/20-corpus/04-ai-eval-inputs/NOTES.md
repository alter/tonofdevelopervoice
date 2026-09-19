# NOTES — 20-corpus/04-ai-eval-inputs

Executed on MAC, same session as `20-corpus/02-pr-collector` (which unblocked
`GITHUB_TOKEN`; see that task's NOTES.md and the memory note `env-token-shadowing`).

## What was built

- `evaluate/ai_inputs.py` (pure, unit-tested): `detect_agent()` (prefers the
  `Co-authored-by:` trailer via `collect.filters.AI_CO_AUTHOR_PATTERN`'s own capture
  group, falls back to a `"Generated with [Agent]"` / `"Generated with Agent"` marker);
  `strip_ai_markers()` (removes only the AI-matching trailer/marker lines, keeps
  everything else, including any genuine human co-author line); `is_eligible()` (date >=
  2023-01-01, length >= a per-source minimum, at least one AI marker present);
  `select_with_repo_cap()` (exact-text dedup + a per-repo cap); `parse_ai_commit()` /
  `parse_ai_pr()` (raw GitHub search result -> the `{id, source, repo, date, agent,
  text}` record shape).
- `collect/http_retry.py` (shared with `02-pr-collector`): extended with
  `is_secondary_rate_limited()` / `secondary_rate_limit_wait_seconds()` (see bug below).
- `collect/github_search.py`: `search(endpoint, query, token, ...)` — pages
  `GET /search/{commits,issues}`, capped at the API's own 1000-result limit, sleeps
  `request_interval` (2.1s) between full pages to stay under the 30/minute search quota,
  retries via `http_retry`.
- `scripts/collect_ai_eval_inputs.py` (thin): 7 agent families (Claude, Copilot, Cursor,
  Devin, aider, Codex, Gemini) x commits (`Co-authored-by:` query) and PRs
  (`Co-authored-by:` + one `"Generated with"` query), deduped by `sha`/`id` across
  queries, filtered + capped + target-trimmed, written to
  `data/eval_real/{ai_commits,ai_prs}.jsonl` + `MANIFEST.json` (counts per agent, min
  date, sha256 of both files).
- Tests: `tests/test_ai_inputs.py`, `tests/test_github_search.py`,
  `tests/test_collect_ai_eval_inputs.py`, plus the `http_retry` additions in
  `tests/test_http_retry.py`.

## A fourth real bug, found by actually running this against GitHub

**GitHub's *secondary* rate limit is a different signal from the primary one.** The very
first real request (`"Co-authored-by: Claude" committer-date:>2023-01-01`) came back
`403` with `x-ratelimit-remaining: 26` (of 30) — nowhere near exhausted — so
`http_retry.is_rate_limited` (which only checks `x-ratelimit-remaining == "0"`) did not
recognise it, and the run died immediately with an unhandled `RuntimeError`. A direct
manual request (outside any retry logic) confirmed the real signal: no `Retry-After`
header, but the JSON body's `message` field: *"You have exceeded a secondary rate limit.
Please wait a few minutes before you try again."* — GitHub's abuse/burst protection, not
the documented per-minute search quota. Root-caused before touching code: this was
triggered by my own rapid-fire manual diagnostic requests during debugging (confirmed —
once I stopped making manual probe requests and let the token sit for ~15 minutes, a
fresh request succeeded even with `20-corpus/02-pr-collector`'s background collection
still running full-tilt against the same token, ruling out that job as the cause).
`http_retry.fetch_with_retries` now also checks `is_secondary_rate_limited()` (a
`Retry-After` header, or the body message) and sleeps that duration (default 60s absent
both signals) before retrying — no attempt cap on this branch, matching the primary
rate-limit branch, since the condition is expected to clear on its own. Tests
(`test_fetch_with_retries_sleeps_for_the_retry_after_header_on_a_secondary_rate_limit`,
`..._sleeps_a_default_on_a_secondary_rate_limit_without_retry_after`) seen red before the
fix.

Practical lesson recorded here rather than relearned next session: **don't probe the
GitHub API manually, back-to-back, while diagnosing a rate-limit issue against it** — the
diagnostic bursts are exactly the pattern the secondary limit exists to catch, and they
make the very thing being diagnosed worse. Once real doubt about the query's correctness
arose (a `total_count` of 96 million looked like a broken query), a *single* manual
request with a real sleep beforehand was enough to check it: the returned commits
genuinely carried the `Co-authored-by: Claude` trailer — the huge `total_count` is a
known GitHub Search API quirk (a rough, often-inflated estimate for commit search, not an
exact count) and not a sign the query is wrong.

## Gate

`ruff check .` / `mypy .` / `pytest` / `coverage_gate.py --run`: all exit 0. 208 tests
(after this task's additions to `http_retry`), coverage 100.00% meets the floor 100.00%.

## VERIFY

1. Gate green (above).
2. **Pending** — needs the finished `data/eval_real/ai_commits.jsonl` /
   `ai_prs.jsonl` (real collection in progress, see below).
3. **Pending** — same reason; `sha256` values in `MANIFEST.json` will be checked against
   the files once the run finishes.
4. Reverse control: with `is_eligible`'s date check inverted (`date >= cutoff: return
   False` instead of `<`), tested against the genuine AI-commit fixture
   (`AI_COMMIT_MESSAGE`, long enough, carries the trailer) dated 2019 — the fixture must
   fail the check for the reverse control to be meaningful (a pre-2021 *human* commit
   fixture is overdetermined: it also fails on length and on having no AI marker at all,
   so inverting only the date condition would NOT turn that particular test red — caught
   this while executing the reverse control, not before, and added a second, isolated
   test — `test_is_eligible_rejects_otherwise_eligible_ai_text_dated_before_the_cutoff`
   — to the suite so a future date-check regression is actually caught):
   ```
   test_is_eligible_rejects_pre_2023_ai_text (date-isolated): FAILED (expected) -> got True, wanted False
   ```

## Real collection run — in progress, backgrounded

Launched detached (`nohup uv run python3 -u ... &`, `disown`) on MAC — `-u` (unbuffered)
so the log at `.claude/scratch/collect_ai_eval_inputs.log` shows progress in real time,
since the default buffered stdout made an earlier attempt look silently stuck when it
was not. Pace: roughly 1-4 minutes per query (7 commit + 8 PR queries), the variance
coming from how often the secondary rate limit's 60s backoff fires. Running concurrently
with `20-corpus/02-pr-collector`'s own background collection on the same token without
issue once the secondary-limit condition (caused by my earlier manual probing, not by
either collector) had cleared.

**To check progress:** `tail .claude/scratch/collect_ai_eval_inputs.log` (which query is
current), or once it finishes, `cat data/eval_real/MANIFEST.json`.

**To finish this task once the run completes:** re-run `task.txt` VERIFY items 2-3 (min
date, per-repo cap, no raw AI-pattern text left in the stored field, sha256 match), append
the numbers here under `## After`, copy `MANIFEST.json` into this task directory, upload
`data/eval_real/` (without `owner/`) to the private Hub dataset repo per `task.txt` SCOPE
(not done yet — needs `HF_TOKEN`; check it the same way `GITHUB_TOKEN` was checked, via
`load_dotenv()` plus a real API call, never by trusting an ambient shell export), set
`labels.txt` `status:done`.

## After (2026-09-19, run finished)

`wrote 300 commits, 200 PRs; manifest at data/eval_real/MANIFEST.json`. Re-ran `task.txt`
VERIFY items 2-3 for real:

- `ai_commits.jsonl`: 300 records (target 300, ≥ 250 required); min `date`
  2026-07-13T10:35:44+09:00 (≥ 2023-01-01); max 5 records per repo; 0 records whose
  stored `text` still matches `AI_CO_AUTHOR_PATTERN` (marker stripping held). Agents:
  Claude 142, Opus 127, Sonnet 30, Gpt 1.
- `ai_prs.jsonl`: 200 records (target 200, ≥ 150 required); min `date`
  2026-07-29T06:04:47Z; max 5 per repo; 0 leaks. Agents: Sonnet 72, Opus 69, Claude 41,
  Claude Code 14, Haiku 3, Cursor 1.
- sha256 of both files matches `MANIFEST.json` exactly.
- `grep -rn "ghp_\|github_pat_" data/eval_real tasks/20-corpus` — no real leak (see VERIFY
  item 2 above; the one hit is `task.txt`'s own documentation of this very check).

Both `--commit-target 300` / `--pr-target 200` caps were hit exactly, meaning demand
exceeded supply at every agent query — the pool of eligible real AI-written text is not
the bottleneck here.

## Hub upload (2026-09-19, unblocked)

Owner replaced `HF_TOKEN` in `.env`; re-verified the same way (never trusting the shell)
via `load_dotenv()` + `GET /api/whoami-v2`: `role: "write"`, `displayName: "WriteToken"`,
created minutes earlier. `tasks/DECISIONS.md` D9 no longer applies.

- `hf repo create alterpub/tonofdevelopervoice-eval-sets --type dataset --private --exist-ok`
  → `https://huggingface.co/datasets/alterpub/tonofdevelopervoice-eval-sets`.
- `hf upload alterpub/tonofdevelopervoice-eval-sets <scratch dir with only ai_commits.jsonl,
  ai_prs.jsonl, MANIFEST.json> . --repo-type dataset` → commit
  `a88663b42211054f67af5e48251709e858fc14b2`. `owner/` and `owner_v1_outputs/` were never
  copied into the upload staging directory, so they cannot have been uploaded.
- Verified from a clean state, not trusted: downloaded both files into a fresh scratch
  directory (`hf download ... --local-dir`) and compared sha256 against the local copies
  — both matched exactly (`6ee36029...` and `2aaef6dd...`, same as `MANIFEST.json`).

## Status

`labels.txt` set to `status:done`: `OUTCOME` now fully exists —
`data/eval_real/ai_commits.jsonl` (300 ≥ 250), `ai_prs.jsonl` (200 ≥ 150), and the Hub
dataset commit above, all verified from a clean state. `verify:passed` is left for
`/verify` (another context), per `tasks/PROTOCOL.md` §5.
