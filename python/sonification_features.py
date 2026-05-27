# sonification_features.py
# ------------------------------------------------------------
# EEG DSP features -> Sonification features
#
# Este módulo NO calcula DSP.
# Este módulo NO importa EEGSignalProcessor.
# Este módulo NO importa BackendService.
#
# Recibe el diccionario ya calculado por:
#   EEGSignalProcessor.compute_live_features(...)
#
# y lo convierte en controles musicales estables para tiempo real.
#
# Entrada:
#   {
#       "rms": float,                  # RMS en voltios
#       "peak_freq": float,
#       "peak_delta": float | None,
#       "peak_theta": float | None,
#       "peak_alpha": float | None,
#       "peak_beta": float | None,
#       "peak_gamma": float | None,
#       "bandpower_rel": {...},
#       "bandpower_abs": {...},
#   }
#
# Salida:
#   SonificationFeatures:
#       activity, calmness, tension, rhythmic_density,
#       register, harmonic_stability, velocity_factor,
#       note_probability, etc.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict
import math


EPS = 1e-12
BANDS = ("delta", "theta", "alpha", "beta", "gamma")


@dataclass
class SonificationFeatures:
    """
    Features musicales derivadas de las features DSP.

    Todos los controles principales están normalizados en [0, 1].
    """

    valid: bool
    quality_score: float
    quality_gate: float
    quality_state: str | None

    activity: float
    calmness: float
    tension: float
    rhythmic_density: float
    register: float
    harmonic_stability: float
    velocity_factor: float
    note_probability: float

    rms: float
    rms_uV: float
    rms_norm: float

    peak_freq: float
    peak_alpha: float | None
    peak_beta: float | None
    dominant_band: str | None

    alpha_beta_ratio: float | None
    beta_alpha_ratio: float | None
    beta_over_alpha_beta: float
    theta_alpha_ratio: float | None

    slow_power: float
    fast_power: float

    bandpower_rel: Dict[str, float]
    bandpower_abs: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el objeto a dict para snapshot/UI."""
        return asdict(self)


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convierte value a float seguro, eliminando NaN/Inf."""
    try:
        x = float(value)
    except Exception:
        return default
    return x if math.isfinite(x) else default


def _safe_optional_float(value: Any) -> float | None:
    """Convierte value a float o None si no es válido."""
    try:
        x = float(value)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def _clamp01(x: float) -> float:
    """Limita un valor al rango [0, 1]."""
    return max(0.0, min(1.0, float(x)))


def _ratio_or_none(num: float, den: float) -> float | None:
    """Devuelve num/den o None si el denominador es casi cero."""
    if abs(den) <= EPS:
        return None
    return float(num) / float(den)


def _ratio01(num: float, den: float) -> float:
    """Ratio seguro limitado a [0, 1]."""
    return _clamp01(float(num) / (float(den) + EPS))


def _ema(prev: float | None, new: float, alpha: float) -> float:
    """Suavizado exponencial simple."""
    if prev is None:
        return float(new)
    return (1.0 - alpha) * float(prev) + alpha * float(new)


def _norm_freq(freq: float, f_min: float = 0.5, f_max: float = 30.0) -> float:
    """
    Normaliza frecuencia EEG a [0, 1].

    Se usa para register:
      - frecuencias bajas -> registro grave
      - frecuencias altas -> registro agudo
    """
    if freq <= 0:
        return 0.5

    f = max(f_min, min(f_max, float(freq)))
    return (f - f_min) / (f_max - f_min)


def _get_bandpower_rel(features: Dict[str, Any]) -> Dict[str, float]:
    """Extrae bandpower_rel y garantiza todas las bandas."""
    bp = features.get("bandpower_rel", {}) or {}
    return {b: _clamp01(_safe_float(bp.get(b, 0.0))) for b in BANDS}


def _get_bandpower_abs(features: Dict[str, Any]) -> Dict[str, float]:
    """Extrae bandpower_abs y garantiza todas las bandas."""
    bp = features.get("bandpower_abs", {}) or {}
    return {b: max(0.0, _safe_float(bp.get(b, 0.0))) for b in BANDS}


def _dominant_band(bp_rel: Dict[str, float]) -> str | None:
    """Devuelve la banda relativa dominante."""
    if not bp_rel:
        return None
    return max(bp_rel.items(), key=lambda kv: kv[1])[0]


def _has_valid_features(features: Dict[str, Any]) -> bool:
    """Comprueba si hay features suficientes para sonificar."""
    if not isinstance(features, dict) or not features:
        return False
    bp_rel = features.get("bandpower_rel", {}) or {}
    return bool(bp_rel)


def build_raw_sonification_features(
    features: Dict[str, Any],
    quality_score: float | None = None,
    quality_gate: float | None = None,
    quality_state: str | None = None,
) -> SonificationFeatures:
    """
    Convierte el dict DSP en features musicales crudas.

    No suaviza.
    No usa memoria.
    No adapta baseline.
    """

    valid = _has_valid_features(features)
    q_score = 1.0 if quality_score is None else _clamp01(_safe_float(quality_score, 0.0))
    q_gate = 1.0 if quality_gate is None else _clamp01(_safe_float(quality_gate, 0.0))
    if q_score < 0.50:
        valid = False

    bp_rel = _get_bandpower_rel(features)
    bp_abs = _get_bandpower_abs(features)

    delta = bp_rel["delta"]
    theta = bp_rel["theta"]
    alpha = bp_rel["alpha"]
    beta = bp_rel["beta"]
    gamma = bp_rel["gamma"]

    rms = max(0.0, _safe_float(features.get("rms", 0.0)))
    rms_uV = rms * 1e6

    peak_freq = max(0.0, _safe_float(features.get("peak_freq", 0.0)))
    peak_alpha = _safe_optional_float(features.get("peak_alpha"))
    peak_beta = _safe_optional_float(features.get("peak_beta"))
    dom_band = _dominant_band(bp_rel)

    alpha_beta_ratio = _ratio_or_none(alpha, beta)
    beta_alpha_ratio = _ratio_or_none(beta, alpha)
    beta_over_alpha_beta = _ratio01(beta, alpha + beta)
    theta_alpha_ratio = _ratio_or_none(theta, alpha)

    slow_power = _clamp01(delta + theta)
    fast_power = _clamp01(beta + gamma)

    rms_norm = _clamp01(rms_uV / 50.0)

    alpha_over_alpha_beta = _clamp01(1.0 - beta_over_alpha_beta)
    fast_drive = _clamp01(0.65 * beta_over_alpha_beta + 0.35 * fast_power)

    activity = _clamp01(0.45 * fast_drive + 0.35 * rms_norm + 0.20 * (1.0 - alpha_over_alpha_beta))
    calmness = _clamp01(0.75 * alpha_over_alpha_beta + 0.15 * theta + 0.10 * (1.0 - gamma))
    tension = _clamp01(0.65 * beta_over_alpha_beta + 0.25 * gamma + 0.10 * rms_norm)
    rhythmic_density = _clamp01(0.55 * activity + 0.30 * tension + 0.15 * (1.0 - calmness))

    register_peak = peak_alpha if peak_alpha is not None else peak_freq
    register = _clamp01(0.65 * _norm_freq(register_peak) + 0.35 * fast_drive)

    harmonic_stability = _clamp01(0.70 * calmness + 0.30 * (1.0 - tension))
    velocity_factor = _clamp01(0.30 + 0.70 * activity)
    note_probability = _clamp01(0.15 + 0.80 * rhythmic_density)

    if not valid:
        activity = 0.0
        rhythmic_density = 0.0
        velocity_factor = 0.0
        note_probability = 0.0
        calmness = 0.5
        tension = 0.5
        register = 0.5
        harmonic_stability = 0.5

    return SonificationFeatures(
        valid=valid,
        quality_score=q_score,
        quality_gate=q_gate,
        quality_state=quality_state,
        activity=activity,
        calmness=calmness,
        tension=tension,
        rhythmic_density=rhythmic_density,
        register=register,
        harmonic_stability=harmonic_stability,
        velocity_factor=velocity_factor,
        note_probability=note_probability,
        rms=rms,
        rms_uV=rms_uV,
        rms_norm=rms_norm,
        peak_freq=peak_freq,
        peak_alpha=peak_alpha,
        peak_beta=peak_beta,
        dominant_band=dom_band,
        alpha_beta_ratio=alpha_beta_ratio,
        beta_alpha_ratio=beta_alpha_ratio,
        beta_over_alpha_beta=beta_over_alpha_beta,
        theta_alpha_ratio=theta_alpha_ratio,
        slow_power=slow_power,
        fast_power=fast_power,
        bandpower_rel=bp_rel,
        bandpower_abs=bp_abs,
    )


class SonificationFeatureAdapter:
    """
    Adaptador live con memoria.

    Se usa desde BackendService.

    Ejemplo:
        self.sonif_adapter = SonificationFeatureAdapter()

        feats = self.proc.compute_live_features(...)
        self._last_sonification = self.sonif_adapter.update(feats)
    """

    def __init__(
        self,
        ema_alpha: float = 0.24,
        rms_baseline_alpha: float = 0.02,
        min_rms_baseline_uV: float = 1.0,
    ) -> None:
        self.ema_alpha = _clamp01(ema_alpha)
        self.rms_baseline_alpha = _clamp01(rms_baseline_alpha)
        self.min_rms_baseline_uV = max(0.01, float(min_rms_baseline_uV))

        self._last: SonificationFeatures | None = None
        self._rms_baseline_uV: float | None = None

    def reset(self) -> None:
        """Resetea suavizado y baseline."""
        self._last = None
        self._rms_baseline_uV = None

    def update(
        self,
        features: Dict[str, Any],
        quality: Dict[str, Any] | None = None,
    ) -> SonificationFeatures:
        """
        Entrada principal.

        Recibe directamente self._last_features del BackendService.
        """
        quality = quality or {}
        quality_score = _safe_float(quality.get("score", 1.0), 1.0)
        quality_gate = _safe_float(quality.get("gate_factor", 1.0), 1.0)
        quality_state = quality.get("state")

        raw = build_raw_sonification_features(
            features,
            quality_score=quality_score,
            quality_gate=quality_gate,
            quality_state=str(quality_state) if quality_state is not None else None,
        )

        if _has_valid_features(features):
            rms_norm = self._update_rms_norm(raw.rms_uV, update_baseline=quality_score >= 0.70)
            raw = self._apply_rms_norm(raw, rms_norm)

        raw = self._apply_quality_gate(raw)

        smoothed = self._smooth(raw)
        self._last = smoothed
        return smoothed

    def _update_rms_norm(self, rms_uV: float, update_baseline: bool = True) -> float:
        """Actualiza baseline lento de RMS y devuelve RMS normalizado."""
        rms = max(0.0, float(rms_uV))

        if self._rms_baseline_uV is None:
            self._rms_baseline_uV = max(self.min_rms_baseline_uV, rms)
        elif update_baseline:
            a = self.rms_baseline_alpha
            self._rms_baseline_uV = _ema(self._rms_baseline_uV, rms, a)

        baseline = max(self.min_rms_baseline_uV, self._rms_baseline_uV)
        return _clamp01(rms / (2.5 * baseline))

    def _apply_rms_norm(
        self,
        raw: SonificationFeatures,
        rms_norm: float,
    ) -> SonificationFeatures:
        """Recalcula controles dependientes de RMS normalizado."""
        alpha_over_alpha_beta = _clamp01(1.0 - raw.beta_over_alpha_beta)
        fast_drive = _clamp01(0.65 * raw.beta_over_alpha_beta + 0.35 * raw.fast_power)
        raw.rms_norm = rms_norm
        raw.activity = _clamp01(0.45 * fast_drive + 0.35 * rms_norm + 0.20 * (1.0 - alpha_over_alpha_beta))
        raw.velocity_factor = _clamp01(0.30 + 0.70 * raw.activity)
        raw.rhythmic_density = _clamp01(0.55 * raw.activity + 0.30 * raw.tension + 0.15 * (1.0 - raw.calmness))
        raw.note_probability = _clamp01(0.15 + 0.80 * raw.rhythmic_density)
        return raw

    def _apply_quality_gate(self, raw: SonificationFeatures) -> SonificationFeatures:
        """Atenua controles musicales sensibles cuando la calidad espectral baja."""
        gate = _clamp01(raw.quality_gate)
        if gate >= 0.999:
            return raw

        raw.activity = _clamp01(raw.activity * gate)
        raw.tension = _clamp01(0.50 * (1.0 - gate) + raw.tension * gate)
        raw.rhythmic_density = _clamp01(raw.rhythmic_density * gate)
        raw.velocity_factor = _clamp01(0.30 + (raw.velocity_factor - 0.30) * gate)
        raw.note_probability = _clamp01(0.15 + (raw.note_probability - 0.15) * gate)
        raw.harmonic_stability = _clamp01(0.50 * (1.0 - gate) + raw.harmonic_stability * gate)
        return raw

    def _smooth(self, raw: SonificationFeatures) -> SonificationFeatures:
        """Suaviza solo controles continuos; conserva metadatos actuales."""
        prev = self._last
        if prev is None:
            return raw

        a = self.ema_alpha

        raw.activity = _ema(prev.activity, raw.activity, a)
        raw.calmness = _ema(prev.calmness, raw.calmness, a)
        raw.tension = _ema(prev.tension, raw.tension, a)
        raw.rhythmic_density = _ema(prev.rhythmic_density, raw.rhythmic_density, a)
        raw.register = _ema(prev.register, raw.register, a)
        raw.harmonic_stability = _ema(prev.harmonic_stability, raw.harmonic_stability, a)
        raw.velocity_factor = _ema(prev.velocity_factor, raw.velocity_factor, a)
        raw.note_probability = _ema(prev.note_probability, raw.note_probability, a)
        raw.rms_norm = _ema(prev.rms_norm, raw.rms_norm, a)

        return raw


def build_sonification_snapshot(
    sonif: SonificationFeatures | None,
) -> Dict[str, Any]:
    """Devuelve un dict pequeño para meter en _build_snapshot()."""
    if sonif is None:
        return {
            "valid": False,
            "state": "no_sonification_features",
        }

    out = sonif.to_dict()
    out["state"] = "ready" if sonif.valid else "invalid"
    return out


if __name__ == "__main__":
    adapter = SonificationFeatureAdapter()

    fake_features = {
        "rms": 12e-6,
        "peak_freq": 10.0,
        "peak_alpha": 10.0,
        "peak_beta": 18.0,
        "bandpower_rel": {
            "delta": 0.05,
            "theta": 0.15,
            "alpha": 0.45,
            "beta": 0.25,
            "gamma": 0.10,
        },
        "bandpower_abs": {
            "delta": 1e-12,
            "theta": 2e-12,
            "alpha": 5e-12,
            "beta": 3e-12,
            "gamma": 1e-12,
        },
    }

    for _ in range(5):
        sf = adapter.update(fake_features)
        print(sf.to_dict())
