from __future__ import annotations

# -----------------------------------------------------------------------------
# Backend de adquisición/procesado EEG.
# Este archivo:
#   1) recibe bloques EEG desde Bridge/receiver
#   2) drena datos al procesador
#   3) calcula features live cuando la ventana/hop lo permiten
#   4) construye snapshots públicos para la UI
#   5) publica histórico/bench
#
# Refactor principal:
#   - una sola publicación live por iteración
#   - separación entre "último intento de feature" y "último feature bueno"
# -----------------------------------------------------------------------------

from arduino.app_utils import Bridge, App
import logging
import sys
import time
from collections import deque
from pathlib import Path

# -----------------------------------------------------------------------------
# Fix para App Lab:
# fuerza la inclusión del site-packages del venv local de la app en sys.path.
# Esto ayuda a encontrar numpy/scipy cuando el runtime embebido no lo hace solo.
# -----------------------------------------------------------------------------
def _inject_app_venv_site_packages():
    project_root = Path(__file__).resolve().parent.parent
    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    venv_site = project_root / ".cache" / ".venv" / "lib" / py_ver / "site-packages"

    if venv_site.exists():
        s = str(venv_site)
        if s not in sys.path:
            sys.path.insert(0, s)


_inject_app_venv_site_packages()

# -----------------------------------------------------------------------------
# Importaciones del pipeline real.
# No se modifica su lógica: solo se orquesta mejor la publicación del estado.
# -----------------------------------------------------------------------------
from eeg_signal_processor import EEGSignalProcessor
from receiver import EEGReceiver
from app_state import publish_runtime_state, publish_snapshot, publish_history

# -----------------------------------------------------------------------------
# Logging básico del backend.
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EEG_APP")

# -----------------------------------------------------------------------------
# Parámetros base del pipeline.
# -----------------------------------------------------------------------------
FS_HZ = 250
NUM_CH = 4

FEATURE_WINDOW_SEC = 4.0
FEATURE_HOP_SAMPLES = 64

SNAPSHOT_PUBLISH_PERIOD_SEC = 0.25
BENCH_PERIOD_SEC = 1.0
PRINT_PERIOD_SEC = 10.0

HISTORY_MAXLEN = 180


# -----------------------------------------------------------------------------
# Clase de métricas de rendimiento del cálculo de features.
# Mantiene acumulados totales y de ventana para bench/diagnóstico.
# -----------------------------------------------------------------------------
class MainPerfStats:
    def __init__(self):
        self.feature_calls_total = 0
        self.feature_calls_window = 0
        self.feature_ok_total = 0
        self.feature_ok_window = 0
        self.feature_empty_total = 0
        self.feature_empty_window = 0
        self.feature_fail_total = 0
        self.feature_fail_window = 0
        self.feature_time_us_accum_total = 0
        self.feature_time_us_accum_window = 0
        self.feature_time_us_max_total = 0
        self.feature_time_us_max_window = 0

    def record_feature(self, dt_us: int, ok: bool, empty: bool, failed: bool):
        """Registra métricas del último intento de feature."""
        self.feature_calls_total += 1
        self.feature_calls_window += 1
        self.feature_time_us_accum_total += dt_us
        self.feature_time_us_accum_window += dt_us

        if dt_us > self.feature_time_us_max_total:
            self.feature_time_us_max_total = dt_us
        if dt_us > self.feature_time_us_max_window:
            self.feature_time_us_max_window = dt_us

        if ok:
            self.feature_ok_total += 1
            self.feature_ok_window += 1
        if empty:
            self.feature_empty_total += 1
            self.feature_empty_window += 1
        if failed:
            self.feature_fail_total += 1
            self.feature_fail_window += 1

    def get_window_metrics(self, reset: bool = False) -> dict:
        """Devuelve las métricas de ventana y opcionalmente las resetea."""
        feature_avg_us = (
            self.feature_time_us_accum_window / self.feature_calls_window
            if self.feature_calls_window > 0 else 0.0
        )

        snap = {
            "feature_calls_window": self.feature_calls_window,
            "feature_ok_window": self.feature_ok_window,
            "feature_empty_window": self.feature_empty_window,
            "feature_fail_window": self.feature_fail_window,
            "feature_avg_us_window": feature_avg_us,
            "feature_max_us_window": self.feature_time_us_max_window,
            "feature_calls_total": self.feature_calls_total,
            "feature_ok_total": self.feature_ok_total,
            "feature_empty_total": self.feature_empty_total,
            "feature_fail_total": self.feature_fail_total,
            "feature_max_us_total": self.feature_time_us_max_total,
        }

        if reset:
            self.feature_calls_window = 0
            self.feature_ok_window = 0
            self.feature_empty_window = 0
            self.feature_fail_window = 0
            self.feature_time_us_accum_window = 0
            self.feature_time_us_max_window = 0

        return snap


# -----------------------------------------------------------------------------
# Helpers de formato para prints de bench.
# -----------------------------------------------------------------------------
def _fmt_float(v, fmt=".3e", default="n/a"):
    """Formatea un float de forma robusta."""
    if v is None:
        return default
    try:
        return format(float(v), fmt)
    except Exception:
        return default


def _fmt_ratio(v, default="n/a"):
    """Formatea un ratio decimal."""
    if v is None:
        return default
    try:
        return f"{float(v):.3f}"
    except Exception:
        return default


def _fmt_freq(v, default="n/a"):
    """Formatea una frecuencia para print."""
    if v is None:
        return default
    try:
        return f"{float(v):.2f}Hz"
    except Exception:
        return default


def _safe_float(v, default=None):
    """Convierte a float cuando es posible; si no, devuelve default."""
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        return default


# -----------------------------------------------------------------------------
# Conversión de features completos a escalares para history y consumo ligero.
# -----------------------------------------------------------------------------
def _extract_feature_scalars(feats: dict | None) -> dict:
    """Extrae los escalares principales del último feature bueno."""
    feats = feats or {}
    bp_abs = feats.get("bandpower_abs", {}) or {}
    bp_rel = feats.get("bandpower_rel", {}) or {}

    return {
        "peak_freq": _safe_float(feats.get("peak_freq")),
        "peak_delta": _safe_float(feats.get("peak_delta")),
        "peak_theta": _safe_float(feats.get("peak_theta")),
        "peak_alpha": _safe_float(feats.get("peak_alpha")),
        "peak_beta": _safe_float(feats.get("peak_beta")),
        "peak_gamma": _safe_float(feats.get("peak_gamma")),
        "rms": _safe_float(feats.get("rms")),
        "bp_abs_delta": _safe_float(bp_abs.get("delta")),
        "bp_abs_theta": _safe_float(bp_abs.get("theta")),
        "bp_abs_alpha": _safe_float(bp_abs.get("alpha")),
        "bp_abs_beta": _safe_float(bp_abs.get("beta")),
        "bp_abs_gamma": _safe_float(bp_abs.get("gamma")),
        "bp_rel_delta": _safe_float(bp_rel.get("delta")),
        "bp_rel_theta": _safe_float(bp_rel.get("theta")),
        "bp_rel_alpha": _safe_float(bp_rel.get("alpha")),
        "bp_rel_beta": _safe_float(bp_rel.get("beta")),
        "bp_rel_gamma": _safe_float(bp_rel.get("gamma")),
    }


# -----------------------------------------------------------------------------
# Estructura del histórico ligero de bench.
# -----------------------------------------------------------------------------
def _new_history(maxlen: int = HISTORY_MAXLEN) -> dict:
    """Crea la estructura circular de history."""
    keys = [
        "t",
        "rx_frame_rate_hz",
        "rx_block_rate_hz",
        "queue_frames_current",
        "queue_blocks_current",
        "queue_drops_blocks_window",
        "queue_drops_frames_window",
        "lost_frames_window",
        "lost_blocks_window",
        "block_callback_avg_us_window",
        "drain_avg_us_window",
        "feature_avg_us_window",
        "feature_calls_window",
        "last_feature_dt_us",
        "peak_freq",
        "rms",
        "bp_rel_delta",
        "bp_rel_theta",
        "bp_rel_alpha",
        "bp_rel_beta",
        "bp_rel_gamma",
        "bp_abs_delta",
        "bp_abs_theta",
        "bp_abs_alpha",
        "bp_abs_beta",
        "bp_abs_gamma",
    ]
    return {k: deque(maxlen=maxlen) for k in keys}


def _append_history_value(history_deque: deque, value):
    """Añade un valor al histórico, guardando None cuando no haya dato válido."""
    history_deque.append(None if value is None else value)


# -----------------------------------------------------------------------------
# Estado global del backend.
# Hay cuatro grupos distintos:
#   1) estado del último feature bueno
#   2) estado del último intento de feature
#   3) estado de snapshot live publicado
#   4) estado de scheduling / bench
# -----------------------------------------------------------------------------
app_perf = MainPerfStats()

# --- último feature bueno realmente mostrado/publicable ---
_last_good_feats = {}
_last_good_feature_seq = 0
_last_good_feature_update_monotonic = 0.0

# --- último intento de feature (puede ser ok, empty o failed) ---
_last_feature_status = "never"
_last_feature_error = ""
_last_feature_dt_us = 0
_feature_attempt_seq = 0
_last_feature_attempt_update_monotonic = 0.0

# --- último snapshot live publicado a la UI ---
_latest_snapshot = {}

# --- history circular para bench / plots posteriores ---
_history = _new_history()

# --- marcadores de frescura reales de ingesta ---
_last_ingest_update_monotonic = 0.0

# --- control temporal de publicaciones / bench / prints ---
_last_snapshot_publish_t = 0.0
_last_bench_t = 0.0
_last_print_t = 0.0

# --- firmas del último snapshot live publicado, para evitar republishes inútiles ---
_last_published_rx_frames_total = -1
_last_published_ingested_total = -1
_last_published_feature_attempt_seq = -1
_last_published_last_good_feature_seq = -1

# --- estado del scheduling de ventana/hop ---
_samples_since_feature = 0
_window_was_ready = False

# -----------------------------------------------------------------------------
# Instancias reales del procesador y del receiver.
# No se modifica su lógica interna.
# -----------------------------------------------------------------------------
proc = EEGSignalProcessor(
    fs=FS_HZ,
    num_channels=NUM_CH,
    buffer_sec=10.0,
    psd_window_sec=FEATURE_WINDOW_SEC,
    window_type="hann",
    welch_overlap=0.5,
)

rx = EEGReceiver(fs_hz=FS_HZ, num_ch=NUM_CH, queue_max=512)

# -----------------------------------------------------------------------------
# Exposición de callbacks del lado Linux/Bridge.
# -----------------------------------------------------------------------------
Bridge.provide("linux_started", rx.linux_started)
Bridge.provide("eeg_block_uV", rx.eeg_block_uV)


# -----------------------------------------------------------------------------
# Construcción del snapshot runtime.
# Importante:
#   - no publica
#   - no muta el último snapshot live
#   - solo empaqueta el estado actual del backend
# -----------------------------------------------------------------------------
def build_runtime_snapshot(reset_window_metrics: bool = False) -> dict:
    """Construye un snapshot consistente del estado actual del backend."""
    now_mono = time.monotonic()
    rxm = rx.get_window_metrics(reset=reset_window_metrics)
    fm = app_perf.get_window_metrics(reset=reset_window_metrics)
    bs = proc.get_buffer_status(window_sec=FEATURE_WINDOW_SEC)
    has_good_feats = bool(_last_good_feats)
    queue_frames = int(rxm.get("queue_frames_current", 0) or 0)
    queue_warn_frames = int(FS_HZ * 1.0)   # ~1s backlog
    queue_crit_frames = int(FS_HZ * 2.0)   # ~2s backlog
    lost_or_drop_window = (
        int(rxm.get("lost_frames_window", 0) or 0)
        + int(rxm.get("queue_drops_frames_window", 0) or 0)
        + int(rxm.get("malformed_blocks_window", 0) or 0)
        + int(rxm.get("invalid_status_window", 0) or 0)
    )

    if _last_feature_status == "failed":
        state_text = "feature_failed"
    elif bs.get("window_ready"):
        state_text = "running"
    else:
        state_text = "filling_window"

    snapshot = {
        "ts_monotonic": now_mono,
        "config": {
            "fs_hz": FS_HZ,
            "num_ch": NUM_CH,
            "feature_window_sec": FEATURE_WINDOW_SEC,
            "feature_hop_samples": FEATURE_HOP_SAMPLES,
            "snapshot_publish_period_sec": SNAPSHOT_PUBLISH_PERIOD_SEC,
            "bench_period_sec": BENCH_PERIOD_SEC,
            "print_period_sec": PRINT_PERIOD_SEC,
            "psd_method": "multitaper",
            "channel_idx": 0,
        },
        "status": {
            "state_text": state_text,
            "window_ready": bool(bs.get("window_ready", False)),
            "has_good_features": has_good_feats,
            # -----------------------------------------------------------------
            # Compatibilidad: estos campos siguen existiendo, pero ahora se
            # interpretan como "último intento de feature".
            # -----------------------------------------------------------------
            "last_feature_status": _last_feature_status,
            "last_feature_error": _last_feature_error,
            "last_feature_dt_us": _last_feature_dt_us,
            "last_feature_update_monotonic": (
                _last_feature_attempt_update_monotonic
                if _last_feature_attempt_update_monotonic > 0
                else None
            ),
            # -----------------------------------------------------------------
            # Nuevos campos: separan intento y último feature bueno.
            # -----------------------------------------------------------------
            "feature_attempt_seq": _feature_attempt_seq,
            "last_feature_attempt_update_monotonic": (
                _last_feature_attempt_update_monotonic
                if _last_feature_attempt_update_monotonic > 0
                else None
            ),
            "last_good_feature_seq": _last_good_feature_seq,
            "last_good_feature_update_monotonic": (
                _last_good_feature_update_monotonic
                if _last_good_feature_update_monotonic > 0
                else None
            ),
            "stream_health": (
                "critical" if (queue_frames >= queue_crit_frames or lost_or_drop_window > 0)
                else "warning" if queue_frames >= queue_warn_frames
                else "ok"
            ),
        },
        "runtime": {
            "samples_since_feature": _samples_since_feature,
            "window_was_ready": _window_was_ready,
            "queue_warn_frames": queue_warn_frames,
            "queue_crit_frames": queue_crit_frames,
            "lost_or_drop_window": lost_or_drop_window,
            "last_ingest_update_monotonic": (
                _last_ingest_update_monotonic if _last_ingest_update_monotonic > 0 else None
            ),
        },
        "rx": rxm,
        "feature_perf": fm,
        "buffer": bs,
        "features": {
            "last_good": dict(_last_good_feats) if _last_good_feats else {},
            "scalars": _extract_feature_scalars(_last_good_feats),
        },
    }

    return snapshot


# -----------------------------------------------------------------------------
# Actualización del history desde un snapshot.
# El history solo usa escalares ligeros y métricas resumidas.
# -----------------------------------------------------------------------------
def update_history_from_snapshot(snapshot: dict):
    """Actualiza la serie histórica ligera a partir de un snapshot."""
    t = snapshot.get("ts_monotonic")
    rxm = snapshot.get("rx", {}) or {}
    fm = snapshot.get("feature_perf", {}) or {}
    scalars = ((snapshot.get("features", {}) or {}).get("scalars", {}) or {})
    status = snapshot.get("status", {}) or {}

    _append_history_value(_history["t"], t)
    _append_history_value(_history["rx_frame_rate_hz"], rxm.get("rx_frame_rate_hz"))
    _append_history_value(_history["rx_block_rate_hz"], rxm.get("rx_block_rate_hz"))
    _append_history_value(_history["queue_frames_current"], rxm.get("queue_frames_current"))
    _append_history_value(_history["queue_blocks_current"], rxm.get("queue_blocks_current"))
    _append_history_value(_history["queue_drops_blocks_window"], rxm.get("queue_drops_blocks_window"))
    _append_history_value(_history["queue_drops_frames_window"], rxm.get("queue_drops_frames_window"))
    _append_history_value(_history["lost_frames_window"], rxm.get("lost_frames_window"))
    _append_history_value(_history["lost_blocks_window"], rxm.get("lost_blocks_window"))
    _append_history_value(_history["block_callback_avg_us_window"], rxm.get("block_callback_avg_us_window"))
    _append_history_value(_history["drain_avg_us_window"], rxm.get("drain_avg_us_window"))
    _append_history_value(_history["feature_avg_us_window"], fm.get("feature_avg_us_window"))
    _append_history_value(_history["feature_calls_window"], fm.get("feature_calls_window"))
    _append_history_value(_history["last_feature_dt_us"], status.get("last_feature_dt_us"))

    for k in (
        "peak_freq",
        "rms",
        "bp_rel_delta",
        "bp_rel_theta",
        "bp_rel_alpha",
        "bp_rel_beta",
        "bp_rel_gamma",
        "bp_abs_delta",
        "bp_abs_theta",
        "bp_abs_alpha",
        "bp_abs_beta",
        "bp_abs_gamma",
    ):
        _append_history_value(_history[k], scalars.get(k))


def get_history() -> dict:
    """Devuelve una copia serializable del histórico actual."""
    return {k: list(v) for k, v in _history.items()}


# -----------------------------------------------------------------------------
# Marcado y firma del último snapshot live publicado.
# Esto define el ownership del snapshot que consume la UI.
# -----------------------------------------------------------------------------
def _mark_live_snapshot_published(snapshot: dict):
    """Registra el último snapshot live publicado y su firma de cambio."""
    global _latest_snapshot
    global _last_snapshot_publish_t
    global _last_published_rx_frames_total
    global _last_published_ingested_total
    global _last_published_feature_attempt_seq
    global _last_published_last_good_feature_seq

    _latest_snapshot = snapshot
    _last_snapshot_publish_t = time.monotonic()
    _last_published_rx_frames_total = rx.rx_frames_total
    _last_published_ingested_total = proc.total_samples_ingested
    _last_published_feature_attempt_seq = _feature_attempt_seq
    _last_published_last_good_feature_seq = _last_good_feature_seq


def _live_snapshot_payload_changed() -> bool:
    """
    Decide si el payload live ha cambiado lo suficiente para justificar publish.

    Se consideran cambios relevantes:
      - nueva ingesta total
      - nuevos frames RX
      - nuevo intento de feature
      - nuevo último feature bueno
    """
    return (
        rx.rx_frames_total != _last_published_rx_frames_total
        or proc.total_samples_ingested != _last_published_ingested_total
        or _feature_attempt_seq != _last_published_feature_attempt_seq
        or _last_good_feature_seq != _last_published_last_good_feature_seq
    )


# -----------------------------------------------------------------------------
# Publicación live del snapshot.
# Refactor clave:
#   - se usa UN solo camino live por iteración
#   - no se publica dos veces cuando hay feature nueva
# -----------------------------------------------------------------------------
def publish_live_snapshot(reset_window_metrics: bool = False) -> dict:
    """Construye y publica el snapshot live actual."""
    snapshot = build_runtime_snapshot(reset_window_metrics=reset_window_metrics)
    publish_snapshot(snapshot)
    _mark_live_snapshot_published(snapshot)
    return snapshot


def publish_live_snapshot_if_due(
    force: bool = False,
    period_s: float = SNAPSHOT_PUBLISH_PERIOD_SEC,
) -> dict | None:
    """
    Publica snapshot live solo si toca por periodo o si hay cambio relevante.

    force=True se usa cuando ha ocurrido un intento de feature o cuando queremos
    forzar el primer snapshot útil, pero aun así solo se publica una vez.
    """
    now = time.monotonic()

    if not force:
        if not _live_snapshot_payload_changed():
            return None
        if _latest_snapshot and (now - _last_snapshot_publish_t) < period_s:
            return None

    return publish_live_snapshot(reset_window_metrics=False)


# -----------------------------------------------------------------------------
# Publicación de bench/history.
# No debe redefinir el significado del último snapshot live publicado.
# -----------------------------------------------------------------------------
def publish_bench_if_due(period_s: float = BENCH_PERIOD_SEC) -> dict | None:
    """Publica el history resumido a la cadencia de bench."""
    global _last_bench_t

    now = time.monotonic()
    if (now - _last_bench_t) < period_s:
        return None

    _last_bench_t = now

    snapshot = build_runtime_snapshot(reset_window_metrics=True)
    update_history_from_snapshot(snapshot)
    publish_history(get_history())
    return snapshot


# -----------------------------------------------------------------------------
# Print de bench/diagnóstico por consola.
# Sigue usando el estado actual, pero ahora con semántica más clara.
# -----------------------------------------------------------------------------
def print_runtime_snapshot(snapshot: dict):
    """Imprime un resumen del estado del backend por consola."""
    rxm = snapshot.get("rx", {}) or {}
    fm = snapshot.get("feature_perf", {}) or {}
    bs = snapshot.get("buffer", {}) or {}
    status = snapshot.get("status", {}) or {}

    feats = ((snapshot.get("features", {}) or {}).get("last_good", {}) or {})
    bp_abs = feats.get("bandpower_abs", {}) or {}
    bp_rel = feats.get("bandpower_rel", {}) or {}

    print("", flush=True)
    print("============================================================", flush=True)
    print("[PYBENCH] EEG_MIDI / PYTHON DSP", flush=True)
    print("------------------------------------------------------------", flush=True)

    print(
        "  STATUS   | "
        f"state={status.get('state_text', 'n/a')}  "
        f"attempt={status.get('last_feature_status', 'n/a')}  "
        f"attempt_dt={status.get('last_feature_dt_us', 0)}us  "
        f"good_seq={status.get('last_good_feature_seq', 0)}",
        flush=True,
    )

    print(
        "  RX/QUEUE | "
        f"frx={rxm.get('rx_frame_rate_hz', 0.0):.1f}Hz  "
        f"brx={rxm.get('rx_block_rate_hz', 0.0):.1f}Hz  "
        f"qblk={rxm.get('queue_blocks_current', 0)}/{rxm.get('queue_blocks_capacity', 0)}  "
        f"qfrm={rxm.get('queue_frames_current', 0)}  "
        f"qblk_max={rxm.get('queue_max_blocks_window', 0)}  "
        f"qfrm_max={rxm.get('queue_max_frames_window', 0)}",
        flush=True,
    )

    print(
        "  ERRORS   | "
        f"drop_blk={rxm.get('queue_drops_blocks_window', 0)}  "
        f"drop_frm={rxm.get('queue_drops_frames_window', 0)}  "
        f"lost_f={rxm.get('lost_frames_window', 0)}  "
        f"lost_b={rxm.get('lost_blocks_window', 0)}  "
        f"mal_blk={rxm.get('malformed_blocks_window', 0)}  "
        f"blk_mis={rxm.get('block_seq_mismatch_window', 0)}",
        flush=True,
    )

    print(
        "  CALLBACK | "
        f"cb_b_avg={rxm.get('block_callback_avg_us_window', 0.0):.1f}us  "
        f"cb_b_max={rxm.get('block_callback_max_us_window', 0)}us",
        flush=True,
    )

    print(
        "  DRAIN    | "
        f"calls={rxm.get('drain_calls_window', 0)}  "
        f"blk={rxm.get('drain_blocks_window', 0)}  "
        f"frm={rxm.get('drain_frames_window', 0)}  "
        f"avg={rxm.get('drain_avg_us_window', 0.0):.1f}us  "
        f"eff_blk={rxm.get('drain_eff_us_per_block_window', 0.0):.2f}us/blk  "
        f"eff_frm={rxm.get('drain_eff_us_per_frame_window', 0.0):.2f}us/frame",
        flush=True,
    )

    print(
        "  FEATURES | "
        f"calls={fm.get('feature_calls_window', 0)}  "
        f"ok={fm.get('feature_ok_window', 0)}  "
        f"empty={fm.get('feature_empty_window', 0)}  "
        f"fail={fm.get('feature_fail_window', 0)}  "
        f"avg={fm.get('feature_avg_us_window', 0.0):.1f}us  "
        f"max={fm.get('feature_max_us_window', 0)}us  "
        f"psd=multitaper",
        flush=True,
    )

    print(
        "  WINDOW   | "
        f"buf={bs.get('min_seconds', 0.0):.2f}s/{bs.get('needed_seconds', 0.0):.2f}s  "
        f"ready={int(bool(bs.get('window_ready', False)))}  "
        f"hop={FEATURE_HOP_SAMPLES}  "
        f"pend={_samples_since_feature}",
        flush=True,
    )

    print("------------------------------------------------------------", flush=True)

    if feats:
        print(
            "  BAND ABS | "
            f"delta={_fmt_float(bp_abs.get('delta'))}  "
            f"theta={_fmt_float(bp_abs.get('theta'))}  "
            f"alpha={_fmt_float(bp_abs.get('alpha'))}  "
            f"beta={_fmt_float(bp_abs.get('beta'))}  "
            f"gamma={_fmt_float(bp_abs.get('gamma'))}",
            flush=True,
        )

        print(
            "  BAND REL | "
            f"delta={_fmt_ratio(bp_rel.get('delta'))}  "
            f"theta={_fmt_ratio(bp_rel.get('theta'))}  "
            f"alpha={_fmt_ratio(bp_rel.get('alpha'))}  "
            f"beta={_fmt_ratio(bp_rel.get('beta'))}  "
            f"gamma={_fmt_ratio(bp_rel.get('gamma'))}",
            flush=True,
        )

        print(
            "  PEAKS    | "
            f"global={_fmt_freq(feats.get('peak_freq'))}  "
            f"delta={_fmt_freq(feats.get('peak_delta'))}  "
            f"theta={_fmt_freq(feats.get('peak_theta'))}  "
            f"alpha={_fmt_freq(feats.get('peak_alpha'))}  "
            f"beta={_fmt_freq(feats.get('peak_beta'))}  "
            f"gamma={_fmt_freq(feats.get('peak_gamma'))}",
            flush=True,
        )

        print(
            "  RMS      | "
            f"rms={_fmt_float(feats.get('rms'))}",
            flush=True,
        )
    else:
        print("  DSP      | filling window...", flush=True)

    if status.get("last_feature_error"):
        print("  LAST ERR | " f"{status.get('last_feature_error')}", flush=True)

    print("============================================================", flush=True)


def print_perf_if_due(snapshot: dict | None = None, period_s: float = PRINT_PERIOD_SEC):
    """Hace print periódico de bench/estado si toca por tiempo."""
    global _last_print_t

    now = time.monotonic()
    if (now - _last_print_t) < period_s:
        return

    _last_print_t = now

    if snapshot is None:
        snapshot = build_runtime_snapshot(reset_window_metrics=False)

    print_runtime_snapshot(snapshot)


# -----------------------------------------------------------------------------
# Bucle principal del backend.
# Refactor clave:
#   - una sola decisión de publish live al final
#   - separación limpia entre ingestión, scheduling, intento y publicación
# -----------------------------------------------------------------------------
def loop():
    global _last_good_feats
    global _last_good_feature_seq, _last_good_feature_update_monotonic
    global _last_feature_status, _last_feature_error, _last_feature_dt_us
    global _feature_attempt_seq, _last_feature_attempt_update_monotonic
    global _samples_since_feature, _window_was_ready
    global _last_ingest_update_monotonic
    global _last_bench_t

    # -------------------------------------------------------------------------
    # 1) Drenado de bloques del receiver al procesador.
    # -------------------------------------------------------------------------
    _, drained_frames = rx.drain_blocks_to_processor(proc, max_blocks=16)

    if drained_frames > 0:
        _last_ingest_update_monotonic = time.monotonic()

    # -------------------------------------------------------------------------
    # 2) Scheduling del cálculo de features:
    #    - primera vez cuando la ventana queda lista
    #    - luego por hop de muestras
    # -------------------------------------------------------------------------
    window_ready = proc.is_window_ready(window_sec=FEATURE_WINDOW_SEC)
    need_feature = False

    if window_ready:
        if not _window_was_ready:
            _window_was_ready = True
            _samples_since_feature = 0
            need_feature = True
        else:
            _samples_since_feature += drained_frames
            if _samples_since_feature >= FEATURE_HOP_SAMPLES:
                _samples_since_feature -= FEATURE_HOP_SAMPLES
                need_feature = True
    else:
        _window_was_ready = False
        _samples_since_feature = 0

    # -------------------------------------------------------------------------
    # 3) Intento de cálculo de features.
    #    Aquí distinguimos:
    #      - intento (siempre que se ejecuta compute_live_features)
    #      - último good feature (solo si feats no está vacío)
    # -------------------------------------------------------------------------
    feature_attempt_happened = False

    if need_feature:
        feature_attempt_happened = True
        t0_us = time.perf_counter_ns() // 1000

        ok = False
        empty = False
        failed = False

        try:
            feats = proc.compute_live_features(
                channel_idx=0,
                window_sec=FEATURE_WINDOW_SEC,
                psd_method="multitaper",
            )

            _feature_attempt_seq += 1
            _last_feature_attempt_update_monotonic = time.monotonic()

            if feats:
                _last_good_feats = feats
                _last_good_feature_seq += 1
                _last_good_feature_update_monotonic = _last_feature_attempt_update_monotonic

                _last_feature_status = "ok"
                _last_feature_error = ""
                ok = True
            else:
                _last_feature_status = "empty"
                _last_feature_error = ""
                empty = True

        except Exception as e:
            logger.exception(f"DSP error: {e}")

            _feature_attempt_seq += 1
            _last_feature_attempt_update_monotonic = time.monotonic()

            _last_feature_status = "failed"
            _last_feature_error = str(e)
            failed = True

        _last_feature_dt_us = (time.perf_counter_ns() // 1000) - t0_us
        app_perf.record_feature(
            dt_us=_last_feature_dt_us,
            ok=ok,
            empty=empty,
            failed=failed,
        )

    # -------------------------------------------------------------------------
    # 4) Primera publicación:
    #    Si aún no existe snapshot live, publicamos uno inicial y además history.
    # -------------------------------------------------------------------------
    live_snapshot = None

    if not _latest_snapshot:
        snapshot = build_runtime_snapshot(reset_window_metrics=False)
        update_history_from_snapshot(snapshot)
        publish_runtime_state(snapshot, get_history())
        _mark_live_snapshot_published(snapshot)
        _last_bench_t = time.monotonic()
        live_snapshot = snapshot
    else:
        # ---------------------------------------------------------------------
        # 5) Publicación live normal:
        #    - una sola vez por iteración
        #    - force si hubo intento de feature
        # ---------------------------------------------------------------------
        live_snapshot = publish_live_snapshot_if_due(
            force=feature_attempt_happened,
            period_s=SNAPSHOT_PUBLISH_PERIOD_SEC,
        )

    # -------------------------------------------------------------------------
    # 6) Publicación de bench/history independiente del snapshot live.
    # -------------------------------------------------------------------------
    bench_snapshot = publish_bench_if_due(period_s=BENCH_PERIOD_SEC)

    # -------------------------------------------------------------------------
    # 7) Print periódico de diagnóstico.
    #    Se prioriza bench_snapshot si existe; si no, el último live generado.
    # -------------------------------------------------------------------------
    print_perf_if_due(
        snapshot=bench_snapshot if bench_snapshot is not None else live_snapshot,
        period_s=PRINT_PERIOD_SEC,
    )

    # -------------------------------------------------------------------------
    # 8) Pequeña pausa cooperativa del loop.
    # -------------------------------------------------------------------------
    time.sleep(0.02)


# -----------------------------------------------------------------------------
# Arranque del loop principal del backend.
# -----------------------------------------------------------------------------
App.run(user_loop=loop)
