# factory.py
import os

from tonofdevelopervoice.serve.backend import InferenceBackend, StubInferenceBackend

MODEL_DIR_ENV_VAR = "TONOFDEVELOPERVOICE_MODEL_DIR"


def default_backend() -> InferenceBackend:
    model_dir = os.environ.get(MODEL_DIR_ENV_VAR)
    if model_dir:
        from tonofdevelopervoice.serve.unsloth_backend import UnslothInferenceBackend

        return UnslothInferenceBackend(model_dir)
    return StubInferenceBackend()
