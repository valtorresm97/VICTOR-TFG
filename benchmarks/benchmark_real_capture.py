from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from benchmark_core import ensure_python_path, make_record, time_function

ensure_python_path()

from eeg_contract import FS_HZ, NUM_CH, BLOCK_SAMPLES, parse_eeg_block_values
from receiver import EEGReceiver
from eeg_signal_processor import EEGSignalProcessor
from dsp_core import DSPCore
from sonification_features import SonificationFeatureAdapter

ITERATIONS_REAL_FAST = 120
WARMUP_REAL_FAST = 12
ITERATIONS_REAL_REPLAY = 12
WARMUP_REAL_REPLAY = 2
FEATURE_WINDOW_SEC = 4.0
FEATURE_HOP_SAMPLES = 64


@dataclass(frozen=True)
class CaptureBlock:
    block_idx: int
    first_sample_idx: int
    sample_count: int
    statuses: tuple[int, ...]
    samples: tuple[tuple[int, ...], ...]

    def flat_vals(self) -> tuple[int, ...]:
        vals: list[int] = []
        for status, sample in zip(self.statuses, self.samples):
            vals.append(int(status))
            vals.extend(int(v) for v in sample)
        return tuple(vals)


def _int_from_row(row: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(float(row.get(key, default)))
    except Exception:
        return int(default)


def discover_latest_capture(root: Path) -> Path | None:
    candidates = []
    for base in (root / "captures", Path("/app/captures")):
        if base.exists():
            candidates.extend([p for p in base.iterdir() if p.is_dir() and (p / "eeg_timeseries.csv").exists()])
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_capture_blocks(capture_dir: Path, *, max_blocks: int | None = None) -> list[CaptureBlock]:
    csv_path = capture_dir / "eeg_timeseries.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe {csv_path}")

    grouped: dict[int, list[tuple[int, int, tuple[int, ...]]]] = {}
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            block_idx = _int_from_row(row, "block_idx", 0)
            sample_idx = _int_from_row(row, "sample_idx", 0)
            status = _int_from_row(row, "status", 0)
            sample = tuple(_int_from_row(row, f"ch{i + 1}_uV", 0) for i in range(NUM_CH))
            grouped.setdefault(block_idx, []).append((sample_idx, status, sample))

    blocks: list[CaptureBlock] = []
    for block_idx in sorted(grouped):
        rows = sorted(grouped[block_idx], key=lambda x: x[0])
        if not rows:
            continue
        first_idx = int(rows[0][0])
        statuses = tuple(int(r[1]) for r in rows)
        samples = tuple(tuple(int(v) for v in r[2]) for r in rows)
        blocks.append(
            CaptureBlock(
                block_idx=int(block_idx),
                first_sample_idx=first_idx,
                sample_count=len(rows),
                statuses=statuses,
                samples=samples,
            )
        )
        if max_blocks is not None and len(blocks) >= int(max_blocks):
            break

    if not blocks:
        raise RuntimeError(f"La captura {capture_dir} no contiene bloques validos")
    return blocks


def blocks_to_uv_matrix(blocks: list[CaptureBlock]) -> np.ndarray:
    samples: list[tuple[int, ...]] = []
    for block in blocks:
        samples.extend(block.samples)
    if not samples:
        return np.empty((0, NUM_CH), dtype=np.float32)
    return np.asarray(samples, dtype=np.float32)


def build_processor_from_blocks(blocks: list[CaptureBlock]) -> EEGSignalProcessor:
    duration_sec = max(10.0, (sum(b.sample_count for b in blocks) / float(FS_HZ)) + 1.0)
    proc = EEGSignalProcessor(fs=FS_HZ, num_channels=NUM_CH, buffer_sec=duration_sec, psd_window_sec=FEATURE_WINDOW_SEC)
    for block in blocks:
        proc.add_block_uV(block.samples)
    return proc


def replay_receiver(blocks: list[CaptureBlock]) -> tuple[int, int]:
    rx = EEGReceiver(fs_hz=FS_HZ, num_ch=NUM_CH, queue_max=max(512, len(blocks) + 1))
    for block in blocks:
        rx.eeg_block_uV(
            block.block_idx,
            block.first_sample_idx,
            block.sample_count,
            *block.flat_vals(),
        )
    return rx.rx_blocks_total, rx.rx_frames_total


def replay_buffer(blocks: list[CaptureBlock]) -> int:
    proc = EEGSignalProcessor(fs=FS_HZ, num_channels=NUM_CH, buffer_sec=10.0, psd_window_sec=FEATURE_WINDOW_SEC)
    total = 0
    for block in blocks:
        total += proc.add_block_uV(block.samples)
    return total


def live_feature_sweep(blocks: list[CaptureBlock]) -> dict[str, int]:
    proc = EEGSignalProcessor(fs=FS_HZ, num_channels=NUM_CH, buffer_sec=10.0, psd_window_sec=FEATURE_WINDOW_SEC)
    adapter = SonificationFeatureAdapter()
    calls = 0
    valid_sonif = 0
    samples_since_feature = 0
    for block in blocks:
        added = proc.add_block_uV(block.samples)
        samples_since_feature += int(added)
        if proc.is_window_ready(FEATURE_WINDOW_SEC) and samples_since_feature >= FEATURE_HOP_SAMPLES:
            features = proc.compute_live_features(0, FEATURE_WINDOW_SEC, psd_method="multitaper")
            diagnostics = proc.compute_quality_diagnostics(channel_idx=0, window_sec=FEATURE_WINDOW_SEC, waveform_sec=2.0)
            quality = {
                "score": 1.0,
                "gate_factor": 1.0,
                "state": "benchmark_real_capture",
                "diagnostics_warnings": diagnostics.get("warnings", []),
            }
            sonif = adapter.update(features, quality)
            calls += 1
            valid_sonif += int(bool(sonif.valid))
            samples_since_feature = 0
    return {"feature_calls": calls, "valid_sonification_calls": valid_sonif}


def run(capture_dir: Path, *, max_blocks: int | None = None) -> list[dict[str, Any]]:
    capture_dir = Path(capture_dir).resolve()
    blocks = load_capture_blocks(capture_dir, max_blocks=max_blocks)
    total_frames = sum(b.sample_count for b in blocks)
    duration_sec = total_frames / float(FS_HZ)
    uv_matrix = blocks_to_uv_matrix(blocks)
    proc = build_processor_from_blocks(blocks)
    x_ch1 = proc.get_signal_window(0, FEATURE_WINDOW_SEC)
    dsp = DSPCore(fs=FS_HZ, window_sec=FEATURE_WINDOW_SEC)

    rows: list[dict[str, Any]] = []
    common_notes = f"captura_real={capture_dir.name}; blocks={len(blocks)}; frames={total_frames}; duration_sec={duration_sec:.2f}"

    first_block = blocks[0]
    summary, _ = time_function(
        lambda: parse_eeg_block_values(first_block.sample_count, first_block.flat_vals(), num_ch=NUM_CH, max_samples=max(BLOCK_SAMPLES, first_block.sample_count)),
        iterations=ITERATIONS_REAL_FAST,
        warmup_iterations=WARMUP_REAL_FAST,
    )
    rows.append(make_record(
        benchmark_id="real_capture.parse_eeg_block_values.first_block",
        module="eeg_contract",
        function="parse_eeg_block_values",
        scenario="real_capture_first_block",
        iterations=ITERATIONS_REAL_FAST,
        warmup_iterations=WARMUP_REAL_FAST,
        input_shape=f"{first_block.sample_count} samples x (status+4 channels)",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        summary=summary,
        notes=common_notes,
    ))

    summary, _ = time_function(
        lambda: replay_receiver(blocks),
        iterations=ITERATIONS_REAL_REPLAY,
        warmup_iterations=WARMUP_REAL_REPLAY,
    )
    rows.append(make_record(
        benchmark_id="real_capture.receiver_replay_all_blocks",
        module="receiver",
        function="EEGReceiver.eeg_block_uV",
        scenario="replay_all_real_capture_blocks",
        iterations=ITERATIONS_REAL_REPLAY,
        warmup_iterations=WARMUP_REAL_REPLAY,
        input_shape=f"{len(blocks)} blocks / {total_frames} frames",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        window_sec=duration_sec,
        summary=summary,
        notes=common_notes + "; tiempo por replay completo, no por bloque",
    ))

    summary, _ = time_function(
        lambda: replay_buffer(blocks),
        iterations=ITERATIONS_REAL_REPLAY,
        warmup_iterations=WARMUP_REAL_REPLAY,
    )
    rows.append(make_record(
        benchmark_id="real_capture.buffer_replay_all_blocks",
        module="eeg_signal_processor",
        function="EEGSignalProcessor.add_block_uV",
        scenario="replay_real_capture_into_ring_buffer",
        iterations=ITERATIONS_REAL_REPLAY,
        warmup_iterations=WARMUP_REAL_REPLAY,
        input_shape=f"{len(blocks)} blocks / {total_frames} frames",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        window_sec=duration_sec,
        summary=summary,
        notes=common_notes + "; tiempo por replay completo",
    ))

    summary, _ = time_function(
        lambda: proc.compute_live_features(0, FEATURE_WINDOW_SEC, psd_method="multitaper"),
        iterations=ITERATIONS_REAL_FAST,
        warmup_iterations=WARMUP_REAL_FAST,
    )
    rows.append(make_record(
        benchmark_id="real_capture.compute_live_features.final_window",
        module="eeg_signal_processor",
        function="EEGSignalProcessor.compute_live_features",
        scenario="real_capture_final_4s_window_ch1",
        iterations=ITERATIONS_REAL_FAST,
        warmup_iterations=WARMUP_REAL_FAST,
        input_shape=f"CH1 final window: {x_ch1.size} samples",
        fs_hz=FS_HZ,
        num_channels=1,
        window_sec=FEATURE_WINDOW_SEC,
        summary=summary,
        notes=common_notes + "; benchmark principal DSP live en ventana real",
    ))

    summary, _ = time_function(
        lambda: proc.compute_quality_diagnostics(channel_idx=0, window_sec=FEATURE_WINDOW_SEC, waveform_sec=2.0),
        iterations=ITERATIONS_REAL_FAST,
        warmup_iterations=WARMUP_REAL_FAST,
    )
    rows.append(make_record(
        benchmark_id="real_capture.compute_quality_diagnostics.final_window",
        module="eeg_signal_processor",
        function="EEGSignalProcessor.compute_quality_diagnostics",
        scenario="real_capture_final_4s_diagnostics_ch1",
        iterations=ITERATIONS_REAL_FAST,
        warmup_iterations=WARMUP_REAL_FAST,
        input_shape=f"CH1 final window: {x_ch1.size} samples",
        fs_hz=FS_HZ,
        num_channels=1,
        window_sec=FEATURE_WINDOW_SEC,
        summary=summary,
        notes=common_notes + "; incluye PSD para ratio 50 Hz",
    ))

    if x_ch1.size >= 4:
        summary, _ = time_function(
            lambda: dsp.compute_features(x_ch1, psd_method="multitaper", include_spectrum=False),
            iterations=ITERATIONS_REAL_FAST,
            warmup_iterations=WARMUP_REAL_FAST,
        )
        rows.append(make_record(
            benchmark_id="real_capture.dsp_core_compute_features.final_window",
            module="dsp_core",
            function="DSPCore.compute_features",
            scenario="real_capture_final_4s_window_direct_dsp",
            iterations=ITERATIONS_REAL_FAST,
            warmup_iterations=WARMUP_REAL_FAST,
            input_shape=f"CH1 final window: {x_ch1.size} samples",
            fs_hz=FS_HZ,
            num_channels=1,
            window_sec=FEATURE_WINDOW_SEC,
            summary=summary,
            notes=common_notes + "; mide DSPCore aislado sobre datos reales",
        ))

    summary, result = time_function(
        lambda: live_feature_sweep(blocks),
        iterations=max(3, min(ITERATIONS_REAL_REPLAY, 8)),
        warmup_iterations=1,
    )
    rows.append(make_record(
        benchmark_id="real_capture.live_feature_sweep_replay",
        module="eeg_signal_processor+sonification_features",
        function="replay_blocks_with_feature_hop",
        scenario="real_capture_replay_compute_features_every_64_samples",
        iterations=max(3, min(ITERATIONS_REAL_REPLAY, 8)),
        warmup_iterations=1,
        input_shape=f"{len(blocks)} blocks / {total_frames} frames",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        window_sec=duration_sec,
        summary=summary,
        notes=common_notes + f"; feature_calls={result.get('feature_calls', 0)}; simula hop real de 64 muestras",
    ))

    # Medida de copia/matriz real para estimar coste de preparacion offline.
    summary, _ = time_function(lambda: np.asarray(uv_matrix, dtype=np.float32), iterations=ITERATIONS_REAL_FAST, warmup_iterations=WARMUP_REAL_FAST)
    rows.append(make_record(
        benchmark_id="real_capture.numpy_materialize_uv_matrix",
        module="benchmark_real_capture",
        function="blocks_to_uv_matrix/asarray",
        scenario="real_capture_materialize_uv_matrix",
        iterations=ITERATIONS_REAL_FAST,
        warmup_iterations=WARMUP_REAL_FAST,
        input_shape=f"{uv_matrix.shape}",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        window_sec=duration_sec,
        summary=summary,
        notes=common_notes + "; coste auxiliar no pertenece al loop real",
    ))

    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmarks sobre una captura real EEG en la placa.")
    parser.add_argument("capture_dir", nargs="?", help="Directorio captures/<timestamp>_<condition>. Si se omite, usa la ultima captura encontrada.")
    parser.add_argument("--max-blocks", type=int, default=None, help="Limita bloques para pruebas rapidas.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    capture = Path(args.capture_dir) if args.capture_dir else discover_latest_capture(root)
    if capture is None:
        raise SystemExit("No se encontro captura. Ejecuta antes python3 python/tools/capture_eeg_quality.py --condition bench_real --duration 60")
    for row in run(capture, max_blocks=args.max_blocks):
        print(row)
