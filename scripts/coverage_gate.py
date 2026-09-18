# coverage_gate.py
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

GATE_FILE = Path(".coverage-gate.json")


def run_coverage() -> float:
    subprocess.run(
        ["pytest", "--cov=src", "--cov-report=xml", "-q"],
        check=True,
    )
    tree = ET.parse("coverage.xml")
    root = tree.getroot()
    return float(root.attrib["line-rate"]) * 100


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run", action="store_true", help="run pytest with coverage and check the floor"
    )
    parser.add_argument(
        "--set-floor", action="store_true", help="record the current coverage as the new floor"
    )
    args = parser.parse_args()

    if not args.run:
        parser.error("--run is required")

    current = run_coverage()

    if args.set_floor or not GATE_FILE.exists():
        GATE_FILE.write_text(json.dumps({"floor": current}, indent=2) + "\n")
        print(f"coverage floor set to {current:.2f}%")
        return 0

    data = json.loads(GATE_FILE.read_text())
    floor = float(data["floor"])

    if current < floor - 1e-9:
        print(f"coverage {current:.2f}% is below the floor {floor:.2f}%")
        return 1

    if current > floor:
        data["floor"] = current
        GATE_FILE.write_text(json.dumps(data, indent=2) + "\n")
        print(f"coverage floor raised to {current:.2f}%")
    else:
        print(f"coverage {current:.2f}% meets the floor {floor:.2f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
