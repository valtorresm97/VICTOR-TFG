from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _FakeBridge:
    call_result = True
    calls: list[tuple] = []

    @classmethod
    def call(cls, *args):
        cls.calls.append(args)
        return cls.call_result


_arduino = types.ModuleType("arduino")
_app_utils = types.ModuleType("arduino.app_utils")
_app_utils.Bridge = _FakeBridge
_arduino.app_utils = _app_utils
sys.modules.setdefault("arduino", _arduino)
sys.modules.setdefault("arduino.app_utils", _app_utils)

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
from midi_byte_transport import MidiByteTransport  # noqa: E402


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


def test_transport_validates_bridge_result() -> None:
    _FakeBridge.calls = []
    _FakeBridge.call_result = True
    transport = MidiByteTransport(enabled=True, log_first_events=0)

    require(
        transport.send_event(_event(NOTE_ON, 9, 60, 100)),
        "transport should accept Bridge.call True",
    )
    require(transport.sent_events_total == 1, "sent counter mismatch after True")
    require(transport.failed_events_total == 0, "failed counter mismatch after True")
    require(
        _FakeBridge.calls[-1] == ("midi_bytes", 3, 0x99, 60, 100),
        "Bridge.call payload mismatch for channel 10 note_on",
    )

    _FakeBridge.call_result = False
    require(
        not transport.send_event(_event(NOTE_OFF, 9, 60, 0)),
        "transport should reject Bridge.call False",
    )
    require(transport.sent_events_total == 1, "False result must not count as sent")
    require(transport.failed_events_total == 1, "False result must count as failed")
    require(
        transport.bridge_rejected_events_total == 1,
        "bridge rejected counter mismatch",
    )

    _FakeBridge.call_result = None
    require(
        transport.send_event(_event(PROGRAM_CHANGE, 9, 0, 0)),
        "transport should keep compatibility with Bridge.call None",
    )
    require(transport.sent_events_total == 2, "None result compatibility mismatch")


def main() -> None:
    test_voice_message_bytes()
    test_program_change_is_two_bytes()
    test_midi_values_are_clamped()
    test_safety_events()
    test_transport_validates_bridge_result()
    print("MIDI byte contract OK")


if __name__ == "__main__":
    main()
