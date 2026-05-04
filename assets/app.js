const bands = ["delta", "theta", "alpha", "beta", "gamma"];

function fmt(v, n = 3) {
  const x = Number(v);
  return Number.isFinite(x) ? x.toFixed(n) : "n/a";
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setStateChip(state) {
  const el = document.getElementById("state");
  if (!el) return;
  el.textContent = state;
  el.style.borderColor = "rgba(87, 184, 255, 0.35)";
  el.style.background = "rgba(87, 184, 255, 0.18)";
  if (state === "waiting_for_data") {
    el.style.borderColor = "rgba(255, 195, 87, 0.45)";
    el.style.background = "rgba(255, 195, 87, 0.16)";
  } else if (state === "features_ready") {
    el.style.borderColor = "rgba(89, 255, 212, 0.45)";
    el.style.background = "rgba(89, 255, 212, 0.14)";
  }
}

function renderBands(bp = {}) {
  const root = document.getElementById("bands");
  root.innerHTML = "";
  bands.forEach((b) => {
    const v = Math.max(0, Math.min(1, Number(bp[b] ?? 0)));
    const row = document.createElement("div");
    row.className = "band-row";
    row.innerHTML = `<div>${b}</div><div class="bar"><div class="fill" style="width:${(v * 100).toFixed(1)}%"></div></div><div class="mono">${fmt(v, 3)}</div>`;
    root.appendChild(row);
  });
}

function renderSnapshot(s) {
  const rx = s.rx || {};
  const status = s.status || {};
  const f = s.features || {};
  const state = status.state ?? "waiting_for_data";
  const waiting = state === "waiting_for_data";
  setStateChip(state);
  setText("sample-rate", waiting ? "waiting for data" : `${fmt(rx.rx_frame_rate_hz, 2)} Hz`);
  setText("block-rate", waiting ? "waiting for data" : `${fmt(rx.rx_block_rate_hz, 2)} Hz`);
  setText("last-idx", String(status.last_sample_idx ?? "n/a"));
  setText("malformed", String(rx.malformed_blocks_total ?? 0));
  setText("lost-frames", String(rx.lost_frames_total ?? 0));
  setText("lost-blocks", String(rx.lost_blocks_total ?? 0));
  setText("rms", fmt(f.rms, 6));
  setText("peak-freq", `${fmt(f.peak_freq, 2)} Hz`);
  setText("dominant-band", f.dominant_band ?? "n/a");
  setText("alpha-beta", fmt(f.alpha_beta_ratio, 3));
  renderBands(f.bandpower_rel || {});
}

async function loadInitial() {
  try {
    const res = await fetch('./latest');
    if (res.ok) renderSnapshot(await res.json());
    else console.warn('[WEBUI] /latest returned', res.status);
  } catch (e) {
    console.warn('[WEBUI] polling error', e);
  }
}

function startSocket() {
  if (typeof io !== 'function') return;
  const socket = io();
  socket.on('eeg_snapshot', renderSnapshot);
}

function startPollingFallback() {
  setInterval(loadInitial, 400);
}

loadInitial();
startSocket();
startPollingFallback();
