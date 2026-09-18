# Evaluation methodology for style-transfer quality (Sept 2026)

Scope: an automated way to judge how well the model's rewrites match genuine pre-2021
engineering style, against a held-out slice of real text never used in training. Builds
on `training-approach.md`'s SFT-on-synthetic-pairs decision.

## Pipeline shape

Single CPU-only script. Inputs: model-output JSONL + held-out real-text JSONL (same
`{input, output, project}` schema as T09's training data). Steps:

1. Materialize a genuinely parallel test set by running T09's own synthesis step on
   held-out real text (never seen in training) — this reuses the training pipeline's
   synthesizer rather than inventing a second one, so the test pairs are apples-to-apples
   with training pairs.
2. Run model inference on the synthetic inputs.
3. Compute the metrics below.
4. Emit one JSON/CSV report row per run with all metric values, plus the worst-scoring
   examples surfaced for a manual spot check — automated metrics alone are not trusted
   without periodic human spot-checks (a recurring finding in the style-transfer
   evaluation literature, see below).

## Metrics

1. **Content-preservation floor** — sentence-embedding cosine similarity
   (`sentence-transformers/all-MiniLM-L6-v2`, CPU) between model output and its source
   (synthetic AI-ish input). Sanity floor only ("did meaning survive"), not a style
   score — MiniLM rewards meaning-preserving paraphrase, which is orthogonal to style.
2. **Reference-based fidelity** — BERTScore (semantic) between model output and the real
   authentic reference produced in step 1, not sBLEU-against-source. sBLEU-against-source
   is the style-transfer literature's usual default, but is wrong here: the target
   transform is compression (verbose AI text -> terse authentic text), so scoring against
   the source penalizes exactly the shortening the model is trained to do.
3. **Style strength** — an authentic-vs-AI-generated style classifier: TF-IDF
   (word+char n-grams) + logistic regression (scikit-learn), trained on held-out real
   text (positive) vs. synthetic AI-ish text (negative), CPU-seconds. This is the same
   classifier `training-approach.md`'s optional Option-3 DPO polish stage would use —
   reuse it here rather than building a second one. Report the classifier's own held-out
   validation accuracy alongside the score it assigns to model outputs (an unvalidated
   style classifier is a known failure mode in the literature).
4. **Fluency** — perplexity of model outputs under a small pretrained LM (GPT-2 small via
   `transformers`, CPU-feasible at eval scale). Sanity check only: flag anomalously high
   perplexity for manual review; do not treat low perplexity as evidence of authentic
   style (it conflates generic fluency with style).
5. **LLM-as-judge, forced-choice** — prompt a capable model with a randomized pair (one
   real held-out sample, one model output): "which was written by a human engineer in a
   commit/PR." Score = win rate vs. a 50% baseline (50% = indistinguishable from
   authentic). Absolute 1-5 Likert ratings are avoided — they have no anchor and are more
   exposed to verbosity/self-preference bias documented in LLM-judge-reliability
   literature. Report output-length distribution vs. real-length distribution as a
   separate diagnostic, since judges are known to be swayed by verbosity independent of
   style.
6. **Optional distributional check** — MAUVE (`mauve-text`, GPT-2-large features)
   comparing the model-output distribution to the held-out authentic distribution. The
   MAUVE paper's own experiments used 5,000 generations per side for stable estimates —
   likely more than this project's held-out set will contain; run only if the held-out
   set is large enough, not a required pipeline stage. Fréchet-distance-style
   embedding-cloud metrics are explicitly rejected by the MAUVE paper's own ablation
   (Fréchet distance nonsensically improved with generation length while MAUVE showed
   the expected degradation) — do not substitute an MMD/Fréchet metric for MAUVE.

## Why not X

- Perplexity alone: conflates fluency with style (a fluent AI-ish sentence scores as well
  as an authentic one).
- sBLEU-against-source alone: penalizes the compression this task is explicitly trained
  to do.
- Absolute LLM-judge Likert scores: no anchor, more exposed to length/self-preference
  bias than forced-choice comparison.
- Fréchet/MMD embedding-cloud distance in place of MAUVE: shown nonsensical (improving
  with generation length) in MAUVE's own ablation.

## Caveats carried forward (not independently verified by research)

`mauve-text`/`bert-score` package names/APIs on current PyPI were assumed stable, not
version-checked. Whether the held-out corpus will be large enough for MAUVE's 5,000-
sample stability target depends on T04/T07's actual corpus size, not yet known. STEL
(Wegmann et al., RepL4NLP 2022) is a possible style-representation upgrade over MiniLM,
flagged as optional for a later iteration, not required for v1.

## Decision

**Evaluation: a six-part automated report** (MiniLM content-preservation floor, BERTScore
fidelity against the real reference, a validated authentic-vs-AI style classifier, GPT-2
perplexity as a fluency sanity check, forced-choice LLM-judge win rate, optional MAUVE if
the held-out set is large enough) run as a single CPU-only script
(`scripts/evaluate.py`, T15), plus worst-scoring examples surfaced for manual spot check.
No new GPU training is required for evaluation itself. The style classifier is shared
with `training-approach.md`'s optional Option-3 DPO polish stage rather than duplicated.
