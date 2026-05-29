# 03. Backend Python funcion por funcion - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Re-auditoria final-v4: revisada contra codigo real en `firmware-final-v4` desde la rama documental `refactor/essential-eeg-midi-plan`.

Objetivo de esta re-auditoria: documentar el backend Python real que orquesta recepcion EEG, buffer DSP, features, quality gate, sonificacion, MIDI fisico, WebUI, capturas y LED opcional, sin modificar runtime.

## 1. Arquitectura backend final-v4

`python/main.py` es el punto de entrada App Lab:

```text
create_backend_service()
  -> BackendService()
  -> EEGWebServer(backend)
  -> backend.start()
  -> web.start()
  -> App.run(user_loop=loop)
```

En cada iteracion:

```text
main.loop()
  -> backend.loop()
  -> backend.get_latest_snapshot()
  -> web.publish_snapshot(snap)
  -> sleep(0.02)
```

`backend_service.py` concentra el loop principal Linux:

```text
Bridge eeg_block_uV
  -> EEGReceiver.eeg_block_uV
  -> cola de bloques
  -> BackendService.step()
  -> EEGSignalProcessor.add_block_uV
  -> CaptureManager.add_block si hay captura activa
  -> compute_live_features cada 64 muestras
  -> compute_spectral_quality
  -> SonificationFeatureAdapter.update
  -> generacion musical
  -> MidiScheduler
  -> MidiByteTransport
  -> Bridge.call("midi_bytes")
  -> snapshot WebUI/disco
```

La WebUI no es Streamlit. Usa:

```text
arduino.app_bricks.web_ui.WebUI
assets/index.html
assets/app.js
assets/styles.css
```

## 2. Archivos y responsabilidades

| Archivo | Responsabilidad | Estado interno | Dependencias criticas | Estado final-v4 |
| --- | --- | --- | --- | --- |
| `python/main.py` | Arranque App Lab y loop de 20 ms | Objetos globales `backend`, `web` | `arduino.app_utils.App` | Activo. |
| `python/backend_service.py` | Orquestacion completa | Procesador, receiver, capture manager, sonificacion, scheduler, transports, snapshot lock | Bridge, DSP, MIDI, LED, app_state | Activo critico y demasiado concentrado. |
| `python/receiver.py` | Callback Bridge y cola | Deque de bloques, contadores RX, continuidad, tasas | `eeg_contract.py` | Activo critico. |
| `python/eeg_contract.py` | Contrato Python del payload EEG | Constantes y parser | Debe seguir `sketch/streaming.h` | Activo critico. |
| `python/eeg_signal_processor.py` | Ring buffer y acceso a DSP | `buffer`, `write_pos`, `valid_samples` | `DSPCore`, `eeg_contract.py` | Activo critico; se audita en documento DSP. |
| `python/app_state.py` | Persistencia runtime atomica | Paths `state/*.json` | `runtime_config.runtime_state_dir` | Activo; sostiene fallback UI/disco. |
| `python/runtime_config.py` | Env vars y defaults | No tiene estado mutable | `os.environ` | Activo; centraliza config. |
| `python/capture_manager.py` | Capturas CSV/metadata desde bloques | Estado de captura, CSV abierto, contadores | `eeg_contract`, `app_state.atomic_write_json` | Activo; no central para UML, pero integrado en backend. |
| `python/web_server.py` | WebUI y endpoints ligeros | WebUI Brick, flag log | `app_state.read_snapshot`, backend | Activo; no debe contener DSP. |

## 3. Contratos Python final-v4

| Contrato | Valor | Fuente | Riesgo |
| --- | --- | --- | --- |
| Evento EEG | `eeg_block_uV` | `eeg_contract.py` | Debe coincidir con `streaming.h`. |
| `FS_HZ` | `250` | `eeg_contract.py` | Cambiar rompe DSP, capturas y benchmarks. |
| `NUM_CH` | `4` | `eeg_contract.py` | Contrato de payload y CSV. |
| `BLOCK_SAMPLES` | `8` | `eeg_contract.py` | Contrato firmware/Python. |
| `STATUS_PREFIX` | `0xC00000` | `eeg_contract.py` | Valida sync ADS1299. |
| `STATUS_MASK` | `0xF00000` | `eeg_contract.py` | Valida status. |
| `LSB_V` | `2.235e-8` | `eeg_contract.py` | Debe coincidir con firmware si se usa para herramientas offline. |
| Feature window | `4.0 s` | `backend_service.py` | Presupuesto y PSD live. |
| Feature hop | `64 muestras` | `backend_service.py` | Presupuesto Python = 256 ms. |
| Snapshot publish | `0.2 s` | `backend_service.py` | WebUI live. |
| Disk publish | `1.0 s` | `backend_service.py` | Fallback/estado disco. |
| MIDI Bridge | `midi_bytes` | `backend_service.py`, `midi_byte_transport.py` | Debe coincidir con firmware. |
| LED Bridge | `led_matrix_row` | `backend_service.py`, LED transport | Secundario/desactivado. |

## 4. Funciones y clases principales

| Archivo | Clase | Funcion | Entrada | Salida | Estado que modifica | Dependencias | Que hace | Riesgo | Test recomendado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `main.py` | N/A | module init | Import App Lab | N/A | Crea backend/web, arranca | App Lab | Construye servicio y servidor | Si falla import `arduino`, no corre fuera de placa | Smoke en App Lab. |
| `main.py` | N/A | `loop()` | Ninguna | Ninguna | Backend/Web | `backend.loop`, `web.publish_snapshot` | Step backend, publica por socket y duerme 20 ms | Sleep alto reduce refresh; bajo consume CPU | Ejecutar app y ver WebUI fluida. |
| `backend_service.py` | N/A | `_midi_to_note_name()` | MIDI int | Nombre | Ninguno | Constante notas | Snapshot musical legible | Bajo | Unit test notas borde. |
| `backend_service.py` | N/A | `_read_ads_diagnostic_mode()` | project_root | int/None | Ninguno | Lee `sketch.ino` | Extrae macro para snapshot | Si formato macro cambia queda None | Test con macro actual. |
| `backend_service.py` | N/A | `_channel_status_for_ads_mode()` | modo | lista dict | Ninguno | `NUM_CH` | Etiqueta canales activos/apagados | UI puede mostrar mal CH2-CH4 | Test modo 5. |
| `backend_service.py` | `BackendService` | `__init__()` | Ninguna | objeto | Todo el estado backend | Bridge, DSP, MIDI, LED, capture | Registra handlers y prepara pipeline | Critico: side effects Bridge | Smoke App Lab. |
| `backend_service.py` | `BackendService` | `_build_quality_rx_delta_metrics()` | metricas RX | dict deltas | `_last_quality_rx_totals` | Receiver metrics | Convierte totales en deltas para quality gate | Si se llama fuera de ciclo puede perder deltas | Test incrementos. |
| `backend_service.py` | `BackendService` | `_build_snapshot()` | Ninguna | dict snapshot | Ninguno directo | RX, proc, capture, MIDI, LED | Construye contrato UI/disco | Cambiar claves rompe assets | Snapshot schema test. |
| `backend_service.py` | `BackendService` | `_current_chord_controls()` | Ninguna | dict | Ninguno | `SonificationFeatures` | Resume controles que justifican acordes | Usa alias legacy internos (`activity`, `tension`, etc.) aunque hay nombres reportables nuevos | Mantener alias o migrar con test. |
| `backend_service.py` | `BackendService` | `_should_play_chord()` | now | bool,reason,score | Lee estado de acorde | `_current_chord_controls` | Limita acordes por periodo/cambio | Si mal calibrado, acordes demasiado frecuentes | Test musical. |
| `backend_service.py` | `BackendService` | `_summarize_generated_notes()` | notas | None | Metricas pitch | `NoteEvent` | Resume diversidad melodica | Bajo | Test lista vacia/notas. |
| `backend_service.py` | `BackendService` | `_remember_recent_notes()` | notas, time_origin | Ninguna | `_recent_notes` | `NoteEvent` | Mantiene ventana para piano roll/LED | Si tiempos mal, UI/LED desincronizan | Test orden/corte. |
| `backend_service.py` | `BackendService` | `_maybe_generate_music()` | now | Ninguna | Scheduler, ultimos acordes/notas | Segment/bar/note generators | Genera compas si hay sonificacion valida | Puede crecer cola MIDI o generar jitter | Test con features reales/offline. |
| `backend_service.py` | `BackendService` | `_maybe_update_led_matrix()` | now | Ninguna | `_last_led_frame_t`, transport metrics | LED visualizer/transport | Envia frame LED si enabled y toca periodo | Bridge calls pueden cargar sistema | Test disabled/enabled separado. |
| `backend_service.py` | `BackendService` | `_pump_midi()` | now | Ninguna | MIDI counters | Scheduler/transport | Extrae eventos vencidos y envia/dropea | Si falla, notas pueden quedar activas | Test panic y scheduler. |
| `backend_service.py` | `BackendService` | `_pump_midi_test_loop()` | now | Ninguna | `_midi_test_loop`, MIDI counters | MIDI transport | Secuencia diagnostica live desde App Lab | Puede enmascarar sonificacion si active | Confirmar autostart false. |
| `backend_service.py` | `BackendService` | `step()` | Ninguna | Ninguna | Todo estado vivo | Receiver, proc, quality, sonif, MIDI, LED, app_state | Loop principal backend | Critico para latencia y CPU | Simular bloques + placa. |
| `backend_service.py` | `BackendService` | `send_panic()` | Ninguna | int enviados | Scheduler/transport | `MidiScheduler.panic` | All Sound Off/All Notes Off si MIDI enabled | Si disabled devuelve 0 aunque limpia scheduler | POST panic. |
| `backend_service.py` | `BackendService` | `update_music_config()` | root/main/scale | dict | Escala, root, main, scheduler, recent_notes | scale_registry, music_utils, panic | Cambia configuracion musical WebUI | Cambios mal validados pueden dejar notas colgadas | Test endpoints `/music/*`. |
| `backend_service.py` | `BackendService` | `send_test_note/send_test_sequence()` | parametros MIDI | dict | MIDI transport | MidiLiveEvent | Diagnostico MIDI directo sin EEG | Usa `time.sleep`, puede bloquear momentaneamente user_loop | Usar solo diagnostico. |
| `backend_service.py` | `BackendService` | `stop()` | Ninguna | None | Scheduler/transport | `send_panic` | Parada segura MIDI | Medio | App stop. |
| `backend_service.py` | `BackendService` | `loop()` | Ninguna | Ninguna | Igual que step | N/A | Alias App.run | Medio | Smoke. |
| `backend_service.py` | `BackendService` | `get_latest_snapshot()` | Ninguna | dict copy | Ninguno | Lock | Lectura thread-safe | Bajo | Thread smoke. |
| `backend_service.py` | N/A | `create_backend_service()` | Ninguna | BackendService | Limpia runtime | `clear_runtime_state` | Factory limpia snapshot/history antiguos | Puede borrar estado debug esperado | Smoke. |
| `receiver.py` | `EEGReceiver` | `__init__()` | fs,num_ch,queue_max | objeto | Inicializa metricas/cola | `eeg_contract` | Prepara callback ultraligero | Critico | Test parser. |
| `receiver.py` | `EEGReceiver` | `_enqueue_block()` | `BlockItem` | Ninguna | Cola y drops | Deque | Inserta bloque y descarta oldest si llena | Critico para perdida controlada | Test overflow. |
| `receiver.py` | `EEGReceiver` | `linux_started()` | Ninguna | True | Ninguno | Bridge | Handshake MCU | Si falta, firmware no streamea | App Lab smoke. |
| `receiver.py` | `EEGReceiver` | `eeg_frame_uV()` | idx,status,chs | Ninguna | Cola, metricas | Legacy | Compatibilidad frame suelto | Legacy; no ruta principal final-v4 | No usar salvo reactivar legacy. |
| `receiver.py` | `EEGReceiver` | `eeg_block_uV()` | block_idx, first_sample_idx, sample_count, vals | Ninguna | Cola, continuidad, status, metricas | `parse_eeg_block_values`, status mask | Callback principal de Bridge | Critico: no hacer DSP aqui | Test payload valid/malformed. |
| `receiver.py` | `EEGReceiver` | `drain_blocks_to_processor()` | proc,max,block_sink | bloques,frames | Cola, drain metrics | `proc.add_block_uV`, capture sink | Drena bloques hacia DSP y captura | Critico: backlog/latencia | Simular bloques. |
| `receiver.py` | `EEGReceiver` | `get_window_metrics()` | reset bool | dict | Opcional reset ventana | N/A | Snapshot metricas RX | Cambiar claves rompe UI/quality | Snapshot schema. |
| `eeg_contract.py` | N/A | `parse_eeg_block_values()` | sample_count, vals | statuses,samples | Ninguno | `BLOCK_SAMPLES`, `NUM_CH` | Parse payload flat | Critico | Test longitud/shape. |
| `eeg_contract.py` | N/A | `iter_eeg_block_samples()` | first_idx,statuses,samples | iterator | Ninguno | `NUM_CH` | Itera filas con sample_idx | Critico para captura | Test mismatch. |
| `web_server.py` | `EEGWebServer` | `_setup_routes()` | Ninguna | Ninguna | Rutas WebUI | WebUI | GET status/latest, POST panic/test/music y socket hooks | Cambiar rutas rompe assets | Endpoint smoke. |
| `web_server.py` | `EEGWebServer` | `post_music_config()` | payload | dict | Backend music config | `update_music_config` | Control root/main/scale | Debe validar inputs | Test UI/API. |
| `web_server.py` | `EEGWebServer` | `publish_snapshot()` | snapshot | Ninguna | Socket emit/log flag | WebUI | Emite `eeg_snapshot` | UI depende de frecuencia | Browser. |

## 5. Flujo de datos backend

1. MCU llama `Bridge.notify("eeg_block_uV", ...)`.
2. `EEGReceiver.eeg_block_uV()` parsea con `parse_eeg_block_values()`.
3. El callback valida longitud, `block_idx`, continuidad aproximada y `status` ADS.
4. El callback encola el bloque completo; no calcula DSP.
5. `BackendService.step()` drena hasta 16 bloques por iteracion hacia `EEGSignalProcessor.add_block_uV()`.
6. El mismo bloque pasa a `CaptureManager.add_block()` como `block_sink` si hay captura activa.
7. Cuando hay ventana de 4 s, calcula features.
8. Despues calcula features cada `FEATURE_HOP_SAMPLES=64` muestras drenadas.
9. El presupuesto temporal asociado es `64 / 250 = 256 ms`.
10. Se calcula `compute_spectral_quality()` usando features, diagnosticos y deltas RX.
11. `SonificationFeatureAdapter.update()` crea controles de sonificacion.
12. Si `valid=True`, `_maybe_generate_music()` genera compases/notas.
13. `_pump_midi()` envia eventos vencidos a `MidiByteTransport`.
14. `MidiByteTransport` usa `Bridge.call("midi_bytes")`.
15. `_maybe_update_led_matrix()` puede enviar LED si esta habilitado; por defecto no lo esta.
16. `_build_snapshot()` publica estado en memoria y disco.
17. `main.loop()` publica por WebSocket con `web.publish_snapshot()`.

## 6. Snapshot final-v4

El snapshot publico contiene, como minimo:

```text
config
status
rx
features
diagnostics
spectral_quality
capture
sonification
music
midi
led_matrix
performance
errors
```

Claves especialmente delicadas:

- `config.fs_hz`, `config.num_ch`, `config.feature_window_sec`, `config.feature_hop_samples`;
- `config.ads_diagnostic_mode`, `config.channels`;
- `rx.rx_frame_rate_hz`, `rx.rx_block_rate_hz`, `rx.invalid_status_total`, `rx.malformed_blocks_total`;
- `features.bandpower_rel`, `features.bandpower_abs`, `features.alpha_beta_ratio`;
- `spectral_quality.score`, `state`, `gate_factor`, `valid_for_sonification`;
- `sonification` con nombres reportables final-v4;
- `music.root_note`, `main_note`, `scale_key`, `recent_notes`;
- `midi.transport`, `midi.scheduler`, `midi.test_loop`;
- `led_matrix.config`, `led_matrix.transport`.

No cambiar nombres de snapshot sin revisar:

- `assets/app.js`;
- reportes offline;
- herramientas de captura;
- documentacion TFG.

## 7. WebUI y endpoints final-v4

`web_server.py` expone:

| Metodo | Ruta | Funcion |
| --- | --- | --- |
| GET | `/status` | Estado minimo backend. |
| GET | `/latest` | Snapshot actual o fallback de disco. |
| POST | `/midi/panic` | Panic MIDI. |
| POST | `/midi/test-note*` | Test nota MIDI sin EEG. |
| POST | `/midi/test-sequence*` | Test secuencia MIDI sin EEG. |
| POST | `/midi/test-loop/start*` | Loop diagnostico MIDI. |
| POST | `/midi/test-loop/stop` | Detiene loop diagnostico. |
| POST | `/music/config` | Cambia root/main/scale con payload. |
| POST | `/music/scale/{key}` | Cambia escala. |
| POST | `/music/root/{note}` | Cambia root note. |
| POST | `/music/main/{note}` | Cambia main note. |
| socket | `eeg_snapshot` | Snapshot live. |

Nota de re-auditoria: en `backend_service.py` queda un comentario historico indicando que todavia no hay controles WebUI. El codigo real final-v4 si expone controles `/music/*` y la WebUI los usa. No se modifica el comentario en esta fase, pero debe limpiarse en la futura fase de simplificacion.

## 8. Hallazgos para simplificacion futura

| Hallazgo | Impacto | Recomendacion futura |
| --- | --- | --- |
| `backend_service.py` concentra muchas responsabilidades | Dificulta UML y pruebas unitarias | Separar logicamente sin mover archivos primero: RX/DSP, quality, music, MIDI, snapshot. |
| `_current_chord_controls()` usa alias legacy | Depende de compatibilidad interna de `SonificationFeatures` | Migrar a nombres reportables final-v4 o mantener alias documentados con test. |
| `send_test_sequence()` usa `time.sleep()` | Puede bloquear el user_loop durante diagnosticos largos | Mantener solo diagnostico o convertir a scheduler no bloqueante. |
| `capture_manager.py` esta integrado en `BackendService.step()` | No es parte del flujo UML minimo, pero no se puede borrar sin romper capturas | Tratarlo como modulo lateral. |
| LED matrix cuelga de `recent_notes` | Secundario, no ruta EEG->MIDI | Omitir de UML principal o poner como consumidor lateral. |
| Snapshot es contrato informal grande | Cambios rompen WebUI/tools | Crear test de schema antes de refactor. |
| `eeg_frame_uV()` legacy sigue existiendo | Puede confundir arquitectura | Marcar como compatibilidad, no ruta principal. |

## 9. Riesgos principales

- `receiver.py` no debe hacer DSP en callback; su ligereza es garantia de latencia.
- `backend_service.py` no debe bloquear el drenaje RX con generacion musical, diagnosticos largos o I/O pesado.
- `capture_manager.py` comparte bloque con DSP; errores de CSV deben aislarse sin tumbar backend.
- `web_server.py` debe seguir siendo capa de rutas, no mover logica DSP ahi.
- Cambiar `FEATURE_HOP_SAMPLES` cambia el presupuesto de 256 ms y obliga a repetir benchmark.
- Cambiar nombres de snapshot rompe `assets/app.js` y documentos de validacion.
- Cambiar `midi_bytes` rompe MIDI fisico.
- Activar LED matrix durante benchmarks cambia la carga de Bridge y debe medirse aparte.

## 10. Pruebas minimas antes de aceptar cambios Python runtime

No aplicar cambios runtime en esta fase documental. Si en el futuro se modifica Python backend, validar:

1. `python3 -m py_compile python/*.py python/tools/*.py`.
2. App Lab arranca sin errores.
3. Firmware detecta `linux_started=true`.
4. WebUI `/status` responde.
5. WebUI `/latest` contiene snapshot no vacio.
6. `rx_frame_rate_hz ~= 250`.
7. `rx_block_rate_hz ~= 31.25`.
8. `malformed_blocks_total=0`.
9. `invalid_status_total=0` en captura estable.
10. `window_ready=True` tras 4 s.
11. `spectral_quality` aparece con `score/state/gate_factor`.
12. `sonification` contiene nombres reportables final-v4.
13. `music.recent_notes` alimenta piano roll.
14. `/midi/panic` funciona.
15. `/music/config` cambia root/main/scale sin notas colgadas.
16. Captura corta genera `eeg_timeseries.csv` y `metadata.json`.
17. Si se cambia timing, repetir benchmark Python/Linux.

## 11. Recomendacion para version esencial UML

UML principal:

```text
EEGReceiver
  -> EEGSignalProcessor
  -> DSPCore
  -> compute_spectral_quality
  -> SonificationFeatureAdapter
  -> MusicSegmentBuilder / BarGenerator / NoteGenerator
  -> MidiScheduler
  -> MidiByteTransport
  -> EEGWebServer como observador/API
```

UML lateral/secundario:

```text
CaptureManager
LedMatrixConfig / LedMatrixTransport
MIDI test loop
app_state persistence
runtime_config helpers
```

No borrar ni mover todavia. Primera fase de simplificacion recomendada:

1. Crear tests de contrato para `eeg_contract.py`.
2. Crear snapshot schema minimo.
3. Crear test de panic/MIDI transport con mock Bridge.
4. Extraer diagramas logicos sin mover imports.
5. Solo despues plantear separacion de modulos.





