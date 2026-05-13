"""
music_note.py
-------------

Bloque 3 - Note Generator LIVE

Convierte:
  - un MusicSegment live,
  - uno o varios Bar live,

en eventos NoteEvent listos para:
  - exportación MIDI offline,
  - scheduler MIDI live,
  - envío futuro por MCU/D1/TX.

Este módulo NO calcula DSP.
Este módulo NO lee alpha/beta directamente de features.
Este módulo usa los controles musicales ya suavizados:

  - segment.register_hint
  - segment.tension
  - segment.velocity_factor
  - segment.activity
  - segment.note_probability

Reglas musicales mantenidas:
  - downbeats -> notas de acorde;
  - upbeats/offbeats -> notas de paso cuando sea posible;
  - salto melódico limitado;
  - duración hasta siguiente note-on o fin de compás;
  - velocity por acento rítmico + factor EEG.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence
import math

from music_segment import MusicSegment, ScaleConfig
from music_bar import Bar


# ------------------------------------------------------------
# Evento de nota
# ------------------------------------------------------------

@dataclass
class NoteEvent:
    """
    Evento musical de alto nivel.

    Todavía NO son bytes MIDI.
    Este objeto luego se convierte en:
      - note_on
      - note_off
      - mensajes MIDI live o archivo .mid
    """

    t_start: float
    t_end: float
    pitch_midi: int
    velocity: int
    channel: int = 0
    program: int = 0


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    """Limita value entre lo y hi."""
    return max(lo, min(hi, float(value)))


def _clamp_int(value: int, lo: int, hi: int) -> int:
    """Limita int entre lo y hi."""
    return max(lo, min(hi, int(value)))


def _safe_float(value, default: float = 0.5) -> float:
    """Convierte a float evitando NaN/Inf."""
    try:
        x = float(value)
    except Exception:
        return default
    return x if math.isfinite(x) else default


# ------------------------------------------------------------
# NoteGenerator live
# ------------------------------------------------------------

class NoteGenerator:
    """
    Generador de notas para sonificación EEG en tiempo real.

    Entrada:
      - MusicSegment live
      - Bar live

    Salida:
      - List[NoteEvent]

    El pitch y velocity se modulan con EEG ya suavizado,
    no con features crudas.
    """

    def __init__(
        self,
        beats_per_bar: int = 4,
        slots_per_beat: int = 4,
        max_interval_semitones: int = 7,
        base_velocity_downbeat: int = 104,
        base_velocity_beat: int = 88,
        base_velocity_offbeat: int = 72,
        min_velocity: int = 28,
        max_velocity: int = 118,
        default_channel: int = 0,
        default_program: int = 0,
        chord_on_first_slot: bool = True,
        max_chord_voices: int = 3,
    ) -> None:
        self.beats_per_bar = int(beats_per_bar)
        self.slots_per_beat = int(slots_per_beat)
        self.n_slots = self.beats_per_bar * self.slots_per_beat

        # El paper limitaba intervalos melódicos para evitar melodía caótica.
        self.max_interval = int(max_interval_semitones)

        self.base_velocity_downbeat = int(base_velocity_downbeat)
        self.base_velocity_beat = int(base_velocity_beat)
        self.base_velocity_offbeat = int(base_velocity_offbeat)

        self.min_velocity = int(min_velocity)
        self.max_velocity = int(max_velocity)

        self.default_channel = int(default_channel)
        self.default_program = int(default_program)

        # Acorde completo al inicio del compás: útil, pero controlable.
        self.chord_on_first_slot = bool(chord_on_first_slot)
        self.max_chord_voices = int(max_chord_voices)

        # Estado melódico persistente para directo.
        self._prev_pitch: Optional[int] = None

    # --------------------------------------------------------
    # Estado
    # --------------------------------------------------------

    def reset(self) -> None:
        """Reinicia memoria melódica."""
        self._prev_pitch = None

    # --------------------------------------------------------
    # Pitch / escala
    # --------------------------------------------------------

    def _register_center(self, segment: MusicSegment) -> int:
        """
        Calcula centro de registro MIDI.

        register_hint:
          0.0 -> más grave
          0.5 -> cerca de main_note
          1.0 -> más agudo

        La main_note sigue siendo fija y musical.
        El EEG solo desplaza suavemente el registro.
        """
        base = int(segment.main_note_midi)
        register = _clamp(_safe_float(segment.register_hint, 0.5), 0.0, 1.0)

        # Rango máximo: ±12 semitonos.
        offset = int(round((register - 0.5) * 24.0))
        center = base + offset

        # Rango musical seguro.
        return _clamp_int(center, 36, 96)

    def _scale_pitches_around(
        self,
        scale: ScaleConfig,
        center: int,
        radius: int = 14,
    ) -> list[int]:
        """Crea notas de la escala alrededor del centro."""
        low = int(center) - int(radius)
        high = int(center) + int(radius)

        return [p for p in range(low, high + 1) if scale.contains(p)]

    def _split_chord_and_passing(
        self,
        scale_pitches: Sequence[int],
        chord_pitches: Sequence[int],
    ) -> tuple[list[int], list[int]]:
        """
        Separa notas de escala en:
          - chord_tones
          - passing_tones
        """
        chord_classes = {int(p) % 12 for p in chord_pitches}

        chord_tones: list[int] = []
        passing_tones: list[int] = []

        for pitch in scale_pitches:
            if int(pitch) % 12 in chord_classes:
                chord_tones.append(int(pitch))
            else:
                passing_tones.append(int(pitch))

        if not chord_tones:
            chord_tones = [int(p) for p in chord_pitches]

        return chord_tones, passing_tones

    def _is_downbeat(self, slot_idx: int) -> bool:
        """True si el slot es inicio de beat."""
        return int(slot_idx) % self.slots_per_beat == 0

    def _pitch_target(self, segment: MusicSegment, center: int) -> float:
        """
        Pitch objetivo por EEG.

        tension:
          baja -> alrededor/ligeramente por debajo del centro
          alta -> empuja hacia arriba

        No rompe escala porque luego se elige candidato diatónico.
        """
        tension = _clamp(_safe_float(segment.tension, 0.5), 0.0, 1.0)

        # ±7 semitonos alrededor del centro.
        return float(center) + (tension - 0.5) * 14.0

    def _choose_pitch(
        self,
        segment: MusicSegment,
        slot_idx: int,
        chord_tones: Sequence[int],
        passing_tones: Sequence[int],
        center: int,
    ) -> int:
        """
        Elige pitch combinando:
          - regla musical downbeat/upbeat,
          - continuidad melódica,
          - tensión EEG suavizada.
        """
        if self._is_downbeat(slot_idx):
            candidates = list(chord_tones)
        else:
            candidates = list(passing_tones) if passing_tones else list(chord_tones)

        if not candidates:
            return int(segment.main_note_midi)

        target = self._pitch_target(segment, center)
        prev = self._prev_pitch

        if prev is None:
            best = min(
                candidates,
                key=lambda p: 0.55 * abs(p - center) + 0.45 * abs(p - target),
            )
        else:
            best = min(
                candidates,
                key=lambda p: 0.72 * abs(p - prev) + 0.28 * abs(p - target),
            )

        return self._apply_interval_limit(int(best), prev, center)

    def _apply_interval_limit(
        self,
        candidate: int,
        prev: Optional[int],
        center: int,
    ) -> int:
        """
        Limita saltos melódicos.

        Si una nota queda demasiado lejos de la anterior,
        se desplaza por octavas hasta acercarla.
        """
        pitch = int(candidate)

        if prev is None:
            return _clamp_int(pitch, 0, 127)

        while pitch - prev > self.max_interval:
            pitch -= 12

        while prev - pitch > self.max_interval:
            pitch += 12

        if abs(pitch - prev) > self.max_interval:
            pitch = int(center)

        return _clamp_int(pitch, 0, 127)

    def _chord_voices(
        self,
        chord_tones: Sequence[int],
        center: int,
    ) -> list[int]:
        """Selecciona voces de acorde cercanas al centro."""
        if not chord_tones:
            return []

        voices = sorted(chord_tones, key=lambda p: abs(int(p) - int(center)))
        voices = voices[: max(1, self.max_chord_voices)]
        voices.sort()

        return [int(v) for v in voices]

    # --------------------------------------------------------
    # Velocity / dinámica
    # --------------------------------------------------------

    def _base_velocity(self, slot_idx: int) -> int:
        """Velocity base según posición rítmica."""
        if int(slot_idx) == 0:
            return self.base_velocity_downbeat

        if self._is_downbeat(slot_idx):
            return self.base_velocity_beat

        return self.base_velocity_offbeat

    def _velocity_for_slot(
        self,
        segment: MusicSegment,
        bar: Bar,
        slot_idx: int,
    ) -> int:
        """
        Calcula velocity final.

        Combina:
          - acento musical,
          - velocity_factor EEG,
          - envolvente musical del Bar.
        """
        base = float(self._base_velocity(slot_idx))

        eeg_vel = _clamp(_safe_float(segment.velocity_factor, 0.5), 0.0, 1.0)

        amp = 0.5
        if bar.amplitude_slots is not None and len(bar.amplitude_slots) > slot_idx:
            amp = _clamp(_safe_float(bar.amplitude_slots[slot_idx], 0.5), 0.0, 1.0)

        # Factor final controlado, sin saltos extremos.
        factor = 0.65 + 0.45 * eeg_vel
        factor *= 0.80 + 0.30 * amp

        velocity = int(round(base * factor))
        return _clamp_int(velocity, self.min_velocity, self.max_velocity)

    # --------------------------------------------------------
    # Tiempo / duración
    # --------------------------------------------------------

    def _slot_times(
        self,
        bar: Bar,
        slot_idx: int,
        next_on_idx: Optional[int],
    ) -> tuple[float, float]:
        """
        Calcula t_start/t_end de una nota.

        La nota dura hasta:
          - el siguiente note-on;
          - o el final del compás.
        """
        bar_duration = max(0.001, float(bar.t_end - bar.t_start))
        slot_duration = bar_duration / self.n_slots

        t_start = float(bar.t_start) + int(slot_idx) * slot_duration

        if next_on_idx is None:
            t_end = float(bar.t_end)
        else:
            t_end = float(bar.t_start) + int(next_on_idx) * slot_duration

        # Seguridad para evitar notas de duración cero.
        if t_end <= t_start:
            t_end = t_start + max(0.02, slot_duration)

        return t_start, t_end

    def _next_on_slot(self, note_positions: Sequence[int], slot_idx: int) -> Optional[int]:
        """Busca el siguiente slot activo."""
        for j in range(int(slot_idx) + 1, len(note_positions)):
            if int(note_positions[j]) == 1:
                return int(j)

        return None

    # --------------------------------------------------------
    # API principal
    # --------------------------------------------------------

    def generate_notes_for_bar(
        self,
        segment: MusicSegment,
        bar: Bar,
        channel: Optional[int] = None,
        program: Optional[int] = None,
    ) -> List[NoteEvent]:
        """
        Genera notas para un único compás live.

        Este es el método principal para tiempo real.
        """
        if not segment.valid:
            return []

        ch = self.default_channel if channel is None else int(channel)
        prog = self.default_program if program is None else int(program)

        note_positions = list(bar.note_positions)
        if len(note_positions) != self.n_slots:
            raise ValueError(
                f"Bar con {len(note_positions)} slots, "
                f"pero NoteGenerator espera {self.n_slots}."
            )

        center = self._register_center(segment)
        scale_pitches = self._scale_pitches_around(segment.scale, center)
        chord_tones, passing_tones = self._split_chord_and_passing(
            scale_pitches=scale_pitches,
            chord_pitches=bar.chord_pitches,
        )

        notes: list[NoteEvent] = []

        for slot_idx, is_on in enumerate(note_positions):
            if int(is_on) != 1:
                continue

            next_on = self._next_on_slot(note_positions, slot_idx)
            t_start, t_end = self._slot_times(bar, slot_idx, next_on)
            velocity = self._velocity_for_slot(segment, bar, slot_idx)

            # Primer slot: opcionalmente generar acorde completo.
            if slot_idx == 0 and self.chord_on_first_slot:
                voices = self._chord_voices(chord_tones, center)

                for voice_idx, pitch in enumerate(voices):
                    # Atenuar voces superiores un poco.
                    v = int(round(velocity * (1.0 - 0.08 * voice_idx)))
                    v = _clamp_int(v, self.min_velocity, self.max_velocity)

                    notes.append(
                        NoteEvent(
                            t_start=t_start,
                            t_end=t_end,
                            pitch_midi=int(pitch),
                            velocity=v,
                            channel=ch,
                            program=prog,
                        )
                    )

                if voices:
                    self._prev_pitch = int(voices[-1])
                    continue

            pitch = self._choose_pitch(
                segment=segment,
                slot_idx=slot_idx,
                chord_tones=chord_tones,
                passing_tones=passing_tones,
                center=center,
            )

            self._prev_pitch = pitch

            notes.append(
                NoteEvent(
                    t_start=t_start,
                    t_end=t_end,
                    pitch_midi=int(pitch),
                    velocity=int(velocity),
                    channel=ch,
                    program=prog,
                )
            )

        notes.sort(key=lambda n: (n.t_start, n.pitch_midi))
        return notes

    def generate_notes_for_segment(
        self,
        segment: MusicSegment,
        bars: Sequence[Bar],
        channel: Optional[int] = None,
        program: Optional[int] = None,
    ) -> List[NoteEvent]:
        """
        Compatibilidad con el flujo anterior.

        En directo normalmente se usará generate_notes_for_bar().
        """
        all_notes: list[NoteEvent] = []

        for bar in bars:
            all_notes.extend(
                self.generate_notes_for_bar(
                    segment=segment,
                    bar=bar,
                    channel=channel,
                    program=program,
                )
            )

        all_notes.sort(key=lambda n: (n.t_start, n.pitch_midi))
        return all_notes


# ------------------------------------------------------------
# Prueba rápida local
# ------------------------------------------------------------

if __name__ == "__main__":
    import numpy as np

    from music_segment import (
        LiveSegment,
        ScaleConfig,
        MusicSegment,
        RhythmCadence,
        MAJOR_INTERVALS,
    )
    from music_bar import Bar

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

    positions = np.zeros(16, dtype=int)
    positions[[0, 3, 5, 8, 12]] = 1

    bar = Bar(
        index=0,
        t_start=0.0,
        t_end=2.0,
        chord_root_midi=60,
        chord_pitches=[60, 64, 67],
        note_positions=positions,
        stability=0.5,
        amplitude_slots=np.ones(16) * 0.7,
    )

    gen = NoteGenerator()
    notes = gen.generate_notes_for_bar(music_seg, bar)

    for n in notes:
        print(n)
