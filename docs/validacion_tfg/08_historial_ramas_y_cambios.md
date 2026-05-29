# 08. Historial de ramas y cambios realizados durante la validación

Generado automáticamente por `python/tools/build_validation_docs.py`.

Este documento resume la evolución técnica realizada durante la fase de validación. No sustituye al historial Git, sino que lo traduce a decisiones de ingeniería justificables en el TFG. La rama de referencia para esta recopilación es `diagnosis/sonificacion-atenuacion-artefactos`.

## Secuencia general

La conversación comenzó con un sistema que ya comunicaba con el ADS1299, pero todavía necesitaba separar tres fuentes de incertidumbre: la cadena digital de adquisición, el montaje bioeléctrico real y la robustez de las features espectrales para sonificación. La estrategia fue avanzar por capas: primero validar ADC/SPI/Bridge/Python, después el montaje BIAS/RLD, después el DSP multitaper, y finalmente crear ramas de diagnóstico para comparar sonificación con y sin atenuación de artefactos.

| Etapa | Rama/commit representativo | Cambio técnico | Motivo | Evidencia generada |
| --- | --- | --- | --- | --- |
| Captura requestable desde la placa | `3be73e1`, `f5f9516` | `capture_eeg_quality.py` permite pedir capturas desde shell y analizarlas con paquetes disponibles en App Lab. | Evitar depender de observaciones visuales y guardar CSV trazables. | `eeg_timeseries.csv`, `metadata.json`, `quality_report.*` por captura. |
| Auditoría y diagnóstico de adquisición | `9b5be72`, `34ecc8e` | Herramientas de auditoría y comparación de capturas open/closed. | Medir gaps, status, RMS, pico-pico, 50 Hz y respuesta por condición. | `eyes_open_closed_comparison.*` y reportes de calidad. |
| Modos diagnósticos ADS1299 | `ebea8f8`, `61cf262` | Se añaden `shorted_inputs` y `test_signal_internal` para aislar ADC/SPI/escala. | Separar problemas digitales de problemas de electrodos o referencia común. | `shorted_inputs` con ruido muy bajo; test interno estable. |
| Corrección de registros ADS1299 | `e0f8437`, `924783f` | Auditoría de CONFIG1/CONFIG3 y preservación de bits reservados/fijos. | Alinear configuración con datasheet y evitar valores como `0x86` o `0x8C` que no preservaban bits esperados. | `docs/ads1299_register_audit_bias_drl.md`. |
| BIAS/RLD y CH1-only | `c6830c4`, `06f92f7` | Modos `bias_ch1pn_loff_off` y `bias_ch1_only_loff_off`; diagnósticos multicanal. | Reducir común, apagar canales no usados y estabilizar el montaje más útil. | Capturas ear-EEG y Fp1-Fp2 con RMS por ventanas plausible. |
| Métricas por ventanas | `aca2ebc` | Se añaden `median_rms_uV`, `p95_rms_uV`, `best_window_rms_uV`, `artifact_window_fraction`. | No rechazar capturas completas por transitorios si existen ventanas limpias. | `quality_report.md/json` más interpretables. |
| Documentación de captura | `d3ed1f1` | Primer documento de validación de captura de datos. | Convertir resultados de pruebas en texto reutilizable para TFG. | `docs/validacion_de_la_captura_de_datos.md`. |
| Validación espectral offline | `73e2dc6`, `aa60128` | `validate_spectral_features.py`, bandpowers por ventana, PSD multitaper, informes espectrales. | Validar que las bandas y features se comportan de forma reproducible con CSV reales. | `windowed_bandpowers.csv`, `spectral_validation_report.*`. |
| Capturas reales versionadas | `91899a6`, `3c42354` | Se suben capturas representativas: shorted, ear-EEG, Fp1-Fp2, mandíbula, frente y sesión mixta. | Permitir análisis local y documentación sin depender de texto pegado. | Carpeta `captures/` versionada. |
| Análisis DSP mixto | `7789a79` | Segmentación de protocolo mixto y evaluación de estados. | Comprobar funcionamiento real del DSP durante cambios de estado y artefactos. | `docs/resultados_validacion_dsp_mixta.md`. |
| Rama base DSP | `captura-datos-dsp`, `02d5f43` | Se fija `ADS_DIAGNOSTIC_MODE=5` (`bias_ch1_only_loff_off`) como modo por defecto. | Establecer una base común para comparar sonificación con y sin atenuación. | Rama `captura-datos-dsp` subida al remoto. |
| Rama sin atenuación | `diagnosis/sonificacion-con-artefactos` | Mantiene el DSP y la sonificación sin quality gate. | Servir como control: observar respuesta musical cuando los artefactos pasan sin amortiguación. | Rama remota para pruebas A/B. |
| Rama con atenuación | `diagnosis/sonificacion-atenuacion-artefactos`, `3a37152` | Se crea `spectral_quality.py` y se integra en backend y `sonification_features.py`. | Atenuar o invalidar ventanas con artefactos sin cambiar adquisición ni DSP base. | `docs/diseno_spectral_quality_score.md`. |
| Capturas de atenuación | `60aab62`, `4b46f2a` | Se suben capturas mixtas con rama de atenuación. | Validar que hay ventanas limpias, ventanas con cautela y ventanas bloqueadas. | `20260524-122200_final_atenuacion_artefactos_mixed_states`. |
| Alineación offline/live | `5c06a4c` | El validador offline aplica el mismo quality gate que el backend live. | Hacer comparables `windowed_sonification_features.csv` y el comportamiento real. | Informes regenerados con estados `clean`, `usable_with_caution`, `artifact_suspected`, `bad`. |

## Ramas finales de diagnóstico

- `captura-datos-dsp`: base común con adquisición y DSP validados preliminarmente, y `bias_ch1_only_loff_off` por defecto.
- `diagnosis/sonificacion-con-artefactos`: rama de control, sin atenuación de artefactos.
- `diagnosis/sonificacion-atenuacion-artefactos`: rama experimental, con `spectral_quality_score` y quality gate.

La comparación entre las dos ramas de diagnóstico permite separar dos preguntas: si la señal/DSP funciona, y si la capa musical debe protegerse frente a artefactos. La respuesta obtenida fue que la señal y el DSP son suficientemente útiles para continuar, pero la sonificación necesita memoria musical, histéresis y control de repetición armónica.

## Cambios que no se hicieron en esta fase

No se rediseñó la sonificación final, no se cambiaron las bandas EEG principales, no se sustituyó multitaper y no se modificó el contrato `Bridge.notify("eeg_block_uV")`. Esto fue deliberado: la fase buscaba validar y documentar, no optimizar todavía la composición musical.
