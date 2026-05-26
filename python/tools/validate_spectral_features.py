from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any


PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
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

if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz

from analyze_eeg_capture import BANDS, analyze
from dsp_core import DSPCore
from eeg_contract import FS_HZ, NUM_CH
from spectral_quality import compute_spectral_quality
from sonification_features import SonificationFeatureAdapter


FS_HZ_DEFAULT = float(FS_HZ)


def _load_capture_csv(capture_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    path = capture_dir / "eeg_timeseries.csv"
    if not path.exists():
        raise FileNotFoundError(path)

    sample_idx: list[int] = []
    statuses: list[int] = []
    channels: list[list[float]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sample_idx.append(int(row["sample_idx"]))
            statuses.append(int(row["status"]))
            channels.append([float(row[f"ch{i}_uV"]) for i in range(1, NUM_CH + 1)])

    return (
        np.asarray(sample_idx, dtype=np.int64),
        np.asarray(statuses, dtype=np.uint32),
        np.asarray(channels, dtype=float),
    )


def _load_metadata(capture_dir: Path) -> dict:
    path = capture_dir / "metadata.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def _bandpower(freqs: np.ndarray, pxx: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs <= high)
    if not np.any(mask):
        return 0.0
    return float(np.trapezoid(pxx[mask], freqs[mask]))


def _line_50_ratio(freqs: np.ndarray | None, pxx: np.ndarray | None) -> float | None:
    if freqs is None or pxx is None:
        return None
    freqs_arr = np.asarray(freqs)
    pxx_arr = np.asarray(pxx)
    total = _bandpower(freqs_arr, pxx_arr, 1.0, 50.0)
    if total <= 0:
        return None
    return float(_bandpower(freqs_arr, pxx_arr, 49.0, 51.0) / total)


def _spectral_entropy(freqs: np.ndarray | None, pxx: np.ndarray | None, low: float = 0.5, high: float = 40.0) -> float | None:
    if freqs is None or pxx is None:
        return None
    freqs_arr = np.asarray(freqs)
    pxx_arr = np.asarray(pxx)
    mask = (freqs_arr >= low) & (freqs_arr <= high)
    if not np.any(mask):
        return None
    p = np.maximum(pxx_arr[mask].astype(float), 1e-20)
    total = float(np.sum(p))
    if total <= 0:
        return None
    p /= total
    entropy = float(-np.sum(p * np.log(p)))
    max_entropy = float(np.log(p.size)) if p.size > 1 else 0.0
    if max_entropy <= 0:
        return None
    return entropy / max_entropy


def _summary(values: list[float]) -> dict:
    finite = [float(v) for v in values if math.isfinite(float(v))]
    if not finite:
        return {"count": 0}
    return {
        "count": len(finite),
        "mean": float(statistics.fmean(finite)),
        "median": float(statistics.median(finite)),
        "p05": float(np.percentile(finite, 5)),
        "p95": float(np.percentile(finite, 95)),
        "min": float(min(finite)),
        "max": float(max(finite)),
    }


def _classify_band(name: str, rows: list[dict], condition: str) -> dict:
    rel_values = [_finite(row.get(f"{name}_rel")) for row in rows]
    abs_values = [_finite(row.get(f"{name}_abs")) for row in rows]
    good_rows = [row for row in rows if _finite(row.get("quality_score")) >= 0.70]
    rel_good = [_finite(row.get(f"{name}_rel")) for row in good_rows]
    condition_l = condition.lower()

    rel_summary = _summary(rel_values)
    abs_summary = _summary(abs_values)
    rel_good_summary = _summary(rel_good)

    decision = "NECESITA MAS CAPTURAS"
    risk = "requiere comparacion entre condiciones"
    usefulness = "solo diagnostico por ahora"

    if name == "gamma":
        decision = "NO USAR EN TIEMPO REAL"
        risk = "muy sensible a EMG y ruido en EEG superficial"
        usefulness = "solo indicador de posible artefacto/actividad muscular"
    elif name == "beta":
        decision = "USAR SOLO COMO APOYO"
        risk = "puede aumentar con mandibula/frente/EMG"
        usefulness = "tension/actividad con suavizado y bloqueo por calidad"
    elif name in ("delta", "theta"):
        decision = "USAR SOLO COMO APOYO"
        risk = "puede reflejar drift, parpadeo o movimiento"
        usefulness = "calma/slow_power si artifact score es bajo"
    elif name == "alpha":
        decision = "NECESITA MAS CAPTURAS"
        risk = "no validada solo por presencia; requiere open/closed robusto"
        usefulness = "calmness si aumenta en condiciones limpias"

    if "jaw" in condition_l or "blink" in condition_l or "artifact" in condition_l or "forehead" in condition_l:
        if name in ("beta", "gamma"):
            decision = "NO USAR EN TIEMPO REAL"
            risk = "condicion de artefacto muestra contaminacion probable"
        elif name in ("delta", "theta"):
            decision = "USAR SOLO COMO APOYO"
            risk = "condicion de artefacto puede inflar baja frecuencia"

    return {
        "band": name,
        "relative": rel_summary,
        "relative_good_windows": rel_good_summary,
        "absolute": abs_summary,
        "decision": decision,
        "risk": risk,
        "sonification_usefulness": usefulness,
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_psd_csv(path: Path, freqs: np.ndarray | None, pxx: np.ndarray | None) -> None:
    if freqs is None or pxx is None:
        return
    rows = [{"freq_hz": float(f), "psd_v2_per_hz": float(p)} for f, p in zip(freqs, pxx)]
    _write_csv(path, rows)


def validate_capture(
    capture_dir: Path,
    *,
    channel: int = 0,
    window_sec: float = 4.0,
    hop_samples: int = 64,
) -> dict:
    metadata = _load_metadata(capture_dir)
    condition = str(metadata.get("condition") or capture_dir.name)
    sample_idx, _statuses, channels_uv = _load_capture_csv(capture_dir)
    fs_hz = float(metadata.get("fs_hz_expected", FS_HZ_DEFAULT) or FS_HZ_DEFAULT)
    channel = max(0, min(channel, channels_uv.shape[1] - 1))

    win = max(4, int(round(window_sec * fs_hz)))
    hop = max(1, int(hop_samples))
    x_uv = channels_uv[:, channel].astype(float)
    x_v = x_uv * 1e-6
    dsp = DSPCore(fs=fs_hz, window_sec=window_sec)
    adapter = SonificationFeatureAdapter()

    starts = list(range(0, max(0, x_v.size - win + 1), hop))
    window_rows: list[dict] = []
    sonif_rows: list[dict] = []

    for start in starts:
        stop = start + win
        segment_v = x_v[start:stop]
        segment_uv = x_uv[start:stop]
        features = dsp.compute_features(
            segment_v,
            psd_method="multitaper",
            include_spectrum=True,
            include_peaks=True,
            include_relative_bandpower=True,
        )
        if not features:
            continue

        freqs = features.get("freqs")
        psd = features.get("psd")
        line_50_ratio = _line_50_ratio(freqs, psd)
        entropy = _spectral_entropy(freqs, psd)

        rms_uv = float(np.sqrt(np.mean(segment_uv ** 2)))
        ptp_uv = float(np.ptp(segment_uv))
        finite_features = all(
            math.isfinite(_finite(v))
            for group in ("bandpower_abs", "bandpower_rel")
            for v in (features.get(group, {}) or {}).values()
        )
        expected_step_ok = True
        if sample_idx.size >= stop and start > 0:
            expected_step_ok = bool(sample_idx[start] - sample_idx[start - 1] == 1)
        quality_obj = compute_spectral_quality(
            features,
            {
                "rms_uv": rms_uv,
                "ptp_uv": ptp_uv,
                "line_50_ratio": line_50_ratio,
                "abrupt_jumps": 0,
                "flatline": False,
                "saturation_fraction": 0.0,
            },
            {
                "lost_frames_delta": 1 if not expected_step_ok else 0,
                "lost_blocks_delta": 0,
                "queue_drops_frames_delta": 0,
                "queue_drops_blocks_delta": 0,
                "malformed_blocks_delta": 0,
                "invalid_status_delta": 0,
            },
            window_ready=finite_features,
        )
        quality = quality_obj.score
        quality_warnings = quality_obj.warnings

        band_abs = features.get("bandpower_abs", {}) or {}
        band_rel = features.get("bandpower_rel", {}) or {}
        row = {
            "capture": capture_dir.name,
            "condition": condition,
            "channel": channel,
            "window_start_sec": float(start / fs_hz),
            "window_end_sec": float(stop / fs_hz),
            "rms_uV": rms_uv,
            "ptp_uV": ptp_uv,
            "line_50_ratio_1_50": line_50_ratio,
            "spectral_entropy_0p5_40": entropy,
            "quality_score": quality,
            "quality_warnings": ";".join(quality_warnings),
            "peak_freq": features.get("peak_freq"),
            "peak_delta": features.get("peak_delta"),
            "peak_theta": features.get("peak_theta"),
            "peak_alpha": features.get("peak_alpha"),
            "peak_beta": features.get("peak_beta"),
            "peak_gamma": features.get("peak_gamma"),
        }
        for band in BANDS:
            row[f"{band}_abs"] = band_abs.get(band, 0.0)
            row[f"{band}_rel"] = band_rel.get(band, 0.0)
        row["alpha_beta_ratio"] = _finite(row["alpha_rel"]) / max(_finite(row["beta_rel"]), 1e-12)
        row["theta_alpha_ratio"] = _finite(row["theta_rel"]) / max(_finite(row["alpha_rel"]), 1e-12)
        row["slow_power_rel"] = _finite(row["delta_rel"]) + _finite(row["theta_rel"])
        row["fast_power_rel"] = _finite(row["beta_rel"]) + _finite(row["gamma_rel"])
        window_rows.append(row)

        features_for_sonif = dict(features)
        features_for_sonif.pop("freqs", None)
        features_for_sonif.pop("psd", None)
        sonif = adapter.update(features_for_sonif, quality=quality_obj.to_dict()).to_dict()
        sonif_rows.append(
            {
                "capture": capture_dir.name,
                "condition": condition,
                "channel": channel,
                "window_start_sec": row["window_start_sec"],
                "quality_score": quality,
                "quality_gate": sonif.get("quality_gate"),
                "quality_state": sonif.get("quality_state"),
                **{
                    key: sonif.get(key)
                    for key in (
                        "valid",
                        "activity",
                        "calmness",
                        "tension",
                        "rhythmic_density",
                        "register",
                        "harmonic_stability",
                        "velocity_factor",
                        "note_probability",
                        "rms_uV",
                        "alpha_beta_ratio",
                        "beta_over_alpha_beta",
                        "theta_alpha_ratio",
                        "slow_power",
                        "fast_power",
                        "dominant_band",
                    )
                },
            }
        )

    _write_csv(capture_dir / "windowed_bandpowers.csv", window_rows)
    _write_csv(capture_dir / "windowed_sonification_features.csv", sonif_rows)

    freqs_full, psd_full = dsp.compute_psd(x_v, method="multitaper")
    _write_psd_csv(capture_dir / "psd_multitaper.csv", freqs_full, psd_full)

    quality_scores = [_finite(row.get("quality_score")) for row in window_rows]
    artifact_fraction = float(np.mean([score < 0.70 for score in quality_scores])) if quality_scores else 1.0
    report = {
        "capture_dir": str(capture_dir),
        "condition": condition,
        "channel": channel,
        "fs_hz": fs_hz,
        "window_sec": window_sec,
        "hop_samples": hop,
        "hop_sec": hop / fs_hz,
        "window_count": len(window_rows),
        "quality": {
            "median_score": _summary(quality_scores).get("median"),
            "p05_score": _summary(quality_scores).get("p05"),
            "artifact_or_low_quality_fraction": artifact_fraction,
        },
        "rms_uV": _summary([row["rms_uV"] for row in window_rows]),
        "line_50_ratio_1_50": _summary([row["line_50_ratio_1_50"] for row in window_rows if row["line_50_ratio_1_50"] is not None]),
        "bands": {band: _classify_band(band, window_rows, condition) for band in BANDS},
        "sonification": {
            key: _summary([_finite(row.get(key)) for row in sonif_rows])
            for key in (
                "activity",
                "calmness",
                "tension",
                "rhythmic_density",
                "register",
                "harmonic_stability",
                "velocity_factor",
                "note_probability",
            )
        },
        "outputs": {
            "windowed_bandpowers_csv": str(capture_dir / "windowed_bandpowers.csv"),
            "windowed_sonification_features_csv": str(capture_dir / "windowed_sonification_features.csv"),
            "psd_multitaper_csv": str(capture_dir / "psd_multitaper.csv"),
        },
    }
    (capture_dir / "spectral_validation_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_markdown(capture_dir / "spectral_validation_report.md", report)
    return report


def _write_markdown(path: Path, report: dict) -> None:
    lines = [
        "# Spectral validation report",
        "",
        f"- Capture: {Path(report['capture_dir']).name}",
        f"- Condition: {report['condition']}",
        f"- Channel: ch{int(report['channel']) + 1}",
        f"- Window: {report['window_sec']} s",
        f"- Hop: {report['hop_sec']:.3f} s",
        f"- Windows: {report['window_count']}",
        f"- Median quality score: {report['quality'].get('median_score')}",
        f"- Low-quality/artifact fraction: {report['quality'].get('artifact_or_low_quality_fraction')}",
        "",
        "## Band Decisions",
        "",
        "| Band | Median rel | P95 rel | Decision | Risk |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for band, data in report["bands"].items():
        rel = data.get("relative", {})
        lines.append(
            f"| {band} | {rel.get('median', 'n/a')} | {rel.get('p95', 'n/a')} | "
            f"{data.get('decision')} | {data.get('risk')} |"
        )

    lines.extend(
        [
            "",
            "## Sonification Controls",
            "",
            "| Control | Median | P05 | P95 |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for control, data in report["sonification"].items():
        lines.append(
            f"| {control} | {data.get('median', 'n/a')} | {data.get('p05', 'n/a')} | {data.get('p95', 'n/a')} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.",
            "- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.",
            "- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.",
            "- Alpha requires open/closed comparison before being considered validated.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _discover_captures(root: Path) -> list[Path]:
    if (root / "eeg_timeseries.csv").exists():
        return [root]
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "eeg_timeseries.csv").exists())


def _write_aggregate(root: Path, reports: list[dict]) -> None:
    out_dir = root / "comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for report in reports:
        rows.append(
            {
                "capture": Path(report["capture_dir"]).name,
                "condition": report["condition"],
                "channel": report["channel"],
                "window_count": report["window_count"],
                "median_quality_score": report["quality"].get("median_score"),
                "artifact_or_low_quality_fraction": report["quality"].get("artifact_or_low_quality_fraction"),
                "median_rms_uV": report["rms_uV"].get("median"),
                "median_50hz_ratio": report["line_50_ratio_1_50"].get("median"),
                **{
                    f"{band}_decision": report["bands"][band]["decision"]
                    for band in BANDS
                },
            }
        )
    _write_csv(out_dir / "spectral_feature_robustness.csv", rows)
    (out_dir / "spectral_feature_robustness.json").write_text(
        json.dumps(reports, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Spectral feature robustness",
        "",
        "| Capture | Median quality | Low-quality % | Median RMS uV | Median 50 Hz | Alpha | Beta | Gamma |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lowq = row["artifact_or_low_quality_fraction"]
        lowq_pct = None if lowq is None else 100.0 * float(lowq)
        lines.append(
            f"| {row['capture']} | {row['median_quality_score']} | {lowq_pct} | "
            f"{row['median_rms_uV']} | {row['median_50hz_ratio']} | "
            f"{row['alpha_decision']} | {row['beta_decision']} | {row['gamma_decision']} |"
        )
    (out_dir / "spectral_feature_robustness.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate EEG spectral features from capture CSV files.")
    parser.add_argument("path", help="Capture directory or captures root.")
    parser.add_argument("--channel", type=int, default=0, help="0-based channel index to analyze.")
    parser.add_argument("--window-sec", type=float, default=4.0, help="DSP feature window in seconds.")
    parser.add_argument("--hop-samples", type=int, default=64, help="Hop in samples; 64 matches live feature cadence.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.path)
    captures = _discover_captures(root)
    if not captures:
        print(f"[spectral-validation] no captures with eeg_timeseries.csv found under {root}")
        return 2

    reports = []
    for capture_dir in captures:
        report = validate_capture(
            capture_dir,
            channel=args.channel,
            window_sec=args.window_sec,
            hop_samples=args.hop_samples,
        )
        reports.append(report)
        print(
            "[spectral-validation] {name}: windows={n} median_quality={q}".format(
                name=capture_dir.name,
                n=report["window_count"],
                q=report["quality"].get("median_score"),
            )
        )

    if len(captures) > 1:
        _write_aggregate(root, reports)
        print(f"[spectral-validation] wrote aggregate under {root / 'comparisons'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
