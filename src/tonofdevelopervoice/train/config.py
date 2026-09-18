# config.py
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_REQUIRED_STR_FIELDS = ("base_model", "train_path", "eval_path", "output_dir")
_REQUIRED_INT_FIELDS = (
    "max_seq_length",
    "lora_r",
    "lora_alpha",
    "per_device_train_batch_size",
    "gradient_accumulation_steps",
)
_REQUIRED_FLOAT_FIELDS = ("lora_dropout", "learning_rate", "num_train_epochs")
_ALL_REQUIRED_FIELDS = _REQUIRED_STR_FIELDS + _REQUIRED_INT_FIELDS + _REQUIRED_FLOAT_FIELDS


@dataclass(frozen=True)
class TrainingConfig:
    base_model: str
    train_path: str
    eval_path: str
    output_dir: str
    max_seq_length: int
    lora_r: int
    lora_alpha: int
    lora_dropout: float
    learning_rate: float
    num_train_epochs: float
    per_device_train_batch_size: int
    gradient_accumulation_steps: int


def _require_str(data: dict[str, Any], field: str) -> str:
    value = data[field]
    if not isinstance(value, str) or not value:
        raise ValueError(f"training config field {field} must be a non-empty string")
    return value


def _require_positive_int(data: dict[str, Any], field: str) -> int:
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"training config field {field} must be a positive integer")
    return value


def _require_positive_float(data: dict[str, Any], field: str) -> float:
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise ValueError(f"training config field {field} must be a positive number")
    return float(value)


def _require_dropout(data: dict[str, Any], field: str) -> float:
    value = data[field]
    if isinstance(value, bool) or not isinstance(value, int | float) or not (0 <= value < 1):
        raise ValueError(f"training config field {field} must be in [0, 1)")
    return float(value)


def load_training_config(path: Path) -> TrainingConfig:
    if not Path(path).exists():
        raise FileNotFoundError(f"training config not found: {path}")

    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("training config must be a YAML mapping at the top level")

    missing = [f for f in _ALL_REQUIRED_FIELDS if f not in raw]
    if missing:
        raise ValueError(f"training config is missing required field: {missing[0]}")

    return TrainingConfig(
        base_model=_require_str(raw, "base_model"),
        train_path=_require_str(raw, "train_path"),
        eval_path=_require_str(raw, "eval_path"),
        output_dir=_require_str(raw, "output_dir"),
        max_seq_length=_require_positive_int(raw, "max_seq_length"),
        lora_r=_require_positive_int(raw, "lora_r"),
        lora_alpha=_require_positive_int(raw, "lora_alpha"),
        lora_dropout=_require_dropout(raw, "lora_dropout"),
        learning_rate=_require_positive_float(raw, "learning_rate"),
        num_train_epochs=_require_positive_float(raw, "num_train_epochs"),
        per_device_train_batch_size=_require_positive_int(raw, "per_device_train_batch_size"),
        gradient_accumulation_steps=_require_positive_int(raw, "gradient_accumulation_steps"),
    )
