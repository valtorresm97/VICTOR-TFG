# 02. Validación del montaje de electrodos, BIAS y RLD

Generado automáticamente por `python/tools/build_validation_docs.py`.

El montaje inicial Fp1-Fp2 permitió observar actividad frontal, pero mostró sensibilidad a contacto, movimiento y ruido común. La activación de BIAS/RLD y el paso a modos `bias_ch1pn_loff_off` y posteriormente `bias_ch1_only_loff_off` redujeron la influencia de canales no usados y facilitaron capturas más estables.

La evidencia versionada muestra dos familias útiles: Fp1-Fp2, más expresiva frente a parpadeo/frente pero menos robusta, y ear-EEG/mastoides, más estable para validación de reposo y cambios de estado. El montaje final de diagnóstico usa CH1 activo, BIAS derivado de CH1P+CH1N y lead-off desactivado.

![rms_comparison](figures/fig_04_rms_comparison.png)

![ptp_comparison](figures/fig_05_ptp_comparison.png)

![line50_comparison](figures/fig_06_50hz_comparison.png)

![final_timeseries](figures/fig_03_final_capture_timeseries.png)

Comparación de montajes: [`tables/table_02_mounting_comparison.csv`](tables/table_02_mounting_comparison.csv).

Conclusión: el montaje final no elimina los artefactos biológicos, pero ofrece una base suficientemente estable para analizar ventanas limpias. La elección se justifica por estabilidad temporal, ausencia de gaps y respuesta clara ante artefactos controlados.
