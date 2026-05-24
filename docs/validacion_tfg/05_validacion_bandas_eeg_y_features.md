# 05. Validación de bandas EEG y features espectrales

Generado automáticamente por `python/tools/build_validation_docs.py`.

Las bandas se interpretan como features de sonificación, no como diagnóstico clínico. La validación distingue presencia espectral, robustez temporal y riesgo de artefacto.

La comparación ojos abiertos/cerrados fue más favorable en ear-EEG que en Fp1-Fp2. En Fp1-Fp2, la alfa clásica puede no aparecer de forma robusta por tratarse de un montaje frontal, con mayor contribución ocular y muscular.

Ear-EEG disponible: `20260523-200925_ear_eeg_ch1_only_eyes_open_60s` y `20260523-201055_ear_eeg_ch1_only_eyes_closed_60s`.

Fp1-Fp2 disponible: `20260523-202208_fp1_fp2_ch1_only_eyes_open_60s` y `20260523-202323_fp1_fp2_ch1_only_eyes_closed_60s`.

![alpha_open_closed](figures/fig_07_eyes_open_vs_closed_alpha.png)

![windowed_bandpowers](figures/fig_08_windowed_bandpowers.png)

Tabla de decisión por banda: [`tables/table_04_spectral_band_validation.csv`](tables/table_04_spectral_band_validation.csv).

Decisiones principales: delta/theta se usan solo como apoyo por sensibilidad a drift y parpadeo; alpha requiere normalización y comparación por sesión; beta puede aportar tensión con cautela; gamma no debe controlar directamente la sonificación en tiempo real por riesgo EMG.
