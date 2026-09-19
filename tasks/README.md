# Task tree — tonofdevelopervoice

One task is one directory with two required files and a validator. The tree is a
ledger of work, not a journal: it holds what must exist, split into executable
pieces.

## Key documents

- `PROTOCOL.md` — read first by every executor: what to check before an edit,
  how to work, reverse control, when a task is closed, when to stop.
- `GOAL.md` — the goal, the gates, signs of progress and signs of self-deception.
- `ROLES.md` — the roles, what each owns and where it writes; the HUMAN role.
- `DECISIONS.md` — cross-cutting decisions `D<n>`: decided / why / rejected.

## Phases

`NN-<slug>` in steps of 10, in dependency order. Every phase carries its own
`task.txt` and `labels.txt`; the phase's SCOPE lists its child tasks, one line
each.

| Phase | What it holds |
|---|---|
| `05-scope` | the owner's decisions of 2026-09-19 recorded in `docs/PROJECT.md` |
| `10-serving` | a 4-bit MLX artefact and an in-process backend that is fast on the Mac |
| `20-corpus` | new collection (git history + PR text), cleaning, diverse synthesis, dataset v2 |
| `30-training` | pinned environment, completion-only loss, recipe, training run v2 |
| `40-evaluation` | degeneracy metrics, baselines, evaluation through the shipped artefact, quality gate |
| `50-docs` | runbooks that match the rebuilt pipeline |

Why the tree exists and the evidence behind every phase: `docs/audit-2026-09-19.md`.
Two hosts are involved and every task says on which one it runs: **MAC** (the dev
MacBook, M2, 24 GB) and **HOST** (Ubuntu under WSL2, RTX 5090). `data/` and `models/`
are gitignored on both; artefacts that must survive live in the task directory.

## Order of execution

One line per task, in the order to take them. "Host" is where the commands run.
Lines with the same step number can run in parallel (different roles, different files).

| Step | Task | Host | Role |
|---|---|---|---|
| 1 | `05-scope/01-ledger-update` | MAC | ARCH |
| 2 | `10-serving/01-merged-export` | HOST | TRAIN |
| 2 | `10-serving/03-rewrite-result` | MAC | SERVE |
| 3 | `10-serving/02-mlx-conversion` | MAC | SERVE |
| 4 | `10-serving/04-mlx-backend` | MAC | SERVE |
| 5 | `10-serving/05-batch-rewrite` | MAC | SERVE |
| 6 | `10-serving/06-mac-speed-gate` — **gate 1** | MAC | SERVE, HUMAN |
| 7 | `40-evaluation/01-degeneracy-metrics` | MAC | EVAL |
| 7 | `20-corpus/01-git-history-collector` | HOST | DATA |
| 7 | `20-corpus/02-pr-collector` | HOST | DATA |
| 7 | `20-corpus/04-ai-eval-inputs` | HOST | EVAL |
| 7 | `30-training/01-pinned-environment` | HOST | TRAIN |
| 8 | `20-corpus/03-text-cleaning` | HOST | DATA |
| 8 | `30-training/02-completion-only-loss` | HOST | TRAIN |
| 9 | `20-corpus/05-diverse-synthesis` (llama-server must be UP) | HOST | DATA, HUMAN |
| 10 | `20-corpus/06-dataset-v2` — **gate 2** | HOST | DATA, HUMAN |
| 11 | `30-training/03-training-recipe` | HOST | TRAIN |
| 12 | `30-training/04-training-run-v2` (llama-server must be DOWN — owner) | HOST, then MAC | TRAIN, HUMAN |
| 13 | `40-evaluation/02-shipped-path-eval` | MAC | EVAL |
| 14 | `40-evaluation/03-baselines` | HOST + MAC | EVAL |
| 15 | `40-evaluation/04-quality-gate` — **gate 3** | MAC | EVAL, HUMAN |
| 16 | `50-docs/01-runbooks` | MAC + HOST | SERVE, TRAIN |

Steps 2-6 can start before the owner is available for steps 7-16: they need only the
existing v1 adapter. Nothing in steps 1-6 improves the text; it only makes the Mac fast.

## Task format

`task.txt`, sections in exactly this order, bodies indented by two spaces:

```
TASK: <short name, names the artefact>

GOAL
  What this produces and why it exists. Two or three lines. If it serves a gate,
  say which. Every number carries its source.

CONTEXT
  3–7 paths to read FOR THIS TASK. Never "read everything".

SCOPE
  + what is included
  − what is deliberately excluded, and where it lives instead

OUTCOME
  The artefact that exists when the task is closed: a path or a measurable number.

VERIFY (<role>)
  Numbered checks somebody else can run. At least one of them is reverse
  control: what must turn the check red.

ROLE
  Who does it.

DEPENDS
  Paths of tasks that must finish first, or (none).
```

`labels.txt` — one `key:value` pair per line.

Optional neighbours: `NOTES.md` (rationale, measurements, rejected alternatives;
dated headings), `VERIFY.md` (proof of verification — written only by the
verifier), `BLOCKED.md` (when `status:blocked`), `PLAN.md` (the current session's
execution plan, created by `/plan`) and any artefact — logs, screenshots,
measurement output.

The `−` lines in SCOPE matter as much as the `+` lines. An unwritten boundary is
a boundary somebody will cross.

## Labels

```
phase:      scope | serving | corpus | training | evaluation | docs
role:       ARCH | DATA | TRAIN | SERVE | EVAL | HUMAN
type:       feature | fix | research | decision | chore
priority:   P0 | P1 | P2 | P3
status:     todo | in_progress | review | done | blocked (with BLOCKED.md next to it)
verify:     pending | passed | failed
depends:    <path to a task>
milestone:  M1 | M2 | M3
gate:       yes — only on tasks that measure the goal
```

## Order of work

1. The executing role works (`status: todo → in_progress → done`).
2. **Another context**, which wrote neither the code nor its tests, sets
   `verify: passed` or `failed` (`/verify`).
3. Tasks with `gate:yes` are confirmed by a human; the next phase does not start
   until they pass.

## The `status:done` rule

`status:done` means **the OUTCOME artefact exists** at the named path, not that
"the work looks finished". An artefact outside the repository (a machine at a
provider, a phone in someone's hand, a signed build, another person's eyes) is
not closed by the context that did the work: it stays `in_progress` with a note
in `NOTES.md` saying what is missing and who can provide it.

## The `verify:passed` rule

Requires a `VERIFY.md` in the task directory. Words in a commit message are not
proof. Required parts:

- a `Verifier:` line naming the context and listing what it did **not** do — it
  authored neither the code nor its tests;
- `## How to reproduce` — at least one command from a clean state: a fresh
  checkout, an empty environment, not a single variable exported by hand;
- `## Reverse control` — what was broken on purpose and what red output it gave;
- `## What was not checked` — non-empty. A verification boundary always exists.

Every number in `VERIFY.md` carries its source — a path, a command, a log line.

## The stopping rule

The executor stops and **does not simulate** when a missing secret is needed; an
owner's decision is needed; a task in DEPENDS is not closed; the artefact
requires a person; or reverse control cannot be made red. A `BLOCKED.md` is
created in the task directory:

```
Blocked: <date>
Missing: <one line, concrete — a variable name, a task path, a question>
Done before stopping: <list, with paths>
What can be done without it: <or "nothing">
```

and `labels.txt` gets `status:blocked`. A stub instead of a secret, "hardcode it
for now", "let us assume that…" — that is not a way around a blocker, it is a
false `done` with delayed discovery.

## Validator

```bash
python3 tasks/check.py     # zero problems is a precondition for closing a task
```

## Language

The tree's language is whatever this file is written in; `check.py` accepts the
`VERIFY.md` and `BLOCKED.md` markers in English or Russian, so a tree kept in
another language keeps its own wording. Code, docstrings and commit messages
follow the existing code.
