# Training approach for style-transfer SFT (Sept 2026)

Scope: how to fine-tune the base model (`base-models.md`) to rewrite AI-generated
commit/PR text into authentic pre-2021 engineering style, given we only have one-sided
data — a large corpus of authentic text, no naturally occurring (AI, authentic) pairs.

## Option 1: plain causal-LM continuation on the authentic corpus alone

Standard next-token training on the target-style corpus shapes the marginal distribution
p(y); there is no (x, y) signal, so nothing in the objective connects "AI text in" to
"rewritten text out." At inference the model would continue or ignore the input rather
than transform it. Legitimate role: a domain-adaptive-pretraining (DAPT) warm-up stage
before SFT (Gururangan et al., "Don't Stop Pretraining," ACL 2020), and as a
perplexity-based style metric for evaluation (feeds `evaluation.md`). Not usable as the
deliverable on its own. Dataset shape: flat plain-text corpus, no input/output structure.

## Option 2: SFT on synthetic paired data (recommended)

Standard technique when only one side of a style pair exists: synthesize the missing
side. Primary source (fetched directly): Krishna, Wieting & Iyyer, "Reformulating
Unsupervised Style Transfer as Paraphrase Generation" (STRAP), EMNLP 2020
(aclanthology.org/2020.emnlp-main.55.pdf) — a 3-stage pipeline (normalize style-corpus
sentences via a paraphraser, train an inverse-paraphraser back to the original style,
swap in the target style's inverse-paraphraser at inference), reported to significantly
outperform prior unsupervised style-transfer systems on both automatic and human
evaluation.

This project's case is structurally easier than STRAP's: we can synthesize the "AI-ish"
input side directly by running authentic commit/PR text through an LLM prompted to
inflate it toward generic AI style (verbose, hedged, over-explained, boilerplate-heavy),
then SFT directly on (synthetic_AI_ish_input -> authentic_output) pairs — a single
supervised step rather than STRAP's two-hop paraphrase/inverse-paraphrase design, and
directly matched to the real inference-time input distribution (real AI-generated text),
not just a stand-in for missing data.

Risk: overfitting to one generator's "inflation fingerprint" rather than learning the
general AI-verbosity style. Mitigation: generate the synthetic input side from multiple
different LLMs, multiple prompts, and multiple sampling temperatures.

Dataset shape: paired records — `{"input": <synthetic AI-ish text>, "output": <authentic
text>}` (JSONL), or chat-format instruction pairs.

## Option 3: preference-based post-training (DPO/ORPO/KTO)

Requires (input, chosen, rejected) triples — needs multiple candidate outputs per input
ranked by preference, which doesn't route around the one-sided-data problem; it swaps one
synthesis problem (paired input/output) for another (chosen/rejected pairs). ORPO merges
the SFT and preference loss into one training run but still consumes chosen/rejected
pairs as input — it does not remove the pairing requirement. Literature broadly treats
preference optimization as a refinement layered on an SFT-initialized policy, not a
standalone replacement (Raschka, "Why preference tuning often follows SFT"; DPO's own
paper constructs an SFT-like reference model first in its experiments).

Correct role here: an optional second-pass polish stage after the Option-2 SFT model
exists — sample k rewrites per synthetic input from the SFT model, score them with (a) an
authentic-vs-AI style classifier trained on held-out authentic text vs. AI-generated
text, and (b) a meaning-preservation/similarity metric, take best-vs-worst as
chosen/rejected, then run DPO or ORPO on top. This mirrors Liu & May, "Style Transfer
with Multi-iteration Preference Optimization" (arXiv:2406.11581).

Dataset shape: preference triples `{input, output_chosen, output_rejected}`, generated
downstream of a trained SFT model — not producible by the raw corpus pipeline directly.

## Established literature

GYAFC (Rao & Tetreault, 2018) is the standard *genuinely parallel* formality-transfer
benchmark, useful here mainly as confirmation that direct supervised seq2seq/SFT on style
pairs is the field's default once parallel/pseudo-parallel data exists. STRAP is the
standard reference for the *no-parallel-data* setting, directly analogous to this
project. Across both threads, the converging standard recipe when parallel data doesn't
exist is: synthesize pseudo-parallel data via paraphrase/back-translation/LLM-transform,
then do ordinary supervised SFT on the synthesized pairs — independently supporting the
Option 2 recommendation.

## Dataset shape summary (what the data pipeline must emit)

- Option 1: flat plain-text corpus — DAPT warm-up / eval-classifier positive class only.
- **Option 2 (what T09's dataset-assembly task must produce): paired records
  `{input: synthetic AI-ish text, output: authentic text}`, JSONL.**
- Option 3: preference triples, produced downstream of a trained SFT model — a later
  stage, not part of the initial corpus/dataset pipeline.
- Regardless of option: hold out a slice of authentic text, untouched by training, for
  (a) an authentic-vs-AI-generated style classifier (used as an eval metric and as the
  Option-3 scorer), and (b) held-out references for automatic/manual evaluation.

## Project-specific consequences for the data pipeline (carried forward to T04/T07/T09)

- Commit/PR trailers and identifiers (`Signed-off-by:`, `Reviewed-by:`, `Fixes: <sha>`,
  `Cc:`, bug-tracker IDs) are project-specific boilerplate the model could memorize and
  hallucinate on unrelated inputs — the collection/cleaning stage should strip or
  explicitly decide how to handle these, not leave it to training.
- linux, postgresql, nginx, apache and mysql each have materially different house styles.
  Training on the union without a project signal averages the style. Decision: train one
  blended style for v1 (simpler, matches the "single rewrite target" framing of the
  project), keep per-project tagging as a documented option if blended output proves too
  generic — this is a data-shape decision made now so the JSONL schema in T09 can carry
  an optional `project` field even if v1's training run doesn't condition on it yet.

## Decision

**Training approach: SFT on synthetic paired data (Option 2)**, using an LLM-based
back-translation/normalization step to synthesize the "AI-ish" input side of each pair
from the authentic corpus, generated across multiple LLMs/prompts/temperatures to avoid
overfitting to one generator's fingerprint. Option 1 (plain LM continuation) is used only
as an optional DAPT warm-up and as one ingredient of the evaluation metric
(`evaluation.md`), never as the deliverable. Option 3 (DPO/ORPO) is deferred to an
optional post-SFT polish stage, out of scope for the v1 training run — `## Out of scope`
in the plan already excludes anything beyond a working CLI/web form on the SFT model.

Consequence for T09 (dataset assembly): output schema is `{"input": ..., "output": ...,
"project": ...}` JSONL with a held-out split reserved for evaluation, not a plain-text
corpus.
