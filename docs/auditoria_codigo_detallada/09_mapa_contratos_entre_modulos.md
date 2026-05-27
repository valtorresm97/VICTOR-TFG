# 09. Mapa de contratos entre modulos

| Contrato | Productor | Consumidor | Formato | Archivo fuente | Riesgo si cambia | Validacion necesaria |
| --- | --- | --- | --- | --- | --- | --- |
| `eeg_block_uV` | MCU `TxBlockRing.publishPendingBlocks` | `EEGReceiver.eeg_block_uV` | `block_idx`, `first_sample_idx`, `sample_count`, 8*(status+ch1..ch4) | `streaming.h`, `eeg_contract.py` | Rompe recepcion, capturas y DSP | Test parser + placa recibe 31.25 blk/s. |
| Constantes EEG | Firmware y `eeg_contract.py` | Receiver, DSP, capture, tools | `FS_HZ=250`, `NUM_CH=4`, `BLOCK_SAMPLES=8`, `LSB_V=2.235e-8` | `sketch.ino`, `streaming.h`, `eeg_contract.py` | Escala/ventana/shape incorrecta | Contract test + captura. |
| ADS1299 status | ADS1299 frame | Firmware/Python receiver | `(status & 0xF00000)==0xC00000` | `ADS1299_Registers.h`, `eeg_contract.py` | Datos corruptos aceptados/rechazados | Test status valid/invalid. |
| Frame ADS1299 | ADS1299 RDATAC | `ADS1299Plus.readFrameRDATAC` | 15 bytes: 3 status + 4*3 ch | `ADS1299Plus.h/cpp` | Desalineacion SPI | Hardware ID/status. |
| uV capture row | `CaptureManager.add_block` | Tools offline | CSV columns `t_capture_sec,timestamp_unix,block_idx,sample_idx,sample_in_block,status,ch1_uV..ch4_uV` | `capture_manager.py` | Tools fallan o analizan mal | Test temp capture + tools. |
| `metadata.json` | `CaptureManager.finish` | Tools docs/analyze | JSON con fs, num_channels, block_samples, ADS metadata, rx_summary, git | `capture_manager.py` | Reports pierden trazabilidad | Schema smoke. |
| `capture_request.json` | `capture_eeg_quality.py` | `CaptureManager.poll_request` | `command`, `request_id`, `condition`, `duration_sec`, `notes` | tool + capture manager | Capturas no empiezan/paran | CLI con app viva. |
| `capture_status.json` | `CaptureManager` | `capture_eeg_quality.py`, snapshot | JSON `state`, `request_id`, counters, `capture_dir` | `capture_manager.py` | CLI espera mal | Temp status test. |
| Runtime snapshot | `BackendService._build_snapshot` | `web_server.py`, `assets/app.js`, disk | Dict con `config/status/rx/features/diagnostics/spectral_quality/capture/sonification/music/midi/led_matrix/performance/errors` | `backend_service.py` | UI rota | Snapshot schema. |
| `snapshot.json` | `app_state.publish_snapshot` | `web_server.get_latest` fallback | JSON atomico con `published_at_unix` | `app_state.py` | UI lee parcial/viejo | Atomic write test. |
| `history.json` | `app_state.publish_history` | Futuro UI/tools | JSON atomico `{published_at_unix, history}` | `app_state.py` | Bajo, poco usado | Read/write smoke. |
| `SonificationFeatures` | `SonificationFeatureAdapter` | `MusicSegmentBuilder`, snapshot | Dataclass normalizada | `sonification_features.py` | Musica deja de mapear EEG | Unit tests mappings. |
| `MusicSegment` | `MusicSegmentBuilder` | `BarGenerator`, `NoteGenerator` | Dataclass con escala, cadence, controles | `music_segment.py` | Generacion bar/note falla | Tests live segment. |
| `Bar` | `BarGenerator` | `NoteGenerator` | Chord root/pitches, note positions, amplitudes | `music_bar.py` | Notas sin ritmo/acorde | Deterministic test. |
| `NoteEvent` | `NoteGenerator` | `MidiScheduler`, recent_notes | t_start,t_end,pitch,velocity,channel,program | `music_note.py` | MIDI/piano roll incorrectos | Test pitch/velocity/time. |
| `MidiLiveEvent` | `midi_live` | `MidiByteTransport` | due_time,type,channel,data1,data2 | `midi_live.py` | Bytes MIDI incorrectos | event_to_midi_bytes tests. |
| `midi_bytes` | `MidiByteTransport` | firmware handler | `Bridge.call("midi_bytes", n,b0,b1,b2)` | `midi_byte_transport.py`, `sketch.ino` | MIDI fisico no suena o bloquea | Mock + placa UART. |
| Music config WebUI | `assets/app.js`, `web_server.py` | `BackendService.update_music_config` | `root_note`, `main_note`, `scale_key`; endpoints `/music/config`, `/music/scale/{key}`, `/music/root/{note}`, `/music/main/{note}` | `web_server.py`, `backend_service.py`, `scale_registry.py` | Escala/nota invalida o UI desincronizada | HTTP smoke + snapshot `music.*`. |
| LED frame `rows` | `build_led_matrix_frame` | `LedMatrixTransport` | `rows[height][width]` ints 0..7 | `led_matrix_visualizer.py` | LED transporte falla | `test_led_matrix_visualizer.py`. |
| `led_matrix_row` | `LedMatrixTransport` | firmware handler | row_idx, 3 chunks positivos 16/16/7 bits | `led_matrix_transport.py`, `sketch.ino` | Pixel mapping roto | Bit-exact test + placa. |
| `/latest` | `web_server.py` | `assets/app.js` | snapshot JSON | `web_server.py` | UI sin datos | HTTP smoke. |
| `/status` | `web_server.py` | Health/debug | `{ok,state,window_ready}` | `web_server.py` | Bajo | HTTP smoke. |
| `/midi/panic` | `web_server.py` | Boton UI | POST -> `{ok,sent_events}` | `web_server.py` | Notas colgadas si falla | Test POST. |
| Socket `eeg_snapshot` | `web_server.publish_snapshot` | `assets/app.js` | snapshot dict | `web_server.py` | UI live no actualiza | Browser/socket smoke. |
| App Lab config | `app.yaml`, `sketch.yaml` | Arduino App Lab build/run | plataforma/librerias | config files | Build roto | Build en placa/App Lab. |

## Contratos resueltos en final-v3

- Controles musicales WebUI runtime: reintroducidos de forma acotada para root/main/scale; falta prueba automatica de endpoints y snapshot.
- MIDI UART fisico: validado en `Serial1`/D1 con `MIDI_UART_ENABLED=1` por defecto y TX invertido obligatorio (`USART_CR2_TXINV`).

## Contratos aun no resueltos a proposito

- Persistencia de configuracion musical entre reinicios.
- Control WebUI para habilitar/deshabilitar MIDI/LED.
- Panic autonomo en firmware si Python/App Lab cae.
