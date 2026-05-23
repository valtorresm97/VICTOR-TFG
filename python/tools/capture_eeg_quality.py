from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path


PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
STATE_DIR = PROJECT_ROOT / "state"
REQUEST_PATH = STATE_DIR / "capture_request.json"
STATUS_PATH = STATE_DIR / "capture_status.json"


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Request a real EEG capture from the running Arduino App Lab app. "
            "This command can run with normal python3 because Bridge capture is "
            "performed inside python/main.py."
        )
    )
    parser.add_argument("--condition", required=True, help="Condition label, for example head_fp1_fp2_eyes_open.")
    parser.add_argument("--duration", type=float, default=60.0, help="Capture duration in seconds.")
    parser.add_argument("--notes", default="", help="Free text notes stored in metadata.json.")
    parser.add_argument("--timeout-extra", type=float, default=20.0, help="Extra seconds to wait after duration.")
    parser.add_argument("--no-wait", action="store_true", help="Only write the request and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request_id = uuid.uuid4().hex
    request = {
        "command": "start",
        "request_id": request_id,
        "condition": args.condition,
        "duration_sec": float(args.duration),
        "notes": args.notes,
        "requested_at_unix": time.time(),
    }

    _atomic_write_json(REQUEST_PATH, request)
    print(f"[capture-request] request_id={request_id}")
    print(f"[capture-request] condition={args.condition} duration={args.duration:.1f}s")
    print("[capture-request] waiting for the running App Lab app to record the capture...")

    if args.no_wait:
        print(f"[capture-request] wrote {REQUEST_PATH}")
        return 0

    deadline = time.monotonic() + float(args.duration) + float(args.timeout_extra)
    last_state = None

    while time.monotonic() < deadline:
        status = _read_json(STATUS_PATH)
        if status.get("request_id") == request_id:
            state = status.get("state")
            if state != last_state:
                print(f"[capture-request] state={state}")
                last_state = state
            if state in {"completed", "stopped"}:
                capture_dir = status.get("capture_dir")
                print(f"[capture-request] saved: {capture_dir}")
                return 0
            if state == "error":
                print(f"[capture-request] ERROR: {status.get('error')}", file=sys.stderr)
                return 1
        time.sleep(0.5)

    print(
        "[capture-request] timeout waiting for capture. "
        "Make sure the App Lab app is running on this same checkout.",
        file=sys.stderr,
    )
    print(f"[capture-request] request file: {REQUEST_PATH}", file=sys.stderr)
    print(f"[capture-request] status file: {STATUS_PATH}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
