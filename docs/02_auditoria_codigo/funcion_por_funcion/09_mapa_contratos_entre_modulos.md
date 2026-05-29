# 09. Mapa de contratos entre modulos - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Re-auditoria final-v4: revisada contra codigo real en `firmware-final-v4` desde la rama documental `refactor/essential-eeg-midi-plan`.

Objetivo: identificar los contratos que conectan firmware, backend Python, DSP, sonificacion, MIDI, WebUI, capturas, benchmarks y herramientas offline. Este documento debe usarse antes de cualquier simplificacion para saber que no se puede romper.

## 1. Clasificacion de contratos

| Tipo | Significado | Puede omitirse en UML principal | Puede borrarse sin pruebas |
| --- | --- | --- | --- |
| Esencial runtime | Necesario para EEG->DSP->sonificacion->MIDI fisico | No | No |
| Esencial seguridad/operacion | Panic, quality gate, status, snapshot minimo | No, aunque puede compactarse | No |
| Lateral runtime | Capturas, WebUI extendida, LED opcional | Si, si se representa lateralmente | No |
| Offline/validacion | Tools, benchmarks, figuras, reportajes | Si | No, porque son trazabilidad TFG |
| Historico/compatibilidad | Rutas legacy o aliases | Si | Solo tras busqueda y pruebas |

Regla para futura version esencial:

```text
Simplificar diagramas no significa borrar contratos.
Primero ocultar/compactar lo lateral.
Luego eliminar solo si hay busqueda de referencias, tests y prueba en placa.
```

## 2. Contratos esenciales firmware -> Python

| Contrato | Productor | Consumidor | Formato | Archivo fuente | Riesgo si cambia | Validacion necesaria | Clasificacion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `eeg_block_uV` | MCU `TxBlockRing.publishPendingBlocks()` | `EEGReceiver.eeg_block_uV()` | `block_idx`, `first_sample_idx`, `sample_count`, `8 * (status, ch1_uV, ch2_uV, ch3_uV, ch4_uV)` | `sketch/streaming.h`, `python/eeg_contract.py`, `python/receiver.py` | Rompe recepcion, capturas, DSP, WebUI y sonificacion | Test parser + placa: ~31.25 bloques/s | Esencial runtime |
| Constantes EEG | Firmware + `eeg_contract.py` | Receiver, DSP, capture, tools | `FS_HZ=250`, `NUM_CH=4`, `BLOCK_SAMPLES=8`, `LSB_V=2.235e-8`, `PGA_GAIN=24` | `sketch/sketch.ino`, `streaming.h`, `eeg_contract.py` | Escala, ventana, shape o timing incorrectos | Contract test + captura real | Esencial runtime |
| ADS1299 status | ADS1299 frame | Firmware/Python receiver/capturas | `(status & 0xF00000) == 0xC00000` | `ADS1299_Registers.h`, `ADS1299Plus.h`, `eeg_contract.py` | Datos corruptos aceptados o datos validos rechazados | Test status valid/invalid + captura | Esencial runtime |
| Frame ADS1299 | ADS1299 RDATAC | `ADS1299Plus.readFrameRDATAC()` | 15 bytes: 3 status + 4*3 canales | `ADS1299Plus.h/cpp` | Desalineacion SPI, canales corruptos | Hardware ID/status/RDATAC | Esencial firmware |
| Modo ADS final-v4 | `sketch.ino` | Capturas, docs, interpretacion CH1 | `ADS_DIAGNOSTIC_MODE=5 / bias_ch1_only_loff_off` | `sketch.ino`, docs ADS | Interpretar CH2-CH4 como EEG o capturar en modo no comparable | Monitor + metadata/notas sesion | Esencial interpretacion |
| Filtros firmware | MCU | DSP Python y validacion | HP 0.5 Hz + notch 50 Hz + LP 40 Hz + salida uV | `sketch/filters.h`, `sketch.ino` | Cambia espectro, quality gate y bandpowers | Captura A/B + benchmark | Esencial runtime |

## 3. Contratos Python runtime internos

| Contrato | Productor | Consumidor | Formato | Archivo fuente | Riesgo si cambia | Validacion necesaria | Clasificacion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Bloques RX en cola | `EEGReceiver.eeg_block_uV()` | `BackendService.step()` | `BlockItem` con block_idx, first_sample_idx, statuses, samples | `receiver.py` | Backlog, perdidas o DSP sin datos | Simular payload + placa | Esencial runtime |
| Buffer EEG | `EEGSignalProcessor.add_block_uV()` | `compute_live_features`, diagnostics, snapshot | Ring buffer multicanal en voltios | `eeg_signal_processor.py` | Unidades uV/V rotas, features falsas | Unit test conversion + seno | Esencial runtime |
| Features live | `EEGSignalProcessor.compute_live_features()` | quality, sonificacion, WebUI | dict con RMS, bandpowers, peaks, ratios | `eeg_signal_processor.py`, `dsp_core.py` | Sonificacion y UI dejan de representar EEG | Seno + captura + benchmark | Esencial runtime |
| Quality diagnostics | `EEGSignalProcessor.compute_quality_diagnostics()` | `compute_spectral_quality()` y snapshot | RMS/PTP/percentiles/saturacion/flatline/jumps/50Hz/waveform | `eeg_signal_processor.py` | Gate pierde indicadores de artefacto | Test clean/bad/artifact | Esencial seguridad |
| Quality gate | `compute_spectral_quality()` | `SonificationFeatureAdapter`, WebUI | `score`, `state`, `gate_factor`, `valid_for_sonification`, warnings | `spectral_quality.py` | Ventanas malas vuelven a mover musica sin barrera | Tests + captura con artefacto | Esencial seguridad |
| SonificationFeatures | `SonificationFeatureAdapter.update()` | `MusicSegmentBuilder`, snapshot | Dataclass normalizada con nombres final-v4 | `sonification_features.py` | Musica deja de mapear EEG o WebUI pierde claves | Unit tests mapping + snapshot | Esencial runtime |
| Nombres de sonificacion | `SonificationFeatures.to_dict()` | WebUI, reports, captures offline | `alpha_drive`, `beta_gamma_drive`, `rms_beta_activity`, `band_driven_density`, `spectral_register`, `alpha_stability`, `rms_band_velocity`, `band_note_probability` | `sonification_features.py`, `assets/app.js`, tools | Reportes/UI incoherentes | Snapshot + docs/figures | Esencial TFG |
| Aliases legacy | Propiedades de `SonificationFeatures` | Codigo interno antiguo | `activity`, `calmness`, `tension`, etc. | `sonification_features.py`, `music_segment.py`, `backend_service.py` | Si se quitan sin migrar, se rompe musica | Busqueda + tests | Historico/compatibilidad |
| Music config | WebUI/backend | `MusicSegmentBuilder`, scale registry | `root_note`, `main_note`, `scale_key` | `web_server.py`, `backend_service.py`, `scale_registry.py` | Escala/nota invalida o UI desincronizada | HTTP smoke + snapshot `music.*` | Esencial operacion |
| MusicSegment | `MusicSegmentBuilder` | `BarGenerator`, `NoteGenerator` | Dataclass con escala, cadence, controles, main note | `music_segment.py` | Generacion bar/note falla | Tests live segment | Esencial runtime |
| Bar | `BarGenerator.generate_live_bar()` | `NoteGenerator.generate_notes_for_bar()` | chord root/pitches, note_positions, amplitudes | `music_bar.py` | Notas sin ritmo/acorde | Deterministic test | Esencial runtime |
| NoteEvent | `NoteGenerator.generate_notes_for_bar()` | `MidiScheduler`, `recent_notes`, captura musical | `t_start`, `t_end`, `pitch_midi`, `velocity`, `channel`, `program` | `music_note.py` | MIDI/piano roll/capturas musicales incorrectos | Test pitch/velocity/time | Esencial runtime |
| MidiLiveEvent | `midi_live` | `MidiByteTransport` | `due_time`, `event_type`, `channel`, `data1`, `data2` | `midi_live.py` | Bytes MIDI incorrectos | `event_to_midi_bytes` tests | Esencial runtime |
| MIDI scheduler | `MidiScheduler` | Backend `_pump_midi()` | heap de eventos + active notes | `midi_live.py`, `backend_service.py` | Jitter, notas colgadas | Tests schedule/panic | Esencial runtime |
| Panic MIDI | `MidiScheduler.panic()` + transport | WebUI `/midi/panic`, backend stop | CC120/CC123 por canales | `midi_live.py`, `web_server.py`, `backend_service.py` | Notas colgadas | Test POST + placa | Esencial seguridad |
| MIDI bytes | `MidiByteTransport` | firmware handler | `Bridge.call("midi_bytes", n, b0, b1, b2)` | `midi_byte_transport.py`, `sketch.ino` | MIDI fisico no suena o se corrompe | Mock + placa UART | Esencial runtime |
| UART MIDI fisica | firmware `midi_bytes()` | Sintetizador externo | `Serial1/D1`, 31250 baudios, TX invertido | `sketch.ino`, docs MIDI | Sin TXINV o UART distinta no suena | Test nota + panic | Esencial hardware |

## 4. Contratos WebUI y snapshot

| Contrato | Productor | Consumidor | Formato | Archivo fuente | Riesgo si cambia | Validacion necesaria | Clasificacion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Runtime snapshot | `BackendService._build_snapshot()` | `web_server.py`, `assets/app.js`, disk, tools | Dict con `config/status/rx/features/diagnostics/spectral_quality/capture/sonification/music/midi/led_matrix/performance/errors` | `backend_service.py` | UI rota o tools sin datos | Snapshot schema | Esencial operacion |
| `snapshot.json` | `app_state.atomic_write_json` desde backend | `web_server.get_latest` fallback, tools | JSON atomico con `published_at_unix` | `app_state.py`, `backend_service.py` | UI lee parcial/viejo | Atomic write/read smoke | Esencial operacion |
| `/latest` | `web_server.py` | `assets/app.js`, navegador | snapshot JSON | `web_server.py` | UI sin datos | HTTP smoke | Esencial WebUI |
| `/status` | `web_server.py` | Health/debug | `{ok,state,window_ready}` | `web_server.py` | Bajo | HTTP smoke | Esencial simple |
| Socket `eeg_snapshot` | `web_server.publish_snapshot()` | `assets/app.js` | snapshot dict | `web_server.py`, `main.py` | UI live no actualiza | Browser/socket smoke | Esencial WebUI |
| Polling fallback | `assets/app.js` | navegador | GET `/latest` cada 400 ms | `assets/app.js` | UI sin fallback si socket falla | Browser smoke | Lateral/robustez |
| WebUI music controls | `assets/app.js` | `web_server.py`, backend | `/music/config` o rutas `/music/scale`, `/music/root`, `/music/main` | `assets/app.js`, `web_server.py` | Config parcial/desincronizada | Cambiar root/main/scale en navegador | Esencial operacion |
| WebUI panic | `assets/app.js` | `web_server.py`, backend | POST `/midi/panic` | `assets/app.js`, `web_server.py` | Notas colgadas | Click panic + placa | Esencial seguridad |
| Piano roll | Backend `music.recent_notes` | `assets/app.js`, LED opcional | Lista de notas con `abs_start`, `abs_end`, `pitch_midi`, `velocity`, `note_name` | `backend_service.py`, `assets/app.js` | UI no muestra musica generada | Browser smoke | Esencial visual TFG |
| Fallback legacy UI | `controlValue()` | WebUI | nombres nuevos + alias legacy | `assets/app.js` | Confusion en final-v4 si se mantiene visible | Confirmar snapshots nuevos antes de quitar | Historico/compatibilidad |

Regla WebUI: simplificar con mucho cuidado, porque `assets/app.js` concentra el contrato de snapshot. Para UML, la WebUI debe verse como observador y control musical ligero, no como parte del DSP ni del firmware.

## 5. Contratos de captura y datos guardados

| Contrato | Productor | Consumidor | Formato | Archivo fuente | Riesgo si cambia | Validacion necesaria | Clasificacion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `capture_request.json` | `capture_eeg_quality.py` | `CaptureManager.poll_request()` | `command`, `request_id`, `condition`, `duration_sec`, `notes` | tool + `capture_manager.py` | Capturas no empiezan/paran | CLI con app viva | Lateral runtime |
| `capture_status.json` | `CaptureManager` | `capture_eeg_quality.py`, snapshot, `final_capture_session.py` | `state`, `request_id`, counters, `capture_dir`, elapsed | `capture_manager.py` | CLI espera mal o sesion no localiza captura | Captura temporal | Lateral runtime |
| CSV EEG | `CaptureManager.add_block()` | Tools offline, reportes, benchmarks | `t_capture_sec`, `timestamp_unix`, `block_idx`, `sample_idx`, `sample_in_block`, `status`, `ch1_uV..ch4_uV` | `capture_manager.py` | Tools fallan o analizan mal | Captura corta + analyzers | Trazabilidad TFG |
| `metadata.json` | `CaptureManager.finish()` | Tools docs/analyze | JSON con fs, num_channels, block_samples, ADS metadata, rx_summary, git, notes | `capture_manager.py` | Reports pierden trazabilidad | Schema smoke | Trazabilidad TFG |
| `music_snapshots.jsonl` | `final_capture_session.py` | Extraccion notas/reportajes | JSONL periodico con snapshot musical | `final_capture_session.py` | No se puede reconstruir sonificacion capturada | Captura final corta | Trazabilidad TFG |
| `music_notes.csv` | `final_capture_session.py` | Figuras/reportajes | Tabla deduplicada de notas con tiempos de captura | `final_capture_session.py` | Piano roll offline/figuras fallan | Comparar con snapshot | Trazabilidad TFG |
| `music_capture_summary.json` | `final_capture_session.py` | Reportajes | Resumen de snapshots/notas | `final_capture_session.py` | Reportaje pierde resumen musical | Captura corta | Trazabilidad TFG |
| `windowed_bandpowers.csv` | `validate_spectral_features.py` | Figuras/reportajes | Bandpowers por ventana | tools offline | Figuras de bandas rotas | Recalcular captura real | Trazabilidad TFG |
| `windowed_sonification_features.csv` | `validate_spectral_features.py` | Figuras/reportajes | Controles final-v4 + quality por ventana | tools offline | Figuras controles rotas | Recalcular captura real | Trazabilidad TFG |
| `psd_multitaper.csv` | `validate_spectral_features.py` | Figuras/reportes | PSD multitaper | tools offline | Espectro offline roto | Recalcular captura real | Trazabilidad TFG |

Aclaracion importante: `capture_eeg_quality.py` no calcula quality gate ni captura directamente. Solo solicita captura. El quality gate vive en el backend runtime y en tools offline como recalculo de validacion.

## 6. Contratos de benchmarks

| Contrato | Productor | Consumidor | Formato | Archivo fuente | Riesgo si cambia | Validacion necesaria | Clasificacion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Monitor `[BENCH] EEG_MIDI` | firmware `reportBenchStatsIfDue()` | `parse_mcu_bench_monitor.py` | Bloques de texto con `rate`, `time`, `queue`, `jitter`, `DRDY`, `total`, `peak` | `bench.h`, `sketch.ino`, parser | Parser no encuentra metricas o interpreta mal | Parsear log final versionado | Trazabilidad benchmark |
| Resultados MCU CSV/JSON/MD | `parse_mcu_bench_monitor.py` | Docs validacion | CSV/JSON/Markdown | parser | Benchmarks no reproducibles | Comparar con docs final-v4 | Trazabilidad benchmark |
| Benchmark Python sobre captura real | `benchmark_real_capture.py` | Docs validacion | JSON/CSV/MD | `benchmarks/` | Resultados no comparables | Ejecutar sobre captura real final | Trazabilidad benchmark |
| Benchmark run all | `run_all_benchmarks.py` | results/reports | Artefactos de benchmark | `benchmarks/` | Se mide otra captura/config | Guardar condicion/captura | Trazabilidad benchmark |

Decision final-v4:

```text
No enviar metricas MCU por Bridge.
Parsear Monitor offline.
```

Este contrato evita contaminar `Bridge.notify("eeg_block_uV")` con trafico adicional.

## 7. Contratos laterales LED

| Contrato | Productor | Consumidor | Formato | Archivo fuente | Riesgo si cambia | Validacion necesaria | Clasificacion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LED frame `rows` | `build_led_matrix_frame()` | `LedMatrixTransport` | `rows[height][width]`, ints 0..7 | `led_matrix_visualizer.py` | LED transporte falla | `test_led_matrix_visualizer.py` | Lateral opcional |
| `led_matrix_row` | `LedMatrixTransport` | firmware handler | `row_idx`, 3 chunks positivos 16/16/7 bits | `led_matrix_transport.py`, `sketch.ino` | Pixel mapping roto o Bridge cargado | Bit-exact + placa | Lateral opcional |
| LED enabled flags | Env + firmware macro | backend/firmware | `EEG_LED_MATRIX_ENABLED`, `LED_MATRIX_ENABLED` | `runtime_config.py`, `sketch.ino` | Python puede enviar a firmware que devuelve false | Smoke enabled/disabled | Lateral opcional |

Regla: LED no entra en el camino principal EEG->MIDI. Puede omitirse del UML principal.

## 8. Contratos App Lab y configuracion

| Contrato | Productor | Consumidor | Formato | Archivo fuente | Riesgo si cambia | Validacion necesaria | Clasificacion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| App Lab config | `app.yaml`, `sketch.yaml` | Arduino App Lab build/run | plataforma/librerias | config files | Build roto | Build en placa/App Lab | Esencial entorno |
| Local libs ADS | `sketch/ADS1299Plus`, `sketch/ADS1299_SafeSPI` | build firmware | `library.properties`, headers/cpp | sketch libs | Build o ADS roto | Compilar + ID | Esencial firmware |
| Runtime state dir | `runtime_config.runtime_state_dir()` | app_state, capture tools | `state/` o config equivalente | `runtime_config.py` | Tools/backend no se encuentran | Smoke capture/latest | Esencial operacion |
| Python deps | App Lab/venv | DSP/tools | SciPy, NumPy, Matplotlib para tools | entorno | DSP/tools fallan | py_compile/import smoke | Esencial entorno |

## 9. Contratos resueltos en final-v4

- MIDI UART fisico validado por `Serial1`/D1 con `MIDI_UART_ENABLED=1` y TX invertido obligatorio.
- `midi_bytes` existe en firmware y `MidiByteTransport` esta activo por defecto.
- Controles musicales WebUI runtime disponibles: `root`, `main` y `scale`.
- Nombres reportables de sonificacion final-v4 integrados en snapshot, reports y figuras.
- Benchmarks reales MCU se conservan por Monitor, no por Bridge adicional.
- Benchmarks Python/Linux se ejecutan sobre captura real.
- Capturas finales conservan EEG, metadata, quality reports, features, sonificacion y notas musicales.
- LED matrix queda documentada como modulo lateral desactivado por defecto.
- `ADS_DIAGNOSTIC_MODE=5 / bias_ch1_only_loff_off` queda como modo final de capturas comparables.

## 10. Contratos no resueltos a proposito

No son errores; son decisiones de alcance:

- Persistencia de configuracion musical entre reinicios.
- Control WebUI para habilitar/deshabilitar MIDI/LED.
- Control WebUI para cambiar ADS/filtros/firmware.
- Panic autonomo en firmware si Python/App Lab cae.
- Eliminacion de aliases legacy de sonificacion.
- Eliminacion de wrappers secundarios (`generate_bars`, `generate_notes_for_segment`, `compute_online_features`, `eeg_frame_uV`).
- Limpieza de comentarios historicos en WebUI/MIDI/firmware.

Estos puntos deben abordarse solo en una rama futura de simplificacion, con pruebas.

## 11. Recomendacion para version esencial UML

Contratos que deben aparecer en UML principal:

```text
eeg_block_uV
EEGReceiver -> EEGSignalProcessor -> DSPCore
SignalQuality / QualityGate
SonificationFeatureAdapter -> MusicSegmentBuilder -> BarGenerator -> NoteGenerator
MidiScheduler -> MidiByteTransport -> midi_bytes -> Serial1/D1 TXINV
EEGWebServer como observador/control musical ligero
/midi/panic
/music/config
```

Contratos que deben aparecer solo como laterales:

```text
CaptureManager + capture_request/status
Tools offline
Benchmarks
LED matrix
MIDI test endpoints
Polling fallback
Reports/figures generation
```

Contratos que deben ocultarse o marcarse como compatibilidad:

```text
eeg_frame_uV
generate_bars
generate_notes_for_segment
compute_online_features
legacy aliases de sonificacion
comentarios historicos de transporte MIDI
```

Regla final:

```text
La version esencial debe explicar el funcionamiento validado.
No debe borrar trazabilidad de validacion.
No debe cambiar contratos hardware/Bridge sin prueba en placa.
```





