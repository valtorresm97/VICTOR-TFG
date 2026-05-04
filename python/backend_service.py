from __future__ import annotations

import logging
import threading
import time

from arduino.app_utils import Bridge

from eeg_signal_processor import EEGSignalProcessor
from receiver import EEGReceiver
from app_state import publish_snapshot, clear_runtime_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EEG_BACKEND")

FS_HZ = 250
NUM_CH = 4

FEATURE_WINDOW_SEC = 4.0
FEATURE_HOP_SAMPLES = 64
SNAPSHOT_PUBLISH_PERIOD_SEC = 0.2  # 5 Hz
DISK_PUBLISH_PERIOD_SEC = 1.0


class BackendService:
    """Orquesta recepción Bridge, buffer DSP y publicación de snapshots ligeros."""

    def __init__(self):
        self.proc = EEGSignalProcessor(
            fs=FS_HZ,
            num_channels=NUM_CH,
            buffer_sec=10.0,
            psd_window_sec=FEATURE_WINDOW_SEC,
            window_type="hann",
            welch_overlap=0.5,
        )
        self.rx = EEGReceiver(fs_hz=FS_HZ, num_ch=NUM_CH, queue_max=512)

        Bridge.provide("linux_started", self.rx.linux_started)
        Bridge.provide("eeg_block_uV", self.rx.eeg_block_uV)

        self._last_features: dict = {}
        self._samples_since_feature = 0
        self._window_was_ready = False

        self._last_snapshot_t = 0.0
        self._last_disk_publish_t = 0.0

        self._snapshot_lock = threading.Lock()
        self._latest_snapshot: dict = {}

    def _build_snapshot(self) -> dict:
        rxm = self.rx.get_window_metrics(reset=False)
        status = {
            "state": "running" if self.proc.is_window_ready(FEATURE_WINDOW_SEC) else "filling_window",
            "window_ready": self.proc.is_window_ready(FEATURE_WINDOW_SEC),
            "last_sample_idx": self.rx.last_idx,
        }

        feats = self._last_features or {}
        bp_rel = feats.get("bandpower_rel", {}) or {}
        bp_abs = feats.get("bandpower_abs", {}) or {}

        alpha_rel = float(bp_rel.get("alpha", 0.0) or 0.0)
        beta_rel = float(bp_rel.get("beta", 0.0) or 0.0)
        alpha_beta_ratio = (alpha_rel / beta_rel) if beta_rel > 1e-12 else None

        dominant_band = None
        if bp_rel:
            dominant_band = max(bp_rel.items(), key=lambda kv: float(kv[1] or 0.0))[0]

        return {
            "ts_monotonic": time.monotonic(),
            "config": {
                "fs_hz": FS_HZ,
                "num_ch": NUM_CH,
                "feature_window_sec": FEATURE_WINDOW_SEC,
                "feature_hop_samples": FEATURE_HOP_SAMPLES,
                "psd_method": "multitaper",
                "channel_idx": 0,
            },
            "status": status,
            "rx": {
                "rx_frame_rate_hz": rxm.get("rx_frame_rate_hz", 0.0),
                "rx_block_rate_hz": rxm.get("rx_block_rate_hz", 0.0),
                "rx_frames_total": rxm.get("rx_frames_total", 0),
                "rx_blocks_total": rxm.get("rx_blocks_total", 0),
                "queue_frames_current": rxm.get("queue_frames_current", 0),
                "queue_blocks_current": rxm.get("queue_blocks_current", 0),
                "lost_frames_total": rxm.get("lost_frames_total", 0),
                "lost_blocks_total": rxm.get("lost_blocks_total", 0),
                "malformed_blocks_total": rxm.get("malformed_blocks_total", 0),
                "invalid_status_total": rxm.get("invalid_status_total", 0),
                "queue_drops_frames_total": rxm.get("queue_drops_frames_total", 0),
                "queue_drops_blocks_total": rxm.get("queue_drops_blocks_total", 0),
            },
            "features": {
                "rms": feats.get("rms"),
                "peak_freq": feats.get("peak_freq"),
                "dominant_band": dominant_band,
                "alpha_beta_ratio": alpha_beta_ratio,
                "bandpower_rel": bp_rel,
                "bandpower_abs": bp_abs,
            },
        }

    def step(self):
        _, drained_frames = self.rx.drain_blocks_to_processor(self.proc, max_blocks=16)

        window_ready = self.proc.is_window_ready(window_sec=FEATURE_WINDOW_SEC)
        need_feature = False

        if window_ready:
            if not self._window_was_ready:
                self._window_was_ready = True
                self._samples_since_feature = 0
                need_feature = True
            else:
                self._samples_since_feature += drained_frames
                if self._samples_since_feature >= FEATURE_HOP_SAMPLES:
                    self._samples_since_feature -= FEATURE_HOP_SAMPLES
                    need_feature = True
        else:
            self._window_was_ready = False
            self._samples_since_feature = 0

        if need_feature and drained_frames > 0:
            try:
                feats = self.proc.compute_live_features(channel_idx=0, window_sec=FEATURE_WINDOW_SEC, psd_method="multitaper")
                if feats:
                    self._last_features = feats
            except Exception as e:
                logger.exception(f"feature computation error: {e}")

        now = time.monotonic()
        if (now - self._last_snapshot_t) >= SNAPSHOT_PUBLISH_PERIOD_SEC:
            snap = self._build_snapshot()
            with self._snapshot_lock:
                self._latest_snapshot = snap
            self._last_snapshot_t = now

        if (now - self._last_disk_publish_t) >= DISK_PUBLISH_PERIOD_SEC:
            with self._snapshot_lock:
                snap = dict(self._latest_snapshot)
            if snap:
                publish_snapshot(snap)
            self._last_disk_publish_t = now

    def get_latest_snapshot(self) -> dict:
        with self._snapshot_lock:
            return dict(self._latest_snapshot)


def create_backend_service() -> BackendService:
    clear_runtime_state()
    return BackendService()
