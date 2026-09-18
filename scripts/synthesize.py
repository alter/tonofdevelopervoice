# synthesize.py
import argparse
import json
import random
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any

from tonofdevelopervoice.dataset.assemble import (
    PrecomputedSynthesizer,
    build_pairs,
    dedup_records,
    load_raw_records,
    split_train_eval,
)

SYSTEM_PROMPT = (
    "You rewrite terse, real open-source commit messages into the kind of verbose, "
    "generic-sounding commit message an AI coding assistant tends to produce. Keep the "
    "same technical meaning and facts, but expand it: add hedging phrasing, explain the "
    "obvious, use a bulleted 'Changes:' list, favor generic verbs like 'update'/'improve', "
    "and drop project-specific jargon and terse imperative style. Output only the rewritten "
    "commit message text, nothing else. /no_think"
)


def synthesize_one(endpoint: str, model: str, authentic_text: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": authentic_text},
        ],
        "max_tokens": 600,
        "temperature": 0.8,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json", "Connection": "close"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read())
    content: str = data["choices"][0]["message"]["content"].strip()
    if not content:
        raise ValueError("model returned empty content (likely truncated reasoning)")
    return content


def synthesize_one_bounded(
    executor: ThreadPoolExecutor, endpoint: str, model: str, authentic_text: str, deadline: float
) -> str:
    future = executor.submit(synthesize_one, endpoint, model, authentic_text)
    try:
        return future.result(timeout=deadline)
    except FutureTimeoutError as exc:
        raise TimeoutError(f"no response within {deadline}s (hard wall-clock cutoff)") from exc


def sample_records(records: list[dict[str, Any]], count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    pool = list(records)
    rng.shuffle(pool)
    return pool[:count]


def write_jsonl(pairs: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair) + "\n")


def load_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    mapping: dict[str, str] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            mapping[entry["sha"]] = entry["synthetic"]
    return mapping


def append_cache(path: Path, sha: str, synthetic: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"sha": sha, "synthetic": synthetic}) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--train-out", type=Path, default=Path("data/dataset/train.jsonl"))
    parser.add_argument("--eval-out", type=Path, default=Path("data/dataset/eval.jsonl"))
    parser.add_argument("--cache", type=Path, default=Path("data/dataset/.synthesis_cache.jsonl"))
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--eval-fraction", type=float, default=0.1)
    parser.add_argument("--per-call-timeout", type=float, default=45.0)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument(
        "--model", default="Qwen3.8-27B-Uncensored-Cyber-IQ4_XS-imatrix-fromq8.gguf"
    )
    args = parser.parse_args()

    records = dedup_records(load_raw_records(args.raw_dir))
    sampled = sample_records(records, args.count, args.seed)

    mapping = load_cache(args.cache)
    failures = 0
    with ThreadPoolExecutor(max_workers=1) as executor:
        for i, record in enumerate(sampled):
            sha = record["sha"]
            if sha in mapping:
                continue
            try:
                synthetic = synthesize_one_bounded(
                    executor, args.endpoint, args.model, record["text"], args.per_call_timeout
                )
            except (urllib.error.URLError, KeyError, json.JSONDecodeError, ValueError,
                     TimeoutError) as exc:
                failures += 1
                print(f"[{i + 1}/{len(sampled)}] synthesis failed for {sha}: {exc}",
                      file=sys.stderr)
                continue
            mapping[sha] = synthetic
            append_cache(args.cache, sha, synthetic)
            if (i + 1) % 10 == 0:
                print(f"[{i + 1}/{len(sampled)}] synthesized ({failures} failures so far)")

    synthesized_records = [r for r in sampled if r["sha"] in mapping]
    train_records, eval_records = split_train_eval(synthesized_records, args.eval_fraction)

    synthesizer = PrecomputedSynthesizer(mapping)
    train_pairs = build_pairs(train_records, synthesizer)
    eval_pairs = build_pairs(eval_records, synthesizer)

    write_jsonl(train_pairs, args.train_out)
    write_jsonl(eval_pairs, args.eval_out)
    print(f"wrote {len(train_pairs)} train pairs to {args.train_out}")
    print(f"wrote {len(eval_pairs)} eval pairs to {args.eval_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
