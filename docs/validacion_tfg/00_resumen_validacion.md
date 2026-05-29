# 00. Resumen general de validacion - final-v4

## 1. Papel de este documento

Este documento resume el bloque de validacion del sistema EEG-MIDI. Los documentos `00` a `05` nacieron como salida automatica de `python/tools/build_validation_docs.py` y siguen siendo utiles para justificar decisiones de diseno: adquisicion ADS1299, montaje de electrodos, BIAS/RLD, calidad de senal, DSP multitaper, bandas EEG y quality gate.

En final-v4 no deben leerse como sustituto de la sesion final de laboratorio. La evidencia final principal queda en:

| Evidencia | Documento |
| --- | --- |
| Rendimiento temporal en placa | `09_benchmarks_rendimiento_placa.md` |
| Captura final de laboratorio | `10_resultados_captura_final_laboratorio.md` |
| Reportaje global de sesion | `reportaje_sesion_final_s01_20260528.md` |
| Reportajes por condicion | `reportajes_capturas_s01_20260528/` |
| Figuras finales | `figures/capturas_finales_s01_20260528_matplotlib/` y `figures/capturas_finales_s01_20260528_enhanced/` |

## 2. Configuracion final-v4 de referencia

| Campo | Valor |
| --- | --- |
| Modo ADS | `ADS_DIAGNOSTIC_MODE=5 / bias_ch1_only_loff_off` |
| Montaje final | `ear_eeg_ch1_only` |
| Canal principal | CH1 |
| CH2-CH4 | Conservados por contrato, no EEG activo en capturas finales |
| Ventana DSP | 4.0 s |
| Hop features | 64 muestras, 256 ms a 250 Hz |
| MIDI fisico | `Serial1`/D1 con TX invertido |
| LED matrix | Desactivada por defecto |

## 3. Bloques validados

| Bloque validado | Evidencia | Resultado final-v4 |
| --- | --- | --- |
| ADS1299/SPI/RDATAC | ID/status, shorted inputs y capturas reales | Cadena digital razonablemente validada. |
| Bridge MCU-Python | CSV con 250 Hz y bloques de 8 muestras | Streaming estable en condiciones probadas. |
| Montaje electrodos | Fp1-Fp2 frente a ear-EEG/CH1-only | Se adopta ear-EEG/CH1-only por estabilidad. |
| DSP multitaper | PSD, bandpowers, ventanas de 4 s | Valido para extraer features de sonificacion. |
| Quality gate | Diagnostico + `spectral_quality_score` | Esencial para atenuar/bloquear ventanas malas. |
| Sonificacion | Controles final-v4 y notas guardadas | Integrada con capturas finales. |
| MIDI fisico | `midi_bytes` hacia UART fisica | Validado en placa. |
| WebUI musical | root/main/scale, panic y piano roll | Integrada como observador y control ligero. |

## 4. Capturas antiguas y sesion final

La captura antigua `20260524-122200_final_atenuacion_artefactos_mixed_states` sigue siendo util como validacion intermedia de quality gate y estados/artefactos. No debe presentarse como captura final principal.

La sesion final reportable es:

```text
s01_20260528
```

con resultados en `10_resultados_captura_final_laboratorio.md` y reportajes asociados.

## 5. Figuras de este bloque

Las figuras enlazadas en `00` a `05` son utiles para explicar decisiones de diseno, pero algunas fueron generadas con titulos y margenes poco adecuados para memoria. Para regenerarlas con estilo final-v4 se ha anadido:

```text
python/tools/build_validation_docs_final_v4_style.py
```

Este wrapper no modifica calculos. Solo mejora estilo Matplotlib: titulos mas pequenos, wrapping, margenes robustos, leyendas moderadas y guardado con `bbox_inches="tight"`.

Comando seguro recomendado:

```bash
python3 python/tools/build_validation_docs_final_v4_style.py --captures captures --output docs/validacion_tfg
```

El wrapper fuerza `--only-figures` por defecto para no sobrescribir los Markdown revisados manualmente.

## 6. Conclusion

La validacion final-v4 demuestra integracion tecnica completa:

```text
ADS1299 -> firmware -> Bridge -> Python -> DSP -> quality gate -> sonificacion -> MIDI fisico / notas registradas
```

Las limitaciones restantes estan relacionadas principalmente con calidad de senal, artefactos, estabilidad del montaje, explicabilidad de la WebUI y futura medicion de latencia fisica end-to-end.



