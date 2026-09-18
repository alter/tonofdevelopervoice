# factory.py
import os
import sys

from tonofdevelopervoice.serve.backend import InferenceBackend, StubInferenceBackend

MODEL_DIR_ENV_VAR = "TONOFDEVELOPERVOICE_MODEL_DIR"
BACKEND_ENV_VAR = "TONOFDEVELOPERVOICE_BACKEND"


def _cuda_available() -> bool:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return False
    return bool(torch.cuda.is_available())


def _real_backend(model_dir: str) -> InferenceBackend:
    backend_choice = os.environ.get(BACKEND_ENV_VAR)
    if backend_choice not in (None, "", "unsloth", "peft"):
        raise ValueError(f"{BACKEND_ENV_VAR} must be 'unsloth' or 'peft', got {backend_choice!r}")

    use_unsloth = backend_choice == "unsloth" or (not backend_choice and _cuda_available())
    if use_unsloth:
        from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

        return UnslothInferenceBackend(model_dir)

    # No CUDA (e.g. Apple Silicon): Unsloth routes through its MLX backend there, which
    # as of unsloth_zoo 2026.9.5 fails to load a bitsandbytes-trained PEFT adapter. Load
    # the same adapter via plain transformers/peft instead (cuda/mps/cpu, whichever the
    # host has) -- see tonofdevelopervoice.serve.peft_backend for why.
    from tonofdevelopervoice.serve.peft_backend import PeftInferenceBackend

    return PeftInferenceBackend(model_dir)


def default_backend() -> InferenceBackend:
    model_dir = os.environ.get(MODEL_DIR_ENV_VAR)
    if model_dir:
        return _real_backend(model_dir)
    print(
        f"WARNING: {MODEL_DIR_ENV_VAR} is not set — using StubInferenceBackend, which "
        "returns the input unchanged (prefixed with '[rewritten] '). Set "
        f"{MODEL_DIR_ENV_VAR} to a trained adapter's path to use the real model.",
        file=sys.stderr,
    )
    return StubInferenceBackend()
