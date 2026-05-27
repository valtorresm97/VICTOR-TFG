from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from benchmark_core import (
    RESULTS_DIR,
    REPORTS_DIR,
    atomic_write_json,
    write_csv,
    write_markdown_report,
)
from benchmark_real_capture import discover_latest_capture, run as run_real_capture


def _timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta benchmarks temporales en placa sobre una captura real EEG."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--capture-dir",
        type=str,
        help="Directorio captures/<timestamp>_<condition> con eeg_timeseries.csv.",
    )
    group.add_argument(
        "--latest-capture",
        action="store_true",
        help="Usa la captura mas reciente encontrada en captures/ o /app/captures/.",
    )
    parser.add_argument(
        "--max-blocks",
        type=int,
        default=None,
        help="Limita los bloques de la captura para una prueba rapida.",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default="real_capture",
        help="Etiqueta para los nombres de salida.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]

    if args.latest_capture:
        capture_dir = discover_latest_capture(root)
        if capture_dir is None:
            raise SystemExit(
                "No se encontro ninguna captura real. Ejecuta antes:\n"
                "python3 python/tools/capture_eeg_quality.py --condition bench_real_rest_60s --duration 60 --timeout-extra 180"
            )
    else:
        capture_dir = Path(args.capture_dir).expanduser().resolve()

    if not (capture_dir / "eeg_timeseries.csv").exists():
        raise SystemExit(f"No existe eeg_timeseries.csv en {capture_dir}")

    rows: list[dict[str, Any]] = []
    rows.extend(run_real_capture(capture_dir, max_blocks=args.max_blocks))

    ts = _timestamp()
    tag = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(args.tag))
    stem = f"{ts}_{tag}"
    json_path = RESULTS_DIR / f"{stem}_benchmark_results.json"
    csv_path = RESULTS_DIR / f"{stem}_benchmark_results.csv"
    md_path = REPORTS_DIR / f"{stem}_benchmark_report.md"

    atomic_write_json(
        json_path,
        {
            "capture_dir": str(capture_dir),
            "max_blocks": args.max_blocks,
            "results": rows,
        },
        indent=2,
    )
    write_csv(csv_path, rows)
    write_markdown_report(md_path, rows)

    print(f"[bench] capture_dir={capture_dir}")
    print(f"[bench] rows={len(rows)}")
    print(f"[bench] json={json_path}")
    print(f"[bench] csv={csv_path}")
    print(f"[bench] report={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
