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
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"matplotlib is required: {exc}")

try:
    from scipy import signal
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"scipy is required for spectrogram generation: {exc}")


DEFAULT_CAPTURE_NAME = "20260528-145809_s01_20260528_ear_eeg_ch1_only_06_eyes_open_repeat_30s"
BANDS = ["delta", "theta", "alpha", "beta", "gamma"]
SONIF_KEYS = ["alpha_drive", "beta_gamma_drive", "band_driven_density", "band_note_probability"]


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


def robust_ylim(y: np.ndarray, percentile: float = 99.0, min_abs: float = 150.0) -> tuple[float, float]:
    finite = y[np.isfinite(y)]
    if finite.size == 0:
        return -min_abs, min_abs
    med = float(np.median(finite))
    centered = finite - med
    lim = float(np.percentile(np.abs(centered), percentile))
    lim = max(min_abs, lim * 1.15)
    return med - lim, med + lim


def save_fig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()


def plot_eeg_full_and_robust(capture_dir: Path, out_dir: Path) -> None:
    t, y = load_eeg(capture_dir)
    if t.size == 0:
        return

    plt.figure(figsize=(14, 4.2))
    plt.plot(t, y, linewidth=0.7)
    plt.title("Captura 06 - EEG CH1 completo con transitorio conservado")
    plt.xlabel("Tiempo de captura (s)")
    plt.ylabel("CH1 (uV)")
    plt.grid(True, alpha=0.3)
    save_fig(out_dir / "06_eeg_ch1_completo_con_transitorio.png")

    lo, hi = robust_ylim(y, percentile=99.0, min_abs=180.0)
    plt.figure(figsize=(14, 4.2))
    plt.plot(t, y, linewidth=0.75)
    plt.ylim(lo, hi)
    plt.title("Captura 06 - EEG CH1 vista robusta por percentil 99")
    plt.xlabel("Tiempo de captura (s)")
    plt.ylabel("CH1 (uV)")
    plt.grid(True, alpha=0.3)
    plt.text(0.01, 0.96, f"ylim robusto: [{lo:.1f}, {hi:.1f}] uV", transform=plt.gca().transAxes, va="top")
    save_fig(out_dir / "06_eeg_ch1_robusto_p99.png")

    plt.figure(figsize=(14, 4.2))
    plt.plot(t, y, linewidth=0.75)
    plt.ylim(-300, 300)
    plt.title("Captura 06 - EEG CH1 zoom fisiologico ±300 uV")
    plt.xlabel("Tiempo de captura (s)")
    plt.ylabel("CH1 (uV)")
    plt.grid(True, alpha=0.3)
    save_fig(out_dir / "06_eeg_ch1_zoom_300uv.png")


def plot_combined_robust(capture_dir: Path, out_dir: Path) -> None:
    eeg_t, eeg_y = load_eeg(capture_dir)
    band_rows = read_csv(capture_dir / "windowed_bandpowers.csv")
    sonif_rows = read_csv(capture_dir / "windowed_sonification_features.csv")
    note_rows = read_csv(capture_dir / "music_notes.csv")

    fig, axes = plt.subplots(4, 1, figsize=(14, 11), sharex=True)
    axes[0].plot(eeg_t, eeg_y, linewidth=0.65)
    axes[0].set_ylim(-300, 300)
    axes[0].set_ylabel("CH1 (uV)")
    axes[0].set_title("Captura 06 reajustada - EEG ±300 uV + bandpowers + sonificacion + notas")
    axes[0].grid(True, alpha=0.3)
    axes[0].text(0.01, 0.95, "Vista EEG recortada para ver el tramo util; el transitorio se conserva en la figura completa.", transform=axes[0].transAxes, va="top", fontsize=9)

    for band in ["alpha", "beta", "gamma"]:
        x, y = rows_xy(band_rows, "window_start_sec", f"{band}_rel")
        axes[1].plot(x, y, linewidth=1.1, label=band)
    axes[1].set_ylabel("Band rel")
    axes[1].set_ylim(-0.03, 1.03)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8, ncol=3)

    for key in SONIF_KEYS:
        x, y = rows_xy(sonif_rows, "window_start_sec", key)
        axes[2].plot(x, y, linewidth=1.1, label=key)
    axes[2].set_ylabel("Sonif")
    axes[2].set_ylim(-0.03, 1.03)
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(fontsize=8, ncol=2)

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

    save_fig(out_dir / "06_figura_combinada_reajustada_300uv.png")


def plot_quality_score(capture_dir: Path, out_dir: Path) -> None:
    rows = read_csv(capture_dir / "windowed_sonification_features.csv")
    x = []
    score = []
    gate = []
    for row in rows:
        tt = safe_float(row.get("window_start_sec"))
        sc = safe_float(row.get("quality_score"))
        gf = safe_float(row.get("quality_gate"))
        if math.isfinite(tt):
            x.append(tt)
            score.append(sc)
            gate.append(gf)
    if not x:
        return
    x_arr = np.asarray(x, dtype=float)
    score_arr = np.asarray(score, dtype=float)
    gate_arr = np.asarray(gate, dtype=float)

    plt.figure(figsize=(14, 4.2))
    if np.isfinite(score_arr).any():
        plt.plot(x_arr, score_arr, linewidth=1.4, label="quality_score")
    if np.isfinite(gate_arr).any():
        plt.plot(x_arr, gate_arr, linewidth=1.4, label="quality_gate")
    plt.axhline(0.85, linestyle="--", linewidth=0.9, label="clean >= 0.85")
    plt.axhline(0.70, linestyle="--", linewidth=0.9, label="usable >= 0.70")
    plt.axhline(0.50, linestyle="--", linewidth=0.9, label="artifact >= 0.50")
    plt.ylim(-0.03, 1.03)
    plt.title("Captura 06 - quality score y quality gate por ventana")
    plt.xlabel("Tiempo de captura (s)")
    plt.ylabel("Score / gate")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8, ncol=3)
    save_fig(out_dir / "06_quality_score_gate.png")


def plot_spectrogram(capture_dir: Path, out_dir: Path, fs: float = 250.0) -> None:
    t, y = load_eeg(capture_dir)
    if t.size < int(fs * 4):
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
    mask = (freqs >= 0.5) & (freqs <= 50.0)
    sxx_db = 10.0 * np.log10(sxx[mask] + 1e-12)

    plt.figure(figsize=(14, 5.5))
    plt.pcolormesh(times, freqs[mask], sxx_db, shading="auto")
    plt.colorbar(label="PSD (dB, escala relativa)")
    plt.title("Captura 06 - espectrograma CH1 completo 0.5-50 Hz")
    plt.xlabel("Tiempo de captura (s)")
    plt.ylabel("Frecuencia (Hz)")
    plt.ylim(0.5, 50.0)
    plt.grid(False)
    save_fig(out_dir / "06_espectrograma_ch1_0p5_50hz.png")

    plt.figure(figsize=(14, 5.0))
    plt.pcolormesh(times, freqs[mask], sxx_db, shading="auto")
    plt.colorbar(label="PSD (dB, escala relativa)")
    plt.title("Captura 06 - espectrograma CH1 bandas EEG 0.5-30 Hz")
    plt.xlabel("Tiempo de captura (s)")
    plt.ylabel("Frecuencia (Hz)")
    plt.ylim(0.5, 30.0)
    plt.grid(False)
    save_fig(out_dir / "06_espectrograma_ch1_0p5_30hz.png")


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

El espectrograma permite observar la evolucion temporal del contenido espectral. Se usa una escala robusta de visualizacion para que el transitorio final no tape la estructura del resto de la captura.

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
