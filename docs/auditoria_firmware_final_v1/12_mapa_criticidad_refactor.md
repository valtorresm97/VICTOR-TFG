# 12. Mapa de criticidad para refactor

| Archivo/funcion | Criticidad | Por que | Tests necesarios antes de tocar |
| --- | --- | --- | --- |
| `sketch/sketch.ino::loop` | CRITICO NO TOCAR sin prueba | Ruta tiempo real ADS/Bridge/filtros. | Bench gen/s, sent/s, pending, Monitor, captura real. |
| `sketch/sketch.ino::setup` | CRITICO NO TOCAR sin prueba | Inicializa ADS/Bridge/handlers/pines. | ID 0x3C, RDATAC, handlers registrados. |
| `sketch/sketch.ino::onDrdyFalling` | CRITICO NO TOCAR sin prueba | ISR de adquisicion. | DRDY 250 Hz, sin bloqueo ISR. |
| `sketch/sketch.ino::applyAdsDiagnosticMode` | CRITICO PERO REFACTORIZABLE con tests | Config analogica ADS. | Capturas modo 0/1/2/5, registros leidos si se agrega readback. |
| `ADS1299Plus::readFrameRDATAC` | CRITICO NO TOCAR sin prueba | Lectura frame 15 bytes y status. | Test signal interno, status 0xC00000, sample rate. |
| `ADS1299Plus::unpack24` | CRITICO NO TOCAR sin prueba | Sign extension signed 24-bit. | Tests con positivos/negativos extremos. |
| `ADS1299_Registers.h` defaults | CRITICO NO TOCAR sin prueba | Registros ADS. | Readback ADS, shorted/test/real. |
| `ADS1299_SafeSPI::begin` | CRITICO NO TOCAR sin prueba | SPI mode/frecuencia. | ID ADS y frames validos. |
| `filters.h` | CRITICO PERO REFACTORIZABLE con tests | Cambia espectro. | Test sintetico, captura comparativa, PSD. |
| `streaming.h::publishPendingBlocks` | CRITICO NO TOCAR sin prueba | Contrato Bridge payload. | Receiver unit test, captura real sin malformed. |
| `receiver.py::eeg_block_uV` | CRITICO NO TOCAR sin prueba | Parseo y validacion de bloques. | Tests payload valido/malformed/status/gaps. |
| `receiver.py::drain_blocks_to_processor` | CRITICO PERO REFACTORIZABLE con tests | Acopla RX a buffer/captura. | Tests cola/drops/capture sink. |
| `eeg_signal_processor.py` | CRITICO PERO REFACTORIZABLE con tests | Buffer y unidades uV->V. | Tests ring buffer, unidades, ventana. |
| `dsp_core.py` | CRITICO PERO REFACTORIZABLE con tests | Features EEG y PSD. | Tests senal sintetica, bandpowers, multitaper. |
| `spectral_quality.py` | CRITICO PERO REFACTORIZABLE con tests | Gate contra artefactos. | Tests score por escenarios y capturas offline. |
| `sonification_features.py` | CRITICO PERO REFACTORIZABLE con tests | Controles musicales live. | Golden outputs con features ejemplo. |
| `music_segment.py`, `music_bar.py`, `music_note.py` | CRITICO PERO REFACTORIZABLE con tests | Generacion musical/piano roll/MIDI. | Tests notas por compas, rangos, histeresis. |
| `midi_live.py` | CRITICO PERO REFACTORIZABLE con tests | Scheduler, active notes, panic y bytes. | Tests event ordering, bytes, panic. |
| `midi_byte_transport.py` | CRITICO PERO REFACTORIZABLE con tests | Bridge MIDI fisico. | Mock Bridge y prueba placa. |
| `led_matrix_visualizer.py` | CRITICO PERO REFACTORIZABLE con tests | Mapeo visual LED. | `test_led_matrix_visualizer.py`, casos duration/saturate. |
| `led_matrix_transport.py` | NO CRITICO hasta habilitar LED | Disabled por defecto, pero usa Bridge. | Mock Bridge, frame 104 bytes. |
| `backend_service.py` | CRITICO PERO REFACTORIZABLE con tests | Orquestador global. | Tests con fake receiver/proc, snapshot schema. |
| `web_server.py` | NO CRITICO | Presentacion/transporte UI. | Smoke UI `/latest`. |
| `assets/app.js` | NO CRITICO | Render UI. | Snapshot fixture + navegador. |
| `capture_manager.py` | CRITICO PERO REFACTORIZABLE con tests | Trazabilidad de capturas. | Tests start/add/finish metadata/gaps. |
| `python/tools/*.py` | TOOL OFFLINE | No afecta live salvo `set_ads_diagnostic_mode.py`. | py_compile y ejecucion con capturas fixture. |
| `docs/validacion_tfg/*` | DOCUMENTACION | Evidencia TFG. | Revision manual. |
| `captures/*` | DATOS/REPORTS | Datos experimentales. | No modificar salvo regeneracion controlada. |
