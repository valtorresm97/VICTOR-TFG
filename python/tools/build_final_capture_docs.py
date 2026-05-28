from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON_DIR = PROJECT_ROOT / "python"
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _add_cached_site_packages() -> None:
    lib_dir = PROJECT_ROOT / ".cache" / ".venv" / "lib"
    if not lib_dir.exists():
        return
    for site_packages in lib_dir.glob("python*/site-packages"):
        site_path = str(site_packages)
        if site_path not in sys.path:
            sys.path.insert(0, site_path)


_add_cached_site_packages()

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover - depends on board env
    raise SystemExit(f"matplotlib is required to build figures: {exc}")


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


def _fig_rel(path: Path, figures_dir: Path) -> str:
    try:
        return str(path.relative_to(figures_dir.parent.parent))
    except Exception:
        return str(path)


def _load_eeg(capture_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = _read_csv(capture_dir / "eeg_timeseries.csv")
    if not rows:
        return np.asarray([]), np.asarray([])
    t = np.asarray([_safe_float(r.get("t_capture_sec"), math.nan) for r in rows], dtype=float)
    ch1 = np.asarray([_safe_float(r.get("ch1_uV"), math.nan) for r in rows], dtype=float)
    mask = np.isfinite(t) & np.isfinite(ch1)
    return t[mask], ch1[mask]


def _downsample_xy(x: np.ndarray, y: np.ndarray, max_points: int = 5000) -> tuple[np.ndarray, np.ndarray]:
    if x.size <= max_points:
        return x, y
    step = max(1, int(math.ceil(x.size / max_points)))
    return x[::step], y[::step]


def plot_eeg(capture_dir: Path, out_path: Path) -> None:
    t, ch1 = _load_eeg(capture_dir)
    fig, ax = plt.subplots(figsize=(12, 4))
    if t.size:
        tx, yx = _downsample_xy(t, ch1)
        ax.plot(tx, yx, linewidth=0.8)
        ax.set_xlim(float(np.nanmin(t)), float(np.nanmax(t)))
    ax.set_title("EEG CH1 temporal")
    ax.set_xlabel("Tiempo de captura (s)")
    ax.set_ylabel("CH1 (uV)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_bandpowers(capture_dir: Path, out_path: Path) -> None:
    rows = _read_csv(capture_dir / "windowed_bandpowers.csv")
    fig, ax = plt.subplots(figsize=(12, 4))
    if rows:
        t = np.asarray([_safe_float(r.get("window_start_sec"), math.nan) for r in rows], dtype=float)
        for band in BANDS:
            y = np.asarray([_safe_float(r.get(f"{band}_rel"), math.nan) for r in rows], dtype=float)
            ax.plot(t, y, linewidth=1.0, label=band)
        ax.legend(loc="upper right", ncol=5, fontsize=8)
    ax.set_title("Bandpowers relativos por ventana")
    ax.set_xlabel("Tiempo de captura (s)")
    ax.set_ylabel("Potencia relativa")
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_sonification(capture_dir: Path, out_path: Path) -> None:
    rows = _read_csv(capture_dir / "windowed_sonification_features.csv")
    fig, ax = plt.subplots(figsize=(12, 5))
    if rows:
        t = np.asarray([_safe_float(r.get("window_start_sec"), math.nan) for r in rows], dtype=float)
        for key in SONIF_CONTROLS:
            y = np.asarray([_safe_float(r.get(key), math.nan) for r in rows], dtype=float)
            ax.plot(t, y, linewidth=1.0, label=key)
        ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8)
    ax.set_title("Controles de sonificacion EEG-reportables")
    ax.set_xlabel("Tiempo de captura (s)")
    ax.set_ylabel("Valor normalizado")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_music_notes(capture_dir: Path, out_path: Path) -> None:
    rows = _read_csv(capture_dir / "music_notes.csv")
    fig, ax = plt.subplots(figsize=(12, 4))
    if rows:
        starts = np.asarray([_safe_float(r.get("t_capture_start_sec"), math.nan) for r in rows], dtype=float)
        ends = np.asarray([_safe_float(r.get("t_capture_end_sec"), math.nan) for r in rows], dtype=float)
        pitches = np.asarray([_safe_float(r.get("pitch_midi"), math.nan) for r in rows], dtype=float)
        velocities = np.asarray([_safe_float(r.get("velocity"), 64.0) for r in rows], dtype=float)
        mask = np.isfinite(starts) & np.isfinite(ends) & np.isfinite(pitches)
        for start, end, pitch, vel in zip(starts[mask], ends[mask], pitches[mask], velocities[mask]):
            width = max(0.04, float(end - start))
            ax.broken_barh([(float(start), width)], (float(pitch) - 0.4, 0.8), alpha=max(0.25, min(1.0, float(vel) / 127.0)))
        ax.set_ylim(max(0, float(np.nanmin(pitches[mask]) - 2)) if np.any(mask) else 40, float(np.nanmax(pitches[mask]) + 2) if np.any(mask) else 90)
    ax.set_title("Notas musicales generadas")
    ax.set_xlabel("Tiempo de captura (s)")
    ax.set_ylabel("Pitch MIDI")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_combined(capture_dir: Path, out_path: Path) -> None:
    t, ch1 = _load_eeg(capture_dir)
    band_rows = _read_csv(capture_dir / "windowed_bandpowers.csv")
    sonif_rows = _read_csv(capture_dir / "windowed_sonification_features.csv")
    note_rows = _read_csv(capture_dir / "music_notes.csv")

    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

    if t.size:
        tx, yx = _downsample_xy(t, ch1)
        axes[0].plot(tx, yx, linewidth=0.7)
        axes[0].set_ylabel("CH1 (uV)")
    axes[0].set_title("Figura combinada EEG + bandpowers + sonificacion + notas")
    axes[0].grid(True, alpha=0.25)

    if band_rows:
        tb = np.asarray([_safe_float(r.get("window_start_sec"), math.nan) for r in band_rows], dtype=float)
        for band in ("alpha", "beta", "gamma"):
            axes[1].plot(tb, [_safe_float(r.get(f"{band}_rel"), math.nan) for r in band_rows], linewidth=1.0, label=band)
        axes[1].legend(loc="upper right", fontsize=8)
    axes[1].set_ylabel("Band rel")
    axes[1].grid(True, alpha=0.25)

    if sonif_rows:
        ts = np.asarray([_safe_float(r.get("window_start_sec"), math.nan) for r in sonif_rows], dtype=float)
        for key in ("alpha_drive", "beta_gamma_drive", "band_driven_density", "band_note_probability"):
            axes[2].plot(ts, [_safe_float(r.get(key), math.nan) for r in sonif_rows], linewidth=1.0, label=key)
        axes[2].legend(loc="upper right", fontsize=8)
    axes[2].set_ylabel("Sonif")
    axes[2].set_ylim(-0.05, 1.05)
    axes[2].grid(True, alpha=0.25)

    if note_rows:
        starts = np.asarray([_safe_float(r.get("t_capture_start_sec"), math.nan) for r in note_rows], dtype=float)
        ends = np.asarray([_safe_float(r.get("t_capture_end_sec"), math.nan) for r in note_rows], dtype=float)
        pitches = np.asarray([_safe_float(r.get("pitch_midi"), math.nan) for r in note_rows], dtype=float)
        mask = np.isfinite(starts) & np.isfinite(ends) & np.isfinite(pitches)
        for start, end, pitch in zip(starts[mask], ends[mask], pitches[mask]):
            axes[3].broken_barh([(float(start), max(0.04, float(end - start)))], (float(pitch) - 0.4, 0.8))
        if np.any(mask):
            axes[3].set_ylim(float(np.nanmin(pitches[mask]) - 2), float(np.nanmax(pitches[mask]) + 2))
    axes[3].set_ylabel("MIDI")
    axes[3].set_xlabel("Tiempo de captura (s)")
    axes[3].grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _quality_summary(capture_dir: Path) -> dict[str, Any]:
    report = _read_json(capture_dir / "quality_report.json")
    music = _read_json(capture_dir / "music_capture_summary.json")
    spectral = _read_json(capture_dir / "spectral_validation_report.json")
    return {"quality": report, "music": music, "spectral": spectral}


def _quality_fields(summary: dict[str, Any]) -> dict[str, Any]:
    q = summary.get("quality", {}) or {}
    ch = ((q.get("channels") or {}).get("ch1") or {}) if isinstance(q.get("channels"), dict) else {}
    # Compatibility with current quality_report formats: also inspect top-level metrics if present.
    out = {
        "diagnosis": q.get("diagnosis") or q.get("Diagnosis") or q.get("overall_diagnosis") or "n/a",
        "duration": q.get("duration_observed_sec") or q.get("duration_sec") or "n/a",
        "sample_rate": q.get("effective_sample_rate_hz") or q.get("fs_effective_hz") or "n/a",
        "sample_gaps": q.get("sample_gaps") or q.get("sample_gaps_total") or 0,
        "invalid_status": q.get("invalid_status") or q.get("invalid_status_total") or 0,
        "rms_uV": ch.get("rms_uV") or q.get("rms_uV") or "n/a",
        "ptp_uV": ch.get("ptp_uV") or q.get("ptp_uV") or "n/a",
        "line_50_ratio": ch.get("line_50_ratio_1_50") or q.get("line_50_ratio_1_50") or "n/a",
        "artifact_fraction": q.get("artifact_window_fraction") or ch.get("artifact_window_fraction") or "n/a",
    }
    return out


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "n/a"
        return f"{value:.6g}"
    return str(value)


def write_capture_doc(capture_dir: Path, docs_dir: Path, figures_dir: Path, figure_paths: dict[str, Path]) -> Path:
    cond = _condition_from_dir(capture_dir)
    info = CONDITION_NOTES.get(cond, {"title": cond, "detail": "full", "purpose": "Condicion capturada durante la sesion final."})
    summary = _quality_summary(capture_dir)
    fields = _quality_fields(summary)
    music = summary.get("music", {}) or {}
    spectral = summary.get("spectral", {}) or {}
    sonif = spectral.get("sonification", {}) if isinstance(spectral.get("sonification"), dict) else {}

    doc_path = docs_dir / f"{capture_dir.name}.md"
    rels = {key: _fig_rel(path, figures_dir) for key, path in figure_paths.items()}

    lines = [
        f"# Captura final: `{cond}`",
        "",
        f"## 1. Identificacion",
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
            "## 3. Lectura",
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
        "## 4. Datos musicales",
        "",
        "| Metrica | Valor |",
        "| --- | ---: |",
        f"| Snapshots totales | `{_fmt(music.get('snapshots_total', 'n/a'))}` |",
        f"| Snapshots con notas | `{_fmt(music.get('snapshots_with_notes', 'n/a'))}` |",
        f"| Notas deduplicadas | `{_fmt(music.get('notes_total_deduplicated', 'n/a'))}` |",
        "",
        "## 5. Controles de sonificacion disponibles",
        "",
        "| Control | Mediana | P05 | P95 |",
        "| --- | ---: | ---: | ---: |",
    ])
    for key in SONIF_CONTROLS:
        data = sonif.get(key, {}) if isinstance(sonif.get(key), dict) else {}
        lines.append(f"| `{key}` | `{_fmt(data.get('median', 'n/a'))}` | `{_fmt(data.get('p05', 'n/a'))}` | `{_fmt(data.get('p95', 'n/a'))}` |")

    lines.extend([
        "",
        "## 6. Interpretacion para el TFG",
        "",
    ])
    if cond == "blink_artifact_30s":
        lines.append("Esta captura debe presentarse como condicion de artefacto fisiologico. Su valor principal es mostrar que el sistema registra y conserva una respuesta musical incluso cuando la señal contiene contaminacion esperada por parpadeo.")
    elif cond == "eyes_open_repeat_30s":
        lines.append("Esta captura es una de las mejores candidatas para figura principal combinada, porque mantiene adquisicion estable, registro musical completo y el diagnostico automatico mas favorable de la sesion.")
    elif cond == "eyes_open_rest_60s":
        lines.append("Esta captura debe usarse con cautela: contiene sonificacion valida y datos persistidos, pero tambien un artefacto transitorio de gran amplitud. Es util para explicar limitaciones reales de la adquisicion y la necesidad de filtrar/segmentar ventanas artefactadas.")
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
            "eeg": fig_dir / "eeg_ch1_temporal.png",
            "bandpowers": fig_dir / "bandpowers_relativos.png",
            "sonification": fig_dir / "controles_sonificacion.png",
            "music_notes": fig_dir / "notas_musicales.png",
            "combined": fig_dir / "figura_combinada_eeg_musica.png",
        }
        plot_eeg(capture_dir, figure_paths["eeg"])
        plot_bandpowers(capture_dir, figure_paths["bandpowers"])
        plot_sonification(capture_dir, figure_paths["sonification"])
        plot_music_notes(capture_dir, figure_paths["music_notes"])
        plot_combined(capture_dir, figure_paths["combined"])
        doc = write_capture_doc(capture_dir, out_docs, out_figures, figure_paths)
        written.append(doc)
        index_lines.append(f"| `{capture_dir.name}` | `{cond}` | [`{doc.name}`]({doc.name}) |")

    index_path = out_docs / "README.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    written.insert(0, index_path)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build detailed docs and figures for final EEG-MIDI capture session.")
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
