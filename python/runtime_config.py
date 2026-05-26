from __future__ import annotations

import math
import os
from pathlib import Path


EEG_MIDI_LIVE_ENABLED_ENV = "EEG_MIDI_LIVE_ENABLED"
EEG_RUNTIME_STATE_DIR_ENV = "EEG_RUNTIME_STATE_DIR"

EEG_LED_MATRIX_ENABLED_ENV = "EEG_LED_MATRIX_ENABLED"
EEG_LED_MATRIX_WIDTH_ENV = "EEG_LED_MATRIX_WIDTH"
EEG_LED_MATRIX_HEIGHT_ENV = "EEG_LED_MATRIX_HEIGHT"
EEG_LED_MATRIX_PITCH_CENTER_ENV = "EEG_LED_MATRIX_PITCH_CENTER"
EEG_LED_MATRIX_DYNAMIC_CENTER_ENV = "EEG_LED_MATRIX_DYNAMIC_CENTER"
EEG_LED_MATRIX_VISIBLE_PITCH_SPAN_ENV = "EEG_LED_MATRIX_VISIBLE_PITCH_SPAN"
EEG_LED_MATRIX_REFRESH_HZ_ENV = "EEG_LED_MATRIX_REFRESH_HZ"
EEG_LED_MATRIX_BRIGHTNESS_ENV = "EEG_LED_MATRIX_BRIGHTNESS"
EEG_LED_MATRIX_MAX_POINTS_ENV = "EEG_LED_MATRIX_MAX_POINTS"
EEG_LED_MATRIX_CLIP_MODE_ENV = "EEG_LED_MATRIX_CLIP_MODE"
EEG_LED_MATRIX_NOTE_MODE_ENV = "EEG_LED_MATRIX_NOTE_MODE"
EEG_LED_MATRIX_BRIDGE_METHOD_ENV = "EEG_LED_MATRIX_BRIDGE_METHOD"

LED_MATRIX_DEFAULT_WIDTH = 13
LED_MATRIX_DEFAULT_HEIGHT = 8
LED_MATRIX_DEFAULT_VISIBLE_PITCH_SPAN = 8
LED_MATRIX_DEFAULT_REFRESH_HZ = 8.0
LED_MATRIX_DEFAULT_BRIGHTNESS = 7
LED_MATRIX_DEFAULT_MAX_POINTS = 24
LED_MATRIX_DEFAULT_CLIP_MODE = "ignore"
LED_MATRIX_DEFAULT_NOTE_MODE = "point"
LED_MATRIX_DEFAULT_BRIDGE_METHOD = "led_matrix_row"
RUNTIME_STATE_DEFAULT_DIR = "state"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return bool(default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, lo: int | None = None, hi: int | None = None) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except Exception:
        value = int(default)

    if lo is not None:
        value = max(int(lo), value)
    if hi is not None:
        value = min(int(hi), value)
    return value


def env_float(name: str, default: float, lo: float | None = None, hi: float | None = None) -> float:
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


def env_choice(name: str, default: str, choices: set[str]) -> str:
    value = os.environ.get(name, default).strip().lower()
    return value if value in choices else default


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def runtime_state_dir(project_root: str | Path) -> Path:
    value = os.environ.get(EEG_RUNTIME_STATE_DIR_ENV, "").strip()
    if value:
        path = Path(value).expanduser()
        return path if path.is_absolute() else Path(project_root) / path
    return Path(project_root) / RUNTIME_STATE_DEFAULT_DIR
