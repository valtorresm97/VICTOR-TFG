# 00. Inventario del proyecto - final-v4

## 1. Objetivo

Este documento resume el inventario global del proyecto EEG-MIDI desde una perspectiva narrativa. Su funcion es orientar la lectura de la arquitectura y de los bloques principales sin repetir la auditoria funcion por funcion.

La auditoria detallada actual esta en:

```text
docs/02_auditoria_codigo/funcion_por_funcion/
```

La configuracion principal actual esta en:

```text
docs/configuracion_final_v4.md
```

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

Nota historica: esta carpeta nacio durante auditorias sobre `firmware-final-v1` y ramas de LED/matrix scroll. El inventario queda ahora reajustado a final-v4.

## 2. Bloques principales del sistema

El sistema queda organizado en estos bloques:

```text
Firmware/MCU
ADS1299/SPI
Streaming Bridge
Python backend
DSP y quality gate
Sonificacion y MIDI
WebUI
Capturas y validacion
Benchmarks
Tools offline
Documentacion TFG
LED matrix lateral
```

El flujo principal validado es:

```text
ADS1299 -> firmware -> eeg_block_uV -> Python backend -> DSP -> quality gate -> sonificacion -> midi_bytes -> Serial1/D1 TXINV -> MIDI OUT fisico
```

## 3. Inventario por familias

| Familia | Archivos principales | Papel | Criticidad | Lectura final-v4 |
| --- | --- | --- | --- | --- |
| Raiz/config | `AGENTS.md`, `README.md`, `app.yaml` | Reglas, entrada del repo y configuracion App Lab. | Media/Alta | Mantener coherentes con final-v4. |
| Config firmware | `sketch/sketch.yaml` | Perfil App Lab, RouterBridge y librerias locales ADS/SPI. | Alta | No romper dependencias locales. |
| Firmware principal | `sketch/sketch.ino` | ADS1299, DRDY, filtros, streaming, handlers MIDI/LED y bench. | Critica | Centro del tiempo real MCU. |
| Firmware streaming | `sketch/streaming.h` | `EegBlockUV`, ring TX y `Bridge.notify("eeg_block_uV")`. | Critica contrato | No cambiar sin `eeg_contract.py`. |
| Firmware filtros | `sketch/filters.h` | HP/DC blocker, notch 50 Hz, LP 40 Hz y conversion a uV. | Critica | Cambia el espectro que recibe Python. |
| Firmware bench | `sketch/bench.h` | Metricas MCU por Monitor. | Media/Alta | Evidencia de rendimiento sin trafico Bridge extra. |
| Firmware sintetico | `sketch/synthetic.h` | Generador diagnostico sin ADS real. | Media | No es evidencia final TFG. |
| ADS1299 driver | `ADS1299Plus.*`, `ADS1299_Registers.h` | Power-up, registros, comandos, RDATAC, status y unpack 24-bit. | Critica hardware | Validado para ADS1299-4. |
| Safe SPI | `ADS1299_SafeSPI.*` | SPI 2 MHz, MSB first, MODE1 y CS manual. | Critica hardware | No tocar sin placa. |
| Python entrada | `python/main.py` | Crea backend, WebUI y loop App Lab. | Critica runtime | Entrada Linux/App Lab. |
| Backend | `python/backend_service.py` | Orquestador RX, DSP, quality, sonificacion, MIDI, snapshot, capture y LED lateral. | Critica runtime | Demasiado ancho; simplificar con cuidado. |
| Contrato EEG | `python/eeg_contract.py` | Constantes y parser `eeg_block_uV`. | Critica contrato | Fuente Python del contrato firmware/Python. |
| Receiver | `python/receiver.py` | Handlers Bridge, validacion de bloques/status/indices y cola. | Critica runtime | Ruta principal `eeg_block_uV`; `eeg_frame_uV` legacy. |
| DSP buffer | `python/eeg_signal_processor.py` | Ring buffer, uV->V, ventana y features live. | Critica runtime | Ruta principal `compute_live_features()`. |
| DSP core | `python/dsp_core.py` | PSD multitaper/Welch/periodogram, bandpowers, picos y spectrogram. | Critica runtime | Multitaper es metodo live principal. |
| Quality gate | `python/spectral_quality.py` | `score`, `state`, `gate_factor`, `valid_for_sonification`. | Critica seguridad | Conservar como `SignalQuality / QualityGate`. |
| Sonificacion features | `python/sonification_features.py` | Features EEG -> controles final-v4 suavizados y con gate. | Critica runtime | Usa nombres `alpha_drive`, etc. |
| Musica | `music_segment.py`, `music_bar.py`, `music_note.py`, `music_utils.py`, `scale_registry.py` | Segmento, compas, notas, escalas y validacion de notas. | Critica runtime | Ruta live: `build_live_segment`, `generate_live_bar`, `generate_notes_for_bar`. |
| MIDI live | `python/midi_live.py` | Scheduler, eventos, bytes MIDI y panic. | Critica runtime/seguridad | Panic esencial. |
| MIDI transport | `python/midi_byte_transport.py` | `Bridge.call("midi_bytes", n,b0,b1,b2)`. | Critica contrato/hardware | Activo por defecto en final-v4. |
| WebUI server | `python/web_server.py` | WebUI brick, `/latest`, `/status`, socket, panic y music config. | Critica UI/TFG | Observador/control musical ligero. |
| WebUI assets | `assets/index.html`, `assets/app.js`, `assets/styles.css` | Dashboard, render snapshot, controles musicales y piano roll. | Critica UI/TFG | Tratar con cuidado; muy acoplado al snapshot. |
| Captura runtime | `python/capture_manager.py` | Solicitudes JSON y escritura CSV/metadata. | Lateral runtime | No calcula quality gate; guarda datos. |
| Estado runtime | `python/app_state.py` | JSON atomico de snapshot/status. | Media/Alta | Fallback WebUI/tools. |
| LED lateral | `led_matrix_visualizer.py`, `led_matrix_transport.py` | `music.recent_notes` -> frame 13x8 -> `led_matrix_row`. | Lateral runtime | Desactivado por defecto; no UML principal. |
| Tools CLI | `python/tools/*.py` | Capturas, analisis, docs, figuras, ADS mode y benchmarks. | Offline/validacion | No runtime principal; si trazabilidad TFG. |
| Benchmarks | `benchmarks/*.py`, `benchmarks/results`, `benchmarks/reports` | Medicion Python/Linux y parser de resultados. | Offline TFG | Evidencia temporal final-v4. |
| Docs validacion | `docs/validacion_tfg/**` | Benchmarks, capturas finales, reportajes y figuras. | Evidencia TFG | Fuente principal de resultados. |
| Capturas | `captures/**` | Datos EEG, metadata, features, calidad y musica. | Evidencia TFG | No modificar salvo regeneracion controlada. |

## 4. Configuracion final-v4 resumida

| Configuracion | Valor | Lectura |
| --- | --- | --- |
| `USE_SYNTHETIC` | `0` | ADS1299 real, no sintetico. |
| `ADS_DIAGNOSTIC_MODE` | `5` | Modo final CH1-only `bias_ch1_only_loff_off`. |
| Montaje | `ear_eeg_ch1_only` | CH1 canal EEG principal. |
| CH2-CH4 | Conservados por contrato | No interpretarlos como EEG activo en capturas finales. |
| `EEG_STREAMING_NOTIFY_ENABLED` | `1` | Activa `eeg_block_uV`. |
| `BLOCK_SAMPLES` | `8` | 31.25 bloques/s. |
| `FEATURE_WINDOW_SEC` | `4.0` | Ventana DSP/quality. |
| `FEATURE_HOP_SAMPLES` | `64` | Presupuesto Python 256 ms. |
| `MIDI_UART_ENABLED` | `1` | MIDI fisico activo en firmware. |
| `EEG_MIDI_LIVE_ENABLED` | `True` | MIDI live activo en Python. |
| UART MIDI | `Serial1`/D1 | TX invertido obligatorio. |
| `LED_MATRIX_ENABLED` | `0` | LED desactivada firmware. |
| `EEG_LED_MATRIX_ENABLED` | `False` | LED desactivada Python. |
| WebUI | Activa | Monitorizacion, panic, root/main/scale y piano roll. |

## 5. Capturas y evidencia actual

La evidencia final actual se organiza alrededor de:

```text
benchmarks reales final-v4
sesion final s01_20260528
reportajes finales
figuras estandar y enhanced
```

Rutas principales:

```text
docs/validacion_tfg/09_benchmarks_rendimiento_placa.md
docs/validacion_tfg/10_resultados_captura_final_laboratorio.md
docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md
docs/validacion_tfg/reportajes_capturas_s01_20260528/
docs/validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib/
docs/validacion_tfg/figures/capturas_finales_s01_20260528_enhanced/
```

Las capturas antiguas de mayo 2026 y capturas mixtas siguen siendo utiles como antecedentes de desarrollo, diagnostico y ajuste del quality gate, pero no deben presentarse como evidencia final principal si contradicen la sesion `s01_20260528`.

## 6. Tools y outputs importantes

| Tool/output | Uso final-v4 |
| --- | --- |
| `capture_eeg_quality.py` | Solicita capturas al backend vivo mediante `capture_request.json`. |
| `final_capture_session.py` | Gestiona sesion final y conserva musica (`music_snapshots.jsonl`, `music_notes.csv`). |
| `validate_spectral_features.py` | Recalcula bandpowers, quality y controles de sonificacion offline. |
| `parse_mcu_bench_monitor.py` | Parseo de Monitor `[BENCH] EEG_MIDI` sin contaminar Bridge. |
| `benchmark_real_capture.py` | Mide funciones Python sobre captura real. |
| `build_final_capture_docs_matplotlib.py` | Genera figuras/reportajes automaticos estandar. |
| `build_capture06_enhanced_figures.py` | Genera figuras enhanced de captura 06. |
| `set_ads_diagnostic_mode.py` | Cambia macro ADS; herramienta peligrosa que requiere recompilar/subir. |

## 7. Contratos y rutas criticas

No tocar sin pruebas:

```text
eeg_block_uV
FS_HZ=250
NUM_CHANNELS=4
BLOCK_SAMPLES=8
LSB_V
status prefix 0xC00000
compute_live_features
compute_quality_diagnostics
compute_spectral_quality
SonificationFeatureAdapter
MidiScheduler
MidiByteTransport
midi_bytes
Serial1/D1 TXINV
snapshot keys WebUI
```

Rutas legacy/compatibilidad a ocultar del UML principal:

```text
eeg_frame_uV
compute_online_features
generate_bars
generate_notes_for_segment
legacy aliases de sonificacion
MIDI test loop
LED matrix
```

## 8. Relacion con el resto de documentos

Este inventario debe leerse como entrada rapida. Para mas detalle:

```text
docs/configuracion_final_v4.md
docs/01_arquitectura_sistema/09_mapa_contratos_entre_modulos.md
docs/01_arquitectura_sistema/10_mapa_funciones_criticas.md
docs/02_auditoria_codigo/funcion_por_funcion/11_hallazgos_para_simplificacion_futura.md
docs/01_arquitectura_sistema/01_arquitectura_global.md
```

## 9. Conclusion

El proyecto final-v4 ya no debe entenderse como un conjunto de scripts sueltos, sino como una arquitectura integrada:

```text
firmware de adquisicion y transporte
backend Python de DSP/quality/sonificacion/MIDI
WebUI de observacion y control musical
herramientas laterales de captura, validacion y benchmark
corpus documental para TFG
```

Este documento conserva una vision global. La precision tecnica y las decisiones de refactor deben tomarse desde la auditoria detallada final-v4.



