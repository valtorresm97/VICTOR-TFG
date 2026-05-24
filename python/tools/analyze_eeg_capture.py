from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path


PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))


def _add_cached_site_packages() -> None:
    """
    App Lab installs numpy/scipy in .cache/.venv, but the venv executable can be
    unusable from the board shell. Add its site-packages when running via
    system python3.
    """
    lib_dir = PROJECT_ROOT / ".cache" / ".venv" / "lib"
    if not lib_dir.exists():
        return
    for site_packages in lib_dir.glob("python*/site-packages"):
        site_path = str(site_packages)
        if site_path not in sys.path:
            sys.path.insert(0, site_path)


_add_cached_site_packages()

import numpy as np
from scipy.signal import windows


FS_HZ_DEFAULT = 250.0
NUM_CH = 4
STATUS_PREFIX = 0xC00000
STATUS_MASK = 0xF00000
LSB_V = 2.235e-8
ADC_FULL_SCALE_UV = 8388607.0 * LSB_V * 1e6
RESTING_RMS_WARN_UV = 500.0
RESTING_PTP_WARN_UV = 5000.0
RESTING_OFFSET_WARN_UV = 250.0
WINDOW_SEC = 2.0
WINDOW_HOP_SEC = 1.0
WINDOW_RMS_CLEAN_UV = 100.0
WINDOW_RMS_ARTIFACT_UV = 200.0
WINDOW_PTP_ARTIFACT_UV = 5000.0
BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 50.0),
}


def _load_metadata(capture_dir: Path) -> dict:
    path = capture_dir / "metadata.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_timeseries(capture_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    path = capture_dir / "eeg_timeseries.csv"
    if not path.exists():
        raise FileNotFoundError(path)

    sample_idx = []
    statuses = []
    channels = []

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


def _multitaper_psd(x_uv: np.ndarray, fs_hz: float, nw: float = 2.5) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x_uv, dtype=float)
    if x.size < 4:
        return np.array([], dtype=float), np.array([], dtype=float)
    x = x - np.mean(x)
    n = x.size
    kmax = max(1, int(2 * nw - 1))
    tapers = windows.dpss(n, nw, Kmax=kmax, sym=False)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs_hz)
    psd = np.zeros_like(freqs)
    dt = 1.0 / fs_hz
    for taper in tapers:
        xf = np.fft.rfft(x * taper)
        psd += (dt / n) * np.abs(xf) ** 2
    return freqs, psd / kmax


def _bandpower(freqs: np.ndarray, psd: np.ndarray, f_low: float, f_high: float) -> float:
    mask = (freqs >= f_low) & (freqs <= f_high)
    if not np.any(mask):
        return 0.0
    return float(np.trapezoid(psd[mask], freqs[mask]))


def _peak_freq(freqs: np.ndarray, psd: np.ndarray, f_low: float, f_high: float) -> float | None:
    mask = (freqs >= f_low) & (freqs <= f_high)
    if not np.any(mask):
        return None
    sub_freqs = freqs[mask]
    sub_psd = psd[mask]
    return float(sub_freqs[int(np.argmax(sub_psd))])


def _windowed_metrics(x: np.ndarray, fs_hz: float) -> dict:
    """Summarize stable windows separately from full-capture transient artifacts."""
    if x.size == 0 or fs_hz <= 0:
        return {}
    win = max(1, int(round(WINDOW_SEC * fs_hz)))
    hop = max(1, int(round(WINDOW_HOP_SEC * fs_hz)))
    if x.size < win:
        return {}

    rows = []
    for start in range(0, x.size - win + 1, hop):
        segment = x[start : start + win]
        rms = float(np.sqrt(np.mean(segment ** 2)))
        ptp = float(np.ptp(segment))
        robust_ptp = float(np.percentile(segment, 95) - np.percentile(segment, 5))
        rows.append((start / fs_hz, rms, ptp, robust_ptp))

    arr = np.asarray(rows, dtype=float)
    starts = arr[:, 0]
    rms_values = arr[:, 1]
    ptp_values = arr[:, 2]
    robust_ptp_values = arr[:, 3]
    artifact_mask = (rms_values > WINDOW_RMS_ARTIFACT_UV) | (ptp_values > WINDOW_PTP_ARTIFACT_UV)
    best_idx = int(np.argmin(rms_values))
    worst_idx = int(np.argmax(rms_values))

    return {
        "window_sec": WINDOW_SEC,
        "hop_sec": WINDOW_HOP_SEC,
        "window_count": int(arr.shape[0]),
        "median_rms_uV": float(np.median(rms_values)),
        "p90_rms_uV": float(np.percentile(rms_values, 90)),
        "p95_rms_uV": float(np.percentile(rms_values, 95)),
        "max_rms_uV": float(np.max(rms_values)),
        "median_ptp_uV": float(np.median(ptp_values)),
        "p95_ptp_uV": float(np.percentile(ptp_values, 95)),
        "max_ptp_uV": float(np.max(ptp_values)),
        "median_robust_ptp_uV": float(np.median(robust_ptp_values)),
        "p95_robust_ptp_uV": float(np.percentile(robust_ptp_values, 95)),
        "artifact_window_fraction": float(np.mean(artifact_mask)),
        "best_window_start_sec": float(starts[best_idx]),
        "best_window_rms_uV": float(rms_values[best_idx]),
        "worst_window_start_sec": float(starts[worst_idx]),
        "worst_window_rms_uV": float(rms_values[worst_idx]),
    }


def _channel_metrics(x: np.ndarray, sample_idx: np.ndarray, fs_hz: float) -> dict:
    if x.size == 0:
        return {}
    diffs = np.diff(x) if x.size >= 2 else np.array([], dtype=float)
    near_adc = np.abs(x) >= 0.98 * ADC_FULL_SCALE_UV
    std = float(np.std(x))
    jump_threshold = max(100.0, 8.0 * std)
    freqs, psd = _multitaper_psd(x, fs_hz)
    total_1_50 = _bandpower(freqs, psd, 1.0, 50.0) if freqs.size else 0.0
    line_50 = _bandpower(freqs, psd, 49.0, 51.0) if freqs.size else 0.0
    band_abs = {name: _bandpower(freqs, psd, lo, hi) for name, (lo, hi) in BANDS.items()}
    total_bands = sum(band_abs.values())
    band_rel = {name: (value / total_bands if total_bands > 0 else 0.0) for name, value in band_abs.items()}

    return {
        "samples": int(x.size),
        "mean_uV": float(np.mean(x)),
        "median_uV": float(np.median(x)),
        "std_uV": std,
        "rms_uV": float(np.sqrt(np.mean(x ** 2))),
        "min_uV": float(np.min(x)),
        "max_uV": float(np.max(x)),
        "ptp_uV": float(np.ptp(x)),
        "p01_uV": float(np.percentile(x, 1)),
        "p05_uV": float(np.percentile(x, 5)),
        "p95_uV": float(np.percentile(x, 95)),
        "p99_uV": float(np.percentile(x, 99)),
        "near_adc_limit_fraction": float(np.mean(near_adc)),
        "flatline": bool(std < 0.05 or np.ptp(x) < 0.5),
        "abrupt_jumps": int(np.sum(np.abs(diffs) > jump_threshold)) if diffs.size else 0,
        "bandpower_abs": band_abs,
        "bandpower_rel": band_rel,
        "peak_freq_hz": _peak_freq(freqs, psd, 0.5, 50.0),
        "peak_by_band_hz": {name: _peak_freq(freqs, psd, lo, hi) for name, (lo, hi) in BANDS.items()},
        "line_50_power": line_50,
        "line_50_ratio_1_50": float(line_50 / total_1_50) if total_1_50 > 0 else None,
        "windowed": _windowed_metrics(x, fs_hz),
    }


def _diagnose(report: dict) -> tuple[str, list[str], list[str]]:
    reasons = []
    recommendations = []
    condition = str(report.get("metadata", {}).get("condition", "") or "").lower()
    is_shorted = "shorted_inputs" in condition
    is_test_signal = "test_signal_internal" in condition
    is_artifact_control = any(
        token in condition
        for token in ("artifact", "blink", "jaw", "forehead", "movement", "cable")
    )

    if report["status"]["invalid_status_total"] > 0:
        reasons.append("invalid ADS1299 status prefix observed")
        recommendations.append("Check SPI framing, DRDY timing, and status prefix 0xC00000.")
    if report["timing"]["sample_gaps_detected"] > 0:
        reasons.append("sample index gaps detected")
        recommendations.append("Check Bridge queue drops and MCU pending>1 DRDY events.")

    ch1 = report["channels"].get("ch1", {})
    ch1_windowed = ch1.get("windowed", {}) or {}
    artifact_fraction = float(ch1_windowed.get("artifact_window_fraction", 1.0))
    median_window_rms = ch1_windowed.get("median_rms_uV")
    stable_windows_clean = (
        median_window_rms is not None
        and float(median_window_rms) <= WINDOW_RMS_CLEAN_UV
        and artifact_fraction < 0.25
    )
    if is_shorted and not reasons:
        if ch1.get("rms_uV", 0.0) <= 5.0 and ch1.get("ptp_uV", 0.0) <= 100.0:
            return (
                "valida_diagnostica",
                ["shorted-input noise/offset is low; ADC/SPI/scale path looks healthy"],
                ["Use this result as evidence that the millivolt scalp captures are dominated by electrodes/common-mode/reference, not digital transport."],
            )
        reasons.append("shorted-input amplitude is higher than expected")
        recommendations.append("Inspect ADS1299 configuration, board noise, filters, and scale before testing electrodes again.")

    if ch1.get("flatline") and not is_shorted:
        reasons.append("CH1 appears flat or frozen")
        recommendations.append("Check electrodes, lead-off state, and whether the input is shorted.")
    if ch1.get("near_adc_limit_fraction", 0.0) > 0:
        reasons.append("samples close to ADC full-scale estimate")
        recommendations.append("Check saturation/clipping, gain, electrode offset, and input range.")

    apply_resting_limits = not (is_shorted or is_test_signal)
    if apply_resting_limits and abs(ch1.get("mean_uV", 0.0)) > 100.0:
        reasons.append("large residual offset after MCU filters")
        recommendations.append("Inspect raw/unfiltered diagnostic capture before changing filters.")
    if apply_resting_limits and abs(ch1.get("mean_uV", 0.0)) > RESTING_OFFSET_WARN_UV:
        reasons.append("very large residual offset for a filtered resting EEG capture")
        recommendations.append("Check electrode contact, input bias/common-mode path, and ADS1299 scaling.")
    if apply_resting_limits and ch1.get("rms_uV", 0.0) > RESTING_RMS_WARN_UV and not stable_windows_clean:
        reasons.append("CH1 RMS is far above typical resting scalp EEG amplitude")
        recommendations.append("Treat this as transport-valid but physiologically suspicious; check gain/LSB, electrode placement, and BIAS/DRL strategy.")
    if apply_resting_limits and ch1.get("ptp_uV", 0.0) > RESTING_PTP_WARN_UV and not stable_windows_clean:
        reasons.append("CH1 peak-to-peak amplitude is far above typical resting scalp EEG")
        recommendations.append("Look for motion, electrode polarization, missing reference/common-mode control, or scaling error.")
    if apply_resting_limits and stable_windows_clean and ch1.get("ptp_uV", 0.0) > RESTING_PTP_WARN_UV:
        recommendations.append("Full-capture peak-to-peak is high, but most 2 s windows are stable; inspect transient movement/artifact periods instead of rejecting the whole capture.")

    if is_test_signal and not reasons:
        if ch1.get("rms_uV", 0.0) > 10.0 and ch1.get("ptp_uV", 0.0) > 100.0:
            return (
                "valida_diagnostica",
                ["internal ADS1299 test signal was captured with stable status and sample timing"],
                ["Use spectral_summary.csv and eeg_timeseries.csv to verify expected test-signal frequency and amplitude against the datasheet."],
            )
        reasons.append("internal test signal amplitude is unexpectedly small")
        recommendations.append("Check CONFIG2 INT_CAL, CHnSET MUX=TESTSIG, and whether the sketch was recompiled after changing diagnostic mode.")

    ratio_50 = ch1.get("line_50_ratio_1_50")
    if ratio_50 is not None and ratio_50 > 0.25 and ch1.get("rms_uV", 0.0) > 5.0:
        reasons.append("high 50 Hz power ratio")
        recommendations.append("Check electrode contact, cable routing, grounding, and notch effectiveness.")
    if ch1.get("abrupt_jumps", 0) > max(3, 0.001 * ch1.get("samples", 0)):
        reasons.append("abrupt jumps or motion artifacts")
        recommendations.append("Repeat capture with still posture and verify electrode stability.")

    if reasons:
        return "dudosa", reasons, recommendations
    if apply_resting_limits and artifact_fraction >= 0.25:
        if is_artifact_control:
            return (
                "artefacto_confirmado",
                ["artifact-control capture produced many high-artifact windows"],
                ["Use this as a positive control for blink, forehead, jaw, cable, or movement artifact detection."],
            )
        return (
            "dudosa_por_artefacto",
            ["many 2 s windows contain movement/EMG-like artifacts"],
            ["Repeat resting capture with still posture, relaxed jaw/forehead, and better cable fixation."],
        )
    if apply_resting_limits and 0.05 <= artifact_fraction < 0.25:
        return (
            "valida_preliminar_con_artefactos",
            ["stable windows look physiologically plausible, with some transient artifacts"],
            ["Use the clean/still intervals for EEG validation and repeat with better cable fixation to reduce transient jumps."],
        )
    return "valida_preliminar", ["no automatic quality failure detected"], ["Compare eyes-open and eyes-closed alpha before accepting physiological validity."]


def _write_spectral_csv(capture_dir: Path, report: dict) -> None:
    path = capture_dir / "spectral_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["channel", "band", "bandpower_abs_uV2", "bandpower_rel", "peak_hz"])
        for channel, metrics in report["channels"].items():
            for band in BANDS:
                writer.writerow(
                    [
                        channel,
                        band,
                        metrics["bandpower_abs"].get(band, 0.0),
                        metrics["bandpower_rel"].get(band, 0.0),
                        metrics["peak_by_band_hz"].get(band),
                    ]
                )


def _fmt_md_number(value) -> str:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return f"{float(value):.6g}"
    return "n/a"


def _write_markdown(capture_dir: Path, report: dict) -> None:
    lines = [
        "# EEG capture quality report",
        "",
        f"- Diagnosis: {report['diagnosis']['state']}",
        f"- Duration observed: {report['timing']['duration_sec']:.2f} s",
        f"- Effective sample rate: {report['timing']['effective_fs_hz']:.2f} Hz",
        f"- Samples received: {report['timing']['samples_received']}",
        f"- Sample gaps: {report['timing']['sample_gaps_detected']}",
        f"- Invalid status: {report['status']['invalid_status_total']}",
        "",
        "## Reasons",
        "",
    ]
    lines.extend(f"- {item}" for item in report["diagnosis"]["reasons"])
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {item}" for item in report["diagnosis"]["recommendations"])
    lines.extend(["", "## CH1 summary", ""])
    ch1 = report["channels"].get("ch1", {})
    for key in ("rms_uV", "mean_uV", "ptp_uV", "line_50_ratio_1_50", "peak_freq_hz"):
        value = ch1.get(key)
        if isinstance(value, float) and math.isfinite(value):
            lines.append(f"- {key}: {value:.6g}")
        else:
            lines.append(f"- {key}: {value}")
    windowed = ch1.get("windowed", {}) or {}
    if windowed:
        lines.extend(["", "## CH1 windowed stability", ""])
        lines.append(f"- window_sec: {windowed.get('window_sec')}")
        lines.append(f"- window_count: {windowed.get('window_count')}")
        for key in (
            "median_rms_uV",
            "p95_rms_uV",
            "best_window_rms_uV",
            "best_window_start_sec",
            "median_ptp_uV",
            "p95_ptp_uV",
            "artifact_window_fraction",
        ):
            lines.append(f"- {key}: {_fmt_md_number(windowed.get(key))}")
    lines.extend(["", "## Multichannel summary", ""])
    lines.append("| Channel | RMS uV | Median win RMS uV | Artifact win % | Mean uV | PTP uV | Peak Hz | 50 Hz ratio |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for channel, metrics in sorted(report["channels"].items()):
        win = metrics.get("windowed", {}) or {}
        lines.append(
            "| {channel} | {rms:.6g} | {median_win} | {artifact_pct} | {mean:.6g} | {ptp:.6g} | {peak} | {ratio} |".format(
                channel=channel,
                rms=float(metrics.get("rms_uV", 0.0) or 0.0),
                median_win=_fmt_md_number(win.get("median_rms_uV")),
                artifact_pct=_fmt_md_number(100.0 * float(win.get("artifact_window_fraction", 0.0))) if win else "n/a",
                mean=float(metrics.get("mean_uV", 0.0) or 0.0),
                ptp=float(metrics.get("ptp_uV", 0.0) or 0.0),
                peak=_fmt_md_number(metrics.get("peak_freq_hz")),
                ratio=_fmt_md_number(metrics.get("line_50_ratio_1_50")),
            )
        )
    (capture_dir / "quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze(capture_dir: Path) -> dict:
    metadata = _load_metadata(capture_dir)
    sample_idx, statuses, channels = _load_timeseries(capture_dir)
    fs_hz = float(metadata.get("fs_hz_expected", FS_HZ_DEFAULT) or FS_HZ_DEFAULT)

    if sample_idx.size > 1:
        duration_by_index = (int(sample_idx[-1]) - int(sample_idx[0]) + 1) / fs_hz
        effective_fs = float(sample_idx.size / duration_by_index) if duration_by_index > 0 else 0.0
        gaps = np.diff(sample_idx)
        sample_gaps = int(np.sum(np.maximum(gaps - 1, 0)))
    else:
        duration_by_index = 0.0
        effective_fs = 0.0
        sample_gaps = 0

    invalid_status = int(np.sum((statuses & STATUS_MASK) != STATUS_PREFIX))
    channels_report = {}
    for ch in range(NUM_CH):
        channels_report[f"ch{ch + 1}"] = _channel_metrics(channels[:, ch], sample_idx, fs_hz)

    report = {
        "metadata": metadata,
        "timing": {
            "fs_hz_expected": fs_hz,
            "duration_sec": float(duration_by_index),
            "samples_expected_from_duration": int(round(duration_by_index * fs_hz)),
            "samples_received": int(sample_idx.size),
            "effective_fs_hz": effective_fs,
            "sample_gaps_detected": sample_gaps,
            "first_sample_idx": int(sample_idx[0]) if sample_idx.size else None,
            "last_sample_idx": int(sample_idx[-1]) if sample_idx.size else None,
        },
        "status": {
            "status_prefix_expected": "0xC00000",
            "invalid_status_total": invalid_status,
            "invalid_status_fraction": float(invalid_status / sample_idx.size) if sample_idx.size else 0.0,
        },
        "channels": channels_report,
    }
    state, reasons, recommendations = _diagnose(report)
    report["diagnosis"] = {
        "state": state,
        "reasons": reasons,
        "recommendations": recommendations,
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze an EEG capture directory.")
    parser.add_argument("capture_dir", help="Directory containing metadata.json and eeg_timeseries.csv.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    capture_dir = Path(args.capture_dir)
    report = analyze(capture_dir)

    with (capture_dir / "quality_report.json").open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    _write_spectral_csv(capture_dir, report)
    _write_markdown(capture_dir, report)

    print(f"[analysis] diagnosis={report['diagnosis']['state']}")
    print(f"[analysis] wrote {capture_dir / 'quality_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
