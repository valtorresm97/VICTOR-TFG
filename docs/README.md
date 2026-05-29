# Indice de documentacion

Este indice define que documentos deben leerse como fuente principal del estado integrado `firmware-final-v4` y cuales quedan como historicos. No se borra documentacion tecnica: se clasifica para evitar confundir versiones antiguas con el estado actual.

Rama documental actual:

```text
refactor/essential-eeg-midi-plan
```

Rama base integrada:

```text
firmware-final-v4
```

## 1. Entrada principal final-v4

| Documento | Estado | Uso recomendado |
| --- | --- | --- |
| `configuracion_final_v4.md` | Principal final-v4 | Resumen consolidado de arquitectura, firmware, streaming, Python backend, DSP, spectral quality, sonificacion, MIDI fisico, WebUI, capturas finales y benchmarks reales. |
| `auditoria_final_v4_fase1_2.md` | Auditoria de arranque final-v4 | Lectura previa para entender que se reviso en fases 1 y 2, que incoherencias se detectaron y que queda pendiente para fase 3. |

Lectura recomendada inicial:

```text
1. docs/configuracion_final_v4.md
2. docs/auditoria_final_v4_fase1_2.md
3. docs/validacion_tfg/09_benchmarks_rendimiento_placa.md
4. docs/validacion_tfg/10_resultados_captura_final_laboratorio.md
5. docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md
```

## 2. Validacion TFG final-v4

La carpeta `validacion_tfg/` contiene la evidencia principal para la memoria: benchmarks reales, capturas finales, reportajes, figuras y tablas. Si un report historico contradice estos documentos, prevalece la documentacion final-v4 listada aqui.

| Documento/carpeta | Estado | Uso recomendado |
| --- | --- | --- |
| `validacion_tfg/09_benchmarks_rendimiento_placa.md` | Principal | Evidencia temporal real en placa UNO Q/Linux: benchmarks Python/Linux, benchmarks MCU, margen de 256 ms y 32 ms. |
| `validacion_tfg/10_resultados_captura_final_laboratorio.md` | Principal | Resumen tecnico de la sesion final `s01_20260528`, calidad de captura, artefactos y datos musicales registrados. |
| `validacion_tfg/reportaje_sesion_final_s01_20260528.md` | Principal | Relato tecnico global de la sesion final para TFG. |
| `validacion_tfg/reportajes_capturas_s01_20260528/` | Principal por captura | Lectura individual de prechecks y condiciones `01`, `02`, `03`, `04` y `06`. |
| `validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib/` | Figuras generadas | Figuras estandar por captura: EEG temporal, bandpowers, controles, calidad y notas. |
| `validacion_tfg/figures/capturas_finales_s01_20260528_enhanced/` | Figuras reajustadas | Figuras enhanced de la captura 06, candidata principal para memoria. |
| `validacion_tfg/capturas_finales_s01_20260528_matplotlib/` | Documentacion generada | Salida automatica auxiliar reproducible. |

## 3. Protocolo experimental y plantillas

| Documento | Estado | Uso recomendado |
| --- | --- | --- |
| `04_protocolos_captura/protocolo_capturas_multiusuario.md` | Activo | Procedimiento repetible para capturas EEG-MIDI multiusuario. |
| `04_protocolos_captura/templates/plantilla_sesion_sujeto.md` | Activo | Plantilla para documentar sesiones por sujeto. |
| `04_protocolos_captura/sesiones_captura/` | Activo | Sesiones documentadas, incluyendo prueba de casa y sesion final de laboratorio. |

## 4. Auditorias tecnicas activas

La familia `02_auditoria_codigo/funcion_por_funcion/` sigue siendo muy valiosa para entender el sistema funcion por funcion. Puede contener referencias a final-v3 o ramas antiguas, pero su contenido tecnico debe conservarse mientras se revisa la organizacion documental.

| Carpeta/documento | Estado | Uso recomendado |
| --- | --- | --- |
| `02_auditoria_codigo/funcion_por_funcion/00_inventario_actual.md` | Activo con posible terminologia historica | Inventario del repo y bloques funcionales. |
| `02_auditoria_codigo/funcion_por_funcion/01_firmware_funcion_por_funcion.md` | Activo | Firmware, streaming, filtros, bench, MIDI y LED. |
| `02_auditoria_codigo/funcion_por_funcion/02_ads1299_spi_driver.md` | Activo | ADS1299, SPI, registros y contratos criticos. |
| `02_auditoria_codigo/funcion_por_funcion/03_python_backend_funcion_por_funcion.md` | Activo | Backend, receiver, contratos, capturas y WebUI. |
| `02_auditoria_codigo/funcion_por_funcion/04_dsp_eeg_funcion_por_funcion.md` | Activo | DSP, features y quality score. |
| `02_auditoria_codigo/funcion_por_funcion/05_sonificacion_midi_funcion_por_funcion.md` | Activo | Sonificacion, musica, MIDI scheduler y transporte. |
| `02_auditoria_codigo/funcion_por_funcion/06_led_matrix_funcion_por_funcion.md` | Activo secundario | LED matrix y piano scroll. |
| `02_auditoria_codigo/funcion_por_funcion/07_web_server_assets_funcion_por_funcion.md` | Activo | Web server, endpoints y assets HTML/JS/CSS. |
| `02_auditoria_codigo/funcion_por_funcion/08_tools_cli_funcion_por_funcion.md` | Activo | Tools offline, capturas, validacion y documentacion. |
| `02_auditoria_codigo/funcion_por_funcion/09_mapa_contratos_entre_modulos.md` | Activo critico | Contratos productor/consumidor que no deben romperse. |
| `02_auditoria_codigo/funcion_por_funcion/10_mapa_funciones_criticas.md` | Activo critico | Criticidad y pruebas minimas. |
| `02_auditoria_codigo/funcion_por_funcion/11_hallazgos_para_simplificacion_futura.md` | Activo para fase UML | Base para futura `propuesta_version_esencial_uml.md`. |

## 5. Documentacion activa de subsistemas

Estos documentos ya han sido revisados en la rama `refactor/essential-eeg-midi-plan` para aclarar su relacion con final-v4. Siguen siendo documentos activos, pero no sustituyen a `configuracion_final_v4.md` ni a la evidencia de `validacion_tfg/`.

| Documento | Estado | Uso recomendado |
| --- | --- | --- |
| `ads1299_diagnostic_modes.md` | Activo final-v4 | Referencia de modos diagnosticos ADS1299. Aclara que el modo final de capturas es `ADS_DIAGNOSTIC_MODE=5 / bias_ch1_only_loff_off`. |
| `ads1299_register_audit_bias_drl.md` | Activo final-v4 | Contexto de registros, BIAS/RLD y decision practica CH1-only para final-v4. |
| `diseno_spectral_quality_score.md` | Activo final-v4 | Diseno del score de calidad espectral y quality gate con nombres reportables de sonificacion final-v4. |
| `midi_out_inverted_tx_validation.md` | Activo final-v4 | Validacion de MIDI OUT fisico, `Serial1`/D1, `midi_bytes` y TX invertido obligatorio. |
| `led_matrix_piano_scroll.md` | Activo secundario final-v4 | Referencia del piano scroll LED como modulo opcional/desactivado por defecto, no ruta principal EEG->MIDI. |

## 6. Historico y documentacion antigua

La documentacion historica se conserva en:

```text
historico/documentacion antigua/
```

| Documento | Estado | Documento preferente actual |
| --- | --- | --- |
| `historico/documentacion antigua/configuracion_final_v3.md` | Historico | `configuracion_final_v4.md` |
| `historico/documentacion antigua/auditoria_captura_datos.md` | Historico | `02_auditoria_codigo/funcion_por_funcion/`, `validacion_tfg/10_resultados_captura_final_laboratorio.md` |
| `historico/documentacion antigua/validacion_de_la_captura_de_datos.md` | Historico | `validacion_tfg/10_resultados_captura_final_laboratorio.md` |
| `historico/documentacion antigua/resultados_validacion_espectral_capturas.md` | Historico | `validacion_tfg/10_resultados_captura_final_laboratorio.md` y reportajes por captura |
| `historico/documentacion antigua/resultados_validacion_dsp_mixta.md` | Historico | `validacion_tfg/09_benchmarks_rendimiento_placa.md` y auditoria DSP |
| `historico/documentacion antigua/validacion_bandas_eeg_sonificacion.md` | Historico | `validacion_tfg/10_resultados_captura_final_laboratorio.md` y `configuracion_final_v4.md` |

Criterio: consultar estos documentos solo para entender decisiones anteriores, no como fuente principal del estado final-v4.

## 7. Regla de lectura

1. Para entender el estado actual, empezar por `configuracion_final_v4.md`.
2. Para comprobar que se reviso en la migracion documental, leer `auditoria_final_v4_fase1_2.md`.
3. Para justificar rendimiento temporal del TFG, usar `validacion_tfg/09_benchmarks_rendimiento_placa.md`.
4. Para justificar capturas reales y resultados experimentales, usar `validacion_tfg/10_resultados_captura_final_laboratorio.md` y `reportaje_sesion_final_s01_20260528.md`.
5. Para tocar codigo o preparar UML, consultar `02_auditoria_codigo/funcion_por_funcion/09_mapa_contratos_entre_modulos.md`, `10_mapa_funciones_criticas.md` y `11_hallazgos_para_simplificacion_futura.md`.
6. Para entender una decision antigua, consultar `historico/documentacion antigua/` o reports historicos.
7. No borrar benchmarks, capturas, reportajes ni figuras durante esta fase de organizacion documental.

