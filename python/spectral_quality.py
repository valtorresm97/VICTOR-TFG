from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import math


EPS = 1e-12


@dataclass
class SpectralQuality:
    score: float
    state: str
    gate_factor: float
    valid_for_sonification: bool
    freeze_recommended: bool
    warnings: list[str]
    penalties: dict[str, float]
    inputs: dict[str, float | int | bool | None]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _penalty_ramp(value: float, start: float, stop: float, max_penalty: float) -> float:
    if value <= start:
        return 0.0
    if value >= stop:
        return float(max_penalty)
    return float(max_penalty) * (value - start) / max(stop - start, EPS)


def compute_spectral_quality(
    features: dict[str, Any] | None,
    diagnostics: dict[str, Any] | None,
    rx_metrics: dict[str, Any] | None = None,
    *,
    window_ready: bool = True,
) -> SpectralQuality:
    """
    Quality gate for live EEG sonification.

    This is deliberately a separate layer from DSPCore: it evaluates whether a
    recent spectral feature window is safe to use musically, without changing
    the band definitions, filters, PSD method, or ADS1299 acquisition path.
    """
    features = features or {}
    diagnostics = diagnostics or {}
    rx_metrics = rx_metrics or {}

    penalties: dict[str, float] = {}
    warnings: list[str] = []

    def add(name: str, value: float, warning: str | None = None) -> None:
        value = max(0.0, float(value))
        if value <= 0:
            return
        penalties[name] = penalties.get(name, 0.0) + value
        warnings.append(warning or name)

    if not window_ready:
        add("window_not_ready", 0.50)

    band_rel = features.get("bandpower_rel", {}) or {}
    finite_bands = bool(band_rel)
    for value in list(band_rel.values()) + list((features.get("bandpower_abs", {}) or {}).values()):
        try:
            finite_bands = finite_bands and math.isfinite(float(value))
        except Exception:
            finite_bands = False
            break
    if not finite_bands:
        add("non_finite_or_missing_bandpowers", 0.50)

    # Prefer per-feature deltas or rolling-window counters over lifetime totals:
    # a single old transport error should not keep the live sonification muted forever.
    invalid_status = int(
        rx_metrics.get(
            "invalid_status_delta",
            rx_metrics.get("invalid_status_window", rx_metrics.get("invalid_status_total", 0)),
        )
        or 0
    )
    lost_frames = int(
        rx_metrics.get(
            "lost_frames_delta",
            rx_metrics.get("lost_frames_window", rx_metrics.get("lost_frames_total", 0)),
        )
        or 0
    )
    lost_blocks = int(
        rx_metrics.get(
            "lost_blocks_delta",
            rx_metrics.get("lost_blocks_window", rx_metrics.get("lost_blocks_total", 0)),
        )
        or 0
    )
    queue_drops = int(
        rx_metrics.get(
            "queue_drops_frames_delta",
            rx_metrics.get("queue_drops_frames_window", rx_metrics.get("queue_drops_frames_total", 0)),
        )
        or 0
    ) + int(
        rx_metrics.get(
            "queue_drops_blocks_delta",
            rx_metrics.get("queue_drops_blocks_window", rx_metrics.get("queue_drops_blocks_total", 0)),
        )
        or 0
    )
    malformed = int(
        rx_metrics.get(
            "malformed_blocks_delta",
            rx_metrics.get("malformed_blocks_window", rx_metrics.get("malformed_blocks_total", 0)),
        )
        or 0
    )
    if invalid_status > 0:
        add("invalid_ads1299_status_seen", 0.35)
    if lost_frames > 0 or lost_blocks > 0 or queue_drops > 0 or malformed > 0:
        add("receiver_transport_errors_seen", 0.25)

    rms_uv = _safe_float(diagnostics.get("rms_uv"), _safe_float(features.get("rms")) * 1e6)
    ptp_uv = _safe_float(diagnostics.get("ptp_uv"))
    line_50_ratio = diagnostics.get("line_50_ratio")
    line_50_ratio = None if line_50_ratio is None else _safe_float(line_50_ratio)
    saturation_fraction = _safe_float(diagnostics.get("saturation_fraction"))
    abrupt_jumps = int(diagnostics.get("abrupt_jumps", 0) or 0)
    flatline = bool(diagnostics.get("flatline", False))

    if saturation_fraction > 0:
        add("possible_adc_saturation", min(0.60, 0.30 + saturation_fraction), "possible_adc_saturation")
    if flatline:
        add("flatline_or_frozen_signal", 0.35)

    # Empirical range from validation captures:
    # shorted_inputs ~0 uV; clean ear-EEG ~9-12 uV; clean Fp1-Fp2 ~30-50 uV;
    # jaw/movement artifacts >200 uV and sometimes mV-level.
    if rms_uv < 3.0:
        add("rms_too_low_for_scalp_eeg", 0.10)
    add("high_rms", _penalty_ramp(rms_uv, 120.0, 400.0, 0.35))
    if rms_uv > 200.0:
        add("artifact_rms_range", 0.25)

    if ptp_uv > 2500.0:
        add("large_peak_to_peak", _penalty_ramp(ptp_uv, 2500.0, 10000.0, 0.30))
    if ptp_uv > 5000.0:
        add("artifact_peak_to_peak", 0.20)

    if line_50_ratio is not None:
        add("high_50hz_ratio", _penalty_ramp(line_50_ratio, 0.25, 0.45, 0.30))

    if abrupt_jumps > 0:
        add("abrupt_jumps", min(0.25, 0.05 + 0.01 * abrupt_jumps))

    gamma_rel = _safe_float(band_rel.get("gamma", 0.0))
    slow_rel = _safe_float(band_rel.get("delta", 0.0)) + _safe_float(band_rel.get("theta", 0.0))
    if gamma_rel > 0.55:
        add("very_high_gamma_rel", 0.15)
    if slow_rel > 0.85 and rms_uv > 80.0:
        add("slow_power_with_high_rms", 0.20)

    score = _clamp01(1.0 - sum(penalties.values()))
    if score >= 0.85:
        state = "clean"
        gate_factor = 1.0
    elif score >= 0.70:
        state = "usable_with_caution"
        gate_factor = 0.75
    elif score >= 0.50:
        state = "artifact_suspected"
        gate_factor = 0.35
    else:
        state = "bad"
        gate_factor = 0.0

    return SpectralQuality(
        score=score,
        state=state,
        gate_factor=gate_factor,
        valid_for_sonification=score >= 0.50,
        freeze_recommended=score < 0.50,
        warnings=warnings,
        penalties={key: float(value) for key, value in penalties.items()},
        inputs={
            "window_ready": bool(window_ready),
            "rms_uv": rms_uv,
            "ptp_uv": ptp_uv,
            "line_50_ratio": line_50_ratio,
            "saturation_fraction": saturation_fraction,
            "abrupt_jumps": abrupt_jumps,
            "flatline": flatline,
            "gamma_rel": gamma_rel,
            "slow_power_rel": slow_rel,
            "invalid_status_total": invalid_status,
            "lost_frames_total": lost_frames,
            "lost_blocks_total": lost_blocks,
            "queue_drops_total": queue_drops,
            "malformed_blocks_total": malformed,
        },
    )
