from __future__ import annotations

import argparse
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKETCH_PATH = PROJECT_ROOT / "sketch" / "sketch.ino"

MODES = {
    "normal": 0,
    "shorted_inputs": 1,
    "test_signal_internal": 2,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set compile-time ADS1299 diagnostic mode in sketch.ino.")
    parser.add_argument("mode", choices=sorted(MODES), help="Diagnostic mode to compile.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    value = MODES[args.mode]
    text = SKETCH_PATH.read_text(encoding="utf-8")
    new_text, count = re.subn(
        r"(^#define\s+ADS_DIAGNOSTIC_MODE\s+)\d+(\s*$)",
        rf"\g<1>{value}\2",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise SystemExit("Could not find '#define ADS_DIAGNOSTIC_MODE <n>' in sketch/sketch.ino")
    SKETCH_PATH.write_text(new_text, encoding="utf-8")
    print(f"ADS_DIAGNOSTIC_MODE={value} ({args.mode}) written to {SKETCH_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
