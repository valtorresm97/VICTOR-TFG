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

function renderAbsBands(bp = {}) {
  const root = document.getElementById("bands-abs");
  if (!root) return;
  root.innerHTML = "";
  bands.forEach((b) => {
    const val = Number(bp[b] ?? 0);
    const row = document.createElement("div");
    row.className = "abs-row";
    row.innerHTML = `<div>${b}</div><div class="mono">${fmt(val, 8)}</div>`;
    root.appendChild(row);
  });
}

function renderWarnings(s) {
  const root = document.getElementById("warnings");
  if (!root) return;
  const sonif = s.sonification || {};
  const midi = s.midi || {};
  const transport = midi.transport || {};
  const ledMatrix = s.led_matrix || {};
  const ledTransport = ledMatrix.transport || {};
  const warnings = [];

  if (!sonif.valid) warnings.push("No hay features de sonificación válidas.");
  if (!midi.live_enabled) warnings.push("MIDI físico desactivado por seguridad.");
  if (transport.enabled === false) warnings.push(`Handler MCU esperado: ${midi.mcu_handler || "midi_bytes"}.`);
  if (Number(transport.failed_events_total || 0) > 0) warnings.push("Bridge/MIDI reporta eventos fallidos.");
  if (Number(transport.dropped_events_total || 0) > 256) warnings.push("Hay muchos eventos MIDI descartados.");
  if (ledTransport.enabled === false) warnings.push("LED matrix desactivada.");
  if (Number(ledTransport.failed_events_total || 0) > 0) warnings.push("Bridge/LED matrix reporta eventos fallidos.");

  root.innerHTML = warnings.map((w) => `<div class="warning">${w}</div>`).join("");
}

function renderDiagnostics(s) {
  const d = s.diagnostics || {};
  setText("diag-rms", `${fmt(d.rms_uv, 2)} uV`);
  setText("diag-ptp", `${fmt(d.ptp_uv, 2)} uV`);
  setText("diag-offset", `${fmt(d.mean_uv, 2)} uV`);
  const ratio = Number(d.line_50_ratio);
  setText("diag-50hz", Number.isFinite(ratio) ? `${fmt(100 * ratio, 1)} %` : "n/a");
  setText("diag-saturation", `${fmt(100 * (d.saturation_fraction || 0), 3)} %`);
  setText("diag-jumps", String(d.abrupt_jumps ?? 0));

  const warnRoot = document.getElementById("diag-warnings");
  if (warnRoot) {
    const warnings = d.warnings || [];
    warnRoot.innerHTML = warnings.map((w) => `<div class="warning">${w}</div>`).join("");
  }

  const canvas = document.getElementById("diag-waveform");
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext("2d");
  const values = (d.waveform_uV || []).map(Number).filter(Number.isFinite);
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "rgba(8, 0, 18, 0.45)";
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = "rgba(255,255,255,0.14)";
  ctx.beginPath();
  ctx.moveTo(0, h / 2);
  ctx.lineTo(w, h / 2);
  ctx.stroke();

  if (values.length < 2) return;
  const maxAbs = Math.max(1, ...values.map((v) => Math.abs(v)));
  ctx.strokeStyle = "#59ffd4";
  ctx.lineWidth = 2;
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h / 2 - (v / maxAbs) * (h * 0.42);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function renderSonification(s) {
  const sonif = s.sonification || {};
  const music = s.music || {};
  const midi = s.midi || {};
  const scheduler = midi.scheduler || {};
  const transport = midi.transport || {};
  const ledMatrix = s.led_matrix || {};
  const ledTransport = ledMatrix.transport || {};

  setText("sonif-activity", fmt(sonif.activity, 3));
  setText("sonif-calmness", fmt(sonif.calmness, 3));
  setText("sonif-tension", fmt(sonif.tension, 3));
  setText("sonif-rhythmic-density", fmt(sonif.rhythmic_density, 3));
  setText("sonif-register", fmt(sonif.register, 3));
  setText("sonif-harmonic-stability", fmt(sonif.harmonic_stability, 3));
  setText("sonif-velocity-factor", fmt(sonif.velocity_factor, 3));
  setText("sonif-note-probability", fmt(sonif.note_probability, 3));

  setText("music-rhythm-cadence", music.rhythm_cadence || "n/a");
  setText("music-current-chord", (music.current_chord_notes || []).join(" · ") || "n/a");
  setText("music-scale", `${music.root_note || "n/a"} ${music.scale_name || ""}`.trim());
  setText("music-main-note", music.main_note || "n/a");

  setText("midi-live-enabled", midi.live_enabled ? "enabled" : "disabled");
  setText("midi-queued-events", String(scheduler.queued_events ?? 0));
  setText("midi-active-notes", String(scheduler.active_notes ?? 0));
  setText("midi-sent-events", String(transport.sent_events_total ?? 0));
  setText("midi-dropped-events", String(transport.dropped_events_total ?? 0));
  setText("midi-failed-events", String(transport.failed_events_total ?? 0));

  setText("led-matrix-enabled", ledMatrix.enabled ? "enabled" : "disabled");
  setText("led-matrix-sent-events", String(ledTransport.sent_events_total ?? 0));
  setText("led-matrix-dropped-events", String(ledTransport.dropped_events_total ?? 0));
  setText("led-matrix-failed-events", String(ledTransport.failed_events_total ?? 0));
}

function renderPianoRoll(s) {
  const root = document.getElementById("piano-roll");
  const empty = document.getElementById("piano-roll-empty");
  if (!root || !empty) return;

  const notes = ((s.music || {}).recent_notes || []).filter((n) => Number.isFinite(Number(n.abs_start)));
  if (!notes.length) {
    root.innerHTML = "";
    empty.style.display = "block";
    return;
  }

  empty.style.display = "none";
  const now = Number(s.ts_monotonic || notes[notes.length - 1].abs_end || notes[notes.length - 1].abs_start);
  const windowSec = Math.max(4, Number((s.performance || {}).recent_notes_window_sec || 20));
  const startWindow = now - windowSec;
  const pitches = notes.map((n) => Number(n.pitch_midi)).filter(Number.isFinite);
  const minPitch = Math.min(...pitches, 48);
  const maxPitch = Math.max(...pitches, 84);
  const pitchSpan = Math.max(1, maxPitch - minPitch + 1);

  const rows = [];
  for (let p = maxPitch; p >= minPitch; p -= 1) {
    const y = ((maxPitch - p) / pitchSpan) * 100;
    rows.push(`<div class="piano-row" style="top:${y.toFixed(2)}%"></div>`);
  }

  const bars = notes.map((n) => {
    const absStart = Number(n.abs_start);
    const absEnd = Math.max(absStart + 0.04, Number(n.abs_end || absStart + 0.2));
    const left = Math.max(0, Math.min(100, ((absStart - startWindow) / windowSec) * 100));
    const right = Math.max(left + 0.8, Math.min(100, ((absEnd - startWindow) / windowSec) * 100));
    const pitch = Number(n.pitch_midi);
    const y = ((maxPitch - pitch) / pitchSpan) * 100;
    const vel = Math.max(0, Math.min(127, Number(n.velocity || 0)));
    const alpha = 0.35 + 0.65 * (vel / 127);
    const label = `${n.note_name || pitch} · v${vel} · ch${n.channel ?? 0}`;
    return `<div class="note-bar" title="${label}" style="left:${left.toFixed(2)}%;width:${(right - left).toFixed(2)}%;top:${y.toFixed(2)}%;opacity:${alpha.toFixed(2)}">${n.note_name || pitch}</div>`;
  });

  root.innerHTML = rows.join("") + bars.join("");
}

function renderSnapshot(s) {
  const rx = s.rx || {};
  const status = s.status || {};
  const f = s.features || {};
  const state = status.state ?? "waiting_for_data";
  const waiting = state === "waiting_for_data";
  const rxFrameRate = rx.rx_frame_rate_hz ?? rx.rxFrameRateHz ?? 0;
  const rxBlockRate = rx.rx_block_rate_hz ?? rx.rxBlockRateHz ?? 0;
  setStateChip(state);
  setText("state", state);
  setText("sample-rate", waiting ? "waiting for data" : `${fmt(rxFrameRate, 2)} Hz`);
  setText("block-rate", waiting ? "waiting for data" : `${fmt(rxBlockRate, 2)} Hz`);
  setText("last-idx", String(status.last_sample_idx ?? "n/a"));
  setText("malformed", String(rx.malformed_blocks_total ?? 0));
  setText("lost-frames", String(rx.lost_frames_total ?? 0));
  setText("lost-blocks", String(rx.lost_blocks_total ?? 0));
  setText("rms", fmt(f.rms, 6));
  setText("peak-freq", `${fmt(f.peak_freq, 2)} Hz`);
  setText("peak-delta", `${fmt(f.peak_delta, 2)} Hz`);
  setText("peak-theta", `${fmt(f.peak_theta, 2)} Hz`);
  setText("peak-alpha", `${fmt(f.peak_alpha, 2)} Hz`);
  setText("peak-beta", `${fmt(f.peak_beta, 2)} Hz`);
  setText("peak-gamma", `${fmt(f.peak_gamma, 2)} Hz`);
  setText("dominant-band", f.dominant_band ?? "n/a");
  setText("alpha-beta", fmt(f.alpha_beta_ratio, 3));
  renderBands(f.bandpower_rel || {});
  renderAbsBands(f.bandpower_abs || {});
  renderDiagnostics(s);
  renderWarnings(s);
  renderSonification(s);
  renderPianoRoll(s);
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
