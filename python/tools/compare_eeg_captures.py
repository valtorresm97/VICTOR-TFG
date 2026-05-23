from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from analyze_eeg_capture import analyze


def _load_or_analyze(capture_dir: Path) -> dict:
    report_path = capture_dir / "quality_report.json"
    if report_path.exists():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return analyze(capture_dir)


def _ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den <= 0:
        return None
    return float(num / den)


def compare(open_dir: Path, closed_dir: Path) -> dict:
    open_report = _load_or_analyze(open_dir)
    closed_report = _load_or_analyze(closed_dir)

    open_ch1 = open_report.get("channels", {}).get("ch1", {})
    closed_ch1 = closed_report.get("channels", {}).get("ch1", {})

    open_bp = open_ch1.get("bandpower_abs", {}) or {}
    closed_bp = closed_ch1.get("bandpower_abs", {}) or {}
    open_rel = open_ch1.get("bandpower_rel", {}) or {}
    closed_rel = closed_ch1.get("bandpower_rel", {}) or {}

    alpha_abs_ratio = _ratio(closed_bp.get("alpha"), open_bp.get("alpha"))
    alpha_rel_delta = None
    if closed_rel.get("alpha") is not None and open_rel.get("alpha") is not None:
        alpha_rel_delta = float(closed_rel.get("alpha", 0.0) - open_rel.get("alpha", 0.0))

    warnings = []
    if alpha_abs_ratio is None:
        warnings.append("cannot_compute_alpha_ratio")
    elif alpha_abs_ratio < 1.2:
        warnings.append("no_clear_alpha_increase_eyes_closed")

    for label, ch in (("eyes_open", open_ch1), ("eyes_closed", closed_ch1)):
        if ch.get("rms_uV", 0.0) > 500.0:
            warnings.append(f"{label}_rms_nonphysiological")
        if ch.get("ptp_uV", 0.0) > 5000.0:
            warnings.append(f"{label}_ptp_nonphysiological")
        ratio_50 = ch.get("line_50_ratio_1_50")
        if ratio_50 is not None and ratio_50 > 0.25:
            warnings.append(f"{label}_high_50hz_ratio")

    state = "compatible_preliminar"
    if warnings:
        state = "dudosa"

    return {
        "state": state,
        "eyes_open_dir": str(open_dir),
        "eyes_closed_dir": str(closed_dir),
        "alpha_abs_eyes_closed_over_open": alpha_abs_ratio,
        "alpha_rel_delta_closed_minus_open": alpha_rel_delta,
        "eyes_open": {
            "diagnosis": open_report.get("diagnosis", {}).get("state"),
            "rms_uV": open_ch1.get("rms_uV"),
            "ptp_uV": open_ch1.get("ptp_uV"),
            "alpha_abs": open_bp.get("alpha"),
            "alpha_rel": open_rel.get("alpha"),
            "peak_freq_hz": open_ch1.get("peak_freq_hz"),
            "line_50_ratio_1_50": open_ch1.get("line_50_ratio_1_50"),
        },
        "eyes_closed": {
            "diagnosis": closed_report.get("diagnosis", {}).get("state"),
            "rms_uV": closed_ch1.get("rms_uV"),
            "ptp_uV": closed_ch1.get("ptp_uV"),
            "alpha_abs": closed_bp.get("alpha"),
            "alpha_rel": closed_rel.get("alpha"),
            "peak_freq_hz": closed_ch1.get("peak_freq_hz"),
            "line_50_ratio_1_50": closed_ch1.get("line_50_ratio_1_50"),
        },
        "warnings": warnings,
        "interpretation": (
            "A clean Fp1-Fp2 eyes-closed capture often shows increased alpha, "
            "but frontal montage can be dominated by blinks, EMG, and common-mode issues. "
            "Amplitude plausibility must be checked before accepting band changes as EEG."
        ),
    }


def _write_markdown(path: Path, report: dict) -> None:
    lines = [
        "# EEG eyes open/closed comparison",
        "",
        f"- State: {report['state']}",
        f"- Alpha abs ratio closed/open: {report['alpha_abs_eyes_closed_over_open']}",
        f"- Alpha relative delta closed-open: {report['alpha_rel_delta_closed_minus_open']}",
        "",
        "## Eyes open CH1",
        "",
    ]
    for key, value in report["eyes_open"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Eyes closed CH1", ""])
    for key, value in report["eyes_closed"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in report["warnings"] or ["none"])
    lines.extend(["", "## Interpretation", "", report["interpretation"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare eyes-open and eyes-closed EEG captures.")
    parser.add_argument("--open", required=True, dest="open_dir", help="Eyes-open capture directory.")
    parser.add_argument("--closed", required=True, dest="closed_dir", help="Eyes-closed capture directory.")
    parser.add_argument("--output", default="", help="Output JSON path. Defaults to captures/eyes_open_closed_comparison.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = compare(Path(args.open_dir), Path(args.closed_dir))
    out_path = Path(args.output) if args.output else PROJECT_ROOT / "captures" / "eyes_open_closed_comparison.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown(out_path.with_suffix(".md"), report)
    print(f"[compare] state={report['state']}")
    print(f"[compare] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
