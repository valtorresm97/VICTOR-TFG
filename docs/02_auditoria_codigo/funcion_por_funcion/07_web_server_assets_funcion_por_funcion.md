# 07. Web server y assets funcion por funcion - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Re-auditoria final-v4: revisada contra codigo real en `firmware-final-v4` desde la rama documental `refactor/essential-eeg-midi-plan`.

Objetivo de esta re-auditoria: documentar la WebUI real final-v4, sus endpoints, contratos de snapshot, controles musicales, panic MIDI, piano roll y riesgos para futura simplificacion UML.

## 1. Estado final-v4

La UI real no es Streamlit. El servidor usa:

```text
python/web_server.py
arduino.app_bricks.web_ui.WebUI
assets/index.html
assets/app.js
assets/styles.css
```

La WebUI muestra:

- rendimiento de adquisicion;
- estado de canales y `ADS_DIAGNOSTIC_MODE`;
- features EEG CH1;
- bandpower relativo y absoluto;
- diagnostico/calidad de senal;
- controles reportables de sonificacion final-v4;
- controles musicales `root`, `main` y `scale`;
- estado MIDI live;
- boton panic;
- piano roll live desde `music.recent_notes`.

Acciones activas actuales:

```text
POST /midi/panic
POST /midi/test-*
POST /midi/test-loop/*
POST /music/config
POST /music/scale/{key}
POST /music/root/{note}
POST /music/main/{note}
```

No expone controles para:

- cambiar firmware;
- cambiar modo ADS runtime;
- habilitar/deshabilitar MIDI fisico;
- habilitar/deshabilitar LED matrix;
- cambiar filtros MCU;
- iniciar/parar capturas.

## 2. Arquitectura WebUI

```text
BackendService
  -> get_latest_snapshot()
  -> EEGWebServer.get_latest()
  -> GET /latest
  -> assets/app.js renderSnapshot()
```

Y en live:

```text
BackendService
  -> main.loop()
  -> web.publish_snapshot(snapshot)
  -> socket eeg_snapshot
  -> assets/app.js renderSnapshot()
```

Fallback:

```text
assets/app.js
  -> startPollingFallback()
  -> GET ./latest cada 400 ms
```

La UI es observadora/control ligero. No calcula DSP, no accede a ADS1299, no genera MIDI por si misma y no modifica el loop de adquisicion.

## 3. Criterio especial para simplificacion futura de WebUI

Esta parte del proyecto debe tratarse con especial cuidado porque concentra mucho contrato implicito entre backend, snapshot, HTML y JavaScript. Ademas, la WebUI fue construida mayoritariamente por Codex, por lo que debe simplificarse de forma que sea comprensible para el autor del TFG sin perder funcionamiento.

Objetivo de simplificacion WebUI:

```text
conservar funcionamiento
conservar resolucion temporal percibida
conservar panic MIDI
conservar controles root/main/scale
conservar piano roll
hacer el codigo y los diagramas comprensibles
facilitar explicacion en la memoria TFG
reducir diagnosticos secundarios sin romper el sistema
```

Reglas de simplificacion WebUI:

1. No tocar la adquisicion, el DSP ni la sonificacion desde WebUI.
2. No exponer controles de ADS1299, filtros MCU, firmware, MIDI enable ni LED enable.
3. Mantener la WebUI como observador y control musical ligero.
4. Mantener `POST /midi/panic` como accion esencial.
5. Mantener una forma clara de cambiar `root_note`, `main_note` y `scale_key`.
6. Mantener `music.recent_notes` y el piano roll como evidencia visual de que la sonificacion genera notas.
7. Antes de quitar compatibilidad legacy, confirmar que el snapshot final-v4 ya no la necesita.
8. Antes de reducir socket/polling, medir que la UI sigue actualizando de forma fluida.
9. Antes de cambiar rutas `/music/*`, probar los controles en navegador y en App Lab.
10. Antes de reordenar `assets/app.js`, crear una lista minima de claves snapshot usadas por la UI.

Criterio para redaccion del TFG:

```text
La WebUI debe describirse como una interfaz de monitorizacion y control musical.
No debe presentarse como parte del calculo DSP ni como parte del firmware.
Su funcion es mostrar el estado del sistema, la calidad de senal, los controles de sonificacion, el estado MIDI y el piano roll generado en tiempo real.
```

## 4. Endpoints y funciones re-auditadas

| Archivo | Funcion/Endpoint/Elemento | Entrada | Salida | Snapshot keys usadas | Estado UI | Riesgo |
| --- | --- | --- | --- | --- | --- | --- |
| `web_server.py` | `EEGWebServer.__init__` | backend, port | servidor | N/A | Inicializa `WebUI` con assets | Si `assets_dir` cambia, UI no carga. |
| `web_server.py` | `_setup_routes` | Ninguna | rutas | N/A | Registra `/status`, `/latest`, rutas MIDI, `/music/*`, socket | Cambiar rutas rompe `app.js`. |
| `web_server.py` | `GET /status` (`get_status`) | HTTP | `{ok,state,window_ready}` | `status.state`, `status.window_ready` | Estado compacto | Bajo. |
| `web_server.py` | `GET /latest` (`get_latest`) | HTTP | snapshot actual o disco | Todo snapshot | Carga inicial/polling | Cambiar contrato rompe UI. |
| `web_server.py` | `POST /midi/panic` | HTTP | `{ok,sent_events}` | N/A | Boton Panic | Esencial; debe conservarse en version UML. |
| `web_server.py` | `POST /midi/test-note*` | HTTP | payload diagnostico MIDI | N/A | Test nota MIDI sin EEG | Diagnostico; no flujo principal. |
| `web_server.py` | `POST /midi/test-sequence*` | HTTP | payload diagnostico MIDI | N/A | Test secuencia MIDI sin EEG | Puede bloquear por sleeps en backend. |
| `web_server.py` | `POST /midi/test-loop/start*` | HTTP | estado loop | N/A | Loop diagnostico MIDI | Puede enmascarar sonificacion EEG. |
| `web_server.py` | `POST /midi/test-loop/stop` | HTTP | estado loop | N/A | Detiene diagnostico MIDI | Diagnostico. |
| `web_server.py` | `POST /music/config` | JSON/kwargs | `{ok,music}` | N/A | Actualiza root/main/scale juntos | Debe validar escala y notas. |
| `web_server.py` | `POST /music/scale/{key}` | HTTP | `{ok,music}` | N/A | Cambia escala | Claves deben coincidir con WebUI/backend. |
| `web_server.py` | `POST /music/root/{note}` | HTTP | `{ok,music}` | N/A | Cambia root note C3..B5 | Mapeo URL usa `s` para sostenidos. |
| `web_server.py` | `POST /music/main/{note}` | HTTP | `{ok,music}` | N/A | Cambia main note C3..B5 | Mapeo URL usa `s` para sostenidos. |
| `web_server.py` | `on_connect` | sid | socket snapshot inicial | snapshot actual | Primer snapshot al cliente | Bajo. |
| `web_server.py` | `on_disconnect` | sid | log | N/A | Log desconexion | Bajo. |
| `web_server.py` | `publish_snapshot` | snapshot | socket `eeg_snapshot` | snapshot completo | Update live | Frecuencia excesiva afecta UI. |
| `web_server.py` | `start` | Ninguna | servidor activo | N/A | Arranque WebUI | Dependencia App Lab/WebUI. |
| `assets/index.html` | Topbar | DOM | Visual | `status.state` | Estado general | IDs deben coincidir con JS. |
| `assets/index.html` | Adquisicion | DOM | Visual | `rx`, `status`, `config.channels` | Rates, indices, perdidas | Cambiar IDs rompe render. |
| `assets/index.html` | Features EEG | DOM | Visual | `features` | RMS, peaks, bands | Unidades deben ser claras. |
| `assets/index.html` | Bandpowers | DOM | Visual | `features.bandpower_rel`, `features.bandpower_abs` | Bandas EEG | Depende de bandas delta..gamma. |
| `assets/index.html` | Diagnostico ADS/calidad | DOM/canvas | Visual | `diagnostics` | RMS/PTP/50Hz/waveform | Canvas depende de `waveform_uV`. |
| `assets/index.html` | Sonificacion Live | DOM | Visual | `sonification`, `music` | Nombres reportables final-v4 | IDs deben coincidir con `app.js`. |
| `assets/index.html` | Music controls | DOM/select/button | POST music | `music.root_note`, `main_note`, `scale_key` | Control usuario root/main/scale | No controla EEG directamente. |
| `assets/index.html` | MIDI Live | DOM/button | Visual + POST panic | `midi` | Scheduler/transport/panic | Panic debe conservarse. |
| `assets/index.html` | Piano roll | DOM | Visual | `music.recent_notes`, `performance.recent_notes_window_sec` | Scroll notas | Tiempos monotonic. |
| `assets/app.js` | `fmt` | value,n | string | N/A | Formato numerico | Bajo. |
| `assets/app.js` | `controlValue` | obj, primary, legacy | valor | `sonification` | Fallback nombres nuevos/legacy | Util para transicion; ocultar en UML. |
| `assets/app.js` | `setText` | id,value | DOM update | N/A | Todos paneles | ID inexistente se ignora. |
| `assets/app.js` | `setStateChip` | state | DOM style | `status.state` | Chip estado | Solo contempla algunos estados. |
| `assets/app.js` | `renderBands` | `features.bandpower_rel` | DOM | `delta..gamma` | Barras relativas | Depende de lista `bands`. |
| `assets/app.js` | `renderAbsBands` | `features.bandpower_abs` | DOM | `delta..gamma` | Valores abs | Unidad V2 aprox. |
| `assets/app.js` | `renderWarnings` | snapshot | DOM | `sonification.valid`, `midi`, `config.channels` | Warnings | Puede alarmar por drops acumulados. |
| `assets/app.js` | `renderChannelStatus` | snapshot | DOM | `config.ads_diagnostic_mode`, `config.channels` | CH activo/apagado | Importante para modo 5. |
| `assets/app.js` | `renderDiagnostics` | snapshot | DOM/canvas | `diagnostics.*`, `waveform_uV` | Calidad CH1 | Canvas no hace downsample extra. |
| `assets/app.js` | `renderSonification` | snapshot | DOM | `sonification`, `music`, `midi.scheduler/transport` | Sonificacion/MIDI | Usa nombres final-v4 con fallback legacy. |
| `assets/app.js` | `noteEndpointKey` | note | url key | N/A | C# -> cs | Bajo. |
| `assets/app.js` | `syncMusicControls` | music | DOM select state | `music.root_note`, `main_note`, `scale_key` | Sincroniza selects sin pisar foco | Bajo. |
| `assets/app.js` | `applyMusicConfig` | DOM click | POSTs | `/music/scale`, `/music/root`, `/music/main` | Aplica configuracion musical | Secuencia parcial puede aplicar escala/root antes de fallar en main. |
| `assets/app.js` | `setupMusicControls` | DOM | options/listener | N/A | Pobla root/main C3..B5 | Debe coincidir con rutas backend. |
| `assets/app.js` | `sendMidiPanic` | click | POST | `/midi/panic` | Panic MIDI | Esencial. |
| `assets/app.js` | `setupMidiPanicButton` | DOM | listener | N/A | Boton panic | Bajo. |
| `assets/app.js` | `renderPianoRoll` | snapshot | DOM | `music.recent_notes`, `ts_monotonic`, `performance` | Notas recientes | Depende de `abs_start/abs_end/pitch_midi`. |
| `assets/app.js` | `renderSnapshot` | snapshot | DOM | `rx`, `status`, `features`, `diagnostics`, `sonification`, `music`, `midi` | Render completo | Funcion mas sensible de UI. |
| `assets/app.js` | `loadInitial` | HTTP | render | `/latest` | Poll inicial/fallback | Bajo. |
| `assets/app.js` | `startSocket` | socket.io | listener | `eeg_snapshot` | Live update | Si `io` no existe cae a polling. |
| `assets/app.js` | `startPollingFallback` | timer | GET loop | `/latest` | Fallback cada 400 ms | Puede duplicar con socket; tolerable. |
| `assets/styles.css` | Selectores dashboard | CSS | Visual | IDs/classes HTML | Layout | No afecta datos. |

## 5. Claves snapshot mas sensibles

- `status.state`, `status.window_ready`, `status.last_sample_idx`.
- `rx.rx_frame_rate_hz`, `rx.rx_block_rate_hz`, `rx.lost_*`, `rx.malformed_blocks_total`, `rx.invalid_status_total`.
- `config.ads_diagnostic_mode`, `config.channels`.
- `features.rms`, `features.peak_*`, `features.bandpower_rel`, `features.bandpower_abs`, `features.alpha_beta_ratio`.
- `diagnostics.rms_uv`, `ptp_uv`, `mean_uv`, `line_50_ratio`, `waveform_uV`, `warnings`.
- `spectral_quality.score`, `state`, `gate_factor`, `valid_for_sonification`.
- `sonification.alpha_drive`, `beta_gamma_drive`, `rms_beta_activity`, `band_driven_density`, `spectral_register`, `alpha_stability`, `rms_band_velocity`, `band_note_probability`.
- `music.recent_notes`, `root_note`, `main_note`, `scale_key`, `scale_name`, `current_chord_notes`.
- `midi.live_enabled`, `midi.scheduler`, `midi.transport`, `midi.mcu_handler`.
- `led_matrix.config`, `led_matrix.transport`.

Nota: `assets/app.js::controlValue()` mantiene fallback a nombres legacy (`activity`, `calmness`, `tension`, etc.) para compatibilidad. En final-v4 la documentacion y el UML deben priorizar los nombres nuevos.

## 6. Acciones esenciales frente a diagnosticas

Para la version esencial/UML, conservar como esenciales:

```text
GET /status
GET /latest
socket eeg_snapshot
POST /midi/panic
POST /music/config o equivalentes root/main/scale
```

Marcar como diagnosticas/secundarias:

```text
POST /midi/test-note*
POST /midi/test-sequence*
POST /midi/test-loop/*
render de metricas LED
fallback legacy de nombres de sonificacion
polling fallback si se decide simplificar a websocket o a polling unico
```

No eliminar en esta fase sin probar WebUI en placa.

## 7. Hallazgos para simplificacion futura

| Hallazgo | Impacto | Recomendacion futura |
| --- | --- | --- |
| `assets/app.js` concentra mucho contrato de snapshot | Dificulta UML y cambios de backend | Crear schema minimo de snapshot antes de tocar claves. |
| `controlValue()` conserva fallback legacy | Util para transicion, pero confunde final-v4 | En version esencial, usar solo nombres final-v4 si ya no hay snapshots legacy. |
| `/music/config` existe pero `app.js` aplica endpoints separados secuencialmente | Riesgo de configuracion parcial si falla a mitad | En simplificacion, preferir una llamada atomica `/music/config`. |
| Socket y polling fallback funcionan a la vez | Robusto, pero genera GET periodicos aunque haya socket | Decidir si se mantiene por robustez o se simplifica tras comprobar fluidez temporal. |
| Test endpoints MIDI estan mezclados con WebUI real | Son utiles para diagnostico, no para UML principal | Ocultarlos o moverlos a bloque diagnostico. |
| Piano roll y LED comparten `music.recent_notes` | Bueno para consistencia | En UML principal usar piano roll como observador; LED lateral. |
| No hay controles firmware/ADS/filtros | Bueno para seguridad | Mantener; no exponer cambios criticos en UI esencial. |
| La WebUI fue generada mayoritariamente por Codex | El autor debe entenderla para poder defenderla | Simplificar nombres, bloques y comentarios antes de usarla en UML/TFG. |

## 8. Riesgos principales

- Cambiar nombres de snapshot rompe `assets/app.js`.
- Cambiar IDs HTML rompe render sin error fuerte porque `setText` ignora ids inexistentes.
- Cambiar rutas `/music/*` rompe controles root/main/scale.
- Quitar panic MIDI deja peor operabilidad ante notas colgadas.
- Activar test loop MIDI puede enmascarar la sonificacion EEG.
- Exponer controles de firmware/ADS desde UI aumentaria riesgo de capturas no comparables.
- Dibujar demasiados puntos/notas en piano roll puede afectar rendimiento del navegador, no del backend.
- Reducir polling/socket sin medir puede empeorar la resolucion temporal percibida de la WebUI.
- Simplificar HTML/JS sin test visual puede dejar partes de la UI congeladas aunque el backend funcione.

## 9. Pruebas minimas antes de aceptar cambios WebUI

No aplicar cambios runtime/UI en esta fase documental. Si en el futuro se modifica WebUI:

1. App Lab arranca y `web.start()` no falla.
2. `GET /status` devuelve `{ok,state,window_ready}`.
3. `GET /latest` devuelve snapshot con `rx/status/features/sonification/music/midi`.
4. WebSocket `eeg_snapshot` actualiza la pagina.
5. Fallback polling funciona si no hay socket.
6. Se ven canales activos/apagados con `ADS_DIAGNOSTIC_MODE=5`.
7. Se ven nombres nuevos de sonificacion.
8. Root/main/scale cambian correctamente.
9. `/midi/panic` funciona.
10. Piano roll muestra `music.recent_notes`.
11. Si se quitan fallbacks legacy, confirmar que snapshots final-v4 no los necesitan.
12. Si se reduce test MIDI, mantener al menos una ruta o procedimiento de diagnostico fuera del UML principal.
13. Medir visualmente que la UI sigue actualizando con suficiente fluidez durante una captura real.
14. Confirmar que ninguna metrica esencial queda congelada mientras `rx_frame_rate_hz` y `rx_block_rate_hz` siguen vivos.
15. Verificar en navegador que no hay errores de consola tras aplicar cambios.

## 10. Recomendacion para version esencial UML

UML principal recomendado:

```text
EEGWebServer
  -> GET /latest
  -> socket eeg_snapshot
  -> POST /midi/panic
  -> POST /music/config
assets/app.js
  -> renderSnapshot()
  -> renderSonification()
  -> renderPianoRoll()
```

UML secundario/diagnostico:

```text
POST /midi/test-*
POST /midi/test-loop/*
legacy fallback controlValue()
LED status render
polling fallback si se decide simplificar
```

Regla para simplificacion:

```text
La WebUI es observador y control musical ligero.
No meter DSP ni adquisicion en WebUI.
No exponer controles ADS/filtros/firmware en la version esencial.
Conservar panic MIDI.
Conservar resolucion temporal percibida de la UI.
Hacer que el codigo sea explicable para el TFG.
Preferir una ruta atomica /music/config para root/main/scale.
```

