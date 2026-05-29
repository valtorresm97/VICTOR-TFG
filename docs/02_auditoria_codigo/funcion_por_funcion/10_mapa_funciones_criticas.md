# 10. Mapa de funciones criticas - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Re-auditoria final-v4: revisada contra codigo real en `firmware-final-v4` desde la rama documental `refactor/essential-eeg-midi-plan`.

Objetivo: clasificar las funciones que no deben tocarse sin pruebas. Este documento complementa `09_mapa_contratos_entre_modulos.md`: el documento 09 dice que contratos no romper; este documento 10 dice que funciones concretas protegen esos contratos.

## 1. Leyenda de criticidad

| Criticidad | Significado | Regla |
| --- | --- | --- |
| `CRITICA HARDWARE` | Toca ADS1299, SPI, DRDY, UART MIDI, pines o timing MCU | No tocar sin placa y prueba real. |
| `CRITICA RUNTIME` | Forma parte del flujo EEG->DSP->sonificacion->MIDI | No tocar sin tests de contrato y smoke App Lab. |
| `CRITICA SEGURIDAD/OPERACION` | Evita notas colgadas, artefactos sonificados o datos corruptos | Conservar en version esencial. |
| `CRITICA SNAPSHOT/UI` | Rompe WebUI, estado, paneles o reportabilidad | Tocar con prueba visual/navegador. |
| `LATERAL RUNTIME` | Capturas o LED opcional; no es nucleo EEG->MIDI | Puede quedar fuera del UML principal, pero no borrar. |
| `OFFLINE TFG` | Tools, benchmarks, figuras y reportajes | No entra en runtime esencial, pero conserva trazabilidad. |
| `COMPATIBILIDAD/HISTORICO` | Rutas legacy/wrappers/aliases | Ocultar en UML; eliminar solo tras busqueda y tests. |

## 2. Nucleo hardware/firmware

| Archivo | Funcion | Criticidad | Motivo | Prueba minima antes de tocar | UML esencial |
| --- | --- | --- | --- | --- | --- |
| `sketch/sketch.ino` | `setup()` | CRITICA HARDWARE | Inicializa Bridge, Monitor, MIDI, ADS, pines, filtros, handlers y RDATAC | Compilar + ADS ID 0x3C + modo diag + status 0xC00000 | Si |
| `sketch/sketch.ino` | `loop()` | CRITICA HARDWARE | Tiempo real: DRDY, lectura, filtros, streaming, benchmark y publicaciones | Placa: ~250 gen/s, ~31.25 blk/s, drops 0 | Si |
| `sketch/sketch.ino` | `onDrdyFalling()` | CRITICA HARDWARE | ISR de adquisicion; solo cuenta DRDY | Ver pending/lag/jitter y sample rate | Si |
| `sketch/sketch.ino` | `applyAdsDiagnosticMode()` | CRITICA HARDWARE | Fija modo ADS final-v4, BIAS, lead-off y canales | Monitor + captura por modo | Si, compacta como configuracion ADS |
| `sketch/sketch.ino` | `midiConfigureTxPolarity()` | CRITICA HARDWARE | Activa TX invertido obligatorio para circuito MIDI OUT | Test MIDI fisico con sintetizador | Si |
| `sketch/sketch.ino` | `midi_bytes()` | CRITICA HARDWARE | Handler Bridge hacia UART MIDI fisica | Test `midi_bytes`, nota y panic | Si |
| `sketch/sketch.ino` | `led_matrix_row()` | LATERAL RUNTIME | Handler LED opcional/desactivado por defecto | Packing bit-exact + prueba si se activa LED | No, solo lateral |
| `sketch/streaming.h` | `TxBlockRing.appendSampleToFillBlock()` | CRITICA RUNTIME | Agrupa 8 muestras en contrato `eeg_block_uV` | Test sample_count/indices | Si |
| `sketch/streaming.h` | `TxBlockRing.enqueueCompletedBlock()` | CRITICA RUNTIME | Encola bloques o cuenta drops | Test overflow/drops | Si |
| `sketch/streaming.h` | `TxBlockRing.publishPendingBlocks()` | CRITICA RUNTIME | Emite payload manual `Bridge.notify("eeg_block_uV")` | Parser test + placa recibe ~31.25 blk/s | Si |
| `sketch/filters.h` | `DCBlocker.process()` | CRITICA HARDWARE | Filtro HP 0.5 Hz antes de Python | Respuesta frecuencia + captura A/B | Si, como bloque filtros MCU |
| `sketch/filters.h` | `Biquad.process()` | CRITICA HARDWARE | Notch 50 Hz y LP 40 Hz antes de Python | Respuesta frecuencia + captura A/B | Si, como bloque filtros MCU |
| `sketch/bench.h` | `BenchStats` y reportes | OFFLINE TFG | Observabilidad temporal MCU por Monitor | Parsear log benchmark final | No, observabilidad lateral |

## 3. Driver ADS1299/SPI

| Archivo | Funcion | Criticidad | Motivo | Prueba minima antes de tocar | UML esencial |
| --- | --- | --- | --- | --- | --- |
| `ADS1299Plus.cpp` | `begin()` | CRITICA HARDWARE | Reset, STOP, SDATAC, lectura ID y validacion 4ch | ADS ID 0x3C + begin OK | Si |
| `ADS1299Plus.cpp` | `configureDefaults()` | CRITICA HARDWARE | Registros base CONFIG/CH/BIAS/LOFF | Leer/validar registros si se modifica | Si, compacta |
| `ADS1299Plus.cpp` | `cmdRDATAC()` / `cmdSDATAC()` | CRITICA HARDWARE | Controla modo continuo y escritura segura de registros | Captura sin invalid status | Si |
| `ADS1299Plus.cpp` | `readFrameRDATAC()` | CRITICA HARDWARE | Lee 15 bytes, status y CH1-CH4 | Status sync y sample rate | Si |
| `ADS1299Plus.h` | `unpack24()` | CRITICA RUNTIME | Sign-extension 24-bit | Test bordes 0x7FFFFF/0x800000 | Si |
| `ADS1299Plus.h` | `statusHasSync()` | CRITICA RUNTIME | Valida prefijo ADS `0xC00000` | Test valid/invalid | Si |
| `ADS1299_Registers.h` | Helpers CONFIG1/CONFIG3/CHn | CRITICA HARDWARE | Bits fijos, gain, BIAS, MUX, lead-off | Datasheet + captura | Si, compacta |
| `ADS1299_SafeSPI.cpp` | `begin()` | CRITICA HARDWARE | SPI MODE1, MSBFIRST, 2 MHz | ADS ID y RDATAC | Si |
| `ADS1299_SafeSPI.cpp` | `select()` / `xfer()` / `deselect()` | CRITICA HARDWARE | Transacciones CS/SPI | ADS ID y status | Si |

Nota para simplificacion futura: se detecto doble inicializacion `safeSpi.begin()` + `ads.begin()->spi_.begin()`. No es fallo demostrado; queda como deuda tecnica importante para revisar solo con placa.

## 4. Contrato EEG Python y receiver

| Archivo | Funcion | Criticidad | Motivo | Prueba minima antes de tocar | UML esencial |
| --- | --- | --- | --- | --- | --- |
| `python/eeg_contract.py` | `parse_eeg_block_values()` | CRITICA RUNTIME | Parser del payload `eeg_block_uV` | Tests longitudes/shape | Si |
| `python/eeg_contract.py` | `iter_eeg_block_samples()` | CRITICA RUNTIME | Convierte bloque en filas con sample_idx | Test sample indices | Si |
| `python/eeg_contract.py` | `is_valid_ads1299_status()` | CRITICA RUNTIME | Valida prefijo ADS | Test status | Si |
| `python/receiver.py` | `linux_started()` | CRITICA RUNTIME | Handshake para que MCU empiece streaming | App Lab smoke | Si, compacta |
| `python/receiver.py` | `eeg_block_uV()` | CRITICA RUNTIME | Callback Bridge principal; encola bloques ligeros | Simular payload + metrics | Si |
| `python/receiver.py` | `drain_blocks_to_processor()` | CRITICA RUNTIME | Entrega datos a DSP y captura lateral | Test cola/backlog | Si |
| `python/receiver.py` | `eeg_frame_uV()` | COMPATIBILIDAD/HISTORICO | Ruta antigua de muestra individual | Buscar referencias antes de eliminar | No |

## 5. DSP, quality gate y features

| Archivo | Funcion | Criticidad | Motivo | Prueba minima antes de tocar | UML esencial |
| --- | --- | --- | --- | --- | --- |
| `python/eeg_signal_processor.py` | `add_block_uV()` | CRITICA RUNTIME | Conversion uV->V y escritura en ring buffer | Test 1000 uV -> 0.001 V + wrap | Si |
| `python/eeg_signal_processor.py` | `get_signal_window()` | CRITICA RUNTIME | Extrae CH1 reciente para DSP | Test wrap/canal | Si |
| `python/eeg_signal_processor.py` | `compute_live_features()` | CRITICA RUNTIME | Ruta live benchmarkeada para features | Seno 10 Hz + benchmark captura real | Si |
| `python/eeg_signal_processor.py` | `compute_quality_diagnostics()` | CRITICA SEGURIDAD/OPERACION | RMS/PTP/50Hz/saltos/saturacion para gate | Test clean/bad/artifact | Si, compacta como `SignalQuality` |
| `python/eeg_signal_processor.py` | `compute_online_features()` | COMPATIBILIDAD/HISTORICO | Ruta secundaria no principal | No priorizar; excluir UML | No |
| `python/dsp_core.py` | `preprocess()` | CRITICA RUNTIME | Detrend/outlier handling antes de PSD | Test outlier y transitorios | Si, dentro de DSPCore |
| `python/dsp_core.py` | `compute_psd()` | CRITICA RUNTIME | Selecciona multitaper/Welch/periodogram | Test seno 10 Hz | Si |
| `python/dsp_core.py` | `_compute_psd_multitaper()` | CRITICA RUNTIME | Fuente unica PSD multitaper | Test seno/ruido/captura | Si |
| `python/dsp_core.py` | `compute_bandpower()` | CRITICA RUNTIME | Bandpowers delta..gamma | Test PSD plana/suma relativa | Si |
| `python/dsp_core.py` | `compute_features()` | CRITICA RUNTIME | RMS, picos y bandas | Test schema + captura | Si |
| `python/spectral_quality.py` | `compute_spectral_quality()` | CRITICA SEGURIDAD/OPERACION | Quality gate que evita sonificar artefactos | Tests clean/bad/artifact | Si, compacta como `QualityGate` |

Regla: `compute_quality_diagnostics()` y `compute_spectral_quality()` se conservan en la version esencial, pero como bloque compacto `SignalQuality / QualityGate`.

## 6. Backend, snapshot y orquestacion

| Archivo | Funcion | Criticidad | Motivo | Prueba minima antes de tocar | UML esencial |
| --- | --- | --- | --- | --- | --- |
| `python/main.py` | `loop()` | CRITICA RUNTIME | Step backend + publica snapshot + sleep 20 ms | App Lab smoke | Si, compacta |
| `python/backend_service.py` | `__init__()` | CRITICA RUNTIME | Construye receiver, DSP, sonificacion, MIDI, WebUI state, capture, LED | App Lab smoke | Si, como constructor del sistema |
| `python/backend_service.py` | `step()` | CRITICA RUNTIME | Orquesta drain RX, capture, DSP, quality, music, MIDI, LED y snapshot | Simular bloques + placa | Si |
| `python/backend_service.py` | `_build_snapshot()` | CRITICA SNAPSHOT/UI | Contrato WebUI/disco/tools | Snapshot schema + browser | Si, como salida de estado |
| `python/backend_service.py` | `_maybe_generate_music()` | CRITICA RUNTIME | Genera MusicSegment, Bar, NoteEvent y agenda MIDI | Test features sinteticas | Si |
| `python/backend_service.py` | `_pump_midi()` | CRITICA RUNTIME | Extrae eventos vencidos y envia por transporte | Scheduler/transport tests | Si |
| `python/backend_service.py` | `send_panic()` | CRITICA SEGURIDAD/OPERACION | Limpia scheduler y envia panic MIDI | Test POST `/midi/panic` + placa | Si |
| `python/backend_service.py` | `update_music_config()` | CRITICA SEGURIDAD/OPERACION | Cambia root/main/scale y llama panic | HTTP smoke + snapshot | Si |
| `python/backend_service.py` | `_maybe_update_led_matrix()` | LATERAL RUNTIME | Actualiza LED opcional si enabled | Test disabled/enabled | No, lateral |
| `python/backend_service.py` | `_pump_midi_test_loop()` | COMPATIBILIDAD/HISTORICO | Diagnostico MIDI, no ruta EEG->MIDI | Test si se conserva | No |
| `python/app_state.py` | `atomic_write_json()` | CRITICA SNAPSHOT/UI | Evita JSON parcial para snapshot/status | Temp + NaN test | Si, compacta |

## 7. Sonificacion, musica y MIDI

| Archivo | Funcion | Criticidad | Motivo | Prueba minima antes de tocar | UML esencial |
| --- | --- | --- | --- | --- | --- |
| `python/sonification_features.py` | `build_raw_sonification_features()` | CRITICA RUNTIME | Mapea features EEG a controles final-v4 | Tests con features reales/sinteticas | Si |
| `python/sonification_features.py` | `SonificationFeatureAdapter.update()` | CRITICA RUNTIME | Aplica baseline, quality gate y EMA | Test gate 0/1 y secuencia | Si |
| `python/sonification_features.py` | `SonificationFeatures.to_dict()` | CRITICA SNAPSHOT/UI | Claves publicas final-v4 | Snapshot/report tests | Si |
| `python/music_segment.py` | `MusicSegmentBuilder.build_live_segment()` | CRITICA RUNTIME | Convierte controles en estado musical | Test valid/invalid | Si |
| `python/music_bar.py` | `BarGenerator.generate_live_bar()` | CRITICA RUNTIME | Genera acorde y patron ritmico live | Test con seed fija | Si |
| `python/music_bar.py` | `BarGenerator.generate_bars()` | COMPATIBILIDAD/HISTORICO | Wrapper no usado por backend live | Buscar referencias antes de eliminar | No |
| `python/music_note.py` | `NoteGenerator.generate_notes_for_bar()` | CRITICA RUNTIME | Genera notas live del compas | Test escala/pitch/velocity | Si |
| `python/music_note.py` | `NoteGenerator.generate_notes_for_segment()` | COMPATIBILIDAD/HISTORICO | Wrapper multi-bar no usado por backend live | Buscar referencias antes de eliminar | No |
| `python/music_utils.py` | `note_name_to_midi()` | CRITICA SEGURIDAD/OPERACION | Valida notas root/main WebUI | Test C3..B5 y invalidas | Si, utilidad |
| `python/scale_registry.py` | `build_scale_config()` | CRITICA SEGURIDAD/OPERACION | Construye escalas WebUI/backend | Test escalas soportadas | Si, utilidad |
| `python/midi_live.py` | `notes_to_live_events()` | CRITICA RUNTIME | NoteEvent -> note_on/note_off ordenados | Test timing y orden | Si |
| `python/midi_live.py` | `event_to_midi_bytes()` | CRITICA RUNTIME | MidiLiveEvent -> bytes MIDI | Test note/program/cc | Si |
| `python/midi_live.py` | `panic_events()` | CRITICA SEGURIDAD/OPERACION | CC120/CC123 por canales | Test 16 canales | Si |
| `python/midi_live.py` | `MidiScheduler.schedule_notes()` | CRITICA RUNTIME | Agenda eventos de notas | Test due events | Si |
| `python/midi_live.py` | `MidiScheduler.pop_due_events()` | CRITICA RUNTIME | Extrae eventos por vencimiento/lookahead | Test jitter/lookahead | Si |
| `python/midi_live.py` | `MidiScheduler.panic()` | CRITICA SEGURIDAD/OPERACION | Limpia cola y active notes | Test active cleared | Si |
| `python/midi_byte_transport.py` | `send_event()` | CRITICA HARDWARE | Bridge a MCU para MIDI fisico | Mock + UART placa TXINV | Si |
| `python/midi_byte_transport.py` | `send_events()` | CRITICA RUNTIME | Envia lote de eventos MIDI | Mock + placa | Si |

## 8. WebUI y assets

| Archivo | Funcion | Criticidad | Motivo | Prueba minima antes de tocar | UML esencial |
| --- | --- | --- | --- | --- | --- |
| `python/web_server.py` | `_setup_routes()` | CRITICA SNAPSHOT/UI | Registra `/latest`, `/status`, MIDI y music routes | HTTP smoke | Si, compacta |
| `python/web_server.py` | `publish_snapshot()` | CRITICA SNAPSHOT/UI | Emite socket `eeg_snapshot` | Browser/socket smoke | Si |
| `python/web_server.py` | `post_midi_panic()` | CRITICA SEGURIDAD/OPERACION | Ruta panic MIDI | POST + placa | Si |
| `python/web_server.py` | `post_music_config()` | CRITICA SEGURIDAD/OPERACION | Ruta atomica root/main/scale | HTTP smoke | Si |
| `assets/app.js` | `renderSnapshot()` | CRITICA SNAPSHOT/UI | Render central del snapshot | Browser + consola sin errores | Si |
| `assets/app.js` | `renderSonification()` | CRITICA SNAPSHOT/UI | Muestra controles final-v4 y MIDI | Browser | Si |
| `assets/app.js` | `renderPianoRoll()` | CRITICA SNAPSHOT/UI | Evidencia visual de notas generadas | Browser | Si |
| `assets/app.js` | `sendMidiPanic()` | CRITICA SEGURIDAD/OPERACION | Boton panic | Click + placa | Si |
| `assets/app.js` | `applyMusicConfig()` | CRITICA SEGURIDAD/OPERACION | Cambia root/main/scale | Browser + snapshot | Si, pero preferir `/music/config` atomica |
| `assets/app.js` | `controlValue()` | COMPATIBILIDAD/HISTORICO | Fallback nombres legacy | Confirmar snapshots final-v4 antes de quitar | No |
| `assets/app.js` | `startPollingFallback()` | LATERAL RUNTIME | Robustez si socket falla | Browser sin socket | No, opcion de robustez |
| `assets/styles.css` | Layout visual | CRITICA SNAPSHOT/UI baja | Afecta legibilidad TFG | Browser visual | No como funcion UML |

Regla WebUI: tratar con especial cuidado. Debe conservar funcionamiento, resolucion temporal percibida, panic, root/main/scale y piano roll, pero quedar comprensible para explicar en el TFG.

## 9. Capturas, benchmarks, LED y tools laterales

| Archivo | Funcion | Criticidad | Motivo | Prueba minima antes de tocar | UML esencial |
| --- | --- | --- | --- | --- | --- |
| `python/capture_manager.py` | `poll_request()` | LATERAL RUNTIME | Consume `capture_request.json` | CLI con app viva | No, lateral |
| `python/capture_manager.py` | `add_block()` | LATERAL RUNTIME | Guarda CSV de bloques reales | Captura temporal | No, lateral |
| `python/capture_manager.py` | `finish()` | LATERAL RUNTIME | Escribe metadata y status final | Captura temporal + metadata | No, lateral |
| `python/led_matrix_visualizer.py` | `build_led_matrix_frame()` | LATERAL RUNTIME | `recent_notes` -> rows LED | Test visualizer | No, lateral |
| `python/led_matrix_transport.py` | `_pack_row()` | LATERAL RUNTIME | Empaquetado 13x8 en chunks | Bit-exact test | No, lateral |
| `python/led_matrix_transport.py` | `send_frame()` | LATERAL RUNTIME | Bridge calls LED opcionales | Mock + placa si enabled | No, lateral |
| `python/tools/capture_eeg_quality.py` | `main()` | OFFLINE TFG / CONTROL EXTERNO | Solicita captura al backend vivo | App viva + captura corta | No |
| `python/tools/final_capture_session.py` | `cmd_capture()` | OFFLINE TFG / CONTROL EXTERNO | Coordina captura final EEG+musica | Prueba corta, no sesion final | No |
| `python/tools/validate_spectral_features.py` | `validate_capture()` | OFFLINE TFG | Recalcula bandpowers, quality y sonificacion offline | Captura conocida | No |
| `python/tools/analyze_eeg_capture.py` | analisis principal | OFFLINE TFG | Reports calidad | Captura conocida | No |
| `python/tools/parse_mcu_bench_monitor.py` | parser principal | OFFLINE TFG | Parser Monitor `[BENCH]` | Log final versionado | No |
| `benchmarks/benchmark_real_capture.py` | benchmark principal | OFFLINE TFG | Mide DSP/backend sobre captura real | Captura benchmark real | No |
| `python/tools/set_ads_diagnostic_mode.py` | `main()` | CRITICA HARDWARE | Reescribe macro firmware | Diff + compile + Monitor | No, herramienta peligrosa |
| `python/tools/build_final_capture_docs_matplotlib.py` | generacion docs/figuras | OFFLINE TFG | Figuras y reportajes automaticos | Copia de captura + revisar diff | No |
| `python/tools/build_capture06_enhanced_figures.py` | generacion enhanced | OFFLINE TFG | Figuras captura 06 | Revisar PNG/links | No |

## 10. Funciones candidatas a ocultar o eliminar en simplificacion futura

No eliminar todavia. Primero busqueda de referencias, tests y prueba en placa si toca runtime.

| Funcion/ruta | Motivo para ocultar/eliminar | Condicion antes de eliminar |
| --- | --- | --- |
| `receiver.eeg_frame_uV()` | Ruta legacy de muestras individuales; final-v4 usa bloques | Buscar referencias + test `eeg_block_uV` |
| `EEGSignalProcessor.compute_online_features()` | Ruta secundaria; final-v4 usa `compute_live_features()` | Buscar referencias + test live features |
| `BarGenerator.generate_bars()` | Wrapper compatibilidad no usado por backend live | Buscar referencias + tests music |
| `NoteGenerator.generate_notes_for_segment()` | Wrapper multi-bar no usado por backend live | Buscar referencias + tests notes |
| Aliases legacy de `SonificationFeatures` | Nombres antiguos confunden TFG/UML | Migrar `MusicSegment`/BackendService a nombres nuevos |
| MIDI test loop/endpoints | Diagnostico; no flujo EEG->MIDI | Mantener procedimiento diagnostico alternativo |
| LED matrix | Lateral opcional/desactivada | Decidir si se excluye de rama esencial o se deja lateral |
| Polling fallback WebUI | Robustez extra | Medir fluidez si se elimina |
| Comentarios historicos MIDI/WebUI/firmware | Confunden lectura | Limpiar cuando se cree rama simplificada |

## 11. Regla de refactor

Antes de tocar cualquier funcion marcada critica:

1. Identificar que contrato protege en `09_mapa_contratos_entre_modulos.md`.
2. Crear o ejecutar una prueba de contrato local.
3. Si toca firmware, ADS, UART MIDI, pines, filtros MCU o Bridge timing: validar en placa.
4. Si toca WebUI: probar navegador, consola y fluidez temporal.
5. Si toca DSP/quality/sonificacion: repetir al menos una captura offline y benchmark si afecta timing.
6. Si toca tools: ejecutar sobre copia de captura real y revisar `git diff --stat`.

## 12. Prioridad para version esencial UML

Incluir en UML principal:

```text
setup/loop firmware
readFrameRDATAC -> filtros -> TxBlockRing -> eeg_block_uV
EEGReceiver.eeg_block_uV -> drain_blocks_to_processor
EEGSignalProcessor.add_block_uV -> compute_live_features
SignalQuality / QualityGate
SonificationFeatureAdapter.update
MusicSegmentBuilder.build_live_segment
BarGenerator.generate_live_bar
NoteGenerator.generate_notes_for_bar
MidiScheduler
MidiByteTransport -> midi_bytes -> Serial1/D1 TXINV
EEGWebServer snapshot + panic + music config
```

Excluir u ocultar:

```text
eeg_frame_uV
compute_online_features
generate_bars
generate_notes_for_segment
LED matrix
MIDI test loop
Tools offline
Benchmarks
Report generators
```

Conservar lateralmente:

```text
CaptureManager
capture_eeg_quality.py
validate_spectral_features.py
parse_mcu_bench_monitor.py
figures/docs tools
```

