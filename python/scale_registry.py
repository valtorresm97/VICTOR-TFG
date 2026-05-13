"""Registro mínimo de escalas para la sonificación live."""

from __future__ import annotations

from music_segment import MAJOR_INTERVALS, NAT_MINOR_INTERVALS, ScaleConfig
from music_utils import note_name_to_midi

_SCALE_INTERVALS = {
    ("diatonic", "major (ionian)"): MAJOR_INTERVALS,
    ("diatonic", "natural minor (aeolian)"): NAT_MINOR_INTERVALS,
    ("diatonic", "minor (aeolian)"): NAT_MINOR_INTERVALS,
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
