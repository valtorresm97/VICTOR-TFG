from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


BANDS = ("delta", "theta", "alpha", "beta", "gamma")
BAND_RANGES = {
    "delta": "0.5-4 Hz",
    "theta": "4-8 Hz",
    "alpha": "8-13 Hz",
    "beta": "13-30 Hz",
    "gamma": "30-45 Hz (cautela)",
}


@dataclass
class CaptureSummary:
    name: str
    path: Path
    condition: str = ""
    duration_sec: float | None = None
    fs_hz: float | None = None
    samples: int | None = None
    channels: int | None = None
    diagnosis: str = "pendiente"
    rms_uv: float | None = None
    median_rms_uv: float | None = None
    p95_rms_uv: float | None = None
    best_window_rms_uv: float | None = None
    ptp_uv: float | None = None
    median_ptp_uv: float | None = None
    p95_ptp_uv: float | None = None
    line_50_ratio: float | None = None
    artifact_fraction: float | None = None
    sample_gaps: int | None = None
    invalid_status: int | None = None
    spectral_quality_median: float | None = None
    spectral_low_quality_fraction: float | None = None
    files: list[str] = field(default_factory=list)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "pendiente"
    try:
        f = float(value)
    except Exception:
        return str(value)
    if not math.isfinite(f):
        return "pendiente"
    if abs(f) >= 1000:
        return f"{f:.0f}"
    if abs(f) >= 100:
        return f"{f:.1f}"
    if abs(f) >= 10:
        return f"{f:.2f}"
    return f"{f:.{digits}f}"


def _safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if math.isfinite(out) else None


def _percent(value: float | None) -> str:
    if value is None:
        return "pendiente"
    return f"{100.0 * value:.1f}%"


def _load_capture_summary(capture_dir: Path) -> CaptureSummary:
    meta = _read_json(capture_dir / "metadata.json")
    quality = _read_json(capture_dir / "quality_report.json")
    spectral = _read_json(capture_dir / "spectral_validation_report.json")
    files = sorted(p.name for p in capture_dir.iterdir() if p.is_file())

    qmeta = quality.get("metadata") or {}
    ch1 = (quality.get("channels") or {}).get("ch1") or {}
    win = ch1.get("windowed") or {}
    status = quality.get("status") or {}
    timing = quality.get("timing") or {}
    rx_summary = meta.get("rx_summary") or {}
    qrx_summary = qmeta.get("rx_summary") or {}
    diagnosis = quality.get("diagnosis") or "pendiente"
    if isinstance(diagnosis, dict):
        diagnosis = diagnosis.get("state") or "pendiente"

    summary = CaptureSummary(
        name=capture_dir.name,
        path=capture_dir,
        condition=str(meta.get("condition") or qmeta.get("condition") or quality.get("condition") or capture_dir.name),
        duration_sec=_safe_float(
            quality.get("duration_observed_sec")
            or (quality.get("metadata") or {}).get("duration_observed_sec")
            or meta.get("duration_observed_sec")
            or meta.get("duration_requested_sec")
            or timing.get("duration_sec")
        ),
        fs_hz=_safe_float(quality.get("fs_effective_hz") or timing.get("effective_fs_hz") or meta.get("fs_hz_expected") or qmeta.get("fs_hz_expected")),
        samples=int(timing.get("samples_received") or status.get("samples_received") or rx_summary.get("rx_samples_total") or qrx_summary.get("rx_samples_total") or ch1.get("samples") or 0),
        channels=int(meta.get("num_channels") or qmeta.get("num_channels") or 4),
        diagnosis=str(diagnosis),
        rms_uv=_safe_float(ch1.get("rms_uV")),
        median_rms_uv=_safe_float(win.get("median_rms_uV")),
        p95_rms_uv=_safe_float(win.get("p95_rms_uV")),
        best_window_rms_uv=_safe_float(win.get("best_window_rms_uV")),
        ptp_uv=_safe_float(ch1.get("ptp_uV")),
        median_ptp_uv=_safe_float(win.get("median_ptp_uV")),
        p95_ptp_uv=_safe_float(win.get("p95_ptp_uV")),
        line_50_ratio=_safe_float(ch1.get("line_50_ratio_1_50")),
        artifact_fraction=_safe_float(win.get("artifact_window_fraction")),
        sample_gaps=int(status.get("sample_gaps_total") or timing.get("sample_gaps_detected") or rx_summary.get("sample_gaps_total") or qrx_summary.get("sample_gaps_total") or 0),
        invalid_status=int(status.get("invalid_status_total") or rx_summary.get("invalid_status_total") or qrx_summary.get("invalid_status_total") or 0),
        spectral_quality_median=_safe_float((spectral.get("quality") or {}).get("median_score")),
        spectral_low_quality_fraction=_safe_float((spectral.get("quality") or {}).get("artifact_fraction")),
        files=files,
    )
    return summary


def load_captures(captures_dir: Path) -> list[CaptureSummary]:
    captures: list[CaptureSummary] = []
    if not captures_dir.exists():
        return captures
    for path in sorted(p for p in captures_dir.iterdir() if p.is_dir() and p.name != "comparisons"):
        if (path / "metadata.json").exists() or (path / "quality_report.json").exists():
            captures.append(_load_capture_summary(path))
    return captures


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def _write_md_table(path: Path, headers: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_markdown_table(headers, rows) + "\n", encoding="utf-8")


def _read_timeseries(capture: CaptureSummary, max_samples: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    path = capture.path / "eeg_timeseries.csv"
    if not path.exists():
        return np.array([]), np.array([])
    t: list[float] = []
    ch1: list[float] = []
    fs = capture.fs_hz or 250.0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if max_samples is not None and i >= max_samples:
                break
            try:
                idx = float(row.get("sample_idx", i))
                value = float(row.get("ch1_uV", 0.0))
            except Exception:
                continue
            t.append(idx / fs)
            ch1.append(value)
    if t:
        t0 = t[0]
        t = [x - t0 for x in t]
    return np.asarray(t), np.asarray(ch1)


def _read_psd(capture: CaptureSummary) -> tuple[np.ndarray, np.ndarray]:
    path = capture.path / "psd_multitaper.csv"
    if not path.exists():
        return np.array([]), np.array([])
    freqs: list[float] = []
    psd: list[float] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                freqs.append(float(row.get("freq_hz", 0.0)))
                psd.append(float(row.get("psd_v2_per_hz", 0.0)))
            except Exception:
                continue
    return np.asarray(freqs), np.asarray(psd)


def _read_windowed_bandpowers(capture: CaptureSummary) -> list[dict[str, float]]:
    path = capture.path / "windowed_bandpowers.csv"
    if not path.exists():
        return []
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out: dict[str, float] = {}
            for key, value in row.items():
                try:
                    out[key] = float(value)
                except Exception:
                    pass
            rows.append(out)
    return rows


def _select(captures: list[CaptureSummary], contains: str) -> CaptureSummary | None:
    contains_l = contains.lower()
    for cap in captures:
        if contains_l in cap.name.lower() or contains_l in cap.condition.lower():
            return cap
    return None


def _savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def generate_figures(captures: list[CaptureSummary], figures_dir: Path) -> dict[str, str]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    figs: dict[str, str] = {}

    shorted = _select(captures, "shorted_inputs")
    test_or_final = _select(captures, "final_atenuacion") or _select(captures, "live_dsp")
    jaw = _select(captures, "jaw_movement")
    fp_open = _select(captures, "fp1_fp2_ch1_only_eyes_open")
    fp_closed = _select(captures, "fp1_fp2_ch1_only_eyes_closed")
    ear_open = _select(captures, "ear_eeg_ch1_only_eyes_open")
    ear_closed = _select(captures, "ear_eeg_ch1_only_eyes_closed")

    if shorted:
        t, x = _read_timeseries(shorted, max_samples=2500)
        if t.size:
            plt.figure(figsize=(8, 3.2))
            plt.plot(t, x, linewidth=0.8)
            plt.title("Señal temporal en modo shorted_inputs")
            plt.xlabel("Tiempo (s)")
            plt.ylabel("CH1 (µV)")
            figs["shorted_timeseries"] = "fig_01_shorted_inputs_timeseries.png"
            _savefig(figures_dir / figs["shorted_timeseries"])

        f, p = _read_psd(shorted)
        if f.size:
            plt.figure(figsize=(8, 3.2))
            plt.semilogy(f, np.maximum(p, 1e-20))
            plt.title("PSD multitaper en modo shorted_inputs")
            plt.xlabel("Frecuencia (Hz)")
            plt.ylabel("PSD (V²/Hz)")
            plt.xlim(0, 60)
            figs["shorted_psd"] = "fig_02_shorted_inputs_psd.png"
            _savefig(figures_dir / figs["shorted_psd"])

    if test_or_final:
        t, x = _read_timeseries(test_or_final, max_samples=7500)
        if t.size:
            plt.figure(figsize=(8, 3.2))
            plt.plot(t, x, linewidth=0.7)
            plt.title(f"Señal temporal real: {test_or_final.condition}")
            plt.xlabel("Tiempo (s)")
            plt.ylabel("CH1 (µV)")
            figs["final_timeseries"] = "fig_03_final_capture_timeseries.png"
            _savefig(figures_dir / figs["final_timeseries"])

    usable = [c for c in captures if c.median_rms_uv is not None]
    if usable:
        labels = [c.condition[:28] for c in usable]
        values = [c.median_rms_uv or 0.0 for c in usable]
        plt.figure(figsize=(10, 5))
        plt.barh(labels, values)
        plt.title("Comparación RMS mediano por ventanas")
        plt.xlabel("RMS mediano CH1 (µV)")
        figs["rms_comparison"] = "fig_04_rms_comparison.png"
        _savefig(figures_dir / figs["rms_comparison"])

        values = [c.p95_ptp_uv or c.ptp_uv or 0.0 for c in usable]
        plt.figure(figsize=(10, 5))
        plt.barh(labels, values)
        plt.title("Comparación pico-pico p95 por ventanas")
        plt.xlabel("Pico-pico p95 CH1 (µV)")
        figs["ptp_comparison"] = "fig_05_ptp_comparison.png"
        _savefig(figures_dir / figs["ptp_comparison"])

        values = [c.line_50_ratio or 0.0 for c in usable]
        plt.figure(figsize=(10, 5))
        plt.barh(labels, values)
        plt.title("Comparación de ratio de ruido 50 Hz")
        plt.xlabel("Ratio potencia 50 Hz / 1-50 Hz")
        figs["line50_comparison"] = "fig_06_50hz_comparison.png"
        _savefig(figures_dir / figs["line50_comparison"])

    alpha_pairs = [(ear_open, ear_closed, "ear-EEG"), (fp_open, fp_closed, "Fp1-Fp2")]
    pair_rows = []
    for open_cap, closed_cap, label in alpha_pairs:
        if open_cap and closed_cap:
            open_spec = _read_json(open_cap.path / "spectral_validation_report.json")
            closed_spec = _read_json(closed_cap.path / "spectral_validation_report.json")
            open_alpha = (((open_spec.get("bands") or {}).get("alpha") or {}).get("relative") or {}).get("median")
            closed_alpha = (((closed_spec.get("bands") or {}).get("alpha") or {}).get("relative") or {}).get("median")
            if open_alpha is not None and closed_alpha is not None:
                pair_rows.append((label, float(open_alpha), float(closed_alpha)))
    if pair_rows:
        x = np.arange(len(pair_rows))
        width = 0.35
        plt.figure(figsize=(7, 4))
        plt.bar(x - width / 2, [r[1] for r in pair_rows], width, label="Ojos abiertos")
        plt.bar(x + width / 2, [r[2] for r in pair_rows], width, label="Ojos cerrados")
        plt.xticks(x, [r[0] for r in pair_rows])
        plt.title("Alpha relativo: ojos abiertos vs ojos cerrados")
        plt.ylabel("alpha_rel mediano")
        plt.legend()
        figs["alpha_open_closed"] = "fig_07_eyes_open_vs_closed_alpha.png"
        _savefig(figures_dir / figs["alpha_open_closed"])

    final_cap = test_or_final
    if final_cap:
        rows = _read_windowed_bandpowers(final_cap)
        if rows:
            t = [r.get("window_start_sec", 0.0) for r in rows]
            plt.figure(figsize=(10, 4))
            for band in BANDS:
                plt.plot(t, [r.get(f"{band}_rel", 0.0) for r in rows], label=band, linewidth=0.9)
            plt.title(f"Evolución temporal de bandpowers relativos: {final_cap.condition}")
            plt.xlabel("Tiempo (s)")
            plt.ylabel("Bandpower relativo")
            plt.legend(ncol=5, fontsize=8)
            figs["windowed_bandpowers"] = "fig_08_windowed_bandpowers.png"
            _savefig(figures_dir / figs["windowed_bandpowers"])

    if jaw:
        t, x = _read_timeseries(jaw, max_samples=7500)
        if t.size:
            plt.figure(figsize=(8, 3.2))
            plt.plot(t, x, linewidth=0.7)
            plt.title("Señal temporal durante movimiento mandibular")
            plt.xlabel("Tiempo (s)")
            plt.ylabel("CH1 (µV)")
            figs["jaw_timeseries"] = "fig_09_jaw_movement_timeseries.png"
            _savefig(figures_dir / figs["jaw_timeseries"])
        f, p = _read_psd(jaw)
        if f.size:
            plt.figure(figsize=(8, 3.2))
            plt.semilogy(f, np.maximum(p, 1e-20))
            plt.title("PSD multitaper durante movimiento mandibular")
            plt.xlabel("Frecuencia (Hz)")
            plt.ylabel("PSD (V²/Hz)")
            plt.xlim(0, 60)
            figs["jaw_psd"] = "fig_10_jaw_emg_psd.png"
            _savefig(figures_dir / figs["jaw_psd"])

    if final_cap:
        sonif_path = final_cap.path / "windowed_sonification_features.csv"
        if sonif_path.exists():
            counts: dict[str, int] = {}
            with sonif_path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    state = row.get("quality_state") or "pendiente"
                    counts[state] = counts.get(state, 0) + 1
            if counts:
                plt.figure(figsize=(7, 4))
                plt.bar(list(counts), list(counts.values()))
                plt.title("Distribución de estados del spectral_quality_score")
                plt.ylabel("Ventanas")
                plt.xticks(rotation=20, ha="right")
                figs["quality_states"] = "fig_11_quality_state_distribution.png"
                _savefig(figures_dir / figs["quality_states"])

    return figs


def generate_tables(captures: list[CaptureSummary], tables_dir: Path) -> dict[str, str]:
    tables_dir.mkdir(parents=True, exist_ok=True)
    table_files: dict[str, str] = {}

    inventory_rows = []
    for c in captures:
        inventory_rows.append(
            {
                "capture": c.name,
                "condition": c.condition,
                "duration_sec": _fmt(c.duration_sec),
                "fs_hz": _fmt(c.fs_hz),
                "channels": c.channels,
                "samples": c.samples,
                "files_available": ";".join(c.files),
                "diagnosis": c.diagnosis,
                "median_rms_uV": _fmt(c.median_rms_uv),
                "p95_rms_uV": _fmt(c.p95_rms_uv),
                "ptp_uV": _fmt(c.ptp_uv),
                "line_50_ratio": _fmt(c.line_50_ratio),
                "artifact_fraction": _percent(c.artifact_fraction),
                "spectral_quality_median": _fmt(c.spectral_quality_median),
                "use_in_docs": _classify_use(c),
            }
        )
    _write_csv(tables_dir / "table_01_capture_summary.csv", inventory_rows)
    table_files["capture_summary"] = "table_01_capture_summary.csv"
    _write_md_table(
        tables_dir / "table_01_capture_summary.md",
        ["Captura", "Condición", "Duración", "Calidad", "RMS med.", "Artefactos", "Uso"],
        [
            [
                r["capture"],
                r["condition"],
                r["duration_sec"],
                r["diagnosis"],
                r["median_rms_uV"],
                r["artifact_fraction"],
                r["use_in_docs"],
            ]
            for r in inventory_rows
        ],
    )

    mounting = []
    for c in captures:
        cond_l = c.condition.lower()
        if any(k in cond_l for k in ("fp1", "ear", "mastoid", "rld", "bias", "quiet", "eyes")):
            mounting.append(
                {
                    "mounting_or_condition": c.condition,
                    "capture": c.name,
                    "median_rms_uV": _fmt(c.median_rms_uv),
                    "ptp_uV": _fmt(c.ptp_uv),
                    "line_50_ratio": _fmt(c.line_50_ratio),
                    "artifact_fraction": _percent(c.artifact_fraction),
                    "conclusion": _mounting_conclusion(c),
                }
            )
    _write_csv(tables_dir / "table_02_mounting_comparison.csv", mounting)
    table_files["mounting_comparison"] = "table_02_mounting_comparison.csv"

    ads_rows = []
    for key in ("shorted_inputs", "test_signal_internal"):
        cap = _select(captures, key)
        if cap:
            ads_rows.append(
                {
                    "test": key,
                    "capture": cap.name,
                    "fs_hz": _fmt(cap.fs_hz),
                    "sample_gaps": cap.sample_gaps,
                    "invalid_status": cap.invalid_status,
                    "rms_uV": _fmt(cap.rms_uv),
                    "ptp_uV": _fmt(cap.ptp_uv),
                    "result": cap.diagnosis,
                }
            )
    if not any(r["test"] == "test_signal_internal" for r in ads_rows):
        ads_rows.append(
            {
                "test": "test_signal_internal",
                "capture": "pendiente en rama actual",
                "fs_hz": "pendiente",
                "sample_gaps": "pendiente",
                "invalid_status": "pendiente",
                "rms_uV": "pendiente",
                "ptp_uV": "pendiente",
                "result": "descrito en conversación, CSV no versionado en esta rama",
            }
        )
    _write_csv(tables_dir / "table_03_ads1299_validation_summary.csv", ads_rows)
    table_files["ads1299_validation"] = "table_03_ads1299_validation_summary.csv"

    final_cap = _select(captures, "final_atenuacion") or _select(captures, "live_dsp")
    band_rows = _band_validation_rows(final_cap)
    _write_csv(tables_dir / "table_04_spectral_band_validation.csv", band_rows)
    table_files["band_validation"] = "table_04_spectral_band_validation.csv"

    sonif_rows = [
        {
            "musical_parameter": "Densidad rítmica",
            "recommended_feature": "activity + RMS normalizado + quality gate",
            "evidence": "cambia con energía de señal; el gate reduce ventanas malas",
            "risk": "puede aumentar con EMG/movimiento",
            "treatment": "suavizado, histéresis y atenuación por calidad",
        },
        {
            "musical_parameter": "Calma",
            "recommended_feature": "alpha_rel / alpha_beta_ratio",
            "evidence": "alpha validado mejor en ear-EEG que en Fp1-Fp2",
            "risk": "alpha no siempre robusto en montaje frontal",
            "treatment": "usar con suavizado y normalización por sesión",
        },
        {
            "musical_parameter": "Tensión",
            "recommended_feature": "beta_rel con apoyo de fast_power",
            "evidence": "beta varía, pero puede contener EMG",
            "risk": "mandíbula/frente contaminan beta/gamma",
            "treatment": "no usar sin quality gate; peso moderado",
        },
        {
            "musical_parameter": "Registro",
            "recommended_feature": "peak_freq estable + bandas relativas",
            "evidence": "peak_freq puede cambiar entre condiciones",
            "risk": "picos espurios por artefacto o 50 Hz",
            "treatment": "limitar rango y suavizar",
        },
        {
            "musical_parameter": "Probabilidad de nota",
            "recommended_feature": "rhythmic_density atenuada por calidad",
            "evidence": "ventanas bad se bloquean en captura final",
            "risk": "repetición excesiva de eventos",
            "treatment": "gate + duración mínima + lógica musical posterior",
        },
    ]
    _write_csv(tables_dir / "table_05_sonification_feature_decisions.csv", sonif_rows)
    table_files["sonification_decisions"] = "table_05_sonification_feature_decisions.csv"
    return table_files


def _classify_use(c: CaptureSummary) -> str:
    name = c.name.lower()
    if "shorted" in name:
        return "validación ADC/SPI/escala"
    if "final_atenuacion" in name or "live_dsp" in name:
        return "validación DSP/quality gate"
    if "ear_eeg" in name:
        return "montaje final y bandas"
    if "fp1_fp2" in name:
        return "comparación frontal"
    if "jaw" in name or "blink" in name:
        return "artefactos"
    return "contexto"


def _mounting_conclusion(c: CaptureSummary) -> str:
    cond = c.condition.lower()
    if "ear_eeg" in cond:
        return "montaje más estable en capturas versionadas"
    if "fp1_fp2" in cond and c.artifact_fraction is not None and c.artifact_fraction > 0.05:
        return "plausible pero sensible a artefactos"
    if "bias" in cond or "rld" in cond:
        return "mejora frente a capturas iniciales sin control común"
    return "evidencia complementaria"


def _band_validation_rows(final_cap: CaptureSummary | None) -> list[dict[str, Any]]:
    default = {
        "delta": ("USAR SOLO COMO APOYO", "drift, parpadeo o movimiento"),
        "theta": ("USAR SOLO COMO APOYO", "drift, parpadeo o somnolencia no controlada"),
        "alpha": ("NECESITA MÁS CAPTURAS", "requiere comparación open/closed robusta"),
        "beta": ("USAR SOLO COMO APOYO", "contaminación EMG"),
        "gamma": ("NO USAR EN TIEMPO REAL", "muy sensible a EMG/ruido superficial"),
    }
    spectral = _read_json(final_cap.path / "spectral_validation_report.json") if final_cap else {}
    bands = spectral.get("bands") or {}
    rows = []
    for band in BANDS:
        info = bands.get(band) or {}
        rel = info.get("relative") or {}
        decision, risk = default[band]
        rows.append(
            {
                "band": band,
                "range": BAND_RANGES[band],
                "median_rel_final_capture": _fmt(rel.get("median")),
                "p95_rel_final_capture": _fmt(rel.get("p95")),
                "evidence": "captura final con quality gate" if final_cap else "pendiente",
                "artifact_risk": info.get("risk") or risk,
                "robustness": _band_robustness(band),
                "decision": info.get("decision") or decision,
            }
        )
    return rows


def _band_robustness(band: str) -> str:
    return {
        "delta": "media-baja",
        "theta": "media-baja",
        "alpha": "media en ear-EEG; baja en Fp1-Fp2",
        "beta": "media con quality gate",
        "gamma": "baja",
    }[band]


def _doc_header(title: str) -> str:
    return f"# {title}\n\nGenerado automáticamente por `python/tools/build_validation_docs.py`.\n\n"


def generate_docs(captures: list[CaptureSummary], output_dir: Path, figs: dict[str, str], tables: dict[str, str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    final_cap = _select(captures, "final_atenuacion") or _select(captures, "live_dsp")
    shorted = _select(captures, "shorted_inputs")
    ear_open = _select(captures, "ear_eeg_ch1_only_eyes_open")
    ear_closed = _select(captures, "ear_eeg_ch1_only_eyes_closed")
    fp_open = _select(captures, "fp1_fp2_ch1_only_eyes_open")
    fp_closed = _select(captures, "fp1_fp2_ch1_only_eyes_closed")

    _write(output_dir / "00_resumen_validacion.md", _doc_00(captures, final_cap))
    _write(output_dir / "01_validacion_captura_datos_ads1299.md", _doc_01(shorted, figs))
    _write(output_dir / "02_validacion_montaje_electrodos_bias_rld.md", _doc_02(captures, figs))
    _write(output_dir / "03_validacion_calidad_senal_real.md", _doc_03(captures, final_cap, figs))
    _write(output_dir / "04_validacion_dsp_multitaper.md", _doc_04(final_cap, figs))
    _write(output_dir / "05_validacion_bandas_eeg_y_features.md", _doc_05(final_cap, ear_open, ear_closed, fp_open, fp_closed, figs))
    _write(output_dir / "06_conclusiones_para_sonificacion.md", _doc_06(final_cap))
    _write(output_dir / "07_protocolo_final_adquisicion.md", _doc_07())
    _write(output_dir / "08_historial_ramas_y_cambios.md", _doc_08())


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _doc_00(captures: list[CaptureSummary], final_cap: CaptureSummary | None) -> str:
    rows = [
        ["ADS1299/SPI/RDATAC", "ID 0x3C, status 0xC00000, shorted_inputs", "sin gaps/invalid status en capturas versionadas", "razonablemente validado"],
        ["Bridge MCU-Python", "capturas CSV con 250 Hz y bloques de 8", "streaming estable", "validado en condiciones probadas"],
        ["Montaje electrodos", "Fp1-Fp2, ear-EEG, BIAS/RLD", "ear-EEG y CH1-only más estables", "montaje final definido"],
        ["DSP multitaper", "windowed PSD, bandpowers, quality score", "features reproducibles offline", "validado para diagnóstico"],
        ["Sonificación", "quality gate y controles espectrales", "atenuación funciona; diseño musical pendiente", "siguiente fase"],
    ]
    text = _doc_header("00. Resumen general de validación")
    text += (
        "La validación se realizó antes de diseñar la sonificación final para separar tres problemas: "
        "la adquisición física de la señal, la extracción espectral de características y la respuesta musical. "
        "Esta separación evita atribuir a la música errores que podrían venir del ADC, del firmware o del montaje de electrodos.\n\n"
        f"En la rama documentada se dispone de {len(captures)} capturas versionadas con informes asociados. "
        "Las pruebas internas y reales indican que la cadena ADS1299 -> SPI -> firmware -> Bridge -> Python funciona "
        "sin pérdidas temporales apreciables en las capturas principales. Las limitaciones restantes se asocian sobre todo "
        "a artefactos biológicos o mecánicos: mandíbula, frente, contacto de electrodos, movimiento de cables y ruido común.\n\n"
    )
    if final_cap:
        text += (
            f"La captura final `{final_cap.name}` resume el estado alcanzado: fs={_fmt(final_cap.fs_hz)} Hz, "
            f"gaps={final_cap.sample_gaps}, invalid_status={final_cap.invalid_status}, "
            f"RMS mediano por ventanas={_fmt(final_cap.median_rms_uv)} µV y "
            f"quality score mediano={_fmt(final_cap.spectral_quality_median)}.\n\n"
        )
    text += _markdown_table(["Bloque validado", "Pruebas realizadas", "Resultado", "Estado final"], rows)
    text += "\n\nQueda fuera del alcance de estos documentos el diseño sonoro definitivo. La evidencia aquí recogida sirve como base para esa fase posterior.\n"
    text += "\nTabla de inventario: [`tables/table_01_capture_summary.csv`](tables/table_01_capture_summary.csv).\n"
    text += "\nLa evolución de ramas, commits y decisiones de esta conversación se documenta en [`08_historial_ramas_y_cambios.md`](08_historial_ramas_y_cambios.md).\n"
    return text


def _doc_01(shorted: CaptureSummary | None, figs: dict[str, str]) -> str:
    text = _doc_header("01. Validación de captura de datos ADS1299")
    text += (
        "La arquitectura de adquisición validada es:\n\n"
        "```text\nElectrodos\n   ↓\nADS1299-4PAG\n   ↓\nSPI / DRDY / RDATAC\n   ↓\nArduino UNO Q MCU\n   ↓\nBridge\n   ↓\nPython backend\n   ↓\nCSV / DSP / UI\n```\n\n"
        "El firmware reconstruye frames RDATAC de 24 bits, valida el prefijo de estado `0xC00000`, convierte cuentas a voltios "
        "mediante el LSB configurado y envía bloques `eeg_block_uV` de 8 muestras. Los CSV analizados contienen la señal ya en microvoltios.\n\n"
    )
    if shorted:
        text += (
            f"La prueba interna `{shorted.name}` se empleó para aislar el ADC y la ruta digital de los electrodos. "
            f"Su diagnóstico fue `{shorted.diagnosis}`, con fs={_fmt(shorted.fs_hz)} Hz, "
            f"gaps={shorted.sample_gaps}, invalid_status={shorted.invalid_status}, "
            f"RMS={_fmt(shorted.rms_uv)} µV y pico-pico={_fmt(shorted.ptp_uv)} µV. "
            "Estos valores son coherentes con una cadena digital sana y ruido interno bajo.\n\n"
        )
    else:
        text += "No se dispone en esta rama de una captura `shorted_inputs`; este punto queda pendiente en los artefactos versionados.\n\n"
    text += "La prueba `test_signal_internal` se usó durante la conversación para confirmar el test interno del ADS1299, pero su CSV no está versionado en esta rama; se marca como evidencia descrita y pendiente de incorporar si se necesita trazabilidad completa.\n\n"
    for key in ("shorted_timeseries", "shorted_psd"):
        if key in figs:
            text += f"![{key}](figures/{figs[key]})\n\n"
    text += "Tabla resumen: [`tables/table_03_ads1299_validation_summary.csv`](tables/table_03_ads1299_validation_summary.csv).\n"
    text += "\nConclusión: bajo las capturas versionadas, la ruta ADC/SPI/Bridge/Python queda razonablemente validada; los problemas posteriores no se explican por gaps, status inválido ni fallo de streaming.\n"
    return text


def _doc_02(captures: list[CaptureSummary], figs: dict[str, str]) -> str:
    text = _doc_header("02. Validación del montaje de electrodos, BIAS y RLD")
    text += (
        "El montaje inicial Fp1-Fp2 permitió observar actividad frontal, pero mostró sensibilidad a contacto, movimiento y ruido común. "
        "La activación de BIAS/RLD y el paso a modos `bias_ch1pn_loff_off` y posteriormente `bias_ch1_only_loff_off` redujeron la influencia de canales no usados y facilitaron capturas más estables.\n\n"
        "La evidencia versionada muestra dos familias útiles: Fp1-Fp2, más expresiva frente a parpadeo/frente pero menos robusta, y ear-EEG/mastoides, más estable para validación de reposo y cambios de estado. "
        "El montaje final de diagnóstico usa CH1 activo, BIAS derivado de CH1P+CH1N y lead-off desactivado.\n\n"
    )
    for key in ("rms_comparison", "ptp_comparison", "line50_comparison", "final_timeseries"):
        if key in figs:
            text += f"![{key}](figures/{figs[key]})\n\n"
    text += "Comparación de montajes: [`tables/table_02_mounting_comparison.csv`](tables/table_02_mounting_comparison.csv).\n\n"
    text += (
        "Conclusión: el montaje final no elimina los artefactos biológicos, pero ofrece una base suficientemente estable para analizar ventanas limpias. "
        "La elección se justifica por estabilidad temporal, ausencia de gaps y respuesta clara ante artefactos controlados.\n"
    )
    return text


def _doc_03(captures: list[CaptureSummary], final_cap: CaptureSummary | None, figs: dict[str, str]) -> str:
    text = _doc_header("03. Validación de calidad de señal real")
    text += (
        "La calidad de señal real se evaluó con métricas globales y por ventanas. Las métricas globales detectan artefactos grandes, "
        "mientras que las ventanas permiten distinguir una captura parcialmente válida de una captura completamente mala.\n\n"
        "Criterios utilizados:\n\n"
        "- señal válida: 250 Hz efectivo, sample gaps 0, invalid status 0, RMS mediano plausible y baja fracción de ventanas artefactadas;\n"
        "- señal dudosa: transporte correcto pero RMS/PTP o 50 Hz altos en una parte relevante de la captura;\n"
        "- señal no válida: gaps, status inválido persistente, saturación, flatline o artefactos dominantes que impiden extraer ventanas limpias.\n\n"
    )
    if final_cap:
        text += (
            f"En la captura final `{final_cap.name}` se observó `{final_cap.diagnosis}`. "
            f"El RMS global fue {_fmt(final_cap.rms_uv)} µV, pero el RMS mediano por ventanas fue {_fmt(final_cap.median_rms_uv)} µV, "
            f"lo que indica que el valor global está influido por transitorios. La fracción de ventanas artefactadas fue {_percent(final_cap.artifact_fraction)} "
            f"y la calidad espectral mediana fue {_fmt(final_cap.spectral_quality_median)}.\n\n"
        )
    for key in ("final_timeseries", "jaw_timeseries", "jaw_psd", "quality_states"):
        if key in figs:
            text += f"![{key}](figures/{figs[key]})\n\n"
    text += "Inventario completo: [`tables/table_01_capture_summary.csv`](tables/table_01_capture_summary.csv).\n"
    return text


def _doc_04(final_cap: CaptureSummary | None, figs: dict[str, str]) -> str:
    text = _doc_header("04. Validación DSP y multitaper")
    text += (
        "El pipeline DSP analizado es:\n\n"
        "```text\neeg_timeseries.csv / stream live\n   ↓\nventana temporal\n   ↓\nPSD multitaper\n   ↓\nbandpowers absolutos y relativos\n   ↓\nfeatures espectrales\n   ↓\nquality gate / sonificación\n```\n\n"
        "Multitaper se mantiene porque reduce leakage y variabilidad de borde frente a un periodograma simple en ventanas EEG cortas. "
        "No sustituye al buen contacto de electrodos, no corrige saturación y no separa por sí solo EMG de EEG; por eso se añadió `spectral_quality_score`.\n\n"
        "La configuración de validación usa fs cercano a 250 Hz, ventanas de 4 s y hop de 64 muestras. Esto da una resolución aproximada de 0.25 Hz, "
        "suficiente para resumir bandas delta/theta/alpha/beta/gamma con una latencia aceptable para sonificación lenta.\n\n"
    )
    if final_cap:
        text += (
            f"En `{final_cap.name}`, el informe espectral produjo { _fmt(final_cap.spectral_quality_median) } de calidad mediana y "
            f"{_percent(final_cap.spectral_low_quality_fraction)} de ventanas de baja calidad/artefacto.\n\n"
        )
    for key in ("windowed_bandpowers", "quality_states"):
        if key in figs:
            text += f"![{key}](figures/{figs[key]})\n\n"
    text += "Conclusión: el DSP queda validado para extracción de características bajo ventanas limpias o controladas; las ventanas artefactadas deben atenuarse o excluirse.\n"
    return text


def _doc_05(final_cap: CaptureSummary | None, ear_open: CaptureSummary | None, ear_closed: CaptureSummary | None, fp_open: CaptureSummary | None, fp_closed: CaptureSummary | None, figs: dict[str, str]) -> str:
    text = _doc_header("05. Validación de bandas EEG y features espectrales")
    text += (
        "Las bandas se interpretan como features de sonificación, no como diagnóstico clínico. "
        "La validación distingue presencia espectral, robustez temporal y riesgo de artefacto.\n\n"
        "La comparación ojos abiertos/cerrados fue más favorable en ear-EEG que en Fp1-Fp2. En Fp1-Fp2, la alfa clásica puede no aparecer de forma robusta por tratarse de un montaje frontal, con mayor contribución ocular y muscular.\n\n"
    )
    if ear_open and ear_closed:
        text += f"Ear-EEG disponible: `{ear_open.name}` y `{ear_closed.name}`.\n\n"
    if fp_open and fp_closed:
        text += f"Fp1-Fp2 disponible: `{fp_open.name}` y `{fp_closed.name}`.\n\n"
    for key in ("alpha_open_closed", "windowed_bandpowers"):
        if key in figs:
            text += f"![{key}](figures/{figs[key]})\n\n"
    text += "Tabla de decisión por banda: [`tables/table_04_spectral_band_validation.csv`](tables/table_04_spectral_band_validation.csv).\n\n"
    text += (
        "Decisiones principales: delta/theta se usan solo como apoyo por sensibilidad a drift y parpadeo; alpha requiere normalización y comparación por sesión; "
        "beta puede aportar tensión con cautela; gamma no debe controlar directamente la sonificación en tiempo real por riesgo EMG.\n"
    )
    return text


def _doc_06(final_cap: CaptureSummary | None) -> str:
    text = _doc_header("06. Conclusiones para sonificación")
    text += (
        "La validación indica que la sonificación debe apoyarse en features relativas y suavizadas, no en potencias absolutas crudas. "
        "El `quality gate` debe actuar antes de disparar eventos musicales para evitar que mandíbula, frente o cableado se traduzcan directamente en más notas.\n\n"
        "La observación musical posterior indica que la respuesta sin atenuación puede resultar interesante, pero tiende a repetir pulsos de acordes. "
        "Esto no se atribuye al DSP, sino a la lógica musical: falta duración mínima de acordes, histéresis y separación entre armonía lenta y notas/arpegios.\n\n"
    )
    if final_cap:
        text += (
            f"La captura final respalda esta estrategia: { _percent(final_cap.spectral_low_quality_fraction) } de ventanas fueron marcadas como baja calidad/artefacto "
            "y por tanto no deberían generar cambios musicales fuertes.\n\n"
        )
    text += "Matriz de decisiones: [`tables/table_05_sonification_feature_decisions.csv`](tables/table_05_sonification_feature_decisions.csv).\n"
    return text


def _doc_07() -> str:
    text = _doc_header("07. Protocolo final de adquisición")
    text += (
        "Rama recomendada para diagnóstico final:\n\n"
        "```bash\ncd /home/arduino/ArduinoApps/eeg_midi\ngit switch diagnosis/sonificacion-atenuacion-artefactos\ngit pull --ff-only\n```\n\n"
        "Después de cambiar de rama se debe ejecutar Run/compile en App Lab. El modo por defecto esperado es `bias_ch1_only_loff_off`.\n\n"
        "Montaje recomendado: CH1 activo con electrodos colocados en configuración ear-EEG/mastoides o Fp1-Fp2 según la prueba, BIAS derivado de CH1P+CH1N y RLD/BIAS con contacto estable. "
        "Antes de grabar, fijar cables, minimizar movimiento mandibular y verificar que la UI muestra RMS plausible.\n\n"
        "Comandos de captura y análisis:\n\n"
        "```bash\npython3 python/tools/capture_eeg_quality.py --condition final_atenuacion_artefactos_mixed_states --duration 190 --timeout-extra 260\nDIR=$(ls -td captures/*_final_atenuacion_artefactos_mixed_states /app/captures/*_final_atenuacion_artefactos_mixed_states 2>/dev/null | head -1)\npython3 python/tools/analyze_eeg_capture.py \"$DIR\"\npython3 python/tools/validate_spectral_features.py \"$DIR\" --channel 0 --window-sec 4 --hop-samples 64\ncat \"$DIR/quality_report.md\"\ncat \"$DIR/spectral_validation_report.md\"\n```\n\n"
        "Aceptar una captura si no hay sample gaps ni invalid status, la frecuencia efectiva es cercana a 250 Hz, existen ventanas limpias y la fracción de artefactos es compatible con el objetivo. "
        "Rechazar o repetir si hay saturación persistente, RMS de mV en la mayoría de ventanas, 50 Hz dominante o señal plana.\n\n"
        "Si aparece mucho 50 Hz, revisar contacto, cableado y entorno. Si el RMS o pico-pico es excesivo, repetir con postura quieta y cables fijados. Si alpha no aparece, no forzar conclusión: puede depender del montaje y del sujeto.\n"
    )
    return text


def _doc_08() -> str:
    text = _doc_header("08. Historial de ramas y cambios realizados durante la validación")
    text += (
        "Este documento resume la evolución técnica realizada durante la fase de validación. "
        "No sustituye al historial Git, sino que lo traduce a decisiones de ingeniería justificables en el TFG. "
        "La rama de referencia para esta recopilación es `diagnosis/sonificacion-atenuacion-artefactos`.\n\n"
        "## Secuencia general\n\n"
        "La conversación comenzó con un sistema que ya comunicaba con el ADS1299, pero todavía necesitaba separar tres fuentes de incertidumbre: "
        "la cadena digital de adquisición, el montaje bioeléctrico real y la robustez de las features espectrales para sonificación. "
        "La estrategia fue avanzar por capas: primero validar ADC/SPI/Bridge/Python, después el montaje BIAS/RLD, después el DSP multitaper, "
        "y finalmente crear ramas de diagnóstico para comparar sonificación con y sin atenuación de artefactos.\n\n"
    )
    text += _markdown_table(
        ["Etapa", "Rama/commit representativo", "Cambio técnico", "Motivo", "Evidencia generada"],
        [
            [
                "Captura requestable desde la placa",
                "`3be73e1`, `f5f9516`",
                "`capture_eeg_quality.py` permite pedir capturas desde shell y analizarlas con paquetes disponibles en App Lab.",
                "Evitar depender de observaciones visuales y guardar CSV trazables.",
                "`eeg_timeseries.csv`, `metadata.json`, `quality_report.*` por captura.",
            ],
            [
                "Auditoría y diagnóstico de adquisición",
                "`9b5be72`, `34ecc8e`",
                "Herramientas de auditoría y comparación de capturas open/closed.",
                "Medir gaps, status, RMS, pico-pico, 50 Hz y respuesta por condición.",
                "`eyes_open_closed_comparison.*` y reportes de calidad.",
            ],
            [
                "Modos diagnósticos ADS1299",
                "`ebea8f8`, `61cf262`",
                "Se añaden `shorted_inputs` y `test_signal_internal` para aislar ADC/SPI/escala.",
                "Separar problemas digitales de problemas de electrodos o referencia común.",
                "`shorted_inputs` con ruido muy bajo; test interno estable.",
            ],
            [
                "Corrección de registros ADS1299",
                "`e0f8437`, `924783f`",
                "Auditoría de CONFIG1/CONFIG3 y preservación de bits reservados/fijos.",
                "Alinear configuración con datasheet y evitar valores como `0x86` o `0x8C` que no preservaban bits esperados.",
                "`docs/ads1299_register_audit_bias_drl.md`.",
            ],
            [
                "BIAS/RLD y CH1-only",
                "`c6830c4`, `06f92f7`",
                "Modos `bias_ch1pn_loff_off` y `bias_ch1_only_loff_off`; diagnósticos multicanal.",
                "Reducir común, apagar canales no usados y estabilizar el montaje más útil.",
                "Capturas ear-EEG y Fp1-Fp2 con RMS por ventanas plausible.",
            ],
            [
                "Métricas por ventanas",
                "`aca2ebc`",
                "Se añaden `median_rms_uV`, `p95_rms_uV`, `best_window_rms_uV`, `artifact_window_fraction`.",
                "No rechazar capturas completas por transitorios si existen ventanas limpias.",
                "`quality_report.md/json` más interpretables.",
            ],
            [
                "Documentación de captura",
                "`d3ed1f1`",
                "Primer documento de validación de captura de datos.",
                "Convertir resultados de pruebas en texto reutilizable para TFG.",
                "`docs/validacion_de_la_captura_de_datos.md`.",
            ],
            [
                "Validación espectral offline",
                "`73e2dc6`, `aa60128`",
                "`validate_spectral_features.py`, bandpowers por ventana, PSD multitaper, informes espectrales.",
                "Validar que las bandas y features se comportan de forma reproducible con CSV reales.",
                "`windowed_bandpowers.csv`, `spectral_validation_report.*`.",
            ],
            [
                "Capturas reales versionadas",
                "`91899a6`, `3c42354`",
                "Se suben capturas representativas: shorted, ear-EEG, Fp1-Fp2, mandíbula, frente y sesión mixta.",
                "Permitir análisis local y documentación sin depender de texto pegado.",
                "Carpeta `captures/` versionada.",
            ],
            [
                "Análisis DSP mixto",
                "`7789a79`",
                "Segmentación de protocolo mixto y evaluación de estados.",
                "Comprobar funcionamiento real del DSP durante cambios de estado y artefactos.",
                "`docs/resultados_validacion_dsp_mixta.md`.",
            ],
            [
                "Rama base DSP",
                "`captura-datos-dsp`, `02d5f43`",
                "Se fija `ADS_DIAGNOSTIC_MODE=5` (`bias_ch1_only_loff_off`) como modo por defecto.",
                "Establecer una base común para comparar sonificación con y sin atenuación.",
                "Rama `captura-datos-dsp` subida al remoto.",
            ],
            [
                "Rama sin atenuación",
                "`diagnosis/sonificacion-con-artefactos`",
                "Mantiene el DSP y la sonificación sin quality gate.",
                "Servir como control: observar respuesta musical cuando los artefactos pasan sin amortiguación.",
                "Rama remota para pruebas A/B.",
            ],
            [
                "Rama con atenuación",
                "`diagnosis/sonificacion-atenuacion-artefactos`, `3a37152`",
                "Se crea `spectral_quality.py` y se integra en backend y `sonification_features.py`.",
                "Atenuar o invalidar ventanas con artefactos sin cambiar adquisición ni DSP base.",
                "`docs/diseno_spectral_quality_score.md`.",
            ],
            [
                "Capturas de atenuación",
                "`60aab62`, `4b46f2a`",
                "Se suben capturas mixtas con rama de atenuación.",
                "Validar que hay ventanas limpias, ventanas con cautela y ventanas bloqueadas.",
                "`20260524-122200_final_atenuacion_artefactos_mixed_states`.",
            ],
            [
                "Alineación offline/live",
                "`5c06a4c`",
                "El validador offline aplica el mismo quality gate que el backend live.",
                "Hacer comparables `windowed_sonification_features.csv` y el comportamiento real.",
                "Informes regenerados con estados `clean`, `usable_with_caution`, `artifact_suspected`, `bad`.",
            ],
        ],
    )
    text += (
        "\n\n## Ramas finales de diagnóstico\n\n"
        "- `captura-datos-dsp`: base común con adquisición y DSP validados preliminarmente, y `bias_ch1_only_loff_off` por defecto.\n"
        "- `diagnosis/sonificacion-con-artefactos`: rama de control, sin atenuación de artefactos.\n"
        "- `diagnosis/sonificacion-atenuacion-artefactos`: rama experimental, con `spectral_quality_score` y quality gate.\n\n"
        "La comparación entre las dos ramas de diagnóstico permite separar dos preguntas: si la señal/DSP funciona, y si la capa musical debe protegerse frente a artefactos. "
        "La respuesta obtenida fue que la señal y el DSP son suficientemente útiles para continuar, pero la sonificación necesita memoria musical, histéresis y control de repetición armónica.\n\n"
        "## Cambios que no se hicieron en esta fase\n\n"
        "No se rediseñó la sonificación final, no se cambiaron las bandas EEG principales, no se sustituyó multitaper y no se modificó el contrato `Bridge.notify(\"eeg_block_uV\")`. "
        "Esto fue deliberado: la fase buscaba validar y documentar, no optimizar todavía la composición musical.\n"
    )
    return text


def build(captures_dir: Path, output_dir: Path) -> None:
    captures = load_captures(captures_dir)
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    tables = generate_tables(captures, tables_dir)
    figs = generate_figures(captures, figures_dir)
    generate_docs(captures, output_dir, figs, tables)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build TFG validation documentation from EEG captures.")
    parser.add_argument("--captures", type=Path, default=Path("captures"))
    parser.add_argument("--output", type=Path, default=Path("docs/validacion_tfg"))
    parser.add_argument("--only-figures", action="store_true", help="Accepted for compatibility; currently rebuilds all outputs.")
    parser.add_argument("--only-docs", action="store_true", help="Accepted for compatibility; currently rebuilds all outputs.")
    parser.add_argument("--include-long-sessions", action="store_true", help="Reserved for future filtering.")
    parser.add_argument("--condition-filter", default="", help="Reserved for future filtering.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build(args.captures, args.output)
    print(f"[validation-docs] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
