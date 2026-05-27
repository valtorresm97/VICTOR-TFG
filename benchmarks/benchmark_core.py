from __future__ import annotations

import csv
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = PROJECT_ROOT / "python"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def ensure_python_path() -> None:
    """Permite importar los modulos actuales de python/ sin mover archivos."""
    path = str(PYTHON_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


def install_arduino_mocks() -> None:
    """Instala mocks minimos para importar transportes que dependen de arduino.*.

    No llama a hardware real. Solo permite medir codigo offline.
    """
    import types

    if "arduino" not in sys.modules:
        arduino = types.ModuleType("arduino")
        arduino.__path__ = []  # type: ignore[attr-defined]
        sys.modules["arduino"] = arduino

    if "arduino.app_utils" not in sys.modules:
        app_utils = types.ModuleType("arduino.app_utils")

        class _BridgeMock:
            calls: list[tuple[str, tuple[Any, ...]]] = []
            providers: dict[str, Callable[..., Any]] = {}

            @classmethod
            def call(cls, method: str, *args: Any) -> bool:
                cls.calls.append((str(method), args))
                return True

            @classmethod
            def provide(cls, name: str, func: Callable[..., Any]) -> None:
                cls.providers[str(name)] = func

        class _AppMock:
            @staticmethod
            def run(*args: Any, **kwargs: Any) -> None:
                return None

        app_utils.Bridge = _BridgeMock
        app_utils.App = _AppMock
        sys.modules["arduino.app_utils"] = app_utils

    if "arduino.app_bricks" not in sys.modules:
        app_bricks = types.ModuleType("arduino.app_bricks")
        app_bricks.__path__ = []  # type: ignore[attr-defined]
        sys.modules["arduino.app_bricks"] = app_bricks

    if "arduino.app_bricks.web_ui" not in sys.modules:
        web_ui = types.ModuleType("arduino.app_bricks.web_ui")

        class _WebUIMock:
            url = "mock://web-ui"

            def __init__(self, *args: Any, **kwargs: Any) -> None:
                self.routes: list[tuple[str, str, Callable[..., Any]]] = []

            def expose_api(self, method: str, path: str, handler: Callable[..., Any]) -> None:
                self.routes.append((method, path, handler))

            def on_connect(self, handler: Callable[..., Any]) -> None:
                self._on_connect = handler

            def on_disconnect(self, handler: Callable[..., Any]) -> None:
                self._on_disconnect = handler

            def send_message(self, *args: Any, **kwargs: Any) -> None:
                return None

            def start(self) -> None:
                return None

        web_ui.WebUI = _WebUIMock
        sys.modules["arduino.app_bricks.web_ui"] = web_ui


def json_safe(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    try:
        if hasattr(obj, "item"):
            return json_safe(obj.item())
    except Exception:
        pass
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    try:
        if hasattr(obj, "tolist"):
            return json_safe(obj.tolist())
    except Exception:
        pass
    try:
        return str(obj)
    except Exception:
        return None


def atomic_write_json(path: Path, payload: Any, *, indent: int | None = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        json.dump(json_safe(payload), tmp, ensure_ascii=False, indent=indent)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def git_value(args: list[str]) -> str | None:
    try:
        out = subprocess.check_output(["git", *args], cwd=str(PROJECT_ROOT), text=True, stderr=subprocess.DEVNULL)
        return out.strip() or None
    except Exception:
        return None


def environment_metadata() -> dict[str, Any]:
    return {
        "git_branch": git_value(["branch", "--show-current"]),
        "git_commit": git_value(["rev-parse", "HEAD"]),
        "python_version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "timestamp_unix": time.time(),
    }


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    rank = (len(xs) - 1) * (float(p) / 100.0)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return float(xs[lo])
    frac = rank - lo
    return float(xs[lo] * (1.0 - frac) + xs[hi] * frac)


def summarize_durations_ns(durations_ns: list[int]) -> dict[str, float]:
    durations_ms = [float(v) / 1_000_000.0 for v in durations_ns]
    if not durations_ms:
        return {
            "duration_ms_min": 0.0,
            "duration_ms_median": 0.0,
            "duration_ms_mean": 0.0,
            "duration_ms_p95": 0.0,
            "duration_ms_p99": 0.0,
            "duration_ms_max": 0.0,
        }
    return {
        "duration_ms_min": float(min(durations_ms)),
        "duration_ms_median": float(statistics.median(durations_ms)),
        "duration_ms_mean": float(statistics.fmean(durations_ms)),
        "duration_ms_p95": percentile(durations_ms, 95),
        "duration_ms_p99": percentile(durations_ms, 99),
        "duration_ms_max": float(max(durations_ms)),
    }


def time_function(
    func: Callable[[], Any],
    *,
    iterations: int = 100,
    warmup_iterations: int = 10,
) -> tuple[dict[str, float], Any]:
    last_result = None
    for _ in range(max(0, int(warmup_iterations))):
        last_result = func()

    durations: list[int] = []
    for _ in range(max(1, int(iterations))):
        t0 = time.perf_counter_ns()
        last_result = func()
        durations.append(time.perf_counter_ns() - t0)

    return summarize_durations_ns(durations), last_result


def make_record(
    *,
    benchmark_id: str,
    module: str,
    function: str,
    scenario: str,
    iterations: int,
    warmup_iterations: int,
    input_shape: str = "",
    fs_hz: int | None = None,
    num_channels: int | None = None,
    window_sec: float | None = None,
    summary: dict[str, float],
    notes: str = "",
) -> dict[str, Any]:
    rec = {
        "benchmark_id": benchmark_id,
        **environment_metadata(),
        "module": module,
        "function": function,
        "scenario": scenario,
        "iterations": int(iterations),
        "warmup_iterations": int(warmup_iterations),
        "input_shape": input_shape,
        "fs_hz": fs_hz,
        "num_channels": num_channels,
        "window_sec": window_sec,
        **summary,
        "notes": notes,
    }
    return json_safe(rec)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(key)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json_safe(row.get(k)) for k in keys})


def write_markdown_report(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Benchmark report", ""]
    meta = environment_metadata()
    lines.append(f"- Branch: `{meta.get('git_branch')}`")
    lines.append(f"- Commit: `{meta.get('git_commit')}`")
    lines.append(f"- Python: `{meta.get('python_version')}`")
    lines.append(f"- Platform: `{meta.get('platform')}`")
    lines.append("")
    lines.append("| benchmark_id | function | scenario | median ms | p95 ms | max ms | notes |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | --- |")
    for row in rows:
        lines.append(
            "| {benchmark_id} | {function} | {scenario} | {med:.4f} | {p95:.4f} | {mx:.4f} | {notes} |".format(
                benchmark_id=row.get("benchmark_id", ""),
                function=row.get("function", ""),
                scenario=row.get("scenario", ""),
                med=float(row.get("duration_ms_median") or 0.0),
                p95=float(row.get("duration_ms_p95") or 0.0),
                mx=float(row.get("duration_ms_max") or 0.0),
                notes=str(row.get("notes", "")).replace("|", "/"),
            )
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
