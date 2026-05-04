from __future__ import annotations

from app_state import read_snapshot


BANDS = ["delta", "theta", "alpha", "beta", "gamma"]


def _fmt(v, nd=3, default="n/a"):
    if v is None:
        return default
    try:
        return f"{float(v):.{nd}f}"
    except Exception:
        return default


def _fmt_hz(v):
    return f"{_fmt(v, nd=2)} Hz" if v is not None else "n/a"


def _render_rx_panel(st, snap: dict):
    status = snap.get("status", {}) or {}
    rx = snap.get("rx", {}) or {}

    st.subheader("Recepción")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estado", status.get("state", "n/a"))
    c2.metric("Sample rate", _fmt_hz(rx.get("rx_frame_rate_hz")))
    c3.metric("Block rate", _fmt_hz(rx.get("rx_block_rate_hz")))
    c4.metric("Última muestra idx", str(status.get("last_sample_idx", "n/a")))

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Lost frames", int(rx.get("lost_frames_total", 0)))
    d2.metric("Lost blocks", int(rx.get("lost_blocks_total", 0)))
    d3.metric("Malformed", int(rx.get("malformed_blocks_total", 0)))
    d4.metric("Invalid status", int(rx.get("invalid_status_total", 0)))


def _render_features_panel(st, snap: dict):
    feats = snap.get("features", {}) or {}
    bp_rel = feats.get("bandpower_rel", {}) or {}
    bp_abs = feats.get("bandpower_abs", {}) or {}

    st.subheader("Features espectrales")
    a, b, c, d = st.columns(4)
    a.metric("RMS", _fmt(feats.get("rms"), nd=6))
    b.metric("Peak freq", _fmt_hz(feats.get("peak_freq")))
    c.metric("Alpha rel", _fmt(feats.get("alpha_power_rel"), nd=3))
    d.metric("Beta rel", _fmt(feats.get("beta_power_rel"), nd=3))

    st.markdown("**Bandas EEG (potencia relativa)**")
    for band in BANDS:
        try:
            v = float(bp_rel.get(band, 0.0))
        except Exception:
            v = 0.0
        v = max(0.0, min(1.0, v))
        c1, c2, c3 = st.columns([1.2, 5.0, 1.6])
        c1.markdown(f"**{band.capitalize()}**")
        c2.progress(v)
        c3.caption(f"rel={_fmt(bp_rel.get(band), nd=3)} | abs={_fmt(bp_abs.get(band), nd=6)}")


def render_dashboard(st):
    st.set_page_config(page_title="EEG Spectral Dashboard", layout="wide")
    st.title("EEG Spectral Dashboard · Mínimo")

    @st.fragment(run_every=0.5)
    def live_view():
        snap = read_snapshot(default={})
        if not isinstance(snap, dict) or not snap:
            st.info("Esperando snapshots del backend...")
            return

        _render_rx_panel(st, snap)
        st.divider()
        _render_features_panel(st, snap)

    live_view()
