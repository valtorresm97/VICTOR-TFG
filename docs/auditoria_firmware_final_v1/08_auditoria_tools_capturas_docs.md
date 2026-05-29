# 08. Auditoria tools, capturas y documentacion - final-v4

## 1. Objetivo

Este documento describe las herramientas CLI, capturas, validaciones offline, benchmarks, reportajes y figuras del proyecto EEG-MIDI. Su objetivo no es definir el runtime principal, sino explicar la capa de validacion y documentacion que permite defender el sistema en el TFG.

La auditoria funcion por funcion mas exhaustiva esta en:

```text
docs/auditoria_codigo_detallada/08_tools_cli_funcion_por_funcion.md
```

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Separacion entre runtime y herramientas

El flujo runtime principal es:

```text
ADS1299 -> firmware -> eeg_block_uV -> backend -> DSP -> quality gate -> sonificacion -> MIDI fisico
```

Las tools y documentos de esta carpeta pertenecen a otro plano:

```text
capturar datos
validar senal
recalcular features offline
generar reportes
generar figuras
parsear benchmarks
documentar sesiones
```

Por tanto:

```text
Las tools no forman parte del UML principal EEG->MIDI.
Las tools si son esenciales para trazabilidad, metodologia y redaccion TFG.
```

## 3. Tools CLI principales final-v4

| Tool | Uso | Entrada | Salida | Ejecuta en | Estado final-v4 | Comentario |
| --- | --- | --- | --- | --- | --- | --- |
| `python/tools/capture_eeg_quality.py` | Solicitar captura real a la app corriendo. | `--condition`, `--duration`, `--notes` | `state/capture_request.json`, espera `capture_status.json`. | Shell normal + App Lab corriendo | Activa | No captura ni calcula quality gate; solo solicita captura al backend vivo. |
| `python/tools/final_capture_session.py` | Coordinar sesion final multi-condicion con EEG + musica. | `init`, `capture`, `finish` | Sesion Markdown, capturas movidas, `music_snapshots.jsonl`, `music_notes.csv`, summary. | Shell normal + App Lab corriendo | Activa final-v4 | Herramienta clave de la sesion `s01_20260528`. |
| `python/tools/analyze_eeg_capture.py` | Analizar una captura CSV. | Directorio de captura | `quality_report.*`, `spectral_summary.csv`, `psd_multitaper.csv`. | Shell normal | Activa | Analisis de calidad y espectro. |
| `python/tools/compare_eeg_captures.py` | Comparar dos capturas, p.ej. ojos abiertos/cerrados. | Dos dirs de captura | Markdown/json comparativo. | Shell normal | Activa | Usar con cautela si hay ruido/artefactos. |
| `python/tools/validate_spectral_features.py` | Recalcular/validar bandpowers, quality y sonificacion por ventanas. | Captura o root de capturas | `windowed_bandpowers.csv`, `windowed_sonification_features.csv`, reports. | Shell normal | Activa final-v4 | Compatible con nombres nuevos de sonificacion. |
| `python/tools/build_final_capture_docs.py` | Generar documentacion final de capturas. | Capturas finales | Markdown/reportajes. | Shell normal | Activa/offline | Usar con git limpio. |
| `python/tools/build_final_capture_docs_matplotlib.py` | Generar figuras y reportajes automaticos con Matplotlib. | Capturas finales | PNG + Markdown automaticos. | Shell con Matplotlib | Activa final-v4 | Genera figuras estandar por captura. |
| `python/tools/build_capture06_enhanced_figures.py` | Generar figuras enhanced de la captura 06. | Captura 06 | PNG enhanced/espectrogramas. | Shell con Matplotlib/SciPy | Activa final-v4 | Figura candidata para memoria. |
| `python/tools/fix_final_capture_markdown_links.py` | Corregir rutas relativas de imagenes en Markdown. | Docs generados | Markdown corregido. | Shell normal | Activa puntual | Usar si GitHub no renderiza imagenes. |
| `python/tools/parse_mcu_bench_monitor.py` | Parsear Monitor MCU `[BENCH] EEG_MIDI`. | Log Monitor/App Lab | CSV/JSON/Markdown benchmark MCU. | Shell normal | Activa final-v4 | Evita enviar metricas por Bridge. |
| `python/tools/build_validation_docs.py` | Construir docs, tablas y figuras TFG antiguas/consolidadas. | `captures/`, `docs/validacion_tfg` | Markdown, CSV, PNG/PDF. | Shell con NumPy/SciPy/Matplotlib | Historica/activa con cautela | Monolitica; priorizar tools finales especificas. |
| `python/tools/set_ads_diagnostic_mode.py` | Cambiar macro `ADS_DIAGNOSTIC_MODE`. | Modo textual | Modifica `sketch/sketch.ino`. | Shell normal | Activa, riesgosa | Requiere revisar diff, compilar y subir firmware. |
| `python/tools/test_led_matrix_visualizer.py` | Tests de mapeo LED sin hardware. | Ninguna | Prints/asserts. | Shell normal | Activa lateral | LED no es flujo principal. |
| `benchmarks/benchmark_real_capture.py` | Benchmark Python/Linux sobre captura real. | `eeg_timeseries.csv` | JSON/CSV/Markdown de tiempos. | Shell normal | Activa final-v4 | Evidencia temporal Python. |
| `benchmarks/run_all_benchmarks.py` | Orquestar benchmarks Python. | Captura real | Resultados/reports. | Shell normal | Activa final-v4 | Usar con captura real, no sintetica. |
| `benchmarks/benchmark_core.py` | Utilidades comunes de benchmark. | Import | Estadistica/export. | Shell normal | Activa final-v4 | Base comun. |

## 4. Capturas finales y datos principales

La evidencia experimental mas actual ya no es la serie antigua de capturas individuales de mayo. La sesion final documentada es:

```text
s01_20260528
```

Configuracion de la sesion final:

```text
SUBJECT=s01
SESSION=20260528
MONTAGE=ear_eeg_ch1_only
MODEL=modelo_captura_final
ADS_MODE=bias_ch1_only_loff_off
ADS_DIAGNOSTIC_MODE=5
FINAL_ROOT="captures/capturas finales"
```

Condiciones principales conservadas:

| Orden | Condicion | Uso dentro del TFG |
| --- | --- | --- |
| `00` | `precheck_10s` | Verificacion tecnica previa. |
| `01` | `eyes_open_rest_60s` | Ojos abiertos. |
| `02` | `eyes_closed_rest_60s` | Ojos cerrados. |
| `03` | `quiet_rest_60s` | Reposo quieto. |
| `04` | `blink_artifact_30s` | Artefacto fisiologico controlado por parpadeo. |
| `06` | `eyes_open_repeat_30s` | Mejor candidata para figura principal, con transitorio documentado. |

No se conserva como captura final principal una condicion `05_jaw_artifact_30s`. Si aparece en planes/protocolos antiguos, debe tratarse como condicion prevista/no disponible en la sesion final documentada.

## 5. Estructura de una captura final

Cada captura final completa puede incluir:

```text
eeg_timeseries.csv
metadata.json
quality_report.json
quality_report.md
spectral_validation_report.json
spectral_validation_report.md
spectral_summary.csv
psd_multitaper.csv
windowed_bandpowers.csv
windowed_sonification_features.csv
music_snapshots.jsonl
music_notes.csv
music_capture_summary.json
```

Lectura:

- `eeg_timeseries.csv`: senal temporal y status por muestra.
- `metadata.json`: configuracion, git, duracion, entorno y resumen.
- `quality_report.*`: analisis de calidad de captura.
- `spectral_validation_report.*`: validacion espectral offline.
- `windowed_bandpowers.csv`: bandas por ventanas.
- `windowed_sonification_features.csv`: controles de sonificacion final-v4 por ventana.
- `music_snapshots.jsonl`: snapshots musicales durante captura.
- `music_notes.csv`: notas deduplicadas y alineadas con tiempo de captura.
- `music_capture_summary.json`: resumen musical.

Esto permite defender trazabilidad:

```text
senal EEG -> features -> quality gate -> controles de sonificacion -> notas MIDI
```

## 6. Reportajes y figuras final-v4

Documentos principales de resultados reales:

```text
docs/validacion_tfg/10_resultados_captura_final_laboratorio.md
docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md
docs/validacion_tfg/reportajes_capturas_s01_20260528/
```

Figuras estandar:

```text
docs/validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib/
```

Figuras enhanced de captura 06:

```text
docs/validacion_tfg/figures/capturas_finales_s01_20260528_enhanced/06_eyes_open_repeat_30s/
```

Carpeta automatica auxiliar:

```text
docs/validacion_tfg/capturas_finales_s01_20260528_matplotlib/
```

Carpeta principal narrativa por captura:

```text
docs/validacion_tfg/reportajes_capturas_s01_20260528/
```

Criterio:

```text
reportajes_capturas_s01_20260528/ = lectura principal para TFG
capturas_finales_s01_20260528_matplotlib/ = salida generada/reproducible
figures/ = recursos visuales
```

## 7. Benchmarks final-v4

Los benchmarks finales se documentan principalmente en:

```text
docs/validacion_tfg/09_benchmarks_rendimiento_placa.md
benchmarks/results/
benchmarks/reports/
```

### MCU / firmware

El firmware imprime:

```text
[BENCH] EEG_MIDI
```

por Monitor/App Lab. El log se copia y se parsea offline con:

```text
python/tools/parse_mcu_bench_monitor.py
```

Decision importante:

```text
No se enviaron metricas MCU por Bridge.
```

Motivo: no contaminar el canal `Bridge.notify("eeg_block_uV")` que se estaba midiendo.

### Python / Linux

Los benchmarks Python se ejecutan sobre captura real:

```text
benchmarks/benchmark_real_capture.py
benchmarks/run_all_benchmarks.py
```

Funcion clave:

```text
EEGSignalProcessor.compute_live_features()
```

contra presupuesto:

```text
FEATURE_HOP_SAMPLES / FS_HZ = 64 / 250 = 256 ms
```

## 8. Documentos relacionados

| Documento | Estado final-v4 | Observacion |
| --- | --- | --- |
| `docs/protocolo_capturas_multiusuario.md` | Vigente | Protocolo repetible multiusuario. |
| `docs/templates/plantilla_sesion_sujeto.md` | Vigente | Plantilla de sesion simplificada. |
| `docs/sesiones_captura/20260528_s01_sesion.md` | Vigente | Sesion final real. |
| `docs/sesiones_captura/20260528_s00_home_test_sesion.md` | Vigente como prueba previa | Validacion en casa, no evidencia principal. |
| `docs/diseno_spectral_quality_score.md` | Vigente con cautela | Base conceptual del quality gate. |
| `docs/midi_out_inverted_tx_validation.md` | Vigente | Validacion MIDI fisico TX invertido. |
| `docs/ads1299_diagnostic_modes.md` | Vigente tecnico | Define modos ADS 0..5. |
| `docs/ads1299_register_audit_bias_drl.md` | Vigente tecnico | Complementa registros/BIAS/DRL. |
| `docs/auditoria_captura_datos.md` | Auditoria previa | Util historicamente; contrastar con final-v4. |
| `docs/resultados_validacion_espectral_capturas.md` | Historico/parcial | Puede contener capturas previas; no debe sustituir sesion final s01. |
| `docs/resultados_validacion_dsp_mixta.md` | Historico/parcial | Util como antecedente. |
| `docs/validacion_tfg/00..08` | Documentacion previa | Revisar contra 09/10/reportajes final-v4. |

## 9. Diferencia entre capturas antiguas y capturas finales

Las capturas antiguas como:

```text
post_configfix_shorted_inputs
ear_eeg_ch1_only_eyes_open_60s
fp1_fp2_ch1_only_eyes_closed_60s
final_atenuacion_artefactos_mixed_states
```

son utiles como historial de desarrollo, diagnostico o validacion intermedia. Sin embargo, para la memoria final deben quedar subordinadas a:

```text
benchmarks reales final-v4
sesion final s01_20260528
captura 06 enhanced como figura candidata
reportajes finales
```

La captura `20260524-122200_final_atenuacion_artefactos_mixed_states` ya no debe describirse como captura final principal. Puede mencionarse como antecedente de ajuste del quality gate.

## 10. Riesgos documentales

- Confundir tools offline con runtime principal.
- Presentar capturas antiguas como evidencia final principal.
- Borrar reportajes/figuras y perder trazabilidad TFG.
- Regenerar figuras con entorno Matplotlib/LaTeX problemático y degradar salidas correctas.
- Cambiar nombres de sonificacion sin regenerar CSV/figuras.
- Cambiar DSP y no recalcular validaciones offline.
- Ejecutar `set_ads_diagnostic_mode.py` y olvidar recompilar/subir firmware.
- Usar benchmarks sinteticos como evidencia final.
- Mezclar capturas de casa con sesion final de laboratorio sin etiquetado claro.

## 11. Reglas de uso seguro

Antes de ejecutar tools que escriben muchos archivos:

```bash
git status --short
```

Debe estar limpio o los cambios deben estar claramente controlados.

Reglas:

1. Ejecutar generadores sobre copias o rutas controladas si hay duda.
2. Revisar `git diff --stat` despues.
3. No sobrescribir reportajes manuales sin revisar.
4. No activar `text.usetex=True` en Matplotlib si el entorno LaTeX no esta completo.
5. Si se modifica DSP/quality/sonificacion, recalcular una captura real y revisar diferencias.
6. Si se modifica benchmark parser, parsear un log final ya versionado.
7. Si se modifica capture session, probar con captura corta antes de una sesion real.

## 12. Relacion con futura version esencial/UML

En UML principal no deben aparecer:

```text
python/tools/*
benchmarks/*
docs/validacion_tfg/figures/*
report generators
```

Como laterales de validacion pueden aparecer:

```text
CaptureManager
capture_eeg_quality.py
final_capture_session.py
validate_spectral_features.py
parse_mcu_bench_monitor.py
build_final_capture_docs_matplotlib.py
```

La version esencial debe explicar el sistema funcionando. Las tools explican como se valido y documento ese sistema.

## 13. Conclusion

La capa de tools, capturas y documentacion final-v4 cumple una funcion distinta al runtime. Permite conservar evidencia de:

```text
adquisicion real
calidad de senal
features espectrales
quality gate
sonificacion
notas MIDI
benchmarks MCU/Python
figuras y reportajes
```

Para el TFG, esta capa es fundamental como metodologia y resultados. Para la futura version esencial/UML, debe mantenerse como soporte lateral y no mezclarse con el flujo principal EEG->MIDI.
