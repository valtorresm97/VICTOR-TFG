const BANDS = ["delta", "theta", "alpha", "beta", "gamma"];
const fmt = (v, n = 2) => Number.isFinite(Number(v)) ? Number(v).toFixed(n) : "n/a";

function renderBands(bands){
  return BANDS.map((b)=>{
    const v = Math.max(0, Math.min(1, Number((bands||{})[b] ?? 0)));
    return `<div class="band-row"><span>${b}</span><div class="bar"><div class="fill" style="width:${(v*100).toFixed(1)}%"></div></div><span>${fmt(v,3)}</span></div>`;
  }).join("");
}

function renderSnapshot(s){
  document.getElementById("state").textContent = s.status || "unknown";
  const g = s.global || {};
  document.getElementById("global").innerHTML = `
    <p>Canales válidos: <b>${g.valid_channels ?? 0}</b></p>
    <p>RMS global: <b>${fmt(g.rms_uV,2)} uV</b> · Peak global: <b>${fmt(g.peak_freq_hz,2)} Hz</b> · Banda dominante: <b>${g.dominant_band || "n/a"}</b></p>
    ${renderBands(g.bands || {})}
  `;
  document.getElementById("rx").innerHTML = `
    <p>Sample rate: <b>${fmt(s.rx_sample_rate_hz,2)} Hz</b> · Block rate: <b>${fmt(s.rx_block_rate_hz,2)} Hz</b> · last_sample_idx: <b>${s.last_sample_idx ?? "n/a"}</b></p>
  `;

  const chRoot = document.getElementById("channels");
  const channels = Array.isArray(s.channels) ? s.channels : [];
  chRoot.innerHTML = channels.map((ch)=>`
    <article class="card channel ${ch.connected ? "ok" : "off"}">
      <h3>${ch.label}</h3>
      <p>Estado: <b>${ch.quality || (ch.connected ? "connected" : "disconnected")}</b></p>
      <p>RMS: <b>${fmt(ch.rms_uV,2)} uV</b></p>
      <p>Peak: <b>${fmt(ch.peak_freq_hz,2)} Hz</b></p>
      <p>Banda dominante: <b>${ch.dominant_band || "n/a"}</b></p>
      <p>Alpha/Beta: <b>${fmt(ch.alpha_beta_ratio,3)}</b></p>
      ${renderBands(ch.bands || {})}
    </article>
  `).join("");
}

async function poll(){
  try { const r = await fetch('./latest'); if(r.ok) renderSnapshot(await r.json()); } catch (_) {}
}
setInterval(poll, 400); poll();
