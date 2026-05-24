# 07. Auditoria Web UI

## Estructura

La UI esta compuesta por:

- `python/web_server.py`: servidor WebUI brick.
- `assets/index.html`: estructura de paneles.
- `assets/app.js`: render de snapshots y polling/websocket.
- `assets/styles.css`: estilos.

No hay `dashboard.py` ni Streamlit en esta rama.

## Rutas y datos

| Ruta/evento | Origen | Uso |
| --- | --- | --- |
| `GET /status` | `web_server.py` | Estado minimo: `ok`, `state`, `window_ready`. |
| `GET /latest` | `web_server.py` | Snapshot completo backend o fallback disco. |
| `eeg_snapshot` | Websocket WebUI | Push de snapshot live. |
| Polling 400 ms | `assets/app.js` | Fallback si socket no esta disponible. |

## Paneles

| Panel UI | Datos usados | Clave snapshot | Archivo origen | Riesgo |
| --- | --- | --- | --- | --- |
| Estado | Estado pipeline | `status.state`, `status.window_ready` | `backend_service.py` | Cambio de nombres rompe chip. |
| Rendimiento adquisicion | Tasas, indice, malformed/lost | `rx.*`, `status.last_sample_idx` | `receiver.py` | UI no muestra todos los contadores RX. |
| Features EEG | RMS, peaks, dominant, alpha/beta | `features.*` | `eeg_signal_processor.py`, `dsp_core.py` | `rms` esta en V, diagnostico usa uV. |
| Bandpower relativo | Delta/theta/alpha/beta/gamma | `features.bandpower_rel` | `dsp_core.py` | Depende de nombres exactos de bandas. |
| Bandpower absoluto | Potencia por banda | `features.bandpower_abs` | `dsp_core.py` | Puede interpretarse como absoluto calibrado, pero es aproximado. |
| Calidad/diagnostico | RMS uV, ptp, 50 Hz, saturacion, jumps, waveform | `diagnostics.*` | `eeg_signal_processor.py` | No muestra `spectral_quality` explicitamente salvo warnings indirectos. |
| Sonificacion live | Controles musicales | `sonification.*` | `sonification_features.py` | Cambios de nombres rompen metric cards. |
| Musica | Cadencia, acorde, escala, main note | `music.*` | `backend_service.py` | No hay controles de usuario aun. |
| MIDI Live | enabled, scheduler, transport | `midi.*` | `midi_live.py`, `midi_byte_transport.py` | No hay boton panic. |
| Piano roll live | Notas recientes | `music.recent_notes`, `performance.recent_notes_window_sec` | `backend_service.py` | Solo intencion musical, no confirmacion MIDI fisico. |
| Warnings | Sonif/MIDI | `sonification.valid`, `midi.live_enabled`, `midi.transport.*` | `assets/app.js` | No incluye LED ni todos los errores RX. |

## Dependencias de snapshot

Claves especialmente fragiles:

- `rx.rx_frame_rate_hz`
- `rx.rx_block_rate_hz`
- `rx.malformed_blocks_total`
- `rx.lost_frames_total`
- `rx.lost_blocks_total`
- `features.bandpower_rel`
- `features.bandpower_abs`
- `diagnostics.waveform_uV`
- `sonification.activity`
- `music.recent_notes`
- `midi.transport.sent_events_total`

## Limitaciones UI

- No muestra panel LED matrix dedicado.
- No muestra `spectral_quality.score/state/gate_factor` en tarjetas propias.
- No expone controles para habilitar/deshabilitar MIDI/LED desde UI.
- No hay botones de capture start/stop; se usa CLI.
- No hay panic MIDI ni clear LED.
- No hay estado visible de BIAS/RLD/ADS mode actual.
