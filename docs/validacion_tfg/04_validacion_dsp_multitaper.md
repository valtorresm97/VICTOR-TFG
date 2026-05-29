# 04. Validacion DSP y multitaper - final-v4

## 1. Objetivo

Este documento valida la decision de usar PSD multitaper para extraer bandpowers y features espectrales en ventanas EEG cortas. Su papel en el TFG es justificar el bloque DSP, no demostrar una interpretacion clinica completa.

Pipeline analizado:

```text
eeg_timeseries.csv / stream live
   ↓
ventana temporal CH1
   ↓
preprocesado ligero
   ↓
PSD multitaper
   ↓
bandpowers absolutos y relativos
   ↓
features espectrales
   ↓
quality gate / sonificacion
```

## 2. Configuracion final-v4

| Parametro | Valor |
| --- | --- |
| Frecuencia | 250 Hz |
| Canal principal | CH1 |
| Ventana | 4.0 s |
| Hop live | 64 muestras |
| Presupuesto temporal | 256 ms |
| Metodo PSD principal | multitaper |
| Bandas | delta, theta, alpha, beta, gamma |

Multitaper se mantiene porque reduce leakage y variabilidad de borde frente a un periodograma simple en ventanas EEG cortas. No sustituye al buen contacto de electrodos, no corrige saturacion y no separa por si solo EMG de EEG; por eso se anadio `spectral_quality_score`.

## 3. Captura intermedia usada para comparar metodos

La captura `20260524-122200_final_atenuacion_artefactos_mixed_states` se conserva como captura intermedia para comparar estados, periodograma, multitaper y quality gate. No sustituye a la sesion final `s01_20260528`, pero es util para justificar la decision DSP.

En esa captura, el informe espectral produjo una calidad mediana de 0.912. El valor de ventanas de baja calidad/artefacto queda documentado en los CSV/reportes asociados.

## 4. Lectura de las figuras

| Figura | Uso recomendado |
| --- | --- |
| `fig_08_windowed_bandpowers.png` | Evolucion de bandpowers relativos por ventana. |
| `fig_11_quality_state_distribution.png` | Distribucion de estados del quality gate. |
| `fig_04_periodogram_by_state.png` | Periodograma por estados de protocolo. |
| `fig_04_multitaper_psd_by_state.png` | PSD multitaper por estados de protocolo. |
| `fig_04_periodogram_vs_multitaper_rest.png` | Comparacion directa en reposo. |
| `fig_04_periodogram_vs_multitaper_artifact.png` | Comparacion directa en artefacto. |
| `fig_04_spectrogram_with_state_bar.png` | Evolucion temporal del espectro con estados. |

![windowed_bandpowers](figures/fig_08_windowed_bandpowers.png)

![quality_states](figures/fig_11_quality_state_distribution.png)

![periodogram_by_state](figures/fig_04_periodogram_by_state.png)

![multitaper_by_state](figures/fig_04_multitaper_psd_by_state.png)

![periodogram_vs_multitaper_rest](figures/fig_04_periodogram_vs_multitaper_rest.png)

![periodogram_vs_multitaper_artifact](figures/fig_04_periodogram_vs_multitaper_artifact.png)

![spectrogram_state_bar](figures/fig_04_spectrogram_with_state_bar.png)

Para regenerar estas figuras con mejor estilo:

```bash
python3 python/tools/build_validation_docs_final_v4_style.py --captures-dir captures --docs-dir docs/validacion_tfg
```

## 5. Interpretacion

Las figuras por estado comparan periodograma y multitaper sobre los mismos segmentos del protocolo. El periodograma conserva mas variabilidad y leakage; multitaper suaviza la estimacion al promediar tapers DPSS, lo que ayuda a obtener bandpowers mas estables para control musical.

El espectrograma resume la evolucion temporal y permite localizar artefactos o cambios de estado, pero no debe interpretarse como diagnostico clinico por si solo.

## 6. Relacion con final-v4

En final-v4, la ruta live benchmarkeada es:

```text
EEGSignalProcessor.compute_live_features()
  -> DSPCore.compute_features(method="multitaper")
```

La ruta secundaria `compute_online_features()` no debe usarse como ruta principal en UML ni memoria.

El resultado temporal de `09_benchmarks_rendimiento_placa.md` muestra que el coste de `compute_live_features()` queda muy por debajo del presupuesto de 256 ms por hop.

## 7. Conclusion

El DSP queda validado para extraccion de caracteristicas bajo ventanas limpias o controladas. Las ventanas artefactadas deben atenuarse o excluirse mediante quality gate. Para sonificacion, la combinacion recomendada es:

```text
multitaper + bandpowers relativos + suavizado + quality gate
```
