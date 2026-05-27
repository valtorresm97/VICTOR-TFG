from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


def _call_midi_bytes(n: int, b0: int, b1: int, b2: int) -> bool:
    from arduino.app_utils import Bridge  # type: ignore

    result = Bridge.call("midi_bytes", int(n), int(b0), int(b1), int(b2))
    if result is None:
        return True
    if isinstance(result, bool):
        return result
    if isinstance(result, tuple) and result and isinstance(result[0], bool):
        return bool(result[0])
    return True


def _parse_notes(value: str) -> list[int]:
    notes: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if part:
            notes.append(_clamp(int(part), 0, 127))
    return notes or [60, 64, 67, 72]


def _print_bytes(label: str, data: list[int]) -> None:
    hex_bytes = " ".join(f"0x{x:02X}" for x in data)
    dec_bytes = " ".join(str(x) for x in data)
    print(f"{label}: {hex_bytes}  [{dec_bytes}]")


def send_test_note(
    channel: int,
    notes: list[int],
    velocity: int,
    duration_sec: float,
    program: int | None,
    repeat: int,
    gap_sec: float,
    dry_run: bool,
) -> int:
    channel_human = _clamp(channel, 1, 16)
    channel_zero = channel_human - 1
    note_values = [_clamp(note, 0, 127) for note in notes][:32] or [60, 64, 67, 72]
    velocity_value = _clamp(velocity, 1, 127)
    duration = max(0.03, min(5.0, float(duration_sec)))
    gap = max(0.0, min(5.0, float(gap_sec)))
    repeats = _clamp(repeat, 1, 32)

    program_change = None
    if program is not None:
        program_change = [0xC0 | channel_zero, _clamp(program, 0, 127)]

    print(f"MIDI test sequence: channel={channel_human} internal={channel_zero}")
    print(f"notes={note_values} duration={duration}s gap={gap}s repeat={repeats}")
    if program_change is not None:
        _print_bytes("program_change", program_change)
    for note_value in note_values:
        _print_bytes("note_on", [0x90 | channel_zero, note_value, velocity_value])
        _print_bytes("note_off", [0x80 | channel_zero, note_value, 0])

    if dry_run:
        return 0

    failed = 0
    for idx in range(repeats):
        if program_change is not None and idx == 0:
            ok = _call_midi_bytes(2, program_change[0], program_change[1], 0)
            print(f"program_change sent={ok}")
            failed += 0 if ok else 1

        for note_value in note_values:
            note_on = [0x90 | channel_zero, note_value, velocity_value]
            note_off = [0x80 | channel_zero, note_value, 0]

            ok = _call_midi_bytes(3, note_on[0], note_on[1], note_on[2])
            print(f"note_on note={note_value} repeat={idx + 1}/{repeats} sent={ok}")
            failed += 0 if ok else 1

            time.sleep(duration)

            ok = _call_midi_bytes(3, note_off[0], note_off[1], note_off[2])
            print(f"note_off note={note_value} repeat={idx + 1}/{repeats} sent={ok}")
            failed += 0 if ok else 1

            if gap > 0.0:
                time.sleep(gap)

        if idx + 1 < repeats:
            time.sleep(gap)

    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send a fixed MIDI test sequence through Bridge.call('midi_bytes')."
    )
    parser.add_argument("--channel", type=int, default=10, help="MIDI RX channel 1..16.")
    parser.add_argument(
        "--notes",
        default="60,64,67,72",
        help="Comma-separated MIDI notes. Default: C4,E4,G4,C5.",
    )
    parser.add_argument("--velocity", type=int, default=100, help="MIDI velocity 1..127.")
    parser.add_argument("--duration", type=float, default=0.08, help="Each note duration seconds.")
    parser.add_argument(
        "--program",
        type=int,
        default=9,
        help="Program byte 0..127 before first note. Default 9 = visible program 10 on many synths.",
    )
    parser.add_argument("--no-program", action="store_true", help="Do not send program_change.")
    parser.add_argument("--repeat", type=int, default=1, help="Number of notes to send.")
    parser.add_argument("--gap", type=float, default=0.02, help="Gap between repeated notes.")
    parser.add_argument("--dry-run", action="store_true", help="Print bytes without Bridge.call.")
    args = parser.parse_args()

    return send_test_note(
        channel=args.channel,
        notes=_parse_notes(args.notes),
        velocity=args.velocity,
        duration_sec=args.duration,
        program=None if args.no_program else args.program,
        repeat=args.repeat,
        gap_sec=args.gap,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
