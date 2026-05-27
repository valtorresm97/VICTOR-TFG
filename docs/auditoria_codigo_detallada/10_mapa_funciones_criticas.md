# 10. Mapa de funciones criticas

| Archivo | Funcion | Criticidad | Motivo | Prueba minima antes de tocar |
| --- | --- | --- | --- | --- |
| `sketch/sketch.ino` | `setup` | CRITICA NO TOCAR SIN HARDWARE | Inicializa ADS, Bridge, pines, handlers, RDATAC | Compilar + ADS ID 0x3C + status 0xC00000. |
| `sketch/sketch.ino` | `loop` | CRITICA NO TOCAR SIN HARDWARE | Tiempo real 250 Hz, filtros, streaming | Placa: gen/s 250, blk/s 31.25, drops 0. |
| `sketch/sketch.ino` | `onDrdyFalling` | CRITICA NO TOCAR SIN HARDWARE | ISR de adquisicion | Ver DRDY/pending/jitter. |
| `sketch/sketch.ino` | `applyAdsDiagnosticMode` | CRITICA NO TOCAR SIN HARDWARE | Configura BIAS, lead-off, canales | Captura por modo diagnostico. |
| `sketch/sketch.ino` | `midi_bytes` | CRITICA NO TOCAR SIN HARDWARE | Puente activo a UART MIDI fisica validada | Test UART D1/TX con TX invertido y panic. |
| `sketch/sketch.ino` | `led_matrix_row` | CRITICA CON TEST DE CONTRATO | Handler Bridge LED | Test packing + LED enabled. |
| `sketch/streaming.h` | `publishPendingBlocks` | CRITICA CON TEST DE CONTRATO | Emite payload manual `eeg_block_uV` | Parser test + placa receive. |
| `sketch/streaming.h` | `appendSampleToFillBlock` | CRITICA CON TEST DE CONTRATO | Agrupa 8 muestras | Test sample_count/indices. |
| `sketch/filters.h` | `DCBlocker.process`, `Biquad.process` | CRITICA DSP/CIENTIFICA | Modifica senal antes de Python | Respuesta frecuencia + captura. |
| `ADS1299Plus.cpp` | `begin`, `configureDefaults` | CRITICA NO TOCAR SIN HARDWARE | Configura chip real | ADS ID + registros. |
| `ADS1299Plus.cpp` | `readFrameRDATAC` | CRITICA NO TOCAR SIN HARDWARE | Lee 15 bytes y status | Status sync y sample rate. |
| `ADS1299Plus.h` | `unpack24` | CRITICA CON TEST DE CONTRATO | Sign-extension 24-bit | Test bordes 0x7FFFFF/0x800000. |
| `ADS1299_SafeSPI.cpp` | `begin/select/xfer/deselect` | CRITICA NO TOCAR SIN HARDWARE | SPI MODE1 2 MHz | ADS ID y RDATAC. |
| `python/eeg_contract.py` | `parse_eeg_block_values` | CRITICA CON TEST DE CONTRATO | Parser payload | Unit tests longitudes/shape. |
| `python/eeg_contract.py` | `is_valid_ads1299_status` | CRITICA CON TEST DE CONTRATO | Valida frames | Test status. |
| `python/receiver.py` | `eeg_block_uV` | CRITICA CON TEST DE CONTRATO | Callback Bridge principal | Simular payload + metrics. |
| `python/receiver.py` | `drain_blocks_to_processor` | CRITICA CON TEST DE CONTRATO | Entrega datos a DSP/captura | Test cola/backlog. |
| `python/eeg_signal_processor.py` | `add_block_uV` | CRITICA DSP/CIENTIFICA | Unidad uV->V y buffer | Test unidad/wrap. |
| `python/eeg_signal_processor.py` | `compute_live_features` | CRITICA DSP/CIENTIFICA | Ruta live dashboard/sonificacion | Seno/PSD features. |
| `python/dsp_core.py` | `compute_psd`, `_compute_psd_multitaper` | CRITICA DSP/CIENTIFICA | Fuente unica PSD | Test seno 10 Hz, compare offline. |
| `python/dsp_core.py` | `compute_features` | CRITICA DSP/CIENTIFICA | Bandpowers y picos | Test features schema. |
| `python/spectral_quality.py` | `compute_spectral_quality` | CRITICA DSP/CIENTIFICA | Gate de sonificacion | Test clean/bad/artifact. |
| `python/backend_service.py` | `__init__` | CRITICA CON TEST DE CONTRATO | Registra Bridge y construye pipeline | App Lab smoke. |
| `python/backend_service.py` | `step` | CRITICA CON TEST DE CONTRATO | Orquesta todo | Simular bloques + placa. |
| `python/backend_service.py` | `_build_snapshot` | CRITICA UI/SNAPSHOT | Contrato UI/disco | Snapshot schema + browser. |
| `python/backend_service.py` | `_maybe_generate_music` | CRITICA CON TEST DE CONTRATO | Genera notas/scheduler | Test features sinteticas. |
| `python/backend_service.py` | `_pump_midi`, `send_panic` | CRITICA CON TEST DE CONTRATO | MIDI seguridad | Scheduler/transport tests. |
| `python/capture_manager.py` | `add_block`, `finish` | CRITICA CON TEST DE CONTRATO | Capturas CSV/metadata | Temp capture test. |
| `python/app_state.py` | `atomic_write_json` | CRITICA UI/SNAPSHOT | Evita JSON parcial | Temp + NaN test. |
| `python/midi_live.py` | `event_to_midi_bytes`, `panic_events` | CRITICA CON TEST DE CONTRATO | Bytes y seguridad MIDI | Unit tests. |
| `python/midi_byte_transport.py` | `send_event` | CRITICA NO TOCAR SIN HARDWARE | Bridge a MCU para MIDI fisico | Mock + UART placa con TX invertido. |
| `python/led_matrix_transport.py` | `_pack_row`, `send_frame` | CRITICA CON TEST DE CONTRATO | Packing LED y Bridge calls | Bit-exact + test visualizer. |
| `python/led_matrix_visualizer.py` | `build_led_matrix_frame` | CRITICA UI/SNAPSHOT | Piano roll LED fisico | Test existente. |
| `python/web_server.py` | `_setup_routes`, `post_midi_panic` | CRITICA UI/SNAPSHOT | Endpoints UI | HTTP smoke. |
| `assets/app.js` | `renderSnapshot`, `renderPianoRoll`, `sendMidiPanic` | CRITICA UI/SNAPSHOT | Render depende de snapshot | Browser local/App Lab. |
| `python/tools/set_ads_diagnostic_mode.py` | `main` | CRITICA NO TOCAR SIN HARDWARE | Reescribe macro firmware | Diff antes/despues + compile. |
| `python/tools/build_validation_docs.py` | `build`, `generate_figures`, `generate_tables`, `generate_docs` | OFFLINE TOOL | Genera docs TFG | Ejecutar offline, revisar diffs. |
| `python/tools/analyze_eeg_capture.py` | `analyze` | OFFLINE TOOL | Reports calidad | Ejecutar sobre captura conocida. |
| `python/tools/validate_spectral_features.py` | `validate_capture` | OFFLINE TOOL | Reports features/sonificacion | Ejecutar sobre captura conocida. |

## Regla de refactor

Antes de tocar cualquier funcion marcada critica, crear o ejecutar al menos una prueba de contrato local y una validacion en placa si toca firmware, ADS, UART MIDI o timing de Bridge.
