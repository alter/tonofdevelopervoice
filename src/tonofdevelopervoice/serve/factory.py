# factory.py
import json
import os
import sys
from pathlib import Path

from tonofdevelopervoice.serve.backend import InferenceBackend, StubInferenceBackend

MODEL_DIR_ENV_VAR = "TONOFDEVELOPERVOICE_MODEL_DIR"
BACKEND_ENV_VAR = "TONOFDEVELOPERVOICE_BACKEND"


def _cuda_available() -> bool:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return False
    return bool(torch.cuda.is_available())


def _is_mlx_model_dir(model_dir: str) -> bool:
    config_path = Path(model_dir) / "config.json"
    if not config_path.exists():
        return False
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and "quantization" in data


def _is_adapter_dir(model_dir: str) -> bool:
    return (Path(model_dir) / "adapter_config.json").exists()


def _unsloth_or_raise(model_dir: str) -> InferenceBackend:
    if not _cuda_available():
        raise RuntimeError(
            f"{model_dir!r} is a LoRA adapter that needs a CUDA/bitsandbytes host to run "
            "via Unsloth; on a Mac, use the MLX 4-bit model instead — see "
            "docs/runbook-deploy.md"
        )
    from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

    return UnslothInferenceBackend(model_dir)


def _real_backend(model_dir: str) -> InferenceBackend:
    backend_choice = os.environ.get(BACKEND_ENV_VAR)
    if backend_choice not in (None, "", "unsloth", "mlx"):
        raise ValueError(f"{BACKEND_ENV_VAR} must be 'unsloth' or 'mlx', got {backend_choice!r}")

    if backend_choice == "mlx":
        from tonofdevelopervoice.serve.mlx_backend import MlxInferenceBackend

        return MlxInferenceBackend(model_dir)
    if backend_choice == "unsloth":
        return _unsloth_or_raise(model_dir)

    if _is_mlx_model_dir(model_dir):
        from tonofdevelopervoice.serve.mlx_backend import MlxInferenceBackend

        return MlxInferenceBackend(model_dir)
    if _is_adapter_dir(model_dir):
        return _unsloth_or_raise(model_dir)

    raise ValueError(
        f"cannot tell what kind of model {model_dir!r} is (no config.json with a "
        f"'quantization' key, and no adapter_config.json); set {BACKEND_ENV_VAR} "
        "to 'unsloth' or 'mlx' explicitly"
    )


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
