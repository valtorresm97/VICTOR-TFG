"""Regenera docs/validacion_tfg con estilo de figuras final-v4.

Este wrapper no cambia los calculos de `build_validation_docs.py`. Solo aplica una
capa de estilo Matplotlib mas segura para la memoria del TFG:

- titulos mas pequenos y envueltos automaticamente;
- margenes/bbox robustos para evitar textos fuera del PNG/PDF;
- leyendas con tamano moderado;
- salida con mas dpi y padding estable.

Uso recomendado desde la raiz del repo:

    python3 python/tools/build_validation_docs_final_v4_style.py \
      --captures captures \
      --output docs/validacion_tfg

La salida pisa las mismas figuras/documentos generados por `build_validation_docs.py`,
por lo que debe ejecutarse con `git status --short` limpio o con cambios controlados.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

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


def _wrap_title(title: str | None, width: int = 74) -> str:
    if not title:
        return ""
    return "\n".join(textwrap.wrap(str(title), width=width, break_long_words=False))


def apply_final_v4_plot_style(ax, xlabel: str | None = None, ylabel: str | None = None, title: str | None = None) -> None:
    """Estilo conservador para figuras de validacion TFG.

    Mantiene etiquetas descriptivas, evita titulos excesivamente grandes y deja
    espacio suficiente para ejes, leyendas y textos de timeline.
    """

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
        # Deja una franja superior para titulos y leyendas ancladas por encima.
        fig.tight_layout(rect=(0.02, 0.02, 0.98, 0.94), pad=1.35)
    except Exception:
        pass

    fig.savefig(path, dpi=220, bbox_inches="tight", pad_inches=0.18)
    try:
        fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", pad_inches=0.18)
    except Exception:
        pass
    plt.close(fig)


def patch_base_generator() -> None:
    """Aplica el estilo final-v4 al generador historico sin tocar sus calculos."""

    plt.rcParams.update(FINAL_V4_RCPARAMS)
    base.plt.rcParams.update(FINAL_V4_RCPARAMS)
    base.apply_tfg_plot_style = apply_final_v4_plot_style
    base._savefig = savefig_final_v4


def main() -> int:
    patch_base_generator()
    return int(base.main() or 0)


if __name__ == "__main__":
    raise SystemExit(main())
