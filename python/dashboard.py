from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from app_state import ensure_state_dir, read_snapshot, clear_runtime_state

try:
    from streamlit_echarts import st_echarts, JsCode
    ECHARTS_AVAILABLE = True
except Exception:
    st_echarts = None
    JsCode = None
    ECHARTS_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON_DIR = PROJECT_ROOT / "python"
STATE_DIR = PROJECT_ROOT / "state"
BACKEND_PID_PATH = STATE_DIR / "backend.pid"
BACKEND_STDOUT_PATH = STATE_DIR / "backend_stdout.log"
BACKEND_STDERR_PATH = STATE_DIR / "backend_stderr.log"

FAST_FEATURES_PERIOD_SEC = 0.25
STATUS_PERIOD_SEC = 0.90
DIAG_PERIOD_SEC = 1.20
SNAPSHOT_MEMO_TTL_SEC = 0.08


# -----------------------------------------------------------------------------
# Helpers de formato
# -----------------------------------------------------------------------------
def _fmt(v, nd=3, default="n/a"):
    if v is None:
        return default
    try:
        return f"{float(v):.{nd}f}"
    except Exception:
        return default


def _fmt_sci(v, default="n/a"):
    if v is None:
        return default
    try:
        return f"{float(v):.3e}"
    except Exception:
        return default


def _fmt_hz(v, default="n/a"):
    if v is None:
        return default
    try:
        return f"{float(v):.2f} Hz"
    except Exception:
        return default


def _fmt_us(v, default="n/a"):
    if v is None:
        return default
    try:
        return f"{float(v):.1f} us"
    except Exception:
        return default


# -----------------------------------------------------------------------------
# Backend process helpers
# -----------------------------------------------------------------------------
def _read_pid() -> int | None:
    try:
        txt = BACKEND_PID_PATH.read_text(encoding="utf-8").strip()
        if not txt:
            return None
        return int(txt)
    except Exception:
        return None


def _pid_is_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _start_backend_if_needed() -> tuple[bool, str]:
    ensure_state_dir()

    pid = _read_pid()
    if _pid_is_alive(pid):
        return True, f"Backend activo (pid={pid})"

    clear_runtime_state()

    backend_path = PYTHON_DIR / "backend_service.py"
    if not backend_path.exists():
        return False, f"No existe backend_service.py en {backend_path}"

    stdout_f = open(BACKEND_STDOUT_PATH, "ab")
    stderr_f = open(BACKEND_STDERR_PATH, "ab")

    proc = subprocess.Popen(
        [sys.executable, str(backend_path)],
        cwd=str(PYTHON_DIR),
        stdout=stdout_f,
        stderr=stderr_f,
        start_new_session=True,
    )

    BACKEND_PID_PATH.write_text(str(proc.pid), encoding="utf-8")
    return True, f"Backend lanzado (pid={proc.pid})"


def _stop_backend() -> tuple[bool, str]:
    pid = _read_pid()

    if not _pid_is_alive(pid):
        try:
            BACKEND_PID_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        clear_runtime_state()
        return True, "Backend ya parado"

    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)

        if _pid_is_alive(pid):
            os.kill(pid, signal.SIGKILL)

        BACKEND_PID_PATH.unlink(missing_ok=True)
        clear_runtime_state()
        return True, f"Backend detenido (pid={pid})"
    except Exception as e:
        return False, f"No se pudo detener backend: {e}"


# -----------------------------------------------------------------------------
# Estado UI
# -----------------------------------------------------------------------------
def _init_ui_state(st):
    if "ui_last_valid_snapshot" not in st.session_state:
        st.session_state.ui_last_valid_snapshot = None

    if "ui_last_snapshot_source" not in st.session_state:
        st.session_state.ui_last_snapshot_source = "none"

    if "ui_snapshot_memo" not in st.session_state:
        st.session_state.ui_snapshot_memo = None

    if "ui_snapshot_memo_loaded_at" not in st.session_state:
        st.session_state.ui_snapshot_memo_loaded_at = 0.0

    if "ui_last_rendered_good_seq" not in st.session_state:
        st.session_state.ui_last_rendered_good_seq = -1

    if "ui_last_echart_options" not in st.session_state:
        st.session_state.ui_last_echart_options = None

    if "ui_booting" not in st.session_state:
        st.session_state.ui_booting = False

    if "ui_boot_started_at" not in st.session_state:
        st.session_state.ui_boot_started_at = 0.0


def _clear_ui_snapshot_cache(st):
    st.session_state.ui_last_valid_snapshot = None
    st.session_state.ui_last_snapshot_source = "none"
    st.session_state.ui_snapshot_memo = None
    st.session_state.ui_snapshot_memo_loaded_at = 0.0
    st.session_state.ui_last_rendered_good_seq = -1
    st.session_state.ui_last_echart_options = None


# -----------------------------------------------------------------------------
# Snapshot helpers
# -----------------------------------------------------------------------------
def _load_snapshot_from_disk_memoized(st):
    now = time.monotonic()
    last_t = st.session_state.get("ui_snapshot_memo_loaded_at", 0.0)

    if (now - last_t) < SNAPSHOT_MEMO_TTL_SEC:
        return st.session_state.get("ui_snapshot_memo")

    snap = read_snapshot(default=None)
    st.session_state.ui_snapshot_memo = snap
    st.session_state.ui_snapshot_memo_loaded_at = now
    return snap


def _load_snapshot_for_render(st) -> tuple[bool, dict, str]:
    pid = _read_pid()
    backend_alive = _pid_is_alive(pid)

    if not backend_alive:
        return False, {}, "none"

    live_snapshot = _load_snapshot_from_disk_memoized(st)

    if isinstance(live_snapshot, dict) and live_snapshot:
        st.session_state.ui_last_valid_snapshot = live_snapshot
        st.session_state.ui_last_snapshot_source = "live"
        return True, live_snapshot, "live"

    cached_snapshot = st.session_state.get("ui_last_valid_snapshot")
    if isinstance(cached_snapshot, dict) and cached_snapshot:
        st.session_state.ui_last_snapshot_source = "cached"
        return True, cached_snapshot, "cached"

    st.session_state.ui_last_snapshot_source = "none"
    return True, {}, "none"


def _snapshot_is_ready(snapshot: dict) -> bool:
    if not snapshot:
        return False
    status = snapshot.get("status", {}) or {}
    last_good = ((snapshot.get("features", {}) or {}).get("last_good", {}) or {})
    return bool(status.get("window_ready", False)) and bool(last_good)


# -----------------------------------------------------------------------------
# Feature helpers
# -----------------------------------------------------------------------------
def _band_rel_dict(last_good: dict):
    return last_good.get("bandpower_rel", {}) or {}


def _band_abs_dict(last_good: dict):
    return last_good.get("bandpower_abs", {}) or {}


def _dominant_band(last_good: dict) -> tuple[str, float | None]:
    bp = _band_rel_dict(last_good)
    if not bp:
        return "n/a", None
    try:
        band = max(bp, key=bp.get)
        return band, bp.get(band)
    except Exception:
        return "n/a", None


def _published_snapshot_age_s(snapshot: dict) -> float | None:
    t_pub = snapshot.get("published_at_unix")
    if t_pub is None:
        return None
    try:
        return max(0.0, time.time() - float(t_pub))
    except Exception:
        return None


def _estimated_event_age_s(snapshot: dict, event_monotonic) -> float | None:
    if event_monotonic is None:
        return None
    try:
        t_pub = snapshot.get("published_at_unix")
        t_snap_mono = snapshot.get("ts_monotonic")
        if t_pub is None or t_snap_mono is None:
            return None

        publish_delay = max(0.0, time.time() - float(t_pub))
        age_at_snapshot = max(0.0, float(t_snap_mono) - float(event_monotonic))
        return age_at_snapshot + publish_delay
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Render startup / loading
# -----------------------------------------------------------------------------
def _render_startup_status(st, snapshot: dict | None, backend_alive: bool):
    if not backend_alive:
        st.info("Pulsa Start backend para iniciar adquisición y procesamiento EEG.")
        return

    if not snapshot:
        st.info("Iniciando backend...")
        st.progress(15)
        return

    status = snapshot.get("status", {}) or {}
    buffer = snapshot.get("buffer", {}) or {}

    state_text = status.get("state_text", "n/a")
    ready = bool(status.get("window_ready", False))
    min_sec = buffer.get("min_seconds")
    need_sec = buffer.get("needed_seconds")

    if state_text == "feature_failed":
        st.error("El backend está activo, pero el último intento de cálculo ha fallado.")
        return

    if not ready:
        st.warning("Filling window… esperando a completar la ventana de análisis.")
        if min_sec is not None and need_sec:
            try:
                ratio = max(0.0, min(1.0, float(min_sec) / float(need_sec)))
                st.progress(ratio)
                st.caption(f"Ventana disponible: {float(min_sec):.2f}s / {float(need_sec):.2f}s")
            except Exception:
                pass
        return

    st.success("Sistema running. Ventana lista y snapshot disponible.")


def _render_boot_screen(st, snapshot: dict | None, backend_alive: bool):
    boot_started_at = st.session_state.get("ui_boot_started_at", 0.0)
    elapsed = max(0.0, time.monotonic() - boot_started_at) if boot_started_at else 0.0

    wrap = st.container()
    with wrap:
        st.markdown("## Cargando sistema EEG...")
        st.caption("Esperando a que backend, buffer y features estén listos antes de mostrar la interfaz.")

        if not backend_alive:
            st.info("Arrancando proceso backend...")
            st.progress(8)
            return

        if not snapshot:
            st.info("Backend activo. Esperando primer snapshot...")
            st.progress(22)
            if elapsed > 2.0:
                st.caption("Primer arranque en curso...")
            return

        status = snapshot.get("status", {}) or {}
        buffer = snapshot.get("buffer", {}) or {}
        last_good = ((snapshot.get("features", {}) or {}).get("last_good", {}) or {})

        if status.get("state_text") == "feature_failed":
            st.error("El backend arrancó, pero el último intento de feature ha fallado.")
            return

        min_sec = buffer.get("min_seconds")
        need_sec = buffer.get("needed_seconds")

        if not bool(status.get("window_ready", False)):
            st.info("Llenando ventana de análisis...")
            if min_sec is not None and need_sec:
                try:
                    ratio = max(0.0, min(1.0, float(min_sec) / float(need_sec)))
                    st.progress(ratio)
                    st.caption(f"Ventana disponible: {float(min_sec):.2f}s / {float(need_sec):.2f}s")
                except Exception:
                    st.progress(55)
            else:
                st.progress(55)
            return

        if not last_good:
            st.info("Ventana lista. Esperando primer feature válido...")
            st.progress(85)
            return

        st.success("Sistema listo.")
        st.progress(100)


# -----------------------------------------------------------------------------
# ECharts de bandas
# -----------------------------------------------------------------------------
def _build_bands_only_echart_options(last_good: dict) -> dict:
    rel_bp = _band_rel_dict(last_good)
    abs_bp = _band_abs_dict(last_good)
    dom_band, _ = _dominant_band(last_good)

    order = ["delta", "theta", "alpha", "beta", "gamma"]
    categories = []
    series_data = []

    for band in order:
        rel_value = rel_bp.get(band)
        abs_value = abs_bp.get(band)

        try:
            rel_value_float = float(rel_value)
        except Exception:
            rel_value_float = 0.0

        rel_value_float = max(0.0, min(1.0, rel_value_float))
        label = band.capitalize()
        categories.append(label)

        color = "#f59e0b" if band == dom_band else "#38bdf8"

        series_data.append(
            {
                "value": round(rel_value_float, 3),
                "rel_str": _fmt(rel_value, nd=3),
                "abs_str": _fmt_sci(abs_value),
                "itemStyle": {"color": color},
            }
        )

    return {
        "animation": True,
        "animationDuration": 80,
        "animationDurationUpdate": 80,
        "animationEasing": "linear",
        "animationEasingUpdate": "linear",
        "grid": {
            "left": 70,
            "right": 90,
            "top": 15,
            "bottom": 20,
            "containLabel": False,
        },
        "xAxis": {
            "type": "value",
            "min": 0.0,
            "max": 1.0,
            "splitNumber": 5,
            "axisLine": {"show": False},
            "axisTick": {"show": False},
            "splitLine": {"show": True, "lineStyle": {"color": "rgba(255,255,255,0.08)"}},
            "axisLabel": {"fontSize": 11},
        },
        "yAxis": {
            "type": "category",
            "inverse": True,
            "data": categories,
            "axisTick": {"show": False},
            "axisLine": {"show": False},
            "axisLabel": {"fontSize": 12, "fontWeight": 600},
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": JsCode(
                """
                function(params) {
                    const p = params[0];
                    return (
                        p.axisValue + "<br/>" +
                        "Relativa: " + p.data.rel_str + "<br/>" +
                        "Absoluta: " + p.data.abs_str
                    );
                }
                """
            ) if JsCode else None,
        },
        "series": [
            {
                "type": "bar",
                "data": series_data,
                "barWidth": 18,
                "showBackground": True,
                "backgroundStyle": {"color": "rgba(180, 180, 180, 0.10)"},
                "label": {
                    "show": True,
                    "position": "right",
                    "distance": 12,
                    "fontSize": 11,
                    "lineHeight": 16,
                    "formatter": JsCode(
                        """
                        function(params) {
                            return params.data.rel_str + "\\n" + params.data.abs_str;
                        }
                        """
                    ) if JsCode else None,
                },
                "itemStyle": {"borderRadius": [0, 6, 6, 0]},
            }
        ],
    }


# -----------------------------------------------------------------------------
# Render bloques principales
# -----------------------------------------------------------------------------
def _render_live_features_table(st, snapshot: dict):
    status = snapshot.get("status", {}) or {}
    last_good = ((snapshot.get("features", {}) or {}).get("last_good", {}) or {})
    dom_band, dom_value = _dominant_band(last_good)

    rows = [
        {"Feature": "RMS", "Valor": _fmt(last_good.get("rms"), nd=6)},
        {"Feature": "Frecuencia pico global", "Valor": _fmt_hz(last_good.get("peak_freq"))},
        {"Feature": "Pico delta", "Valor": _fmt_hz(last_good.get("peak_delta"))},
        {"Feature": "Pico theta", "Valor": _fmt_hz(last_good.get("peak_theta"))},
        {"Feature": "Pico alpha", "Valor": _fmt_hz(last_good.get("peak_alpha"))},
        {"Feature": "Pico beta", "Valor": _fmt_hz(last_good.get("peak_beta"))},
        {"Feature": "Pico gamma", "Valor": _fmt_hz(last_good.get("peak_gamma"))},
        {"Feature": "Banda dominante", "Valor": str(dom_band).capitalize()},
        {"Feature": "Peso dominante", "Valor": _fmt(dom_value, nd=3)},
        {"Feature": "Último intento", "Valor": status.get("last_feature_status", "n/a")},
        {"Feature": "Tiempo intento", "Valor": _fmt_us(status.get("last_feature_dt_us"))},
    ]

    st.table(rows)


def _render_live_bands_block(st, snapshot: dict, snapshot_source: str):
    status = snapshot.get("status", {}) or {}
    last_good = ((snapshot.get("features", {}) or {}).get("last_good", {}) or {})
    good_seq = int(status.get("last_good_feature_seq", 0) or 0)

    if snapshot_source == "cached":
        st.warning("Mostrando último snapshot válido en caché visual.")
    else:
        pub_age = _published_snapshot_age_s(snapshot)
        if pub_age is not None:
            st.caption(f"Snapshot live · edad publicación {_fmt(pub_age, nd=2)} s")

    if not last_good:
        st.info("Sin feature válido para mostrar todavía.")
        return

    if not ECHARTS_AVAILABLE:
        rel_bp = _band_rel_dict(last_good)
        abs_bp = _band_abs_dict(last_good)
        dom_band, _ = _dominant_band(last_good)
        order = ["delta", "theta", "alpha", "beta", "gamma"]

        for band in order:
            c1, c2, c3 = st.columns([1.2, 4.8, 1.6])
            with c1:
                st.markdown(f"**{band.capitalize()}{' ★' if band == dom_band else ''}**")
            with c2:
                try:
                    v = max(0.0, min(1.0, float(rel_bp.get(band))))
                except Exception:
                    v = 0.0
                st.progress(v)
            with c3:
                st.markdown(f"**{_fmt(rel_bp.get(band), nd=3)}**")
                st.caption(_fmt_sci(abs_bp.get(band)))
        return

    if good_seq != st.session_state.ui_last_rendered_good_seq or st.session_state.ui_last_echart_options is None:
        st.session_state.ui_last_echart_options = _build_bands_only_echart_options(last_good)
        st.session_state.ui_last_rendered_good_seq = good_seq

    st_echarts(
        options=st.session_state.ui_last_echart_options,
        height="300px",
        width="100%",
        theme="streamlit",
        renderer="canvas",
        key="bands_live_echart",
    )


def _render_static_config_panel(st, snapshot: dict):
    config = snapshot.get("config", {}) or {}

    with st.expander("Configuración", expanded=False):
        c1, c2 = st.columns(2)
        c1.metric("Frecuencia de muestreo", f"{config.get('fs_hz', 'n/a')} Hz")
        c2.metric("Canales", config.get("num_ch", "n/a"))

        c3, c4 = st.columns(2)
        c3.metric("Ventana análisis", f"{config.get('feature_window_sec', 'n/a')} s")
        c4.metric("Hop actualización", f"{config.get('feature_hop_samples', 'n/a')} muestras")

        c5, c6 = st.columns(2)
        c5.metric("Snapshot live", f"{config.get('snapshot_publish_period_sec', 'n/a')} s")
        c6.metric("Bench period", f"{config.get('bench_period_sec', 'n/a')} s")

        c7, c8 = st.columns(2)
        c7.metric("Método espectral", config.get("psd_method", "n/a"))
        try:
            ch_label = f"CH{int(config.get('channel_idx', 0)) + 1}"
        except Exception:
            ch_label = "n/a"
        c8.metric("Canal analizado", ch_label)


def _render_diagnostics_panel(st, snapshot: dict):
    status = snapshot.get("status", {}) or {}
    runtime = snapshot.get("runtime", {}) or {}
    rx = snapshot.get("rx", {}) or {}
    feat_perf = snapshot.get("feature_perf", {}) or {}
    buffer = snapshot.get("buffer", {}) or {}
    config = snapshot.get("config", {}) or {}

    snapshot_publish_age = _published_snapshot_age_s(snapshot)
    data_age = _estimated_event_age_s(snapshot, runtime.get("last_ingest_update_monotonic"))
    good_feature_age = _estimated_event_age_s(snapshot, status.get("last_good_feature_update_monotonic"))

    with st.expander("Diagnóstico avanzado", expanded=True):
        c1, c2 = st.columns(2)
        c1.metric("Estado", status.get("state_text", "n/a"))
        c2.metric("Ready", int(bool(status.get("window_ready", False))))

        c3, c4 = st.columns(2)
        c3.metric("Edad publicación", f"{snapshot_publish_age:.2f}s" if snapshot_publish_age is not None else "n/a")
        c4.metric("Edad datos", f"{data_age:.2f}s" if data_age is not None else "n/a")

        c5, c6 = st.columns(2)
        c5.metric("Edad feature bueno", f"{good_feature_age:.2f}s" if good_feature_age is not None else "n/a")
        c6.metric(
            "Ventana buffer",
            f"{_fmt(buffer.get('min_seconds'), nd=2)} / {_fmt(buffer.get('needed_seconds'), nd=2)} s",
        )

        c7, c8 = st.columns(2)
        c7.metric("Frame rate", _fmt_hz(rx.get("rx_frame_rate_hz")))
        c8.metric("Block rate", _fmt_hz(rx.get("rx_block_rate_hz")))

        c9, c10 = st.columns(2)
        c9.metric("Último intento", _fmt_us(status.get("last_feature_dt_us")))
        c10.metric("Estado intento", status.get("last_feature_status", "n/a"))

        st.json(
            {
                "config": config,
                "status": status,
                "runtime": runtime,
                "rx": rx,
                "feature_perf": feat_perf,
                "buffer": buffer,
            }
        )


# -----------------------------------------------------------------------------
# Render principal
# -----------------------------------------------------------------------------
def render_dashboard(st):
    st.set_page_config(page_title="EEG Spectral Dashboard", layout="wide")
    _init_ui_state(st)

    st.title("EEG Spectral Dashboard")
    st.caption("Visualización local de métricas espectrales EEG en Arduino UNO Q")

    top_left, top_right = st.columns([3.4, 1.3])

    with top_left:
        st.subheader("Panel principal · Features live")

    with top_right:
        c1, c2 = st.columns(2)

        with c1:
            if st.button("Start backend", width="stretch"):
                ok, msg = _start_backend_if_needed()
                if ok:
                    st.session_state.ui_booting = True
                    st.session_state.ui_boot_started_at = time.monotonic()
                    _clear_ui_snapshot_cache(st)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()

        with c2:
            if st.button("Stop backend", width="stretch"):
                ok, msg = _stop_backend()
                st.session_state.ui_booting = False
                st.session_state.ui_boot_started_at = 0.0
                _clear_ui_snapshot_cache(st)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()

    @st.fragment(run_every=STATUS_PERIOD_SEC)
    def startup_status_fragment():
        backend_alive, snapshot, _ = _load_snapshot_for_render(st)

        if st.session_state.ui_booting:
            _render_boot_screen(st, snapshot if snapshot else None, backend_alive)
            if _snapshot_is_ready(snapshot):
                st.session_state.ui_booting = False
            return

        _render_startup_status(st, snapshot if snapshot else None, backend_alive)

    startup_status_fragment()

    backend_alive_static, static_snapshot, _ = _load_snapshot_for_render(st)

    if static_snapshot:
        _render_static_config_panel(st, static_snapshot)
    elif backend_alive_static:
        with st.expander("Configuración", expanded=False):
            st.info("Configuración pendiente de snapshot.")
    else:
        with st.expander("Configuración", expanded=False):
            st.info("Backend no activo.")

    if st.session_state.ui_booting:
        return

    @st.fragment(run_every=FAST_FEATURES_PERIOD_SEC)
    def live_panel():
        backend_alive, snapshot, snapshot_source = _load_snapshot_for_render(st)

        if not snapshot:
            if backend_alive:
                st.info("Esperando datos EEG...")
            else:
                st.info("Pulsa Start backend para iniciar adquisición y procesamiento EEG.")
            return

        status = snapshot.get("status", {}) or {}
        last_good = ((snapshot.get("features", {}) or {}).get("last_good", {}) or {})

        if not last_good:
            state_text = status.get("state_text", "n/a")
            if state_text == "filling_window":
                st.info("Filling window… esperando al primer feature bueno.")
            else:
                st.info("Esperando primer snapshot útil de features.")
            return

        st.markdown("### Features live")
        a, b = st.columns([1.15, 1.85])

        with a:
            _render_live_features_table(st, snapshot)

        with b:
            _render_live_bands_block(st, snapshot, snapshot_source)

    live_panel()

    @st.fragment(run_every=DIAG_PERIOD_SEC)
    def diagnostics_panel():
        backend_alive, snapshot, _ = _load_snapshot_for_render(st)

        st.markdown("### Diagnóstico")
        if not snapshot:
            if backend_alive:
                st.info("Diagnóstico pendiente de datos.")
            else:
                st.info("Backend no activo.")
            return

        _render_diagnostics_panel(st, snapshot)

    diagnostics_panel()