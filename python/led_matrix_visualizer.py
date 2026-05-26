from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import median
from typing import Any, Iterable

from runtime_config import (
    EEG_LED_MATRIX_BRIDGE_METHOD_ENV,
    EEG_LED_MATRIX_BRIGHTNESS_ENV,
    EEG_LED_MATRIX_CLIP_MODE_ENV,
    EEG_LED_MATRIX_DYNAMIC_CENTER_ENV,
    EEG_LED_MATRIX_ENABLED_ENV,
    EEG_LED_MATRIX_HEIGHT_ENV,
    EEG_LED_MATRIX_MAX_POINTS_ENV,
    EEG_LED_MATRIX_NOTE_MODE_ENV,
    EEG_LED_MATRIX_PITCH_CENTER_ENV,
    EEG_LED_MATRIX_REFRESH_HZ_ENV,
    EEG_LED_MATRIX_VISIBLE_PITCH_SPAN_ENV,
    EEG_LED_MATRIX_WIDTH_ENV,
    LED_MATRIX_DEFAULT_BRIDGE_METHOD,
    LED_MATRIX_DEFAULT_BRIGHTNESS,
    LED_MATRIX_DEFAULT_CLIP_MODE,
    LED_MATRIX_DEFAULT_HEIGHT,
    LED_MATRIX_DEFAULT_MAX_POINTS,
    LED_MATRIX_DEFAULT_NOTE_MODE,
    LED_MATRIX_DEFAULT_REFRESH_HZ,
    LED_MATRIX_DEFAULT_VISIBLE_PITCH_SPAN,
    LED_MATRIX_DEFAULT_WIDTH,
    env_bool,
    env_choice,
    env_float,
    env_int,
    env_str,
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return float(default)
    return out if math.isfinite(out) else float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(float(lo), min(float(hi), float(value)))


@dataclass(frozen=True)
class LedMatrixConfig:
    """
    Configuracion del piano scroll LED.

    La matriz fisica queda desactivada por defecto. Cuando se activa, el frame
    se calcula en Python y se envia al MCU como bytes row-major 13x8.
    """

    enabled: bool = False
    width: int = LED_MATRIX_DEFAULT_WIDTH
    height: int = LED_MATRIX_DEFAULT_HEIGHT
    pitch_center: int = 67
    dynamic_pitch_center: bool = False
    visible_pitch_span: int = LED_MATRIX_DEFAULT_VISIBLE_PITCH_SPAN
    refresh_rate_hz: float = LED_MATRIX_DEFAULT_REFRESH_HZ
    brightness: int = LED_MATRIX_DEFAULT_BRIGHTNESS
    max_points: int = LED_MATRIX_DEFAULT_MAX_POINTS
    clip_mode: str = LED_MATRIX_DEFAULT_CLIP_MODE
    note_mode: str = LED_MATRIX_DEFAULT_NOTE_MODE
    bridge_method: str = LED_MATRIX_DEFAULT_BRIDGE_METHOD

    @classmethod
    def from_env(cls, default_pitch_center: int = 67) -> "LedMatrixConfig":
        return cls(
            enabled=env_bool(EEG_LED_MATRIX_ENABLED_ENV, False),
            width=env_int(EEG_LED_MATRIX_WIDTH_ENV, LED_MATRIX_DEFAULT_WIDTH, lo=1, hi=64),
            height=env_int(EEG_LED_MATRIX_HEIGHT_ENV, LED_MATRIX_DEFAULT_HEIGHT, lo=1, hi=32),
            pitch_center=env_int(
                EEG_LED_MATRIX_PITCH_CENTER_ENV,
                int(default_pitch_center),
                lo=0,
                hi=127,
            ),
            dynamic_pitch_center=env_bool(EEG_LED_MATRIX_DYNAMIC_CENTER_ENV, False),
            visible_pitch_span=env_int(
                EEG_LED_MATRIX_VISIBLE_PITCH_SPAN_ENV,
                LED_MATRIX_DEFAULT_VISIBLE_PITCH_SPAN,
                lo=1,
                hi=64,
            ),
            refresh_rate_hz=env_float(
                EEG_LED_MATRIX_REFRESH_HZ_ENV,
                LED_MATRIX_DEFAULT_REFRESH_HZ,
                lo=1.0,
                hi=30.0,
            ),
            brightness=env_int(EEG_LED_MATRIX_BRIGHTNESS_ENV, LED_MATRIX_DEFAULT_BRIGHTNESS, lo=1, hi=7),
            max_points=env_int(EEG_LED_MATRIX_MAX_POINTS_ENV, LED_MATRIX_DEFAULT_MAX_POINTS, lo=1, hi=64),
            clip_mode=env_choice(
                EEG_LED_MATRIX_CLIP_MODE_ENV,
                LED_MATRIX_DEFAULT_CLIP_MODE,
                {"ignore", "saturate"},
            ),
            note_mode=env_choice(
                EEG_LED_MATRIX_NOTE_MODE_ENV,
                LED_MATRIX_DEFAULT_NOTE_MODE,
                {"point", "duration"},
            ),
            bridge_method=env_str(EEG_LED_MATRIX_BRIDGE_METHOD_ENV, LED_MATRIX_DEFAULT_BRIDGE_METHOD),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "width": self.width,
            "height": self.height,
            "pitch_center": self.pitch_center,
            "dynamic_pitch_center": self.dynamic_pitch_center,
            "visible_pitch_span": self.visible_pitch_span,
            "refresh_rate_hz": self.refresh_rate_hz,
            "brightness": self.brightness,
            "max_points": self.max_points,
            "clip_mode": self.clip_mode,
            "note_mode": self.note_mode,
            "bridge_method": self.bridge_method,
        }


def _pitch_center(notes: list[dict[str, Any]], config: LedMatrixConfig) -> int:
    if not config.dynamic_pitch_center:
        return int(config.pitch_center)

    pitches = [
        _safe_int(note.get("pitch_midi"), -1)
        for note in notes
        if 0 <= _safe_int(note.get("pitch_midi"), -1) <= 127
    ]
    if not pitches:
        return int(config.pitch_center)
    return int(round(median(pitches)))


def _x_for_note(note: dict[str, Any], now: float, window_sec: float, width: int) -> int | None:
    abs_start = _safe_float(note.get("abs_start"), math.nan)
    if not math.isfinite(abs_start):
        return None

    start_window = float(now) - float(window_sec)
    rel = (abs_start - start_window) / float(window_sec)
    if rel < 0.0 or rel > 1.0:
        return None
    return int(round(rel * max(0, int(width) - 1)))


def _duration_x_end(
    note: dict[str, Any],
    now: float,
    window_sec: float,
    width: int,
    x_start: int,
) -> int:
    abs_end = _safe_float(note.get("abs_end"), _safe_float(note.get("abs_start"), now) + 0.04)
    start_window = float(now) - float(window_sec)
    rel = (abs_end - start_window) / float(window_sec)
    x_end = int(round(_clamp(rel, 0.0, 1.0) * max(0, int(width) - 1)))
    return max(int(x_start), x_end)


def _y_for_pitch(pitch: int, center: int, config: LedMatrixConfig) -> int | None:
    if config.height <= 1:
        return 0

    span = max(1, int(config.visible_pitch_span))
    scale = (config.height - 1) / float(max(1, span - 1))
    y = (config.height - 1) / 2.0 - (int(pitch) - int(center)) * scale

    if config.clip_mode == "saturate":
        return int(round(_clamp(y, 0, config.height - 1)))

    if y < 0 or y > (config.height - 1):
        return None
    return int(round(y))


def _velocity_to_intensity(velocity: int, brightness: int) -> int:
    vel = int(_clamp(int(velocity), 0, 127))
    return int(round((vel / 127.0) * int(brightness)))


def build_led_matrix_frame(
    recent_notes: Iterable[dict[str, Any]],
    *,
    now: float,
    window_sec: float,
    config: LedMatrixConfig,
) -> dict[str, Any]:
    """
    Convierte las mismas recent_notes del piano roll web en puntos LED.

    Eje X: usa el mismo reloj absoluto monotonic del piano roll.
    Eje Y: pitch MIDI centrado en pitch_center o mediana reciente configurable.
    """
    notes = [n for n in recent_notes if isinstance(n, dict)]
    notes.sort(key=lambda n: (_safe_float(n.get("abs_start"), 0.0), _safe_int(n.get("pitch_midi"), 0)))

    center = _pitch_center(notes, config)
    points: list[dict[str, int]] = []
    occupied: set[tuple[int, int]] = set()

    for note in notes:
        pitch = _safe_int(note.get("pitch_midi"), -1)
        if pitch < 0 or pitch > 127:
            continue

        x = _x_for_note(note, now=now, window_sec=window_sec, width=config.width)
        if x is None:
            continue

        y = _y_for_pitch(pitch, center=center, config=config)
        if y is None:
            continue

        velocity = _safe_int(note.get("velocity"), 0)
        intensity = max(1, _velocity_to_intensity(velocity, config.brightness))

        x_end = x
        if config.note_mode == "duration":
            x_end = _duration_x_end(note, now=now, window_sec=window_sec, width=config.width, x_start=x)

        for px in range(x, min(x_end, config.width - 1) + 1):
            key = (px, y)
            if key in occupied:
                continue
            occupied.add(key)
            points.append(
                {
                    "x": int(px),
                    "y": int(y),
                    "pitch_midi": int(pitch),
                    "velocity": int(_clamp(velocity, 0, 127)),
                    "intensity": int(intensity),
                }
            )
            if len(points) >= config.max_points:
                break

        if len(points) >= config.max_points:
            break

    rows = [[0 for _ in range(config.width)] for _ in range(config.height)]
    for p in points:
        rows[p["y"]][p["x"]] = max(rows[p["y"]][p["x"]], int(p["intensity"]))

    return {
        "config": config.to_dict(),
        "pitch_center_used": int(center),
        "window_sec": float(window_sec),
        "point_count": len(points),
        "points": points,
        "rows": rows,
    }
