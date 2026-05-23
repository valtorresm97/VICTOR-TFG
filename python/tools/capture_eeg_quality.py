from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


FS_HZ = 250
NUM_CH = 4
BLOCK_SAMPLES = 8
STATUS_PREFIX = 0xC00000
STATUS_MASK = 0xF00000
LSB_V = 2.235e-8
PGA_GAIN = 24
VREF_V_ASSUMED = LSB_V * PGA_GAIN * ((2 ** 23) - 1)


class CaptureComplete(Exception):
    pass


def _git_value(args: list[str]) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=str(PROJECT_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip() or None
    except Exception:
        return None


def _safe_condition(value: str) -> str:
    allowed = []
    for ch in value.strip().lower():
        if ch.isalnum() or ch in {"_", "-"}:
            allowed.append(ch)
        elif ch.isspace():
            allowed.append("_")
    return "".join(allowed).strip("_") or "unknown_condition"


class EegCaptureRecorder:
    def __init__(self, capture_dir: Path, condition: str, duration_sec: float):
        self.capture_dir = capture_dir
        self.condition = condition
        self.duration_sec = float(duration_sec)
        self.started_monotonic = time.monotonic()
        self.started_unix = time.time()
        self.rows: list[dict] = []
        self.lock = Lock()

        self.rx_blocks_total = 0
        self.rx_samples_total = 0
        self.malformed_blocks_total = 0
        self.invalid_status_total = 0
        self.sample_gaps_total = 0
        self.block_gaps_total = 0
        self.last_sample_idx: int | None = None
        self.last_block_idx: int | None = None

    def linux_started(self) -> bool:
        return True

    def eeg_block_uV(self, block_idx: int, first_sample_idx: int, sample_count: int, *vals: int):
        try:
            block_idx = int(block_idx)
            first_sample_idx = int(first_sample_idx)
            sample_count = int(sample_count)
        except Exception:
            with self.lock:
                self.malformed_blocks_total += 1
            return

        stride = 1 + NUM_CH
        if sample_count <= 0 or sample_count > BLOCK_SAMPLES or len(vals) != sample_count * stride:
            with self.lock:
                self.malformed_blocks_total += 1
            return

        now_mono = time.monotonic()
        now_unix = time.time()
        parsed_rows = []
        invalid_status = 0

        for i in range(sample_count):
            base = i * stride
            status = int(vals[base])
            if (status & STATUS_MASK) != STATUS_PREFIX:
                invalid_status += 1
            sample_idx = first_sample_idx + i
            parsed_rows.append(
                {
                    "t_capture_sec": now_mono - self.started_monotonic,
                    "timestamp_unix": now_unix,
                    "block_idx": block_idx,
                    "sample_idx": sample_idx,
                    "sample_in_block": i,
                    "status": status,
                    "ch1_uV": int(vals[base + 1]),
                    "ch2_uV": int(vals[base + 2]),
                    "ch3_uV": int(vals[base + 3]),
                    "ch4_uV": int(vals[base + 4]),
                }
            )

        with self.lock:
            if self.last_block_idx is not None and block_idx > self.last_block_idx + 1:
                self.block_gaps_total += block_idx - (self.last_block_idx + 1)
            if self.last_sample_idx is not None and first_sample_idx > self.last_sample_idx + 1:
                self.sample_gaps_total += first_sample_idx - (self.last_sample_idx + 1)

            self.rows.extend(parsed_rows)
            self.rx_blocks_total += 1
            self.rx_samples_total += sample_count
            self.invalid_status_total += invalid_status
            self.last_block_idx = block_idx
            self.last_sample_idx = first_sample_idx + sample_count - 1

    def elapsed(self) -> float:
        return time.monotonic() - self.started_monotonic

    def save(self, args: argparse.Namespace) -> None:
        self.capture_dir.mkdir(parents=True, exist_ok=True)

        with self.lock:
            rows = list(self.rows)
            metadata = {
                "condition": self.condition,
                "duration_requested_sec": self.duration_sec,
                "duration_observed_sec": self.elapsed(),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "started_unix": self.started_unix,
                "fs_hz_expected": FS_HZ,
                "num_channels": NUM_CH,
                "block_samples_expected": BLOCK_SAMPLES,
                "bridge_event": "eeg_block_uV",
                "value_units": "microvolts",
                "raw_counts_available": False,
                "firmware_pipeline": "ADS1299 raw counts -> volts -> MCU HP 0.5 Hz -> notch 50 Hz -> LP 40 Hz -> microvolts",
                "ads1299": {
                    "expected_device": "ADS1299-4PAG",
                    "expected_id": "0x3C",
                    "status_prefix_expected": "0xC00000",
                    "status_mask": "0xF00000",
                    "channels_streamed": 4,
                    "lsb_v_firmware": LSB_V,
                    "pga_gain_assumed": PGA_GAIN,
                    "vref_v_assumed_from_lsb_gain": VREF_V_ASSUMED,
                    "bias_drl_used": False,
                    "lead_off_impedance_measured": False,
                },
                "rx_summary": {
                    "rx_blocks_total": self.rx_blocks_total,
                    "rx_samples_total": self.rx_samples_total,
                    "malformed_blocks_total": self.malformed_blocks_total,
                    "invalid_status_total": self.invalid_status_total,
                    "sample_gaps_total": self.sample_gaps_total,
                    "block_gaps_total": self.block_gaps_total,
                    "last_sample_idx": self.last_sample_idx,
                    "last_block_idx": self.last_block_idx,
                },
                "git": {
                    "branch": _git_value(["branch", "--show-current"]),
                    "commit": _git_value(["rev-parse", "HEAD"]),
                    "dirty": bool(_git_value(["status", "--short"])),
                },
                "command": " ".join(sys.argv),
                "notes": args.notes,
            }

        csv_path = self.capture_dir / "eeg_timeseries.csv"
        fieldnames = [
            "t_capture_sec",
            "timestamp_unix",
            "block_idx",
            "sample_idx",
            "sample_in_block",
            "status",
            "ch1_uV",
            "ch2_uV",
            "ch3_uV",
            "ch4_uV",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        with (self.capture_dir / "metadata.json").open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, sort_keys=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture real EEG blocks from Bridge.notify('eeg_block_uV').")
    parser.add_argument("--condition", required=True, help="Condition label, for example head_fp1_fp2_eyes_open.")
    parser.add_argument("--duration", type=float, default=60.0, help="Capture duration in seconds.")
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "captures"), help="Root directory for captures.")
    parser.add_argument("--notes", default="", help="Free text notes stored in metadata.json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    condition = _safe_condition(args.condition)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    capture_dir = Path(args.output_root) / f"{stamp}_{condition}"
    recorder = EegCaptureRecorder(capture_dir=capture_dir, condition=condition, duration_sec=args.duration)

    try:
        from arduino.app_utils import App, Bridge
    except Exception as exc:
        print(f"ERROR: this capture script must run in Arduino App Lab/UNO Q environment: {exc}", file=sys.stderr)
        return 2

    Bridge.provide("linux_started", recorder.linux_started)
    Bridge.provide("eeg_block_uV", recorder.eeg_block_uV)

    print(f"[capture] writing to {capture_dir}")
    print(f"[capture] condition={condition} duration={args.duration:.1f}s")

    def loop():
        if recorder.elapsed() >= args.duration:
            raise CaptureComplete()
        time.sleep(0.02)

    try:
        App.run(user_loop=loop)
    except CaptureComplete:
        pass
    except KeyboardInterrupt:
        print("[capture] interrupted by user")
    finally:
        recorder.save(args)
        print(f"[capture] saved {recorder.rx_samples_total} samples in {capture_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
