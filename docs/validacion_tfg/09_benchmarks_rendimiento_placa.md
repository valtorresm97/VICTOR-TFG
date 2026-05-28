# 09. Validación temporal del procesamiento en placa

## Objetivo

Este documento recoge los resultados de benchmark temporal obtenidos en la placa Arduino UNO Q/Linux durante la fase final de validación del sistema EEG-MIDI. Su objetivo es servir como base para la sección de validación y resultados del TFG, mostrando si el procesamiento Python ejecutado en la placa dispone de margen suficiente para operar en tiempo real.

A diferencia de las pruebas sintéticas o de PC, esta validación se ha realizado sobre una captura real adquirida por el sistema completo:

```text
ADS1299 -> SPI/RDATAC -> firmware MCU -> filtros MCU -> Bridge.notify("eeg_block_uV") -> Python -> DSPCore -> sonificación
```

El análisis no pretende validar fisiológicamente la señal EEG por sí solo. Su finalidad principal es evaluar el coste computacional real del pipeline Python en la placa usando datos capturados por el hardware.

## Rama, commit y entorno

Los benchmarks se ejecutaron en la rama:

```text
docs/final-v3-audit-update
```

El reporte de benchmark fue generado con:

| Campo | Valor |
| --- | --- |
| Commit base del benchmark | `51d5ebc97ab660b50b311c0f1b65dd04847f4f72` |
| Commit de captura subido | `9f305a9 Capture board benchmark results` |
| Python | `3.13.5` |
| Plataforma | `Linux-7.0.0-g122c2c22d838-aarch64-with-glibc2.41` |
| Placa | Arduino UNO Q / Linux App Lab |

Los resultados quedaron versionados en:

```text
benchmarks/results/20260528-105120_real_capture__benchmark_results.json
benchmarks/results/20260528-105120_real_capture__benchmark_results.csv
benchmarks/reports/20260528-105120_real_capture__benchmark_report.md
captures/20260528-104617_bench_real_rest_60s/
```

## Captura real empleada

La captura usada para el benchmark fue:

```text
captures/20260528-104617_bench_real_rest_60s
```

Condición:

```text
bench_real_rest_60s
```

Resumen de adquisición:

| Métrica | Valor |
| --- | ---: |
| Duración solicitada | 60.0 s |
| Duración observada en metadata | 60.019 s |
| Duración efectiva según quality report | 57.09 s |
| Frecuencia esperada | 250 Hz |
| Canales transmitidos | 4 |
| Bloques recibidos | 1784 |
| Muestras recibidas / filas CSV | 14272 |
| Muestras por bloque | 8 |
| Gaps de bloque | 0 |
| Gaps de muestra | 0 |
| Bloques malformados | 0 |
| Status ADS1299 inválidos | 0 |
| Evento Bridge | `eeg_block_uV` |

La ausencia de gaps, bloques malformados y status inválidos indica que la captura es adecuada para medir el rendimiento temporal del procesamiento en placa.

## Calidad de señal durante la prueba

El informe de calidad clasificó la captura como:

```text
valida_preliminar_con_artefactos
```

Resumen de CH1:

| Métrica | Valor |
| --- | ---: |
| RMS global | 289.062 µV |
| Media | 31.116 µV |
| Pico-pico | 16851 µV |
| Ratio 50 Hz | 0.0714 |
| Pico dominante | 24.9965 Hz |

Resumen por ventanas de 2 s:

| Métrica | Valor |
| --- | ---: |
| Número de ventanas | 56 |
| RMS mediano | 97.95 µV |
| RMS p95 | 480.71 µV |
| Mejor ventana RMS | 43.88 µV |
| Fracción de ventanas artefactadas | 16.07 % |

Esta captura contiene artefactos transitorios y no debe usarse por sí sola como demostración fisiológica definitiva. Sin embargo, sí es válida como benchmark temporal porque reproduce la carga real del sistema: lectura desde CSV generado por el hardware, reconstrucción de bloques, ring buffer, cálculo espectral, diagnóstico de calidad y adaptación de sonificación.

## Criterio temporal de referencia

El backend calcula características espectrales con:

```text
FEATURE_HOP_SAMPLES = 64
FS_HZ = 250 Hz
```

Por tanto, el tiempo disponible entre actualizaciones de features es:

```text
64 / 250 = 0.256 s = 256 ms
```

Este valor se usa como referencia para valorar si el cálculo live dispone de margen suficiente. El tiempo de cálculo de cada ciclo crítico debe quedar claramente por debajo de 256 ms.

## Resultados de benchmark

| Benchmark | Función | Escenario | Mediana ms | P95 ms | Máx ms | Interpretación |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `real_capture.parse_eeg_block_values.first_block` | `parse_eeg_block_values` | Primer bloque real | 0.0489 | 0.0502 | 0.1404 | Coste despreciable del parser por bloque. |
| `real_capture.receiver_replay_all_blocks` | `EEGReceiver.eeg_block_uV` | Replay de toda la captura | 162.6736 | 252.6365 | 318.8870 | Tiempo de reprocesar 1784 bloques completos; no es tiempo por bloque live. |
| `real_capture.buffer_replay_all_blocks` | `EEGSignalProcessor.add_block_uV` | Replay de toda la captura al ring buffer | 74.6253 | 75.5110 | 75.9692 | Tiempo de reinyectar toda la captura; no es tiempo por bloque live. |
| `real_capture.compute_live_features.final_window` | `EEGSignalProcessor.compute_live_features` | Ventana real final de 4 s | 5.4151 | 10.4633 | 23.1306 | Benchmark crítico del cálculo live. Muy por debajo de 256 ms. |
| `real_capture.compute_quality_diagnostics.final_window` | `EEGSignalProcessor.compute_quality_diagnostics` | Diagnóstico sobre ventana real de 4 s | 5.9687 | 7.3465 | 8.2549 | Coste bajo del diagnóstico de calidad. |
| `real_capture.dsp_core_compute_features.final_window` | `DSPCore.compute_features` | DSP aislado sobre ventana real de 4 s | 5.2113 | 6.3767 | 7.3927 | Coste bajo del cálculo espectral multitaper. |
| `real_capture.live_feature_sweep_replay` | `replay_blocks_with_feature_hop` | Replay con hop real de 64 muestras | 2630.2501 | 2642.7249 | 2644.4776 | Reprocesa toda la captura, con 208 llamadas de features. |
| `real_capture.numpy_materialize_uv_matrix` | `blocks_to_uv_matrix/asarray` | Materialización auxiliar de matriz | 0.0015 | 0.0016 | 0.0031 | Coste auxiliar, no pertenece al loop real. |

## Interpretación temporal

### Cálculo live de features

La función crítica `EEGSignalProcessor.compute_live_features` presentó:

| Métrica | Valor |
| --- | ---: |
| Mediana | 5.4151 ms |
| P95 | 10.4633 ms |
| Máximo | 23.1306 ms |
| Presupuesto temporal por hop | 256 ms |

Porcentaje aproximado del presupuesto temporal:

| Caso | Cálculo | Resultado |
| --- | --- | ---: |
| Mediana | 5.4151 / 256 | 2.1 % |
| P95 | 10.4633 / 256 | 4.1 % |
| Máximo | 23.1306 / 256 | 9.0 % |

Incluso el máximo observado queda por debajo del 10 % del tiempo disponible entre hops. Esto indica que el cálculo espectral live no constituye un cuello de botella temporal en la placa.

### DSPCore aislado

`DSPCore.compute_features` presentó una mediana de 5.2113 ms y un máximo de 7.3927 ms sobre una ventana real de 4 s. Este resultado confirma que el cálculo PSD multitaper y la extracción de bandpowers/picos son compatibles con la ejecución en tiempo real.

### Diagnóstico de calidad

`compute_quality_diagnostics` presentó una mediana de 5.9687 ms y un máximo de 8.2549 ms. Su coste es bajo frente al hop de 256 ms y puede ejecutarse junto al cálculo de features sin comprometer la cadencia del sistema.

### Parser, receiver y buffer

El parser de bloques tuvo una mediana de 0.0489 ms. Los benchmarks de receiver y buffer se ejecutaron como replay completo de la captura. Para interpretarlos correctamente:

```text
receiver: 162.6736 ms / 1784 bloques ≈ 0.091 ms/bloque
buffer:    74.6253 ms / 1784 bloques ≈ 0.042 ms/bloque
```

Esto muestra que la recepción, validación básica e ingesta al ring buffer tienen un coste muy inferior al cálculo DSP.

### Replay con hop real

El replay completo con hop real procesó 208 llamadas de features en 2630.2501 ms de mediana:

```text
2630.2501 ms / 208 ≈ 12.65 ms/ciclo
```

Este ciclo incluye entrada de bloques, cálculo de features, diagnóstico de calidad y adaptación de sonificación. Frente a los 256 ms disponibles por hop:

```text
12.65 / 256 ≈ 4.9 %
```

El resultado confirma que, incluso simulando una secuencia completa de procesamiento con hop real, el sistema mantiene amplio margen temporal.

## Validación espectral complementaria

La validación espectral procesó 208 ventanas con ventana de 4.0 s y hop de 0.256 s. La calidad espectral mediana fue 0.974, con una fracción de ventanas de baja calidad o artefacto del 17.3 %.

Decisiones por banda:

| Banda | Mediana relativa | P95 relativo | Decisión |
| --- | ---: | ---: | --- |
| delta | 0.363 | 0.510 | Usar solo como apoyo |
| theta | 0.099 | 0.208 | Usar solo como apoyo |
| alpha | 0.050 | 0.114 | Necesita más capturas |
| beta | 0.108 | 0.340 | Usar solo como apoyo |
| gamma | 0.334 | 0.468 | No usar en tiempo real |

Estas conclusiones no afectan a la validez temporal del benchmark, pero sí son relevantes para interpretar la sonificación. La captura confirma que las bandas relativas y ratios son más defendibles que las potencias absolutas, y que beta/gamma deben tratarse con cautela por sensibilidad a artefactos.

## Relación con los controles de sonificación

El informe actual todavía usa los nombres internos existentes:

```text
activity, calmness, tension, rhythmic_density, register,
harmonic_stability, velocity_factor, note_probability
```

En esta fase no se modifican esos nombres para no mezclar la documentación de benchmarks con cambios de contrato en snapshot, WebUI o tools. No obstante, de cara a la redacción final del TFG se recomienda tratarlos como controles derivados de características espectrales y no como conceptos musicales abstractos.

Correspondencia interpretativa provisional:

| Nombre actual | Interpretación reportable |
| --- | --- |
| `activity` | Actividad global asociada a RMS, beta y gamma. |
| `calmness` | Predominio alpha frente a beta. |
| `tension` | Activación beta/gamma. |
| `rhythmic_density` | Densidad rítmica derivada de bandas rápidas y RMS. |
| `register` | Registro melódico asociado a actividad espectral rápida y pico dominante. |
| `harmonic_stability` | Estabilidad asociada a alpha/theta y menor RMS. |
| `velocity_factor` | Intensidad MIDI derivada de RMS y bandas rápidas. |
| `note_probability` | Probabilidad de generar nota a partir de la densidad. |

En una rama posterior se puede renombrar el snapshot y la UI a nombres directamente reportables (`alpha_drive`, `beta_gamma_drive`, etc.), pero no es necesario para documentar este benchmark temporal.

## Limitaciones de esta prueba

1. Se trata de una única ejecución de benchmark temporal.
2. La captura contiene artefactos transitorios, aunque no presenta pérdidas de adquisición.
3. Algunos archivos auxiliares de `benchmarks/reports/` quedaron con prefijo `_` porque la variable `TS` se perdió durante parte de la ejecución de shell. Los resultados principales sí tienen timestamp y son trazables.
4. No se midió latencia física end-to-end EEG -> nota -> MIDI OUT.
5. No se midió el coste del navegador WebUI ni la latencia física del UART MIDI.
6. El benchmark evalúa el coste de funciones Python sobre captura real, no el tiempo interno de SPI/DRDY en el firmware.

## ¿Es necesario repetir el benchmark?

La prueba actual es suficiente para documentar una validación temporal preliminar, porque:

- se ejecutó en la placa real,
- usó captura real,
- la adquisición no tuvo gaps ni status inválidos,
- el cálculo crítico quedó muy por debajo del hop de 256 ms,
- los resultados fueron versionados en Git.

No obstante, para una sección de resultados más robusta sería recomendable realizar al menos una repetición adicional con el mismo protocolo. Lo óptimo sería registrar tres ejecuciones independientes:

```text
bench_real_rest_60s_run1
bench_real_rest_60s_run2
bench_real_rest_60s_run3
```

Con tres repeticiones se podría reportar media y desviación entre ejecuciones, no solo percentiles dentro de una ejecución. Esta repetición no es imprescindible para afirmar que existe margen temporal, pero sí reforzaría la presentación del TFG.

Si se repite, se recomienda:

1. Mantener la misma rama y commit.
2. Exportar `PYTHONPATH` antes de ejecutar benchmarks para evitar el error de NumPy.
3. Usar condiciones con nombre único.
4. Guardar correctamente `TS` para evitar archivos con prefijo `_`.
5. No mezclar en el commit capturas antiguas no relacionadas.

Comandos recomendados para una repetición limpia:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
git checkout docs/final-v3-audit-update
git pull --ff-only origin docs/final-v3-audit-update
export BOARD_SITE_PACKAGES="/home/arduino/ArduinoApps/eeg_midi/.cache/.venv/lib/python3.13/site-packages"
export PYTHONPATH="$BOARD_SITE_PACKAGES:$PYTHONPATH"
TS=$(date +"%Y%m%d-%H%M%S")
CONDITION="bench_real_rest_60s_run2"
mkdir -p benchmarks/results benchmarks/reports
python3 python/tools/capture_eeg_quality.py --condition "$CONDITION" --duration 60 --timeout-extra 180 2>&1 | tee "benchmarks/reports/${TS}_${CONDITION}_capture_stdout.log"
CAPTURE_DIR=$(ls -td captures/*_${CONDITION} /app/captures/*_${CONDITION} 2>/dev/null | head -1)
python3 benchmarks/run_all_benchmarks.py --capture-dir "$CAPTURE_DIR" --tag "real_capture_${CONDITION}_${TS}" 2>&1 | tee "benchmarks/reports/${TS}_${CONDITION}_benchmark_stdout.log"
```

## Conclusión

Los benchmarks realizados sobre captura real muestran que el procesamiento Python de la placa dispone de margen temporal amplio. El cálculo live de features espectrales requiere una mediana de 5.4 ms frente a un presupuesto de 256 ms por hop, y el ciclo completo simulado de procesamiento con hop real requiere aproximadamente 12.65 ms por actualización. Por tanto, en la configuración evaluada, el cuello de botella principal del sistema no se encuentra en el cálculo DSP/sonificación de Python, sino en la calidad de señal, artefactos, estabilidad del montaje bioeléctrico y futuras mediciones de latencia física end-to-end.
