from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = PROJECT_ROOT / "state"
SNAPSHOT_PATH = STATE_DIR / "snapshot.json"
CAPTURE_STATUS_PATH = STATE_DIR / "capture_status.json"
CAPTURES_ROOT = PROJECT_ROOT / "captures"
DEFAULT_FINAL_ROOT = CAPTURES_ROOT / "capturas finales"

DEFAULT_MONTAGE = "ear_eeg_ch1_only"
DEFAULT_MODEL = "modelo_captura_final"
DEFAULT_ADS_MODE = "bias_ch1_only_loff_off"


def _today() -> str:
    return datetime.now().strftime("%Y%m%d")


def _safe_text(value: str) -> str:
    return str(value).replace("\n", " ").replace("|", "/").strip()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _git_value(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=str(PROJECT_ROOT),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _session_file(session: str, subject: str) -> Path:
    return PROJECT_ROOT / "docs" / "sesiones_captura" / f"{session}_{subject}_sesion.md"


def _context_log(session: str, subject: str) -> Path:
    return PROJECT_ROOT / "logs" / "capturas" / f"{session}_{subject}_context.txt"


def _ensure_dirs(final_root: Path) -> None:
    final_root.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "docs" / "sesiones_captura").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "logs" / "capturas").mkdir(parents=True, exist_ok=True)


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def _note_base(subject: str, session: str, montage: str, model: str, ads_mode: str) -> str:
    return (
        f"subject={subject};session={session};montage={montage};"
        f"model={model};ads_mode={ads_mode}"
    )


def cmd_init(args: argparse.Namespace) -> int:
    final_root = Path(args.final_root).expanduser()
    if not final_root.is_absolute():
        final_root = PROJECT_ROOT / final_root
    _ensure_dirs(final_root)

    subject = args.subject
    session = args.session
    montage = args.montage
    model = args.model
    ads_mode = args.ads_mode

    if args.prompt:
        hora_inicio = _prompt("Hora inicio (HH:MM)")
        entorno = _prompt("Entorno (lab_quiet/classroom/home/other)", "lab_quiet")
        ch1p = _prompt("CH1P colocado en")
        ch1n = _prompt("CH1N colocado en")
        bias = _prompt("BIAS/RLD colocado en")
    else:
        hora_inicio = args.hora_inicio
        entorno = args.entorno
        ch1p = args.ch1p
        ch1n = args.ch1n
        bias = args.bias

    session_path = _session_file(session, subject)
    context_path = _context_log(session, subject)

    branch = _git_value(["branch", "--show-current"])
    commit = _git_value(["rev-parse", "HEAD"])
    dirty = "clean" if not _git_value(["status", "--short"]) else "dirty"
    python_version = sys.version.split()[0]

    session_path.write_text(
        f"# Sesion final EEG-MIDI\n\n"
        f"## Datos fijos\n\n"
        f"| Campo | Valor |\n"
        f"| --- | --- |\n"
        f"| Sujeto | `{_safe_text(subject)}` |\n"
        f"| Sesion | `{_safe_text(session)}` |\n"
        f"| Hora inicio | `{_safe_text(hora_inicio)}` |\n"
        f"| Hora fin | `PENDIENTE` |\n"
        f"| Entorno | `{_safe_text(entorno)}` |\n"
        f"| Montage | `{_safe_text(montage)}` |\n"
        f"| Modelo | `{_safe_text(model)}` |\n"
        f"| ADS_MODE | `{_safe_text(ads_mode)}` |\n"
        f"| Carpeta final | `{_safe_text(str(final_root.relative_to(PROJECT_ROOT) if final_root.is_relative_to(PROJECT_ROOT) else final_root))}` |\n"
        f"| Rama | `{_safe_text(branch)}` |\n"
        f"| Commit | `{_safe_text(commit)}` |\n"
        f"| Dirty state | `{_safe_text(dirty)}` |\n"
        f"| Python | `{_safe_text(python_version)}` |\n\n"
        f"## Electrodos\n\n"
        f"| Electrodo | Posicion |\n"
        f"| --- | --- |\n"
        f"| CH1P | `{_safe_text(ch1p)}` |\n"
        f"| CH1N | `{_safe_text(ch1n)}` |\n"
        f"| BIAS/RLD | `{_safe_text(bias)}` |\n\n"
        f"## Capturas\n\n"
        f"| Orden | Condicion | Duracion | Carpeta | EEG | Musica | Decision | Comentario |\n"
        f"| --- | --- | ---: | --- | --- | --- | --- | --- |\n",
        encoding="utf-8",
    )

    context_path.write_text(
        "\n".join(
            [
                f"subject={subject}",
                f"session={session}",
                f"hora_inicio={hora_inicio}",
                f"entorno={entorno}",
                f"montage={montage}",
                f"model={model}",
                f"ads_mode={ads_mode}",
                f"final_root={final_root}",
                f"branch={branch}",
                f"commit={commit}",
                f"dirty={dirty}",
                f"python={python_version}",
                f"ch1p={ch1p}",
                f"ch1n={ch1n}",
                f"bias={bias}",
                f"created_at={datetime.now().isoformat(timespec='seconds')}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"[session] plantilla={session_path}")
    print(f"[session] contexto={context_path}")
    return 0


def _snapshot_music_payload() -> dict[str, Any]:
    snap = _read_json(SNAPSHOT_PATH)
    status = _read_json(CAPTURE_STATUS_PATH)
    if not snap:
        return {}

    ts_monotonic = snap.get("ts_monotonic")
    elapsed = status.get("elapsed_sec")
    t0_est = None
    try:
        if ts_monotonic is not None and elapsed is not None:
            t0_est = float(ts_monotonic) - float(elapsed)
    except Exception:
        t0_est = None

    return {
        "logged_at_unix": time.time(),
        "snapshot_ts_monotonic": ts_monotonic,
        "capture_status": {
            "state": status.get("state"),
            "request_id": status.get("request_id"),
            "condition": status.get("condition"),
            "elapsed_sec": status.get("elapsed_sec"),
            "capture_dir": status.get("capture_dir"),
        },
        "capture_t0_monotonic_est": t0_est,
        "config": snap.get("config", {}),
        "status": snap.get("status", {}),
        "features": snap.get("features", {}),
        "diagnostics": snap.get("diagnostics", {}),
        "spectral_quality": snap.get("spectral_quality", {}),
        "sonification": snap.get("sonification", {}),
        "music": snap.get("music", {}),
        "midi": snap.get("midi", {}),
    }


def _music_logger(stop_event: threading.Event, out_path: Path, period_sec: float) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        while not stop_event.is_set():
            payload = _snapshot_music_payload()
            if payload:
                f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
                f.flush()
            stop_event.wait(period_sec)


def _discover_capture_dir(condition: str) -> Path | None:
    if not CAPTURES_ROOT.exists():
        return None
    candidates = []
    suffix = f"_{condition}"
    for path in CAPTURES_ROOT.iterdir():
        if path.is_dir() and path.name.endswith(suffix):
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _unique_final_dir(final_root: Path, basename: str) -> Path:
    target = final_root / basename
    if not target.exists():
        return target
    for idx in range(2, 100):
        candidate = final_root / f"{basename}_repeat{idx}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"No unique final directory available for {basename}")


def _extract_music_notes(jsonl_path: Path, notes_csv: Path, summary_json: Path, duration_sec: float) -> None:
    rows_by_key: dict[tuple, dict[str, Any]] = {}
    snapshots = 0
    snapshots_with_notes = 0

    if jsonl_path.exists():
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except Exception:
                    continue
                snapshots += 1
                t0 = payload.get("capture_t0_monotonic_est")
                music = payload.get("music", {}) or {}
                recent_notes = music.get("recent_notes", []) or []
                if recent_notes:
                    snapshots_with_notes += 1
                for note in recent_notes:
                    try:
                        abs_start = float(note.get("abs_start"))
                        abs_end = float(note.get("abs_end"))
                        pitch = int(note.get("pitch_midi"))
                        velocity = int(note.get("velocity", 0) or 0)
                        channel = int(note.get("channel", 0) or 0)
                        program = int(note.get("program", 0) or 0)
                        if t0 is not None:
                            t_start = abs_start - float(t0)
                            t_end = abs_end - float(t0)
                        else:
                            t_start = ""
                            t_end = ""
                    except Exception:
                        continue

                    if isinstance(t_start, float):
                        if t_end < -1.0 or t_start > float(duration_sec) + 5.0:
                            continue
                        t_start_value = round(t_start, 6)
                        t_end_value = round(t_end, 6)
                    else:
                        t_start_value = ""
                        t_end_value = ""

                    key = (
                        round(abs_start, 3),
                        round(abs_end, 3),
                        pitch,
                        velocity,
                        channel,
                        program,
                    )
                    rows_by_key[key] = {
                        "t_capture_start_sec": t_start_value,
                        "t_capture_end_sec": t_end_value,
                        "abs_start_monotonic": round(abs_start, 6),
                        "abs_end_monotonic": round(abs_end, 6),
                        "pitch_midi": pitch,
                        "note_name": note.get("note_name", ""),
                        "velocity": velocity,
                        "channel": channel,
                        "program": program,
                        "source_snapshot_ts_monotonic": payload.get("snapshot_ts_monotonic", ""),
                    }

    rows = sorted(
        rows_by_key.values(),
        key=lambda r: (
            float(r["t_capture_start_sec"]) if r["t_capture_start_sec"] != "" else 1e18,
            int(r["pitch_midi"]),
        ),
    )

    fieldnames = [
        "t_capture_start_sec",
        "t_capture_end_sec",
        "abs_start_monotonic",
        "abs_end_monotonic",
        "pitch_midi",
        "note_name",
        "velocity",
        "channel",
        "program",
        "source_snapshot_ts_monotonic",
    ]
    with notes_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "snapshots_total": snapshots,
        "snapshots_with_notes": snapshots_with_notes,
        "notes_total_deduplicated": len(rows),
        "music_notes_csv": str(notes_csv),
        "music_snapshots_jsonl": str(jsonl_path),
        "duration_sec": duration_sec,
        "note": "music_notes.csv is extracted from periodic state/snapshot.json music.recent_notes during the capture",
    }
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _append_capture_row(
    session_file: Path,
    order: str,
    condition: str,
    duration: float,
    final_dir: Path,
    music_notes_csv: Path,
) -> None:
    rel_dir = final_dir.relative_to(PROJECT_ROOT) if final_dir.is_relative_to(PROJECT_ROOT) else final_dir
    rel_music = music_notes_csv.relative_to(PROJECT_ROOT) if music_notes_csv.is_relative_to(PROJECT_ROOT) else music_notes_csv
    with session_file.open("a", encoding="utf-8") as f:
        f.write(
            f"| {order} | `{condition}` | {duration:g} s | `{rel_dir}` | `eeg_timeseries.csv` | `{rel_music}` | `pendiente` |  |\n"
        )


def cmd_capture(args: argparse.Namespace) -> int:
    final_root = Path(args.final_root).expanduser()
    if not final_root.is_absolute():
        final_root = PROJECT_ROOT / final_root
    _ensure_dirs(final_root)

    subject = args.subject
    session = args.session
    montage = args.montage
    model = args.model
    ads_mode = args.ads_mode
    order = args.order
    short_condition = args.condition
    duration = float(args.duration)
    instruction = args.instruction

    full_condition = f"{subject}_{session}_{montage}_{order}_{short_condition}"
    notes = _note_base(subject, session, montage, model, ads_mode)
    notes = f"{notes};condition={short_condition};order={order};instruction={instruction}"

    session_path = _session_file(session, subject)
    tmp_music_log = PROJECT_ROOT / "logs" / "capturas" / f"{session}_{subject}_{order}_{short_condition}_music_snapshots.tmp.jsonl"

    stop_event = threading.Event()
    logger_thread = threading.Thread(
        target=_music_logger,
        args=(stop_event, tmp_music_log, float(args.music_log_period)),
        daemon=True,
    )
    logger_thread.start()

    cmd = [
        sys.executable,
        "python/tools/capture_eeg_quality.py",
        "--condition",
        full_condition,
        "--duration",
        str(duration),
        "--timeout-extra",
        str(float(args.timeout_extra)),
        "--notes",
        notes,
    ]

    print(f"[capture-final] condition={full_condition}")
    print(f"[capture-final] final_root={final_root}")
    print(f"[capture-final] music_tmp={tmp_music_log}")

    try:
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    finally:
        # Capture a few final snapshots so late note_off / status updates are kept.
        time.sleep(max(0.1, float(args.music_log_period) * 2.0))
        stop_event.set()
        logger_thread.join(timeout=3.0)

    if result.returncode != 0:
        print(f"[capture-final] ERROR: capture command failed with code {result.returncode}", file=sys.stderr)
        return int(result.returncode)

    source_dir = _discover_capture_dir(full_condition)
    if source_dir is None:
        print(f"[capture-final] ERROR: capture directory not found for {full_condition}", file=sys.stderr)
        return 1

    final_dir = _unique_final_dir(final_root, source_dir.name)
    shutil.move(str(source_dir), str(final_dir))

    music_jsonl = final_dir / "music_snapshots.jsonl"
    if tmp_music_log.exists():
        shutil.move(str(tmp_music_log), str(music_jsonl))
    else:
        music_jsonl.write_text("", encoding="utf-8")

    music_notes_csv = final_dir / "music_notes.csv"
    music_summary_json = final_dir / "music_capture_summary.json"
    _extract_music_notes(music_jsonl, music_notes_csv, music_summary_json, duration_sec=duration)

    if args.analyze:
        subprocess.run([sys.executable, "python/tools/analyze_eeg_capture.py", str(final_dir)], cwd=str(PROJECT_ROOT), check=False)
        subprocess.run(
            [
                sys.executable,
                "python/tools/validate_spectral_features.py",
                str(final_dir),
                "--channel",
                "0",
                "--window-sec",
                "4",
                "--hop-samples",
                "64",
            ],
            cwd=str(PROJECT_ROOT),
            check=False,
        )

    if session_path.exists():
        _append_capture_row(session_path, order, short_condition, duration, final_dir, music_notes_csv)

    print(f"[capture-final] moved_to={final_dir}")
    print(f"[capture-final] music_snapshots={music_jsonl}")
    print(f"[capture-final] music_notes={music_notes_csv}")
    print(f"[capture-final] music_summary={music_summary_json}")
    return 0


def cmd_finish(args: argparse.Namespace) -> int:
    session_path = _session_file(args.session, args.subject)
    if not session_path.exists():
        print(f"[finish] ERROR: session file not found: {session_path}", file=sys.stderr)
        return 1
    hora_fin = args.hora_fin or _prompt("Hora fin (HH:MM)")
    decision = args.decision or _prompt("Sesion valida (si/parcial/no)", "pendiente")
    comentario = args.comentario or _prompt("Comentario final", "")
    with session_path.open("a", encoding="utf-8") as f:
        f.write(
            "\n## Cierre\n\n"
            "| Campo | Valor |\n"
            "| --- | --- |\n"
            f"| Hora fin | `{_safe_text(hora_fin)}` |\n"
            f"| Sesion valida | `{_safe_text(decision)}` |\n"
            f"| Comentario final | `{_safe_text(comentario)}` |\n"
        )
    print(f"[finish] actualizado={session_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Helper para capturas finales EEG + musica.")
    sub = parser.add_subparsers(dest="command", required=True)

    common_defaults = {
        "session": _today(),
        "montage": DEFAULT_MONTAGE,
        "model": DEFAULT_MODEL,
        "ads_mode": DEFAULT_ADS_MODE,
        "final_root": str(DEFAULT_FINAL_ROOT.relative_to(PROJECT_ROOT)),
    }

    p_init = sub.add_parser("init", help="Crea plantilla simple de sesion y log de contexto.")
    p_init.add_argument("--subject", required=True)
    p_init.add_argument("--session", default=common_defaults["session"])
    p_init.add_argument("--montage", default=common_defaults["montage"])
    p_init.add_argument("--model", default=common_defaults["model"])
    p_init.add_argument("--ads-mode", default=common_defaults["ads_mode"])
    p_init.add_argument("--final-root", default=common_defaults["final_root"])
    p_init.add_argument("--prompt", action="store_true", help="Pregunta solo los campos manuales esenciales.")
    p_init.add_argument("--hora-inicio", default="")
    p_init.add_argument("--entorno", default="lab_quiet")
    p_init.add_argument("--ch1p", default="")
    p_init.add_argument("--ch1n", default="")
    p_init.add_argument("--bias", default="")
    p_init.set_defaults(func=cmd_init)

    p_cap = sub.add_parser("capture", help="Ejecuta captura final, registra musica y mueve carpeta.")
    p_cap.add_argument("--subject", required=True)
    p_cap.add_argument("--session", default=common_defaults["session"])
    p_cap.add_argument("--montage", default=common_defaults["montage"])
    p_cap.add_argument("--model", default=common_defaults["model"])
    p_cap.add_argument("--ads-mode", default=common_defaults["ads_mode"])
    p_cap.add_argument("--final-root", default=common_defaults["final_root"])
    p_cap.add_argument("--order", required=True)
    p_cap.add_argument("--condition", required=True)
    p_cap.add_argument("--duration", type=float, required=True)
    p_cap.add_argument("--instruction", default="")
    p_cap.add_argument("--timeout-extra", type=float, default=120.0)
    p_cap.add_argument("--music-log-period", type=float, default=0.5)
    p_cap.add_argument("--no-analyze", dest="analyze", action="store_false")
    p_cap.set_defaults(func=cmd_capture, analyze=True)

    p_finish = sub.add_parser("finish", help="Cierra plantilla simple de sesion.")
    p_finish.add_argument("--subject", required=True)
    p_finish.add_argument("--session", default=common_defaults["session"])
    p_finish.add_argument("--hora-fin", default="")
    p_finish.add_argument("--decision", default="")
    p_finish.add_argument("--comentario", default="")
    p_finish.set_defaults(func=cmd_finish)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
