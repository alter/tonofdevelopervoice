# Fine-tuning framework survey (Sept 2026)

Scope: which framework to use for fine-tuning on a single Ubuntu/WSL2 host, 80GB RAM,
one RTX 5090 (32GB VRAM), no cluster. Candidates: Soup, Axolotl, Unsloth, LLaMA-Factory,
raw Hugging Face (transformers+peft+trl).

## Soup (soup-cli, github.com/MakazhanAlpamys/Soup)

YAML-config CLI wrapping transformers/peft/trl, headline feature "layer streaming"
(streams the frozen base model layer-by-layer into VRAM to fit large models on tiny
cards). Apache-2.0, Python 3.10-3.12, ~6.8k stars, weekly release cadence, current
v0.75.0 (2026-09-12). Supports LoRA/QLoRA/DoRA and DPO/GRPO/PPO/KTO/ORPO/SimPO/IPO/BCO,
has a web UI and an OpenAI-compatible serving mode.

Concern: its own release notes through Aug-Sep 2026 show a run of *silent correctness*
bugs fixed only in the last few weeks before this survey — v0.73.0 silent gradient
corruption in layer streaming ("bit-exact forward, healthy-looking loss curve, wrong
gradients"), v0.73.1 a bf16-assumption bug and a VRAM-prediction error, v0.73.3 four
validated config flags that silently no-op, v0.74.0 the frozen base loading in fp32
instead of checkpoint precision (doubling memory use). Its own layer-streaming
correctness paper is scoped only to v0.73.0 behavior and its VRAM formula was found to
under-predict shortly after publication. Source: github.com/MakazhanAlpamys/Soup/releases.

Its headline feature (layer streaming) solves a VRAM problem this project doesn't have —
32GB comfortably fits an 8-13B QLoRA fine-tune without it.

## Axolotl

Mature, config-driven (YAML) wrapper over transformers/peft/trl/accelerate/DeepSpeed.
2026 releases added 4-bit MoE-expert LoRA/QLoRA and Blackwell/Hopper-targeted kernels.
Comfortably fits 8-13B on 32GB; its multi-GPU/FSDP strength is unused on a single-GPU
box. Public 2026 benchmarks show Unsloth beating it on raw single-GPU QLoRA speed
(~3.2h vs ~5.8h for a comparable Llama-3.1-8B QLoRA run), Axolotl pulling ahead only at
multi-GPU scale.

## Unsloth

Very mature (66.5k stars), the most actively pushed option specifically for
consumer/single-GPU fine-tuning. Hand-written Triton backprop kernels bypass PyTorch
autograd; claims ~2x speed and large memory reduction vs standard HF fine-tuning,
depending on workload. Near-drop-in over the HF stack (`FastLanguageModel` in place of
`AutoModelForCausalLM`, still uses `trl`'s trainers), so full control over the
DPO/preference setup is retained. Explicit native Blackwell/RTX-50-series (5060-5090)
support with a ready-made Docker image, which sidesteps most of the WSL2/CUDA
version-matching pain (see hardware note below). Also ships a no-code local Studio
(beta, March 2026). Multi-GPU is paid-tier only; irrelevant here (one GPU).

## LLaMA-Factory

Very mature (~75k stars), broad community, config-driven with an optional web UI
(LlamaBoard). Supports full FT, LoRA, QLoRA, GaLore, BAdam, DoRA, PiSSA, OFT, and the
full SFT/RM/PPO/DPO/KTO/ORPO training-stage menu. Comfortably fits this hardware.
Positioned as the broadest "pick from a menu" option — arguably the easiest on-ramp for
a solo dev who wants a GUI without writing training code, at the cost of being one layer
further from raw control than Unsloth.

## Raw Hugging Face stack (transformers + peft + trl)

The reference implementation every wrapper above sits on. QLoRA via
`BitsAndBytesConfig` + `LoraConfig` fed into `SFTTrainer`/`DPOTrainer`; documented to
handle a 65B model on a single 48GB GPU, so 8-13B on 32GB is routine even
unquantized at moderate context lengths. Fully code-driven — most flexible, most control
over data format and loss function, most setup/debugging burden. `trl`'s CLI scripts now
support `--use_peft --load_in_4bit` directly, narrowing the gap with wrapper CLIs for
simple cases.

## Also checked, ruled out

Meta's torchtune: development wound down in 2025 per the repo's own notice; not a
candidate.

## Hardware note: RTX 5090 on WSL2 (applies regardless of framework choice)

The 5090 (Blackwell, compute capability sm_120) needs driver >=570 (open kernel module
variant), CUDA Toolkit 12.8, and PyTorch >=2.7.0 with the cu128 wheel — stable PyTorch
had no pre-built sm_120 binaries before 2.7.0. Do not let `apt` pull the default
`nvidia-cuda-toolkit` package (CUDA 12.0, predates Blackwell). WSL2 2.6.3 does not expose
Blackwell's native FP8 tensor cores to compute workloads (falls back to FP16 emulation);
WSL2 2.7.0 fixed CUDA graph capture on the 5090. This is recorded here for
`docs/runbook-training.md` (T10) to act on.

## Decision

**Framework: Unsloth**, fallback: raw Hugging Face stack (transformers+peft+trl).

Rationale: 32GB VRAM already fits an 8-13B QLoRA fine-tune without needing Soup's
layer-streaming trick, so Soup's headline feature buys nothing here, while its Aug-Sep
2026 release history (silent gradient corruption, silently-no-op config flags, a 2.6x
memory-accounting bug, all fixed only weeks before this survey) is exactly the failure
mode that's dangerous for a subjective style-transfer task — a "healthy-looking loss
curve" with wrong gradients would be very hard to notice by eye. Unsloth has explicit
Blackwell/RTX-5090 support with a ready Docker path, is free for single-GPU use, is the
fastest current single-GPU QLoRA option in public benchmarks, and stays close enough to
raw `transformers`/`trl` that the DPO/preference setup this project likely needs (see
`training-approach.md`) is not fought by the wrapper. If Unsloth's hand-written kernels
ever produce a hard-to-diagnose discrepancy, the fallback is dropping straight to
`SFTTrainer`/`DPOTrainer` with a standard `BitsAndBytesConfig`+`LoraConfig` — a
known-quantity path with no wrapper-specific magic to debug. Axolotl and LLaMA-Factory
remain credible alternates if a GUI/YAML-first workflow is later preferred; neither beats
Unsloth on single-GPU speed for this box.
