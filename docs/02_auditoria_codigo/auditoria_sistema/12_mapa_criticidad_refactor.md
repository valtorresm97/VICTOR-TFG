# 12. Mapa de criticidad para refactor - final-v4

## 1. Objetivo

Este documento clasifica los archivos y funciones del proyecto segun el riesgo de modificarlos. Su proposito es servir como guia antes de crear la futura version simplificada/UML.

La auditoria funcion por funcion mas exhaustiva esta en:

```text
docs/02_auditoria_codigo/funcion_por_funcion/10_mapa_funciones_criticas.md
docs/02_auditoria_codigo/funcion_por_funcion/11_hallazgos_para_simplificacion_futura.md
```

Este documento no propone cambios de codigo. Define que se puede tocar, que solo debe compactarse en diagramas y que requiere pruebas en placa.

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Leyenda de criticidad

| Nivel | Significado | Regla |
| --- | --- | --- |
| `CRITICO HARDWARE` | Afecta ADS1299, SPI, DRDY, pines, filtros MCU, UART MIDI o TX invertido. | No tocar sin placa y prueba real. |
| `CRITICO CONTRATO` | Afecta formato `eeg_block_uV`, `midi_bytes`, snapshot o CSV. | No tocar sin tests de contrato. |
| `CRITICO RUNTIME` | Afecta el flujo EEG->DSP->quality->sonificacion->MIDI. | Requiere tests y smoke App Lab. |
| `CRITICO SEGURIDAD/OPERACION` | Afecta quality gate, panic MIDI, configuracion musical o errores. | Conservar en version esencial. |
| `CRITICO UI/TFG` | Afecta WebUI, snapshot visual, fluidez o explicabilidad para memoria. | Tocar con prueba visual/navegador. |
| `LATERAL RUNTIME` | Capturas o LED opcional; no es nucleo EEG->MIDI. | Puede quedar fuera del UML principal, pero no borrar. |
| `OFFLINE TFG` | Tools, benchmarks, figuras, reportajes. | No entra en runtime esencial, pero conserva evidencia. |
| `COMPATIBILIDAD/HISTORICO` | Rutas legacy/wrappers/aliases. | Ocultar en UML; eliminar solo tras busqueda y tests. |

## 3. Firmware y hardware

| Archivo/funcion | Criticidad final-v4 | Por que | Tests necesarios antes de tocar | Entra en UML principal |
| --- | --- | --- | --- | --- |
| `sketch/sketch.ino::setup()` | CRITICO HARDWARE | Inicializa Bridge, Monitor, ADS, MIDI, handlers, pines, filtros y RDATAC. | Compilar, ADS ID 0x3C, RDATAC, handlers, MIDI note. | Si |
| `sketch/sketch.ino::loop()` | CRITICO HARDWARE/RUNTIME | Ruta tiempo real ADS/Bridge/filtros/streaming/bench. | Rates 250 Hz y 31.25 blk/s, drops 0, captura real. | Si |
| `sketch/sketch.ino::onDrdyFalling()` | CRITICO HARDWARE | ISR de adquisicion; no debe bloquear. | DRDY 250 Hz, sin bloqueo ISR, lag controlado. | Si |
| `sketch/sketch.ino::applyAdsDiagnosticMode()` | CRITICO HARDWARE | Config analogica ADS, modo 5 CH1-only, BIAS/lead-off. | Captura modo 5, status valido, metadata clara. | Si, compacta como config ADS |
| `sketch/sketch.ino::midiConfigureTxPolarity()` | CRITICO HARDWARE | Activa TX invertido necesario para MIDI OUT. | Nota fisica + panic en sintetizador externo. | Si |
| `sketch/sketch.ino::midi_bytes()` | CRITICO HARDWARE/CONTRATO | Handler `Bridge.call("midi_bytes")` hacia UART fisica. | Mock Python + prueba placa MIDI. | Si |
| `sketch/sketch.ino::led_matrix_row()` | LATERAL RUNTIME | LED opcional/desactivado; usa Bridge si se activa. | Packing bit-exact + prueba LED si se activa. | No, lateral |
| `ADS1299Plus::begin()` | CRITICO HARDWARE | Power-up, reset, ID y variante ADS1299-4. | ID 0x3C y begin OK. | Si |
| `ADS1299Plus::configureDefaults()` | CRITICO HARDWARE | Registros base CONFIG/CH/BIAS/LOFF. | Readback si se modifica, captura real. | Si, compacta |
| `ADS1299Plus::readFrameRDATAC()` | CRITICO HARDWARE | Lectura frame 15 bytes y status. | Test interno, status 0xC00000, sample rate. | Si |
| `ADS1299Plus::unpack24()` | CRITICO CONTRATO | Sign extension signed 24-bit. | Tests positivos/negativos extremos. | Si |
| `ADS1299_Registers.h` | CRITICO HARDWARE | Defaults y bits ADS. | Datasheet, readback, short/test/real. | Si, compacta |
| `ADS1299_SafeSPI::begin/select/xfer/deselect` | CRITICO HARDWARE | SPI mode/frecuencia/CS. | ID ADS y frames validos. | Si |
| `filters.h` | CRITICO HARDWARE/RUNTIME | Cambia espectro antes de Python. | Senal sintetica, captura comparativa, PSD. | Si, como filtros MCU |
| `streaming.h::publishPendingBlocks()` | CRITICO CONTRATO | Contrato Bridge payload `eeg_block_uV`. | Receiver unit test, captura real sin malformed. | Si |
| `bench.h` | OFFLINE TFG | Observabilidad temporal MCU por Monitor. | Parsear log final benchmark. | No, lateral |
| `synthetic.h` | COMPATIBILIDAD/DIAGNOSTICO | Test sin ADS real, no evidencia final. | Solo si se usa modo sintetico. | No |

## 4. Receiver, contrato y backend Python

| Archivo/funcion | Criticidad final-v4 | Por que | Tests necesarios antes de tocar | Entra en UML principal |
| --- | --- | --- | --- | --- |
| `eeg_contract.py::parse_eeg_block_values()` | CRITICO CONTRATO | Parser central `eeg_block_uV`. | Payload valido/malformed/status/gaps. | Si |
| `eeg_contract.py::iter_eeg_block_samples()` | CRITICO CONTRATO | Reconstruye filas por muestra. | Indices/timestamps/shape. | Si |
| `receiver.py::eeg_block_uV()` | CRITICO RUNTIME/CONTRATO | Callback Bridge principal. | Tests payload + App Lab smoke. | Si |
| `receiver.py::drain_blocks_to_processor()` | CRITICO RUNTIME | Acopla RX a buffer y capture sink lateral. | Tests cola/drops/capture sink. | Si |
| `receiver.py::eeg_frame_uV()` | COMPATIBILIDAD/HISTORICO | Ruta antigua de muestra individual. | Buscar referencias antes de eliminar. | No |
| `backend_service.py::__init__()` | CRITICO RUNTIME | Construye receiver, DSP, quality, music, MIDI, capture, WebUI, LED. | App Lab smoke. | Si, compacta |
| `backend_service.py::step()` | CRITICO RUNTIME | Orquestador global de cada iteracion. | Fake receiver/proc + captura real. | Si |
| `backend_service.py::_build_snapshot()` | CRITICO CONTRATO/UI | Contrato WebUI/disco/tools. | Snapshot schema + navegador. | Si, como salida estado |
| `backend_service.py::_maybe_generate_music()` | CRITICO RUNTIME | Genera segmento, bar, notas y agenda MIDI. | Features sinteticas + notes. | Si |
| `backend_service.py::_pump_midi()` | CRITICO RUNTIME | Extrae eventos y envia por transporte. | Scheduler/transport tests. | Si |
| `backend_service.py::send_panic()` | CRITICO SEGURIDAD/OPERACION | Limpia notas y envia panic. | POST `/midi/panic` + placa. | Si |
| `backend_service.py::update_music_config()` | CRITICO SEGURIDAD/OPERACION | Cambia root/main/scale y resetea musica. | HTTP + snapshot + panic. | Si |
| `backend_service.py::_maybe_update_led_matrix()` | LATERAL RUNTIME | LED opcional desde recent_notes. | Test disabled/enabled. | No |
| `backend_service.py::_pump_midi_test_loop()` | COMPATIBILIDAD/DIAGNOSTICO | Test MIDI sin EEG. | Conservar solo como diagnostico. | No |
| `main.py::loop()` | CRITICO RUNTIME | Llama backend step y publica snapshot. | App Lab smoke. | Si, compacta |
| `app_state.py::atomic_write_json()` | CRITICO CONTRATO/OPERACION | Evita snapshots/status corruptos. | Escritura atomica + JSON seguro. | Si, compacta |

## 5. DSP, quality gate y sonificacion

| Archivo/funcion | Criticidad final-v4 | Por que | Tests necesarios antes de tocar | Entra en UML principal |
| --- | --- | --- | --- | --- |
| `eeg_signal_processor.py::add_block_uV()` | CRITICO RUNTIME | Conversion uV->V y ring buffer. | 1000 uV -> 0.001 V, wrap. | Si |
| `eeg_signal_processor.py::get_signal_window()` | CRITICO RUNTIME | Extrae CH1 reciente. | Window/wrap/canal. | Si |
| `eeg_signal_processor.py::compute_live_features()` | CRITICO RUNTIME | Ruta live benchmarkeada. | Seno 10 Hz + captura + benchmark. | Si |
| `eeg_signal_processor.py::compute_quality_diagnostics()` | CRITICO SEGURIDAD/OPERACION | RMS/PTP/50Hz/saltos/saturacion. | Clean/artifact/bad. | Si, compacta como SignalQuality |
| `eeg_signal_processor.py::compute_online_features()` | COMPATIBILIDAD/HISTORICO | Ruta secundaria no principal. | Buscar referencias antes de eliminar. | No |
| `dsp_core.py::preprocess()` | CRITICO RUNTIME | Detrend/outlier handling. | Outlier/transitorio. | Si, dentro de DSPCore |
| `dsp_core.py::compute_psd()` | CRITICO RUNTIME | PSD multitaper/Welch/periodogram. | Seno 10 Hz. | Si |
| `dsp_core.py::_compute_psd_multitaper()` | CRITICO RUNTIME | Metodo principal PSD final-v4. | Seno/ruido/captura. | Si |
| `dsp_core.py::compute_bandpower()` | CRITICO RUNTIME | Bandpowers delta..gamma. | PSD plana/suma relativa. | Si |
| `dsp_core.py::compute_features()` | CRITICO RUNTIME | Features finales de DSP. | Schema + captura. | Si |
| `spectral_quality.py::compute_spectral_quality()` | CRITICO SEGURIDAD/OPERACION | Gate contra artefactos. | Score por escenarios y captura offline. | Si, como QualityGate |
| `sonification_features.py::build_raw_sonification_features()` | CRITICO RUNTIME | Mapea features EEG a controles. | Golden outputs features ejemplo. | Si |
| `sonification_features.py::SonificationFeatureAdapter.update()` | CRITICO RUNTIME | Quality gate + baseline + EMA. | Gate 0/1 y secuencia. | Si |
| `sonification_features.py::SonificationFeatures.to_dict()` | CRITICO CONTRATO/UI | Nombres publicos final-v4. | Snapshot/report tests. | Si |

## 6. Musica y MIDI

| Archivo/funcion | Criticidad final-v4 | Por que | Tests necesarios antes de tocar | Entra en UML principal |
| --- | --- | --- | --- | --- |
| `music_segment.py::MusicSegmentBuilder.build_live_segment()` | CRITICO RUNTIME | Crea estado musical por compas. | Root/main/scale validos. | Si |
| `music_bar.py::BarGenerator.generate_live_bar()` | CRITICO RUNTIME | Acorde, slots y ritmo live. | Seed fija + rangos. | Si |
| `music_bar.py::generate_bars()` | COMPATIBILIDAD/HISTORICO | Wrapper no usado por backend live. | Buscar referencias. | No |
| `music_note.py::NoteGenerator.generate_notes_for_bar()` | CRITICO RUNTIME | Genera notas live. | Pitch/velocity/duracion. | Si |
| `music_note.py::generate_notes_for_segment()` | COMPATIBILIDAD/HISTORICO | Wrapper multi-bar no usado por backend live. | Buscar referencias. | No |
| `music_utils.py::note_name_to_midi()` | CRITICO SEGURIDAD/OPERACION | Valida root/main WebUI. | C3..B5 e invalidas. | Si, utilidad |
| `scale_registry.py::build_scale_config()` | CRITICO SEGURIDAD/OPERACION | Escalas disponibles. | Todas las escalas UI. | Si, utilidad |
| `midi_live.py::notes_to_live_events()` | CRITICO RUNTIME | NoteEvent -> note_on/off. | Orden y tiempos. | Si |
| `midi_live.py::event_to_midi_bytes()` | CRITICO CONTRATO | Bytes MIDI estandar. | note_on/off, CC, program. | Si |
| `midi_live.py::panic_events()` | CRITICO SEGURIDAD/OPERACION | CC120/CC123. | Canales y bytes. | Si |
| `midi_live.py::MidiScheduler.schedule_notes()` | CRITICO RUNTIME | Agenda notas. | Due events. | Si |
| `midi_live.py::MidiScheduler.pop_due_events()` | CRITICO RUNTIME | Extrae eventos vencidos. | Lookahead/jitter. | Si |
| `midi_live.py::MidiScheduler.panic()` | CRITICO SEGURIDAD/OPERACION | Limpia cola/active notes. | Active cleared. | Si |
| `midi_byte_transport.py::send_event()` | CRITICO CONTRATO/HARDWARE | Bridge a `midi_bytes`. | Mock Bridge + placa. | Si |
| `midi_byte_transport.py::send_events()` | CRITICO RUNTIME | Envia lotes. | Mock + placa. | Si |

## 7. WebUI y assets

| Archivo/funcion | Criticidad final-v4 | Por que | Tests necesarios antes de tocar | Entra en UML principal |
| --- | --- | --- | --- | --- |
| `web_server.py::_setup_routes()` | CRITICO UI/TFG | Registra `/latest`, `/status`, `/midi/panic`, `/music/*`, socket. | HTTP smoke. | Si, compacta |
| `web_server.py::publish_snapshot()` | CRITICO UI/TFG | Emite `eeg_snapshot`. | Socket/browser. | Si |
| `web_server.py::post_midi_panic()` | CRITICO SEGURIDAD/OPERACION | Ruta panic WebUI. | POST + placa. | Si |
| `web_server.py::post_music_config()` | CRITICO SEGURIDAD/OPERACION | Ruta atomica root/main/scale. | HTTP + snapshot. | Si |
| `web_server.py::post_music_scale/root/main()` | CRITICO SEGURIDAD/OPERACION | Rutas actuales de controles musicales. | Browser + snapshot. | Si o compactar en `/music/config` |
| `assets/app.js::renderSnapshot()` | CRITICO UI/TFG | Render central del estado. | Snapshot fixture + navegador. | Si |
| `assets/app.js::renderSonification()` | CRITICO UI/TFG | Muestra controles final-v4. | Browser. | Si |
| `assets/app.js::renderPianoRoll()` | CRITICO UI/TFG | Evidencia visual de notas. | Browser. | Si |
| `assets/app.js::sendMidiPanic()` | CRITICO SEGURIDAD/OPERACION | Boton panic. | Click + placa. | Si |
| `assets/app.js::applyMusicConfig()` | CRITICO SEGURIDAD/OPERACION | Cambia root/main/scale. | Browser + snapshot. | Si, pero migrable a `/music/config` atomico |
| `assets/app.js::controlValue()` | COMPATIBILIDAD/HISTORICO | Fallback nombres legacy. | Confirmar snapshot final-v4 antes de quitar. | No |
| `assets/app.js::startPollingFallback()` | LATERAL RUNTIME | Robustez si falla socket. | Browser sin socket. | No, salvo decidir mantener robustez |
| `assets/styles.css` | CRITICO UI/TFG BAJO | Legibilidad y defensa TFG. | Revision visual. | No como funcion UML |

Nota: WebUI no es critica para leer ADS o enviar MIDI si el backend sigue vivo, pero si es critica para operacion, panic, control musical, supervision y explicabilidad del TFG. Por eso no debe tratarse como "no critica" en final-v4.

## 8. Capturas, LED, tools y documentacion

| Archivo/funcion | Criticidad final-v4 | Por que | Tests necesarios antes de tocar | Entra en UML principal |
| --- | --- | --- | --- | --- |
| `capture_manager.py::poll_request()` | LATERAL RUNTIME | Consume `capture_request.json`. | CLI con app viva. | No, lateral |
| `capture_manager.py::add_block()` | LATERAL RUNTIME | Guarda CSV real. | Captura temporal. | No, lateral |
| `capture_manager.py::finish()` | LATERAL RUNTIME | Metadata y status final. | Captura temporal + metadata. | No, lateral |
| `led_matrix_visualizer.py::build_led_matrix_frame()` | LATERAL RUNTIME | `recent_notes` -> rows LED. | Test visualizer. | No, lateral |
| `led_matrix_transport.py::_pack_row()` | LATERAL RUNTIME | Empaquetado 13x8. | Bit-exact. | No, lateral |
| `led_matrix_transport.py::send_frame()` | LATERAL RUNTIME | Bridge calls LED opcionales. | Mock + placa si enabled. | No, lateral |
| `python/tools/capture_eeg_quality.py` | OFFLINE TFG / CONTROL EXTERNO | Solicita captura al backend vivo. | App viva + captura corta. | No |
| `python/tools/final_capture_session.py` | OFFLINE TFG / CONTROL EXTERNO | Sesion final EEG+musica. | Prueba corta. | No |
| `python/tools/validate_spectral_features.py` | OFFLINE TFG | Recalcula bands/quality/sonif. | Captura conocida. | No |
| `python/tools/parse_mcu_bench_monitor.py` | OFFLINE TFG | Parser benchmark MCU. | Log final versionado. | No |
| `python/tools/set_ads_diagnostic_mode.py` | CRITICO HARDWARE / TOOL | Reescribe macro firmware. | Diff + compile + Monitor. | No, herramienta peligrosa |
| `python/tools/build_final_capture_docs_matplotlib.py` | OFFLINE TFG | Figuras/reportajes. | Copia de captura + revisar diff. | No |
| `docs/validacion_tfg/*` | DOCUMENTACION/EVIDENCIA | Resultados TFG. | Revision manual, enlaces. | No |
| `captures/*` | DATOS/REPORTS | Datos experimentales. | No modificar salvo regeneracion controlada. | No |

## 9. Refactor permitido por nivel

| Nivel | Permitido | No permitido |
| --- | --- | --- |
| CRITICO HARDWARE | Comentarios, documentacion, tests. | Cambiar comportamiento sin placa. |
| CRITICO CONTRATO | Anadir tests/schema, comentarios. | Renombrar campos o cambiar payload sin migracion completa. |
| CRITICO RUNTIME | Refactor interno con tests equivalentes. | Cambiar semantica/timing sin benchmark. |
| CRITICO SEGURIDAD/OPERACION | Mejorar claridad y tests. | Quitar panic, quality gate o validacion de notas. |
| CRITICO UI/TFG | Reordenar con prueba visual y snapshot fixture. | Cambiar claves/IDs/rutas sin navegador. |
| LATERAL RUNTIME | Omitir del UML principal, mantener funcional. | Borrar sin busqueda y pruebas. |
| OFFLINE TFG | Reorganizar documentacion, no mezclar con runtime. | Borrar resultados/figuras/reportes. |
| COMPATIBILIDAD/HISTORICO | Ocultar en UML, marcar legacy. | Eliminar sin confirmar referencias externas. |

## 10. Ruta de validacion antes de tocar cada bloque

### Firmware/ADS/MIDI fisico

```text
compile App Lab
ADS ID 0x3C
RDATAC/status 0xC00000
rx_frame_rate_hz ~= 250
rx_block_rate_hz ~= 31.25
captura corta
nota MIDI fisica
/midi/panic
```

### Backend/DSP/Quality/Sonificacion

```text
py_compile
unit tests de contrato
seno 10 Hz
quality clean/artifact/bad
captura offline con validate_spectral_features.py
benchmark si cambia timing
```

### WebUI

```text
GET /status
GET /latest
socket eeg_snapshot
panic button
root/main/scale
piano roll
consola navegador sin errores
fluidez durante captura real
```

### Tools/capturas/docs

```text
git status limpio
ejecutar sobre copia o captura corta
revisar git diff --stat
validar enlaces Markdown
no sobrescribir reportajes manuales sin revision
```

## 11. Prioridad para version esencial/UML

### Mostrar en UML principal

```text
setup/loop firmware
readFrameRDATAC
filtros MCU
TxBlockRing / eeg_block_uV
EEGReceiver
EEGSignalProcessor
DSPCore
SignalQuality / QualityGate
SonificationFeatureAdapter
MusicSegmentBuilder
BarGenerator
NoteGenerator
MidiScheduler
MidiByteTransport
midi_bytes
Serial1/D1 TXINV
EEGWebServer snapshot + panic + music config
```

### Mostrar como lateral

```text
CaptureManager
capture_eeg_quality.py
final_capture_session.py
validate_spectral_features.py
benchmarks
LED matrix
MIDI test endpoints
report generators
```

### Ocultar como compatibilidad/historico

```text
eeg_frame_uV
compute_online_features
generate_bars
generate_notes_for_segment
legacy aliases de sonificacion
controlValue legacy fallback
comentarios historicos
```

## 12. Conclusion

El refactor futuro debe ser conservador. La version esencial no debe reducir el sistema a costa de perder validacion, panic, quality gate, MIDI fisico o trazabilidad experimental.

La regla practica es:

```text
Primero documentar y testear contratos.
Despues simplificar diagramas.
Despues refactorizar con commits pequenos.
Solo al final eliminar legacy.
```

