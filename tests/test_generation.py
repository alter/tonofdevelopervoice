# test_generation.py
from tonofdevelopervoice.serve.generation import GenerationSettings, completion_budget


def test_completion_budget_adds_margin_to_input_length() -> None:
    settings = GenerationSettings(max_completion_tokens=2048, completion_margin=64)
    assert completion_budget(100, settings) == 164


def test_completion_budget_caps_at_max_completion_tokens() -> None:
    settings = GenerationSettings(max_completion_tokens=200, completion_margin=64)
    assert completion_budget(1000, settings) == 200


def test_completion_budget_uses_default_settings_when_none_given() -> None:
    assert completion_budget(10) == 74
