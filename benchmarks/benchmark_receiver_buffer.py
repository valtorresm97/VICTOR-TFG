from __future__ import annotations

import math
from typing import Any

from benchmark_core import ensure_python_path, make_record, time_function

ensure_python_path()

from eeg_contract import FS_HZ, NUM_CH, BLOCK_SAMPLES, STATUS_PREFIX, parse_eeg_block_values, iter_eeg_block_samples
from receiver import EEGReceiver
from eeg_signal_processor import EEGSignalProcessor

ITERATIONS = 1000
WARMUP = 100


def synthetic_eeg_uv(sample_idx: int, channel: int, fs_hz: int = FS_HZ) -> int:
    """Replica ligera del criterio de sketch/synthetic.h para benchmarks Python."""
    t = float(sample_idx) / float(fs_hz)
    ch = float(channel)
    value = (
        22.0 * math.sin(2.0 * math.pi * 2.0 * t + 0.35 * ch)
        + 16.0 * math.sin(2.0 * math.pi * 6.0 * t + 0.71 * ch)
        + 28.0 * math.sin(2.0 * math.pi * 10.0 * t + 1.13 * ch)
        + 11.0 * math.sin(2.0 * math.pi * 20.0 * t + 1.57 * ch)
        + 4.0 * math.sin(2.0 * math.pi * 38.0 * t + 0.9 * ch)
        + 18.0 * math.sin(2.0 * math.pi * 0.20 * t + 0.15 * ch)
        + 8.0 * math.sin(2.0 * math.pi * 50.0 * t + 0.1 * ch)
    )
    return int(round(value))


def make_payload(block_idx: int = 0, first_sample_idx: int = 0, sample_count: int = BLOCK_SAMPLES) -> tuple[int, int, int, tuple[int, ...]]:
    vals: list[int] = []
    for i in range(sample_count):
        sample_idx = first_sample_idx + i
        vals.append(STATUS_PREFIX)
        for ch in range(NUM_CH):
            vals.append(synthetic_eeg_uv(sample_idx, ch))
    return block_idx, first_sample_idx, sample_count, tuple(vals)


class _ProcessorSink:
    def __init__(self) -> None:
        self.calls = 0
        self.frames = 0

    def add_block_uV(self, samples: Any) -> int:
        self.calls += 1
        self.frames += len(samples)
        return len(samples)


def run() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    block_idx, first_idx, count, vals = make_payload()

    summary, _ = time_function(
        lambda: parse_eeg_block_values(count, vals, num_ch=NUM_CH, max_samples=BLOCK_SAMPLES),
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
    )
    rows.append(make_record(
        benchmark_id="receiver.parse_eeg_block_values.valid_8x4",
        module="eeg_contract",
        function="parse_eeg_block_values",
        scenario="valid_block_8_samples_4_channels",
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
        input_shape="8 samples x (status+4 channels)",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        summary=summary,
        notes="Parser de contrato EEG MCU->Python",
    ))

    statuses, samples = parse_eeg_block_values(count, vals, num_ch=NUM_CH, max_samples=BLOCK_SAMPLES)
    summary, _ = time_function(
        lambda: list(iter_eeg_block_samples(first_idx, statuses, samples, num_ch=NUM_CH)),
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
    )
    rows.append(make_record(
        benchmark_id="receiver.iter_eeg_block_samples.valid_8x4",
        module="eeg_contract",
        function="iter_eeg_block_samples",
        scenario="valid_block_iteration_8_samples_4_channels",
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
        input_shape="8 statuses + 8x4 samples",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        summary=summary,
        notes="Iterador usado por capturas CSV",
    ))

    block_counter = {"idx": 0, "first": 0}

    def call_receiver() -> None:
        rx = EEGReceiver(fs_hz=FS_HZ, num_ch=NUM_CH, queue_max=512)
        b_idx = block_counter["idx"]
        first = block_counter["first"]
        _, _, c, v = make_payload(b_idx, first)
        rx.eeg_block_uV(b_idx, first, c, *v)
        block_counter["idx"] += 1
        block_counter["first"] += c

    summary, _ = time_function(call_receiver, iterations=ITERATIONS, warmup_iterations=WARMUP)
    rows.append(make_record(
        benchmark_id="receiver.eeg_block_uV.valid_8x4",
        module="receiver",
        function="EEGReceiver.eeg_block_uV",
        scenario="callback_valid_block_8_samples_4_channels",
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
        input_shape="Bridge args: block_idx, first_sample_idx, sample_count, 40 vals",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        summary=summary,
        notes="Callback debe mantenerse ultraligero y sin DSP",
    ))

    def drain_scenario() -> tuple[int, int]:
        rx = EEGReceiver(fs_hz=FS_HZ, num_ch=NUM_CH, queue_max=512)
        for i in range(16):
            _, _, c, v = make_payload(i, i * BLOCK_SAMPLES)
            rx.eeg_block_uV(i, i * BLOCK_SAMPLES, c, *v)
        sink = _ProcessorSink()
        return rx.drain_blocks_to_processor(sink, max_blocks=16)

    summary, _ = time_function(drain_scenario, iterations=400, warmup_iterations=40)
    rows.append(make_record(
        benchmark_id="receiver.drain_blocks_to_processor.16_blocks",
        module="receiver",
        function="EEGReceiver.drain_blocks_to_processor",
        scenario="drain_16_valid_blocks_to_mock_processor",
        iterations=400,
        warmup_iterations=40,
        input_shape="16 blocks x 8 samples x 4 channels",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        summary=summary,
        notes="Incluye coste de cola y llamada add_block_uV mock",
    ))

    processor = EEGSignalProcessor(fs=FS_HZ, num_channels=NUM_CH, buffer_sec=10.0, psd_window_sec=4.0)
    block_samples = samples
    summary, _ = time_function(
        lambda: processor.add_block_uV(block_samples),
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
    )
    rows.append(make_record(
        benchmark_id="buffer.add_block_uV.valid_8x4",
        module="eeg_signal_processor",
        function="EEGSignalProcessor.add_block_uV",
        scenario="ingest_valid_block_8_samples_4_channels",
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
        input_shape="8 samples x 4 channels uV",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        summary=summary,
        notes="Incluye conversion uV->V y escritura circular",
    ))

    full_processor = EEGSignalProcessor(fs=FS_HZ, num_channels=NUM_CH, buffer_sec=10.0, psd_window_sec=4.0)
    for block in range(400):
        _, _, _, block_vals = make_payload(block, block * BLOCK_SAMPLES)
        _, block_samples_for_fill = parse_eeg_block_values(BLOCK_SAMPLES, block_vals)
        full_processor.add_block_uV(block_samples_for_fill)

    summary, _ = time_function(
        lambda: full_processor.get_signal_window(0, 4.0),
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
    )
    rows.append(make_record(
        benchmark_id="buffer.extract_recent_channel.4s",
        module="eeg_signal_processor",
        function="EEGSignalProcessor.get_signal_window",
        scenario="extract_recent_channel_4s_1000_samples",
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
        input_shape="channel 0, 1000 samples",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        window_sec=4.0,
        summary=summary,
        notes="Extraccion previa a DSP live",
    ))

    summary, _ = time_function(
        lambda: full_processor.get_recent_multichannel_window(4.0),
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
    )
    rows.append(make_record(
        benchmark_id="buffer.extract_recent_matrix.4s",
        module="eeg_signal_processor",
        function="EEGSignalProcessor.get_recent_multichannel_window",
        scenario="extract_recent_matrix_4s_4x1000",
        iterations=ITERATIONS,
        warmup_iterations=WARMUP,
        input_shape="4 channels x 1000 samples",
        fs_hz=FS_HZ,
        num_channels=NUM_CH,
        window_sec=4.0,
        summary=summary,
        notes="Extraccion multicanal para diagnostico/offline",
    ))

    return rows


if __name__ == "__main__":
    for row in run():
        print(row)
