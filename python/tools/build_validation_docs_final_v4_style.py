"""Regenera docs/validacion_tfg con estilo de figuras final-v4.

Este wrapper no cambia los calculos base de `build_validation_docs.py`. Aplica una
capa de estilo Matplotlib mas segura para la memoria del TFG y mejora la
homogeneidad de las figuras por estado de la captura mixed_states:

- titulos mas pequenos y envueltos automaticamente;
- margenes/bbox robustos para evitar textos fuera del PNG/PDF;
- leyendas con tamano moderado;
- salida con mas dpi y padding estable;
- senal temporal + PSD multitaper para todos los estados de la timeline;
- periodograma vs multitaper para todos los estados de la timeline.

Uso recomendado desde la raiz del repo:

    python3 python/tools/build_validation_docs_final_v4_style.py \
      --captures captures \
      --output docs/validacion_tfg

La salida pisa las mismas figuras/documentos generados por `build_validation_docs.py`,
por lo que debe ejecutarse con `git status --short` limpio o con cambios controlados.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import build_validation_docs as base


FINAL_V4_RCPARAMS = {
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "figure.titlesize": 15,
    "axes.titlepad": 12,
    "figure.autolayout": False,
}

FIGSIZE_TIMESERIES = (10.5, 3.8)
FIGSIZE_PSD = (10.5, 3.8)
FIGSIZE_COMPARE = (10.5, 3.8)


def _wrap_title(title: str | None, width: int = 74) -> str:
    if not title:
        return ""
    return "\n".join(textwrap.wrap(str(title), width=width, break_long_words=False))


def _slug(text: str) -> str:
    text = text.lower()
    text = (
        text.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "estado"


def apply_final_v4_plot_style(ax, xlabel: str | None = None, ylabel: str | None = None, title: str | None = None) -> None:
    """Estilo conservador para figuras de validacion TFG."""

    ax.set_xlabel(xlabel or "", fontsize=12, labelpad=8)
    ax.set_ylabel(ylabel or "", fontsize=12, labelpad=8)
    ax.set_title(_wrap_title(title), fontsize=14, pad=14)
    ax.tick_params(axis="both", labelsize=10)
    ax.grid(True, alpha=0.22)

    legend = ax.get_legend()
    if legend is not None:
        for text in legend.get_texts():
            text.set_fontsize(9)
        legend.set_frame_on(True)
        legend.get_frame().set_alpha(0.88)


def savefig_final_v4(path: Path) -> None:
    """Guarda PNG/PDF evitando recortes de titulos y leyendas."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.gcf()
    try:
        fig.tight_layout(rect=(0.02, 0.02, 0.98, 0.94), pad=1.35)
    except Exception:
        pass

    fig.savefig(path, dpi=220, bbox_inches="tight", pad_inches=0.18)
    try:
        fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.18)
    except Exception:
        pass
    plt.close(fig)


def plot_all_state_timeseries_and_psd(capture, figures_dir: Path) -> dict[str, str]:
    """Genera el mismo par de figuras para todos los estados de mixed_states."""

    out: dict[str, str] = {}
    fs = capture.fs_hz or 250.0
    for state, start, stop, label in base.infer_or_load_state_timeline(capture):
        x_v = base._segment_signal(capture, start, stop)
        if x_v.size < 16:
            continue
        key = _slug(state)
        t = np.arange(x_v.size) / fs

        fig, ax = plt.subplots(figsize=FIGSIZE_TIMESERIES)
        ax.plot(t, x_v * 1e6, linewidth=0.85)
        apply_final_v4_plot_style(
            ax,
            xlabel="Tiempo dentro del estado (s)",
            ylabel="CH1 (uV)",
            title=f"Senal temporal por estado: {label}",
        )
        name = f"fig_03_state_{key}_timeseries.png"
        savefig_final_v4(figures_dir / name)
        out[f"state_{key}_timeseries"] = name

        f, p = base._compute_psd_for_segment(capture, start, stop, "multitaper")
        if f.size:
            fig, ax = plt.subplots(figsize=FIGSIZE_PSD)
            ax.semilogy(f, np.maximum(p, 1e-20), linewidth=1.15)
            ax.set_xlim(0.5, 45)
            apply_final_v4_plot_style(
                ax,
                xlabel="Frecuencia (Hz)",
                ylabel="PSD (V^2/Hz)",
                title=f"PSD multitaper por estado: {label}",
            )
            name = f"fig_03_state_{key}_psd.png"
            savefig_final_v4(figures_dir / name)
            out[f"state_{key}_psd"] = name
    return out


def plot_all_periodogram_vs_multitaper(capture, figures_dir: Path) -> dict[str, str]:
    """Compara periodograma y multitaper en todos los estados disponibles."""

    out: dict[str, str] = {}
    for state, start, stop, label in base.infer_or_load_state_timeline(capture):
        f1, p1 = base._compute_psd_for_segment(capture, start, stop, "periodogram")
        f2, p2 = base._compute_psd_for_segment(capture, start, stop, "multitaper")
        if not f1.size or not f2.size:
            continue
        key = _slug(state)
        fig, ax = plt.subplots(figsize=FIGSIZE_COMPARE)
        ax.semilogy(f1, np.maximum(p1, 1e-20), label="Periodograma", alpha=0.72, linewidth=1.0)
        ax.semilogy(f2, np.maximum(p2, 1e-20), label="Multitaper", linewidth=1.45)
        ax.set_xlim(0.5, 45)
        ax.legend(loc="best")
        apply_final_v4_plot_style(
            ax,
            xlabel="Frecuencia (Hz)",
            ylabel="PSD (V^2/Hz)",
            title=f"Periodograma vs multitaper por estado: {label}",
        )
        name = f"fig_04_periodogram_vs_multitaper_{key}.png"
        savefig_final_v4(figures_dir / name)
        out[f"periodogram_vs_multitaper_{key}"] = name
    return out


def patch_base_generator() -> None:
    """Aplica estilo y figuras homogeneas al generador historico."""

    plt.rcParams.update(FINAL_V4_RCPARAMS)
    base.plt.rcParams.update(FINAL_V4_RCPARAMS)
    base.apply_tfg_plot_style = apply_final_v4_plot_style
    base._savefig = savefig_final_v4
    base.plot_state_timeseries_and_psd = plot_all_state_timeseries_and_psd
    base.plot_periodogram_vs_multitaper = plot_all_periodogram_vs_multitaper


def main() -> int:
    patch_base_generator()
    return int(base.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
