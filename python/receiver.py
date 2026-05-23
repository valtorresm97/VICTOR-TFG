# receiver.py
from __future__ import annotations
from collections import deque
import time
import logging
from typing import Deque, Tuple, Optional, Any

logger = logging.getLogger(__name__)

# Block item:
# (
#   block_idx,
#   first_sample_idx,
#   sample_count,
#   statuses_tuple,                # len = sample_count
#   samples_tuple_of_tuples        # len = sample_count, each inner tuple len = num_ch
# )
BlockItem = Tuple[int, int, int, Tuple[int, ...], Tuple[Tuple[int, ...], ...]]


class EEGReceiver:
    """
    Receptor MCU->MPU por Bridge.

    Fase 2:
    - callback Bridge ultraligero
    - cola explícita de BLOQUES
    - drenado por bloques hacia el procesador
    - métricas separadas de recepción y consumo
    """

    def __init__(self, fs_hz: int = 250, num_ch: int = 4, queue_max: int = 512):
        self.fs_hz = int(fs_hz)
        self.num_ch = int(num_ch)

        # Cola explícita de bloques
        self.block_queue: Deque[BlockItem] = deque(maxlen=int(queue_max))

        # Backlog actual en frames (muestras)
        self.block_queue_frames_current: int = 0

        # -------- Estado de continuidad --------
        self.last_idx: Optional[int] = None
        self.last_block_idx: Optional[int] = None
        self.last_block_last_sample_idx: Optional[int] = None

        # -------- Totales acumulados --------
        self.rx_frames_total: int = 0
        self.rx_blocks_total: int = 0

        self.lost_frames_total: int = 0
        self.lost_blocks_total: int = 0

        self.malformed_blocks_total: int = 0
        self.block_seq_mismatch_total: int = 0

        self.queue_drops_blocks_total: int = 0
        self.queue_drops_frames_total: int = 0

        self.queue_max_blocks_total: int = 0
        self.queue_max_frames_total: int = 0

        self.frame_callback_calls_total: int = 0
        self.block_callback_calls_total: int = 0

        self.frame_callback_time_us_accum_total: int = 0
        self.block_callback_time_us_accum_total: int = 0

        self.frame_callback_time_us_max_total: int = 0
        self.block_callback_time_us_max_total: int = 0

        self.drain_calls_total: int = 0
        self.drain_blocks_total: int = 0
        self.drain_frames_total: int = 0

        self.drain_time_us_accum_total: int = 0
        self.drain_time_us_max_total: int = 0

        # -------- Ventana actual --------
        self._reset_window_metrics()

        # -------- Tasas RX --------
        self.t0 = time.monotonic()
        self._last_rate_t = self.t0
        self._last_rate_frames = 0
        self._last_rate_blocks = 0
        self._rx_frame_rate_hz = 0.0
        self._rx_block_rate_hz = 0.0

        self._last_report_t = self.t0
        # Contrato esperado del firmware actual.
        self.expected_block_samples: int = 8
        self.expected_status_prefix: int = 0xC00000
        self.status_prefix_mask: int = 0xF00000
        self.invalid_status_total: int = 0
        self._logged_first_block: bool = False

    # ============================================================
    # Helpers internos
    # ============================================================
    def _reset_window_metrics(self):
        self.rx_frames_window: int = 0
        self.rx_blocks_window: int = 0

        self.lost_frames_window: int = 0
        self.lost_blocks_window: int = 0

        self.malformed_blocks_window: int = 0
        self.block_seq_mismatch_window: int = 0
        self.invalid_status_window: int = 0

        self.queue_drops_blocks_window: int = 0
        self.queue_drops_frames_window: int = 0

        self.queue_max_blocks_window: int = len(self.block_queue)
        self.queue_max_frames_window: int = self.block_queue_frames_current

        self.frame_callback_calls_window: int = 0
        self.block_callback_calls_window: int = 0

        self.frame_callback_time_us_accum_window: int = 0
        self.block_callback_time_us_accum_window: int = 0

        self.frame_callback_time_us_max_window: int = 0
        self.block_callback_time_us_max_window: int = 0

        self.drain_calls_window: int = 0
        self.drain_blocks_window: int = 0
        self.drain_frames_window: int = 0

        self.drain_time_us_accum_window: int = 0
        self.drain_time_us_max_window: int = 0

    def _now_us(self) -> int:
        return time.perf_counter_ns() // 1000

    def _update_queue_max(self):
        q_blocks = len(self.block_queue)
        q_frames = self.block_queue_frames_current

        if q_blocks > self.queue_max_blocks_total:
            self.queue_max_blocks_total = q_blocks
        if q_blocks > self.queue_max_blocks_window:
            self.queue_max_blocks_window = q_blocks

        if q_frames > self.queue_max_frames_total:
            self.queue_max_frames_total = q_frames
        if q_frames > self.queue_max_frames_window:
            self.queue_max_frames_window = q_frames

    def _record_frame_callback_timing(self, dt_us: int):
        self.frame_callback_calls_total += 1
        self.frame_callback_calls_window += 1

        self.frame_callback_time_us_accum_total += dt_us
        self.frame_callback_time_us_accum_window += dt_us

        if dt_us > self.frame_callback_time_us_max_total:
            self.frame_callback_time_us_max_total = dt_us
        if dt_us > self.frame_callback_time_us_max_window:
            self.frame_callback_time_us_max_window = dt_us

    def _record_block_callback_timing(self, dt_us: int):
        self.block_callback_calls_total += 1
        self.block_callback_calls_window += 1

        self.block_callback_time_us_accum_total += dt_us
        self.block_callback_time_us_accum_window += dt_us

        if dt_us > self.block_callback_time_us_max_total:
            self.block_callback_time_us_max_total = dt_us
        if dt_us > self.block_callback_time_us_max_window:
            self.block_callback_time_us_max_window = dt_us

    def _enqueue_block(self, item: BlockItem):
        _, _, sample_count, _, _ = item

        # Control manual de overflow para saber exactamente qué se descarta
        if len(self.block_queue) == self.block_queue.maxlen:
            old = self.block_queue.popleft()
            old_sample_count = old[2]

            self.block_queue_frames_current -= old_sample_count
            self.queue_drops_blocks_total += 1
            self.queue_drops_blocks_window += 1

            self.queue_drops_frames_total += old_sample_count
            self.queue_drops_frames_window += old_sample_count

        self.block_queue.append(item)
        self.block_queue_frames_current += sample_count

        self._update_queue_max()

    # ============================================================
    # Bridge handlers
    # ============================================================
    def linux_started(self) -> bool:
        return True

    def eeg_frame_uV(self, idx: int, status: int, *chs: int):
        """
        Compatibilidad legado.
        Empaqueta el frame como bloque de 1 muestra.
        """
        t0_us = self._now_us()
        try:
            if len(chs) < self.num_ch:
                return

            idx = int(idx)
            status = int(status)
            sample = tuple(int(c) for c in chs[:self.num_ch])

            if self.last_idx is not None:
                expected = self.last_idx + 1
                if idx > expected:
                    gap = idx - expected
                    self.lost_frames_total += gap
                    self.lost_frames_window += gap

            self.last_idx = idx

            item: BlockItem = (
                -1,                  # block_idx legado
                idx,                 # first_sample_idx
                1,                   # sample_count
                (status,),           # statuses
                (sample,),           # samples
            )

            self._enqueue_block(item)

            self.rx_blocks_total += 1
            self.rx_blocks_window += 1
            self.rx_frames_total += 1
            self.rx_frames_window += 1
        finally:
            self._record_frame_callback_timing(self._now_us() - t0_us)

    def eeg_block_uV(self, block_idx: int, first_sample_idx: int, sample_count: int, *vals: int):
        """
        Callback principal para bloques.
        En Fase 2 NO se expande a frames dentro del callback.
        """
        t0_us = self._now_us()
        try:
            block_idx = int(block_idx)
            first_sample_idx = int(first_sample_idx)
            sample_count = int(sample_count)

            if sample_count <= 0 or sample_count > self.expected_block_samples:
                self.malformed_blocks_total += 1
                self.malformed_blocks_window += 1
                return
            if block_idx < 0 or first_sample_idx < 0:
                self.malformed_blocks_total += 1
                self.malformed_blocks_window += 1
                return

            stride = 1 + self.num_ch
            expected_vals = sample_count * stride

            if len(vals) != expected_vals:
                self.malformed_blocks_total += 1
                self.malformed_blocks_window += 1
                return

            # Continuidad por block_idx
            if self.last_block_idx is not None:
                expected_block_idx = self.last_block_idx + 1
                if block_idx > expected_block_idx:
                    gap_blocks = block_idx - expected_block_idx
                    self.lost_blocks_total += gap_blocks
                    self.lost_blocks_window += gap_blocks

            # Continuidad por sample_idx entre bloques
            if self.last_block_last_sample_idx is not None:
                expected_first_sample_idx = self.last_block_last_sample_idx + 1
                if first_sample_idx != expected_first_sample_idx:
                    self.block_seq_mismatch_total += 1
                    self.block_seq_mismatch_window += 1

                    if first_sample_idx > expected_first_sample_idx:
                        gap_frames = first_sample_idx - expected_first_sample_idx
                        self.lost_frames_total += gap_frames
                        self.lost_frames_window += gap_frames

            statuses = [0] * sample_count
            samples = [None] * sample_count

            for i in range(sample_count):
                base = i * stride
                statuses[i] = int(vals[base])
                if (statuses[i] & self.status_prefix_mask) != self.expected_status_prefix:
                    self.invalid_status_total += 1
                    self.invalid_status_window += 1
                samples[i] = tuple(int(v) for v in vals[base + 1: base + 1 + self.num_ch])

            item: BlockItem = (
                block_idx,
                first_sample_idx,
                sample_count,
                tuple(statuses),
                tuple(samples),
            )

            self._enqueue_block(item)

            self.rx_blocks_total += 1
            self.rx_blocks_window += 1

            self.rx_frames_total += sample_count
            self.rx_frames_window += sample_count

            self.last_block_idx = block_idx
            self.last_block_last_sample_idx = first_sample_idx + sample_count - 1
            self.last_idx = self.last_block_last_sample_idx

            if not self._logged_first_block:
                logger.info(
                    "[RX] first eeg_block_uV block received: block_idx=%d, first_sample_idx=%d, sample_count=%d",
                    block_idx,
                    first_sample_idx,
                    sample_count,
                )
                self._logged_first_block = True
        finally:
            self._record_block_callback_timing(self._now_us() - t0_us)

    # ============================================================
    # Consumo hacia el procesador
    # ============================================================
    def drain_blocks_to_processor(self, proc, max_blocks: int = 16, block_sink=None) -> tuple[int, int]:
        """
        Saca hasta max_blocks de la cola y los pasa al procesador.
        El procesador recibe directamente el BLOQUE.
        """
        if not self.block_queue:
            return 0, 0

        t0_us = self._now_us()
        n_blocks = 0
        n_frames = 0

        while self.block_queue and n_blocks < max_blocks:
            block_idx, first_sample_idx, sample_count, statuses, samples = self.block_queue.popleft()
            self.block_queue_frames_current -= sample_count

            # Fase 2: consumo desacoplado por bloque
            proc.add_block_uV(samples)
            if block_sink is not None:
                block_sink(block_idx, first_sample_idx, sample_count, statuses, samples)

            n_blocks += 1
            n_frames += sample_count

        dt_us = self._now_us() - t0_us

        self.drain_calls_total += 1
        self.drain_calls_window += 1

        self.drain_blocks_total += n_blocks
        self.drain_blocks_window += n_blocks

        self.drain_frames_total += n_frames
        self.drain_frames_window += n_frames

        self.drain_time_us_accum_total += dt_us
        self.drain_time_us_accum_window += dt_us

        if dt_us > self.drain_time_us_max_total:
            self.drain_time_us_max_total = dt_us
        if dt_us > self.drain_time_us_max_window:
            self.drain_time_us_max_window = dt_us

        return n_blocks, n_frames

    # ============================================================
    # Stats / métricas
    # ============================================================
    def update_rx_rate(self):
        now = time.monotonic()
        dt = now - self._last_rate_t
        if dt >= 1.0:
            frames = self.rx_frames_total - self._last_rate_frames
            blocks = self.rx_blocks_total - self._last_rate_blocks

            self._rx_frame_rate_hz = frames / dt if dt > 0 else 0.0
            self._rx_block_rate_hz = blocks / dt if dt > 0 else 0.0

            self._last_rate_t = now
            self._last_rate_frames = self.rx_frames_total
            self._last_rate_blocks = self.rx_blocks_total

    @property
    def rx_frame_rate_hz(self) -> float:
        return self._rx_frame_rate_hz

    @property
    def rx_block_rate_hz(self) -> float:
        return self._rx_block_rate_hz

    def get_window_metrics(self, reset: bool = False) -> dict[str, Any]:
        self.update_rx_rate()

        frame_cb_avg_us = (
            self.frame_callback_time_us_accum_window / self.frame_callback_calls_window
            if self.frame_callback_calls_window > 0 else 0.0
        )
        block_cb_avg_us = (
            self.block_callback_time_us_accum_window / self.block_callback_calls_window
            if self.block_callback_calls_window > 0 else 0.0
        )
        drain_avg_us = (
            self.drain_time_us_accum_window / self.drain_calls_window
            if self.drain_calls_window > 0 else 0.0
        )
        drain_eff_us_per_frame = (
            self.drain_time_us_accum_window / self.drain_frames_window
            if self.drain_frames_window > 0 else 0.0
        )
        drain_eff_us_per_block = (
            self.drain_time_us_accum_window / self.drain_blocks_window
            if self.drain_blocks_window > 0 else 0.0
        )

        snap = {
            "queue_blocks_current": len(self.block_queue),
            "queue_blocks_capacity": self.block_queue.maxlen,
            "queue_frames_current": self.block_queue_frames_current,

            "queue_max_blocks_window": self.queue_max_blocks_window,
            "queue_max_blocks_total": self.queue_max_blocks_total,
            "queue_max_frames_window": self.queue_max_frames_window,
            "queue_max_frames_total": self.queue_max_frames_total,

            "queue_drops_blocks_window": self.queue_drops_blocks_window,
            "queue_drops_blocks_total": self.queue_drops_blocks_total,
            "queue_drops_frames_window": self.queue_drops_frames_window,
            "queue_drops_frames_total": self.queue_drops_frames_total,

            "rx_frame_rate_hz": self._rx_frame_rate_hz,
            "rx_block_rate_hz": self._rx_block_rate_hz,

            "rx_frames_window": self.rx_frames_window,
            "rx_frames_total": self.rx_frames_total,
            "rx_blocks_window": self.rx_blocks_window,
            "rx_blocks_total": self.rx_blocks_total,

            "lost_frames_window": self.lost_frames_window,
            "lost_frames_total": self.lost_frames_total,
            "lost_blocks_window": self.lost_blocks_window,
            "lost_blocks_total": self.lost_blocks_total,

            "malformed_blocks_window": self.malformed_blocks_window,
            "malformed_blocks_total": self.malformed_blocks_total,
            "block_seq_mismatch_window": self.block_seq_mismatch_window,
            "block_seq_mismatch_total": self.block_seq_mismatch_total,
            "invalid_status_window": self.invalid_status_window,
            "invalid_status_total": self.invalid_status_total,

            "frame_callback_avg_us_window": frame_cb_avg_us,
            "frame_callback_max_us_window": self.frame_callback_time_us_max_window,
            "frame_callback_calls_window": self.frame_callback_calls_window,

            "block_callback_avg_us_window": block_cb_avg_us,
            "block_callback_max_us_window": self.block_callback_time_us_max_window,
            "block_callback_calls_window": self.block_callback_calls_window,

            "drain_calls_window": self.drain_calls_window,
            "drain_blocks_window": self.drain_blocks_window,
            "drain_frames_window": self.drain_frames_window,
            "drain_avg_us_window": drain_avg_us,
            "drain_eff_us_per_block_window": drain_eff_us_per_block,
            "drain_eff_us_per_frame_window": drain_eff_us_per_frame,
            "drain_max_us_window": self.drain_time_us_max_window,
        }

        if reset:
            self._reset_window_metrics()

        return snap
