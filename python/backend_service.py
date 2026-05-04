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
SNAPSHOT_PUBLISH_PERIOD_SEC = 0.2
DISK_PUBLISH_PERIOD_SEC = 1.0
BANDS = ("delta", "theta", "alpha", "beta", "gamma")


class BackendService:
    def __init__(self):
        self.proc = EEGSignalProcessor(fs=FS_HZ, num_channels=NUM_CH, buffer_sec=10.0, psd_window_sec=FEATURE_WINDOW_SEC)
        self.rx = EEGReceiver(fs_hz=FS_HZ, num_ch=NUM_CH, queue_max=512)
        Bridge.provide("linux_started", self.rx.linux_started)
        Bridge.provide("eeg_block_uV", self.rx.eeg_block_uV)

        self._last_channels: list[dict] = []
        self._samples_since_feature = 0
        self._window_was_ready = False
        self._last_snapshot_t = 0.0
        self._last_disk_publish_t = 0.0
        self._snapshot_lock = threading.Lock()
        self._latest_snapshot: dict = {}

    def _compute_global(self, channels: list[dict]) -> dict:
        valid = [c for c in channels if c.get("connected")]
        if not valid:
            return {"valid_channels": 0, "rms_uV": None, "peak_freq_hz": None, "dominant_band": None, "bands": {b: 0.0 for b in BANDS}}
        bands = {b: float(sum(float(c["bands"].get(b, 0.0) or 0.0) for c in valid) / len(valid)) for b in BANDS}
        dom = max(bands.items(), key=lambda kv: kv[1])[0]
        rms = float(sum(float(c.get("rms_uV") or 0.0) for c in valid) / len(valid))
        peak = float(sum(float(c.get("peak_freq_hz") or 0.0) for c in valid) / len(valid))
        return {"valid_channels": len(valid), "rms_uV": rms, "peak_freq_hz": peak, "dominant_band": dom, "bands": bands}

    def _build_snapshot(self) -> dict:
        rxm = self.rx.get_window_metrics(reset=False)
        window_ready = self.proc.is_window_ready(FEATURE_WINDOW_SEC)
        state = "waiting_for_data" if int(rxm.get("rx_blocks_total", 0) or 0) <= 0 else ("features_ready" if self._last_channels else ("waiting_for_window" if not window_ready else "receiving"))
        channels = self._last_channels
        if not window_ready and int(rxm.get("rx_blocks_total", 0) or 0) > 0:
            channels = [{"index": i, "label": f"CH{i+1}", "connected": False, "quality": "waiting_for_window", "rms_uV": None, "peak_freq_hz": None, "dominant_band": None, "alpha_beta_ratio": None, "bands": {b: 0.0 for b in BANDS}} for i in range(NUM_CH)]

        return {
            "status": state,
            "rx_sample_rate_hz": float(rxm.get("rx_frame_rate_hz", 0.0) or 0.0),
            "rx_block_rate_hz": float(rxm.get("rx_block_rate_hz", 0.0) or 0.0),
            "last_sample_idx": self.rx.last_idx,
            "rx": {
                "rx_frames_total": rxm.get("rx_frames_total", 0),
                "rx_blocks_total": rxm.get("rx_blocks_total", 0),
                "lost_frames_total": rxm.get("lost_frames_total", 0),
                "lost_blocks_total": rxm.get("lost_blocks_total", 0),
                "malformed_blocks_total": rxm.get("malformed_blocks_total", 0),
                "invalid_status_total": rxm.get("invalid_status_total", 0),
            },
            "channels": channels,
            "global": self._compute_global(channels),
        }

    def step(self):
        _, drained_frames = self.rx.drain_blocks_to_processor(self.proc, max_blocks=16)
        window_ready = self.proc.is_window_ready(FEATURE_WINDOW_SEC)
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
            self._last_channels = self.proc.compute_channel_features(window_sec=FEATURE_WINDOW_SEC, psd_method="multitaper")

        now = time.monotonic()
        if (now - self._last_snapshot_t) >= SNAPSHOT_PUBLISH_PERIOD_SEC:
            with self._snapshot_lock:
                self._latest_snapshot = self._build_snapshot()
            self._last_snapshot_t = now

        if (now - self._last_disk_publish_t) >= DISK_PUBLISH_PERIOD_SEC:
            with self._snapshot_lock:
                snap = dict(self._latest_snapshot)
            if snap:
                publish_snapshot(snap)
            self._last_disk_publish_t = now

    def start(self):
        return None

    def loop(self):
        self.step()

    def get_latest_snapshot(self) -> dict:
        with self._snapshot_lock:
            return dict(self._latest_snapshot)


def create_backend_service() -> BackendService:
    clear_runtime_state()
    return BackendService()
