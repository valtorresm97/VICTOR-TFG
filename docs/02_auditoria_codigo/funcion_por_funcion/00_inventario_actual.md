# 00. Inventario actual final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Actualizacion final-v4: revisada en la rama documental `refactor/essential-eeg-midi-plan` contra la rama integrada `firmware-final-v4`.

Alcance final-v4: codigo runtime, firmware, WebUI, herramientas offline, benchmarks reales, capturas finales y documentacion TFG relevantes de la aplicacion EEG-MIDI. La version final-v4 integra dos bloques nuevos respecto al inventario final-v3:

- benchmarks reales en placa y parser de Monitor MCU;
- capturas finales `s01_20260528`, reportajes, figuras y datos musicales.

Criterio de lectura:

- `configuracion_final_v4.md` es el resumen principal activo.
- Este inventario sirve como mapa funcion/archivo para auditorias y futura version esencial UML.
- Los artefactos `benchmarks/`, `captures/` y `docs/validacion_tfg/` no deben borrarse durante la simplificacion; pueden quedar fuera del UML principal, pero son evidencia del TFG.

## 1. Inventario de runtime, firmware y herramientas

| Archivo | Bloque | Rol | Critico | Tipo | Observaciones final-v4 |
| --- | --- | --- | --- | --- | --- |
| `app.yaml` | Configuracion App Lab | Perfil principal de Arduino App Lab | Si | Config | Debe conservar `arduino:zephyr` y librerias locales ADS1299. |
| `README.md` | Documentacion | Resumen de proyecto | No | Doc | Punto de entrada humano; puede requerir alineacion posterior con final-v4. |
| `AGENTS.md` | Documentacion | Reglas tecnicas del agente | Si | Doc | Define contratos de pines, streaming y prioridades. Puede contener lenguaje historico; no cambiar reglas sin revision. |
| `sketch/sketch.ino` | Firmware MCU | Loop real-time ADS1299, Bridge, MIDI y LED handlers | Si | C++ | Archivo mas delicado de firmware. Contiene `ADS_DIAGNOSTIC_MODE=5`, `MIDI_UART_ENABLED=1`, `LED_MATRIX_ENABLED=0`. |
| `sketch/streaming.h` | Streaming/Bridge | Ring de bloques y `Bridge.notify("eeg_block_uV")` | Si | C++ header | Contrato MCU->Python. No cambiar sin sincronizar `python/eeg_contract.py`. |
| `sketch/filters.h` | Firmware MCU | DC blocker, notch 50 Hz, low-pass 40 Hz, conversion uV | Si | C++ header | Afecta escala y contenido espectral recibido. No hay modo raw/unfiltered runtime. |
| `sketch/bench.h` | Benchmarks | Contadores de rendimiento MCU | Medio | C++ header | Observabilidad MCU; se usa con Monitor/App Lab y parser offline, sin aÃ±adir trafico Bridge. |
| `sketch/synthetic.h` | Benchmarks y modos sinteticos | Generador EEG-like sin ADS1299 | Medio | C++ header | Util para validar Bridge/DSP sin hardware analogico, pero no usar como evidencia TFG final. |
| `sketch/sketch.yaml` | Configuracion App Lab | Librerias firmware | Si | YAML | Conserva librerias locales y dependencias necesarias. Revisar antes de tocar App Lab. |
| `sketch/ADS1299Plus/src/ADS1299Plus.h` | Driver ADS1299 | API alto nivel ADS1299 | Si | C++ header | Define `NUM_CHANNELS=4`, frame 15 bytes y `unpack24`. |
| `sketch/ADS1299Plus/src/ADS1299Plus.cpp` | Driver ADS1299 | Implementa comandos, registros y lectura RDATAC | Si | C++ | Critico para SPI/DRDY/status. |
| `sketch/ADS1299Plus/src/ADS1299_Registers.h` | Driver ADS1299 | Mapa de registros, comandos y mascaras | Si | C++ header | Cambios requieren datasheet y prueba en placa. Bits fijos CONFIG1/CONFIG3 ya documentados. |
| `sketch/ADS1299Plus/library.properties` | Configuracion App Lab | Libreria local ADS1299Plus | Medio | Config | Mantener local. |
| `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.h` | SPI seguro | API wrapper SPI | Si | C++ header | Encapsula CS/SPI. |
| `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.cpp` | SPI seguro | SPI MODE1, MSBFIRST, 2 MHz | Si | C++ | No cambiar modo/velocidad sin validar ADS1299. |
| `sketch/ADS1299_SafeSPI/library.properties` | Configuracion App Lab | Libreria local SafeSPI | Medio | Config | Mantener local. |
| `python/main.py` | Backend Python | Arranque App Lab, backend y WebUI | Si | Python | Punto de entrada runtime en Linux/App Lab. |
| `python/backend_service.py` | Backend Python | Orquestacion RX, DSP, sonificacion, MIDI, LED, snapshot y capturas | Si | Python | Archivo con mayor responsabilidad en Linux. No refactorizar sin pruebas de contrato. |
| `python/receiver.py` | Receiver | Callback Bridge `eeg_block_uV`, cola y metricas | Si | Python | Critico para contrato, perdidas y tasas. |
| `python/eeg_contract.py` | Streaming/Bridge | Constantes y parser Python del payload EEG | Si | Python | Fuente Python compartida: `FS_HZ=250`, `NUM_CH=4`, `BLOCK_SAMPLES=8`, `STATUS_PREFIX=0xC00000`. |
| `python/eeg_signal_processor.py` | EEG signal processor | Ring buffer multicanal y acceso a DSP | Si | Python | Contrato uV->V; ventana live de features. |
| `python/dsp_core.py` | DSP | PSD, multitaper, bandpowers y features | Si | Python | Fuente unica de multitaper live/offline. |
| `python/spectral_quality.py` | DSP/calidad | Score/gate de calidad espectral | Si | Python | Controla si sonificacion se considera valida. Documento activo: `diseno_spectral_quality_score.md`. |
| `python/sonification_features.py` | Sonificacion | Features DSP -> controles reportables de sonificacion | Si | Python | En final-v4 usa nombres publicos `alpha_drive`, `beta_gamma_drive`, `rms_beta_activity`, etc.; alias legacy solo internos. |
| `python/music_segment.py` | Generacion musical | Estado musical live desde sonificacion | Medio | Python | Escala, nota principal, cadencia y resumen musical. |
| `python/music_bar.py` | Generacion musical | Acordes, posiciones ritmicas y barras | Medio | Python | Usa RNG; requiere cautela si se busca reproducibilidad. |
| `python/music_note.py` | Generacion musical | `NoteEvent` y generacion de notas | Medio | Python | Afecta densidad, pitch, velocity y duraciones. |
| `python/music_utils.py` | Generacion musical | Parseo nota musical -> MIDI | Bajo | Python | Utilidad compartida. |
| `python/scale_registry.py` | Generacion musical | Registro de escalas expuestas en WebUI | Bajo | Python | Incluye major, minor, blues, spanish, arabic, harmonic_minor, phrygian_dominant y pentatonicas. |
| `python/midi_live.py` | MIDI live | Eventos MIDI, scheduler, panic, bytes | Si | Python | Evita notas colgadas y define bytes MIDI. |
| `python/midi_byte_transport.py` | MIDI byte transport | `MidiLiveEvent` -> `Bridge.call("midi_bytes")` | Si | Python | Activo por defecto; depende del handler firmware `midi_bytes`, Serial1/D1 y TX invertido. |
| `python/led_matrix_visualizer.py` | LED matrix | `recent_notes` -> frame `rows` 13x8 | Medio | Python | Subsistema secundario; no ruta principal EEG->MIDI. |
| `python/led_matrix_transport.py` | LED matrix | `rows` -> chunks `led_matrix_row` | Medio | Python | Desactivado por defecto. No activar durante benchmarks salvo prueba especifica. |
| `python/app_state.py` | Estado runtime | JSON atomico snapshot/history | Si | Python | Helper `atomic_write_json` centralizado; sostiene fallback UI/disco. |
| `python/runtime_config.py` | Configuracion App Lab | Env vars y defaults runtime | Medio | Python | Centraliza configuracion Python/LED/MIDI. |
| `python/capture_manager.py` | Capturas | Captura CSV incremental desde bloques EEG | Si | Python | Escribe `capture_status.json`, `metadata.json`, `eeg_timeseries.csv` y datos musicales cuando procede. Integrado en backend. |
| `python/web_server.py` | Web server | WebUI Brick y endpoints | Medio | Python | Rutas `/latest`, `/status`, `/midi/*`, `/music/*`; no DSP pesado. |
| `assets/index.html` | Assets WebUI | Estructura dashboard y controles musicales | Medio | HTML | Root/main/scale, panic, bandpowers, controles de sonificacion y piano roll live. |
| `assets/app.js` | Assets WebUI | Render de snapshot, controles musicales, panic, piano roll | Medio | JS | Depende de nombres de claves del snapshot y endpoints WebUI. |
| `assets/styles.css` | Assets WebUI | Estilos dashboard | Bajo | CSS | No afecta backend. |
| `python/tools/analyze_eeg_capture.py` | Tools CLI | Analisis calidad de una captura | Medio | Python CLI | Usa `DSPCore`; genera reports. Offline. |
| `python/tools/capture_eeg_quality.py` | Tools CLI | Solicita captura a app App Lab en ejecucion | Medio | Python CLI | Escribe `capture_request.json`. Offline/control. |
| `python/tools/compare_eeg_captures.py` | Tools CLI | Compara ojos abiertos/cerrados | Bajo | Python CLI | Offline. |
| `python/tools/validate_spectral_features.py` | Tools CLI | Validacion ventana a ventana de features | Medio | Python CLI | Usa `DSPCore`, `spectral_quality` y sonificacion; genera CSV/reportes offline. |
| `python/tools/build_validation_docs.py` | Tools CLI | Genera docs, tablas y figuras de validacion antiguas/consolidadas | Medio | Python CLI | Tool offline; no confundir con runtime. |
| `python/tools/final_capture_session.py` | Tools CLI | Gestiona sesion final de capturas | Medio | Python CLI | Usado para flujo `s01_20260528`; no forma parte del loop live esencial. |
| `python/tools/build_final_capture_docs.py` | Tools CLI | Genera documentacion final de capturas | Medio | Python CLI | Offline; conservar por trazabilidad. |
| `python/tools/build_final_capture_docs_matplotlib.py` | Tools CLI | Genera figuras/reportajes matplotlib | Medio | Python CLI | Offline; salida en `docs/validacion_tfg/`. |
| `python/tools/build_capture06_enhanced_figures.py` | Tools CLI | Figuras enhanced captura 06 | Bajo | Python CLI | Offline; usado para figura principal candidata. |
| `python/tools/parse_mcu_bench_monitor.py` | Tools CLI | Parser de logs `[BENCH] EEG_MIDI` del Monitor MCU | Medio | Python CLI | Clave para benchmarks reales MCU sin trafico Bridge adicional. |
| `python/tools/set_ads_diagnostic_mode.py` | Tools CLI | Cambia macro `ADS_DIAGNOSTIC_MODE` | Si | Python CLI | Modifica firmware; usar con cuidado y recompilar. |
| `python/tools/test_led_matrix_visualizer.py` | Tests/validaciones | Test manual LED visualizer | Medio | Python test | Test ejecutable detectado para subsistema LED. |

## 2. Artefactos de validacion, benchmarks y capturas

| Ruta | Bloque | Rol | Critico | Tipo | Observaciones final-v4 |
| --- | --- | --- | --- | --- | --- |
| `benchmarks/benchmark_core.py` | Benchmarks | Utilidades comunes de medicion y exportacion | Medio | Python | Offline. No forma parte del loop EEG->MIDI. |
| `benchmarks/benchmark_real_capture.py` | Benchmarks | Benchmark Python/Linux sobre captura real | Medio | Python | Usa `eeg_timeseries.csv` real. |
| `benchmarks/run_all_benchmarks.py` | Benchmarks | Ejecucion agrupada de benchmarks Python/Linux | Medio | Python | Entrada principal de benchmark Python. |
| `benchmarks/results/` | Benchmarks | CSV/JSON de resultados | No | Datos | Evidencia de rendimiento; no borrar. |
| `benchmarks/reports/` | Benchmarks | Markdown/logs de resultados | No | Doc/datos | Evidencia de rendimiento; no borrar. |
| `captures/capturas finales/` | Capturas | Capturas finales `s01_20260528` | No | Datos | Evidencia experimental final; no borrar ni mover sin plan. |
| `captures/capturas pruebas casa/` | Capturas | Prueba previa de flujo de captura | No | Datos | Trazabilidad tecnica, no evidencia principal. |
| `docs/validacion_tfg/09_benchmarks_rendimiento_placa.md` | Validacion TFG | Resultados temporales MCU + Python/Linux | Si | Doc | Documento principal de benchmarks reales. |
| `docs/validacion_tfg/10_resultados_captura_final_laboratorio.md` | Validacion TFG | Resultados de sesion final laboratorio | Si | Doc | Documento principal de capturas finales. |
| `docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md` | Validacion TFG | Relato tecnico global de la sesion | Si | Doc | Entrada narrativa principal para memoria. |
| `docs/validacion_tfg/reportajes_capturas_s01_20260528/` | Validacion TFG | Reportajes individuales por captura | Si | Doc | Analisis por condicion. |
| `docs/validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib/` | Figuras | Figuras estandar por captura | No | Imagenes | Fuente visual para memoria. |
| `docs/validacion_tfg/figures/capturas_finales_s01_20260528_enhanced/` | Figuras | Figuras reajustadas captura 06 | No | Imagenes | Figura 06 candidata principal. |

## 3. Documentacion activa e historica

| Ruta | Bloque | Rol | Critico | Tipo | Observaciones final-v4 |
| --- | --- | --- | --- | --- | --- |
| `docs/README.md` | Documentacion | Indice activo final-v4 | Si | Doc | Punto de entrada documental. |
| `docs/configuracion_final_v4.md` | Documentacion | Resumen tecnico principal final-v4 | Si | Doc | Fuente preferente de estado actual. |
| `docs/auditoria_final_v4_fase1_2.md` | Documentacion | Auditoria de fases 1 y 2 | Medio | Doc | Deja trazabilidad de decisiones de limpieza documental. |
| `docs/04_protocolos_captura/04_protocolos_captura/protocolo_capturas_multiusuario.md` | Capturas | Protocolo experimental repetible | Medio | Doc | Activo para nuevas sesiones. |
| `docs/04_protocolos_captura/04_protocolos_captura/templates/plantilla_sesion_sujeto.md` | Capturas | Plantilla de sesion | Medio | Doc | Activo. |
| `docs/04_protocolos_captura/04_protocolos_captura/sesiones_captura/` | Capturas | Sesiones documentadas | Medio | Doc | Incluye prueba de casa y sesion final. |
| `docs/ads1299_diagnostic_modes.md` | Subsistema ADS1299 | Modos diagnosticos | Medio | Doc | Activo final-v4; modo final de capturas = 5. |
| `docs/ads1299_register_audit_bias_drl.md` | Subsistema ADS1299 | Registros, BIAS/DRL y CH1-only | Medio | Doc | Activo final-v4. |
| `docs/diseno_spectral_quality_score.md` | Subsistema DSP/calidad | Diseno quality gate | Medio | Doc | Activo final-v4 con nombres reportables nuevos. |
| `docs/midi_out_inverted_tx_validation.md` | Subsistema MIDI | Validacion TX invertido y `midi_bytes` | Medio | Doc | Activo final-v4. |
| `docs/led_matrix_piano_scroll.md` | Subsistema LED | Piano scroll opcional | Bajo | Doc | Activo secundario; desactivado por defecto. |
| `docs/historico/documentacion antigua/` | Historico | Documentos reemplazados o solapados | No | Doc | Consultar solo para trazabilidad historica. |
| `docs/02_auditoria_codigo/funcion_por_funcion/**` | Auditoria detallada | Auditoria funcion por funcion y mapas | Medio | Doc | Bloque activo pendiente de refresco progresivo a final-v4. |

## 4. Componentes esenciales para futura version UML

Para una futura version esencial explicativa, el flujo principal deberia concentrarse en:

```text
sketch/sketch.ino
sketch/streaming.h
sketch/filters.h
sketch/ADS1299Plus/
sketch/ADS1299_SafeSPI/
python/main.py
python/backend_service.py
python/receiver.py
python/eeg_contract.py
python/eeg_signal_processor.py
python/dsp_core.py
python/spectral_quality.py
python/sonification_features.py
python/music_segment.py
python/music_bar.py
python/music_note.py
python/music_utils.py
python/scale_registry.py
python/midi_live.py
python/midi_byte_transport.py
python/app_state.py
python/runtime_config.py
python/web_server.py
assets/index.html
assets/app.js
assets/styles.css
```

No incluir como nucleo principal, aunque deben conservarse:

```text
benchmarks/
captures/
docs/validacion_tfg/reportajes_*
docs/validacion_tfg/figures/
python/tools/
python/led_matrix_visualizer.py
python/led_matrix_transport.py
```

Matiz importante: `capture_manager.py` esta integrado en `backend_service.py`, asi que no debe eliminarse sin plan y pruebas aunque no sea central para el UML principal.

## 5. Contratos intocables detectados

- `Bridge.notify("eeg_block_uV")`.
- `Bridge.call("midi_bytes", n, b0, b1, b2)`.
- `Bridge.call("led_matrix_row", row_idx, chunk0, chunk1, chunk2)` si se mantiene LED.
- `FS_HZ=250`.
- `NUM_CH=4`.
- `BLOCK_SAMPLES=8`.
- `STATUS_PREFIX=0xC00000`.
- `STATUS_MASK=0xF00000`.
- `LSB_V=2.235e-8`.
- `ADS_DIAGNOSTIC_MODE=5` si se quieren capturas comparables con final-v4.
- `Serial1/D1` con TX invertido para MIDI OUT fisico.
- Snapshot consumido por WebUI.
- `music.recent_notes` para piano roll y LED opcional.
- CSV de capturas con `sample_idx`, `status`, `ch1_uV..ch4_uV`.

## 6. Lectura para el siguiente documento

Siguiente auditoria recomendada:

```text
docs/02_auditoria_codigo/funcion_por_funcion/01_firmware_funcion_por_funcion.md
```

Objetivo al revisarla:

- actualizar contexto a final-v4;
- confirmar `ADS_DIAGNOSTIC_MODE=5`;
- confirmar MIDI fisico `Serial1/D1/TXINV`;
- confirmar `BENCH_REPORT_ENABLED=1` y uso de Monitor;
- marcar LED matrix como secundaria/desactivada por defecto;
- no modificar firmware.

