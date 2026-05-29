# 07. Auditoria Web UI - final-v4

## 1. Objetivo

Este documento explica la WebUI del sistema EEG-MIDI en lenguaje narrativo para que pueda entenderse y redactarse en el TFG. La auditoria funcion por funcion mas exhaustiva esta en:

```text
docs/02_auditoria_codigo/funcion_por_funcion/07_web_server_assets_funcion_por_funcion.md
```

La WebUI es una parte delicada porque fue generada principalmente por Codex y concentra mucho contrato implicito entre backend, snapshot, HTML y JavaScript. Por eso, en una futura simplificacion no debe modificarse a ciegas: debe conservar funcionamiento, fluidez temporal, panic MIDI, controles musicales y piano roll.

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Papel arquitectonico de la WebUI

La WebUI actua como:

```text
interfaz de monitorizacion
control musical ligero
herramienta de operacion y diagnostico visual
```

No es parte del DSP ni del firmware. No accede directamente al ADS1299, no calcula bandpowers, no genera notas y no envia bytes MIDI por si misma. Consume el snapshot que construye el backend y envia acciones HTTP al backend.

Flujo conceptual:

```text
BackendService._build_snapshot()
  -> web_server.publish_snapshot(snapshot)
  -> socket eeg_snapshot
  -> assets/app.js renderSnapshot()
```

Con fallback:

```text
assets/app.js
  -> GET /latest cada 400 ms
```

## 3. Estructura

La UI esta compuesta por:

- `python/web_server.py`: servidor WebUI brick, rutas HTTP y websocket.
- `assets/index.html`: estructura de paneles y controles.
- `assets/app.js`: render de snapshots, websocket, polling y acciones de usuario.
- `assets/styles.css`: estilos visuales.

No hay `dashboard.py` ni Streamlit en esta rama.

## 4. Rutas y datos

| Ruta/evento | Origen | Uso | Clasificacion |
| --- | --- | --- | --- |
| `GET /status` | `web_server.py` | Estado minimo: `ok`, `state`, `window_ready`. | Esencial simple |
| `GET /latest` | `web_server.py` | Snapshot completo backend o fallback disco. | Esencial WebUI |
| `POST /midi/panic` | `web_server.py` | All Sound Off / All Notes Off via backend. | Esencial seguridad |
| `POST /midi/test-*` | `web_server.py` | Diagnosticos MIDI sin depender de EEG. | Diagnostico |
| `POST /midi/test-loop/*` | `web_server.py` | Loop diagnostico MIDI. | Diagnostico |
| `POST /music/config` | `web_server.py` | Actualiza root/main/scale en una llamada si se envia payload. | Esencial operacion |
| `POST /music/scale/{key}` | `web_server.py` | Cambia escala musical. | Esencial actual |
| `POST /music/root/{note}` | `web_server.py` | Cambia root note C3..B5. | Esencial actual |
| `POST /music/main/{note}` | `web_server.py` | Cambia main note C3..B5. | Esencial actual |
| `eeg_snapshot` | Websocket WebUI | Push de snapshot live. | Esencial WebUI |
| Polling 400 ms | `assets/app.js` | Fallback si socket no esta disponible. | Robustez/lateral |

Para la futura simplificacion, conviene preferir una ruta atomica `/music/config` para root/main/scale, pero solo tras probar en navegador y App Lab.

## 5. Paneles

| Panel UI | Datos usados | Clave snapshot | Archivo origen | Riesgo |
| --- | --- | --- | --- | --- |
| Estado | Estado pipeline | `status.state`, `status.window_ready` | `backend_service.py` | Cambio de nombres rompe chip. |
| Rendimiento adquisicion | Tasas, indice, malformed/lost | `rx.*`, `status.last_sample_idx` | `receiver.py` | UI no muestra todos los contadores RX. |
| Canales/ADS mode | Modo ADS y canales activos/apagados | `config.ads_diagnostic_mode`, `config.channels` | `backend_service.py` | Importante para explicar CH1-only. |
| Features EEG | RMS, peaks, dominant, alpha/beta | `features.*` | `eeg_signal_processor.py`, `dsp_core.py` | `rms` esta en V, diagnostico usa uV. |
| Bandpower relativo | Delta/theta/alpha/beta/gamma | `features.bandpower_rel` | `dsp_core.py` | Depende de nombres exactos de bandas. |
| Bandpower absoluto | Potencia por banda | `features.bandpower_abs` | `dsp_core.py` | Puede interpretarse como absoluto calibrado, pero es aproximado. |
| Calidad/diagnostico | RMS uV, ptp, 50 Hz, saturacion, jumps, waveform | `diagnostics.*`, `spectral_quality.*` | `eeg_signal_processor.py`, `spectral_quality.py` | Debe quedar claro que es diagnostico/quality gate, no EEG clinico. |
| Sonificacion live | Controles musicales final-v4 | `sonification.*` | `sonification_features.py` | Cambios de nombres rompen metric cards. |
| Musica | Cadencia, acorde, escala, root/main note y selects editables | `music.*` | `backend_service.py`, `web_server.py` | Cambios UI deben validar escala/notas. |
| MIDI Live | enabled, scheduler, transport y panic | `midi.*` | `midi_live.py`, `midi_byte_transport.py` | Panic debe seguir disponible aunque transporte falle. |
| Piano roll live | Notas recientes | `music.recent_notes`, `performance.recent_notes_window_sec` | `backend_service.py` | Solo intencion musical, no confirmacion MIDI fisico. |
| Warnings | Sonif/MIDI | `sonification.valid`, `midi.live_enabled`, `midi.transport.*` | `assets/app.js` | No incluye LED ni todos los errores RX. |

## 6. Claves snapshot especialmente fragiles

Claves generales:

```text
status.state
status.window_ready
status.last_sample_idx
rx.rx_frame_rate_hz
rx.rx_block_rate_hz
rx.malformed_blocks_total
rx.lost_frames_total
rx.lost_blocks_total
features.bandpower_rel
features.bandpower_abs
diagnostics.waveform_uV
spectral_quality.score
spectral_quality.state
spectral_quality.gate_factor
music.recent_notes
music.root_note
music.main_note
music.scale_key
music.scale_options
midi.transport.sent_events_total
```

Claves de sonificacion final-v4:

```text
sonification.alpha_drive
sonification.beta_gamma_drive
sonification.rms_beta_activity
sonification.band_driven_density
sonification.spectral_register
sonification.alpha_stability
sonification.rms_band_velocity
sonification.band_note_probability
```

`assets/app.js` conserva fallback a nombres legacy mediante `controlValue()`, pero para TFG, UML y documentacion deben usarse los nombres final-v4.

## 7. Controles musicales

La WebUI permite modificar:

```text
root_note
main_note
scale_key
```

Esto afecta a la generacion musical, pero no modifica:

- ADS1299;
- firmware;
- filtros MCU;
- frecuencia de muestreo;
- quality gate;
- habilitacion MIDI;
- LED matrix.

El cambio se ejecuta en backend mediante `BackendService.update_music_config()`, que reconstruye la escala, reinicia memoria musical relevante y llama panic si procede.

## 8. Piano roll

El piano roll no lee el puerto MIDI real. Representa:

```text
music.recent_notes
```

Estas notas se guardan justo despues de la generacion musical, antes o alrededor del envio MIDI. Por tanto:

- sirve para visualizar la intencion musical del sistema;
- sirve para explicar la relacion EEG -> notas;
- no demuestra por si solo que el sintetizador externo haya recibido el MIDI fisico;
- complementa la validacion del MIDI OUT fisico, no la sustituye.

## 9. Panic MIDI

`POST /midi/panic` es esencial y debe conservarse siempre.

Su funcion es enviar mensajes de seguridad:

```text
CC120 All Sound Off
CC123 All Notes Off
```

Esto es necesario porque un error de scheduling, transporte o sintetizador puede dejar notas colgadas.

## 10. Limitaciones UI

- No muestra panel LED matrix dedicado.
- No expone controles para habilitar/deshabilitar MIDI/LED desde UI.
- No hay botones de capture start/stop; se usa CLI.
- No hay clear LED.
- Muestra `ADS_DIAGNOSTIC_MODE` y canales activos/apagados, pero no un panel BIAS/RLD detallado.
- El piano roll muestra intencion musical, no confirmacion fisica del puerto MIDI.
- Algunos fallbacks legacy siguen en `app.js` para compatibilidad.

Estas limitaciones son aceptables para final-v4. No conviene exponer controles de firmware/ADS/filtros desde la WebUI esencial.

## 11. Riesgos de modificacion

- Cambiar nombres de snapshot rompe el render.
- Cambiar IDs HTML puede dejar metricas congeladas sin error evidente.
- Cambiar rutas `/music/*` puede romper root/main/scale.
- Quitar panic reduce seguridad operativa.
- Quitar fallback socket/polling sin medir puede empeorar resolucion temporal percibida.
- Reducir demasiado los paneles puede hacer la UI menos defendible en el TFG.
- Mantener demasiados diagnosticos puede hacerla incomprensible para el autor.
- Exponer controles ADS/filtros desde UI puede generar capturas no comparables.

## 12. Criterio especial de simplificacion futura

La WebUI debe simplificarse de forma delicada.

Objetivo:

```text
conservar funcionamiento
conservar resolucion temporal percibida
conservar panic MIDI
conservar root/main/scale
conservar piano roll
hacer codigo y diagrama comprensibles
facilitar redaccion del TFG
```

Reglas:

1. No meter DSP ni adquisicion en WebUI.
2. No exponer ADS1299, filtros MCU ni firmware.
3. Mantener WebUI como observador y control musical ligero.
4. Mantener `POST /midi/panic`.
5. Mantener una forma clara de cambiar root/main/scale.
6. Mantener `music.recent_notes` y piano roll.
7. Antes de quitar compatibilidad legacy, confirmar snapshot final-v4.
8. Antes de tocar socket/polling, comprobar fluidez visual.
9. Antes de cambiar rutas `/music/*`, probar en navegador y App Lab.
10. Antes de reordenar `assets/app.js`, crear schema minimo de snapshot.

## 13. Pruebas minimas si se toca WebUI

1. App Lab arranca y `web.start()` no falla.
2. `GET /status` devuelve `ok/state/window_ready`.
3. `GET /latest` devuelve snapshot con `rx/status/features/sonification/music/midi`.
4. WebSocket `eeg_snapshot` actualiza la pagina.
5. Fallback polling funciona si no hay socket.
6. Canales activos/apagados se muestran correctamente con `ADS_DIAGNOSTIC_MODE=5`.
7. Se ven nombres nuevos de sonificacion.
8. Root/main/scale cambian correctamente.
9. `/midi/panic` funciona.
10. Piano roll muestra `music.recent_notes`.
11. No hay errores en consola del navegador.
12. Ninguna metrica esencial queda congelada durante una captura real.
13. La UI mantiene fluidez suficiente.

## 14. Relacion con futura version esencial/UML

En UML principal debe aparecer:

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

Deben quedar secundarios/diagnosticos:

```text
POST /midi/test-*
POST /midi/test-loop/*
legacy fallback controlValue()
LED status render
polling fallback si se decide simplificar
```

## 15. Conclusion

La WebUI final-v4 es una interfaz de monitorizacion y control musical. Permite observar el estado de adquisicion, DSP, quality gate, sonificacion y MIDI, y permite operar panic y configuracion musical root/main/scale.

Para el TFG debe describirse como una capa de supervision y control, no como parte del calculo DSP ni del firmware. Su simplificacion futura debe hacerla mas comprensible sin perder fluidez ni funcionalidad.





