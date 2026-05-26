from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from midi_live import (  # noqa: E402
    CONTROL_CHANGE,
    NOTE_OFF,
    NOTE_ON,
    PROGRAM_CHANGE,
    MidiLiveEvent,
    all_notes_off_events,
    event_to_midi_bytes,
    panic_events,
)


def _event(event_type: str, channel: int, data1: int, data2: int = 0) -> MidiLiveEvent:
    return MidiLiveEvent(
        sort_index=0.0,
        due_time=0.0,
        type=event_type,
        channel=channel,
        data1=data1,
        data2=data2,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_voice_message_bytes() -> None:
    require(
        event_to_midi_bytes(_event(NOTE_ON, 0, 60, 100)) == bytes([0x90, 60, 100]),
        "note_on channel 1 bytes mismatch",
    )
    require(
        event_to_midi_bytes(_event(NOTE_OFF, 15, 127, 0)) == bytes([0x8F, 127, 0]),
        "note_off channel 16 bytes mismatch",
    )
    require(
        event_to_midi_bytes(_event(CONTROL_CHANGE, 2, 123, 0)) == bytes([0xB2, 123, 0]),
        "control_change bytes mismatch",
    )


def test_program_change_is_two_bytes() -> None:
    data = event_to_midi_bytes(_event(PROGRAM_CHANGE, 4, 10, 99))
    require(data == bytes([0xC4, 10]), "program_change bytes mismatch")
    require(len(data) == 2, "program_change must be 2 bytes")


def test_midi_values_are_clamped() -> None:
    require(
        event_to_midi_bytes(_event(NOTE_ON, 99, 200, -5)) == bytes([0x9F, 127, 0]),
        "MIDI channel/data clamp mismatch",
    )


def test_safety_events() -> None:
    all_off = all_notes_off_events(due_time=0.0)
    panic = panic_events(due_time=0.0)

    require(len(all_off) == 16, "all_notes_off must emit one CC per channel")
    require(len(panic) == 32, "panic must emit CC 120 and CC 123 per channel")
    require(
        event_to_midi_bytes(all_off[0]) == bytes([0xB0, 123, 0]),
        "all_notes_off first channel bytes mismatch",
    )
    require(
        event_to_midi_bytes(panic[0]) == bytes([0xB0, 120, 0]),
        "panic all_sound_off bytes mismatch",
    )
    require(
        event_to_midi_bytes(panic[1]) == bytes([0xB0, 123, 0]),
        "panic all_notes_off bytes mismatch",
    )


def main() -> None:
    test_voice_message_bytes()
    test_program_change_is_two_bytes()
    test_midi_values_are_clamped()
    test_safety_events()
    print("MIDI byte contract OK")


if __name__ == "__main__":
    main()
