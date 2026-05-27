# 00. Inventario actual post-redundancias

Rama auditada originalmente: `eliminacion-redudancias`.
Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Alcance: codigo y artefactos relevantes de la aplicacion EEG-MIDI despues de eliminar redundancias y tras la validacion MIDI fisica final. Los controles WebUI/MIDI ya no son una deuda general: existen controles acotados para root, main note y escala.

| Archivo | Bloque | Rol | Critico | Tipo | Observaciones |
| --- | --- | --- | --- | --- | --- |
| `app.yaml` | Configuracion App Lab | Perfil principal de Arduino App Lab | Si | Config | Debe conservar `arduino:zephyr` y librerias locales ADS1299. |
| `README.md` | Documentacion | Resumen de proyecto | No | Doc | Punto de entrada humano. |
| `AGENTS.md` | Documentacion | Reglas tecnicas del agente | Si | Doc | Define contratos de pines, streaming y prioridades. |
| `sketch/sketch.ino` | Firmware MCU | Loop real-time ADS1299, Bridge, MIDI y LED handlers | Si | C++ | Archivo mas delicado de firmware. |
| `sketch/streaming.h` | Streaming/Bridge | Ring de bloques y `Bridge.notify("eeg_block_uV")` | Si | C++ header | Contrato MCU->Python. |
| `sketch/filters.h` | Firmware MCU | DC blocker, notch 50 Hz, low-pass 40 Hz, conversion uV | Si | C++ header | Afecta escala y contenido espectral recibido. |
| `sketch/bench.h` | Benchmarks | Contadores de rendimiento MCU | Medio | C++ header | Observabilidad; no debe alterar payload. |
| `sketch/synthetic.h` | Benchmarks y modos sinteticos | Generador EEG-like sin ADS1299 | Medio | C++ header | Util para validar Bridge/DSP sin hardware analogico. |
| `sketch/sketch.yaml` | Configuracion App Lab | Librerias firmware | Si | YAML | NeoPixel retirado; conserva `Arduino_LED_Matrix`. |
| `sketch/ADS1299Plus/src/ADS1299Plus.h` | Driver ADS1299 | API alto nivel ADS1299 | Si | C++ header | Define `NUM_CHANNELS=4`, frame 15 bytes y `unpack24`. |
| `sketch/ADS1299Plus/src/ADS1299Plus.cpp` | Driver ADS1299 | Implementa comandos, registros y lectura RDATAC | Si | C++ | Critico para SPI/DRDY/status. |
| `sketch/ADS1299Plus/src/ADS1299_Registers.h` | Driver ADS1299 | Mapa de registros, comandos y mascaras | Si | C++ header | Cambios requieren datasheet y prueba en placa. |
| `sketch/ADS1299Plus/library.properties` | Configuracion App Lab | Libreria local ADS1299Plus | Medio | Config | Mantener local. |
| `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.h` | SPI seguro | API wrapper SPI | Si | C++ header | Encapsula CS/SPI. |
| `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.cpp` | SPI seguro | SPI MODE1, MSBFIRST, 2 MHz | Si | C++ | No cambiar modo/velocidad sin validar ADS1299. |
| `sketch/ADS1299_SafeSPI/library.properties` | Configuracion App Lab | Libreria local SafeSPI | Medio | Config | Mantener local. |
| `python/main.py` | Backend Python | Arranque App Lab, backend y WebUI | Si | Python | Loop central de 20 ms. |
| `python/backend_service.py` | Backend Python | Orquestacion RX, DSP, sonificacion, MIDI, LED, snapshot | Si | Python | Archivo con mayor responsabilidad en Linux. |
| `python/receiver.py` | Receiver | Callback Bridge `eeg_block_uV`, cola y metricas | Si | Python | Critico para contrato y perdidas. |
| `python/eeg_contract.py` | Streaming/Bridge | Constantes y parser Python del payload EEG | Si | Python | Fuente Python compartida post-redundancias. |
| `python/eeg_signal_processor.py` | EEG signal processor | Ring buffer multicanal y acceso a DSP | Si | Python | Contrato uV->V. |
| `python/dsp_core.py` | DSP | PSD, multitaper, bandpowers y features | Si | Python | Fuente unica de multitaper live/offline. |
| `python/spectral_quality.py` | DSP | Score/gate de calidad espectral | Si | Python | Controla si sonificacion se considera valida. |
| `python/sonification_features.py` | Sonificacion | Features DSP -> controles musicales | Si | Python | No calcula DSP; aplica EMA y quality gate. |
| `python/music_segment.py` | Generacion musical | Estado musical live desde sonificacion | Medio | Python | Escala, nota principal, cadencia. |
| `python/music_bar.py` | Generacion musical | Acordes, posiciones ritmicas y barras | Medio | Python | Usa RNG; requiere reproducibilidad. |
| `python/music_note.py` | Generacion musical | NoteEvent y generacion de notas | Medio | Python | Afecta densidad, pitch, velocity y duraciones. |
| `python/music_utils.py` | Generacion musical | Parseo nota musical -> MIDI | Bajo | Python | Utilidad compartida. |
| `python/scale_registry.py` | Generacion musical | Registro de escalas expuestas en WebUI | Bajo | Python | Incluye mayor, menor, blues, modos heptatonicos y pentatonicas. |
| `python/midi_live.py` | MIDI live | Eventos MIDI, scheduler, panic, bytes | Si | Python | Evita notas colgadas y define bytes MIDI. |
| `python/midi_byte_transport.py` | MIDI byte transport | `MidiLiveEvent` -> `Bridge.call("midi_bytes")` | Si | Python | Activo por defecto en final-v3; depende del handler firmware `midi_bytes`. |
| `python/led_matrix_visualizer.py` | LED matrix | `recent_notes` -> frame `rows` 13x8 | Medio | Python | `packed_points` legacy eliminado. |
| `python/led_matrix_transport.py` | LED matrix | `rows` -> chunks `led_matrix_row` | Medio | Python | Desactivado por defecto. |
| `python/app_state.py` | Estado runtime | JSON atomico snapshot/history | Si | Python | Helper `atomic_write_json` centralizado. |
| `python/runtime_config.py` | Configuracion App Lab | Env vars y defaults runtime | Medio | Python | Centraliza configuracion Python/LED/MIDI. |
| `python/capture_manager.py` | Capturas | Captura CSV incremental desde bloques EEG | Si | Python | Escribe `capture_status.json`, `metadata.json`, CSV. |
| `python/web_server.py` | Web server | WebUI Brick y endpoints | Medio | Python | Solo rutas y snapshots; no DSP pesado. |
| `assets/index.html` | Assets Web UI | Estructura dashboard y controles musicales acotados | Medio | HTML | Root/main/scale, panic y piano roll live. |
| `assets/app.js` | Assets Web UI | Render de snapshot, controles musicales, panic, piano roll | Medio | JS | Depende de nombres de claves del snapshot y endpoints WebUI. |
| `assets/styles.css` | Assets Web UI | Estilos dashboard | Bajo | CSS | No afecta backend. |
| `python/tools/analyze_eeg_capture.py` | Tools CLI | Analisis calidad de una captura | Medio | Python CLI | Usa `DSPCore`; genera reports. |
| `python/tools/capture_eeg_quality.py` | Tools CLI | Solicita captura a app App Lab en ejecucion | Medio | Python CLI | Escribe `capture_request.json`. |
| `python/tools/compare_eeg_captures.py` | Tools CLI | Compara ojos abiertos/cerrados | Bajo | Python CLI | Offline. |
| `python/tools/validate_spectral_features.py` | Tools CLI | Validacion ventana a ventana de features | Medio | Python CLI | Usa `DSPCore`, `SpectralQuality`, sonificacion. |
| `python/tools/build_validation_docs.py` | Tools CLI | Genera docs, tablas y figuras de validacion | Medio | Python CLI | Tool grande, offline, dependiente de matplotlib/scipy. |
| `python/tools/set_ads_diagnostic_mode.py` | Tools CLI | Cambia macro `ADS_DIAGNOSTIC_MODE` | Si | Python CLI | Modifica firmware; usar con cuidado. |
| `python/tools/test_led_matrix_visualizer.py` | Tests/validaciones | Test manual LED visualizer | Medio | Python test | Unico test ejecutable detectado. |
| `captures/**` | Capturas | CSV, metadata y reports reales | No | Datos | Evidencia de validacion; no tocar en refactor. |
| `docs/auditoria_firmware_final_v1/**` | Documentacion | Auditoria previa global | No | Doc | Base historica. |
| `docs/validacion_tfg/**` | Documentacion | Validacion TFG, tablas y figuras | No | Doc/datos | Resultado consolidado. |
| `docs/*.md` | Documentacion | Informes de captura, DSP, LED, registros | No | Doc | Varias piezas definitivas e historicas. |
