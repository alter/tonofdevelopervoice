Blocked: 2026-09-19
Missing: a write-scoped HF_TOKEN (tasks/DECISIONS.md D9) — the one in .env is
  role=read ("public_read"), confirmed via load_dotenv() + GET /api/whoami-v2 (never by
  trusting an ambient shell export). `hf upload data/eval_real <hf-user>/tonofdevelopervoice-eval-sets --repo-type dataset --private`
  needs write access on the target repo.
Done before stopping: real collection run completed and verified against every
  numeric criterion in task.txt VERIFY item 2 and 3:
  - data/eval_real/ai_commits.jsonl: 300 records (target 300, >= 250 required), min
    date 2026-07-13 (>= 2023-01-01), max 5 records per repo, 0 records whose stored
    text still matches AI_CO_AUTHOR_PATTERN.
  - data/eval_real/ai_prs.jsonl: 200 records (target 200, >= 150 required), min date
    2026-07-29, max 5 per repo, 0 leaks.
  - sha256 of both files matches data/eval_real/MANIFEST.json.
  - No token substring anywhere in data/eval_real or tasks/20-corpus (grep -rn
    "ghp_\|github_pat_", the one hit is task.txt's own documentation of the check).
  - Reverse control executed and red (see NOTES.md).
  - Gate green: ruff/mypy/pytest (208 tests)/coverage 100%.
What can be done without it: nothing further on this task — the Hub upload is the
  only remaining OUTCOME item. Once a write-scoped token exists, run:
  `hf upload data/eval_real <hf-user>/tonofdevelopervoice-eval-sets --repo-type dataset --private`
  (uploads ai_commits.jsonl, ai_prs.jsonl, MANIFEST.json — never owner/), copy the
  resulting commit into MANIFEST.json here, set status:done.
