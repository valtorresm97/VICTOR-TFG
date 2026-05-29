# Configuracion final v4

Documento resumen del estado integrado `firmware-final-v4` del sistema EEG-MIDI. Consolida el estado real del codigo, los benchmarks reales en placa, las capturas finales de laboratorio y la documentacion generada para el TFG.

Este documento no cambia firmware ni runtime. Sirve como punto de entrada tecnico para entender que contiene la version final-v4 y que partes deben preservarse antes de cualquier simplificacion futura.

## Estado de rama y procedencia

Rama final integrada:

```text
firmware-final-v4
```

Ramas/documentos de procedencia integrados:

| Procedencia | Contenido integrado | Estado en final-v4 |
| --- | --- | --- |
| `docs/final-v3-audit-update` | Auditorias final-v3, benchmarks reales Python/Linux, benchmarks MCU y documento de validacion temporal | Integrado como evidencia de rendimiento |
| `docs/capture-protocol` | Protocolo de capturas, sesion final `s01_20260528`, reportajes, figuras y datos musicales | Integrado como evidencia experimental |
| `bench-y-capturas` | Rama puente con benchmarks + capturas | Equivalente al contenido base usado para `firmware-final-v4` |
| `firmware-final-v4` | Rama final para continuar futuras modificaciones | Estado actual de referencia |

Nota importante: algunos documentos conservan referencias historicas a las ramas donde se generaron originalmente los resultados. Eso no invalida los resultados; en final-v4 deben leerse como artefactos integrados.

## Arquitectura general

Flujo tecnico completo:

```text
Electrodos EEG
  -> ADS1299-4PAG
  -> SPI RDATAC / DRDY
  -> STM32U585 en Arduino UNO Q
  -> filtros MCU y conversion a microvoltios
  -> Bridge.notify("eeg_block_uV")
  -> Python EEGReceiver
  -> EEGSignalProcessor / DSPCore
  -> compute_spectral_quality
  -> SonificationFeatureAdapter
  -> MusicSegment / Bar / NoteEvent
  -> MidiScheduler / MidiByteTransport
  -> Bridge.call("midi_bytes")
  -> firmware midi_bytes()
  -> Serial1 / D1 / TX invertido
  -> MIDI OUT fisico
```

La WebUI se alimenta del snapshot Python y muestra adquisicion, features, bandpowers, diagnostico, quality gate, controles de sonificacion, configuracion musical, estado MIDI y piano roll live.

La matriz LED existe como pipeline secundario basado en `music.recent_notes`, pero esta desactivada por defecto.

## Firmware MCU

Archivo principal:

```text
sketch/sketch.ino
```

Responsabilidades principales:

- inicializar Bridge y Monitor;
- registrar handlers `midi_bytes` y `led_matrix_row`;
- configurar pines ADS1299;
- inicializar SPI seguro;
- configurar ADS1299;
- aplicar modo diagnostico ADS;
- arrancar START + RDATAC;
- atender DRDY;
- leer frames RDATAC;
- reconstruir muestras signed 24-bit;
- convertir counts a voltios;
- aplicar filtros MCU;
- convertir a microvoltios;
- agrupar bloques de 8 muestras;
- publicar `eeg_block_uV`;
- imprimir metricas `[BENCH] EEG_MIDI` en Monitor;
- enviar bytes MIDI por UART fisica.

Configuracion critica observada:

| Parametro | Valor final-v4 | Comentario |
| --- | --- | --- |
| `USE_SYNTHETIC` | `0` | El flujo normal usa ADS1299 real. |
| `ADS_DIAGNOSTIC_MODE` | `5` | CH1 activo, CH2-CH4 apagados/cortocircuitados, BIAS CH1P+CH1N, lead-off off. |
| `FS_HZ` | `250.0f` | Debe coincidir con Python. |
| `LSB_V` | `2.235e-8f` | Consistente con gain 24 y Vref aprox. 4.5 V. |
| `EEG_STREAMING_NOTIFY_ENABLED` | `1` | Publica bloques EEG por Bridge. |
| `BENCH_REPORT_ENABLED` | `1` | Imprime metricas por Monitor, sin modificar payload EEG. |
| `MIDI_UART_ENABLED` | `1` | MIDI fisico activo por defecto. |
| `MIDI_SERIAL` | `Serial1` | Salida fisica D1/TX en UNO Q. |
| `MIDI_MCU_SELF_TEST_ENABLED` | `0` | Test autonomo apagado en flujo normal. |
| `LED_MATRIX_ENABLED` | `0` | Handler registrado, matriz fisica apagada por defecto. |

Pines criticos:

```text
PIN_CS    = D10
PIN_SCLK  = SCK
PIN_MOSI  = MOSI
PIN_MISO  = MISO
PIN_DRDY  = 7
PIN_START = D9
PIN_RESET = D8
PIN_PWDN  = D5
```

No cambiar estos pines sin prueba en placa.

## ADS1299 y modo de adquisicion

El sistema esta preparado para ADS1299-4PAG y conserva contrato de 4 canales.

Modo final usado para capturas principales:

```text
bias_ch1_only_loff_off
```

Equivale a:

- CH1 activo como canal EEG principal;
- BIAS/RLD derivado de CH1P + CH1N;
- lead-off sense desactivado;
- CH2-CH4 apagados/cortocircuitados para evitar entradas flotantes;
- el payload sigue transmitiendo cuatro columnas para no romper el contrato Python.

Implicacion documental:

```text
CH1 es la evidencia EEG principal.
CH2-CH4 se conservan por compatibilidad del contrato, pero no deben interpretarse como EEG activo en la sesion final s01_20260528.
```

## Streaming MCU -> Python

Contrato principal:

```text
Bridge.notify("eeg_block_uV", block_idx, first_sample_idx, sample_count, 8 * (status + ch1_uV + ch2_uV + ch3_uV + ch4_uV))
```

Constantes compartidas:

| Constante | Valor |
| --- | ---: |
| `FS_HZ` | `250` |
| `NUM_CH` | `4` |
| `BLOCK_SAMPLES` | `8` |
| `STATUS_PREFIX` | `0xC00000` |
| `STATUS_MASK` | `0xF00000` |
| `LSB_V` | `2.235e-8` |

El lado Python centraliza estas constantes en:

```text
python/eeg_contract.py
```

Cualquier cambio de `streaming.h` debe ir acompaÃ±ado de cambios coordinados en `eeg_contract.py`, `receiver.py`, capturas y herramientas offline.

## Python backend

Archivo orquestador:

```text
python/backend_service.py
```

Responsabilidades principales:

- crear `EEGSignalProcessor`;
- crear `EEGReceiver`;
- crear `CaptureManager`;
- registrar `linux_started`;
- registrar `eeg_block_uV`;
- drenar bloques hacia el buffer DSP;
- calcular features cada `FEATURE_HOP_SAMPLES`;
- calcular diagnosticos de calidad;
- calcular `spectral_quality`;
- adaptar controles de sonificacion;
- generar compases/notas;
- programar eventos MIDI;
- enviar bytes MIDI por Bridge;
- actualizar LED matrix si se activa;
- publicar snapshots WebUI/disco.

Parametros temporales:

| Parametro | Valor | Uso |
| --- | ---: | --- |
| `FEATURE_WINDOW_SEC` | `4.0 s` | Ventana de analisis espectral. |
| `FEATURE_HOP_SAMPLES` | `64` | Cadencia de actualizacion de features. |
| `SNAPSHOT_PUBLISH_PERIOD_SEC` | `0.2 s` | Publicacion UI/socket. |
| `DISK_PUBLISH_PERIOD_SEC` | `1.0 s` | Publicacion a disco. |

Margen Python:

```text
64 muestras / 250 muestras/s = 0.256 s = 256 ms
```

El benchmark final muestra que `compute_live_features` esta muy por debajo de ese presupuesto.

## DSP

Modulos principales:

```text
python/eeg_signal_processor.py
python/dsp_core.py
```

Flujo:

```text
bloques uV
  -> add_block_uV()
  -> conversion uV a V
  -> ring buffer multicanal
  -> ventana CH1 de 4 s
  -> DSPCore.compute_features(psd_method="multitaper")
  -> RMS, PSD, bandpowers, picos
```

Caracteristicas principales:

- frecuencia de muestreo: 250 Hz;
- buffer live: 10 s;
- ventana de features: 4 s;
- metodo PSD principal: multitaper;
- bandas: delta, theta, alpha, beta, gamma;
- salida: RMS, bandpower absoluto, bandpower relativo, picos por banda y frecuencia dominante.

La senal ya llega filtrada desde firmware con:

- high-pass/DC blocker 0.5 Hz;
- notch 50 Hz;
- low-pass 40 Hz.

Python no debe presentarse como fuente de filtrado EEG principal, sino como etapa de buffer, PSD, features y diagnostico.

## Spectral quality

Modulo:

```text
python/spectral_quality.py
```

Funciona como puerta de calidad para evitar interpretar o sonificar con demasiada fuerza ventanas contaminadas.

Estados principales:

| Estado | Comportamiento |
| --- | --- |
| `clean` | Sonificacion plena. |
| `usable_with_caution` | Atenuacion leve. |
| `artifact_suspected` | Atenuacion fuerte. |
| `bad` | No valido para generar nueva sonificacion. |

El quality gate no modifica la adquisicion ni el DSP. Actua despues de calcular features y antes de generar controles musicales.

## Sonificacion

Modulo principal:

```text
python/sonification_features.py
```

En final-v4 los nombres publicos/reportables son:

| Control final-v4 | Interpretacion |
| --- | --- |
| `alpha_drive` | Predominio relativo alpha frente a beta. |
| `beta_gamma_drive` | Activacion relativa de bandas rapidas. |
| `rms_beta_activity` | Actividad global combinando RMS, beta y gamma. |
| `band_driven_density` | Densidad ritmica derivada de bandas y RMS. |
| `spectral_register` | Registro melodico asociado a frecuencia/potencia rapida. |
| `alpha_stability` | Estabilidad asociada a alpha/theta y menor RMS. |
| `rms_band_velocity` | Intensidad MIDI derivada de RMS y bandas. |
| `band_note_probability` | Probabilidad de nota derivada de densidad espectral. |

Compatibilidad:

- Los nombres antiguos `activity`, `calmness`, `tension`, `rhythmic_density`, `register`, `harmonic_stability`, `velocity_factor` y `note_probability` siguen existiendo como alias internos de solo lectura.
- Los alias no deben usarse como nombres principales en la redaccion final del TFG.
- Las figuras y reportes finales deben priorizar los nombres reportables nuevos.

## Generacion musical y MIDI

Modulos principales:

```text
python/music_segment.py
python/music_bar.py
python/music_note.py
python/midi_live.py
python/midi_byte_transport.py
```

Flujo:

```text
SonificationFeatures
  -> MusicSegmentBuilder
  -> BarGenerator
  -> NoteGenerator
  -> NoteEvent
  -> MidiScheduler
  -> MidiLiveEvent
  -> event_to_midi_bytes
  -> MidiByteTransport
  -> Bridge.call("midi_bytes")
  -> firmware midi_bytes()
  -> Serial1/D1
  -> MIDI OUT fisico
```

Configuracion musical activa:

| Parametro | Valor |
| --- | --- |
| `MUSIC_BAR_SEC` | `2.0` |
| `MUSIC_CHORD_MIN_PERIOD_SEC` | `12.0` |
| `MUSIC_CHORD_CHANGE_THRESHOLD` | `0.45` |
| `MUSIC_LOW_NOTES_PER_BAR` | `2` |
| `MUSIC_MEDIUM_NOTES_PER_BAR` | `6` |
| `MUSIC_HIGH_NOTES_PER_BAR` | `11` |
| `MUSIC_PITCH_VARIETY` | `0.65` |
| Canal MIDI interno | `9` = canal MIDI 10 |
| Programa MIDI | `0` |
| Root note default | `C4` |
| Main note default | `G4` |
| Lookahead MIDI | `0.02 s` |

Escalas disponibles en WebUI:

- major;
- minor;
- blues;
- spanish;
- arabic;
- harmonic_minor;
- phrygian_dominant;
- minor_pentatonic;
- major_pentatonic.

## MIDI fisico

Ruta validada:

```text
Python MidiByteTransport
  -> Bridge.call("midi_bytes", n, b0, b1, b2)
  -> firmware midi_bytes()
  -> Serial1 / D1 / USART1_TX
  -> TX invertido
  -> circuito N-audio MIDI OUT
  -> DIN5 / sintetizador fisico
```

Politica final-v4:

- `MIDI_UART_ENABLED=1` por defecto.
- `MIDI_SERIAL=Serial1`.
- TX invertido mediante `USART_CR2_TXINV` es obligatorio.
- Si no existen los simbolos `USART1` o `USART_CR2_TXINV`, el build debe fallar para evitar emitir con polaridad incorrecta.
- `MIDI_MCU_SELF_TEST_ENABLED=0` por defecto.
- `EEG_MIDI_LIVE_ENABLED=True` por defecto en Python.
- Existe `panic` desde Python/WebUI.
- Falta panic autonomo en firmware si Python/App Lab cae.

## WebUI

La UI real no es Streamlit.

Modulo servidor:

```text
python/web_server.py
```

Assets:

```text
assets/index.html
assets/app.js
assets/styles.css
```

Tecnologia:

```text
arduino.app_bricks.web_ui.WebUI
```

Rutas principales:

| Ruta | Funcion |
| --- | --- |
| `GET /status` | Estado minimo del backend. |
| `GET /latest` | Snapshot completo o fallback de disco. |
| websocket `eeg_snapshot` | Snapshot live. |
| `POST /midi/panic` | All Sound Off / All Notes Off. |
| `POST /midi/test-*` | Diagnosticos MIDI. |
| `POST /music/config` | Actualiza root/main/scale. |
| `POST /music/scale/{key}` | Cambia escala. |
| `POST /music/root/{note}` | Cambia root note. |
| `POST /music/main/{note}` | Cambia main note. |

Paneles principales:

- rendimiento de adquisicion;
- features EEG;
- bandpower relativo;
- bandpower absoluto aproximado;
- diagnostico ADS1299/calidad;
- controles de sonificacion;
- controles musicales root/main/scale;
- estado MIDI;
- panic;
- piano roll live.

No hay controles WebUI para:

- cambiar filtros MCU;
- cambiar modo ADS runtime;
- activar/desactivar MIDI desde UI;
- activar/desactivar LED desde UI;
- iniciar capturas desde UI.

## LED matrix

Modulos:

```text
python/led_matrix_visualizer.py
python/led_matrix_transport.py
firmware handler led_matrix_row()
```

Estado final-v4:

- LED fisico desactivado por defecto en firmware (`LED_MATRIX_ENABLED=0`).
- LED desactivado por defecto en Python salvo env var.
- El handler `led_matrix_row` esta registrado como dry-run si LED esta apagado.
- El frame se calcula desde `music.recent_notes`, la misma fuente que el piano roll web.
- No es un pipeline musical independiente.

La version esencial UML puede tratar LED como modulo secundario, no como ruta principal EEG->MIDI.

## Capturas finales

Documento principal:

```text
docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md
```

Documento de resultados globales:

```text
docs/validacion_tfg/10_resultados_captura_final_laboratorio.md
```

Configuracion de sesion:

| Campo | Valor |
| --- | --- |
| Sujeto | `s01` |
| Fecha | `20260528` |
| Montaje | `ear_eeg_ch1_only` |
| ADS mode | `bias_ch1_only_loff_off` |
| Modelo musical | `modelo_captura_final` |
| Carpeta | `captures/capturas finales` |

Condiciones documentadas:

- `00_precheck_10s`;
- `01_eyes_open_rest_60s`;
- `02_eyes_closed_rest_60s`;
- `03_quiet_rest_60s`;
- `04_blink_artifact_30s`;
- `06_eyes_open_repeat_30s`.

Lectura correcta para el TFG:

```text
La sesion valida la integracion tecnica EEG-MIDI con adquisicion real, procesamiento, sonificacion, persistencia de datos y documentacion reproducible.
No debe presentarse como EEG clinicamente limpio.
```

Todas las capturas revisadas mantienen:

- 250 Hz efectivos;
- sample gaps = 0;
- invalid status = 0;
- datos musicales persistidos;
- reports y figuras generadas.

## Benchmarks finales

Documento principal:

```text
docs/validacion_tfg/09_benchmarks_rendimiento_placa.md
```

Principio de validacion:

```text
Solo se usan resultados reales de placa UNO Q/Linux y capturas reales.
No se usan benchmarks sinteticos ni resultados de PC como evidencia del TFG.
```

Artefactos principales:

- `benchmarks/benchmark_core.py`;
- `benchmarks/benchmark_real_capture.py`;
- `benchmarks/run_all_benchmarks.py`;
- `python/tools/parse_mcu_bench_monitor.py`;
- `benchmarks/results/`;
- `benchmarks/reports/`;
- capturas benchmark en `captures/`.

Resultados clave Python/Linux:

| Metrica | Resultado |
| --- | ---: |
| `compute_live_features` mediana | `5.2158 ms` |
| `compute_live_features` p95 | `6.4103 ms` |
| `compute_live_features` maximo | `6.9831 ms` |
| Presupuesto por hop | `256 ms` |

Resultados clave MCU:

| Metrica | Resultado |
| --- | ---: |
| `filt_avg_us` mediana | `5.050 us` |
| `notify_avg_us` mediana | `3367.250 us` |
| `notify_max_us_win` maximo | `11528 us` |
| `loop_max_us_win` maximo | `12886 us` |
| Presupuesto por bloque | `32 ms` |
| `drops_total` | `0` |
| `qmax_global` | `1` |

Conclusion temporal:

```text
El sistema dispone de margen temporal amplio tanto en MCU como en Python/Linux.
El cuello de botella principal no esta en el DSP Python ni en el filtrado MCU.
Los aspectos mas criticos posteriores son calidad de senal, artefactos, estabilidad de montaje y latencia fisica end-to-end EEG -> MIDI OUT.
```

## Herramientas offline

Las herramientas offline son importantes para trazabilidad y TFG, pero no forman parte del loop minimo EEG->MIDI.

Familias principales:

- captura: `python/tools/capture_eeg_quality.py`, `python/tools/final_capture_session.py`;
- analisis: `python/tools/analyze_eeg_capture.py`, `python/tools/validate_spectral_features.py`, `python/tools/compare_eeg_captures.py`;
- documentacion/figuras: `python/tools/build_final_capture_docs.py`, `python/tools/build_final_capture_docs_matplotlib.py`, `python/tools/build_capture06_enhanced_figures.py`;
- benchmarks: `benchmarks/`, `python/tools/parse_mcu_bench_monitor.py`;
- diagnostico ADS: `python/tools/set_ads_diagnostic_mode.py`.

Para una futura version esencial UML, estas herramientas deben conservarse como validacion/offline o archivo historico, no borrarse sin plan.

## Documentacion principal final-v4

Documentos recomendados como entrada:

| Documento | Uso |
| --- | --- |
| `docs/configuracion_final_v4.md` | Resumen tecnico principal final-v4. |
| `docs/00_entrada_tfg/00_entrada_tfg/auditoria_final_v4_fase1_2.md` | Auditoria previa de estado real y pendientes documentales. |
| `docs/validacion_tfg/09_benchmarks_rendimiento_placa.md` | Evidencia temporal en placa. |
| `docs/validacion_tfg/10_resultados_captura_final_laboratorio.md` | Resumen de sesion final de laboratorio. |
| `docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md` | Relato tecnico global de la sesion. |
| `docs/validacion_tfg/reportajes_capturas_s01_20260528/` | Lectura individual por captura. |
| `docs/04_protocolos_captura/protocolo_capturas_multiusuario.md` | Protocolo experimental. |
| `docs/04_protocolos_captura/templates/plantilla_sesion_sujeto.md` | Plantilla de sesion. |
| `docs/02_auditoria_codigo/funcion_por_funcion/` | Auditoria funcion por funcion. |

## Que no se debe tocar sin placa

No cambiar sin validacion en Arduino UNO Q:

- pines ADS1299;
- SPI mode/velocidad;
- secuencia RESET/SDATAC/WREG/RDATAC;
- `ADS_DIAGNOSTIC_MODE` si se van a hacer capturas comparables;
- `FS_HZ`;
- `BLOCK_SAMPLES`;
- `LSB_V`;
- `Bridge.notify("eeg_block_uV")`;
- orden del payload por muestra;
- `MIDI_SERIAL=Serial1`;
- TX invertido;
- `midi_bytes`;
- filtros MCU;
- formato CSV de capturas;
- snapshot consumido por WebUI.

## Limitaciones actuales

- La sesion final valida integracion tecnica, pero no EEG clinico limpio.
- La calidad fisiologica es parcial y contiene artefactos.
- CH1 es el unico canal EEG activo principal en la sesion final.
- CH2-CH4 se conservan por contrato, pero no deben interpretarse como EEG activo en `ADS_DIAGNOSTIC_MODE=5`.
- No existe modo raw/unfiltered runtime para comparar contra filtros MCU.
- El quality score es empirico y necesita mas usuarios/capturas para calibracion fina.
- No se ha medido latencia fisica end-to-end EEG -> MIDI OUT.
- LED matrix sigue deshabilitada por defecto.
- Falta panic autonomo firmware si Python/App Lab cae.
- Falta suite automatica completa para snapshot, endpoints WebUI, MIDI fisico y contratos Bridge.

## Riesgos para una futura simplificacion

Riesgos principales:

- romper Arduino App Lab por reorganizar imports;
- romper el contrato `eeg_block_uV`;
- romper WebUI al cambiar nombres de snapshot;
- romper MIDI fisico al tocar UART/TXINV;
- perder trazabilidad de benchmarks/capturas;
- confundir version esencial explicativa con version validada;
- borrar herramientas necesarias para defender el TFG;
- mezclar resultados de PC/sinteticos con resultados reales de placa.

## Proximo paso recomendado

Antes de refactorizar codigo, la secuencia segura es:

1. Mantener `firmware-final-v4` como rama integrada de referencia.
2. Usar `refactor/essential-eeg-midi-plan` para documentacion y planificacion.
3. Organizar la seccion documental con supervision.
4. Crear `docs/propuesta_version_esencial_uml.md`.
5. Revisar diagramas UML/estados.
6. Solo despues crear una rama de implementacion real, por ejemplo `refactor/essential-eeg-midi`.
7. Aplicar cambios en commits pequenos, con pruebas de contrato y validacion en placa.

Conclusion:

```text
final-v4 es la version integrada y trazable del sistema EEG-MIDI.
La futura version esencial debe simplificar la explicacion y los diagramas, no perder la evidencia de validacion ni modificar contratos criticos sin pruebas.
```





