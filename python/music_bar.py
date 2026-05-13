"""
music_bar.py
------------

Bloque 2 - Bar Generator LIVE

Genera compases musicales en tiempo real a partir de un MusicSegment live.

Este módulo ya NO depende de:
  - stability_per_bar offline
  - amplitude_slots_per_bar offline
  - normalización local por segmento

Ahora usa los controles musicales ya suavizados:

  - segment.harmonic_stability
  - segment.activity
  - segment.tension
  - segment.note_probability
  - segment.rhythm_cadence

Salida:
  - Bar con acorde diatónico
  - Bar con patrón note_positions de 16 slots
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence
import random
import math

import numpy as np

from music_segment import MusicSegment, RhythmCadence, ScaleConfig


# ------------------------------------------------------------
# Bar
# ------------------------------------------------------------

@dataclass
class Bar:
    """
    Representa un compás musical.

    Campos mantenidos por compatibilidad con music_note.py:

    index:
        Índice del compás.

    t_start / t_end:
        Tiempo absoluto del compás.

    chord_root_midi:
        Raíz MIDI del acorde.

    chord_pitches:
        Triada diatónica del compás.

    note_positions:
        Array de 16 posiciones.
        1 = hay note-on.
        0 = silencio.

    stability:
        Estabilidad armónica usada para elegir acorde.

    amplitude_slots:
        Ya no viene de amplitud EEG por slot.
        Se mantiene como envolvente musical sintética [0..1]
        para compatibilidad con music_note.py.
    """

    index: int
    t_start: float
    t_end: float
    chord_root_midi: int
    chord_pitches: List[int]
    note_positions: np.ndarray
    stability: float
    amplitude_slots: np.ndarray


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _clamp01(value: float) -> float:
    """Limita un valor a [0, 1]."""
    return max(0.0, min(1.0, float(value)))


def _safe_float(value, default: float = 0.5) -> float:
    """Convierte a float evitando NaN/Inf."""
    try:
        x = float(value)
    except Exception:
        return default
    return x if math.isfinite(x) else default


# ------------------------------------------------------------
# BarGenerator live
# ------------------------------------------------------------

class BarGenerator:
    """
    Generador de compases para sonificación en tiempo real.

    Decisiones:
      - El acorde sale de harmonic_stability/tension.
      - La cantidad de notas sale de rhythm_cadence.
      - La probabilidad de activar slots sale de note_probability.
      - La actividad aumenta densidad y acentos.
      - La tensión introduce más síncopas.
    """

    def __init__(
        self,
        beats_per_bar: int = 4,
        slots_per_beat: int = 4,
        low_notes_per_bar: int = 3,
        medium_notes_per_bar: int = 6,
        high_notes_per_bar: int = 10,
        chord_hysteresis: float = 0.10,
        random_seed: int | None = None,
    ) -> None:
        self.beats_per_bar = int(beats_per_bar)
        self.slots_per_beat = int(slots_per_beat)
        self.n_slots = self.beats_per_bar * self.slots_per_beat

        # En directo evitamos 16 notas por compás para no saturar MIDI.
        self.low_notes_per_bar = int(low_notes_per_bar)
        self.medium_notes_per_bar = int(medium_notes_per_bar)
        self.high_notes_per_bar = int(high_notes_per_bar)

        # Histéresis armónica para evitar saltos I-IV-V constantes.
        self.chord_hysteresis = max(0.0, float(chord_hysteresis))
        self._last_degree_idx = 0

        self.rng = random.Random(random_seed)

    # --------------------------------------------------------
    # Acordes
    # --------------------------------------------------------

    def _build_diatonic_triad(
        self,
        scale: ScaleConfig,
        degree_idx: int,
        base_octave_offset: int = 0,
    ) -> tuple[int, List[int]]:
        """
        Construye una triada diatónica.

        degree_idx:
          0 = I
          3 = IV
          4 = V

        Usa intervalos de la escala, por lo que funciona con mayor,
        menor, modos y pentatónicas si tienen suficientes grados.
        """
        intervals = list(scale.intervals)
        n = len(intervals)

        if n == 0:
            root = int(scale.root_midi)
            return root, [root]

        d = int(degree_idx) % n

        root = scale.root_midi + 12 * base_octave_offset + intervals[d]
        third = scale.root_midi + 12 * base_octave_offset + intervals[(d + 2) % n]
        fifth = scale.root_midi + 12 * base_octave_offset + intervals[(d + 4) % n]

        return int(root), [int(root), int(third), int(fifth)]

    def _target_degree_raw(self, stability: float, tension: float, n_degrees: int) -> int:
        """
        Selecciona grado armónico sin histéresis.

        Reglas:
          - Estabilidad alta y tensión baja -> I
          - Zona media -> IV
          - Estabilidad baja o tensión alta -> V
        """
        if n_degrees < 5:
            return 0

        s = _clamp01(stability)
        t = _clamp01(tension)

        if s > 0.66 and t < 0.65:
            return 0  # I, reposo

        if s < 0.33 or t > 0.72:
            return 4  # V, tensión

        return 3      # IV, zona intermedia

    def _choose_chord_degree(self, segment: MusicSegment) -> int:
        """
        Selecciona el grado del acorde con histéresis.

        Esto evita que pequeños cambios EEG cambien el acorde
        constantemente en directo.
        """
        n_degrees = len(segment.scale.intervals)
        raw = self._target_degree_raw(
            stability=segment.harmonic_stability,
            tension=segment.tension,
            n_degrees=n_degrees,
        )

        if raw == self._last_degree_idx:
            return raw

        # Cambio permitido si la señal musical es suficientemente clara.
        s = _clamp01(segment.harmonic_stability)
        t = _clamp01(segment.tension)
        h = self.chord_hysteresis

        if raw == 0 and s > 0.66 + h:
            self._last_degree_idx = raw
        elif raw == 4 and (s < 0.33 - h or t > 0.72 + h):
            self._last_degree_idx = raw
        elif raw == 3 and 0.25 < s < 0.75:
            self._last_degree_idx = raw

        return self._last_degree_idx

    # --------------------------------------------------------
    # Ritmo
    # --------------------------------------------------------

    def _target_notes_for_cadence(self, cadence: RhythmCadence) -> int:
        """Cantidad base de notas por compás según cadencia."""
        if cadence == RhythmCadence.LOW:
            return self.low_notes_per_bar

        if cadence == RhythmCadence.HIGH:
            return self.high_notes_per_bar

        return self.medium_notes_per_bar

    def _base_slot_weights(self) -> list[float]:
        """
        Pesos musicales base por slot.

        Se favorecen:
          - downbeat del compás
          - beats principales
          - algunas subdivisiones musicales
        """
        weights = [0.10] * self.n_slots

        for i in range(self.n_slots):
            if i == 0:
                weights[i] = 1.00          # primer golpe del compás
            elif i % self.slots_per_beat == 0:
                weights[i] = 0.75          # beat
            elif i % 2 == 0:
                weights[i] = 0.45          # semicorchea par
            else:
                weights[i] = 0.25          # síncopa/offbeat

        return weights

    def _apply_eeg_to_weights(
        self,
        weights: list[float],
        activity: float,
        tension: float,
        note_probability: float,
    ) -> list[float]:
        """
        Modula los pesos rítmicos con EEG.

        activity:
            Aumenta probabilidad global.

        tension:
            Favorece síncopas/offbeats.

        note_probability:
            Control directo de cuántos slots pueden activarse.
        """
        a = _clamp01(activity)
        t = _clamp01(tension)
        p = _clamp01(note_probability)

        out = []

        for idx, w in enumerate(weights):
            is_offbeat = idx % self.slots_per_beat != 0

            # Actividad sube todo.
            w *= 0.50 + 0.80 * a

            # Tensión da más peso a offbeats.
            if is_offbeat:
                w *= 0.80 + 0.70 * t

            # Probabilidad general de notas.
            w *= 0.40 + 0.90 * p

            out.append(max(0.0, w))

        return out

    def _weighted_pick_unique(self, weights: Sequence[float], k: int) -> list[int]:
        """
        Elige k slots sin repetir usando pesos.

        Implementación simple y eficiente para 16 slots.
        """
        available = list(range(len(weights)))
        chosen: list[int] = []

        for _ in range(max(0, min(k, len(weights)))):
            total = sum(weights[i] for i in available)

            if total <= 0:
                idx = available[0]
            else:
                r = self.rng.random() * total
                acc = 0.0
                idx = available[-1]

                for candidate in available:
                    acc += weights[candidate]
                    if acc >= r:
                        idx = candidate
                        break

            chosen.append(idx)
            available.remove(idx)

        chosen.sort()
        return chosen

    def _build_note_positions(self, segment: MusicSegment) -> np.ndarray:
        """
        Genera el patrón ON/OFF del compás.

        Mantiene siempre slot 0 activo para anclar el compás.
        """
        target = self._target_notes_for_cadence(segment.rhythm_cadence)

        # Ajuste fino por actividad.
        activity = _clamp01(segment.activity)
        if activity > 0.75:
            target += 1
        elif activity < 0.25:
            target -= 1

        target = max(1, min(target, self.n_slots))

        weights = self._base_slot_weights()
        weights = self._apply_eeg_to_weights(
            weights=weights,
            activity=segment.activity,
            tension=segment.tension,
            note_probability=segment.note_probability,
        )

        # El primer slot se fuerza como ancla musical.
        positions = np.zeros(self.n_slots, dtype=int)
        positions[0] = 1

        if target > 1:
            weights[0] = 0.0
            chosen = self._weighted_pick_unique(weights, target - 1)

            for idx in chosen:
                positions[idx] = 1

        return positions

    def _build_amplitude_slots(self, segment: MusicSegment, note_positions: np.ndarray) -> np.ndarray:
        """
        Crea una envolvente musical sintética.

        Ya no representa amplitud EEG por slot.
        Sirve para compatibilidad con music_note.py y para modular
        ligeramente velocity/octava si el siguiente bloque lo usa.
        """
        amps = np.full(self.n_slots, 0.25, dtype=float)

        activity = _clamp01(segment.activity)
        velocity = _clamp01(segment.velocity_factor)

        for i in range(self.n_slots):
            if note_positions[i]:
                if i == 0:
                    amps[i] = 0.90
                elif i % self.slots_per_beat == 0:
                    amps[i] = 0.70
                else:
                    amps[i] = 0.45

                amps[i] = _clamp01(amps[i] * (0.70 + 0.60 * velocity))

        # Actividad sube levemente toda la envolvente.
        amps = np.clip(amps + 0.10 * activity, 0.0, 1.0)
        return amps

    # --------------------------------------------------------
    # API live
    # --------------------------------------------------------

    def generate_live_bar(
        self,
        segment: MusicSegment,
        index: int = 0,
        base_octave_offset: int = 0,
    ) -> Bar:
        """
        Genera un único compás live a partir del MusicSegment actual.

        Este es el método principal para tiempo real.
        """
        degree_idx = self._choose_chord_degree(segment)

        chord_root, chord_pitches = self._build_diatonic_triad(
            scale=segment.scale,
            degree_idx=degree_idx,
            base_octave_offset=base_octave_offset,
        )

        note_positions = self._build_note_positions(segment)
        amplitude_slots = self._build_amplitude_slots(segment, note_positions)

        return Bar(
            index=int(index),
            t_start=float(segment.segment.t_start),
            t_end=float(segment.segment.t_end),
            chord_root_midi=chord_root,
            chord_pitches=chord_pitches,
            note_positions=note_positions,
            stability=_clamp01(segment.harmonic_stability),
            amplitude_slots=amplitude_slots,
        )

    def generate_live_bars(
        self,
        segment: MusicSegment,
        n_bars: int = 1,
        base_octave_offset: int = 0,
    ) -> List[Bar]:
        """
        Genera n compases live dentro de la duración de segment.

        Normalmente en tiempo real se usará n_bars=1.
        """
        n = max(1, int(n_bars))
        total_duration = max(0.001, float(segment.segment.duration_sec))
        bar_duration = total_duration / n

        bars: list[Bar] = []

        for i in range(n):
            sub_seg = segment
            sub_seg.segment.t_start = segment.segment.t_start + i * bar_duration
            sub_seg.segment.t_end = sub_seg.segment.t_start + bar_duration

            bars.append(
                self.generate_live_bar(
                    segment=sub_seg,
                    index=i,
                    base_octave_offset=base_octave_offset,
                )
            )

        return bars

    # --------------------------------------------------------
    # Compatibilidad temporal
    # --------------------------------------------------------

    def generate_bars(
        self,
        segment: MusicSegment,
        stability_per_bar=None,
        amplitude_slots_per_bar=None,
        base_octave_offset: int = 0,
    ) -> List[Bar]:
        """
        Wrapper de compatibilidad.

        El pipeline live debe usar generate_live_bar().
        Este método existe para no romper llamadas antiguas mientras
        se migra el resto del sistema.
        """
        return self.generate_live_bars(
            segment=segment,
            n_bars=1,
            base_octave_offset=base_octave_offset,
        )


# ------------------------------------------------------------
# Prueba rápida local
# ------------------------------------------------------------

if __name__ == "__main__":
    from music_segment import (
        LiveSegment,
        ScaleConfig,
        MusicSegment,
        MAJOR_INTERVALS,
        RhythmCadence,
    )

    scale = ScaleConfig(
        root_midi=60,
        name="C_major",
        intervals=MAJOR_INTERVALS,
    )

    seg = LiveSegment(
        start_idx=0,
        end_idx=500,
        t_start=0.0,
        t_end=2.0,
    )

    music_seg = MusicSegment(
        segment=seg,
        main_note_midi=67,
        scale=scale,
        rhythm_cadence=RhythmCadence.MEDIUM,
        register_hint=0.55,
        features={},
        activity=0.65,
        calmness=0.40,
        tension=0.55,
        harmonic_stability=0.45,
        velocity_factor=0.75,
        note_probability=0.70,
        valid=True,
    )

    gen = BarGenerator(random_seed=123)
    bar = gen.generate_live_bar(music_seg)

    print("Bar:")
    print("  chord_root:", bar.chord_root_midi)
    print("  chord:", bar.chord_pitches)
    print("  note_positions:", bar.note_positions.tolist())
    print("  amplitude_slots:", np.round(bar.amplitude_slots, 2).tolist())
