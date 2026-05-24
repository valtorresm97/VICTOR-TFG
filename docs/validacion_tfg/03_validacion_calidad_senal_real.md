# 03. Validación de calidad de señal real

Generado automáticamente por `python/tools/build_validation_docs.py`.

La calidad de señal real se evaluó con métricas globales y por ventanas. Las métricas globales detectan artefactos grandes, mientras que las ventanas permiten distinguir una captura parcialmente válida de una captura completamente mala.

Criterios utilizados:

- señal válida: 250 Hz efectivo, sample gaps 0, invalid status 0, RMS mediano plausible y baja fracción de ventanas artefactadas;
- señal dudosa: transporte correcto pero RMS/PTP o 50 Hz altos en una parte relevante de la captura;
- señal no válida: gaps, status inválido persistente, saturación, flatline o artefactos dominantes que impiden extraer ventanas limpias.

En la captura final `20260524-122200_final_atenuacion_artefactos_mixed_states` se observó `valida_preliminar_con_artefactos`. El RMS global fue 848.7 µV, pero el RMS mediano por ventanas fue 83.30 µV, lo que indica que el valor global está influido por transitorios. La fracción de ventanas artefactadas fue 6.0% y la calidad espectral mediana fue 0.912.

![final_timeseries](figures/fig_03_final_capture_timeseries.png)

![jaw_timeseries](figures/fig_09_jaw_movement_timeseries.png)

![jaw_psd](figures/fig_10_jaw_emg_psd.png)

![quality_states](figures/fig_11_quality_state_distribution.png)

Inventario completo: [`tables/table_01_capture_summary.csv`](tables/table_01_capture_summary.csv).
