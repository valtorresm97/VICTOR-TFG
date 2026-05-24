from __future__ import annotations

from dataclasses import dataclass
import math
import os
from statistics import median
from typing import Any, Iterable


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return bool(default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, lo: int | None = None, hi: int | None = None) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except Exception:
        value = int(default)

    if lo is not None:
        value = max(int(lo), value)
    if hi is not None:
        value = min(int(hi), value)
    return value


def _env_float(name: str, default: float, lo: float | None = None, hi: float | None = None) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except Exception:
        value = float(default)

    if not math.isfinite(value):
        value = float(default)
    if lo is not None:
        value = max(float(lo), value)
    if hi is not None:
        value = min(float(hi), value)
    return value


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

    La matriz fisica queda desactivada por defecto. El frame se calcula de
    todos modos para snapshot, pruebas y preview UI sin tocar hardware.
    """

    enabled: bool = False
    width: int = 13
    height: int = 8
    pitch_center: int = 67
    dynamic_pitch_center: bool = False
    visible_pitch_span: int = 8
    refresh_rate_hz: float = 12.0
    brightness: int = 7
    max_points: int = 24
    clip_mode: str = "ignore"
    note_mode: str = "point"
    bridge_method: str = "led_matrix_frame"

    @classmethod
    def from_env(cls, default_pitch_center: int = 67) -> "LedMatrixConfig":
        clip_mode = os.environ.get("EEG_LED_MATRIX_CLIP_MODE", "ignore").strip().lower()
        if clip_mode not in {"ignore", "saturate"}:
            clip_mode = "ignore"

        note_mode = os.environ.get("EEG_LED_MATRIX_NOTE_MODE", "point").strip().lower()
        if note_mode not in {"point", "duration"}:
            note_mode = "point"

        return cls(
            enabled=_env_bool("EEG_LED_MATRIX_ENABLED", False),
            width=_env_int("EEG_LED_MATRIX_WIDTH", 13, lo=1, hi=64),
            height=_env_int("EEG_LED_MATRIX_HEIGHT", 8, lo=1, hi=32),
            pitch_center=_env_int(
                "EEG_LED_MATRIX_PITCH_CENTER",
                int(default_pitch_center),
                lo=0,
                hi=127,
            ),
            dynamic_pitch_center=_env_bool("EEG_LED_MATRIX_DYNAMIC_CENTER", False),
            visible_pitch_span=_env_int("EEG_LED_MATRIX_VISIBLE_PITCH_SPAN", 8, lo=1, hi=64),
            refresh_rate_hz=_env_float("EEG_LED_MATRIX_REFRESH_HZ", 12.0, lo=1.0, hi=30.0),
            brightness=_env_int("EEG_LED_MATRIX_BRIGHTNESS", 7, lo=1, hi=7),
            max_points=_env_int("EEG_LED_MATRIX_MAX_POINTS", 24, lo=1, hi=64),
            clip_mode=clip_mode,
            note_mode=note_mode,
            bridge_method=os.environ.get("EEG_LED_MATRIX_BRIDGE_METHOD", "led_matrix_frame").strip()
            or "led_matrix_frame",
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


def pack_point(x: int, y: int, intensity: int) -> int:
    """Empaqueta x, y e intensidad en un entero pequeño para Bridge."""
    return (
        (int(intensity) & 0xFF) << 16
        | (int(y) & 0xFF) << 8
        | (int(x) & 0xFF)
    )


def unpack_point(value: int) -> dict[str, int]:
    packed = int(value)
    return {
        "x": packed & 0xFF,
        "y": (packed >> 8) & 0xFF,
        "intensity": (packed >> 16) & 0xFF,
    }


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

    packed_points = [pack_point(p["x"], p["y"], p["intensity"]) for p in points]

    return {
        "config": config.to_dict(),
        "pitch_center_used": int(center),
        "window_sec": float(window_sec),
        "point_count": len(points),
        "points": points,
        "packed_points": packed_points,
        "rows": rows,
    }
