# 05. Validación de bandas EEG y features espectrales

Generado automáticamente por `python/tools/build_validation_docs.py`.

Las bandas se interpretan como features de sonificación, no como diagnóstico clínico. La validación distingue presencia espectral, robustez temporal y riesgo de artefacto.

La comparación ojos abiertos/cerrados fue más favorable en ear-EEG que en Fp1-Fp2. En Fp1-Fp2, la alfa clásica puede no aparecer de forma robusta por tratarse de un montaje frontal, con mayor contribución ocular y muscular.

Ear-EEG disponible: `20260523-200925_ear_eeg_ch1_only_eyes_open_60s` y `20260523-201055_ear_eeg_ch1_only_eyes_closed_60s`.

Fp1-Fp2 disponible: `20260523-202208_fp1_fp2_ch1_only_eyes_open_60s` y `20260523-202323_fp1_fp2_ch1_only_eyes_closed_60s`.

| Montaje | Condición | Delta | Theta | Alpha | Beta | Gamma | Alpha/Beta | Calidad | Conclusión |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ear-EEG | eyes_open | 0.391 | 0.108 | 0.064 | 0.154 | 0.260 | 0.414 | 1.000 | más estable para validación de reposo |
| ear-EEG | eyes_closed | 0.369 | 0.110 | 0.158 | 0.137 | 0.163 | 1.150 | 1.000 | más estable para validación de reposo |
| Fp1-Fp2 | eyes_open | 0.432 | 0.078 | 0.041 | 0.133 | 0.306 | 0.310 | 1.000 | útil pero más sensible a frente/parpadeo |
| Fp1-Fp2 | eyes_closed | 0.499 | 0.094 | 0.044 | 0.064 | 0.281 | 0.680 | 1.000 | útil pero más sensible a frente/parpadeo |
| ear-EEG | jaw_movement | 0.945 | 0.026 | 0.007 | 0.012 | 0.010 | 0.541 | 0.490 | condición de artefacto; usar para rechazo/gate |
| Fp1-Fp2 | forehead_blink | 0.861 | 0.066 | 0.009 | 0.024 | 0.064 | 0.386 | 0.864 | condición de artefacto; usar para rechazo/gate |

Tabla CSV completa: [`tables/table_05_band_stats_fp1fp2_vs_eareeg.csv`](tables/table_05_band_stats_fp1fp2_vs_eareeg.csv).

![alpha_open_closed](figures/fig_07_eyes_open_vs_closed_alpha.png)

![windowed_bandpowers](figures/fig_08_windowed_bandpowers.png)

![relative_bandpowers_by_mounting](figures/fig_05_relative_bandpowers_by_mounting.png)

![alpha_beta_ratio_comparison](figures/fig_05_alpha_beta_ratio_comparison.png)

![feature_robustness_heatmap](figures/fig_05_feature_robustness_heatmap.png)

Tabla de decisión por banda: [`tables/table_04_spectral_band_validation.csv`](tables/table_04_spectral_band_validation.csv).

Conclusiones principales: alpha fue más útil en ear-EEG que en Fp1-Fp2 para la validación disponible; Fp1-Fp2 queda más expuesto a parpadeo/frente; beta y gamma deben tratarse como riesgo EMG; delta/theta son útiles solo como apoyo por sensibilidad a drift y movimiento; para sonificación se recomiendan bandas relativas, suavizado, normalización por sesión y `quality gate`.
