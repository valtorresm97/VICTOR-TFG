from __future__ import annotations

import argparse
import csv
import json
import math
import os
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
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"matplotlib is required: {exc}")

try:
    from scipy import signal
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"scipy is required for spectrogram generation: {exc}")


DEFAULT_CAPTURE_NAME = "20260528-145809_s01_20260528_ear_eeg_ch1_only_06_eyes_open_repeat_30s"
BANDS = ["delta", "theta", "alpha", "beta", "gamma"]
SONIF_KEYS = ["alpha_drive", "beta_gamma_drive", "band_driven_density", "band_note_probability"]

FIG_SIZE = (12.8, 4.35)
SPECTROGRAM_SIZE = (12.8, 5.15)
COMBINED_SIZE = (12.8, 10.2)
EXPORT_DPI = 220
GRID_ALPHA = 0.22
GRID_COLOR = "#b9c0c7"
AXIS_COLOR = "#29323d"
TEXT_COLOR = "#111827"
EEG_COLOR = "#1f4e79"
NOTE_COLOR = "#3657c9"
BAND_COLORS = {"alpha": "#54A24B", "beta": "#E45756", "gamma": "#B279A2"}
SONIF_COLORS = {
    "alpha_drive": "#1f77b4",
    "beta_gamma_drive": "#d62728",
    "band_driven_density": "#ff7f0e",
    "band_note_probability": "#e377c2",
}
QUALITY_COLORS = {"quality_score": "#1f77b4", "quality_gate": "#ff7f0e"}


def apply_publication_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": AXIS_COLOR,
            "axes.labelcolor": TEXT_COLOR,
            "axes.titlecolor": TEXT_COLOR,
            "xtick.color": AXIS_COLOR,
            "ytick.color": AXIS_COLOR,
            "text.color": TEXT_COLOR,
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "semibold",
            "axes.labelsize": 10.5,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "legend.fontsize": 8.2,
            "legend.frameon": True,
            "legend.framealpha": 0.88,
            "legend.edgecolor": "#d0d7de",
            "legend.facecolor": "white",
            "savefig.dpi": EXPORT_DPI,
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
        }
    )


apply_publication_style()


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


def load_eeg(capture_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = read_csv(capture_dir / "eeg_timeseries.csv")
    t: list[float] = []
    y: list[float] = []
    for row in rows:
        tt = safe_float(row.get("t_capture_sec"))
        yy = safe_float(row.get("ch1_uV"))
        if math.isfinite(tt) and math.isfinite(yy):
            t.append(tt)
            y.append(yy)
    return np.asarray(t, dtype=float), np.asarray(y, dtype=float)


def capture_duration_sec(capture_dir: Path) -> float | None:
    t, _ = load_eeg(capture_dir)
    if t.size:
        return float(np.nanmax(t))
    metadata = read_json(capture_dir / "metadata.json")
    for key in ("duration_sec", "requested_duration_sec", "observed_duration_sec"):
        value = safe_float(metadata.get(key))
        if math.isfinite(value) and value > 0:
            return value
    return None


def apply_capture_xlim(ax: Any, duration_sec: float | None) -> None:
    if duration_sec is not None and math.isfinite(duration_sec) and duration_sec > 0:
        ax.set_xlim(0.0, duration_sec)


def rows_xy(rows: list[dict[str, str]], x_key: str, y_key: str) -> tuple[np.ndarray, np.ndarray]:
    x: list[float] = []
    y: list[float] = []
    for row in rows:
        xx = safe_float(row.get(x_key))
        yy = safe_float(row.get(y_key))
        if math.isfinite(xx) and math.isfinite(yy):
            x.append(xx)
            y.append(yy)
    return np.asarray(x, dtype=float), np.asarray(y, dtype=float)


def rows_xy_windowed(rows: list[dict[str, str]], y_key: str) -> tuple[np.ndarray, np.ndarray]:
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
                center = start + 2.0
        if math.isfinite(center):
            x.append(center)
            y.append(yy)
    return np.asarray(x, dtype=float), np.asarray(y, dtype=float)


def robust_ylim(y: np.ndarray, percentile: float = 99.0, min_abs: float = 150.0) -> tuple[float, float]:
    finite = y[np.isfinite(y)]
    if finite.size == 0:
        return -min_abs, min_abs
    med = float(np.median(finite))
    centered = finite - med
    lim = float(np.percentile(np.abs(centered), percentile))
    lim = max(min_abs, lim * 1.15)
    return med - lim, med + lim


def style_axes(ax: Any, *, grid: bool = True) -> None:
    if grid:
        ax.grid(True, color=GRID_COLOR, alpha=GRID_ALPHA, linewidth=0.75)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#8b949e")
    ax.spines["bottom"].set_color("#8b949e")
    ax.tick_params(axis="both", which="major", length=4, width=0.8)


def save_fig(fig: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=1.15)
    fig.savefig(path, dpi=EXPORT_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_eeg_full_and_robust(capture_dir: Path, out_dir: Path) -> None:
    duration = capture_duration_sec(capture_dir)
    t, y = load_eeg(capture_dir)
    if t.size == 0:
        return

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(t, y, linewidth=0.82, color=EEG_COLOR)
    ax.set_title("Captura 06 - EEG CH1 completo")
    ax.set_xlabel("Tiempo de captura (s)")
    ax.set_ylabel("Amplitud CH1 (uV)")
    apply_capture_xlim(ax, duration)
    style_axes(ax)
    save_fig(fig, out_dir / "06_eeg_ch1_completo_con_transitorio.png")

    lo, hi = robust_ylim(y, percentile=99.0, min_abs=180.0)
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(t, y, linewidth=0.84, color=EEG_COLOR)
    ax.set_ylim(lo, hi)
    ax.set_title("Captura 06 - EEG CH1 con escala robusta")
    ax.set_xlabel("Tiempo de captura (s)")
    ax.set_ylabel("Amplitud CH1 (uV)")
    apply_capture_xlim(ax, duration)
    style_axes(ax)
    ax.text(
        0.012,
        0.955,
        f"Percentil 99: [{lo:.1f}, {hi:.1f}] uV",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.5,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#d0d7de", "alpha": 0.82},
    )
    save_fig(fig, out_dir / "06_eeg_ch1_robusto_p99.png")

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(t, y, linewidth=0.84, color=EEG_COLOR)
    ax.set_ylim(-300, 300)
    ax.set_title("Captura 06 - EEG CH1 en rango fisiologico")
    ax.set_xlabel("Tiempo de captura (s)")
    ax.set_ylabel("Amplitud CH1 (uV)")
    apply_capture_xlim(ax, duration)
    style_axes(ax)
    save_fig(fig, out_dir / "06_eeg_ch1_zoom_300uv.png")


def plot_combined_robust(capture_dir: Path, out_dir: Path) -> None:
    duration = capture_duration_sec(capture_dir)
    eeg_t, eeg_y = load_eeg(capture_dir)
    band_rows = read_csv(capture_dir / "windowed_bandpowers.csv")
    sonif_rows = read_csv(capture_dir / "windowed_sonification_features.csv")
    note_rows = read_csv(capture_dir / "music_notes.csv")

    fig, axes = plt.subplots(4, 1, figsize=COMBINED_SIZE, sharex=True)
    axes[0].plot(eeg_t, eeg_y, linewidth=0.74, color=EEG_COLOR)
    axes[0].set_ylim(-300, 300)
    axes[0].set_ylabel("CH1 (uV)")
    axes[0].set_title("Captura 06 reajustada: EEG, espectro, sonificacion y notas")
    axes[0].text(
        0.012,
        0.94,
        "Vista EEG ±300 uV; transitorio documentado por separado",
        transform=axes[0].transAxes,
        va="top",
        fontsize=8.0,
        bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "edgecolor": "#d0d7de", "alpha": 0.82},
    )
    style_axes(axes[0])

    for band in ["alpha", "beta", "gamma"]:
        x, y = rows_xy_windowed(band_rows, f"{band}_rel")
        axes[1].plot(x, y, linewidth=1.25, color=BAND_COLORS.get(band), label=band)
    axes[1].set_ylabel("Band rel")
    axes[1].set_ylim(-0.03, 1.03)
    style_axes(axes[1])
    axes[1].legend(loc="upper right", fontsize=7.5, ncol=3)

    for key in SONIF_KEYS:
        x, y = rows_xy_windowed(sonif_rows, key)
        axes[2].plot(x, y, linewidth=1.22, color=SONIF_COLORS.get(key), label=key)
    axes[2].set_ylabel("Sonif")
    axes[2].set_ylim(-0.03, 1.03)
    style_axes(axes[2])
    axes[2].legend(loc="upper right", fontsize=7.2, ncol=2)

    pitches: list[float] = []
    for row in note_rows:
        start = safe_float(row.get("t_capture_start_sec"))
        end = safe_float(row.get("t_capture_end_sec"))
        pitch = safe_float(row.get("pitch_midi"))
        if not (math.isfinite(start) and math.isfinite(end) and math.isfinite(pitch)):
            continue
        axes[3].broken_barh(
            [(start, max(0.04, end - start))],
            (pitch - 0.35, 0.7),
            facecolors=NOTE_COLOR,
            edgecolors="#233a9f",
            linewidth=0.2,
            alpha=0.72,
        )
        pitches.append(pitch)
    axes[3].set_ylabel("MIDI")
    axes[3].set_xlabel("Tiempo de captura (s)")
    if pitches:
        axes[3].set_ylim(max(0, math.floor(min(pitches) - 2)), min(127, math.ceil(max(pitches) + 2)))
    style_axes(axes[3])
    apply_capture_xlim(axes[3], duration)
    save_fig(fig, out_dir / "06_figura_combinada_reajustada_300uv.png")


def plot_quality_score(capture_dir: Path, out_dir: Path) -> None:
    duration = capture_duration_sec(capture_dir)
    rows = read_csv(capture_dir / "windowed_sonification_features.csv")
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    plotted = 0
    for key, label in [("quality_score", "quality_score"), ("quality_gate", "quality_gate")]:
        x, y = rows_xy_windowed(rows, key)
        if x.size and y.size:
            ax.plot(x, y, linewidth=1.55, color=QUALITY_COLORS[key], label=label)
            plotted += 1
    if plotted:
        for y_thr, label in [(0.85, "clean 0.85"), (0.70, "usable 0.70"), (0.50, "artifact 0.50")]:
            ax.axhline(y_thr, linestyle="--", linewidth=0.95, color="#6b7280", alpha=0.72, label=label)
    ax.set_ylim(-0.03, 1.03)
    ax.set_title("Captura 06 - calidad de senal y gate")
    ax.set_xlabel("Tiempo de captura (s)")
    ax.set_ylabel("Score / gate")
    apply_capture_xlim(ax, duration)
    style_axes(ax)
    if plotted:
        ax.legend(loc="upper right", ncol=2, fontsize=7.8, borderpad=0.42, handlelength=1.55, columnspacing=0.72)
    save_fig(fig, out_dir / "06_quality_score_gate.png")


def contrast_limits(values: np.ndarray) -> tuple[float, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return -120.0, 0.0
    vmin = float(np.percentile(finite, 7.0))
    vmax = float(np.percentile(finite, 99.7))
    if not math.isfinite(vmin) or not math.isfinite(vmax) or vmax <= vmin:
        vmin = float(np.nanmin(finite))
        vmax = float(np.nanmax(finite))
    if vmax <= vmin:
        vmax = vmin + 1.0
    return vmin, vmax


def render_spectrogram(times: np.ndarray, freqs: np.ndarray, sxx_db: np.ndarray, out_path: Path, title: str, ylim: tuple[float, float]) -> None:
    vmin, vmax = contrast_limits(sxx_db)
    fig, ax = plt.subplots(figsize=SPECTROGRAM_SIZE)
    mesh = ax.pcolormesh(
        times,
        freqs,
        sxx_db,
        shading="auto",
        cmap="turbo",
        vmin=vmin,
        vmax=vmax,
    )
    cbar = fig.colorbar(mesh, ax=ax, pad=0.015)
    cbar.set_label("PSD relativa (dB)", fontsize=9.5)
    cbar.ax.tick_params(labelsize=8.5)
    ax.set_title(title)
    ax.set_xlabel("Tiempo de captura (s)")
    ax.set_ylabel("Frecuencia (Hz)")
    ax.set_ylim(*ylim)
    style_axes(ax, grid=False)
    save_fig(fig, out_path)


def plot_spectrogram(capture_dir: Path, out_dir: Path, fs: float = 250.0) -> None:
    _t, y = load_eeg(capture_dir)
    if y.size < int(fs * 4):
        return
    # Robust clipping only for display so that the final artifact does not hide the whole spectrogram.
    lo, hi = robust_ylim(y, percentile=99.5, min_abs=300.0)
    y_disp = np.clip(y, lo, hi)
    y_disp = y_disp - np.nanmedian(y_disp)

    nperseg = int(fs * 2.0)
    noverlap = int(nperseg * 0.75)
    freqs, times, sxx = signal.spectrogram(
        y_disp,
        fs=fs,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        scaling="density",
        mode="psd",
    )
    mask_50 = (freqs >= 0.5) & (freqs <= 50.0)
    freqs_50 = freqs[mask_50]
    sxx_db_50 = 10.0 * np.log10(sxx[mask_50] + 1e-12)
    # The turbo colormap maps the highest displayed power to red/yellow,
    # making power differences visually clearer without changing the PSD data.
    render_spectrogram(
        times,
        freqs_50,
        sxx_db_50,
        out_dir / "06_espectrograma_ch1_0p5_50hz.png",
        "Captura 06 - espectrograma CH1 0.5-50 Hz",
        (0.5, 50.0),
    )
    mask_30 = (freqs_50 >= 0.5) & (freqs_50 <= 30.0)
    render_spectrogram(
        times,
        freqs_50[mask_30],
        sxx_db_50[mask_30],
        out_dir / "06_espectrograma_ch1_0p5_30hz.png",
        "Captura 06 - espectrograma CH1 0.5-30 Hz",
        (0.5, 30.0),
    )


def write_enhanced_report(capture_dir: Path, out_dir: Path, docs_dir: Path) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    rel_base = "../figures/capturas_finales_s01_20260528_enhanced/06_eyes_open_repeat_30s"
    text = f"""# Seccion final reajustada - captura `06_eyes_open_repeat_30s`

## 1. Motivo de esta seccion

La figura combinada original de la captura `06_eyes_open_repeat_30s` conserva toda la amplitud real de la senal. Eso es correcto para trazabilidad, pero el transitorio final obliga a que el eje vertical del EEG alcance valores del orden de decenas de miles de microvoltios. Como consecuencia, la parte util de la senal queda visualmente aplastada.

Por este motivo se generan dos lecturas complementarias:

1. **Vista completa**, donde el transitorio queda visible y no se oculta.
2. **Vista reajustada**, donde el eje EEG se limita de forma robusta para observar la dinamica principal de la captura.

La vista reajustada no sustituye a la completa. Solo sirve para explicar mejor el tramo util de la senal y su relacion con la sonificacion.

## 2. EEG completo con transitorio conservado

![EEG completo]({rel_base}/06_eeg_ch1_completo_con_transitorio.png)

Esta figura conserva toda la amplitud. Es la prueba de que existe un transitorio final de gran magnitud. Debe mantenerse para no ocultar artefactos.

## 3. EEG con escala robusta por percentil

![EEG robusto p99]({rel_base}/06_eeg_ch1_robusto_p99.png)

La escala robusta permite ver la mayor parte de la senal sin que el transitorio domine toda la grafica. Esta vista es util para discusion visual, pero debe explicarse que el artefacto existe y se muestra en la figura completa.

## 4. EEG con zoom fisiologico ±300 uV

![EEG zoom 300 uV]({rel_base}/06_eeg_ch1_zoom_300uv.png)

Esta vista permite observar el rango en el que se concentra la mayor parte de la actividad util. No debe usarse para negar el artefacto, sino para inspeccionar la parte no dominada por el transitorio.

## 5. Quality score y quality gate

![Quality score]({rel_base}/06_quality_score_gate.png)

Esta grafica muestra la evolucion de la calidad por ventana. Es importante porque conecta los artefactos con la atenuacion o validacion de la sonificacion. En el TFG debe explicarse que el sistema no solo genera musica, sino que tambien calcula un indicador de calidad que permite interpretar las ventanas con cautela.

## 6. Espectrograma completo

![Espectrograma 0.5-50 Hz]({rel_base}/06_espectrograma_ch1_0p5_50hz.png)

El espectrograma permite observar la evolucion temporal del contenido espectral. Se usa una escala robusta de visualizacion para que el transitorio final no tape la estructura del resto de la captura. La paleta de alto contraste hace que las zonas de mayor potencia alcancen rojo/amarillo y que las diferencias de potencia sean mas visibles.

## 7. Espectrograma en bandas EEG hasta 30 Hz

![Espectrograma 0.5-30 Hz]({rel_base}/06_espectrograma_ch1_0p5_30hz.png)

Esta version se centra en el rango mas interpretable para la sesion, evitando dar demasiado peso visual al extremo alto donde la interpretacion de gamma es mas delicada por filtros y ruido.

## 8. Figura combinada reajustada

![Figura combinada reajustada]({rel_base}/06_figura_combinada_reajustada_300uv.png)

Esta es la figura combinada recomendada para la memoria si se quiere mostrar la relacion entre EEG, bandpowers, controles de sonificacion y notas sin que el transitorio final aplaste toda la senal.

## 9. Texto recomendado para la memoria

> La captura `06_eyes_open_repeat_30s` fue la mejor candidata de la sesion final. La figura completa muestra un transitorio de gran amplitud al final, por lo que no se presenta como EEG clinicamente limpio. Para analizar la parte util de la captura se genero una visualizacion reajustada del eje EEG, manteniendo por separado la figura completa para trazabilidad. Esta doble representacion permite documentar honestamente el artefacto y, al mismo tiempo, observar la relacion entre la actividad registrada, los bandpowers, los controles de sonificacion y las notas MIDI generadas.

## 10. Conclusion

La captura 06 debe reportarse con ambas vistas: completa y reajustada. La completa demuestra transparencia experimental; la reajustada permite interpretar la parte util y defender la integracion EEG-MIDI.
"""
    (docs_dir / "06_eyes_open_repeat_30s_reajustada.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build enhanced figures for final capture 06.")
    parser.add_argument("--capture-dir", default=f"captures/capturas finales/{DEFAULT_CAPTURE_NAME}")
    parser.add_argument("--out-figures", default="docs/validacion_tfg/figures/capturas_finales_s01_20260528_enhanced/06_eyes_open_repeat_30s")
    parser.add_argument("--out-docs", default="docs/validacion_tfg/reportajes_capturas_s01_20260528")
    args = parser.parse_args()

    capture_dir = PROJECT_ROOT / args.capture_dir
    out_dir = PROJECT_ROOT / args.out_figures
    docs_dir = PROJECT_ROOT / args.out_docs
    if not capture_dir.exists():
        raise SystemExit(f"Capture directory not found: {capture_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    plot_eeg_full_and_robust(capture_dir, out_dir)
    plot_combined_robust(capture_dir, out_dir)
    plot_quality_score(capture_dir, out_dir)
    plot_spectrogram(capture_dir, out_dir)
    write_enhanced_report(capture_dir, out_dir, docs_dir)

    print(f"[capture06-enhanced] figures={out_dir}")
    print(f"[capture06-enhanced] doc={docs_dir / '06_eyes_open_repeat_30s_reajustada.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
