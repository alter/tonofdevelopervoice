# train.py
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tonofdevelopervoice.train.config import TrainingConfig, load_training_config  # noqa: E402

PROMPT_TEMPLATE = (
    "Rewrite the following text in terse, authentic open-source engineering "
    "commit/PR style, preserving its meaning:\n\n{input}\n\n### Rewritten:\n{output}"
)

LORA_TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]


def load_dataset_jsonl(path: str) -> Any:
    from datasets import Dataset

    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return Dataset.from_list(records)


def format_example(example: dict[str, str]) -> dict[str, str]:
    return {"text": PROMPT_TEMPLATE.format(input=example["input"], output=example["output"])}


def train(config: TrainingConfig) -> None:
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config.base_model,
        max_seq_length=config.max_seq_length,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=LORA_TARGET_MODULES,
    )

    train_dataset = load_dataset_jsonl(config.train_path).map(format_example)
    eval_dataset = load_dataset_jsonl(config.eval_path).map(format_example)

    training_args = SFTConfig(
        output_dir=config.output_dir,
        per_device_train_batch_size=config.per_device_train_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        num_train_epochs=config.num_train_epochs,
        max_seq_length=config.max_seq_length,
        dataset_text_field="text",
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        bf16=True,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        args=training_args,
    )
    trainer.train()
    model.save_pretrained(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)


if __name__ == "__main__":
    train(load_training_config(Path("training/config.yaml")))
