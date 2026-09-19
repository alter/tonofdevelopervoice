# GOAL — why this tree exists

## The goal

On the owner's MacBook, `scripts/batch_rewrite.py --dir <dir>` turns a directory of
AI-written commit and PR texts into terse pre-2021 engineering prose: every fact kept,
nothing copied verbatim, nothing cut off, about a minute per file.

## What hurts right now

Full evidence: `docs/audit-2026-09-19.md`.

- ~3.4 hours per file, ~48 s per token: `/tmp/pr/1.rewritten.txt` 05:45 →
  `/tmp/pr/2.rewritten.txt` 09:10 on 2026-09-19. Cause: 16 GB of fp16 weights on a
  24 GB machine with 7132 MB of 8192 MB swap already used
  (`src/tonofdevelopervoice/serve/peft_backend.py:38`, `sysctl vm.swapusage`).
- The model copies instead of rewriting: output = verbatim prefix of the input, 1039/1039
  and 1200/1200 characters, cut at the 256-token cap
  (`data/eval_real/owner/` vs `data/eval_real/owner_v1_outputs/`).
- 550 training pairs, commits only, one year of history, one synthesis style, 6.5% empty
  targets, loss computed on the prompt (`docs/plans/tonofdevelopervoice-v1.md:241`,
  `training/train.py:34`).
- The evaluation rewards copying (`src/tonofdevelopervoice/evaluate/metrics.py:31`) and
  never ran through the path the Mac uses.

## The gates — and only they measure the goal

**Gate 1 — `10-serving/06-mac-speed-gate` (milestone M1).** The shipped 4-bit artefact
rewrites the owner's nine files on the MacBook at >= 10 generated tokens/second with peak
memory <= 6.5 GB and the run finishes in under 20 minutes. Only a run on the real machine
with the owner's usual applications open shows this.

**Gate 2 — `20-corpus/06-dataset-v2` (milestone M2).** Dataset v2 exists with a manifest:
>= 12000 training pairs, >= 30% PR text, 0 empty targets, 0 merge commits, 0 identity
trailers, no normalised text on both sides of the split, no record dated 2021 or later.
Only a manifest computed from the files shows this; a log line saying "cleaned" does not.

**Gate 3 — `40-evaluation/04-quality-gate` (milestone M3).** Model v2, run through the
shipped artefact on the MacBook over real AI-written inputs, stays inside thresholds
written down before training (copy rate, truncation, empty, trailer leak, fact retention,
length ratio, style score), beats the prompted-instruct baseline, and the owner accepts 20
side-by-side samples by eye.

## Milestones

| Milestone | What it means | Entry condition |
|---|---|---|
| **M1** | the existing adapter runs fast and honestly on the Mac; "before" numbers exist | now |
| **M2** | dataset v2 and model v2 exist, exported as the 4-bit artefact | gate 1 passed |
| **M3** | model v2 is proven on real inputs through the shipped artefact; runbooks match | gate 2 passed |

## Signs that we are getting closer

- A closed task removes uncertainty about one of the gate questions, rather than
  increasing the amount of work done.
- Every number in the documents came from a measurement and carries its source.
- Rejected decisions are recorded together with the reason.
- The copy rate on `data/eval_real/` goes down while fact retention does not.

## Signs that we are NOT getting closer

- "N tasks closed" reported as progress.
- A report ahead of its check: something declared done that does not reproduce
  from a clean state.
- A run that has never been red.
- A check that is green by construction: the data is chosen so the defect cannot
  appear. Here specifically: evaluating only on text made by the same synthesis prompts
  that made the training set.
- A short output read as a good output. `"Authentication module improvements."` is a
  failure, not a success.
- Evaluation numbers produced on HOST through a different backend than the Mac uses.
- Work on a later milestone before an earlier one.

## Stop condition

The goal is revised, not "trained some more", when either holds:

- Gate 1 fails and Qwen3-4B-Base at 4 bits (DECISIONS D6) also fails it — the MacBook
  cannot host this product; the owner decides between a smaller model and remote serving.
- After training run v2 the prompted-instruct baseline
  (`40-evaluation/02-baselines`) still wins on style score at equal or better fact
  retention — fine-tuning is not earning its cost; the owner decides whether the product
  becomes a prompt around an instruct model.
