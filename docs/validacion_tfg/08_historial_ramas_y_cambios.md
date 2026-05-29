# 08. Historial de ramas y cambios realizados durante la validacion - final-v4

## 1. Objetivo del documento

Este documento resume la evolucion tecnica del proyecto EEG-MIDI durante la fase de validacion, benchmarks, capturas finales y consolidacion documental final-v4.

No sustituye al historial Git. Su funcion es traducir las ramas y commits en decisiones de ingenieria justificables en el TFG:

```text
validacion de adquisicion -> validacion DSP/quality gate -> benchmarks reales -> capturas finales -> integracion final-v4 -> plan de simplificacion futura
```

La version anterior de este documento fue generada automaticamente por `python/tools/build_validation_docs.py` y estaba centrada en la rama historica:

```text
diagnosis/sonificacion-atenuacion-artefactos
```

Esa informacion sigue siendo util, pero ahora debe leerse como una fase intermedia. La referencia final del bloque de resultados es:

```text
firmware-final-v4
```

con documentacion de trabajo actual en:

```text
refactor/essential-eeg-midi-plan
```

## 2. Lectura general de la evolucion

El proyecto avanzo por capas para no mezclar problemas:

1. Validar que el ADS1299 y el transporte digital funcionaban.
2. Separar problemas de ADC/SPI/Bridge de problemas de electrodos.
3. Comparar montajes y definir el modo CH1-only con BIAS/RLD.
4. Validar DSP multitaper, bandpowers y features offline/live.
5. Anadir quality gate para proteger la sonificacion de artefactos.
6. Validar MIDI fisico y controles musicales.
7. Medir benchmarks reales en placa.
8. Tomar capturas finales con EEG y musica persistida.
9. Consolidar todo en una rama final-v4.
10. Preparar una futura simplificacion para UML y memoria.

La decision importante es que `mixed_states` no es la sesion final principal. Es una captura intermedia valiosa para estudiar estados, artefactos, quality gate y DSP. La sesion final reportable es `s01_20260528`.

## 3. Ramas historicas de diagnostico

| Rama | Papel | Estado actual |
| --- | --- | --- |
| `captura-datos-dsp` | Base comun para validar adquisicion, CH1-only, DSP y modo `bias_ch1_only_loff_off`. | Historica util. |
| `diagnosis/sonificacion-con-artefactos` | Rama de control sin atenuacion de artefactos. | Historica, util para comparacion A/B. |
| `diagnosis/sonificacion-atenuacion-artefactos` | Rama con `spectral_quality_score` y quality gate. | Historica, antecedente directo de final-v4. |

Estas ramas permitieron separar dos preguntas:

```text
1. La senal y el DSP funcionan?
2. La sonificacion necesita proteccion frente a artefactos?
```

La respuesta obtenida fue que la adquisicion y el DSP eran suficientemente utiles, pero la sonificacion necesitaba una capa de calidad para no traducir directamente ventanas artefactadas en eventos musicales.

## 4. Evolucion tecnica por etapas

| Etapa | Rama/estado representativo | Cambio tecnico | Motivo | Evidencia generada |
| --- | --- | --- | --- | --- |
| Captura requestable | primeras ramas de captura | `capture_eeg_quality.py` permite solicitar capturas al backend vivo. | Guardar CSV/metadata en lugar de depender de observacion visual. | `eeg_timeseries.csv`, `metadata.json`, `quality_report.*`. |
| Diagnostico ADS1299 | fases `shorted_inputs` / test interno | Modos diagnosticos para aislar ADC/SPI/escala. | Separar problemas digitales de problemas de electrodos. | Capturas diagnosticas, RMS bajo en shorted inputs. |
| Auditoria de registros ADS1299 | documentacion de auditoria | Revision de CONFIG1/CONFIG3, bits fijos/reservados, BIAS/RLD. | Alinear firmware con datasheet y evitar configuraciones ambiguas. | `docs/03_subsistemas_final_v4/03_subsistemas_final_v4/ads1299_register_audit_bias_drl.md`. |
| BIAS/RLD y CH1-only | `captura-datos-dsp` | Modo `bias_ch1_only_loff_off`. | Reducir influencia de canales no usados y estabilizar montaje. | Capturas ear-EEG/Fp1-Fp2. |
| Metricas por ventanas | herramientas de calidad | RMS mediano, P95, best window, fraccion de artefactos. | No rechazar capturas completas si existen ventanas utiles. | `quality_report.md/json`. |
| Validacion espectral offline | herramientas DSP | PSD multitaper, bandpowers por ventana, reports espectrales. | Comprobar reproducibilidad de features con CSV reales. | `windowed_bandpowers.csv`, `spectral_validation_report.*`. |
| Captura `mixed_states` | `diagnosis/sonificacion-atenuacion-artefactos` | Sesion con ojos abiertos/cerrados, mandibula, recuperacion y parpadeo/frente. | Estudiar artefactos y cambios de estado en una misma adquisicion. | Figuras por estado en docs `03` y `04`. |
| Quality gate | rama de atenuacion | `compute_spectral_quality()` integrado con backend/sonificacion. | Atenuar o bloquear ventanas malas antes de producir musica. | `docs/03_subsistemas_final_v4/03_subsistemas_final_v4/diseno_spectral_quality_score.md`. |
| Alineacion offline/live | validadores offline | Offline aplica logica comparable al backend live. | Hacer comparables reports, features y snapshots. | `windowed_sonification_features.csv`. |
| MIDI fisico | final-v3/final-v4 | `midi_bytes`, `Serial1`/D1 y TX invertido. | Validar salida MIDI real en placa. | `docs/03_subsistemas_final_v4/03_subsistemas_final_v4/midi_out_inverted_tx_validation.md`. |
| Benchmarks reales | `docs/final-v3-audit-update` | Medicion MCU/Python sobre placa y capturas reales. | Cuantificar margen temporal real. | `09_benchmarks_rendimiento_placa.md`, `benchmarks/results`, `benchmarks/reports`. |
| Capturas finales | `docs/capture-protocol` | Sesion `s01_20260528` con EEG, calidad, features y musica persistida. | Evidencia final de integracion EEG-MIDI real. | `10_resultados_captura_final_laboratorio.md`, reportajes y figuras. |
| Integracion final | `bench-y-capturas` / `firmware-final-v4` | Fusion de benchmarks y capturas finales. | No perder resultados de ninguna de las dos ramas. | Rama final integrada. |
| Plan de simplificacion | `refactor/essential-eeg-midi-plan` | Auditoria documental para futura version esencial UML. | Preparar reduccion de codigo sin romper final-v4. | Documentos actualizados y notas de simplificacion. |

## 5. Ramas de benchmarks

La rama de benchmarks procedia de la documentacion final-v3 y quedo orientada a medir rendimiento temporal real en placa.

Elementos principales:

```text
docs/validacion_tfg/09_benchmarks_rendimiento_placa.md
benchmarks/benchmark_core.py
benchmarks/benchmark_real_capture.py
benchmarks/run_all_benchmarks.py
python/tools/parse_mcu_bench_monitor.py
benchmarks/results/
benchmarks/reports/
```

Decision importante:

```text
No anadir un canal Bridge extra para metricas MCU.
Usar el Monitor/App Lab y parsearlo offline.
```

Motivo: medir `Bridge.notify("eeg_block_uV")` sin meter trafico adicional en el mismo puente que se queria evaluar.

Conclusiones principales:

- El margen Python/Linux frente al hop de 256 ms es amplio.
- El margen MCU frente al bloque de 32 ms es suficiente.
- El coste dominante del MCU es `Bridge.notify`, no el filtrado.
- No se observaron drops relevantes en la prueba reportada.

## 6. Ramas de capturas finales

La rama de capturas finales documento el protocolo experimental y la sesion `s01_20260528`.

Elementos principales:

```text
docs/04_protocolos_captura/protocolo_capturas_multiusuario.md
docs/04_protocolos_captura/templates/plantilla_sesion_sujeto.md
docs/04_protocolos_captura/sesiones_captura/
docs/validacion_tfg/10_resultados_captura_final_laboratorio.md
docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md
docs/validacion_tfg/reportajes_capturas_s01_20260528/
docs/validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib/
docs/validacion_tfg/figures/capturas_finales_s01_20260528_enhanced/
```

Sesion final:

```text
SUBJECT=s01
SESSION=20260528
MONTAGE=ear_eeg_ch1_only
ADS_MODE=bias_ch1_only_loff_off
ADS_DIAGNOSTIC_MODE=5
MODEL=modelo_captura_final
```

La sesion final valida integracion tecnica, no EEG clinica limpia. La lectura correcta es:

```text
La sesion contiene artefactos y ruido.
Aun asi, valida adquisicion, persistencia de datos, DSP, quality gate, controles de sonificacion y notas registradas.
```

## 7. Rama integrada final-v4

La rama `firmware-final-v4` se creo como estado integrado con:

- documentacion final-v4;
- benchmarks reales en placa;
- capturas finales con reportajes;
- figuras de validacion;
- controles de sonificacion reportables;
- MIDI fisico validado;
- protocolo de adquisicion final-v4.

Tambien se creo una rama gemela `bench-y-capturas` para conservar el estado fusionado de benchmarks y capturas antes de continuar modificaciones.

Papel de cada rama:

| Rama | Papel |
| --- | --- |
| `bench-y-capturas` | Rama de fusion documental y artefactos de benchmarks + capturas. |
| `firmware-final-v4` | Rama final integrada sobre la que se construyen futuras modificaciones. |
| `refactor/essential-eeg-midi-plan` | Rama actual de auditoria/documentacion para preparar simplificacion UML. |

## 8. Estado de los documentos de validacion

| Documento | Estado final-v4 |
| --- | --- |
| `00_resumen_validacion.md` | Vigente como indice de validacion final-v4. |
| `01_validacion_captura_datos_ads1299.md` | Vigente, valida ADS1299/cadena digital. |
| `02_validacion_montaje_electrodos_bias_rld.md` | Vigente, justifica montaje final. |
| `03_validacion_calidad_senal_real.md` | Vigente, usa `mixed_states` como estudio intermedio por estado. |
| `04_validacion_dsp_multitaper.md` | Vigente, valida multitaper y comparacion por estado. |
| `05_validacion_bandas_eeg_y_features.md` | Vigente, conecta bandas con features de sonificacion. |
| `06_conclusiones_para_sonificacion.md` | Vigente, resume decisiones musicales final-v4. |
| `07_protocolo_final_adquisicion.md` | Vigente, sustituye protocolo automatico historico. |
| `08_historial_ramas_y_cambios.md` | Vigente, este documento. |
| `09_benchmarks_rendimiento_placa.md` | Vigente, benchmarks reales en placa. |
| `10_resultados_captura_final_laboratorio.md` | Vigente, resultados de sesion final `s01_20260528`. |

## 9. Que queda como historico

Quedan como historicos o antecedentes:

- ramas `diagnosis/*`;
- rama `captura-datos-dsp`;
- captura `final_atenuacion_artefactos_mixed_states` como sesion intermedia;
- nombres antiguos de sonificacion (`activity`, `calmness`, `tension`, etc.);
- comentarios/documentos que hablaban de sonificacion pendiente;
- figuras antiguas no insertadas en el relato principal.

No se eliminan porque explican decisiones tecnicas y sirven para justificar el proceso experimental.

## 10. Que queda pendiente para fases futuras

Pendiente para fases posteriores, fuera de esta revision documental:

- simplificar WebUI sin perder resolucion temporal ni funcionalidad;
- reducir herramientas/diagnosticos no esenciales en una rama UML;
- separar codigo esencial de benchmarks/capturas/reportes offline;
- limpiar aliases legacy internos de sonificacion si no rompen contratos;
- decidir que figuras pasan a memoria y cuales quedan como anexo;
- medir latencia fisica end-to-end EEG -> MIDI OUT si se dispone de instrumentacion.

## 11. Conclusion

El historial de ramas muestra una evolucion ordenada: primero se valido la adquisicion y el DSP, despues se introdujo el quality gate, posteriormente se midieron benchmarks reales y finalmente se tomaron capturas finales con musica persistida.

La rama `firmware-final-v4` representa el estado integrado defendible para el TFG. La rama `refactor/essential-eeg-midi-plan` debe entenderse como una fase posterior de preparacion para simplificar y explicar el sistema, no como sustituto de la evidencia final-v4.





