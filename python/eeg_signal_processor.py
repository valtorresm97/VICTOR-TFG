from __future__ import annotations

import logging
import numpy as np

from dsp_core import DSPCore

logger = logging.getLogger(__name__)

SAMPLING_RATE = 250
NUM_CHANNELS = 4


class EEGSignalProcessor:
    """Procesa señal EEG y estima features/estado por canal."""

    def __init__(self, fs: int = SAMPLING_RATE, num_channels: int = NUM_CHANNELS, buffer_sec: float = 10.0, psd_window_sec: float = 4.0, window_type: str = "hann", welch_overlap: float = 0.5):
        self.fs = int(fs)
        self.num_channels = int(num_channels)
        self.buffer_size = max(1, int(round(buffer_sec * self.fs)))
        self.buffer = np.zeros((self.num_channels, self.buffer_size), dtype=np.float32)  # volts
        self.status_buffer = np.zeros((self.buffer_size,), dtype=np.uint32)
        self.write_pos = 0
        self.valid_samples = 0
        self.total_samples_ingested = 0

        self.dsp = DSPCore(fs=self.fs, window_sec=psd_window_sec, window_type=window_type, welch_overlap=welch_overlap)
        self._lead_off_recent = np.zeros((self.num_channels,), dtype=np.float32)

    def _write_block(self, volts: np.ndarray, statuses: np.ndarray | None) -> int:
        arr = np.asarray(volts, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[1] != self.num_channels:
            return 0
        n = int(arr.shape[0])
        if n <= 0:
            return 0
        if n >= self.buffer_size:
            arr = arr[-self.buffer_size:, :]
            n = self.buffer_size
            if statuses is not None:
                statuses = statuses[-n:]

        arr_t = arr.T
        end_space = self.buffer_size - self.write_pos
        if n <= end_space:
            self.buffer[:, self.write_pos:self.write_pos + n] = arr_t
            if statuses is not None:
                self.status_buffer[self.write_pos:self.write_pos + n] = statuses
        else:
            first = end_space
            second = n - first
            self.buffer[:, self.write_pos:] = arr_t[:, :first]
            self.buffer[:, :second] = arr_t[:, first:]
            if statuses is not None:
                self.status_buffer[self.write_pos:] = statuses[:first]
                self.status_buffer[:second] = statuses[first:]

        self.write_pos = (self.write_pos + n) % self.buffer_size
        self.valid_samples = min(self.buffer_size, self.valid_samples + n)
        self.total_samples_ingested += n
        return n

    def add_block_uV(self, block_samples_uV, statuses=None) -> int:
        arr_uV = np.asarray(block_samples_uV, dtype=np.float32)
        if arr_uV.ndim != 2 or arr_uV.shape[1] != self.num_channels:
            return 0
        status_arr = None
        if statuses is not None:
            status_arr = np.asarray(statuses, dtype=np.uint32)
            if status_arr.shape[0] != arr_uV.shape[0]:
                status_arr = None
        return self._write_block(arr_uV * 1e-6, status_arr)

    def is_window_ready(self, window_sec: float | None = None) -> bool:
        needed = int(round((window_sec or self.dsp.window_sec) * self.fs))
        return self.valid_samples >= needed

    def _extract_recent(self, n: int) -> tuple[np.ndarray, np.ndarray]:
        if n <= 0:
            return np.empty((self.num_channels, 0), dtype=float), np.empty((0,), dtype=np.uint32)
        start = (self.write_pos - n) % self.buffer_size
        if start + n <= self.buffer_size:
            return np.array(self.buffer[:, start:start+n], dtype=float, copy=True), np.array(self.status_buffer[start:start+n], dtype=np.uint32, copy=True)
        first = self.buffer_size - start
        second = n - first
        sig = np.empty((self.num_channels, n), dtype=float)
        sig[:, :first] = self.buffer[:, start:]
        sig[:, first:] = self.buffer[:, :second]
        st = np.empty((n,), dtype=np.uint32)
        st[:first] = self.status_buffer[start:]
        st[first:] = self.status_buffer[:second]
        return sig, st

    def compute_channel_features(self, window_sec: float = 4.0, psd_method: str = "multitaper") -> list[dict]:
        n = min(self.valid_samples, int(round(window_sec * self.fs)))
        if n < 4:
            return []
        signals, statuses = self._extract_recent(n)

        loff_p = ((statuses >> 19) & 0x0F).astype(np.uint8)
        loff_n = ((statuses >> 15) & 0x0F).astype(np.uint8)

        channels = []
        for ch in range(self.num_channels):
            x = signals[ch]
            x_uV = x * 1e6
            rms = float(np.sqrt(np.mean(x_uV * x_uV))) if x_uV.size else 0.0
            uniq = np.unique(np.round(x_uV, 3)).size
            flat = uniq <= 2
            sat = np.mean(np.abs(x_uV) > 2000.0) > 0.05
            loff_hits = np.mean((((loff_p >> ch) & 0x1) | ((loff_n >> ch) & 0x1)).astype(np.float32))

            feats = self.dsp.compute_features(x, psd_method=psd_method, include_spectrum=False, include_peaks=False, include_relative_bandpower=True)
            bp_rel = feats.get("bandpower_rel", {}) if feats else {}
            bp_abs = feats.get("bandpower_abs", {}) if feats else {}
            alpha = float(bp_rel.get("alpha", 0.0) or 0.0)
            beta = float(bp_rel.get("beta", 0.0) or 0.0)
            ratio = (alpha / beta) if beta > 1e-12 else None
            peak_freq = float(feats.get("peak_freq", 0.0) or 0.0) if feats else None
            dominant = max(bp_rel.items(), key=lambda kv: float(kv[1] or 0.0))[0] if bp_rel else None

            quality = "ok"
            connected = True
            if loff_hits > 0.30:
                quality = "lead_off"
                connected = False
            elif rms < 0.2 or flat:
                quality = "no_valid_signal"
                connected = False
            elif sat:
                quality = "saturated"
                connected = False

            channels.append({
                "index": ch,
                "label": f"CH{ch+1}",
                "connected": connected,
                "quality": quality,
                "rms_uV": rms,
                "peak_freq_hz": peak_freq,
                "dominant_band": dominant,
                "alpha_beta_ratio": ratio,
                "bands": {k: float(bp_rel.get(k, 0.0) or 0.0) for k in ("delta", "theta", "alpha", "beta", "gamma")},
                "bands_abs": {k: float(bp_abs.get(k, 0.0) or 0.0) for k in ("delta", "theta", "alpha", "beta", "gamma")},
                "lead_off_ratio": float(loff_hits),
            })
        return channels
