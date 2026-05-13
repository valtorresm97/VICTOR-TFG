"""
music_segment.py
----------------

Bloque 1 - Music Segment LIVE

Este módulo convierte las features musicales ya suavizadas de
sonification_features.py en un estado musical usable por:

  - music_bar.py
  - music_note.py
  - motor MIDI live futuro

IMPORTANTE:
- No calcula DSP.
- No usa EEGSegmenter.
- No segmenta EEG offline.
- No decide la main note automáticamente.
- La escala y la nota principal siguen siendo decisión del usuario/UI.
- El EEG modula densidad, registro, tensión, dinámica y estabilidad.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum, auto
from typing import Any, Dict, Optional, Sequence
import math

from sonification_features import SonificationFeatures


# ------------------------------------------------------------
# Utilidades pequeñas
# ------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.5) -> float:
    """Convierte un valor a float seguro, evitando NaN/Inf."""
    try:
        x = float(value)
    except Exception:
        return default
    return x if math.isfinite(x) else default


def _clamp01(value: float) -> float:
    """Limita un valor al rango [0, 1]."""
    return max(0.0, min(1.0, float(value)))


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """
    Lee un campo desde un objeto o un dict.

    Permite usar:
      - SonificationFeatures
      - dict procedente de snapshot["sonification"]
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


# ------------------------------------------------------------
# Segmento temporal mínimo para tiempo real
# ------------------------------------------------------------

@dataclass
class LiveSegment:
    """
    Segmento temporal mínimo.

    No representa una segmentación EEG offline.
    Solo define una ventana musical viva:
      - t_start
      - t_end
      - duración

    Se mantiene con nombres start_idx/end_idx para compatibilidad
    con bloques antiguos, aunque en live no son lo importante.
    """

    start_idx: int
    end_idx: int
    t_start: float
    t_end: float

    @property
    def duration_sec(self) -> float:
        """Duración del segmento musical en segundos."""
        return max(0.0, self.t_end - self.t_start)


# ------------------------------------------------------------
# Escala musical
# ------------------------------------------------------------

@dataclass
class ScaleConfig:
    """
    Configuración de escala musical.

    root_midi:
        Nota raíz en MIDI. Ejemplo: 60 = C4.

    name:
        Nombre de la escala. Ejemplo: C_major.

    intervals:
        Semitonos de la escala dentro de una octava.
        Ejemplo escala mayor: [0, 2, 4, 5, 7, 9, 11].
    """

    root_midi: int
    name: str
    intervals: Sequence[int]

    def contains(self, midi_note: int) -> bool:
        """True si midi_note pertenece a la escala."""
        rel = (int(midi_note) - int(self.root_midi)) % 12
        return rel in self.intervals

    def nearest_note(self, midi_note: int) -> int:
        """Devuelve la nota de la escala más cercana a midi_note."""
        best = int(midi_note)
        best_dist = float("inf")

        for octave in range(-3, 4):
            base = int(self.root_midi) + 12 * octave
            for interval in self.intervals:
                candidate = base + int(interval)
                dist = abs(candidate - int(midi_note))
                if dist < best_dist:
                    best = candidate
                    best_dist = dist

        return int(best)


MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
NAT_MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]


# ------------------------------------------------------------
# Cadencia rítmica discreta
# ------------------------------------------------------------

class RhythmCadence(Enum):
    """Nivel discreto de densidad rítmica."""

    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


# ------------------------------------------------------------
# Estado musical live
# ------------------------------------------------------------

@dataclass
class MusicSegment:
    """
    Estado musical para una ventana live.

    Se llama MusicSegment para mantener compatibilidad con:
      - music_bar.py
      - music_note.py

    Pero conceptualmente ya no es un segmento EEG offline.
    Es el estado musical actual derivado de SonificationFeatures.
    """

    segment: LiveSegment

    main_note_midi: int
    scale: ScaleConfig
    rhythm_cadence: RhythmCadence
    register_hint: float

    # Features DSP originales, por trazabilidad/debug.
    features: Dict[str, Any]

    # Controles musicales live normalizados [0, 1].
    activity: float
    calmness: float
    tension: float
    harmonic_stability: float
    velocity_factor: float
    note_probability: float

    # Estado de validez.
    valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Devuelve dict serializable para debug/snapshot."""
        out = asdict(self)
        out["rhythm_cadence"] = self.rhythm_cadence.name
        return out


# ------------------------------------------------------------
# Builder live
# ------------------------------------------------------------

class MusicSegmentBuilder:
    """
    Construye MusicSegment para tiempo real.

    Entrada principal:
      - SonificationFeatures ya suavizadas.
      - Escala seleccionada por usuario.
      - Main note seleccionada por usuario.
      - Tiempo musical actual.

    El EEG NO cambia directamente la tonalidad ni la main note.
    Solo modula:
      - cadencia rítmica,
      - registro,
      - tensión,
      - estabilidad armónica,
      - dinámica,
      - probabilidad de nota.
    """

    def __init__(
        self,
        fs: float = 250.0,
        density_low: float = 0.33,
        density_high: float = 0.66,
        cadence_hysteresis: float = 0.08,
    ) -> None:
        self.fs = float(fs)

        # Umbrales para pasar de densidad continua a LOW/MEDIUM/HIGH.
        self.density_low = _clamp01(density_low)
        self.density_high = _clamp01(density_high)

        # Histéresis para evitar cambios bruscos de cadencia.
        self.cadence_hysteresis = max(0.0, float(cadence_hysteresis))

        # Estado previo de cadencia.
        self._last_cadence = RhythmCadence.MEDIUM

    def reset(self) -> None:
        """Reinicia el estado de histéresis."""
        self._last_cadence = RhythmCadence.MEDIUM

    def _map_density_to_cadence(self, density: float) -> RhythmCadence:
        """
        Convierte rhythmic_density [0,1] en LOW/MEDIUM/HIGH.

        Usa histéresis para que el ritmo no salte continuamente
        por pequeñas fluctuaciones EEG.
        """
        d = _clamp01(density)
        h = self.cadence_hysteresis
        prev = self._last_cadence

        if prev == RhythmCadence.LOW:
            return RhythmCadence.MEDIUM if d > self.density_low + h else RhythmCadence.LOW

        if prev == RhythmCadence.HIGH:
            return RhythmCadence.MEDIUM if d < self.density_high - h else RhythmCadence.HIGH

        if d < self.density_low - h:
            return RhythmCadence.LOW

        if d > self.density_high + h:
            return RhythmCadence.HIGH

        return RhythmCadence.MEDIUM

    def _make_live_segment(
        self,
        t_start: float,
        duration_sec: float,
    ) -> LiveSegment:
        """
        Crea una ventana temporal musical.

        No depende del EEGSegmenter.
        """
        t0 = max(0.0, float(t_start))
        dur = max(0.001, float(duration_sec))
        t1 = t0 + dur

        return LiveSegment(
            start_idx=int(round(t0 * self.fs)),
            end_idx=int(round(t1 * self.fs)),
            t_start=t0,
            t_end=t1,
        )

    def build_live_segment(
        self,
        sonification_features: SonificationFeatures | Dict[str, Any],
        user_scale: ScaleConfig,
        user_main_note_midi: Optional[int] = None,
        eeg_features: Optional[Dict[str, Any]] = None,
        t_start: float = 0.0,
        duration_sec: float = 2.0,
    ) -> MusicSegment:
        """
        Construye el estado musical live.

        sonification_features:
            Objeto SonificationFeatures o dict.

        user_scale:
            Escala fija elegida por usuario/UI.

        user_main_note_midi:
            Nota principal fija elegida por usuario/UI.
            Si es None, se usa user_scale.root_midi.

        eeg_features:
            Dict DSP original. Solo se guarda para debug/trazabilidad.

        t_start / duration_sec:
            Ventana musical actual.
        """

        valid = bool(_get(sonification_features, "valid", False))

        rhythmic_density = _clamp01(
            _safe_float(_get(sonification_features, "rhythmic_density", 0.0), 0.0)
        )

        cadence = self._map_density_to_cadence(rhythmic_density)
        self._last_cadence = cadence

        main_note = (
            int(user_scale.root_midi)
            if user_main_note_midi is None
            else int(user_main_note_midi)
        )

        return MusicSegment(
            segment=self._make_live_segment(t_start, duration_sec),
            main_note_midi=main_note,
            scale=user_scale,
            rhythm_cadence=cadence,
            register_hint=_clamp01(_safe_float(_get(sonification_features, "register", 0.5), 0.5)),
            features=eeg_features or {},
            activity=_clamp01(_safe_float(_get(sonification_features, "activity", 0.5), 0.5)),
            calmness=_clamp01(_safe_float(_get(sonification_features, "calmness", 0.5), 0.5)),
            tension=_clamp01(_safe_float(_get(sonification_features, "tension", 0.5), 0.5)),
            harmonic_stability=_clamp01(_safe_float(_get(sonification_features, "harmonic_stability", 0.5), 0.5)),
            velocity_factor=_clamp01(_safe_float(_get(sonification_features, "velocity_factor", 0.5), 0.5)),
            note_probability=_clamp01(_safe_float(_get(sonification_features, "note_probability", 0.5), 0.5)),
            valid=valid,
        )


# ------------------------------------------------------------
# Prueba rápida local
# ------------------------------------------------------------

if __name__ == "__main__":
    scale = ScaleConfig(
        root_midi=60,
        name="C_major",
        intervals=MAJOR_INTERVALS,
    )

    sonif = {
        "valid": True,
        "activity": 0.7,
        "calmness": 0.3,
        "tension": 0.6,
        "rhythmic_density": 0.75,
        "register": 0.65,
        "harmonic_stability": 0.4,
        "velocity_factor": 0.8,
        "note_probability": 0.7,
    }

    builder = MusicSegmentBuilder(fs=250.0)

    music_segment = builder.build_live_segment(
        sonification_features=sonif,
        user_scale=scale,
        user_main_note_midi=67,
        eeg_features={"rms": 12e-6},
        t_start=0.0,
        duration_sec=2.0,
    )

    print(music_segment.to_dict())
