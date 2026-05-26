# Auditoria detallada de codigo

Rama auditada: `eliminacion-redudancias`.

Objetivo: documentar archivo por archivo y funcion por funcion la aplicacion EEG-MIDI despues de resolver redundancias principales. Esta auditoria no simplifica codigo, no cambia comportamiento y no reintroduce controles WebUI/MIDI.

## Alcance

Documentos generados:

1. `00_inventario_actual.md`: inventario post-redundancias.
2. `01_firmware_funcion_por_funcion.md`: firmware, streaming, filtros, bench y sintetico.
3. `02_ads1299_spi_driver.md`: driver ADS1299 y SPI.
4. `03_python_backend_funcion_por_funcion.md`: backend, receiver, contratos, estado, capturas y web server.
5. `04_dsp_eeg_funcion_por_funcion.md`: DSP, buffer EEG y quality score.
6. `05_sonificacion_midi_funcion_por_funcion.md`: sonificacion, musica, MIDI scheduler y transporte.
7. `06_led_matrix_funcion_por_funcion.md`: LED visualizer, transport y handler firmware.
8. `07_web_server_assets_funcion_por_funcion.md`: endpoints, HTML, JS y CSS.
9. `08_tools_cli_funcion_por_funcion.md`: tools offline y auxiliares.
10. `09_mapa_contratos_entre_modulos.md`: contratos productor/consumidor.
11. `10_mapa_funciones_criticas.md`: criticidad y pruebas minimas.
12. `11_hallazgos_para_simplificacion_futura.md`: hallazgos sin refactor.

## Estado post-redundancias

Resuelto:

- Constantes EEG y parser Python centralizados en `eeg_contract.py`.
- Multitaper live/offline centralizado en `DSPCore`.
- Quality score centralizado en `spectral_quality.py`.
- Config runtime Python centralizada en `runtime_config.py`.
- Captura CSV incremental.
- Escritura JSON atomica centralizada en `app_state.atomic_write_json`.
- NeoPixel no usado retirado.
- `packed_points` LED legacy eliminado.
- Controles musicales WebUI retirados por estabilidad.

Pendiente a proposito:

- Diseno futuro de controles WebUI/MIDI. No se ha reintroducido ningun endpoint ni UI de configuracion musical runtime.

## Arquitectura resumida

```text
ADS1299-4PAG
  -> SPI RDATAC 15 bytes
  -> MCU sketch.ino
  -> filtros MCU y uV
  -> Bridge.notify("eeg_block_uV")
  -> EEGReceiver
  -> EEGSignalProcessor
  -> DSPCore multitaper
  -> spectral_quality + sonification_features
  -> MusicSegment/Bar/NoteEvent
  -> MidiScheduler
  -> MidiByteTransport -> Bridge.call("midi_bytes")
  -> WebUI snapshot/piano roll
  -> LedMatrixTransport -> Bridge.call("led_matrix_row")
```

## Modulos mas criticos

- Firmware: `sketch.ino`, `streaming.h`, `ADS1299Plus.cpp`, `ADS1299_SafeSPI.cpp`.
- Python runtime: `receiver.py`, `backend_service.py`, `eeg_signal_processor.py`, `dsp_core.py`, `capture_manager.py`.
- Contratos: `eeg_contract.py`, snapshot de `backend_service.py`, `midi_live.py`, LED `rows`.
- UI: `assets/app.js` por dependencia fuerte de claves snapshot.

## Contratos principales

- `eeg_block_uV`: 3 campos de cabecera + 8 muestras * 5 campos.
- ADS1299 status: mascara `0xF00000`, valor `0xC00000`.
- CSV de captura: `sample_idx`, `status`, `ch1_uV..ch4_uV`.
- Snapshot: `config/status/rx/features/diagnostics/spectral_quality/capture/sonification/music/midi/led_matrix/performance/errors`.
- MIDI: `MidiLiveEvent` -> bytes MIDI -> `midi_bytes`.
- LED: `rows` -> chunks `led_matrix_row`.

## Pruebas imprescindibles antes de refactor

- Parser `eeg_block_uV` con payload valido/malformed.
- Snapshot schema consumido por `assets/app.js`.
- `DSPCore` con seno conocido y ruido.
- `compute_spectral_quality` con casos clean/bad/artifact.
- `MidiScheduler` y `event_to_midi_bytes`.
- LED visualizer y row packing.
- Placa: ADS ID, status, 250 Hz, 31.25 bloques/s, drops 0.

## Orden recomendado para simplificar

1. Tests de contrato.
2. Extraer snapshot builder puro desde `backend_service.py`.
3. Separar motor musical live de la orquestacion.
4. Validar UART MIDI fisico.
5. Redisenar controles WebUI/MIDI con endpoint y schema testeados.
6. Refactor offline tools grandes.
7. Tocar firmware solo con placa y benchmark antes/despues.
