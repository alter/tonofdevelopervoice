# Roles

Every role is a separate run with its own area, its own subtree and its own
right to write. **Overlap is forbidden:** two executors editing one file is the
source of half the breakage.

| Role | Owns | Writes to | Language |
|---|---|---|---|
| **ARCH** | scope ledger, cross-cutting decisions, review of others' work | `docs/PROJECT.md`, `tasks/DECISIONS.md` | — |
| **DATA** | collection, cleaning, synthesis, dataset assembly | `src/tonofdevelopervoice/collect/`, `src/tonofdevelopervoice/dataset/`, `scripts/collect*.py`, `scripts/synthesize.py`, `scripts/build_*.py`, their tests | Python |
| **TRAIN** | training, export of the merged model, training environment | `training/`, `src/tonofdevelopervoice/train/`, `docs/runbook-training.md`, their tests | Python |
| **SERVE** | inference backends, CLI, web form, batch script, MLX conversion | `src/tonofdevelopervoice/serve/`, `src/tonofdevelopervoice/cli.py`, `src/tonofdevelopervoice/web/`, `scripts/batch_rewrite.py`, `scripts/convert_mlx.py`, `pyproject.toml`, `docs/runbook-deploy.md`, their tests | Python |
| **EVAL** | metrics, reports, evaluation runs, thresholds | `src/tonofdevelopervoice/evaluate/`, `scripts/evaluate.py`, `scripts/generate_eval_outputs.py`, `scripts/collect_ai_eval_inputs.py`, their tests | Python |
| **HUMAN** | everything a machine cannot check | — | — |

Every role also writes to its own task directory (`NOTES.md`, artefacts).

## ARCH

Writes no product code. After every closed task it answers: has a second source of
truth appeared (two backends, two prompt templates, two dataset layouts); has the cost of
adding one more source repository or one more synthesis style gone up; by which route
does a newly trained model reach the owner's MacBook.

## EVAL

Never accepts work from whoever did it. Thresholds are written in `task.txt` **before**
the training run and are not tuned to the result. A changed threshold is its own commit
with its own reason.

## HUMAN — and this is not a formality

Tasks and VERIFY items with this role are not executed by an agent and not simulated. Not
because it could not, but because it errs systematically in one direction: it reports
that the result looks good.

Where a person must judge:

- whether 20 side-by-side rewrites read like a real pre-2021 engineer wrote them and kept
  every fact (gate 3);
- whether the MacBook stays usable while the batch runs (gate 1);
- anything that deletes collected data or stops the owner's `llama-server` on HOST.
