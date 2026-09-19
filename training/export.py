# export.py
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tonofdevelopervoice.env import load_dotenv  # noqa: E402
from tonofdevelopervoice.serve.prompts import PROMPT_PREFIX_TEMPLATE  # noqa: E402

DEFAULT_BASE = "Qwen/Qwen3-8B-Base"
CLOSE_THRESHOLD = 0.05
DIFFERENT_THRESHOLD = 0.05


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_dir(path: Path) -> str:
    digest = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.is_file():
            digest.update(p.relative_to(path).as_posix().encode())
            digest.update(sha256_file(p).encode())
    return digest.hexdigest()


def load_first_eval_prompt(eval_path: Path) -> str:
    with eval_path.open(encoding="utf-8") as f:
        first = json.loads(f.readline())
    return PROMPT_PREFIX_TEMPLATE.format(input=first["input"])


def last_token_logits(model: object, tokenizer: object, prompt: str, device: str) -> object:
    import torch

    inputs = tokenizer(prompt, return_tensors="pt").to(device)  # type: ignore[attr-defined]
    with torch.no_grad():
        out = model(**inputs)  # type: ignore[operator]
    return out.logits[0, -1, :].float()


def pre_merge_logits(
    peft_model: object, tokenizer: object, prompt: str, device: str
) -> tuple[object, object]:
    # Must run BEFORE merge_and_unload(): merging strips the adapter layers out of
    # peft_model in place, so disable_adapter() has nothing left to disable afterwards.
    with peft_model.disable_adapter():  # type: ignore[attr-defined]
        base_logits = last_token_logits(peft_model, tokenizer, prompt, device)
    adapter_logits = last_token_logits(peft_model, tokenizer, prompt, device)
    return base_logits, adapter_logits


def compare_logits(
    base_logits: object, adapter_logits: object, merged_logits: object
) -> tuple[bool, float, float]:
    diff_bc = (adapter_logits - merged_logits).abs().max().item()  # type: ignore[operator]
    diff_ac = (base_logits - merged_logits).abs().max().item()  # type: ignore[operator]

    print(f"max|adapter-merged| = {diff_bc:.6f} (require < {CLOSE_THRESHOLD})")
    print(f"max|base-merged|    = {diff_ac:.6f} (require > {DIFFERENT_THRESHOLD})")

    if diff_bc >= CLOSE_THRESHOLD:
        print("self-check failed: merged model differs from base+adapter", file=sys.stderr)
        return False, diff_bc, diff_ac
    if diff_ac <= DIFFERENT_THRESHOLD:
        print("self-check failed: merged model equals base", file=sys.stderr)
        return False, diff_bc, diff_ac
    return True, diff_bc, diff_ac


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge a LoRA adapter into its bf16 base model and publish the result."
    )
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--push", default=None, help="Hub repo id to upload the merged model to")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--eval-file",
        default=Path("data/dataset/eval.jsonl"),
        type=Path,
        help="first row's input feeds the self-check prompt",
    )
    return parser


def main() -> int:
    load_dotenv()
    args = build_parser().parse_args()

    import torch
    from huggingface_hub import HfApi
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cpu"
    prompt = load_first_eval_prompt(args.eval_file)

    # float16, not bfloat16: see NOTES.md 2026-09-19 -- merging in bfloat16 rounds
    # W + delta to 7 mantissa bits and fails this file's own self-check (0.25 > 0.05
    # measured directly); float16's 10 mantissa bits pass it with margin (0.039 < 0.05).
    print(f"loading base '{args.base}' at float16 on {device}...")
    base_model = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.float16)
    base_model.to(device)
    tokenizer = AutoTokenizer.from_pretrained(str(args.adapter))

    api = HfApi()
    base_commit = api.model_info(args.base).sha

    print(f"loading adapter '{args.adapter}'...")
    peft_model = PeftModel.from_pretrained(base_model, str(args.adapter))
    peft_model.eval()

    print("computing pre-merge logits (base, base+adapter)...")
    base_logits, adapter_logits = pre_merge_logits(peft_model, tokenizer, prompt, device)

    print("merging...")
    merged_model = peft_model.merge_and_unload()
    merged_model.eval()

    merged_logits = last_token_logits(merged_model, tokenizer, prompt, device)
    ok, diff_bc, diff_ac = compare_logits(base_logits, adapter_logits, merged_logits)
    if not ok:
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    merged_model.save_pretrained(str(args.out), safe_serialization=True)
    tokenizer.save_pretrained(str(args.out))

    written_files = {}
    for p in sorted(args.out.rglob("*")):
        if p.is_file():
            written_files[p.relative_to(args.out).as_posix()] = {
                "sha256": sha256_file(p),
                "size": p.stat().st_size,
            }

    import peft as peft_pkg
    import transformers as transformers_pkg

    manifest: dict[str, object] = {
        "adapter_dir": str(args.adapter),
        "adapter_sha256": sha256_dir(args.adapter),
        "base_repo_id": args.base,
        "base_commit": base_commit,
        "self_check": {
            "prompt_source": str(args.eval_file),
            "max_adapter_minus_merged": diff_bc,
            "max_base_minus_merged": diff_ac,
        },
        "written_files": written_files,
        "versions": {
            "torch": torch.__version__,
            "transformers": transformers_pkg.__version__,
            "peft": peft_pkg.__version__,
        },
        "hub_repo_id": None,
        "hub_commit": None,
    }

    if args.push:
        print(f"pushing to {args.push}...")
        api.create_repo(args.push, exist_ok=True, private=False)
        commit_info = api.upload_folder(folder_path=str(args.out), repo_id=args.push)
        manifest["hub_repo_id"] = args.push
        manifest["hub_commit"] = commit_info.oid

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote manifest to {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
