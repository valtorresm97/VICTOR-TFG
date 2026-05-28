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

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover - depends on environment
    raise SystemExit(
        "matplotlib is required for this tool. "
        "Run it on a PC/venv with matplotlib installed, or install matplotlib in the board environment. "
        f"Original error: {exc}"
    )


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

CONDITION_INFO = {
    "precheck_10s": ("Precheck tecnico", "brief", "Comprobacion breve de contacto, streaming, guardado EEG y guardado musical."),
    "eyes_open_rest_60s": ("Ojos abiertos en reposo", "full", "Condicion basal con ojos abiertos; util para documentar sonificacion real, con cautela por artefactos."),
    "eyes_closed_rest_60s": ("Ojos cerrados en reposo", "full", "Condicion de reposo con ojos cerrados; util para comparacion cualitativa, con cautela por 50 Hz."),
    "quiet_rest_60s": ("Reposo quieto", "full", "Condicion de reposo general; util para observar estabilidad y sonificacion."),
    "blink_artifact_30s": ("Artefacto por parpadeo", "full", "Condicion de artefacto fisiologico controlado."),
    "eyes_open_repeat_30s": ("Repeticion ojos abiertos", "full", "Candidata principal para figura combinada de la sesion final."),
}

# Standard TFG plots use a fixed EEG scale so large terminal artifacts do not
# hide the useful signal. Full-amplitude traces remain documented in enhanced
# reports when needed.
EEG_STANDARD_YLIM_UV = (-400.0, 400.0)
FEATURE_WINDOW_SEC = 4.0


def safe_float(value: Any, default: float = math.nan) -> float:
    try:
        x = float(value)
    except Exception:
        return default
    return x if math.isfinite(x) else default


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def parse_quality_md(path: Path) -> dict[str, str]:
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


def condition_from_dir(capture_dir: Path) -> str:
    name = capture_dir.name
    for marker in [
        "precheck_10s",
        "eyes_open_rest_60s",
        "eyes_closed_rest_60s",
        "quiet_rest_60s",
        "blink_artifact_30s",
        "jaw_artifact_30s",
        "eyes_open_repeat_30s",
    ]:
        if name.endswith(marker):
            return marker
    return name.split("_", 5)[-1]


def discover_captures(final_root: Path, subject: str, session: str, montage: str) -> list[Path]:
    pattern = f"*_{subject}_{session}_{montage}_*"
    return sorted(p for p in final_root.glob(pattern) if p.is_dir())


def posix_rel(path: Path, base: Path) -> str:
    """Return a portable Markdown link path, even when generated on Windows."""
    try:
        return path.relative_to(base).as_posix()
    except Exception:
        try:
            return path.relative_to(PROJECT_ROOT).as_posix()
        except Exception:
            return path.as_posix()


def repo_rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def load_eeg(capture_dir: Path) -> tuple[list[float], list[float]]:
    rows = read_csv(capture_dir / "eeg_timeseries.csv")
    t: list[float] = []
    ch1: list[float] = []
    for row in rows:
        x = safe_float(row.get("t_capture_sec"))
        y = safe_float(row.get("ch1_uV"))
        if math.isfinite(x) and math.isfinite(y):
            t.append(x)
            ch1.append(y)
    return t, ch1


def capture_duration_sec(capture_dir: Path) -> float | None:
    t, _ = load_eeg(capture_dir)
    if t:
        return max(t)
    metadata = read_json(capture_dir / "metadata.json")
    for key in ("duration_sec", "requested_duration_sec", "observed_duration_sec"):
        value = safe_float(metadata.get(key))
        if math.isfinite(value) and value > 0:
            return value
    return None


def apply_capture_xlim(duration_sec: float | None) -> None:
    if duration_sec is not None and math.isfinite(duration_sec) and duration_sec > 0:
        plt.xlim(0.0, duration_sec)


def downsample(x: list[float], y: list[float], max_points: int = 7000) -> tuple[list[float], list[float]]:
    if len(x) <= max_points:
        return x, y
    step = max(1, math.ceil(len(x) / max_points))
    return x[::step], y[::step]


def rows_xy(rows: list[dict[str, str]], x_key: str, y_key: str) -> tuple[list[float], list[float]]:
    x: list[float] = []
    y: list[float] = []
    for row in rows:
        xx = safe_float(row.get(x_key))
        yy = safe_float(row.get(y_key))
        if math.isfinite(xx) and math.isfinite(yy):
            x.append(xx)
            y.append(yy)
    return x, y


def rows_xy_windowed(rows: list[dict[str, str]], y_key: str) -> tuple[list[float], list[float]]:
    """Use a center-of-window time for offline spectral features.

    `windowed_bandpowers.csv` and `windowed_sonification_features.csv` store
    features computed over finite windows. Plotting only `window_start_sec` makes
    the spectral curves look artificially shifted and shorter than EEG/MIDI.
    For visual comparison with raw EEG and notes, use the window center when
    possible and always keep the x-axis range equal to the capture duration.
    """
    x: list[float] = []
    y: list[float] = []
    for row in rows:
        yy = safe_float(row.get(y_key))
        if not math.isfinite(yy):
            continue
        center = safe_float(row.get("window_center_sec"))
        if not math.isfinite(center):
            start = safe_float(row.get("window_start_sec"))
            end = safe_float(row.get("window_end_sec"))
            if math.isfinite(start) and math.isfinite(end):
                center = 0.5 * (start + end)
            elif math.isfinite(start):
                center = start + 0.5 * FEATURE_WINDOW_SEC
        if math.isfinite(center):
            x.append(center)
            y.append(yy)
    return x, y


def save_fig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def plot_eeg(capture_dir: Path, out_path: Path) -> None:
    duration = capture_duration_sec(capture_dir)
    t, ch1 = load_eeg(capture_dir)
    t, ch1 = downsample(t, ch1)
    plt.figure(figsize=(13, 4.2))
    plt.plot(t, ch1, linewidth=0.7)
    plt.title("EEG temporal CH1 - escala fija ±400 uV")
    plt.xlabel("Tiempo de captura (s)")
    plt.ylabel("CH1 (uV)")
    plt.ylim(*EEG_STANDARD_YLIM_UV)
    apply_capture_xlim(duration)
    plt.grid(True, alpha=0.3)
    save_fig(out_path)


def plot_bandpowers(capture_dir: Path, out_path: Path) -> None:
    duration = capture_duration_sec(capture_dir)
    rows = read_csv(capture_dir / "windowed_bandpowers.csv")
    plt.figure(figsize=(13, 4.5))
    for band in BANDS:
        x, y = rows_xy_windowed(rows, f"{band}_rel")
        plt.plot(x, y, linewidth=1.2, label=band)
    plt.title("Bandpowers relativos por ventana - tiempo centrado")
    plt.xlabel("Tiempo de captura (s)")
    plt.ylabel("Potencia relativa")
    plt.ylim(-0.03, 1.03)
    apply_capture_xlim(duration)
    plt.grid(True, alpha=0.3)
    plt.legend(loc="upper right", ncol=5, fontsize=9, frameon=True)
    save_fig(out_path)


def plot_sonification(capture_dir: Path, out_path: Path) -> None:
    duration = capture_duration_sec(capture_dir)
    rows = read_csv(capture_dir / "windowed_sonification_features.csv")
    fig, ax = plt.subplots(figsize=(13, 4.5))
    for key in SONIF_CONTROLS:
        x, y = rows_xy_windowed(rows, key)
        ax.plot(x, y, linewidth=1.0, label=key)
    ax.set_title("Controles de sonificacion EEG-reportables - tiempo centrado")
    ax.set_xlabel("Tiempo de captura (s)")
    ax.set_ylabel("Valor normalizado")
    ax.set_ylim(-0.03, 1.03)
    if duration is not None and math.isfinite(duration) and duration > 0:
        ax.set_xlim(0.0, duration)
    ax.grid(True, alpha=0.3)
    # Same visual convention as bandpowers: legend inside the axes, upper right,
    # so the PNG keeps the same footprint and does not grow horizontally.
    ax.legend(loc="upper right", ncol=2, fontsize=7, frameon=True, framealpha=0.90)
    save_fig(out_path)


def plot_quality(capture_dir: Path, out_path: Path) -> None:
    duration = capture_duration_sec(capture_dir)
    rows = read_csv(capture_dir / "windowed_sonification_features.csv")
    series = [
        ("quality_score", "quality_score"),
        ("quality_gate", "quality_gate"),
    ]
    plt.figure(figsize=(13, 4.5))
    plotted = 0
    for key, label in series:
        x, y = rows_xy_windowed(rows, key)
        if x and y:
            plt.plot(x, y, linewidth=1.2, label=label)
            plotted += 1
    if plotted:
        plt.axhline(0.85, linestyle="--", linewidth=0.9, label="clean 0.85")
        plt.axhline(0.70, linestyle="--", linewidth=0.9, label="usable 0.70")
        plt.axhline(0.50, linestyle="--", linewidth=0.9, label="artifact 0.50")
    plt.title("Calidad de señal y gate de sonificacion - tiempo centrado")
    plt.xlabel("Tiempo de captura (s)")
    plt.ylabel("Score / gate")
    plt.ylim(-0.03, 1.03)
    apply_capture_xlim(duration)
    plt.grid(True, alpha=0.3)
    plt.legend(loc="upper right", ncol=2, fontsize=8, frameon=True, framealpha=0.90)
    save_fig(out_path)


def plot_music_notes(capture_dir: Path, out_path: Path) -> None:
    duration = capture_duration_sec(capture_dir)
    rows = read_csv(capture_dir / "music_notes.csv")
    plt.figure(figsize=(13, 4.5))
    for row in rows:
        start = safe_float(row.get("t_capture_start_sec"))
        end = safe_float(row.get("t_capture_end_sec"))
        pitch = safe_float(row.get("pitch_midi"))
        vel = safe_float(row.get("velocity"), 64.0)
        if not (math.isfinite(start) and math.isfinite(end) and math.isfinite(pitch)):
            continue
        width = max(0.04, end - start)
        plt.broken_barh([(start, width)], (pitch - 0.35, 0.7), alpha=max(0.25, min(1.0, vel / 127.0)))
    plt.title("Notas musicales generadas")
    plt.xlabel("Tiempo de captura (s)")
    plt.ylabel("Pitch MIDI")
    apply_capture_xlim(duration)
    plt.grid(True, alpha=0.3)
    save_fig(out_path)


def plot_combined(capture_dir: Path, out_path: Path) -> None:
    duration = capture_duration_sec(capture_dir)
    eeg_t, eeg_y = load_eeg(capture_dir)
    eeg_t, eeg_y = downsample(eeg_t, eeg_y)
    band_rows = read_csv(capture_dir / "windowed_bandpowers.csv")
    sonif_rows = read_csv(capture_dir / "windowed_sonification_features.csv")
    note_rows = read_csv(capture_dir / "music_notes.csv")

    fig, axes = plt.subplots(4, 1, figsize=(13, 10.5), sharex=True)
    axes[0].plot(eeg_t, eeg_y, linewidth=0.65)
    axes[0].set_ylim(*EEG_STANDARD_YLIM_UV)
    axes[0].set_ylabel("CH1 (uV)")
    axes[0].set_title("EEG + bandpowers + controles de sonificacion + notas")
    axes[0].grid(True, alpha=0.3)
    axes[0].text(0.01, 0.94, "EEG mostrado con escala fija ±400 uV", transform=axes[0].transAxes, va="top", fontsize=8)

    for band in ["alpha", "beta", "gamma"]:
        x, y = rows_xy_windowed(band_rows, f"{band}_rel")
        axes[1].plot(x, y, linewidth=1.0, label=band)
    axes[1].set_ylabel("Band rel")
    axes[1].set_ylim(-0.03, 1.03)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="upper right", fontsize=8, ncol=3)

    for key in ["alpha_drive", "beta_gamma_drive", "band_driven_density", "band_note_probability"]:
        x, y = rows_xy_windowed(sonif_rows, key)
        axes[2].plot(x, y, linewidth=1.0, label=key)
    axes[2].set_ylabel("Sonif")
    axes[2].set_ylim(-0.03, 1.03)
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="upper right", fontsize=8, ncol=2)

    for row in note_rows:
        start = safe_float(row.get("t_capture_start_sec"))
        end = safe_float(row.get("t_capture_end_sec"))
        pitch = safe_float(row.get("pitch_midi"))
        if not (math.isfinite(start) and math.isfinite(end) and math.isfinite(pitch)):
            continue
        axes[3].broken_barh([(start, max(0.04, end - start))], (pitch - 0.35, 0.7), alpha=0.75)
    axes[3].set_ylabel("MIDI")
    axes[3].set_xlabel("Tiempo de captura (s)")
    axes[3].grid(True, alpha=0.3)

    if duration is not None and math.isfinite(duration) and duration > 0:
        axes[3].set_xlim(0.0, duration)

    save_fig(out_path)


def normalize_diagnosis(value: Any) -> str:
    if isinstance(value, dict):
        state = value.get("state", "n/a")
        reasons = value.get("reasons") or []
        if reasons:
            return f"{state} - {', '.join(map(str, reasons))}"
        return str(state)
    return fmt(value)


def quality_fields(capture_dir: Path) -> dict[str, Any]:
    q = read_json(capture_dir / "quality_report.json")
    md = parse_quality_md(capture_dir / "quality_report.md")
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


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return "n/a" if math.isnan(value) else f"{value:.6g}"
    return str(value)


def write_capture_doc(capture_dir: Path, docs_dir: Path, fig_paths: dict[str, Path]) -> Path:
    cond = condition_from_dir(capture_dir)
    title, detail, purpose = CONDITION_INFO.get(cond, (cond, "full", "Condicion capturada durante la sesion final."))
    fields = quality_fields(capture_dir)
    music = read_json(capture_dir / "music_capture_summary.json")
    spectral = read_json(capture_dir / "spectral_validation_report.json")
    sonif = spectral.get("sonification", {}) if isinstance(spectral.get("sonification"), dict) else {}
    doc_path = docs_dir / f"{capture_dir.name}.md"

    lines = [
        f"# Captura final: `{cond}`",
        "",
        "## 1. Identificacion",
        "",
        f"- Carpeta: `{repo_rel(capture_dir)}`",
        f"- Tipo: {title}",
        f"- Nivel de detalle documental: `{detail}`",
        f"- Objetivo: {purpose}",
        "",
        "## 2. Calidad de adquisicion",
        "",
        "| Metrica | Valor |",
        "| --- | ---: |",
        f"| Diagnostico | `{normalize_diagnosis(fields['diagnosis'])}` |",
        f"| Duracion observada | `{fmt(fields['duration'])}` |",
        f"| Frecuencia efectiva | `{fmt(fields['sample_rate'])}` |",
        f"| Sample gaps | `{fmt(fields['sample_gaps'])}` |",
        f"| Invalid status | `{fmt(fields['invalid_status'])}` |",
        f"| RMS CH1 | `{fmt(fields['rms_uV'])}` |",
        f"| Pico-pico CH1 | `{fmt(fields['ptp_uV'])}` |",
        f"| Ratio 50 Hz | `{fmt(fields['line_50_ratio'])}` |",
        f"| Fraccion de ventanas con artefacto | `{fmt(fields['artifact_fraction'])}` |",
        "",
        "## 3. Figuras",
        "",
        "Nota: las figuras EEG temporales estandar usan escala fija `±400 uV` para facilitar la inspeccion visual. Los transitorios completos se conservan en las metricas de calidad y, cuando procede, en las figuras enhanced.",
        "",
        f"![EEG temporal]({posix_rel(fig_paths['eeg'], docs_dir)})",
        "",
    ]

    if detail != "brief":
        lines += [
            f"![Bandpowers relativos]({posix_rel(fig_paths['bandpowers'], docs_dir)})",
            "",
            f"![Controles de sonificacion]({posix_rel(fig_paths['sonification'], docs_dir)})",
            "",
            f"![Calidad de senal y gate]({posix_rel(fig_paths['quality'], docs_dir)})",
            "",
            f"![Notas musicales]({posix_rel(fig_paths['music_notes'], docs_dir)})",
            "",
        ]

    lines += [
        "## 4. Datos musicales",
        "",
        "| Metrica | Valor |",
        "| --- | ---: |",
        f"| Snapshots totales | `{fmt(music.get('snapshots_total', 'n/a'))}` |",
        f"| Snapshots con notas | `{fmt(music.get('snapshots_with_notes', 'n/a'))}` |",
        f"| Notas deduplicadas | `{fmt(music.get('notes_total_deduplicated', 'n/a'))}` |",
        "",
        "## 5. Controles de sonificacion disponibles",
        "",
        "| Control | Mediana | P05 | P95 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key in SONIF_CONTROLS:
        data = sonif.get(key, {}) if isinstance(sonif.get(key), dict) else {}
        lines.append(f"| `{key}` | `{fmt(data.get('median', 'n/a'))}` | `{fmt(data.get('p05', 'n/a'))}` | `{fmt(data.get('p95', 'n/a'))}` |")

    lines += ["", "## 6. Interpretacion para el TFG", ""]
    if cond == "blink_artifact_30s":
        lines.append("Condicion de artefacto fisiologico. No se reporta como EEG limpio; se usa para mostrar respuesta del sistema ante contaminacion esperada por parpadeo.")
    elif cond == "eyes_open_repeat_30s":
        lines.append("Candidata principal de la sesion final por ser la condicion con mejor diagnostico automatico y sonificacion persistida. La figura combinada se conserva como PNG, pero este documento automatico evita repetirla porque las graficas ya aparecen por separado.")
    elif cond == "eyes_open_rest_60s":
        lines.append("Contiene sonificacion valida y datos persistidos, pero tambien un artefacto transitorio de gran amplitud. Es util para explicar limitaciones reales de adquisicion.")
    elif cond == "eyes_closed_rest_60s":
        lines.append("Condicion real de ojos cerrados; debe interpretarse con cautela por contaminacion de 50 Hz.")
    elif cond == "quiet_rest_60s":
        lines.append("Reposo general con sonificacion registrada; interpretacion fisiologica matizada por ruido y variabilidad de amplitud.")
    else:
        lines.append("Captura conservada como trazabilidad tecnica de la sesion final.")

    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return doc_path


def build_docs(final_root: Path, subject: str, session: str, montage: str, docs_dir: Path, figures_dir: Path) -> list[Path]:
    captures = discover_captures(final_root, subject, session, montage)
    docs_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index = [
        f"# Documentacion matplotlib de capturas finales {subject} {session}",
        "",
        "Figuras generadas con matplotlib a partir de la sesion real reportada en el TFG.",
        "",
        "Criterios de representacion aplicados:",
        "",
        "- EEG temporal estandar con escala fija `±400 uV` para evitar que transitorios grandes oculten la dinamica util.",
        "- Bandpowers, controles de sonificacion y calidad con tiempo centrado en la ventana y eje X alineado con la duracion total de la captura.",
        "- La figura combinada se conserva como PNG en la carpeta de figuras, pero no se inserta en los Markdown automaticos para evitar duplicacion visual.",
        "- Las graficas de controles de sonificacion usan leyenda interna en esquina superior derecha, igual que las graficas de bandpowers, para mantener el mismo tamano de imagen.",
        "",
        "| Captura | Condicion | Documento |",
        "| --- | --- | --- |",
    ]

    for capture_dir in captures:
        cond = condition_from_dir(capture_dir)
        fig_dir = figures_dir / capture_dir.name
        fig_dir.mkdir(parents=True, exist_ok=True)
        fig_paths = {
            "eeg": fig_dir / "eeg_ch1_temporal.png",
            "bandpowers": fig_dir / "bandpowers_relativos.png",
            "sonification": fig_dir / "controles_sonificacion.png",
            "quality": fig_dir / "calidad_senal_quality_gate.png",
            "music_notes": fig_dir / "notas_musicales.png",
            "combined": fig_dir / "figura_combinada_eeg_musica.png",
        }
        plot_eeg(capture_dir, fig_paths["eeg"])
        plot_bandpowers(capture_dir, fig_paths["bandpowers"])
        plot_sonification(capture_dir, fig_paths["sonification"])
        plot_quality(capture_dir, fig_paths["quality"])
        plot_music_notes(capture_dir, fig_paths["music_notes"])
        plot_combined(capture_dir, fig_paths["combined"])
        doc = write_capture_doc(capture_dir, docs_dir, fig_paths)
        written.append(doc)
        index.append(f"| `{capture_dir.name}` | `{cond}` | [`{doc.name}`]({doc.name}) |")

    readme = docs_dir / "README.md"
    readme.write_text("\n".join(index) + "\n", encoding="utf-8")
    written.insert(0, readme)
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build final capture docs and PNG figures with matplotlib.")
    parser.add_argument("--final-root", default="captures/capturas finales")
    parser.add_argument("--subject", default="s01")
    parser.add_argument("--session", default="20260528")
    parser.add_argument("--montage", default="ear_eeg_ch1_only")
    parser.add_argument("--out-docs", default="docs/validacion_tfg/capturas_finales_s01_20260528_matplotlib")
    parser.add_argument("--out-figures", default="docs/validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    written = build_docs(
        PROJECT_ROOT / args.final_root,
        args.subject,
        args.session,
        args.montage,
        PROJECT_ROOT / args.out_docs,
        PROJECT_ROOT / args.out_figures,
    )
    print(f"[final-capture-docs-matplotlib] written_docs={len(written)}")
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
