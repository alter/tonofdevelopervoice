# check_env.py
import argparse
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

DEFAULT_REQUIREMENTS = Path(__file__).resolve().parent / "requirements.txt"


def parse_requirements(path: Path) -> dict[str, str]:
    pins = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, pinned_version = line.partition("==")
        pins[name.strip()] = pinned_version.strip()
    return pins


def check_versions(requirements_path: Path) -> list[str]:
    problems = []
    for name, expected in parse_requirements(requirements_path).items():
        try:
            installed = version(name)
        except PackageNotFoundError:
            problems.append(f"{name}: not installed (expected {expected})")
            continue
        if installed != expected:
            problems.append(f"{name}: installed {installed}, expected {expected}")
    return problems


def check_cuda() -> list[str]:
    import torch

    if not torch.cuda.is_available():
        return ["torch.cuda.is_available() is False"]
    if not torch.cuda.is_bf16_supported():
        return ["torch.cuda.is_bf16_supported() is False"]
    return []


def check_torchvision_nms() -> list[str]:
    import torch
    import torchvision

    boxes = torch.tensor([[0.0, 0.0, 1.0, 1.0]])
    scores = torch.tensor([0.9])
    try:
        torchvision.ops.nms(boxes, scores, 0.5)
    except Exception as exc:
        return [f"torchvision.ops.nms failed: {exc}"]
    return []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail if the installed training environment drifts from requirements.txt."
    )
    parser.add_argument("requirements", nargs="?", type=Path, default=DEFAULT_REQUIREMENTS)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    problems = check_versions(args.requirements)
    problems += check_cuda()
    problems += check_torchvision_nms()

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print("environment OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
