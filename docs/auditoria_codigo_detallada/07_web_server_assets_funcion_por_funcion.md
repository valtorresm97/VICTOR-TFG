# 07. Web server y assets funcion por funcion

## Estado actual

La Web UI muestra adquisicion, DSP, calidad, sonificacion, MIDI status, panic, piano roll y estado LED. Los controles musicales WebUI fueron retirados por estabilidad y no deben reintroducirse en esta fase.

## Endpoints y funciones

| Archivo | Funcion/Endpoint/Elemento | Entrada | Salida | Snapshot keys usadas | Estado UI | Riesgo |
| --- | --- | --- | --- | --- | --- | --- |
| `web_server.py` | `EEGWebServer.__init__` | backend, port | servidor | N/A | Inicializa WebUI | Si assets path cambia, UI no carga. |
| `web_server.py` | `_setup_routes` | Ninguna | rutas | N/A | Registra `/status`, `/latest`, `/midi/panic`, socket | Cambiar rutas rompe `app.js`. |
| `web_server.py` | `GET /status` (`get_status`) | HTTP | `{ok,state,window_ready}` | `status.state`, `status.window_ready` | Estado compacto | Bajo. |
| `web_server.py` | `GET /latest` (`get_latest`) | HTTP | snapshot | Todo snapshot | Carga inicial/polling | Cambiar contrato rompe UI. |
| `web_server.py` | `POST /midi/panic` | HTTP | `{ok,sent_events}` | N/A | Boton Panic | Si transporte disabled, sent=0 esperado. |
| `web_server.py` | `on_connect` | sid | Socket emit opcional | snapshot actual | Primer snapshot al cliente | Bajo. |
| `web_server.py` | `on_disconnect` | sid | log | N/A | Ninguno | Bajo. |
| `web_server.py` | `publish_snapshot` | snapshot | socket `eeg_snapshot` | snapshot completo | Update live | Frecuencia excesiva afecta UI. |
| `web_server.py` | `start` | Ninguna | servidor activo | N/A | Arranque WebUI | App Lab dependency. |
| `assets/index.html` | Topbar | DOM | Visual | `status.state` | Estado general | IDs deben coincidir con JS. |
| `assets/index.html` | Adquisicion | DOM | Visual | `rx`, `status`, `config.channels` | Rates, indices, perdidas | Cambiar IDs rompe render. |
| `assets/index.html` | Features EEG | DOM | Visual | `features` | RMS, peaks, bands | Unidades deben ser claras. |
| `assets/index.html` | Diagnostico | DOM/canvas | Visual | `diagnostics` | Waveform, 50Hz, warnings | Canvas depende de waveform_uV. |
| `assets/index.html` | Sonificacion | DOM | Visual | `sonification`, `music` | Controles musicales derivados | No hay controles editables. |
| `assets/index.html` | MIDI Live | DOM/button | Visual + POST panic | `midi` | Estado scheduler/transport | Panic debe conservarse. |
| `assets/index.html` | Piano roll | DOM | Visual | `music.recent_notes`, `performance.recent_notes_window_sec` | Scroll notas | Tiempos monotonic. |
| `assets/app.js` | `fmt` | value,n | string | N/A | Formato numerico | Bajo. |
| `assets/app.js` | `setText` | id,value | DOM update | N/A | Todos paneles | ID inexistente se ignora. |
| `assets/app.js` | `setStateChip` | state | DOM style | `status.state` | Chip estado | Solo contempla algunos estados. |
| `assets/app.js` | `renderBands` | `features.bandpower_rel` | DOM | `delta..gamma` | Barras relativas | Depende de lista `bands`. |
| `assets/app.js` | `renderAbsBands` | `features.bandpower_abs` | DOM | `delta..gamma` | Valores abs | Unidad V2 aprox. |
| `assets/app.js` | `renderWarnings` | snapshot | DOM | `sonification.valid`, `midi`, `config.channels` | Warnings | Puede alarmar por drops acumulados. |
| `assets/app.js` | `renderChannelStatus` | snapshot | DOM | `config.ads_diagnostic_mode`, `config.channels` | CH activo/apagado | Importante para modo 5. |
| `assets/app.js` | `renderDiagnostics` | snapshot | DOM/canvas | `diagnostics.*`, `waveform_uV` | Calidad CH1 | Canvas no hace downsample extra. |
| `assets/app.js` | `renderSonification` | snapshot | DOM | `sonification`, `music`, `midi.scheduler/transport` | Sonificacion/MIDI | Sin controles WebUI. |
| `assets/app.js` | `setPanicStatus` | text,error | DOM | N/A | Feedback panic | Bajo. |
| `assets/app.js` | `sendMidiPanic` | click | POST | `/midi/panic` | Panic | Ruta debe existir. |
| `assets/app.js` | `setupMidiPanicButton` | DOM | listener | N/A | Boton | Bajo. |
| `assets/app.js` | `renderPianoRoll` | snapshot | DOM | `music.recent_notes`, `ts_monotonic`, `performance` | Notas recientes | Depende de `abs_start/abs_end/pitch_midi`. |
| `assets/app.js` | `renderSnapshot` | snapshot | DOM | `rx`, `status`, `features`, `diagnostics`, `sonification`, `music`, `midi` | Render completo | Funcion mas sensible de UI. |
| `assets/app.js` | `loadInitial` | HTTP | render | `/latest` | Poll inicial/fallback | Bajo. |
| `assets/app.js` | `startSocket` | socket.io | listener | `eeg_snapshot` | Live update | Si `io` no existe cae a polling. |
| `assets/app.js` | `startPollingFallback` | timer | GET loop | `/latest` | Fallback cada 400 ms | Duplicado con socket; tolerable. |
| `assets/styles.css` | Selectores dashboard | CSS | Visual | IDs/classes HTML | Layout | No afecta datos. |

## Claves snapshot mas sensibles

- `status.state`, `status.window_ready`, `status.last_sample_idx`.
- `rx.rx_frame_rate_hz`, `rx.rx_block_rate_hz`, `rx.lost_*`, `rx.malformed_blocks_total`.
- `config.ads_diagnostic_mode`, `config.channels`.
- `features.rms`, `features.peak_*`, `features.bandpower_rel`, `features.bandpower_abs`.
- `diagnostics.rms_uv`, `ptp_uv`, `mean_uv`, `line_50_ratio`, `waveform_uV`.
- `sonification.activity/calmness/tension/...`.
- `music.recent_notes`, `current_chord_notes`, `scale_name`, `main_note`.
- `midi.scheduler`, `midi.transport`, `midi.live_enabled`.
- `led_matrix.config`, `led_matrix.transport`.

## Riesgos

- `assets/app.js` contiene mucho contrato de snapshot implicito. Antes de cambiar claves backend, crear prueba de schema.
- WebUI no debe alojar DSP ni adquisicion.
- La ruta de panic es la unica accion activa actual; controles musicales quedan fuera hasta rediseño MIDI/UI.
