# 05. Validacion de bandas EEG y features espectrales - final-v4

## 1. Objetivo

Este documento justifica que las bandas EEG se usen como features de sonificacion y no como diagnostico clinico. La validacion distingue:

```text
presencia espectral
robustez temporal
riesgo de artefacto
utilidad para control musical
```

En final-v4, estas bandas alimentan controles de sonificacion reportables y siempre deben interpretarse junto al quality gate.

## 2. Comparacion de montajes y condiciones

La comparacion ojos abiertos/cerrados fue mas favorable en ear-EEG que en Fp1-Fp2. En Fp1-Fp2, la alfa clasica puede no aparecer de forma robusta por tratarse de un montaje frontal, con mayor contribucion ocular y muscular.

Capturas usadas en la validacion de diseno:

```text
ear-EEG:
20260523-200925_ear_eeg_ch1_only_eyes_open_60s
20260523-201055_ear_eeg_ch1_only_eyes_closed_60s

Fp1-Fp2:
20260523-202208_fp1_fp2_ch1_only_eyes_open_60s
20260523-202323_fp1_fp2_ch1_only_eyes_closed_60s
```

Estas capturas son antecedentes de diseno. La sesion final reportable es `s01_20260528`.

## 3. Resultados resumidos

| Montaje | Condicion | Delta | Theta | Alpha | Beta | Gamma | Alpha/Beta | Calidad | Conclusion |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| ear-EEG | eyes_open | 0.391 | 0.108 | 0.064 | 0.154 | 0.260 | 0.414 | 1.000 | mas estable para validacion de reposo |
| ear-EEG | eyes_closed | 0.369 | 0.110 | 0.158 | 0.137 | 0.163 | 1.150 | 1.000 | mas estable para validacion de reposo |
| Fp1-Fp2 | eyes_open | 0.432 | 0.078 | 0.041 | 0.133 | 0.306 | 0.310 | 1.000 | util pero mas sensible a frente/parpadeo |
| Fp1-Fp2 | eyes_closed | 0.499 | 0.094 | 0.044 | 0.064 | 0.281 | 0.680 | 1.000 | util pero mas sensible a frente/parpadeo |
| ear-EEG | jaw_movement | 0.945 | 0.026 | 0.007 | 0.012 | 0.010 | 0.541 | 0.490 | condicion de artefacto; usar para rechazo/gate |
| Fp1-Fp2 | forehead_blink | 0.861 | 0.066 | 0.009 | 0.024 | 0.064 | 0.386 | 0.864 | condicion de artefacto; usar para rechazo/gate |

Tabla CSV completa:

```text
tables/table_05_band_stats_fp1fp2_vs_eareeg.csv
```

## 4. Decisiones por banda

| Banda | Uso final-v4 | Cautela |
| --- | --- | --- |
| Delta | Apoyo contextual y estabilidad lenta | Sensible a drift, movimiento y transitorios. |
| Theta | Apoyo contextual | No sobreinterpretar sin mas sujetos/condiciones. |
| Alpha | Util especialmente en ear-EEG y reposo | En Fp1-Fp2 no aparece robusta por montaje frontal. |
| Beta | Puede contribuir a actividad/tension | Riesgo de EMG y movimiento. |
| Gamma | Usar con mucha cautela | Muy sensible a EMG; no usar como indicador fisiologico directo. |

## 5. Controles final-v4 relacionados

Los nombres reportables actuales son:

| Control final-v4 | Relacion con bandas/features |
| --- | --- |
| `alpha_drive` | Relacionado con alpha relativa y reposo espectral. |
| `beta_gamma_drive` | Relacionado con beta/gamma, siempre con cautela por EMG. |
| `rms_beta_activity` | Combina RMS normalizado y bandas rapidas. |
| `band_driven_density` | Densidad ritmica derivada de actividad/bandas. |
| `spectral_register` | Registro melodico vinculado a pico/frecuencia dominante. |
| `alpha_stability` | Estabilidad armonica derivada de alpha frente a tension rapida. |
| `rms_band_velocity` | Intensidad MIDI desde RMS/bandas. |
| `band_note_probability` | Probabilidad de nota desde densidad/bandas. |

Los nombres antiguos (`activity`, `calmness`, `tension`, etc.) se consideran aliases legacy internos y no deben usarse como nombres principales del TFG.

## 6. Figuras asociadas

| Figura | Uso recomendado |
| --- | --- |
| `fig_07_eyes_open_vs_closed_alpha.png` | Comparacion alpha ojos abiertos/cerrados. |
| `fig_08_windowed_bandpowers.png` | Evolucion de bandpowers relativos. |
| `fig_05_relative_bandpowers_by_mounting.png` | Bandas relativas por montaje/condicion. |
| `fig_05_alpha_beta_ratio_comparison.png` | Relacion alpha/beta por montaje. |
| `fig_05_feature_robustness_heatmap.png` | Mapa de robustez relativa de bandas. |

![alpha_open_closed](figures/fig_07_eyes_open_vs_closed_alpha.png)

![windowed_bandpowers](figures/fig_08_windowed_bandpowers.png)

![relative_bandpowers_by_mounting](figures/fig_05_relative_bandpowers_by_mounting.png)

![alpha_beta_ratio_comparison](figures/fig_05_alpha_beta_ratio_comparison.png)

![feature_robustness_heatmap](figures/fig_05_feature_robustness_heatmap.png)

Para regenerar estas figuras con mejor estilo:

```bash
python3 python/tools/build_validation_docs_final_v4_style.py --captures-dir captures --docs-dir docs/validacion_tfg
```

## 7. Tablas

- Tabla CSV completa: [`tables/table_05_band_stats_fp1fp2_vs_eareeg.csv`](tables/table_05_band_stats_fp1fp2_vs_eareeg.csv).
- Tabla de decision por banda: [`tables/table_04_spectral_band_validation.csv`](tables/table_04_spectral_band_validation.csv).

## 8. Conclusion

Alpha fue mas util en ear-EEG que en Fp1-Fp2 para la validacion disponible. Fp1-Fp2 queda mas expuesto a parpadeo/frente. Beta y gamma deben tratarse como riesgo EMG. Delta/theta son utiles solo como apoyo por sensibilidad a drift y movimiento.

Para sonificacion final-v4 se recomiendan:

```text
bandas relativas
suavizado temporal
normalizacion por sesion
quality gate
nombres reportables vinculados a EEG/features
```
