# 04. Validación DSP y multitaper

Generado automáticamente por `python/tools/build_validation_docs.py`.

El pipeline DSP analizado es:

```text
eeg_timeseries.csv / stream live
   ↓
ventana temporal
   ↓
PSD multitaper
   ↓
bandpowers absolutos y relativos
   ↓
features espectrales
   ↓
quality gate / sonificación
```

Multitaper se mantiene porque reduce leakage y variabilidad de borde frente a un periodograma simple en ventanas EEG cortas. No sustituye al buen contacto de electrodos, no corrige saturación y no separa por sí solo EMG de EEG; por eso se añadió `spectral_quality_score`.

La configuración de validación usa fs cercano a 250 Hz, ventanas de 4 s y hop de 64 muestras. Esto da una resolución aproximada de 0.25 Hz, suficiente para resumir bandas delta/theta/alpha/beta/gamma con una latencia aceptable para sonificación lenta.

En `20260524-122200_final_atenuacion_artefactos_mixed_states`, el informe espectral produjo 0.912 de calidad mediana y pendiente de ventanas de baja calidad/artefacto.

Las figuras por estado comparan periodograma y multitaper sobre los mismos segmentos del protocolo. El periodograma conserva más variabilidad y leakage; multitaper suaviza la estimación al promediar tapers DPSS, lo que ayuda a obtener bandpowers más estables para control musical. El espectrograma resume la evolución temporal y permite localizar artefactos.

![windowed_bandpowers](figures/fig_08_windowed_bandpowers.png)

![quality_states](figures/fig_11_quality_state_distribution.png)

![periodogram_by_state](figures/fig_04_periodogram_by_state.png)

![multitaper_by_state](figures/fig_04_multitaper_psd_by_state.png)

![periodogram_vs_multitaper_rest](figures/fig_04_periodogram_vs_multitaper_rest.png)

![periodogram_vs_multitaper_artifact](figures/fig_04_periodogram_vs_multitaper_artifact.png)

![spectrogram_state_bar](figures/fig_04_spectrogram_with_state_bar.png)

Conclusión: el DSP queda validado para extracción de características bajo ventanas limpias o controladas; las ventanas artefactadas deben atenuarse o excluirse.
