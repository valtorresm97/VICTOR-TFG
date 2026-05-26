# 03. Backend Python funcion por funcion

## Arquitectura backend

`main.py` crea `BackendService`, crea `EEGWebServer`, arranca ambos y registra `loop()` en `App.run`. El backend registra Bridge handlers, drena bloques recibidos, actualiza buffer, calcula features cada `FEATURE_HOP_SAMPLES=64`, genera sonificacion/MIDI/LED y publica snapshots.

## Archivos y responsabilidades

| Archivo | Responsabilidad | Estado interno | Dependencias criticas |
| --- | --- | --- | --- |
| `main.py` | Arranque App Lab y loop de 20 ms | Objetos globales `backend`, `web` | `arduino.app_utils.App`, Bridge indirecto. |
| `backend_service.py` | Orquestacion completa | Procesador, receiver, capture manager, sonificacion, scheduler, transports, snapshot lock | Bridge, DSP, MIDI, LED, app_state. |
| `receiver.py` | Callback Bridge y cola | Deques, contadores RX, continuidad, tasas | `eeg_contract.py`. |
| `eeg_contract.py` | Contrato Python del payload EEG | Constantes | Debe seguir `streaming.h`. |
| `eeg_signal_processor.py` | Ring buffer y acceso a DSP | `buffer`, `write_pos`, `valid_samples` | `DSPCore`, `eeg_contract.py`. |
| `app_state.py` | Persistencia runtime atomica | Paths `state/*.json` | `runtime_config.runtime_state_dir`. |
| `runtime_config.py` | Env vars y defaults | No tiene estado mutable | `os.environ`. |
| `capture_manager.py` | Capturas CSV/metadata desde bloques | Estado de captura, CSV abierto, contadores | `eeg_contract`, `app_state.atomic_write_json`. |
| `web_server.py` | WebUI y endpoints ligeros | WebUI Brick, flag log | `app_state.read_snapshot`, backend. |

## Funciones y clases

| Archivo | Clase | Funcion | Entrada | Salida | Estado que modifica | Dependencias | Que hace | Riesgo | Test recomendado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `main.py` | N/A | module init | Import App Lab | N/A | Crea backend/web, arranca | App Lab | Construye servicio y servidor | Si falla import `arduino`, no corre fuera de placa | Smoke en App Lab. |
| `main.py` | N/A | `loop()` | Ninguna | Ninguna | Backend/Web | `backend.loop`, `web.publish_snapshot` | Step backend, publica por socket y duerme 20 ms | Sleep alto reduce refresh; bajo consume CPU | Ejecutar app y ver dashboard fluido. |
| `backend_service.py` | N/A | `_midi_to_note_name()` | MIDI int | Nombre | Ninguno | Constante notas | Snapshot musical legible | Bajo | Unit test notas borde. |
| `backend_service.py` | N/A | `_read_ads_diagnostic_mode()` | project_root | int/None | Ninguno | Lee `sketch.ino` | Extrae macro para snapshot | Si formato macro cambia queda None | Test con macro actual. |
| `backend_service.py` | N/A | `_channel_status_for_ads_mode()` | modo | lista dict | Ninguno | `NUM_CH` | Etiqueta canales activos/apagados | UI puede mostrar mal CH2-CH4 | Test modo 5. |
| `backend_service.py` | `BackendService` | `__init__()` | Ninguna | objeto | Todo el estado backend | Bridge, DSP, MIDI, LED, capture | Registra handlers y prepara pipeline | Critico: side effects Bridge | Smoke App Lab. |
| `backend_service.py` | `BackendService` | `_build_quality_rx_delta_metrics()` | metricas RX | dict deltas | `_last_quality_rx_totals` | Receiver metrics | Convierte totales en deltas para quality gate | Si se llama fuera de ciclo puede perder deltas | Test incrementos. |
| `backend_service.py` | `BackendService` | `_build_snapshot()` | Ninguna | dict snapshot | Ninguno directo | RX, proc, capture, MIDI, LED | Construye contrato UI/disco | Cambiar claves rompe assets | Snapshot schema test. |
| `backend_service.py` | `BackendService` | `_remember_recent_notes()` | notas, time_origin | Ninguna | `_recent_notes` | `NoteEvent` | Mantiene ventana para piano roll/LED | Si tiempos mal, UI/LED desincronizan | Test orden/corte. |
| `backend_service.py` | `BackendService` | `_maybe_generate_music()` | now | Ninguna | Scheduler, ultimos acordes/notas | Segment/bar/note generators | Genera compas si hay sonificacion valida | Puede crecer cola MIDI o generar jitter | Test con features sinteticas. |
| `backend_service.py` | `BackendService` | `_maybe_update_led_matrix()` | now | Ninguna | `_last_led_frame_t`, transport metrics | LED visualizer/transport | Envia frame LED si enabled y toca periodo | Bridge calls pueden cargar sistema | Test disabled/enabled. |
| `backend_service.py` | `BackendService` | `_pump_midi()` | now | Ninguna | MIDI counters | Scheduler/transport | Extrae eventos vencidos y envia/dropea | Si falla, notas pueden quedar activas | Test panic y scheduler. |
| `backend_service.py` | `BackendService` | `step()` | Ninguna | Ninguna | Todo estado vivo | Receiver, proc, quality, sonif, MIDI, LED, app_state | Loop principal backend | Critico para latencia y CPU | Simular bloques + py_compile + placa. |
| `backend_service.py` | `BackendService` | `start()` | Ninguna | None | Ninguno | N/A | Hook explicito | Bajo | Smoke. |
| `backend_service.py` | `BackendService` | `send_panic()` | Ninguna | int enviados | Scheduler/transport | `MidiScheduler.panic` | All Sound Off/All Notes Off si MIDI enabled | Si disabled devuelve 0 aunque limpia scheduler | Test POST panic. |
| `backend_service.py` | `BackendService` | `stop()` | Ninguna | Ninguna | Scheduler/transport | `send_panic` | Parada segura MIDI | Medio | App stop. |
| `backend_service.py` | `BackendService` | `loop()` | Ninguna | Ninguna | Igual que step | N/A | Alias App.run | Medio | Smoke. |
| `backend_service.py` | `BackendService` | `get_latest_snapshot()` | Ninguna | dict copy | Ninguno | Lock | Lectura thread-safe | Bajo | Thread smoke. |
| `backend_service.py` | N/A | `create_backend_service()` | Ninguna | BackendService | Limpia runtime | `clear_runtime_state` | Factory limpia snapshot/history antiguos | Si borra estado esperado por UI | Smoke. |
| `receiver.py` | `EEGReceiver` | `__init__()` | fs,num_ch,queue_max | objeto | Inicializa metricas/cola | `eeg_contract` | Prepara callback ultraligero | Critico | Test parser. |
| `receiver.py` | `EEGReceiver` | `_reset_window_metrics()` | Ninguna | Ninguna | Ventana metricas | N/A | Reinicia contadores de ventana | Bajo | Metrics reset. |
| `receiver.py` | `EEGReceiver` | `_now_us()` | Ninguna | int us | Ninguno | `perf_counter_ns` | Timing callbacks | Bajo | N/A. |
| `receiver.py` | `EEGReceiver` | `_update_queue_max()` | Ninguna | Ninguna | Maximos cola | N/A | Observabilidad backlog | Bajo | Queue fill. |
| `receiver.py` | `EEGReceiver` | `_record_frame_callback_timing()` | dt_us | Ninguna | Metricas frame callback | N/A | Acumula timing legado | Bajo | Test. |
| `receiver.py` | `EEGReceiver` | `_record_block_callback_timing()` | dt_us | Ninguna | Metricas block callback | N/A | Acumula timing bloque | Bajo | Test. |
| `receiver.py` | `EEGReceiver` | `_enqueue_block()` | `BlockItem` | Ninguna | Cola y drops | Deque | Inserta bloque y descarta oldest si llena | Critico para perdida controlada | Test overflow. |
| `receiver.py` | `EEGReceiver` | `linux_started()` | Ninguna | True | Ninguno | Bridge | Handshake MCU | Si falta, firmware no streamea | App Lab smoke. |
| `receiver.py` | `EEGReceiver` | `eeg_frame_uV()` | idx,status,chs | Ninguna | Cola, metricas | Legacy | Compatibilidad frame suelto | Legacy; puede confundir metricas | Test solo si se reactiva. |
| `receiver.py` | `EEGReceiver` | `eeg_block_uV()` | block_idx, first_sample_idx, sample_count, vals | Ninguna | Cola, continuidad, status, metricas | `parse_eeg_block_values`, status mask | Callback principal de Bridge | Critico: no hacer DSP aqui | Test payload valid/malformed. |
| `receiver.py` | `EEGReceiver` | `drain_blocks_to_processor()` | proc,max,block_sink | bloques,frames | Cola, drain metrics | `proc.add_block_uV`, capture sink | Drena bloques hacia DSP y captura | Critico: backlog/latencia | Simular bloques. |
| `receiver.py` | `EEGReceiver` | `update_rx_rate()` | Ninguna | Ninguna | Tasas RX | time | Actualiza Hz cada 1 s | Bajo | Test temporal. |
| `receiver.py` | `EEGReceiver` | `rx_frame_rate_hz/rx_block_rate_hz` | Ninguna | float | Ninguno | N/A | Propiedades | Bajo | N/A. |
| `receiver.py` | `EEGReceiver` | `get_window_metrics()` | reset bool | dict | Opcional reset ventana | N/A | Snapshot metricas RX | Cambiar claves rompe UI/quality | Snapshot schema. |
| `eeg_contract.py` | N/A | `eeg_block_value_count()` | sample_count,num_ch | int | Ninguno | Constantes | Cuenta campos por muestras | Critico para parser | Unit test. |
| `eeg_contract.py` | N/A | `is_valid_ads1299_status()` | status | bool | Ninguno | `STATUS_MASK/PREFIX` | Valida sync 0xC00000 | Critico | Test status. |
| `eeg_contract.py` | N/A | `parse_eeg_block_values()` | sample_count, vals | statuses,samples | Ninguno | `BLOCK_SAMPLES`, `NUM_CH` | Parse payload flat | Critico | Test longitud/shape. |
| `eeg_contract.py` | N/A | `iter_eeg_block_samples()` | first_idx,statuses,samples | iterator | Ninguno | `NUM_CH` | Itera filas con sample_idx | Critico para captura | Test mismatch. |
| `app_state.py` | N/A | `ensure_state_dir()` | Ninguna | Ninguna | Directorio | runtime path | Crea state dir | Bajo | Temp dir. |
| `app_state.py` | N/A | `clear_runtime_state()` | Ninguna | Ninguna | Borra snapshot/history | Paths | Limpieza arranque | Puede borrar estado debug | Smoke. |
| `app_state.py` | N/A | `json_safe()` | objeto | JSON-safe | Ninguno | math/numpy duck typing | Convierte NaN/arrays a JSON seguro | Critico para snapshots | Test NaN. |
| `app_state.py` | N/A | `atomic_write_json()` | path,payload,indent | Ninguna | Archivo destino | tempfile, fsync, replace | Escritura atomica compartida | Critico para UI/capturas | Test lectura concurrente basica. |
| `app_state.py` | N/A | `_make_public_snapshot()` | snapshot | dict | Ninguno | `json_safe` | Añade `published_at_unix` | UI/disco | Schema test. |
| `app_state.py` | N/A | `publish_snapshot/history/runtime_state()` | dicts | Ninguna | JSON runtime | `atomic_write_json` | Publica estado | Medio | Smoke. |
| `app_state.py` | N/A | `read_snapshot/read_history()` | default | dict/default | Ninguno | json | Lectura tolerante | Bajo | Malformed file. |
| `runtime_config.py` | N/A | `env_bool/int/float/choice/str()` | env name/default | valor | Ninguno | `os.environ` | Parseo robusto env | Medio | Unit env. |
| `runtime_config.py` | N/A | `runtime_state_dir()` | project_root | Path | Ninguno | `EEG_RUNTIME_STATE_DIR` | Centraliza state dir | Medio | Env override. |
| `capture_manager.py` | N/A | `_safe_condition()` | string | string | Ninguno | N/A | Sanitiza nombre carpeta | Bajo | Test espacios. |
| `capture_manager.py` | N/A | `_git_value()` | root,args | str/None | Ninguno | subprocess git | Metadata git | Bajo | Sin git. |
| `capture_manager.py` | `CaptureManager` | `__init__()` | project_root | objeto | Estado captura | runtime_config | Prepara rutas y contadores | Medio | Temp root. |
| `capture_manager.py` | `CaptureManager` | `_reset_counters()` | Ninguna | Ninguna | Estado/CSV | `_close_csv` | Limpia captura previa | Medio | Start twice. |
| `capture_manager.py` | `CaptureManager` | `_open_csv/_close_csv()` | Ninguna | Ninguna | CSV file/writer | csv | Abre/cierra `eeg_timeseries.csv` | Critico para datos | Temp capture. |
| `capture_manager.py` | `CaptureManager` | `_write_capture_row()` | row | Ninguna | CSV rows/flush | csv | Escribe incrementalmente | Critico para memoria/datos | Test 2 rows. |
| `capture_manager.py` | `CaptureManager` | `_status_payload/_publish_status()` | state,force | dict/None | status JSON | atomic_write_json | Estado captura | Medio | JSON schema. |
| `capture_manager.py` | `CaptureManager` | `poll_request()` | Ninguna | Ninguna | Estado captura/status | `capture_request.json` | Atiende start/stop | Medio | CLI capture request. |
| `capture_manager.py` | `CaptureManager` | `start()` | request | Ninguna | Captura activa, CSV | `_open_csv` | Inicia carpeta/CSV | Critico | Temp start. |
| `capture_manager.py` | `CaptureManager` | `add_block()` | block fields | Ninguna | CSV, metricas, gaps | `iter_eeg_block_samples` | Guarda bloque recibido | Critico | Simular bloque. |
| `capture_manager.py` | `CaptureManager` | `step()` | Ninguna | Ninguna | Estado captura | time | Auto-finish por duracion | Medio | Duracion corta. |
| `capture_manager.py` | `CaptureManager` | `finish()` | state | Ninguna | Metadata/status/CSV | git/eeg_contract | Cierra y escribe metadata | Critico para reports | Temp finish. |
| `capture_manager.py` | `CaptureManager` | `get_status()` | Ninguna | dict | Ninguno | status JSON | Estado para snapshot | Bajo | Idle/active. |
| `web_server.py` | `EEGWebServer` | `__init__()` | backend,port | objeto | WebUI routes | WebUI Brick | Crea servidor assets | Medio | App Lab web. |
| `web_server.py` | `EEGWebServer` | `_setup_routes()` | Ninguna | Ninguna | Rutas WebUI | WebUI | GET status/latest, POST panic, socket hooks | Cambiar rutas rompe assets | Endpoint smoke. |
| `web_server.py` | `EEGWebServer` | `get_status/get_latest()` | HTTP | dict | Ninguno | backend/app_state | Devuelve estado/snapshot | Bajo | HTTP GET. |
| `web_server.py` | `EEGWebServer` | `post_midi_panic()` | HTTP POST | dict | Scheduler/transport via backend | `send_panic` | Boton panic | Medio | POST panic. |
| `web_server.py` | `EEGWebServer` | `on_connect/on_disconnect()` | sid | Ninguna | Logs | WebUI | Socket lifecycle | Bajo | Browser connect. |
| `web_server.py` | `EEGWebServer` | `publish_snapshot()` | snapshot | Ninguna | Socket emit/log flag | WebUI | Emite `eeg_snapshot` | UI depende de frecuencia | Browser. |
| `web_server.py` | `EEGWebServer` | `start()` | Ninguna | Ninguna | WebUI server | WebUI | Arranca servidor | Medio | App Lab. |

## Flujo de datos backend

1. MCU llama `Bridge.notify("eeg_block_uV", ...)`.
2. `EEGReceiver.eeg_block_uV` valida forma, status y continuidad, y encola bloque.
3. `BackendService.step` drena hasta 16 bloques por iteracion hacia `EEGSignalProcessor.add_block_uV`.
4. `CaptureManager.add_block` recibe el mismo bloque como sink si hay captura activa.
5. Cuando hay ventana de 4 s y hop de 64 muestras, se calcula `compute_live_features`.
6. `compute_spectral_quality` decide score/gate.
7. `SonificationFeatureAdapter.update` produce controles musicales.
8. Generadores musicales programan `MidiLiveEvent`.
9. Scheduler bombea eventos hacia `MidiByteTransport`.
10. Snapshot se publica en memoria, WebSocket y disco.

## Riesgos

- `backend_service.py` concentra muchas responsabilidades; futura simplificacion debe tener tests de snapshot y flujo RX.
- `receiver.py` no debe hacer DSP en callback; su ligereza es una garantia de latencia.
- `capture_manager.py` comparte bloque con DSP; errores de escritura CSV deben aislarse sin tumbar el backend.
- `web_server.py` debe seguir siendo capa de rutas; no mover logica DSP aqui.
