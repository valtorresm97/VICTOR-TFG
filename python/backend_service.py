from __future__ import annotations

from arduino.app_utils import Bridge, App
import logging
import time

from eeg_signal_processor import EEGSignalProcessor
from receiver import EEGReceiver
from app_state import publish_snapshot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EEG_BACKEND")

FS_HZ = 250
NUM_CH = 4

FEATURE_WINDOW_SEC = 4.0
FEATURE_HOP_SAMPLES = 64
SNAPSHOT_PUBLISH_PERIOD_SEC = 0.5

proc = EEGSignalProcessor(
    fs=FS_HZ,
    num_channels=NUM_CH,
    buffer_sec=10.0,
    psd_window_sec=FEATURE_WINDOW_SEC,
    window_type="hann",
    welch_overlap=0.5,
)
rx = EEGReceiver(fs_hz=FS_HZ, num_ch=NUM_CH, queue_max=512)

Bridge.provide("linux_started", rx.linux_started)
Bridge.provide("eeg_block_uV", rx.eeg_block_uV)

_last_features: dict = {}
_samples_since_feature = 0
_window_was_ready = False
_last_snapshot_t = 0.0


def _build_snapshot() -> dict:
    rxm = rx.get_window_metrics(reset=False)
    status = {
        "state": "running" if proc.is_window_ready(FEATURE_WINDOW_SEC) else "filling_window",
        "window_ready": proc.is_window_ready(FEATURE_WINDOW_SEC),
        "last_sample_idx": rx.last_idx,
    }

    feats = _last_features or {}
    bp_rel = feats.get("bandpower_rel", {}) or {}
    bp_abs = feats.get("bandpower_abs", {}) or {}

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
            "bandpower_rel": bp_rel,
            "bandpower_abs": bp_abs,
            "alpha_power_rel": bp_rel.get("alpha"),
            "beta_power_rel": bp_rel.get("beta"),
            "alpha_power_abs": bp_abs.get("alpha"),
            "beta_power_abs": bp_abs.get("beta"),
        },
    }


def loop():
    global _samples_since_feature, _window_was_ready, _last_features, _last_snapshot_t

    _, drained_frames = rx.drain_blocks_to_processor(proc, max_blocks=16)

    window_ready = proc.is_window_ready(window_sec=FEATURE_WINDOW_SEC)
    need_feature = False

    if window_ready:
        if not _window_was_ready:
            _window_was_ready = True
            _samples_since_feature = 0
            need_feature = True
        else:
            _samples_since_feature += drained_frames
            if _samples_since_feature >= FEATURE_HOP_SAMPLES:
                _samples_since_feature -= FEATURE_HOP_SAMPLES
                need_feature = True
    else:
        _window_was_ready = False
        _samples_since_feature = 0

    if need_feature and drained_frames > 0:
        try:
            feats = proc.compute_live_features(channel_idx=0, window_sec=FEATURE_WINDOW_SEC, psd_method="multitaper")
            if feats:
                _last_features = feats
        except Exception as e:
            logger.exception(f"feature computation error: {e}")

    now = time.monotonic()
    if (now - _last_snapshot_t) >= SNAPSHOT_PUBLISH_PERIOD_SEC or drained_frames > 0:
        publish_snapshot(_build_snapshot())
        _last_snapshot_t = now

    time.sleep(0.02)


App.run(user_loop=loop)
