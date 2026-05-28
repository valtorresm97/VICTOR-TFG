from __future__ import annotations

import argparse
import csv
import html
import json
import math
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON_DIR = PROJECT_ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


BANDS = ["delta", "theta", "alpha", "beta", "gamma"]
SONIF_CONTROLS = [
    "alpha_drive",
    "beta_gamma_drive",
    "rms_beta_activity",
    "band_driven_density",
    "spectral_register",
    "alpha_stability",
    "rms_band_velocity",
    "band_note_probability",
]

CONDITION_NOTES = {
    "precheck_10s": {
        "title": "Precheck tecnico",
        "detail": "brief",
        "purpose": "Comprobacion breve de contacto, streaming, guardado EEG y guardado musical antes de las condiciones principales.",
    },
    "eyes_open_rest_60s": {
        "title": "Ojos abiertos en reposo",
        "detail": "full",
        "purpose": "Condicion real de reposo con ojos abiertos. Sirve para documentar sonificacion durante una tarea basal, aunque contiene artefactos transitorios.",
    },
    "eyes_closed_rest_60s": {
        "title": "Ojos cerrados en reposo",
        "detail": "full",
        "purpose": "Condicion de reposo con ojos cerrados. Permite comparar respuesta espectral y musical frente a ojos abiertos, con cautela por ruido de 50 Hz.",
    },
    "quiet_rest_60s": {
        "title": "Reposo quieto",
        "detail": "full",
        "purpose": "Condicion de reposo general. Se usa para observar estabilidad temporal, bandpowers y continuidad de la sonificacion.",
    },
    "blink_artifact_30s": {
        "title": "Artefacto por parpadeo",
        "detail": "full",
        "purpose": "Condicion de artefacto fisiologico controlado. No se usa como EEG limpio, sino para documentar respuesta del sistema ante contaminacion fisiologica.",
    },
    "eyes_open_repeat_30s": {
        "title": "Repeticion ojos abiertos",
        "detail": "full",
        "purpose": "Repeticion breve de ojos abiertos. Es la condicion candidata principal para figura combinada al ser la mejor diagnosticada por los reports.",
    },
}

SVG_STROKES = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]


def _safe_float(value: Any, default: float = math.nan) -> float:
    try:
        x = float(value)
    except Exception:
        return default
    return x if math.isfinite(x) else default


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _parse_quality_md(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line.startswith("-") or ":" not in line:
            continue
        key, value = line[1:].split(":", 1)
        out[key.strip().lower().replace(" ", "_")] = value.strip()
    return out


def _condition_from_dir(capture_dir: Path) -> str:
    name = capture_dir.name
    markers = [
        "precheck_10s",
        "eyes_open_rest_60s",
        "eyes_closed_rest_60s",
        "quiet_rest_60s",
        "blink_artifact_30s",
        "jaw_artifact_30s",
        "eyes_open_repeat_30s",
    ]
    for marker in markers:
        if name.endswith(marker):
            return marker
    parts = name.split("_", 5)
    return parts[-1] if parts else name


def _discover_session_captures(final_root: Path, subject: str, session: str, montage: str) -> list[Path]:
    pattern = f"*_{subject}_{session}_{montage}_*"
    captures = [p for p in final_root.glob(pattern) if p.is_dir()]
    return sorted(captures)


def _fig_rel(path: Path, docs_dir: Path) -> str:
    try:
        return str(path.relative_to(docs_dir))
    except Exception:
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except Exception:
            return str(path)


def _load_eeg(capture_dir: Path) -> tuple[list[float], list[float]]:
    rows = _read_csv(capture_dir / "eeg_timeseries.csv")
    t: list[float] = []
    ch1: list[float] = []
    for r in rows:
        x = _safe_float(r.get("t_capture_sec"))
        y = _safe_float(r.get("ch1_uV"))
        if math.isfinite(x) and math.isfinite(y):
            t.append(x)
            ch1.append(y)
    return t, ch1


def _downsample(x: list[float], y: list[float], max_points: int = 2500) -> tuple[list[float], list[float]]:
    if len(x) <= max_points:
        return x, y
    step = max(1, math.ceil(len(x) / max_points))
    return x[::step], y[::step]


def _finite(values: list[float]) -> list[float]:
    return [v for v in values if math.isfinite(v)]


def _range(values: list[float], default: tuple[float, float] = (0.0, 1.0), pad_ratio: float = 0.05) -> tuple[float, float]:
    vals = _finite(values)
    if not vals:
        return default
    lo = min(vals)
    hi = max(vals)
    if lo == hi:
        delta = max(1.0, abs(lo) * 0.1)
        return lo - delta, hi + delta
    pad = (hi - lo) * pad_ratio
    return lo - pad, hi + pad


def _scale_x(x: float, xmin: float, xmax: float, left: float, width: float) -> float:
    if xmax <= xmin:
        return left
    return left + (x - xmin) / (xmax - xmin) * width


def _scale_y(y: float, ymin: float, ymax: float, top: float, height: float) -> float:
    if ymax <= ymin:
        return top + height / 2
    return top + height - (y - ymin) / (ymax - ymin) * height


def _polyline(xs: list[float], ys: list[float], xmin: float, xmax: float, ymin: float, ymax: float, left: int, top: int, width: int, height: int, stroke: str) -> str:
    pts = []
    for x, y in zip(xs, ys):
        if not (math.isfinite(x) and math.isfinite(y)):
            continue
        pts.append(f"{_scale_x(x, xmin, xmax, left, width):.2f},{_scale_y(y, ymin, ymax, top, height):.2f}")
    if len(pts) < 2:
        return ""
    return f'<polyline points="{" ".join(pts)}" fill="none" stroke="{stroke}" stroke-width="1.3" />'


def _svg_header(width: int, height: int, title: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white" />',
        f'<text x="20" y="28" font-family="Arial" font-size="18" font-weight="bold">{html.escape(title)}</text>',
    ]


def _axes(left: int, top: int, width: int, height: int, xlabel: str, ylabel: str) -> list[str]:
    return [
        f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="none" stroke="#333" stroke-width="1" />',
        f'<text x="{left + width/2:.1f}" y="{top + height + 42}" text-anchor="middle" font-family="Arial" font-size="12">{html.escape(xlabel)}</text>',
        f'<text x="{left - 45}" y="{top + height/2:.1f}" text-anchor="middle" transform="rotate(-90 {left - 45},{top + height/2:.1f})" font-family="Arial" font-size="12">{html.escape(ylabel)}</text>',
    ]


def _legend(labels: list[str], left: int, top: int) -> list[str]:
    lines: list[str] = []
    x = left
    y = top
    for i, label in enumerate(labels):
        stroke = SVG_STROKES[i % len(SVG_STROKES)]
        lines.append(f'<line x1="{x}" y1="{y}" x2="{x+22}" y2="{y}" stroke="{stroke}" stroke-width="2" />')
        lines.append(f'<text x="{x+28}" y="{y+4}" font-family="Arial" font-size="11">{html.escape(label)}</text>')
        x += 155
        if x > 900:
            x = left
            y += 18
    return lines


def _write_svg_line(path: Path, title: str, series: list[tuple[str, list[float], list[float]]], ylabel: str, y_fixed: tuple[float, float] | None = None) -> None:
    width, height = 1100, 420
    left, top, plot_w, plot_h = 80, 58, 980, 285
    all_x = [v for _, xs, _ in series for v in xs]
    all_y = [v for _, _, ys in series for v in ys]
    xmin, xmax = _range(all_x, (0.0, 1.0), 0.0)
    ymin, ymax = y_fixed if y_fixed is not None else _range(all_y, (0.0, 1.0))

    lines = _svg_header(width, height, title)
    lines += _axes(left, top, plot_w, plot_h, "Tiempo de captura (s)", ylabel)
    for i, (label, xs, ys) in enumerate(series):
        dx, dy = _downsample(xs, ys)
        lines.append(_polyline(dx, dy, xmin, xmax, ymin, ymax, left, top, plot_w, plot_h, SVG_STROKES[i % len(SVG_STROKES)]))
    lines += _legend([label for label, _, _ in series], left, 380)
    lines.append(f'<text x="{left}" y="{top + plot_h + 20}" font-family="Arial" font-size="11">x=[{xmin:.2f}, {xmax:.2f}] y=[{ymin:.3g}, {ymax:.3g}]</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_eeg(capture_dir: Path, out_path: Path) -> None:
    t, ch1 = _load_eeg(capture_dir)
    _write_svg_line(out_path, "EEG CH1 temporal", [("CH1 uV", t, ch1)], "CH1 (uV)")


def plot_bandpowers(capture_dir: Path, out_path: Path) -> None:
    rows = _read_csv(capture_dir / "windowed_bandpowers.csv")
    series = []
    t = [_safe_float(r.get("window_start_sec")) for r in rows]
    for band in BANDS:
        y = [_safe_float(r.get(f"{band}_rel")) for r in rows]
        series.append((band, t, y))
    _write_svg_line(out_path, "Bandpowers relativos por ventana", series, "Potencia relativa", (0.0, 1.0))


def plot_sonification(capture_dir: Path, out_path: Path) -> None:
    rows = _read_csv(capture_dir / "windowed_sonification_features.csv")
    series = []
    t = [_safe_float(r.get("window_start_sec")) for r in rows]
    for key in SONIF_CONTROLS:
        y = [_safe_float(r.get(key)) for r in rows]
        series.append((key, t, y))
    _write_svg_line(out_path, "Controles de sonificacion EEG-reportables", series, "Valor normalizado", (0.0, 1.0))


def plot_music_notes(capture_dir: Path, out_path: Path) -> None:
    rows = _read_csv(capture_dir / "music_notes.csv")
    width, height = 1100, 420
    left, top, plot_w, plot_h = 80, 58, 980, 285
    starts = [_safe_float(r.get("t_capture_start_sec")) for r in rows]
    ends = [_safe_float(r.get("t_capture_end_sec")) for r in rows]
    pitches = [_safe_float(r.get("pitch_midi")) for r in rows]
    velocities = [_safe_float(r.get("velocity"), 64.0) for r in rows]
    valid_x = [v for v in starts + ends if math.isfinite(v)]
    valid_p = _finite(pitches)
    xmin, xmax = _range(valid_x, (0.0, 1.0), 0.0)
    ymin, ymax = _range(valid_p, (48.0, 84.0), 0.1)

    lines = _svg_header(width, height, "Notas musicales generadas")
    lines += _axes(left, top, plot_w, plot_h, "Tiempo de captura (s)", "Pitch MIDI")
    for start, end, pitch, vel in zip(starts, ends, pitches, velocities):
        if not (math.isfinite(start) and math.isfinite(end) and math.isfinite(pitch)):
            continue
        x = _scale_x(start, xmin, xmax, left, plot_w)
        x2 = _scale_x(max(end, start + 0.04), xmin, xmax, left, plot_w)
        y = _scale_y(pitch, ymin, ymax, top, plot_h)
        alpha = max(0.25, min(1.0, vel / 127.0 if math.isfinite(vel) else 0.5))
        lines.append(f'<rect x="{x:.2f}" y="{y-3:.2f}" width="{max(2.0, x2-x):.2f}" height="6" fill="#1f77b4" opacity="{alpha:.2f}" />')
    lines.append(f'<text x="{left}" y="{top + plot_h + 20}" font-family="Arial" font-size="11">notas={len(rows)} pitch=[{ymin:.1f}, {ymax:.1f}]</text>')
    lines.append("</svg>")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def plot_combined(capture_dir: Path, out_path: Path) -> None:
    t_eeg, ch1 = _load_eeg(capture_dir)
    band_rows = _read_csv(capture_dir / "windowed_bandpowers.csv")
    sonif_rows = _read_csv(capture_dir / "windowed_sonification_features.csv")
    note_rows = _read_csv(capture_dir / "music_notes.csv")

    width, height = 1100, 900
    left, plot_w = 80, 980
    panel_h = 155
    tops = [58, 258, 458, 658]
    all_x = t_eeg[:]
    all_x += [_safe_float(r.get("window_start_sec")) for r in band_rows]
    all_x += [_safe_float(r.get("window_start_sec")) for r in sonif_rows]
    all_x += [_safe_float(r.get("t_capture_start_sec")) for r in note_rows]
    xmin, xmax = _range(all_x, (0.0, 1.0), 0.0)

    lines = _svg_header(width, height, "Figura combinada EEG + bandpowers + sonificacion + notas")

    # EEG panel
    ymin, ymax = _range(ch1, (-100.0, 100.0))
    lines += _axes(left, tops[0], plot_w, panel_h, "", "CH1 uV")
    dx, dy = _downsample(t_eeg, ch1)
    lines.append(_polyline(dx, dy, xmin, xmax, ymin, ymax, left, tops[0], plot_w, panel_h, SVG_STROKES[0]))

    # Band panel
    lines += _axes(left, tops[1], plot_w, panel_h, "", "Band rel")
    tb = [_safe_float(r.get("window_start_sec")) for r in band_rows]
    for i, band in enumerate(["alpha", "beta", "gamma"]):
        y = [_safe_float(r.get(f"{band}_rel")) for r in band_rows]
        lines.append(_polyline(tb, y, xmin, xmax, 0.0, 1.0, left, tops[1], plot_w, panel_h, SVG_STROKES[i + 1]))
    lines += _legend(["alpha", "beta", "gamma"], left + 650, tops[1] + 18)

    # Sonification panel
    lines += _axes(left, tops[2], plot_w, panel_h, "", "Sonif")
    ts = [_safe_float(r.get("window_start_sec")) for r in sonif_rows]
    keys = ["alpha_drive", "beta_gamma_drive", "band_driven_density", "band_note_probability"]
    for i, key in enumerate(keys):
        y = [_safe_float(r.get(key)) for r in sonif_rows]
        lines.append(_polyline(ts, y, xmin, xmax, 0.0, 1.0, left, tops[2], plot_w, panel_h, SVG_STROKES[i]))
    lines += _legend(keys, left + 430, tops[2] + 18)

    # Notes panel
    lines += _axes(left, tops[3], plot_w, panel_h, "Tiempo de captura (s)", "MIDI")
    starts = [_safe_float(r.get("t_capture_start_sec")) for r in note_rows]
    ends = [_safe_float(r.get("t_capture_end_sec")) for r in note_rows]
    pitches = [_safe_float(r.get("pitch_midi")) for r in note_rows]
    ymin_p, ymax_p = _range(_finite(pitches), (48.0, 84.0), 0.1)
    for start, end, pitch in zip(starts, ends, pitches):
        if not (math.isfinite(start) and math.isfinite(end) and math.isfinite(pitch)):
            continue
        x = _scale_x(start, xmin, xmax, left, plot_w)
        x2 = _scale_x(max(end, start + 0.04), xmin, xmax, left, plot_w)
        y = _scale_y(pitch, ymin_p, ymax_p, tops[3], panel_h)
        lines.append(f'<rect x="{x:.2f}" y="{y-3:.2f}" width="{max(2.0, x2-x):.2f}" height="6" fill="#1f77b4" opacity="0.75" />')

    lines.append("</svg>")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _quality_summary(capture_dir: Path) -> dict[str, Any]:
    report = _read_json(capture_dir / "quality_report.json")
    report_md = _parse_quality_md(capture_dir / "quality_report.md")
    music = _read_json(capture_dir / "music_capture_summary.json")
    spectral = _read_json(capture_dir / "spectral_validation_report.json")
    return {"quality": report, "quality_md": report_md, "music": music, "spectral": spectral}


def _quality_fields(summary: dict[str, Any]) -> dict[str, Any]:
    q = summary.get("quality", {}) or {}
    md = summary.get("quality_md", {}) or {}
    ch = ((q.get("channels") or {}).get("ch1") or {}) if isinstance(q.get("channels"), dict) else {}
    return {
        "diagnosis": q.get("diagnosis") or q.get("overall_diagnosis") or md.get("diagnosis", "n/a"),
        "duration": q.get("duration_observed_sec") or q.get("duration_sec") or md.get("duration_observed", "n/a"),
        "sample_rate": q.get("effective_sample_rate_hz") or q.get("fs_effective_hz") or md.get("effective_sample_rate", "n/a"),
        "sample_gaps": q.get("sample_gaps") or q.get("sample_gaps_total") or md.get("sample_gaps", 0),
        "invalid_status": q.get("invalid_status") or q.get("invalid_status_total") or md.get("invalid_status", 0),
        "rms_uV": ch.get("rms_uV") or q.get("rms_uV") or md.get("rms_uv", "n/a"),
        "ptp_uV": ch.get("ptp_uV") or q.get("ptp_uV") or md.get("ptp_uv", "n/a"),
        "line_50_ratio": ch.get("line_50_ratio_1_50") or q.get("line_50_ratio_1_50") or md.get("line_50_ratio_1_50", "n/a"),
        "artifact_fraction": q.get("artifact_window_fraction") or ch.get("artifact_window_fraction") or md.get("artifact_window_fraction", "n/a"),
    }


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        return f"{value:.6g}"
    return str(value)


def write_capture_doc(capture_dir: Path, docs_dir: Path, figure_paths: dict[str, Path]) -> Path:
    cond = _condition_from_dir(capture_dir)
    info = CONDITION_NOTES.get(cond, {"title": cond, "detail": "full", "purpose": "Condicion capturada durante la sesion final."})
    summary = _quality_summary(capture_dir)
    fields = _quality_fields(summary)
    music = summary.get("music", {}) or {}
    spectral = summary.get("spectral", {}) or {}
    sonif = spectral.get("sonification", {}) if isinstance(spectral.get("sonification"), dict) else {}

    doc_path = docs_dir / f"{capture_dir.name}.md"
    rels = {key: _fig_rel(path, docs_dir) for key, path in figure_paths.items()}

    lines = [
        f"# Captura final: `{cond}`",
        "",
        "## 1. Identificacion",
        "",
        f"- Carpeta: `{capture_dir}`",
        f"- Tipo: {info['title']}",
        f"- Nivel de detalle documental: `{info['detail']}`",
        f"- Objetivo: {info['purpose']}",
        "",
        "## 2. Calidad de adquisicion",
        "",
        "| Metrica | Valor |",
        "| --- | ---: |",
        f"| Diagnostico | `{_fmt(fields['diagnosis'])}` |",
        f"| Duracion observada | `{_fmt(fields['duration'])}` |",
        f"| Frecuencia efectiva | `{_fmt(fields['sample_rate'])}` |",
        f"| Sample gaps | `{_fmt(fields['sample_gaps'])}` |",
        f"| Invalid status | `{_fmt(fields['invalid_status'])}` |",
        f"| RMS CH1 | `{_fmt(fields['rms_uV'])}` |",
        f"| Pico-pico CH1 | `{_fmt(fields['ptp_uV'])}` |",
        f"| Ratio 50 Hz | `{_fmt(fields['line_50_ratio'])}` |",
        f"| Fraccion de ventanas con artefacto | `{_fmt(fields['artifact_fraction'])}` |",
        "",
    ]

    if info["detail"] == "brief":
        lines.extend([
            "## 3. Figuras de comprobacion",
            "",
            f"![EEG temporal]({rels['eeg']})",
            "",
            "## 4. Lectura",
            "",
            "Esta captura se usa como comprobacion tecnica previa. No se interpreta como condicion EEG principal. Sirve para verificar continuidad, guardado de CSV, metadatos y registro musical antes de las condiciones reportables.",
            "",
        ])
    else:
        lines.extend([
            "## 3. Figuras",
            "",
            "### 3.1 EEG temporal CH1",
            "",
            f"![EEG temporal]({rels['eeg']})",
            "",
            "### 3.2 Bandpowers relativos",
            "",
            f"![Bandpowers]({rels['bandpowers']})",
            "",
            "### 3.3 Controles de sonificacion",
            "",
            f"![Sonificacion]({rels['sonification']})",
            "",
            "### 3.4 Notas musicales",
            "",
            f"![Notas musicales]({rels['music_notes']})",
            "",
            "### 3.5 Figura combinada",
            "",
            f"![Figura combinada]({rels['combined']})",
            "",
        ])

    lines.extend([
        "## 5. Datos musicales",
        "",
        "| Metrica | Valor |",
        "| --- | ---: |",
        f"| Snapshots totales | `{_fmt(music.get('snapshots_total', 'n/a'))}` |",
        f"| Snapshots con notas | `{_fmt(music.get('snapshots_with_notes', 'n/a'))}` |",
        f"| Notas deduplicadas | `{_fmt(music.get('notes_total_deduplicated', 'n/a'))}` |",
        "",
        "## 6. Controles de sonificacion disponibles",
        "",
        "| Control | Mediana | P05 | P95 |",
        "| --- | ---: | ---: | ---: |",
    ])
    for key in SONIF_CONTROLS:
        data = sonif.get(key, {}) if isinstance(sonif.get(key), dict) else {}
        lines.append(f"| `{key}` | `{_fmt(data.get('median', 'n/a'))}` | `{_fmt(data.get('p05', 'n/a'))}` | `{_fmt(data.get('p95', 'n/a'))}` |")

    lines.extend(["", "## 7. Interpretacion para el TFG", ""])
    if cond == "blink_artifact_30s":
        lines.append("Esta captura debe presentarse como condicion de artefacto fisiologico. Su valor principal es mostrar que el sistema registra y conserva una respuesta musical incluso cuando la senal contiene contaminacion esperada por parpadeo.")
    elif cond == "eyes_open_repeat_30s":
        lines.append("Esta captura es una de las mejores candidatas para figura principal combinada, porque mantiene adquisicion estable, registro musical completo y el diagnostico automatico mas favorable de la sesion.")
    elif cond == "eyes_open_rest_60s":
        lines.append("Esta captura debe usarse con cautela: contiene sonificacion valida y datos persistidos, pero tambien un artefacto transitorio de gran amplitud. Es util para explicar limitaciones reales de la adquisicion y la necesidad de filtrar o segmentar ventanas artefactadas.")
    elif cond == "eyes_closed_rest_60s":
        lines.append("Esta captura permite documentar una condicion de ojos cerrados real, aunque contaminada por 50 Hz. Conviene interpretarla como evidencia de sistema y no como comparacion neurofisiologica concluyente.")
    elif cond == "quiet_rest_60s":
        lines.append("Esta captura sirve para documentar reposo general y sonificacion durante estado quieto. La interpretacion fisiologica debe matizarse por ruido y variabilidad de amplitud.")
    else:
        lines.append("Esta captura se conserva como parte de la trazabilidad completa de la sesion final.")

    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return doc_path


def build_session_docs(final_root: Path, subject: str, session: str, montage: str, out_docs: Path, out_figures: Path) -> list[Path]:
    captures = _discover_session_captures(final_root, subject, session, montage)
    out_docs.mkdir(parents=True, exist_ok=True)
    out_figures.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    index_lines = [
        f"# Documentacion detallada de capturas finales {subject} {session}",
        "",
        "Esta carpeta documenta las capturas concretas de la sesion final reportada en el TFG. Los prechecks se resumen de forma breve y las condiciones principales se documentan con graficas EEG, bandpowers, sonificacion y notas musicales.",
        "",
        "| Captura | Condicion | Documento |",
        "| --- | --- | --- |",
    ]

    for capture_dir in captures:
        cond = _condition_from_dir(capture_dir)
        stem = capture_dir.name
        fig_dir = out_figures / stem
        fig_dir.mkdir(parents=True, exist_ok=True)
        figure_paths = {
            "eeg": fig_dir / "eeg_ch1_temporal.svg",
            "bandpowers": fig_dir / "bandpowers_relativos.svg",
            "sonification": fig_dir / "controles_sonificacion.svg",
            "music_notes": fig_dir / "notas_musicales.svg",
            "combined": fig_dir / "figura_combinada_eeg_musica.svg",
        }
        plot_eeg(capture_dir, figure_paths["eeg"])
        plot_bandpowers(capture_dir, figure_paths["bandpowers"])
        plot_sonification(capture_dir, figure_paths["sonification"])
        plot_music_notes(capture_dir, figure_paths["music_notes"])
        plot_combined(capture_dir, figure_paths["combined"])
        doc = write_capture_doc(capture_dir, out_docs, figure_paths)
        written.append(doc)
        index_lines.append(f"| `{capture_dir.name}` | `{cond}` | [`{doc.name}`]({doc.name}) |")

    index_path = out_docs / "README.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    written.insert(0, index_path)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build detailed docs and SVG figures for final EEG-MIDI capture session without matplotlib.")
    parser.add_argument("--final-root", default="captures/capturas finales")
    parser.add_argument("--subject", default="s01")
    parser.add_argument("--session", default="20260528")
    parser.add_argument("--montage", default="ear_eeg_ch1_only")
    parser.add_argument("--out-docs", default="docs/validacion_tfg/capturas_finales_s01_20260528")
    parser.add_argument("--out-figures", default="docs/validacion_tfg/figures/capturas_finales_s01_20260528")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    final_root = PROJECT_ROOT / args.final_root
    out_docs = PROJECT_ROOT / args.out_docs
    out_figures = PROJECT_ROOT / args.out_figures
    written = build_session_docs(final_root, args.subject, args.session, args.montage, out_docs, out_figures)
    print(f"[final-capture-docs] written_docs={len(written)}")
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
