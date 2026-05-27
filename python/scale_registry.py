"""Registro mínimo de escalas para la sonificación live."""

from __future__ import annotations

from music_segment import MAJOR_INTERVALS, NAT_MINOR_INTERVALS, ScaleConfig
from music_utils import note_name_to_midi

_SCALE_INTERVALS = {
    ("diatonic", "major (ionian)"): MAJOR_INTERVALS,
    ("diatonic", "natural minor (aeolian)"): NAT_MINOR_INTERVALS,
    ("diatonic", "minor (aeolian)"): NAT_MINOR_INTERVALS,
    ("pentatonic", "minor blues"): [0, 3, 5, 6, 7, 10],
    ("heptatonic", "spanish phrygian"): [0, 1, 4, 5, 7, 8, 10],
    ("heptatonic", "arabic double harmonic"): [0, 1, 4, 5, 7, 8, 11],
    ("heptatonic", "harmonic minor"): [0, 2, 3, 5, 7, 8, 11],
    ("heptatonic", "phrygian dominant"): [0, 1, 4, 5, 7, 8, 10],
    ("pentatonic", "minor pentatonic"): [0, 3, 5, 7, 10],
    ("pentatonic", "major pentatonic"): [0, 2, 4, 7, 9],
}


def build_scale_config(
    family: str,
    scale_name: str,
    root_note: str,
) -> ScaleConfig:
    """
    Construye ScaleConfig desde nombres de configuración/UI.

    Mantiene la tonalidad bajo control del usuario/UI; el EEG no cambia
    root_note, familia ni modo, solo modula parámetros live posteriores.
    """
    key = (str(family).strip().lower(), str(scale_name).strip().lower())
    intervals = _SCALE_INTERVALS.get(key)
    if intervals is None:
        raise ValueError(f"Escala no soportada: {family!r} / {scale_name!r}")

    return ScaleConfig(
        root_midi=note_name_to_midi(root_note),
        name=f"{root_note}_{scale_name}",
        intervals=list(intervals),
    )
