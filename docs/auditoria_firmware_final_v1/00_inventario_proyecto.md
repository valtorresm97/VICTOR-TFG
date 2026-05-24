# 00. Inventario del proyecto

Rama de auditoria creada: `firmware-final-v1`.

Base real usada en este checkout: `matrixz-scroll`. La rama solicitada como `matrix-scroll` no existe local ni remota en este repositorio; la rama activa contenia los commits de scroll LED/matriz (`Add LED matrix piano scroll`, `Optimize LED matrix runtime cost`).

Inventario levantado con `rg --files` y clasificado por bloque funcional. Las capturas y figuras repetitivas se agrupan por familia para mantener el documento legible; los directorios de captura existentes se enumeran explicitamente.

| Archivo | Bloque | Descripcion breve | Critico | Observaciones |
| --- | --- | --- | --- | --- |
| `AGENTS.md` | Documentacion | Reglas persistentes del proyecto, arquitectura, pines, contratos y validacion esperada. | Si | Fuente normativa principal para futuros prompts. |
| `README.md` | Documentacion | Resumen raiz y enlaces principales. | No | Muy breve; apunta a LED matrix. |
| `app.yaml` | Configuracion App Lab | Define app `EEG_MIDI`, brick web UI e icono. | Si | No contiene dependencias firmware; eso vive en `sketch/sketch.yaml`. |
| `sketch/sketch.yaml` | Configuracion App Lab | Perfil `arduino:zephyr`, RouterBridge, LED Matrix, librerias ADS locales. | Si | Mantiene `dir: ADS1299Plus` y `dir: ADS1299_SafeSPI`. |
| `sketch/sketch.ino` | Firmware / MCU | Firmware principal: ADS1299, DRDY, filtros, streaming, handlers MIDI/LED, bench. | Si | Archivo mas critico de tiempo real. |
| `sketch/bench.h` | Firmware / benchmarks | Estructura de metricas de adquisicion, filtros, notify, cola y jitter. | Si | No cambia payload EEG. |
| `sketch/filters.h` | Firmware / filtros | DC blocker, notch 50 Hz, low-pass 40 Hz y conversion V a microvoltios. | Si | Afecta directamente a senal y features. |
| `sketch/streaming.h` | Firmware / Bridge | Define `EegBlockUV`, ring TX y `Bridge.notify("eeg_block_uV", ...)`. | Si | Contrato MCU-Python. No cambiar sin `receiver.py`. |
| `sketch/synthetic.h` | Firmware / diagnostico | Generador EEG-like sintetico para validar filtros/Bridge/Python sin ADS real. | Medio | `USE_SYNTHETIC=0` por defecto. |
| `sketch/ADS1299Plus/library.properties` | ADS1299 / libreria local | Manifest local del driver ADS1299Plus. | Medio | Debe seguir siendo libreria local. |
| `sketch/ADS1299Plus/src/ADS1299Plus.h` | ADS1299 / driver | API alto nivel, constantes 4 canales, unpack 24-bit, status sync. | Si | `NUM_CHANNELS=4`, frame 15 bytes. |
| `sketch/ADS1299Plus/src/ADS1299Plus.cpp` | ADS1299 / driver | Power-up, comandos SPI, registros, configuracion, RDATAC/RDATA. | Si | Valida ID ADS1299-4 y status sync. |
| `sketch/ADS1299Plus/src/ADS1299_Registers.h` | ADS1299 / registros | Mapa de registros, comandos, mascaras, defaults CONFIG/CH/LOFF. | Si | Cambios aqui pueden romper adquisicion. |
| `sketch/ADS1299_SafeSPI/library.properties` | SPI / libreria local | Manifest local del wrapper SPI. | Medio | Debe seguir local. |
| `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.h` | SPI / wrapper | API de SPI seguro, CS, transfer y waitDecode. | Si | Contrato de bajo nivel ADS1299. |
| `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.cpp` | SPI / wrapper | `SPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE1))`. | Si | 2 MHz, MSB first, SPI_MODE1. |
| `python/main.py` | Python backend | Punto de entrada App Lab: crea backend, WebUI y `App.run`. | Si | Loop con `sleep(0.02)`. |
| `python/backend_service.py` | Python backend | Orquestador: receiver, DSP, quality, sonificacion, MIDI, LED, snapshot. | Si | Centro del pipeline Linux/Python. |
| `python/receiver.py` | Python backend | Handler `eeg_block_uV`, validacion de bloques/status/indices y colas. | Si | Contrato directo con `streaming.h`. |
| `python/eeg_signal_processor.py` | DSP y buffers | Ring buffer multicanal, ingestion uV->V, ventanas y features live. | Si | No aplica filtros EEG adicionales. |
| `python/dsp_core.py` | DSP y features | PSD periodogram/Welch/multitaper, bandpowers, picos, spectrogram. | Si | Depende de NumPy/SciPy. |
| `python/spectral_quality.py` | DSP / quality gate | Calcula `score`, estado y `gate_factor` de calidad espectral. | Si | Protege sonificacion frente a artefactos. |
| `python/sonification_features.py` | Sonificacion | Convierte features DSP en controles musicales suavizados y con gate. | Si | No calcula DSP. |
| `python/music_utils.py` | Sonificacion | Conversor de nombre de nota a MIDI. | Medio | Usado por escala/main note. |
| `python/scale_registry.py` | Sonificacion | Registro de escalas y construccion de `ScaleConfig`. | Medio | Config musical fija actual. |
| `python/music_segment.py` | Sonificacion | `LiveSegment`, `ScaleConfig`, `MusicSegment`, cadencia e histeresis. | Si | Entrada a bar generator. |
| `python/music_bar.py` | Sonificacion | Genera compas, acorde y slots ritmicos desde controles EEG. | Si | Modula densidad/tension/estabilidad. |
| `python/music_note.py` | Sonificacion / MIDI | Convierte compas en `NoteEvent` con pitch, velocity y duracion. | Si | Alimenta scheduler y piano roll. |
| `python/midi_live.py` | MIDI live | `MidiLiveEvent`, scheduler, program/CC/note on/off, panic y bytes MIDI. | Si | Panic existe en Python. |
| `python/midi_byte_transport.py` | MIDI transporte | Envia bytes por `Bridge.call("midi_bytes", n,b0,b1,b2)`. | Si | Desactivado por defecto por env. |
| `python/led_matrix_visualizer.py` | LED matrix | Config por env y conversion `recent_notes` a frame 13x8 row-major. | Si | Misma fuente que piano roll web. |
| `python/led_matrix_transport.py` | LED matrix transporte | Envia frame LED por `Bridge.call("led_matrix_frame", payload)`. | Medio | Desactivado por defecto. |
| `python/capture_manager.py` | Capturas | Gestiona solicitudes `state/capture_request.json` y guarda CSV/metadata. | Si | Vive dentro de App Lab. |
| `python/app_state.py` | Estado / snapshot | Publica/lee `state/snapshot.json` con escritura atomica. | Medio | UI puede leer fallback desde disco. |
| `python/web_server.py` | Web UI | WebUI brick, rutas `/status` y `/latest`, websocket `eeg_snapshot`. | Medio | Sustituye a `dashboard.py`; no hay Streamlit. |
| `python/requirements.txt` | Python config | Dependencias: `numpy`, `scipy`. | Medio | App Lab aporta modulos `arduino.*`. |
| `assets/index.html` | Web UI | Dashboard HTML: adquisicion, features, calidad, sonificacion, MIDI, piano roll. | Medio | Depende de claves snapshot. |
| `assets/app.js` | Web UI | Render de snapshots, bandas, waveform, warnings, sonificacion y piano roll. | Medio | Fragil ante cambios de nombres de snapshot. |
| `assets/styles.css` | Web UI | Estilos visuales del dashboard. | No | No afecta pipeline. |
| `python/tools/capture_eeg_quality.py` | Tools CLI | Solicita captura real a la app mediante JSON de estado. | Medio | Requiere app corriendo. |
| `python/tools/analyze_eeg_capture.py` | Tools CLI / offline | Analiza CSV de captura, PSD, metricas y reports. | Medio | Duplica parte de DSP para analisis offline. |
| `python/tools/validate_spectral_features.py` | Tools CLI / offline | Valida features espectrales y sonificacion por ventanas. | Medio | Usa quality gate offline. |
| `python/tools/compare_eeg_captures.py` | Tools CLI / offline | Compara capturas abiertas/cerradas u otras condiciones. | Bajo | Produce markdown comparativo. |
| `python/tools/build_validation_docs.py` | Tools CLI / docs | Genera documentos, tablas y figuras de validacion TFG. | Medio | Script grande; toca muchos outputs. |
| `python/tools/set_ads_diagnostic_mode.py` | Tools CLI / firmware | Cambia `ADS_DIAGNOSTIC_MODE` en `sketch.ino`. | Medio | Edita firmware; usar con cuidado. |
| `python/tools/test_led_matrix_visualizer.py` | Tests / LED | Tests simples para frame LED, clipping y mapeo. | Medio | Se puede ejecutar sin hardware. |
| `docs/auditoria_captura_datos.md` | Documentacion | Auditoria previa de captura, ADS1299, filtros y tools. | Medio | Base muy util para esta auditoria. |
| `docs/ads1299_diagnostic_modes.md` | Documentacion | Modos ADS, protocolos y capturas recomendadas. | Medio | Define modo CH1-only/Bias. |
| `docs/ads1299_register_audit_bias_drl.md` | Documentacion | Auditoria de registros ADS1299 y BIAS/DRL. | Medio | Complementa `ADS1299_Registers.h`. |
| `docs/diseno_spectral_quality_score.md` | Documentacion | Diseno del quality gate y efectos en sonificacion. | Medio | Explica umbrales y gate. |
| `docs/led_matrix_piano_scroll.md` | Documentacion | Diseno/auditoria del piano scroll LED 13x8. | Medio | Documento de la rama scroll. |
| `docs/resultados_validacion_dsp_mixta.md` | Reports | Resultados DSP de captura mixta. | Bajo | Evidencia experimental. |
| `docs/resultados_validacion_espectral_capturas.md` | Reports | Resumen de validacion espectral de capturas reales. | Medio | Soporta decisiones de features. |
| `docs/validacion_bandas_eeg_sonificacion.md` | Reports | Validacion de bandas y usos para sonificacion. | Medio | Similar a docs TFG, posible redundancia. |
| `docs/validacion_de_la_captura_de_datos.md` | Reports | Validacion de captura de datos. | Medio | Documento historico. |
| `docs/validacion_tfg/*.md` | Documentacion TFG | Serie 00-08 de validacion formal: captura, montaje, calidad, DSP, features, protocolo e historial. | Medio | Documentacion mas definitiva. |
| `docs/validacion_tfg/tables/*.csv|*.md` | Reports / tablas | Inventario de capturas, resumen, comparaciones y decisiones. | Bajo | Salidas generadas por tools. |
| `docs/validacion_tfg/figures/*.png|*.pdf` | Assets / figuras | Figuras de validacion de captura, PSD, estados y quality gate. | Bajo | Artefactos para memoria TFG. |
| `captures/<timestamp>/eeg_timeseries.csv` | Capturas | Series temporales reales con `block_idx`, `sample_idx`, status y CH1-CH4 uV. | Medio | Datos base; no modificar. |
| `captures/<timestamp>/metadata.json` | Capturas | Metadatos de condicion, fs, ADS1299, git y resumen RX. | Medio | Trazabilidad clave. |
| `captures/<timestamp>/quality_report.md|json` | Reports | Analisis de calidad por captura. | Medio | Evidencia experimental. |
| `captures/<timestamp>/spectral_validation_report.md|json` | Reports | Validacion espectral por captura. | Medio | Contiene quality score y conclusiones. |
| `captures/<timestamp>/spectral_summary.csv` | Reports | Resumen espectral por canal. | Bajo | Salida derivada. |
| `captures/<timestamp>/psd_multitaper.csv` | Reports | PSD multitaper por captura. | Bajo | Salida derivada. |
| `captures/<timestamp>/windowed_bandpowers.csv` | Reports | Bandpowers por ventanas. | Medio | Usado para validacion y docs. |
| `captures/<timestamp>/windowed_sonification_features.csv` | Reports | Features de sonificacion por ventanas. | Medio | Compara offline/live. |
| `captures/comparisons/*.csv|*.json|*.md` | Reports | Comparaciones agregadas de robustez y protocolo mixto. | Bajo | Evidencia resumida. |

Directorios de captura existentes:

| Directorio | Condicion / uso inferido |
| --- | --- |
| `20260523-175959_post_configfix_shorted_inputs` | Diagnostico entradas internas en corto. |
| `20260523-195752_ear_eeg_ch1_only_still_30s` | Ear EEG CH1-only quieto 30 s. |
| `20260523-200925_ear_eeg_ch1_only_eyes_open_60s` | Ear EEG ojos abiertos 60 s. |
| `20260523-201055_ear_eeg_ch1_only_eyes_closed_60s` | Ear EEG ojos cerrados 60 s. |
| `20260523-201321_ear_eeg_ch1_only_jaw_movement_30s` | Artefacto mandibula. |
| `20260523-202120_fp1_fp2_ch1_only_quiet_30s` | Fp1-Fp2 quieto. |
| `20260523-202208_fp1_fp2_ch1_only_eyes_open_60s` | Fp1-Fp2 ojos abiertos. |
| `20260523-202323_fp1_fp2_ch1_only_eyes_closed_60s` | Fp1-Fp2 ojos cerrados. |
| `20260523-202451_fp1_fp2_ch1_only_forehead_blink_artifact_30s` | Artefacto frente/parpadeo. |
| `20260524-104015_live_dsp_validation_mixed_states_ear_eeg` | Validacion DSP live con estados mixtos. |
| `20260524-115948_diag_atenuacion_mixed_states_ear_eeg` | Diagnostico atenuacion artefactos. |
| `20260524-122200_final_atenuacion_artefactos_mixed_states` | Captura final de referencia para quality gate. |
| `comparisons` | Comparativas agregadas entre capturas. |
