# 08. Auditoria tools, capturas y documentacion

## Tools CLI

| Tool | Uso | Entrada | Salida | Ejecuta en shell/App Lab | Estado |
| --- | --- | --- | --- | --- | --- |
| `python/tools/capture_eeg_quality.py` | Solicitar captura real a la app corriendo. | `--condition`, `--duration`, `--notes` | `state/capture_request.json`, espera `capture_status.json`. | Shell normal + App Lab corriendo | Activa |
| `python/tools/analyze_eeg_capture.py` | Analizar una captura CSV. | Directorio `captures/<...>` | `quality_report.*`, `spectral_summary.csv`, `psd_multitaper.csv`. | Shell normal | Activa |
| `python/tools/compare_eeg_captures.py` | Comparar dos capturas, p.ej. ojos abiertos/cerrados. | Dos dirs de captura | Markdown/json comparativo. | Shell normal | Activa |
| `python/tools/validate_spectral_features.py` | Recalcular/validar bandpowers y features por ventanas. | Captura o root de capturas | `windowed_bandpowers.csv`, `windowed_sonification_features.csv`, reports. | Shell normal | Activa |
| `python/tools/build_validation_docs.py` | Construir docs, tablas y figuras TFG. | `captures/`, `docs/validacion_tfg` | Markdown, CSV, PNG/PDF. | Shell normal con NumPy/SciPy/Matplotlib | Activa |
| `python/tools/set_ads_diagnostic_mode.py` | Cambiar macro `ADS_DIAGNOSTIC_MODE`. | Modo textual | Modifica `sketch/sketch.ino`. | Shell normal | Activa, riesgosa |
| `python/tools/test_led_matrix_visualizer.py` | Tests de mapeo LED sin hardware. | Ninguna | Prints/asserts. | Shell normal | Activa |

## Capturas existentes

| Captura | Tipo | Uso principal |
| --- | --- | --- |
| `post_configfix_shorted_inputs` | Diagnostico ADC | Ruido/offset interno y cadena digital. |
| `ear_eeg_ch1_only_still_30s` | EEG real | Reposo quieto ear EEG. |
| `ear_eeg_ch1_only_eyes_open_60s` | EEG real | Condicion ojos abiertos ear EEG. |
| `ear_eeg_ch1_only_eyes_closed_60s` | EEG real | Condicion ojos cerrados ear EEG. |
| `ear_eeg_ch1_only_jaw_movement_30s` | Artefacto | Control EMG/mandibula. |
| `fp1_fp2_ch1_only_quiet_30s` | EEG real | Montaje frontal quieto. |
| `fp1_fp2_ch1_only_eyes_open_60s` | EEG real | Ojos abiertos Fp1-Fp2. |
| `fp1_fp2_ch1_only_eyes_closed_60s` | EEG real | Ojos cerrados Fp1-Fp2. |
| `fp1_fp2_ch1_only_forehead_blink_artifact_30s` | Artefacto | Control frente/parpadeo. |
| `live_dsp_validation_mixed_states_ear_eeg` | Validacion live | Estados mixtos para DSP/gate. |
| `diag_atenuacion_mixed_states_ear_eeg` | Validacion gate | Diagnostico atenuacion. |
| `final_atenuacion_artefactos_mixed_states` | Referencia final | Captura de referencia para quality gate. |

## Reports por captura

Cada captura completa suele incluir:

- `eeg_timeseries.csv`
- `metadata.json`
- `quality_report.md/json`
- `spectral_validation_report.md/json`
- `spectral_summary.csv`
- `psd_multitaper.csv`
- `windowed_bandpowers.csv`
- `windowed_sonification_features.csv`

## Documentos existentes

| Documento | Estado | Observacion |
| --- | --- | --- |
| `docs/auditoria_captura_datos.md` | Auditoria previa | Muy relevante y vigente para ADS/SPI/DSP. |
| `docs/ads1299_diagnostic_modes.md` | Protocolo tecnico | Define modos 0..5 y pruebas. |
| `docs/ads1299_register_audit_bias_drl.md` | Auditoria ADS | Complementa registros/BIAS. |
| `docs/diseno_spectral_quality_score.md` | Diseno | Explica quality gate y decisiones. |
| `docs/led_matrix_piano_scroll.md` | Diseno/auditoria | Documento principal de matrix scroll. |
| `docs/resultados_validacion_espectral_capturas.md` | Report | Resumen ejecutivo de validacion espectral. |
| `docs/resultados_validacion_dsp_mixta.md` | Report | Validacion DSP mixta. |
| `docs/validacion_tfg/00..08` | Documentacion final | Serie mas formal para TFG. |
| `docs/validacion_tfg/tables/*` | Tablas generadas | Defendibles como anexos/evidencia. |
| `docs/validacion_tfg/figures/*` | Figuras generadas | PNG/PDF para memoria. |

## Conclusiones documentales

- La captura final de referencia parece ser `20260524-122200_final_atenuacion_artefactos_mixed_states`.
- Ear EEG CH1-only muestra mejor validacion de alpha que Fp1-Fp2 en documentos existentes.
- Mandibula y frente/parpadeo se usan como controles de artefacto.
- `docs/validacion_tfg` es la familia mas definitiva; otros docs son auditorias o reports historicos.
