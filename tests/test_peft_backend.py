# test_peft_backend.py
import sys
from collections.abc import Generator
from types import ModuleType
from unittest.mock import MagicMock

import pytest


class FakeEncoding(dict[str, MagicMock]):
    def to(self, _device: object) -> "FakeEncoding":
        return self


class FakeNoGrad:
    def __enter__(self) -> "FakeNoGrad":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _make_fake_torch(cuda_available: bool, mps_available: bool) -> ModuleType:
    torch_module = ModuleType("torch")
    torch_module.float16 = "float16"  # type: ignore[attr-defined]
    torch_module.no_grad = FakeNoGrad  # type: ignore[attr-defined]
    cuda_ns = ModuleType("torch.cuda")
    cuda_ns.is_available = lambda: cuda_available  # type: ignore[attr-defined]
    torch_module.cuda = cuda_ns  # type: ignore[attr-defined]
    backends_ns = ModuleType("torch.backends")
    mps_ns = ModuleType("torch.backends.mps")
    mps_ns.is_available = lambda: mps_available  # type: ignore[attr-defined]
    backends_ns.mps = mps_ns  # type: ignore[attr-defined]
    torch_module.backends = backends_ns  # type: ignore[attr-defined]
    return torch_module


@pytest.fixture
def fake_peft_stack() -> Generator[dict[str, MagicMock], None, None]:
    fake_tokenizer = MagicMock()
    fake_base_model = MagicMock()
    fake_peft_model = MagicMock()
    fake_peft_model.to.return_value = fake_peft_model

    fake_auto_tokenizer = MagicMock()
    fake_auto_tokenizer.from_pretrained.return_value = fake_tokenizer
    fake_auto_model = MagicMock()
    fake_auto_model.from_pretrained.return_value = fake_base_model
    fake_peft_model_cls = MagicMock()
    fake_peft_model_cls.from_pretrained.return_value = fake_peft_model

    torch_module = _make_fake_torch(cuda_available=False, mps_available=False)
    transformers_module = ModuleType("transformers")
    transformers_module.AutoModelForCausalLM = fake_auto_model  # type: ignore[attr-defined]
    transformers_module.AutoTokenizer = fake_auto_tokenizer  # type: ignore[attr-defined]
    peft_module = ModuleType("peft")
    peft_module.PeftModel = fake_peft_model_cls  # type: ignore[attr-defined]

    originals = {
        name: sys.modules.get(name) for name in ("torch", "transformers", "peft")
    }
    sys.modules["torch"] = torch_module
    sys.modules["transformers"] = transformers_module
    sys.modules["peft"] = peft_module
    try:
        yield {
            "tokenizer": fake_tokenizer,
            "base_model": fake_base_model,
            "model": fake_peft_model,
            "auto_tokenizer": fake_auto_tokenizer,
            "auto_model": fake_auto_model,
            "peft_model_cls": fake_peft_model_cls,
        }
    finally:
        for name, original in originals.items():
            if original is not None:
                sys.modules[name] = original
            else:
                del sys.modules[name]


def test_constructs_base_model_and_applies_adapter(
    fake_peft_stack: dict[str, MagicMock],
) -> None:
    from tonofdevelopervoice.serve.peft_backend import BASE_MODEL_NAME, PeftInferenceBackend

    PeftInferenceBackend("training/output")

    fake_peft_stack["auto_tokenizer"].from_pretrained.assert_called_once_with("training/output")
    _, kwargs = fake_peft_stack["auto_model"].from_pretrained.call_args
    assert fake_peft_stack["auto_model"].from_pretrained.call_args[0][0] == BASE_MODEL_NAME
    assert kwargs["dtype"] == "float16"
    fake_peft_stack["peft_model_cls"].from_pretrained.assert_called_once_with(
        fake_peft_stack["base_model"], "training/output"
    )
    fake_peft_stack["model"].eval.assert_called_once()


def test_rewrite_builds_prompt_generates_and_decodes(
    fake_peft_stack: dict[str, MagicMock],
) -> None:
    from tonofdevelopervoice.serve.peft_backend import PeftInferenceBackend

    fake_encoded = FakeEncoding({"input_ids": MagicMock()})
    fake_peft_stack["tokenizer"].return_value = fake_encoded
    fake_peft_stack["model"].generate.return_value = ["ids"]
    fake_peft_stack["tokenizer"].decode.return_value = (
        "Rewrite the following text in terse, authentic open-source engineering "
        "commit/PR style, preserving its meaning:\n\nfix bug\n\n### Rewritten:\nfix null deref"
    )

    backend = PeftInferenceBackend("training/output")
    result = backend.rewrite("fix bug")

    assert result == "fix null deref"
    fake_peft_stack["model"].generate.assert_called_once()


def test_satisfies_inference_backend_protocol(fake_peft_stack: dict[str, MagicMock]) -> None:
    from tonofdevelopervoice.serve.backend import InferenceBackend
    from tonofdevelopervoice.serve.peft_backend import PeftInferenceBackend

    backend: InferenceBackend = PeftInferenceBackend("training/output")
    assert isinstance(backend, InferenceBackend)


def test_select_device_prefers_cuda_then_mps_then_cpu() -> None:
    from tonofdevelopervoice.serve.peft_backend import _select_device

    originals = {"torch": sys.modules.get("torch")}
    try:
        sys.modules["torch"] = _make_fake_torch(cuda_available=True, mps_available=True)
        assert _select_device() == "cuda"

        sys.modules["torch"] = _make_fake_torch(cuda_available=False, mps_available=True)
        assert _select_device() == "mps"

        sys.modules["torch"] = _make_fake_torch(cuda_available=False, mps_available=False)
        assert _select_device() == "cpu"
    finally:
        if originals["torch"] is not None:
            sys.modules["torch"] = originals["torch"]
        else:
            del sys.modules["torch"]
