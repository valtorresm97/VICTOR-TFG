from __future__ import annotations

"""
EEGSignalProcessor
------------------
Procesador de señal EEG orientado a tiempo real:

- Gestiona un ring buffer multicanal basado en arrays
- Ingiere bloques desde el Bridge/receiver
- Extrae ventanas recientes para DSP
- La señal ya llega filtrada desde la etapa de adquisición
- Usa DSPCore para PSD, bandpower y features
"""

import numpy as np
import logging

from dsp_core import DSPCore

logger = logging.getLogger(__name__)

SAMPLING_RATE = 250
NUM_CHANNELS = 4


class EEGSignalProcessor:
    """Procesa señales EEG en tiempo real usando DSPCore internamente."""

    def __init__(
        self,
        fs: int = SAMPLING_RATE,
        num_channels: int = NUM_CHANNELS,
        buffer_sec: float = 4.0,
        psd_window_sec: float = 4.0,
        window_type: str = "hann",
        welch_overlap: float = 0.5,
    ):
        self.fs = int(fs)
        self.num_channels = int(num_channels)

        self.buffer_size = int(round(buffer_sec * self.fs))
        self.buffer_size = max(1, self.buffer_size)

        self.buffer = np.zeros((self.num_channels, self.buffer_size), dtype=np.float32)

        self.write_pos = 0
        self.valid_samples = 0
        self.total_samples_ingested = 0

        self.dsp = DSPCore(
            fs=self.fs,
            window_sec=psd_window_sec,
            window_type=window_type,
            welch_overlap=welch_overlap,
        )

        logger.info(
            f"EEGSignalProcessor iniciado: fs={self.fs}Hz, "
            f"buffer={buffer_sec}s, psd_window={psd_window_sec}s"
        )
        logger.info("Filtros Python eliminados: se usa la señal filtrada recibida del MCU")

    # ------------------- helpers internos de buffer -------------------
    def _write_block_volts(self, block_v: np.ndarray) -> int:
        """
        Escribe un bloque en VOLTIOS con shape (n_samples, num_channels)
        dentro del ring buffer.
        """
        arr = np.asarray(block_v, dtype=np.float32)
        if arr.size == 0:
            return 0

        if arr.ndim != 2 or arr.shape[1] != self.num_channels:
            logger.warning(
                f"Bloque de voltios con shape incorrecta: {arr.shape}, "
                f"esperado (*, {self.num_channels})"
            )
            return 0

        n_samples = int(arr.shape[0])
        if n_samples <= 0:
            return 0

        if n_samples >= self.buffer_size:
            arr = arr[-self.buffer_size:, :]
            n_samples = self.buffer_size

        arr_t = arr.T  # shape (num_channels, n_samples)

        end_space = self.buffer_size - self.write_pos

        if n_samples <= end_space:
            self.buffer[:, self.write_pos:self.write_pos + n_samples] = arr_t
        else:
            first = end_space
            second = n_samples - first

            self.buffer[:, self.write_pos:] = arr_t[:, :first]
            self.buffer[:, :second] = arr_t[:, first:]

        self.write_pos = (self.write_pos + n_samples) % self.buffer_size
        self.valid_samples = min(self.buffer_size, self.valid_samples + n_samples)
        self.total_samples_ingested += n_samples

        return n_samples

    def _get_recent_count(self, window_sec: float | None = None) -> int:
        if self.valid_samples <= 0:
            return 0

        if window_sec is None:
            return self.valid_samples

        n = int(round(window_sec * self.fs))
        n = max(0, n)
        return min(self.valid_samples, n)

    def _extract_recent_channel(self, channel_idx: int, n_samples: int) -> np.ndarray:
        """
        Devuelve las últimas n_samples del canal como array contiguo float64.
        """
        if n_samples <= 0:
            return np.array([], dtype=float)

        start = (self.write_pos - n_samples) % self.buffer_size

        if start + n_samples <= self.buffer_size:
            return np.array(
                self.buffer[channel_idx, start:start + n_samples],
                dtype=float,
                copy=True,
            )

        first = self.buffer_size - start
        second = n_samples - first

        out = np.empty(n_samples, dtype=float)
        out[:first] = self.buffer[channel_idx, start:]
        out[first:] = self.buffer[channel_idx, :second]
        return out

    def _extract_recent_matrix(self, n_samples: int) -> np.ndarray:
        """
        Devuelve las últimas n_samples de todos los canales.
        shape = (num_channels, n_samples)
        """
        if n_samples <= 0:
            return np.empty((self.num_channels, 0), dtype=float)

        start = (self.write_pos - n_samples) % self.buffer_size

        if start + n_samples <= self.buffer_size:
            return np.array(
                self.buffer[:, start:start + n_samples],
                dtype=float,
                copy=True,
            )

        first = self.buffer_size - start
        second = n_samples - first

        out = np.empty((self.num_channels, n_samples), dtype=float)
        out[:, :first] = self.buffer[:, start:]
        out[:, first:] = self.buffer[:, :second]
        return out

    # ------------------- buffer -------------------
    def add_sample(self, voltages: list[float]) -> int:
        arr = np.asarray(voltages, dtype=np.float32)
        if arr.shape != (self.num_channels,):
            logger.warning(f"Número incorrecto de canales: {len(voltages)}")
            return 0

        block_v = arr.reshape(1, self.num_channels)
        return self._write_block_volts(block_v)

    def add_block_uV(self, block_samples_uV) -> int:
        """
        Ingesta por bloque.
        block_samples_uV:
            iterable de shape (n_samples, num_channels),
            con valores en microvoltios.
        """
        if block_samples_uV is None:
            return 0

        arr_uV = np.asarray(block_samples_uV, dtype=np.float32)
        if arr_uV.size == 0:
            return 0

        if arr_uV.ndim != 2 or arr_uV.shape[1] != self.num_channels:
            logger.warning(
                f"Bloque con shape incorrecta: {arr_uV.shape}, esperado (*, {self.num_channels})"
            )
            return 0

        arr_v = arr_uV * 1e-6
        return self._write_block_volts(arr_v)

    def _get_channel_array(self, channel_idx: int, window_sec: float | None = None):
        n = self._get_recent_count(window_sec)
        return self._extract_recent_channel(channel_idx, n)

    def get_recent_multichannel_window(self, window_sec: float | None = None) -> np.ndarray:
        """
        Devuelve la ventana multicanal más reciente.
        shape = (num_channels, n_samples)
        """
        n = self._get_recent_count(window_sec)
        return self._extract_recent_matrix(n)

    # ------------------- estado del buffer -------------------
    def available_samples(self, channel_idx: int = 0) -> int:
        return self.valid_samples

    def available_seconds(self, channel_idx: int = 0) -> float:
        return self.valid_samples / float(self.fs)

    def min_available_samples(self) -> int:
        return self.valid_samples

    def min_available_seconds(self) -> float:
        return self.valid_samples / float(self.fs)

    def is_window_ready(self, window_sec: float | None = None) -> bool:
        if window_sec is None:
            window_sec = self.dsp.window_sec
        needed = int(round(window_sec * self.fs))
        return self.valid_samples >= needed

    def get_buffer_status(self, window_sec: float | None = None) -> dict:
        if window_sec is None:
            window_sec = self.dsp.window_sec
        needed = int(round(window_sec * self.fs))
        have = self.valid_samples
        return {
            "min_samples": have,
            "min_seconds": have / float(self.fs),
            "needed_samples": needed,
            "needed_seconds": float(window_sec),
            "window_ready": have >= needed,
            "write_pos": self.write_pos,
            "buffer_size": self.buffer_size,
            "total_samples_ingested": self.total_samples_ingested,
        }

    # ------------------- acceso a señal -------------------
    def get_signal_window(
        self, channel_idx: int, window_sec: float | None = None
    ) -> np.ndarray:
        """
        Devuelve la señal más reciente del canal, tal y como llega del MCU,
        sin filtrado adicional en Python.
        """
        return self._get_channel_array(channel_idx, window_sec)

    # ------------------- PSD / bandas / features -------------------
    def get_power_spectrum(
        self,
        channel_idx: int,
        window_sec: float | None = None,
        method: str = "multitaper",
    ):
        x = self.get_signal_window(channel_idx, window_sec)
        if x.size < 4:
            return None, None
        freqs, pxx = self.dsp.compute_psd(x, method=method)
        return freqs, pxx

    def get_band_power(
        self,
        channel_idx: int,
        window_sec: float | None = None,
        method: str = "multitaper",
    ):
        freqs, pxx = self.get_power_spectrum(channel_idx, window_sec, method=method)
        if freqs is None:
            return {}
        return self.dsp.compute_bandpower(freqs, pxx, relative=False)

    def get_rms_amplitude(self, channel_idx: int, window_sec: float | None = None):
        x = self.get_signal_window(channel_idx, window_sec)
        if x.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(x ** 2)))

    def compute_features(
        self,
        channel_idx: int,
        window_sec: float | None = None,
        psd_method: str = "multitaper",
    ):
        """
        Ruta completa/rica:
        devuelve espectro y picos.
        """
        x_sig = self.get_signal_window(channel_idx, window_sec)
        if x_sig.size < 4:
            return {}

        return self.dsp.compute_features(
            x_sig,
            psd_method=psd_method,
            include_spectrum=True,
            include_peaks=True,
            include_relative_bandpower=True,
        )

    def compute_live_features(
        self,
        channel_idx: int,
        window_sec: float | None = None,
        psd_method: str = "multitaper",
    ):
        """
        Ruta live para dashboard:
        - sin freqs/psd completos
        - con peaks
        - con bandpower relativa
        """
        x_sig = self.get_signal_window(channel_idx, window_sec)
        if x_sig.size < 4:
            return {}

        return self.dsp.compute_features(
            x_sig,
            psd_method=psd_method,
            include_spectrum=False,
            include_peaks=True,
            include_relative_bandpower=True,
        )

    def compute_online_features(
        self,
        channel_idx: int,
        window_sec: float | None = None,
    ):
        """
        Ruta online mínima:
        - usa solo multitaper
        - no devuelve freqs/psd
        - no calcula picos
        """
        x_sig = self.get_signal_window(channel_idx, window_sec)
        if x_sig.size < 4:
            return {}

        return self.dsp.compute_features(
            x_sig,
            psd_method="multitaper",
            include_spectrum=False,
            include_peaks=False,
            include_relative_bandpower=True,
        )

    def compute_quality_diagnostics(
        self,
        channel_idx: int = 0,
        window_sec: float = 4.0,
        waveform_sec: float = 2.0,
    ) -> dict:
        """
        Metricas ligeras de calidad para diagnostico EEG en vivo.

        No modifica la senal ni el pipeline DSP principal: solo observa la
        ventana reciente que ya llega filtrada desde el MCU.
        """
        if channel_idx < 0 or channel_idx >= self.num_channels:
            return {}

        x_v = self.get_signal_window(channel_idx, window_sec)
        if x_v.size == 0:
            return {}

        x_uv = x_v.astype(float) * 1e6
        diffs = np.diff(x_uv) if x_uv.size >= 2 else np.array([], dtype=float)

        rms_uv = float(np.sqrt(np.mean(x_uv ** 2)))
        mean_uv = float(np.mean(x_uv))
        median_uv = float(np.median(x_uv))
        std_uv = float(np.std(x_uv))
        min_uv = float(np.min(x_uv))
        max_uv = float(np.max(x_uv))
        ptp_uv = float(max_uv - min_uv)
        p01_uv, p05_uv, p95_uv, p99_uv = [
            float(v) for v in np.percentile(x_uv, [1, 5, 95, 99])
        ]

        # El escalado actual del firmware usa 2.235e-8 V/count.
        adc_full_scale_uv = 8388607.0 * 2.235e-8 * 1e6
        near_adc_limit = np.abs(x_uv) >= (0.98 * adc_full_scale_uv)
        saturation_fraction = float(np.mean(near_adc_limit))

        flatline = bool(std_uv < 0.05 or ptp_uv < 0.5)
        jump_threshold_uv = max(100.0, 8.0 * std_uv)
        abrupt_jumps = int(np.sum(np.abs(diffs) > jump_threshold_uv)) if diffs.size else 0

        freqs, pxx = self.dsp.compute_psd(x_v, method="multitaper")
        line_50_power = 0.0
        total_1_50_power = 0.0
        line_50_ratio = None
        if freqs is not None and pxx is not None and len(freqs) == len(pxx):
            freqs_arr = np.asarray(freqs)
            pxx_arr = np.asarray(pxx)
            total_mask = (freqs_arr >= 1.0) & (freqs_arr <= 50.0)
            line_mask = (freqs_arr >= 49.0) & (freqs_arr <= 51.0)
            if np.any(total_mask):
                total_1_50_power = float(np.trapezoid(pxx_arr[total_mask], freqs_arr[total_mask]))
            if np.any(line_mask):
                line_50_power = float(np.trapezoid(pxx_arr[line_mask], freqs_arr[line_mask]))
            if total_1_50_power > 0:
                line_50_ratio = float(line_50_power / total_1_50_power)

        wave_n = min(int(round(waveform_sec * self.fs)), x_uv.size)
        waveform = x_uv[-wave_n:] if wave_n > 0 else np.array([], dtype=float)
        max_points = 250
        if waveform.size > max_points:
            step = int(np.ceil(waveform.size / max_points))
            waveform = waveform[::step]

        warnings = []
        if saturation_fraction > 0:
            warnings.append("possible_adc_saturation")
        if flatline:
            warnings.append("flatline_or_frozen_signal")
        if line_50_ratio is not None and line_50_ratio > 0.25:
            warnings.append("high_50hz_power")
        if abrupt_jumps > 0:
            warnings.append("abrupt_jumps")
        if abs(mean_uv) > 100.0:
            warnings.append("large_offset_after_filters")

        return {
            "channel_idx": int(channel_idx),
            "window_samples": int(x_uv.size),
            "window_sec": float(x_uv.size / float(self.fs)),
            "rms_uv": rms_uv,
            "mean_uv": mean_uv,
            "median_uv": median_uv,
            "std_uv": std_uv,
            "min_uv": min_uv,
            "max_uv": max_uv,
            "ptp_uv": ptp_uv,
            "p01_uv": p01_uv,
            "p05_uv": p05_uv,
            "p95_uv": p95_uv,
            "p99_uv": p99_uv,
            "adc_full_scale_uv_est": float(adc_full_scale_uv),
            "saturation_fraction": saturation_fraction,
            "abrupt_jumps": abrupt_jumps,
            "flatline": flatline,
            "line_50_power": line_50_power,
            "line_50_ratio": line_50_ratio,
            "warnings": warnings,
            "waveform_uV": [float(v) for v in waveform],
        }

    def get_spectrogram(
        self,
        channel_idx: int,
        window_sec: float | None = None,
        step_sec: float | None = None,
        method: str = "multitaper",
    ):
        """
        Devuelve el espectrograma de un canal usando la señal tal y como
        llega del MCU, sin filtrado adicional en Python.
        """
        x = self.get_signal_window(channel_idx, window_sec=None)
        if x.size < 4:
            return None, None, None

        return self.dsp.compute_spectrogram(
            x,
            method=method,
            window_sec=window_sec,
            step_sec=step_sec,
        )
