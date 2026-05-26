# Indice de documentacion

Este indice evita que los reports historicos se interpreten como el estado
actual del proyecto. No se borra ningun documento: se clasifica la fuente que
debe usarse en cada fase.

## Documentacion definitiva para la fase actual

| Documento | Estado | Uso recomendado |
| --- | --- | --- |
| `auditoria_firmware_final_v1/README.md` | Definitivo para arquitectura y riesgos de refactor | Punto de entrada tecnico antes de tocar firmware/backend/DSP/UI. |
| `auditoria_firmware_final_v1/10_redundancias_y_deuda_tecnica.md` | Definitivo para eliminacion incremental de redundancias | Lista de trabajo actual de esta rama. |
| `auditoria_firmware_final_v1/12_mapa_criticidad_refactor.md` | Definitivo para decidir riesgo de cambios | Consultar antes de modificar archivos criticos. |
| `validacion_tfg/00_resumen_validacion.md` | Definitivo para evidencia de captura/DSP | Resumen consolidado generado desde capturas y tablas. |
| `validacion_tfg/07_protocolo_final_adquisicion.md` | Definitivo para repetir pruebas en placa | Protocolo recomendado de captura y validacion. |

## Documentacion activa de subsistemas

| Documento | Estado | Uso recomendado |
| --- | --- | --- |
| `ads1299_diagnostic_modes.md` | Activo | Referencia de modos diagnosticos ADS1299. |
| `ads1299_register_audit_bias_drl.md` | Activo | Contexto de registros, BIAS/RLD y decisiones ADS1299. |
| `diseno_spectral_quality_score.md` | Activo | Diseno del score de calidad espectral. |
| `led_matrix_piano_scroll.md` | Activo | Referencia del piano scroll LED y su transporte. |

## Validacion TFG consolidada

La carpeta `validacion_tfg/` contiene la salida consolidada generada por
`python/tools/build_validation_docs.py`. Si hay discrepancia con reports raiz
anteriores, prevalece `validacion_tfg/`.

| Carpeta/archivo | Estado | Uso recomendado |
| --- | --- | --- |
| `validacion_tfg/01_validacion_captura_datos_ads1299.md` | Consolidado | Evidencia ADS1299/SPI/RDATAC/Bridge. |
| `validacion_tfg/02_validacion_montaje_electrodos_bias_rld.md` | Consolidado | Comparacion de montajes y decision CH1-only. |
| `validacion_tfg/03_validacion_calidad_senal_real.md` | Consolidado | Calidad de senal, artefactos y capturas finales. |
| `validacion_tfg/04_validacion_dsp_multitaper.md` | Consolidado | Validacion DSP multitaper. |
| `validacion_tfg/05_validacion_bandas_eeg_y_features.md` | Consolidado | Bandpowers, features y comparativas. |
| `validacion_tfg/06_conclusiones_para_sonificacion.md` | Consolidado | Conclusiones para mapping musical. |
| `validacion_tfg/tables/` | Generado | Tablas fuente para memoria/figuras. |
| `validacion_tfg/figures/` | Generado | Figuras fuente para memoria. |

## Reports historicos o solapados

Estos documentos siguen siendo utiles para trazabilidad, pero no deben usarse
como fuente principal si contradicen `validacion_tfg/` o la auditoria final.

| Documento | Estado | Documento preferente |
| --- | --- | --- |
| `auditoria_captura_datos.md` | Historico | `auditoria_firmware_final_v1/` y `validacion_tfg/01_validacion_captura_datos_ads1299.md`. |
| `validacion_de_la_captura_de_datos.md` | Historico | `validacion_tfg/01_validacion_captura_datos_ads1299.md`. |
| `resultados_validacion_espectral_capturas.md` | Historico | `validacion_tfg/05_validacion_bandas_eeg_y_features.md`. |
| `resultados_validacion_dsp_mixta.md` | Historico | `validacion_tfg/04_validacion_dsp_multitaper.md`. |
| `validacion_bandas_eeg_sonificacion.md` | Historico | `validacion_tfg/05_validacion_bandas_eeg_y_features.md` y `validacion_tfg/06_conclusiones_para_sonificacion.md`. |

## Regla de lectura

1. Para cambiar codigo, empezar por `auditoria_firmware_final_v1/`.
2. Para justificar resultados del TFG, usar `validacion_tfg/`.
3. Para entender una decision antigua, consultar reports historicos.
4. Para regenerar evidencia, usar `python/tools/build_validation_docs.py`.
