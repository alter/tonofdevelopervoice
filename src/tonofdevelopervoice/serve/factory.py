# factory.py
import os
import sys

from tonofdevelopervoice.serve.backend import InferenceBackend, StubInferenceBackend

MODEL_DIR_ENV_VAR = "TONOFDEVELOPERVOICE_MODEL_DIR"


def default_backend() -> InferenceBackend:
    model_dir = os.environ.get(MODEL_DIR_ENV_VAR)
    if model_dir:
        from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

        return UnslothInferenceBackend(model_dir)
    print(
        f"WARNING: {MODEL_DIR_ENV_VAR} is not set — using StubInferenceBackend, which "
        "returns the input unchanged (prefixed with '[rewritten] '). Set "
        f"{MODEL_DIR_ENV_VAR} to a trained adapter's path to use the real model.",
        file=sys.stderr,
    )
    return StubInferenceBackend()
