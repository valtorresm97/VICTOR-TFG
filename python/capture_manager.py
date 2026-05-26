from __future__ import annotations

import csv
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO


from app_state import atomic_write_json
from eeg_contract import (
    BLOCK_SAMPLES,
    EEG_BLOCK_EVENT,
    EegBlockPayloadError,
    FS_HZ,
    LSB_V,
    NUM_CH,
    PGA_GAIN,
    STATUS_MASK,
    STATUS_PREFIX,
    is_valid_ads1299_status,
    iter_eeg_block_samples,
)
from runtime_config import runtime_state_dir


VREF_V_ASSUMED = LSB_V * PGA_GAIN * ((2 ** 23) - 1)

CAPTURE_FIELDNAMES = [
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


def _safe_condition(value: str) -> str:
    chars = []
    for ch in value.strip().lower():
        if ch.isalnum() or ch in {"_", "-"}:
            chars.append(ch)
        elif ch.isspace():
            chars.append("_")
    return "".join(chars).strip("_") or "unknown_condition"


def _git_value(project_root: Path, args: list[str]) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=str(project_root),
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip() or None
    except Exception:
        return None


class CaptureManager:
    """
    Captura bloques EEG desde la app App Lab.

    El terminal normal de Linux no tiene el modulo `arduino`, asi que la CLI
    escribe `state/capture_request.json` y este gestor, que vive dentro de la
    app, graba los bloques reales que ya llegan por Bridge.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.state_dir = runtime_state_dir(self.project_root)
        self.captures_root = self.project_root / "captures"
        self.request_path = self.state_dir / "capture_request.json"
        self.status_path = self.state_dir / "capture_status.json"

        self.active = False
        self.completed = False
        self.request_id: str | None = None
        self.condition = ""
        self.notes = ""
        self.duration_sec = 0.0
        self.capture_dir: Path | None = None
        self.started_monotonic = 0.0
        self.started_unix = 0.0
        self.last_seen_request_id: str | None = None
        self.last_status_write = 0.0
        self.last_csv_flush = 0.0

        self.csv_path: Path | None = None
        self.csv_file: TextIO | None = None
        self.csv_writer: csv.DictWriter | None = None
        self.csv_rows_written = 0
        self.rx_blocks_total = 0
        self.rx_samples_total = 0
        self.malformed_blocks_total = 0
        self.invalid_status_total = 0
        self.sample_gaps_total = 0
        self.block_gaps_total = 0
        self.last_sample_idx: int | None = None
        self.last_block_idx: int | None = None

    def _reset_counters(self) -> None:
        self._close_csv()
        self.csv_path = None
        self.csv_writer = None
        self.csv_rows_written = 0
        self.last_csv_flush = 0.0
        self.rx_blocks_total = 0
        self.rx_samples_total = 0
        self.malformed_blocks_total = 0
        self.invalid_status_total = 0
        self.sample_gaps_total = 0
        self.block_gaps_total = 0
        self.last_sample_idx = None
        self.last_block_idx = None

    def _open_csv(self) -> None:
        if self.capture_dir is None:
            raise RuntimeError("capture_dir is not set")
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.capture_dir / "eeg_timeseries.csv"
        self.csv_file = self.csv_path.open("w", newline="", encoding="utf-8")
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=CAPTURE_FIELDNAMES)
        self.csv_writer.writeheader()
        self.csv_file.flush()
        self.last_csv_flush = time.monotonic()

    def _close_csv(self) -> None:
        if self.csv_file is None:
            return
        try:
            self.csv_file.flush()
        finally:
            self.csv_file.close()
        self.csv_file = None
        self.csv_writer = None

    def _write_capture_row(self, row: dict) -> None:
        if self.csv_writer is None:
            raise RuntimeError("capture CSV writer is not open")
        self.csv_writer.writerow(row)
        self.csv_rows_written += 1

        now = time.monotonic()
        if self.csv_file is not None and (now - self.last_csv_flush) >= 1.0:
            self.csv_file.flush()
            self.last_csv_flush = now

    def _status_payload(self, state: str) -> dict:
        elapsed = time.monotonic() - self.started_monotonic if self.started_monotonic else 0.0
        return {
            "state": state,
            "request_id": self.request_id,
            "condition": self.condition,
            "duration_sec": self.duration_sec,
            "elapsed_sec": elapsed,
            "capture_dir": str(self.capture_dir) if self.capture_dir else None,
            "rx_blocks_total": self.rx_blocks_total,
            "rx_samples_total": self.rx_samples_total,
            "csv_rows_written": self.csv_rows_written,
            "invalid_status_total": self.invalid_status_total,
            "sample_gaps_total": self.sample_gaps_total,
            "block_gaps_total": self.block_gaps_total,
            "updated_at_unix": time.time(),
        }

    def _publish_status(self, state: str, force: bool = False) -> None:
        now = time.monotonic()
        if not force and (now - self.last_status_write) < 0.5:
            return
        atomic_write_json(self.status_path, self._status_payload(state), indent=2, sort_keys=True)
        self.last_status_write = now

    def poll_request(self) -> None:
        if not self.request_path.exists():
            return

        try:
            request = json.loads(self.request_path.read_text(encoding="utf-8"))
        except Exception as exc:
            atomic_write_json(
                self.status_path,
                {"state": "error", "error": f"cannot_read_request: {exc}", "updated_at_unix": time.time()},
                indent=2,
                sort_keys=True,
            )
            return

        request_id = str(request.get("request_id") or "")
        if not request_id or request_id == self.last_seen_request_id:
            return

        command = str(request.get("command") or "start").lower()
        if command == "stop":
            if self.active:
                self.finish("stopped")
            self.last_seen_request_id = request_id
            return

        if command != "start":
            atomic_write_json(
                self.status_path,
                {"state": "error", "error": f"unsupported_command: {command}", "updated_at_unix": time.time()},
                indent=2,
                sort_keys=True,
            )
            self.last_seen_request_id = request_id
            return

        if self.active:
            atomic_write_json(
                self.status_path,
                {"state": "busy", "active_request_id": self.request_id, "updated_at_unix": time.time()},
                indent=2,
                sort_keys=True,
            )
            return

        self.start(request)
        self.last_seen_request_id = request_id

    def start(self, request: dict) -> None:
        self._reset_counters()
        self.request_id = str(request.get("request_id") or f"capture-{int(time.time())}")
        self.condition = _safe_condition(str(request.get("condition") or "unknown_condition"))
        self.notes = str(request.get("notes") or "")
        self.duration_sec = max(1.0, float(request.get("duration_sec") or 60.0))

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.capture_dir = self.captures_root / f"{stamp}_{self.condition}"
        self.started_monotonic = time.monotonic()
        self.started_unix = time.time()
        self.completed = False
        try:
            self._open_csv()
        except Exception as exc:
            self.active = False
            atomic_write_json(
                self.status_path,
                {
                    "state": "error",
                    "request_id": self.request_id,
                    "error": f"cannot_open_capture_csv: {exc}",
                    "updated_at_unix": time.time(),
                },
                indent=2,
                sort_keys=True,
            )
            return

        self.active = True
        self._publish_status("recording", force=True)

    def add_block(
        self,
        block_idx: int,
        first_sample_idx: int,
        sample_count: int,
        statuses,
        samples,
    ) -> None:
        if not self.active:
            return

        if sample_count <= 0 or sample_count > BLOCK_SAMPLES:
            self.malformed_blocks_total += 1
            return

        now_mono = time.monotonic()
        now_unix = time.time()
        block_idx = int(block_idx)
        first_sample_idx = int(first_sample_idx)

        if self.last_block_idx is not None and block_idx > self.last_block_idx + 1:
            self.block_gaps_total += block_idx - (self.last_block_idx + 1)
        if self.last_sample_idx is not None and first_sample_idx > self.last_sample_idx + 1:
            self.sample_gaps_total += first_sample_idx - (self.last_sample_idx + 1)

        try:
            block_samples = tuple(iter_eeg_block_samples(first_sample_idx, statuses, samples, num_ch=NUM_CH))
        except EegBlockPayloadError:
            self.malformed_blocks_total += 1
            return

        if len(block_samples) != sample_count:
            self.malformed_blocks_total += 1
            return

        try:
            for sample_idx, sample_in_block, status, sample in block_samples:
                if not is_valid_ads1299_status(status):
                    self.invalid_status_total += 1
                self._write_capture_row(
                    {
                        "t_capture_sec": now_mono - self.started_monotonic,
                        "timestamp_unix": now_unix,
                        "block_idx": block_idx,
                        "sample_idx": sample_idx,
                        "sample_in_block": sample_in_block,
                        "status": status,
                        "ch1_uV": int(sample[0]),
                        "ch2_uV": int(sample[1]),
                        "ch3_uV": int(sample[2]),
                        "ch4_uV": int(sample[3]),
                    }
                )
        except Exception as exc:
            self._close_csv()
            self.active = False
            atomic_write_json(
                self.status_path,
                {
                    "state": "error",
                    "request_id": self.request_id,
                    "capture_dir": str(self.capture_dir) if self.capture_dir else None,
                    "error": f"cannot_write_capture_csv: {exc}",
                    "updated_at_unix": time.time(),
                },
                indent=2,
                sort_keys=True,
            )
            return

        self.rx_blocks_total += 1
        self.rx_samples_total += sample_count
        self.last_block_idx = block_idx
        self.last_sample_idx = first_sample_idx + sample_count - 1
        self._publish_status("recording")

    def step(self) -> None:
        if not self.active:
            return
        if (time.monotonic() - self.started_monotonic) >= self.duration_sec:
            self.finish("completed")
        else:
            self._publish_status("recording")

    def finish(self, state: str = "completed") -> None:
        if not self.active or self.capture_dir is None:
            return

        self._close_csv()

        metadata = {
            "condition": self.condition,
            "duration_requested_sec": self.duration_sec,
            "duration_observed_sec": time.monotonic() - self.started_monotonic,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "started_unix": self.started_unix,
            "fs_hz_expected": FS_HZ,
            "num_channels": NUM_CH,
            "block_samples_expected": BLOCK_SAMPLES,
            "bridge_event": EEG_BLOCK_EVENT,
            "value_units": "microvolts",
            "raw_counts_available": False,
            "firmware_pipeline": "ADS1299 raw counts -> volts -> MCU HP 0.5 Hz -> notch 50 Hz -> LP 40 Hz -> microvolts",
            "ads1299": {
                "expected_device": "ADS1299-4PAG",
                "expected_id": "0x3C",
                "status_prefix_expected": f"0x{STATUS_PREFIX:06X}",
                "status_mask": f"0x{STATUS_MASK:06X}",
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
                "csv_rows_written": self.csv_rows_written,
            },
            "git": {
                "branch": _git_value(self.project_root, ["branch", "--show-current"]),
                "commit": _git_value(self.project_root, ["rev-parse", "HEAD"]),
                "dirty": bool(_git_value(self.project_root, ["status", "--short"])),
            },
            "notes": self.notes,
        }
        atomic_write_json(self.capture_dir / "metadata.json", metadata, indent=2, sort_keys=True)

        self.active = False
        self.completed = state == "completed"
        self._publish_status(state, force=True)

    def get_status(self) -> dict:
        if self.active:
            return self._status_payload("recording")
        if self.status_path.exists():
            try:
                data = json.loads(self.status_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {"state": "idle", "updated_at_unix": time.time()}
