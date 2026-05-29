# 08. Tools CLI funcion por funcion - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Re-auditoria final-v4: revisada contra codigo real en `firmware-final-v4` desde la rama documental `refactor/essential-eeg-midi-plan`.

Objetivo de esta re-auditoria: clasificar las herramientas CLI y offline usadas para capturas, analisis, validacion espectral, benchmarks, figuras, documentacion y configuracion. Estas tools conservan trazabilidad del TFG, pero no forman parte del loop esencial EEG->MIDI.

## 1. Criterio general

Las tools se dividen en cuatro grupos:

| Grupo | Papel | Entra en UML principal EEG->MIDI | Debe conservarse |
| --- | --- | --- | --- |
| Captura/control | Solicitan capturas o coordinan sesiones finales | No, salvo mencionar `CaptureManager` como modulo lateral | Si |
| Analisis/validacion offline | Recalculan calidad, bandas, features, reports | No | Si, por trazabilidad TFG |
| Benchmarks | Miden rendimiento real sobre placa/captura | No | Si, como evidencia de validacion |
| Documentacion/figuras | Generan reportajes y figuras finales | No | Si, mientras se redacta el TFG |
| Configuracion peligrosa | Cambia `ADS_DIAGNOSTIC_MODE` en firmware | No | Si, pero con mucho cuidado |

Regla para simplificacion futura:

```text
No borrar tools durante la version esencial.
Sacarlas del UML principal.
Documentarlas como herramientas offline de validacion y trazabilidad.
```

La unica herramienta que interactua con el backend vivo sin ser runtime es:

```text
python/tools/capture_eeg_quality.py
```

porque escribe `state/capture_request.json`, que el backend en ejecucion consume mediante `CaptureManager`.

## 2. Inventario final-v4 de herramientas

| Tool | Funcion | Entrada CLI | Archivos que lee | Archivos que escribe | Algoritmo/flujo | Estado final-v4 | Riesgo | Uso recomendado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `python/tools/capture_eeg_quality.py` | Solicitar captura real al backend vivo | `--condition`, `--duration`, `--notes`, `--timeout-extra`, `--no-wait` | `state/capture_status.json` | `state/capture_request.json` | Escribe request atomico y espera `completed/stopped/error` | Activa | Requiere App Lab corriendo en el mismo checkout | Capturas controladas. |
| `python/tools/analyze_eeg_capture.py` | Analizar una captura EEG | `capture_dir` | `metadata.json`, `eeg_timeseries.csv` | `quality_report.json/md`, `spectral_summary.csv` | Metricas tiempo, PSD multitaper via `DSPCore`, diagnostico | Activa | Offline; puede tardar | Analisis inicial de captura. |
| `python/tools/compare_eeg_captures.py` | Comparar ojos abiertos/cerrados | open_dir, closed_dir | Capturas/reports | Markdown/JSON comparativo | Ratios alpha y resumen | Activa | Depende de reports previos o recalcula | Comparacion cualitativa. |
| `python/tools/validate_spectral_features.py` | Validar features ventana a ventana | root/capture, `--channel`, `--window-sec`, `--hop-samples` | CSV captura, metadata | `windowed_bandpowers.csv`, `windowed_sonification_features.csv`, `psd_multitaper.csv`, reports | `DSPCore` + `compute_spectral_quality` + `SonificationFeatureAdapter` | Activa final-v4 | Coste alto; genera muchos artefactos | Validacion offline comparable con backend. |
| `python/tools/final_capture_session.py` | Gestionar sesion final EEG+musica | `init`, `capture`, `finish` | `state/snapshot.json`, `state/capture_status.json`, capturas temporales | plantilla sesion, logs, `music_snapshots.jsonl`, `music_notes.csv`, `music_capture_summary.json` | Coordina captura, log musical, mueve carpeta y analiza | Activa final-v4 | Mueve carpetas y lanza subprocesos | Sesiones finales multi-condicion. |
| `python/tools/build_final_capture_docs.py` | Generar documentacion final de capturas | args de sesion/root | Capturas finales y reports | Markdown/reportajes | Generacion documental final | Activa/offline | Puede tocar muchos docs | Usar con git limpio. |
| `python/tools/build_final_capture_docs_matplotlib.py` | Generar reportajes/figuras matplotlib estandar | final_root, subject/session, output dirs | `eeg_timeseries.csv`, `windowed_*`, `music_notes.csv`, reports | Figuras PNG y Markdown automaticos | Matplotlib Agg, escala EEG fija ±400 uV, controles final-v4 | Activa final-v4 | Depende de matplotlib; puede regenerar muchas figuras | Figuras/reportajes estandar. |
| `python/tools/build_capture06_enhanced_figures.py` | Figuras enhanced captura 06 | captura 06/output | CSV EEG, features, quality | PNG enhanced | Zoom, espectrogramas, figura combinada | Activa/offline | Es especifica de captura 06 | Figura candidata de memoria. |
| `python/tools/fix_final_capture_markdown_links.py` | Corregir rutas relativas de Markdown | docs/figures | Markdown generados | Markdown corregidos | Normaliza enlaces relativos | Activa puntual | Puede tocar muchos enlaces | Solo si GitHub no renderiza imagenes. |
| `python/tools/build_validation_docs.py` | Generar documentacion TFG antigua/consolidada | captures_dir/output_dir | Capturas, reports, git branches | `docs/validacion_tfg/**`, figures, tables | Agrega capturas, plots, tablas y docs | Historica/activa con cautela | Muy grande y mezclada | No usar sin revisar salida. |
| `python/tools/parse_mcu_bench_monitor.py` | Parsear Monitor MCU `[BENCH] EEG_MIDI` | log_path, out-csv/json/md, condition | Log copiado de Monitor/App Lab | CSV, JSON, Markdown | Regex de bloques BENCH, resumen estadistico | Activa final-v4 | Depende del formato exacto del Monitor | Benchmarks MCU reales. |
| `python/tools/set_ads_diagnostic_mode.py` | Cambiar macro ADS | modo/nombre | `sketch/sketch.ino` | `sketch/sketch.ino` | Reescribe `#define ADS_DIAGNOSTIC_MODE` | Activa peligrosa | Modifica firmware critico | Solo con commit claro y recompilacion. |
| `python/tools/test_led_matrix_visualizer.py` | Test manual LED | Ninguna | Modulo LED | Ninguno | Assertions sobre frame LED | Activa | No usa pytest | Prueba de subsistema lateral LED. |
| `benchmarks/benchmark_core.py` | Utilidades comunes benchmark | import | N/A | CSV/JSON/MD desde callers | Estadistica/exportacion | Activa final-v4 | Offline | Base benchmarks. |
| `benchmarks/benchmark_real_capture.py` | Benchmark Python/Linux con captura real | captura real | `eeg_timeseries.csv` | resultados benchmark | Reconstruye bloques y mide funciones criticas | Activa final-v4 | Resultados dependen de captura | Evidencia temporal Python. |
| `benchmarks/run_all_benchmarks.py` | Ejecutar todos los benchmarks Python/Linux | captura | benchmark scripts | results/reports | Orquestador benchmark | Activa final-v4 | Puede tardar | Benchmark final sobre captura real. |

## 3. Herramientas de captura y sesion

### `capture_eeg_quality.py`

Funciones principales:

| Funcion | Entrada | Salida | Que hace | Riesgo |
| --- | --- | --- | --- | --- |
| `_read_json` | path | dict | Lee status tolerante a errores | Bajo |
| `parse_args` | argv | Namespace | Define condicion, duracion, notas y espera | Bajo |
| `main` | CLI | exit code | Genera `request_id`, escribe `capture_request.json`, espera estado | Medio |

Esta herramienta no captura datos por si sola. Solo solicita al backend vivo que capture. Por tanto:

```text
App Lab debe estar corriendo.
CaptureManager debe estar integrado en BackendService.
El checkout debe coincidir con la app en ejecucion.
```

### `final_capture_session.py`

Funciones principales:

| Funcion | Entrada | Salida | Que hace | Riesgo |
| --- | --- | --- | --- | --- |
| `cmd_init` | subject/session/montage/model/ads_mode | Markdown sesion + contexto | Crea plantilla de sesion y log de contexto | Bajo/medio |
| `_snapshot_music_payload` | snapshot/status | dict | Extrae estado musical/snapshot para log | Bajo |
| `_music_logger` | stop_event,out_path,period | jsonl | Log periodico de snapshot musical | Medio si periodo demasiado bajo |
| `_discover_capture_dir` | condition | Path | Encuentra captura temporal mas reciente | Medio si nombres se solapan |
| `_unique_final_dir` | final_root/basename | Path | Evita pisar carpetas finales | Bajo |
| `_extract_music_notes` | jsonl,duration | CSV/JSON | Deduplica `music.recent_notes` y los alinea con tiempo de captura | Medio |
| `_append_capture_row` | sesion/captura | Markdown row | Añade fila a plantilla sesion | Bajo |
| `cmd_capture` | args captura | exit code | Lanza `capture_eeg_quality`, mueve carpeta, guarda musica, analiza | Alto: mueve carpetas y lanza subprocesos |
| `cmd_finish` | cierre sesion | Markdown | Añade hora fin/decision/comentario | Bajo |
| `build_parser/main` | argv | exit code | CLI multi-comando | Bajo |

Importante final-v4: esta tool fue clave para conservar no solo EEG, sino tambien:

```text
music_snapshots.jsonl
music_notes.csv
music_capture_summary.json
```

Estos archivos justifican la trazabilidad EEG->sonificacion->notas MIDI.

## 4. Herramientas de analisis espectral/offline

| Tool | Funcion | Entrada | Salida | Observacion final-v4 |
| --- | --- | --- | --- | --- |
| `analyze_eeg_capture.py` | `analyze` | captura | quality report + spectral summary | Analisis de calidad inicial. |
| `compare_eeg_captures.py` | `compare` | open/closed | comparacion JSON/MD | Usar con cautela si hay ruido de red o artefactos. |
| `validate_spectral_features.py` | `validate_capture` | captura/params | windowed CSV + reports | Recalcula bandpowers, quality gate y controles de sonificacion. |
| `validate_spectral_features.py` | `_write_aggregate` | reports | agregado multi-captura | Util para comparaciones, no runtime. |

Criterio importante:

```text
Las tools offline deben reutilizar DSPCore y spectral_quality.
No deben mantener una version paralela incompatible del DSP live.
```

Si se cambia `DSPCore`, bandas, ventana, quality gate o nombres de sonificacion, hay que revisar tambien estas tools.

## 5. Herramientas de figuras y documentacion

### `build_final_capture_docs_matplotlib.py`

Puntos final-v4 confirmados:

- usa `SONIF_CONTROLS` con nombres nuevos: `alpha_drive`, `beta_gamma_drive`, `rms_beta_activity`, `band_driven_density`, `spectral_register`, `alpha_stability`, `rms_band_velocity`, `band_note_probability`;
- usa `CONDITION_INFO` para `precheck_10s`, `eyes_open_rest_60s`, `eyes_closed_rest_60s`, `quiet_rest_60s`, `blink_artifact_30s`, `eyes_open_repeat_30s`;
- fija escala EEG estandar en ±400 uV para no aplastar la señal util con transitorios;
- usa Matplotlib Agg para generar PNG y Markdown;
- genera documentacion automatica auxiliar, no sustituye los reportajes manuales principales.

Riesgos:

- depende de Matplotlib instalado;
- puede regenerar muchos archivos;
- no activar `text.usetex=True` sin entorno LaTeX completo;
- no cambiar etiquetas descriptivas por notacion abstracta incomprensible para el TFG.

### `build_capture06_enhanced_figures.py`

Uso:

```text
Figuras reajustadas y espectrogramas de la captura 06, candidata principal para memoria.
```

No debe generalizarse como pipeline obligatorio de todas las capturas sin revisar.

### `build_validation_docs.py`

Se conserva por trazabilidad, pero es menos recomendable como herramienta principal actual porque mezcla:

- lectura de capturas;
- lectura de git/ramas;
- plots;
- tablas;
- generacion de varios documentos.

Para la fase final-v4, priorizar:

```text
reportajes_capturas_s01_20260528/
reportaje_sesion_final_s01_20260528.md
build_final_capture_docs_matplotlib.py
build_capture06_enhanced_figures.py
```

## 6. Herramientas de benchmarks

| Tool | Entrada | Salida | Uso final-v4 |
| --- | --- | --- | --- |
| `parse_mcu_bench_monitor.py` | Log Monitor/App Lab con `[BENCH] EEG_MIDI` | CSV/JSON/Markdown | Benchmarks MCU reales sin trafico Bridge adicional. |
| `benchmarks/benchmark_real_capture.py` | `eeg_timeseries.csv` real | Resultados Python/Linux | Mide coste de funciones criticas sobre captura real. |
| `benchmarks/run_all_benchmarks.py` | captura real | results/reports | Orquesta benchmarks Python. |
| `benchmarks/benchmark_core.py` | importado | estadistica/export | Base comun. |

Decision importante final-v4:

```text
No enviar metricas MCU por Bridge.
Copiar Monitor/App Lab y parsearlo offline.
```

Motivo: enviar benchmarks MCU por Bridge habria alterado el mismo canal que se queria medir.

## 7. Herramientas peligrosas o de configuracion

### `set_ads_diagnostic_mode.py`

Riesgo alto porque modifica firmware:

```text
sketch/sketch.ino
#define ADS_DIAGNOSTIC_MODE ...
```

Uso seguro:

1. Git limpio.
2. Cambiar modo con la tool.
3. Revisar diff.
4. Compilar/subir en App Lab.
5. Confirmar Monitor.
6. Capturar.
7. Volver al modo objetivo si procede.

Para capturas comparables con final-v4:

```text
ADS_DIAGNOSTIC_MODE=5
bias_ch1_only_loff_off
```

No usar esta tool dentro de la version esencial UML como flujo normal. Es herramienta de preparacion/diagnostico.

## 8. Clasificacion para version esencial UML

No incluir en UML principal:

```text
python/tools/*
benchmarks/*
docs/validacion_tfg/figures/*
```

Incluir solo como modulos laterales en documentacion:

```text
Capture tools
Offline validation tools
Benchmark tools
Documentation/figure generation tools
ADS diagnostic mode helper
```

Si se quiere mencionar una ruta minima de validacion:

```text
capture_eeg_quality.py
  -> CaptureManager en backend vivo
  -> eeg_timeseries.csv
  -> validate_spectral_features.py
  -> reports/figures
```

Pero esa ruta no es el runtime EEG->MIDI.

## 9. Hallazgos para simplificacion futura

| Hallazgo | Impacto | Recomendacion futura |
| --- | --- | --- |
| `build_validation_docs.py` es muy grande y mezcla muchas responsabilidades | Dificulta mantenimiento | Mantener como historico/auxiliar; priorizar tools finales mas especificas. |
| `build_final_capture_docs_matplotlib.py` contiene estilo, lectura, plots y escritura | Funciona, pero es grande | No refactorizar antes de cerrar TFG; si se toca, hacerlo por funciones pequenas. |
| `final_capture_session.py` mueve carpetas y lanza subprocesos | Util pero delicado | Usarlo con git limpio y backups; no integrarlo en runtime esencial. |
| `validate_spectral_features.py` recalcula DSP y sonificacion offline | Muy util para trazabilidad | Mantener sincronizado con `DSPCore` y nombres final-v4. |
| `set_ads_diagnostic_mode.py` modifica firmware critico | Riesgo alto | Mantener fuera de UML principal y documentar como herramienta peligrosa. |
| `parse_mcu_bench_monitor.py` depende del formato del Monitor | Si cambia `bench.h`, puede romper parser | Mantener tests/log de ejemplo si se modifica bench output. |
| Tools de figuras dependen de Matplotlib/entorno | Puede fallar en placa o Windows si falta entorno | Ejecutarlas preferentemente en entorno controlado. |

## 10. Riesgos principales

- Confundir tools offline con runtime real.
- Borrar tools o reports y perder trazabilidad del TFG.
- Cambiar `DSPCore` sin actualizar `validate_spectral_features.py` y reportes.
- Cambiar nombres de sonificacion sin regenerar CSV/figuras.
- Cambiar formato de captura sin actualizar analyzers.
- Ejecutar `set_ads_diagnostic_mode.py` y olvidar recompilar/subir firmware.
- Ejecutar generadores de docs con git sucio y sobreescribir reportajes manuales.
- Usar benchmarks sinteticos como evidencia final en vez de capturas reales.

## 11. Pruebas minimas antes de aceptar cambios en tools

Si en el futuro se modifica una tool:

1. `python3 -m py_compile python/tools/*.py benchmarks/*.py`.
2. Ejecutar la tool sobre una copia de una captura real, no sobre la unica carpeta final.
3. Revisar `git diff --stat` antes de commit.
4. Revisar que no se eliminan figuras/reportajes manuales.
5. Si se modifica `validate_spectral_features.py`, comparar una captura conocida antes/despues.
6. Si se modifica `parse_mcu_bench_monitor.py`, parsear el log benchmark final ya versionado.
7. Si se modifica `final_capture_session.py`, probar con una captura corta de prueba, no con sesion final.
8. Si se modifica `set_ads_diagnostic_mode.py`, revisar diff de `sketch.ino` y compilar.
9. Si se modifica generacion Matplotlib, confirmar que GitHub renderiza los enlaces Markdown.
10. Mantener benchmarks, capturas, reports y figuras versionados.

## 12. Recomendacion final

Para la fase de simplificacion/UML:

```text
Mantener runtime limpio.
No incorporar tools al flujo principal.
Conservar tools como respaldo de validacion.
Usar docs/validacion_tfg como evidencia final.
Usar tools solo para reproducir capturas, benchmarks y figuras.
```

La version esencial debe explicar el sistema funcionando. Las tools explican como se valido y documento ese sistema.
