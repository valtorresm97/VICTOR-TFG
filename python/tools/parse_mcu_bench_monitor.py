#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from pathlib import Path
from typing import Any


BENCH_HEADER = "[BENCH] EEG_MIDI"

PREFERRED_COLUMNS = [
    "bench_block_idx",
    "gen/s",
    "sent/s",
    "blk_enq/s",
    "blk_sent/s",
    "filt_avg_us",
    "filt_max_us_win",
    "notify_avg_us",
    "notify_eff_us/sample",
    "notify_max_us_win",
    "q",
    "qmax_win",
    "drops_win",
    "pub_burst_win",
    "lag_win",
    "catchup_win",
    "sample_iter_max_us_win",
    "loop_max_us_win",
    "pin",
    "drdy_count_now",
    "gen",
    "sent",
    "blk_enq",
    "blk_sent",
    "notify_calls",
    "qmax_global",
    "drops_total",
    "pub_burst_global",
    "notify_max_global_us",
    "loop_max_global_us",
]

SUMMARY_COLUMNS = [
    "gen/s",
    "sent/s",
    "blk_sent/s",
    "filt_avg_us",
    "filt_max_us_win",
    "notify_avg_us",
    "notify_eff_us/sample",
    "notify_max_us_win",
    "qmax_win",
    "drops_win",
    "lag_win",
    "sample_iter_max_us_win",
    "loop_max_us_win",
    "pub_burst_win",
]

LAST_COUNTER_COLUMNS = [
    "gen",
    "sent",
    "blk_enq",
    "blk_sent",
    "notify_calls",
    "qmax_global",
    "drops_total",
    "pub_burst_global",
    "notify_max_global_us",
    "loop_max_global_us",
    "drdy_count_now",
]


def parse_pairs(line: str) -> dict[str, int | float]:
    pairs: dict[str, int | float] = {}
    for key, value in re.findall(r"([A-Za-z0-9_/]+)=(-?[0-9]+(?:\.[0-9]+)?)", line):
        pairs[key] = float(value) if "." in value else int(value)
    return pairs


def parse_monitor_log(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in text.splitlines():
        if BENCH_HEADER in line:
            if current:
                blocks.append(current)
            current = {}
            continue

        if current is None:
            continue

        if any(marker in line for marker in (
            "rate   |",
            "time   |",
            "queue  |",
            "jitter |",
            "DRDY   |",
            "total  |",
            "peak   |",
        )):
            current.update(parse_pairs(line))

    if current:
        blocks.append(current)

    for idx, block in enumerate(blocks, start=1):
        block["bench_block_idx"] = idx

    return blocks


def ordered_columns(blocks: list[dict[str, Any]]) -> list[str]:
    cols: list[str] = []
    for col in PREFERRED_COLUMNS:
        if any(col in block for block in blocks):
            cols.append(col)
    for block in blocks:
        for col in block:
            if col not in cols:
                cols.append(col)
    return cols


def numeric_values(blocks: list[dict[str, Any]], key: str) -> list[float]:
    vals: list[float] = []
    for block in blocks:
        val = block.get(key)
        if isinstance(val, (int, float)):
            vals.append(float(val))
    return vals


def metric_summary(blocks: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    keys = sorted({key for block in blocks for key in block if key != "bench_block_idx"})
    for key in keys:
        vals = numeric_values(blocks, key)
        if not vals:
            continue
        out[key] = {
            "min": min(vals),
            "median": statistics.median(vals),
            "mean": statistics.fmean(vals),
            "max": max(vals),
        }
    return out


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.3f}"
    return str(value)


def write_csv(path: Path, blocks: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ordered_columns(blocks)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for block in blocks:
            writer.writerow({col: block.get(col, "") for col in cols})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, *, log_path: Path, blocks: list[dict[str, Any]], summary: dict[str, dict[str, float]], condition: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Firmware/MCU benchmark report")
    lines.append("")
    lines.append(f"- Source log: `{log_path}`")
    if condition:
        lines.append(f"- Condition: `{condition}`")
    lines.append(f"- Parsed BENCH windows: {len(blocks)}")
    lines.append("")

    last = blocks[-1] if blocks else {}
    lines.append("## Last cumulative counters")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | ---: |")
    for key in LAST_COUNTER_COLUMNS:
        if key in last:
            lines.append(f"| `{key}` | {fmt(last.get(key))} |")
    lines.append("")

    lines.append("## Window metric summary")
    lines.append("")
    lines.append("| Metric | Min | Median | Mean | Max |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for key in SUMMARY_COLUMNS:
        if key not in summary:
            continue
        s = summary[key]
        lines.append(
            f"| `{key}` | {fmt(s['min'])} | {fmt(s['median'])} | {fmt(s['mean'])} | {fmt(s['max'])} |"
        )
    lines.append("")

    table_cols = [
        "bench_block_idx",
        "gen/s",
        "sent/s",
        "blk_sent/s",
        "filt_avg_us",
        "filt_max_us_win",
        "notify_avg_us",
        "notify_max_us_win",
        "qmax_win",
        "drops_win",
        "lag_win",
        "loop_max_us_win",
    ]
    table_cols = [col for col in table_cols if any(col in block for block in blocks)]

    lines.append("## Per-window table")
    lines.append("")
    lines.append("| " + " | ".join(table_cols) + " |")
    lines.append("| " + " | ".join(["---:" for _ in table_cols]) + " |")
    for block in blocks:
        lines.append("| " + " | ".join(fmt(block.get(col, "")) for col in table_cols) + " |")
    lines.append("")

    drops_total = float(last.get("drops_total", 0) or 0)
    drops_win_max = summary.get("drops_win", {}).get("max", 0.0)
    qmax_global = float(last.get("qmax_global", 0) or 0)
    lag_max = summary.get("lag_win", {}).get("max", 0.0)

    lines.append("## Automatic interpretation")
    lines.append("")
    if drops_total == 0 and drops_win_max == 0:
        lines.append("- No TX queue drops were reported in the parsed MCU benchmark windows.")
    else:
        lines.append(f"- TX queue drops were reported: drops_total={fmt(drops_total)}, max drops_win={fmt(drops_win_max)}.")
    lines.append(f"- Maximum reported TX queue occupancy was qmax_global={fmt(qmax_global)}.")
    lines.append(f"- Maximum reported lag_win across parsed windows was {fmt(lag_max)}.")
    lines.append("- These MCU metrics should be interpreted together with the Python/Linux benchmark report over the same capture.")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse pasted Arduino Monitor [BENCH] EEG_MIDI logs into CSV/JSON/Markdown.")
    parser.add_argument("log_path", type=Path, help="Path to firmware_bench_monitor.log copied from Monitor/App Lab.")
    parser.add_argument("--out-csv", type=Path, required=True, help="Output CSV path.")
    parser.add_argument("--out-json", type=Path, required=True, help="Output JSON path.")
    parser.add_argument("--out-md", type=Path, required=True, help="Output Markdown report path.")
    parser.add_argument("--condition", default=None, help="Capture/benchmark condition name.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = args.log_path.read_text(encoding="utf-8", errors="replace")
    blocks = parse_monitor_log(text)
    if not blocks:
        raise SystemExit(
            f"No se encontraron bloques {BENCH_HEADER!r} en {args.log_path}. "
            "Copia del Monitor/App Lab desde una linea [BENCH] EEG_MIDI hasta los bloques siguientes."
        )

    summary = metric_summary(blocks)
    payload = {
        "source_log": str(args.log_path),
        "condition": args.condition,
        "parsed_windows": len(blocks),
        "last_counters": blocks[-1],
        "summary": summary,
        "windows": blocks,
    }

    write_csv(args.out_csv, blocks)
    write_json(args.out_json, payload)
    write_markdown(args.out_md, log_path=args.log_path, blocks=blocks, summary=summary, condition=args.condition)

    print(f"Parsed BENCH windows: {len(blocks)}")
    print(f"CSV: {args.out_csv}")
    print(f"JSON: {args.out_json}")
    print(f"Markdown: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
