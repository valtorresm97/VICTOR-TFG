"""Pequeñas utilidades musicales compartidas por el pipeline live."""

from __future__ import annotations

_NOTE_OFFSETS = {
    "C": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
}


def note_name_to_midi(note_name: str) -> int:
    """
    Convierte una nota tipo C4, F#3 o Bb5 a número MIDI.

    Se usa para la configuración inicial fija del backend; la UI podrá
    sustituir estos valores más adelante sin cambiar la lógica musical.
    """
    text = str(note_name).strip()
    if len(text) < 2:
        raise ValueError(f"Nombre de nota inválido: {note_name!r}")

    if len(text) >= 3 and text[1] in ("#", "b", "B"):
        name = text[:2].upper()
        octave_text = text[2:]
    else:
        name = text[:1].upper()
        octave_text = text[1:]

    if name not in _NOTE_OFFSETS:
        raise ValueError(f"Nota no soportada: {note_name!r}")

    try:
        octave = int(octave_text)
    except ValueError as exc:
        raise ValueError(f"Octava inválida en nota: {note_name!r}") from exc

    midi = (octave + 1) * 12 + _NOTE_OFFSETS[name]
    return max(0, min(127, midi))
