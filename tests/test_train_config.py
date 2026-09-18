# test_train_config.py
from pathlib import Path

import pytest

from tonofdevelopervoice.train.config import TrainingConfig, load_training_config

VALID_YAML = """
base_model: Qwen/Qwen3-8B-Base
train_path: data/dataset/train.jsonl
eval_path: data/dataset/eval.jsonl
output_dir: training/output
max_seq_length: 1024
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
learning_rate: 0.0002
num_train_epochs: 3
per_device_train_batch_size: 4
gradient_accumulation_steps: 4
"""


def test_load_training_config_parses_valid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(VALID_YAML)

    config = load_training_config(path)

    assert isinstance(config, TrainingConfig)
    assert config.base_model == "Qwen/Qwen3-8B-Base"
    assert config.lora_r == 16
    assert config.learning_rate == pytest.approx(0.0002)


def test_load_training_config_raises_for_missing_required_field(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("base_model: Qwen/Qwen3-8B-Base\n")

    with pytest.raises(ValueError, match="train_path"):
        load_training_config(path)


def test_load_training_config_raises_for_wrong_type(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(VALID_YAML.replace("lora_r: 16", 'lora_r: "sixteen"'))

    with pytest.raises(ValueError, match="lora_r"):
        load_training_config(path)


def test_load_training_config_raises_for_non_positive_values(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(VALID_YAML.replace("max_seq_length: 1024", "max_seq_length: 0"))

    with pytest.raises(ValueError, match="max_seq_length"):
        load_training_config(path)


def test_load_training_config_raises_for_empty_string_field(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(VALID_YAML.replace("base_model: Qwen/Qwen3-8B-Base", 'base_model: ""'))

    with pytest.raises(ValueError, match="base_model"):
        load_training_config(path)


def test_load_training_config_raises_for_non_positive_learning_rate(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(VALID_YAML.replace("learning_rate: 0.0002", "learning_rate: -0.1"))

    with pytest.raises(ValueError, match="learning_rate"):
        load_training_config(path)


def test_load_training_config_accepts_zero_dropout(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(VALID_YAML.replace("lora_dropout: 0.05", "lora_dropout: 0.0"))

    config = load_training_config(path)

    assert config.lora_dropout == 0.0


def test_load_training_config_raises_for_dropout_out_of_range(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(VALID_YAML.replace("lora_dropout: 0.05", "lora_dropout: 1.5"))

    with pytest.raises(ValueError, match="lora_dropout"):
        load_training_config(path)


def test_load_training_config_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_training_config(tmp_path / "does-not-exist.yaml")


def test_load_training_config_raises_for_non_mapping_yaml(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("- just\n- a\n- list\n")

    with pytest.raises(ValueError, match="mapping"):
        load_training_config(path)
