---
status: done
created: 2026-09-19
---
# PROJECT.md ledger matches the decisions of 2026-09-19

## Goal
`docs/PROJECT.md` and `AGENTS.md` describe the project that is about to be rebuilt: three
new capability rows exist (PR text collection, on-device MLX inference, AI-written text for
evaluation), every remaining mention of "Soup" as the training tool is gone except the one
sentence in §1 that records it was rejected, §5 carries the 2026-09-19 collection approval,
§9 points at `tasks/`, and `AGENTS.md` says new work lives there. `docs/PROJECT.md` and
`AGENTS.md` end up edited together in one commit, as `task.txt` OUTCOME asks.

## Acceptance criteria
- [ ] AC1 `grep -c "Soup" docs/PROJECT.md` prints `1`, and that one hit (§1, the Stack row)
      reads as a rejection, not an instruction — verify: `grep -n "Soup" docs/PROJECT.md`
- [ ] AC2 Three new ledger rows exist — verify:
      `grep -n "PR text collection\|On-device inference\|AI-written" docs/PROJECT.md`
      prints three lines
- [ ] AC3 §5 carries the approval note — verify: `grep -n "2026-09-19" docs/PROJECT.md`
- [ ] AC4 Gate green — verify:
      `ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run`

## Stack
Python (repo-wide: ruff, mypy strict, pytest, pytest-cov per `pyproject.toml`). This task
touches only Markdown; the gate runs unchanged.

## Decisions
- Scope, wording and target line ranges → fully specified by `task.txt` (audited and
  decided by the owner on 2026-09-19); no open question survived reconnaissance, so no
  interview was run.
- Commit granularity → `task.txt` OUTCOME says "edited ... in one commit"; this overrides
  the repository's general "commit per finished task" for this specific deliverable. T01-T04
  edit in the working tree without committing; T05 makes the one commit.
- Branch → `docs/PROJECT.md` §7: work directly on `main`. No branch task.

## Assumptions
- The repository currently has three uncommitted, unrelated-to-this-task items from the
  audit session: `tasks/` (the whole tree this task lives in), `docs/audit-2026-09-19.md`,
  and one line added to `pyproject.toml` (`extend-exclude = ["tasks"]`, without which
  `ruff check .` fails on the template's `tasks/check.py` with 6 `E501` — confirmed by the
  advisor before this plan was written). None of this belongs in the ledger-update commit
  (`AGENTS.md`: "Stage by path, never `git add -A`"), so T00 commits it first, separately,
  as ordinary prep — not attributed to any single task in the tree.
- The exact wording of every edit follows `task.txt` SCOPE verbatim; where SCOPE gives a
  template ("add row `\"X | included | Y\"`"), that string is inserted into the ledger
  table as its own row.

## Out of scope
- Any change to the gate checks in `docs/PROJECT.md` §6.
- `docs/runbook-deploy.md` / `docs/runbook-training.md` — owned by `50-docs/01-runbooks`.
- `docs/research/*.md` — history, not edited.
- Deleting or rewording the §1 sentence that records why Soup was rejected.

## Tasks
- [x] T00 Baseline: stage and commit the audit session's untracked prep work
      (`tasks/ docs/audit-2026-09-19.md pyproject.toml`) as its own local commit (not
      pushed) so the gate reflects a clean checkout, not a dirty tree; then run the gate
      once and record the result; then capture the "before" reverse-control evidence
      (`grep -n "Soup" docs/PROJECT.md` — expect 4 hits) into
      `tasks/05-scope/01-ledger-update/NOTES.md` under a `## Before (T00)` heading —
      verify: `git status --short` shows only `docs/PROJECT.md`/`AGENTS.md` as candidates
      for the next commit (everything else already committed);
      `ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run` exits 0;
      `NOTES.md` contains the 4-line grep output
- [x] T01 Add the three new capability-ledger rows to §3 (PR text collection; on-device
      inference on Apple Silicon; AI-written commit/PR text collection) and update the
      "External integrations" row (replace Soup with Unsloth; add Hugging Face Hub) — per
      `task.txt` SCOPE lines 1-4 — verify:
      `grep -n "PR text collection\|On-device inference\|AI-written" docs/PROJECT.md`
      prints three lines; `grep -n "External integrations" -A1 docs/PROJECT.md | grep -c "Soup"`
      prints `0`; `ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run`
      exits 0
- [x] T02 Replace "via Soup" (§2, goal row) and "Soup training recipe" (§4, agent-decisions
      bullet) with Unsloth-appropriate wording; leave §1's rejection sentence untouched —
      verify: `grep -c "Soup" docs/PROJECT.md` prints `1`; `grep -n "Soup" docs/PROJECT.md`
      shows only the §1 line, and it still contains "chosen over Soup" or equivalent
      rejection language; `ruff check . && mypy . && pytest &&
      python3 scripts/coverage_gate.py --run` exits 0
- [x] T03 §5: add a dated note that on 2026-09-19 the owner approved a new collection into
      `data/raw_v2/` while `data/raw/`/`data/dataset/` (v1) stay untouched (`tasks/DECISIONS.md`
      D2). §9: add a row pointing at `tasks/` (`README.md`, `PROTOCOL.md`, `GOAL.md`,
      `DECISIONS.md`) — verify: `grep -n "2026-09-19" docs/PROJECT.md` shows the §5 note;
      `grep -n "tasks/" docs/PROJECT.md` shows the new §9 row;
      `ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run` exits 0
- [x] T04 `AGENTS.md` "Source of truth": add one bullet saying new work lives in `tasks/`
      and `docs/plans/tonofdevelopervoice-v1.md` is closed history — verify:
      `grep -n "tasks/" AGENTS.md` shows the new bullet;
      `ruff check . && mypy . && pytest && python3 scripts/coverage_gate.py --run` exits 0
- [x] T05 Close out: `python3 tasks/check.py` (0 problems); re-run the four VERIFY items
      from `task.txt` (AC1-AC4 above) and append their output to `NOTES.md` under
      `## After (T05)`; stage exactly `docs/PROJECT.md AGENTS.md` and commit as
      `T05: update PROJECT.md ledger and AGENTS.md for v2 rebuild decisions`
      (per `docs/PROJECT.md` §7's `T##: <what changed>` pattern; not pushed); set
      `tasks/05-scope/01-ledger-update/labels.txt` `status:done` (OUTCOME now exists in the
      repository — `PROTOCOL.md` §5) — verify: `git log --oneline -1` shows the T05 commit
      touching only those two files (`git show --stat HEAD`); `python3 tasks/check.py`
      exits 0; AC1-AC4 all pass

## Log
- T00: committed prep work as `a5313de` (61 files: `tasks/`, `docs/audit-2026-09-19.md`,
  `pyproject.toml`). Gate on the clean commit: ruff/mypy/115 tests/coverage 100% — all 0.
  `git status --short` clean. Captured the 4-hit "before" grep into NOTES.md.
- T01: added 3 ledger rows (PR text collection, On-device inference, AI-written text
  collection) and rewrote the External integrations row (Soup → Unsloth, added HF Hub).
  grep for the 3 rows: 3 lines; Soup count in that row: 0. Gate all 0.
- T02: replaced "via Soup" (§2) and "Soup training recipe" (§4) with Unsloth. `grep -c
  "Soup"` now `1`, matching only §1's rejection sentence ("chosen over Soup ...
  silent-correctness bugs"). Gate all 0.
- T03: added the §5 2026-09-19 approval note (new collection into data/raw_v2/ etc.,
  v1 data untouched) and a §9 row pointing at tasks/README.md, PROTOCOL.md, GOAL.md,
  DECISIONS.md. Both greps found; gate all 0.
- T04: added the AGENTS.md bullet pointing new work at tasks/ and marking
  docs/plans/tonofdevelopervoice-v1.md closed history. Grep found; gate all 0.
- T05: `python3 tasks/check.py` → 0 problems. Re-ran AC1-AC4, all pass (recorded in
  NOTES.md "After (T05)"). Committed `docs/PROJECT.md AGENTS.md` only as `8b401e0`
  (`git show --stat HEAD` confirms exactly those two files). Set
  `tasks/05-scope/01-ledger-update/labels.txt` to `status:done`. All plan tasks closed;
  `verify:passed` is left for `/verify` (another context), per `PROTOCOL.md` §5.
