from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from led_matrix_visualizer import LedMatrixConfig, build_led_matrix_frame


def _notes():
    return [
        {
            "abs_start": 100.0,
            "abs_end": 100.4,
            "pitch_midi": 60,
            "velocity": 100,
            "channel": 0,
            "program": 0,
        },
        {
            "abs_start": 102.0,
            "abs_end": 102.5,
            "pitch_midi": 64,
            "velocity": 80,
            "channel": 0,
            "program": 0,
        },
        {
            "abs_start": 104.0,
            "abs_end": 104.2,
            "pitch_midi": 72,
            "velocity": 120,
            "channel": 0,
            "program": 0,
        },
    ]


def test_empty_frame_is_valid():
    cfg = LedMatrixConfig(width=13, height=8, pitch_center=64, brightness=7)
    frame = build_led_matrix_frame([], now=105.0, window_sec=10.0, config=cfg)
    assert frame["point_count"] == 0
    assert len(frame["rows"]) == 8
    assert all(len(row) == 13 for row in frame["rows"])


def test_pitch_center_and_clipping_ignore_out_of_range():
    cfg = LedMatrixConfig(width=13, height=8, pitch_center=64, visible_pitch_span=8, brightness=7)
    frame = build_led_matrix_frame(_notes(), now=105.0, window_sec=10.0, config=cfg)
    assert frame["pitch_center_used"] == 64
    assert frame["point_count"] == 1
    pitches = {p["pitch_midi"] for p in frame["points"]}
    assert pitches == {64}


def test_x_moves_left_to_right_with_time():
    cfg = LedMatrixConfig(width=13, height=8, pitch_center=64, visible_pitch_span=24, brightness=7)
    frame = build_led_matrix_frame(_notes(), now=105.0, window_sec=10.0, config=cfg)
    xs = [p["x"] for p in frame["points"]]
    assert xs == sorted(xs)
    assert xs[0] < xs[-1]


def test_saturate_mode_keeps_extreme_notes_visible():
    cfg = LedMatrixConfig(
        width=13,
        height=8,
        pitch_center=64,
        visible_pitch_span=8,
        brightness=7,
        clip_mode="saturate",
    )
    frame = build_led_matrix_frame(_notes(), now=105.0, window_sec=10.0, config=cfg)
    assert frame["point_count"] == 3
    assert all(0 <= p["y"] < 8 for p in frame["points"])


def test_velocity_controls_intensity():
    cfg = LedMatrixConfig(width=13, height=8, pitch_center=64, visible_pitch_span=24, brightness=7)
    frame = build_led_matrix_frame(_notes(), now=105.0, window_sec=10.0, config=cfg)
    by_pitch = {p["pitch_midi"]: p["intensity"] for p in frame["points"]}
    assert by_pitch[72] >= by_pitch[64]


if __name__ == "__main__":
    test_empty_frame_is_valid()
    test_pitch_center_and_clipping_ignore_out_of_range()
    test_x_moves_left_to_right_with_time()
    test_saturate_mode_keeps_extreme_notes_visible()
    test_velocity_controls_intensity()
    print("led_matrix_visualizer tests passed")
