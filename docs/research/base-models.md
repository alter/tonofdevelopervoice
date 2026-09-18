# Base model candidates for a 32GB-VRAM QLoRA fine-tune (Sept 2026)

Scope: which open-weight base model to fine-tune for a short-form technical-text style
transfer task (input: AI-flavored commit/PR text, output: authentic pre-2021 terse
engineering prose), on a single RTX 5090 (32GB VRAM). `HF_TOKEN` is available, so gated
models are on the table, but permissive/ungated licenses are still preferred where a
comparable model exists.

## Landscape shift since major-model training cutoffs

- **Qwen**: Qwen3 (Apr 2025, Apache 2.0) -> Qwen3.5 (Feb 2026, hybrid linear-attention +
  MoE flagship, Apache 2.0, small series 0.8B-9B) -> early Qwen3.6 / Qwen3.8-27B mentions.
- **Llama**: Llama 4 (Scout/Maverick, Apr 2025) is MoE-only and moved to a custom
  "open-weight" Meta community license (700M MAU cap, EU multimodal exclusion) — there is
  no dense Llama 4 8B; the current dense small is still Llama 3.1 8B, which is gated and
  license-restricted.
- **Gemma**: Gemma 3 (gated, custom Google license) -> **Gemma 4** (Apr 2026) is the first
  Gemma generation under **Apache 2.0**, with E2B/E4B edge variants plus a dense 12B and
  a 26B-A4B / 31B.
- **Mistral**: **Mistral 3** (Dec 2025), dense 3B/8B/14B + MoE Large-3, all Apache 2.0
  (except non-production Codestral / non-commercial Voxtral).
- **Phi**: Phi-4-mini 3.8B (MIT) -> Phi-4-reasoning line; no Phi-5 as of Sept 2026. Phi
  models are trained on synthetic "textbook" data (math/code/reasoning) — stylistically
  closer to verbose AI prose, a mismatch for this task.
- **DeepSeek**: R1-Distill family remains current but is reasoning-distilled (verbose
  chain-of-thought), a mismatch for short-text style transfer.
- **GLM/Zhipu**: GLM-4.6 (MIT) is a 357B MoE flagship — no compact dense variant found
  that fits this use case.

## Candidates in the 3-14B range

| Model | Size | License | Gated on HF | Base checkpoint published separately | Note |
|---|---|---|---|---|---|
| Qwen3-8B-Base | 8B | Apache 2.0 | No | Yes (`Qwen/Qwen3-8B-Base`) | Widest QLoRA tooling coverage (Unsloth documents recipes specifically for it) |
| Qwen3-14B(-Base) | 14B | Apache 2.0 | No | Yes | Same family, next size up if 8B proves insufficiently expressive |
| Qwen3.5 small series (up to 9B) | up to 9B | Apache 2.0 (per flagship; small-series license not independently confirmed) | Unconfirmed | Unconfirmed | Newer, less-verified in this survey — confirm the exact HF repo/license before use |
| Mistral-3-8B | 8B | Apache 2.0 | No | Yes (base + instruct both published) | Independent architecture/tokenizer, good fallback if Qwen3 shows characteristic-phrasing artifacts |
| Gemma-4-12B(-pt) | 12B | Apache 2.0 | No | Yes (`-pt` variants) | First ungated/Apache Gemma generation; larger, still comfortable at 32GB |
| Llama-3.1-8B | 8B | Custom Meta community license | Yes | Yes | Largest recipe/dataset ecosystem, but gated and license-restricted for redistribution — no reason to accept that when Apache alternatives of the same class exist |
| Phi-4-mini | 3.8B | MIT | No | N/A (instruct-focused) | Smallest footprint, but trained on synthetic reasoning/textbook data — stylistically a poor match for terse engineering prose |

Not recommended: DeepSeek-R1-Distill (reasoning chain-of-thought is a parasitic behavior
to fight for a non-reasoning rewrite task); GLM-4.6 and other >100B flagships (outside a
single-5090 QLoRA budget); Gemma-4 26B-A4B/31B (leaves less VRAM headroom for
activations/optimizer state than the 8-14B tier).

## Base vs. instruct checkpoint

Instruct checkpoints already carry a learned "voice" (polite preambles, bulleted
self-description of changes — exactly what this task needs to move away from). Full SFT
on (rough/AI-flavored -> terse-engineer) pairs on top of a **base** checkpoint gives a
cleaner style transfer without competing against baked-in instruct priors; on an instruct
checkpoint the same LoRA typically has to "overpower" a stronger prior, needing more
steps or higher rank/alpha. This is a heuristic from task shape + general QLoRA practice,
not a measured fact — worth a small-scale eval (a few hundred examples) before committing
to a full training run.

## VRAM headroom at 32GB

Aggregated 2026 guidance: QLoRA 4-bit weights are roughly 0.5 x (params in B) GB, plus
adapters/gradients/optimizer/activations. A 14B model needs roughly 8-10GB for weights
alone and typically fits well within 16GB total; 32GB leaves large headroom for batch
size and (for this task) short sequence lengths, and could even accommodate full-precision
LoRA (not just QLoRA) up to ~14B per the same sources. 8B models leave more headroom
still.

## Decision

**Base model: Qwen3-8B-Base** (Apache 2.0, not gated), fallback: **Mistral-3-8B**
(dense, Apache 2.0, base+instruct both published); next step up if 8B proves
insufficiently expressive: **Qwen3-14B** or **Gemma-4-12B-pt**, both still comfortable at
32GB QLoRA.

Rationale: fits 32GB with large headroom (room to raise LoRA rank/alpha or batch size
rather than being memory-bound); a separate base checkpoint exists (matches the
base-preferred-over-instruct reasoning above); the widest verified QLoRA tooling coverage
of any 2026 candidate (Unsloth documents recipes specifically for Qwen3-8B, matching the
`frameworks.md` T01 decision); Apache 2.0 with no redistribution restriction, avoiding
the licensing friction of gated Llama-3.1-8B for no benefit — Apache alternatives of the
same class are available. Mistral-3-8B is the fallback if Qwen3-8B shows
characteristic-phrasing artifacts that a LoRA struggles to overcome, since it's an
independent architecture/tokenizer at the same VRAM budget.

Caveat carried forward: the Qwen3.5 small series and exact base-checkpoint IDs should be
confirmed directly on huggingface.co (license, gated status) before being hard-coded into
`soup.yaml`/training config in T10 — this survey's confirmation for anything past
Qwen3(-Base)/Mistral-3/Gemma-4/Llama-3.1 came through aggregator sources, not always a
primary model card.
