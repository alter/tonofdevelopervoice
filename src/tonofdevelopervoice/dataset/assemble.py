# assemble.py
import hashlib
import json
from pathlib import Path
from typing import Any, Protocol


def load_raw_records(raw_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
    return records


def dedup_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for record in records:
        sha = record["sha"]
        if sha in seen:
            continue
        seen.add(sha)
        deduped.append(record)
    return deduped


def _split_bucket(sha: str, eval_fraction: float) -> bool:
    digest = hashlib.sha256(sha.encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % 10_000
    return bucket < int(eval_fraction * 10_000)


def split_train_eval(
    records: list[dict[str, Any]], eval_fraction: float = 0.1
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    eval_split: list[dict[str, Any]] = []
    for record in records:
        if _split_bucket(record["sha"], eval_fraction):
            eval_split.append(record)
        else:
            train.append(record)
    return train, eval_split


class Synthesizer(Protocol):
    def synthesize(self, key: str) -> str: ...


class PrecomputedSynthesizer:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping

    def synthesize(self, key: str) -> str:
        return self._mapping[key]


def build_pairs(
    records: list[dict[str, Any]], synthesizer: Synthesizer
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for record in records:
        try:
            synthetic_input = synthesizer.synthesize(record["sha"])
        except KeyError:
            continue
        pairs.append(
            {
                "input": synthetic_input,
                "output": record["text"],
                "project": record["repo"],
            }
        )
    return pairs
