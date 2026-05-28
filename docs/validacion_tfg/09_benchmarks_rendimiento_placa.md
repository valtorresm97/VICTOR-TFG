# 09. Validación temporal del procesamiento en placa

## Objetivo

Este documento recoge los resultados de benchmark temporal obtenidos en la placa Arduino UNO Q/Linux durante la fase final de validación del sistema EEG-MIDI. Su objetivo es servir como base para la sección de validación y resultados del TFG, mostrando si el firmware del MCU y el procesamiento Python ejecutado en Linux disponen de margen suficiente para operar en tiempo real.

A diferencia de las pruebas sintéticas o de PC, esta validación se ha realizado sobre capturas reales adquiridas por el sistema completo:

```text
ADS1299 -> SPI/RDATAC -> firmware MCU -> filtros MCU -> Bridge.notify("eeg_block_uV") -> Python -> DSPCore -> sonificación
```

El análisis no pretende validar fisiológicamente la señal EEG por sí solo. Su finalidad principal es evaluar el coste computacional real del pipeline en la placa usando datos capturados por el hardware.

## Por qué el margen temporal de Python es de 256 ms

El cálculo de características espectrales en Python no se ejecuta para cada muestra individual recibida. El backend mantiene un buffer temporal y calcula nuevas características cuando se acumula un avance mínimo de muestras, definido por:

```text
FEATURE_HOP_SAMPLES = 64
FS_HZ = 250 Hz
```

Esto significa que, aunque la ventana analizada para extraer las características espectrales es de 4 s, la actualización de dichas características se produce cada 64 muestras nuevas. Con una frecuencia de muestreo de 250 Hz, el tiempo físico correspondiente a 64 muestras es:

```text
64 muestras / 250 muestras/s = 0.256 s = 256 ms
```

Por tanto, 256 ms es el presupuesto temporal aproximado disponible para completar un ciclo de procesamiento live antes de que llegue la siguiente actualización de features. Dentro de ese ciclo se incluyen las operaciones relevantes del lado Python/Linux: recepción del bloque, actualización del buffer, cálculo de características espectrales, diagnóstico de calidad y adaptación de los controles de sonificación.

La interpretación del benchmark se basa en comparar el tiempo medido de las funciones críticas con esos 256 ms. Si `compute_live_features` o el ciclo completo de procesamiento quedan claramente por debajo de ese valor, el sistema dispone de margen temporal para operar en tiempo real. En las pruebas realizadas, los tiempos medidos se sitúan en el orden de 5-13 ms, por lo que el procesamiento Python/Linux queda muy por debajo del presupuesto temporal disponible.

## Rama, commits y entorno

Los benchmarks se ejecutaron en la rama:

```text
docs/final-v3-audit-update
```

Artefactos principales:

| Elemento | Valor |
| --- | --- |
| Commit con parser de monitor MCU | `163dce7 Add MCU monitor benchmark parser` |
| Commit con primera captura de benchmark Python | `9f305a9 Capture board benchmark results` |
| Commit con captura MCU + Python | `5514fd9 Capture board benchmark results with MCU monitor metrics` |
| Python | `3.13.5` |
| Plataforma | `Linux-7.0.0-g122c2c22d838-aarch64-with-glibc2.41` |
| Placa | Arduino UNO Q / Linux App Lab |

Resultados versionados principales:

```text
benchmarks/results/20260528-105120_real_capture__benchmark_results.json
benchmarks/reports/20260528-105120_real_capture__benchmark_report.md
captures/20260528-104617_bench_real_rest_60s/

benchmarks/results/20260528-111703_bench_real_rest_60s_mcu_mcu_bench.csv
benchmarks/results/20260528-111703_bench_real_rest_60s_mcu_mcu_bench.json
benchmarks/reports/20260528-111703_bench_real_rest_60s_mcu_mcu_bench_report.md
benchmarks/reports/20260528-111703_bench_real_rest_60s_mcu_firmware_bench_monitor.log
benchmarks/results/20260528-111954_real_capture_bench_real_rest_60s_mcu_20260528-111703_benchmark_results.json
benchmarks/reports/20260528-111954_real_capture_bench_real_rest_60s_mcu_20260528-111703_benchmark_report.md
captures/20260528-111723_bench_real_rest_60s_mcu/
```

## Capturas reales empleadas

Se realizaron dos ejecuciones principales:

| Captura | Condición | Uso |
| --- | --- | --- |
| `captures/20260528-104617_bench_real_rest_60s` | `bench_real_rest_60s` | Benchmark inicial Python/Linux sobre captura real. |
| `captures/20260528-111723_bench_real_rest_60s_mcu` | `bench_real_rest_60s_mcu` | Benchmark completo con resultados MCU copiados del Monitor y benchmark Python/Linux sobre la misma captura. |

La primera captura generó 14272 muestras en 1784 bloques, sin gaps de bloque, sin gaps de muestra, sin status ADS1299 inválidos y sin bloques malformados. La segunda captura generó 14368 muestras en 1796 bloques y se usó para completar la validación con métricas del firmware/MCU.

## Criterios temporales de referencia

### Python/Linux

El backend calcula características espectrales con:

```text
FEATURE_HOP_SAMPLES = 64
FS_HZ = 250 Hz
```

Por tanto, el tiempo disponible entre actualizaciones de features es:

```text
64 / 250 = 0.256 s = 256 ms
```

Este valor se usa como referencia para valorar si el cálculo live de Python dispone de margen suficiente.

### Firmware/MCU

El firmware empaqueta y publica bloques de 8 muestras:

```text
BLOCK_SAMPLES = 8
FS_HZ = 250 Hz
```

Por tanto, el periodo asociado a un bloque completo es:

```text
8 / 250 = 0.032 s = 32 ms
```

Este valor se usa como referencia orientativa para interpretar el coste de filtrado, publicación por Bridge y máximos de loop del MCU.

## Resultados Python/Linux sobre captura real

### Primera ejecución: `bench_real_rest_60s`

| Benchmark | Función | Escenario | Mediana ms | P95 ms | Máx ms | Interpretación |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `real_capture.parse_eeg_block_values.first_block` | `parse_eeg_block_values` | Primer bloque real | 0.0489 | 0.0502 | 0.1404 | Coste despreciable del parser por bloque. |
| `real_capture.receiver_replay_all_blocks` | `EEGReceiver.eeg_block_uV` | Replay de toda la captura | 162.6736 | 252.6365 | 318.8870 | Tiempo de reprocesar 1784 bloques completos; no es tiempo por bloque live. |
| `real_capture.buffer_replay_all_blocks` | `EEGSignalProcessor.add_block_uV` | Replay de toda la captura al ring buffer | 74.6253 | 75.5110 | 75.9692 | Tiempo de reinyectar toda la captura; no es tiempo por bloque live. |
| `real_capture.compute_live_features.final_window` | `EEGSignalProcessor.compute_live_features` | Ventana real final de 4 s | 5.4151 | 10.4633 | 23.1306 | Benchmark crítico del cálculo live. Muy por debajo de 256 ms. |
| `real_capture.compute_quality_diagnostics.final_window` | `EEGSignalProcessor.compute_quality_diagnostics` | Diagnóstico sobre ventana real de 4 s | 5.9687 | 7.3465 | 8.2549 | Coste bajo del diagnóstico de calidad. |
| `real_capture.dsp_core_compute_features.final_window` | `DSPCore.compute_features` | DSP aislado sobre ventana real de 4 s | 5.2113 | 6.3767 | 7.3927 | Coste bajo del cálculo espectral multitaper. |
| `real_capture.live_feature_sweep_replay` | `replay_blocks_with_feature_hop` | Replay con hop real de 64 muestras | 2630.2501 | 2642.7249 | 2644.4776 | Reprocesa toda la captura, con 208 llamadas de features. |

### Segunda ejecución: `bench_real_rest_60s_mcu`

| Benchmark | Función | Escenario | Mediana ms | P95 ms | Máx ms | Interpretación |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `real_capture.parse_eeg_block_values.first_block` | `parse_eeg_block_values` | Primer bloque real | 0.0492 | 0.0516 | 0.1084 | Coste despreciable del parser por bloque. |
| `real_capture.receiver_replay_all_blocks` | `EEGReceiver.eeg_block_uV` | Replay de 1796 bloques | 169.4442 | 245.3876 | 329.4355 | Tiempo de reprocesar toda la captura; no es tiempo por bloque live. |
| `real_capture.buffer_replay_all_blocks` | `EEGSignalProcessor.add_block_uV` | Replay de 1796 bloques al ring buffer | 76.1546 | 76.3177 | 76.3869 | Ingesta completa de la captura al buffer. |
| `real_capture.compute_live_features.final_window` | `EEGSignalProcessor.compute_live_features` | Ventana real final de 4 s | 5.2158 | 6.4103 | 6.9831 | Cálculo live principal. Muy por debajo de 256 ms. |
| `real_capture.compute_quality_diagnostics.final_window` | `EEGSignalProcessor.compute_quality_diagnostics` | Diagnóstico sobre ventana real de 4 s | 6.0806 | 8.1642 | 9.4764 | Coste bajo frente al hop. |
| `real_capture.dsp_core_compute_features.final_window` | `DSPCore.compute_features` | DSP aislado sobre ventana real de 4 s | 5.1967 | 6.2634 | 6.5716 | Coste estable del cálculo espectral. |
| `real_capture.live_feature_sweep_replay` | `replay_blocks_with_feature_hop` | Replay con hop real de 64 muestras | 2624.4660 | 2635.7004 | 2640.8206 | Reprocesa toda la captura, con 209 llamadas de features. |

## Interpretación Python/Linux

La función crítica `EEGSignalProcessor.compute_live_features` presentó en la segunda ejecución:

| Métrica | Valor |
| --- | ---: |
| Mediana | 5.2158 ms |
| P95 | 6.4103 ms |
| Máximo | 6.9831 ms |
| Presupuesto temporal por hop | 256 ms |

Porcentaje aproximado del presupuesto temporal:

| Caso | Cálculo | Resultado |
| --- | --- | ---: |
| Mediana | 5.2158 / 256 | 2.0 % |
| P95 | 6.4103 / 256 | 2.5 % |
| Máximo | 6.9831 / 256 | 2.7 % |

La primera ejecución ya mostraba margen amplio, con un máximo de 23.1306 ms, equivalente aproximadamente al 9.0 % del presupuesto de 256 ms. La segunda ejecución confirma el resultado con tiempos todavía más estables. Por tanto, el cálculo DSP/sonificación en Python no constituye un cuello de botella temporal.

El replay completo con hop real de la segunda captura procesó 209 llamadas de features en 2624.4660 ms de mediana:

```text
2624.4660 ms / 209 ≈ 12.56 ms/ciclo
```

Frente a los 256 ms disponibles por hop:

```text
12.56 / 256 ≈ 4.9 %
```

Este ciclo incluye entrada de bloques, cálculo de features, diagnóstico de calidad y adaptación de sonificación. El resultado confirma que el pipeline Python mantiene amplio margen temporal incluso al reproducir la lógica de hop real sobre una captura completa.

## Benchmarks del firmware/MCU

Para no alterar el transporte real de la aplicación, no se añadió ningún `Bridge.notify` adicional para exportar métricas del MCU. En su lugar, se copió el log original del Monitor/App Lab y se parseó automáticamente con `python/tools/parse_mcu_bench_monitor.py`. De este modo, el benchmark del MCU conserva el comportamiento real del firmware: adquisición, filtrado, cola TX y publicación de bloques EEG mediante el `Bridge.notify("eeg_block_uV")` ya existente.

El informe MCU parseó:

| Métrica | Valor |
| --- | ---: |
| Ventanas `[BENCH] EEG_MIDI` parseadas | 94 |
| `gen` acumulado final | 534534 |
| `sent` acumulado final | 532112 |
| `blk_enq` acumulado final | 66514 |
| `blk_sent` acumulado final | 66514 |
| `notify_calls` acumulado final | 66514 |
| `qmax_global` | 1 |
| `drops_total` | 0 |
| `pub_burst_global` | 1 |
| `notify_max_global_us` | 11587 µs |
| `loop_max_global_us` | 32494 µs |

### Resumen por ventanas del MCU

| Métrica MCU | Mín | Mediana | Media | Máx | Interpretación |
| --- | ---: | ---: | ---: | ---: | --- |
| `gen/s` | 222.750 | 240.200 | 238.646 | 240.800 | Tasa de muestras generadas próxima a 240 Hz en mediana. |
| `sent/s` | 222.350 | 240.000 | 238.651 | 241.600 | Tasa de muestras publicadas similar a la generada. |
| `blk_sent/s` | 27.790 | 30.000 | 29.830 | 30.200 | Aproximadamente 30 bloques/s de 8 muestras. |
| `filt_avg_us` | 5.010 | 5.050 | 5.065 | 5.200 | Filtrado digital extremadamente ligero. |
| `filt_max_us_win` | 14 | 15 | 14.798 | 17 | Máximo de filtrado por ventana muy bajo. |
| `notify_avg_us` | 3219.890 | 3367.250 | 3592.776 | 5741.420 | Coste medio de publicación por Bridge por bloque. |
| `notify_eff_us/sample` | 402.490 | 420.905 | 449.097 | 717.680 | Coste efectivo por muestra al repartir el notify del bloque. |
| `notify_max_us_win` | 7297 | 7666 | 7859.511 | 11528 | Máximo por ventana del envío Bridge. |
| `qmax_win` | 1 | 1 | 1 | 1 | La cola TX no acumuló más de un bloque. |
| `drops_win` | 0 | 0 | 0 | 0 | No hubo drops de cola TX en ninguna ventana parseada. |
| `lag_win` | 4 | 5 | 11.649 | 83 | Eventos de DRDY pendientes/catch-up; existen picos aislados. |
| `sample_iter_max_us_win` | 273 | 277 | 277.894 | 289 | Máximo por iteración de muestra bajo. |
| `loop_max_us_win` | 9409 | 10829 | 10674.106 | 12886 | Máximo de loop por ventana por debajo de 13 ms. |
| `pub_burst_win` | 1 | 1 | 1 | 1 | El firmware publicó como máximo un bloque por ráfaga. |

### Interpretación MCU

El filtrado del MCU tiene un coste despreciable frente al periodo de muestreo: `filt_avg_us` se mantiene alrededor de 5 µs y el máximo por ventana de filtrado no supera 17 µs. El coste dominante del lado MCU no es el filtrado, sino la publicación de bloques mediante Bridge, con `notify_avg_us` mediano de 3367.250 µs y máximo de ventana de 11528 µs.

Incluso ese máximo de `notify_max_us_win` queda por debajo del periodo asociado a un bloque de 8 muestras:

```text
11528 µs = 11.528 ms < 32 ms
```

El máximo de loop por ventana fue 12886 µs, también inferior a 32 ms:

```text
12886 µs = 12.886 ms < 32 ms
```

La cola TX se mantuvo controlada:

```text
qmax_global = 1
drops_total = 0
pub_burst_global = 1
```

Esto indica que el firmware no acumuló backlog significativo ni descartó bloques durante las ventanas analizadas. La tasa mediana de publicación fue de 30 bloques/s, coherente con bloques de 8 muestras en una adquisición cercana a 240 Hz efectiva durante esta prueba.

Los picos de `lag_win` muestran que existen ventanas con interrupciones DRDY pendientes o catch-up, con máximo 83. Sin embargo, estos picos no se tradujeron en drops de cola TX ni en crecimiento de backlog. Además, la captura Python asociada conservó continuidad suficiente para ejecutar el benchmark sobre 1796 bloques y 14368 frames.

## Comparación conjunta MCU + Python/Linux

| Parte del sistema | Métrica crítica | Resultado | Presupuesto/Referencia | Conclusión |
| --- | --- | ---: | ---: | --- |
| MCU | `filt_avg_us` mediano | 5.050 µs | 4000 µs por muestra a 250 Hz | Coste de filtrado despreciable. |
| MCU | `notify_avg_us` mediano | 3367.250 µs | 32 ms por bloque de 8 muestras | Publicación Bridge asumible. |
| MCU | `notify_max_us_win` máximo | 11528 µs | 32 ms por bloque de 8 muestras | Pico inferior al periodo de bloque. |
| MCU | `loop_max_us_win` máximo | 12886 µs | 32 ms por bloque de 8 muestras | Loop máximo de ventana con margen. |
| MCU | `drops_total` | 0 | 0 esperado | Sin pérdidas por cola TX. |
| MCU | `qmax_global` | 1 | Cola estable | Sin acumulación significativa. |
| Python/Linux | `compute_live_features` mediano | 5.2158 ms | 256 ms por hop | Coste muy bajo. |
| Python/Linux | `compute_live_features` máximo | 6.9831 ms | 256 ms por hop | Amplio margen temporal. |
| Python/Linux | ciclo replay con hop real | 12.56 ms/ciclo | 256 ms por hop | Pipeline Python completo con margen. |

La validación conjunta indica que el sistema dispone de margen tanto en el MCU como en Python/Linux. En el MCU, el filtrado es muy ligero y la publicación por Bridge no provoca crecimiento de cola ni drops. En Python/Linux, el cálculo espectral, diagnóstico de calidad y adaptación de sonificación quedan muy por debajo del hop de 256 ms.

## Validación espectral complementaria

La validación espectral de la primera captura procesó 208 ventanas con ventana de 4.0 s y hop de 0.256 s. La calidad espectral mediana fue 0.974, con una fracción de ventanas de baja calidad o artefacto del 17.3 %.

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

## Limitaciones

1. La validación temporal se ha realizado sobre capturas reales concretas, no sobre una batería estadística extensa de sujetos y condiciones.
2. Las capturas contienen artefactos transitorios, por lo que no deben usarse por sí solas para extraer conclusiones fisiológicas fuertes.
3. Los benchmarks MCU se obtuvieron copiando el Monitor/App Lab para no añadir tráfico extra por Bridge. El copiado manual se mitigó usando un parser automático que genera CSV/JSON/Markdown.
4. El log MCU incluye líneas de diagnóstico como `Frame invalido / error sincronía`. Estas incidencias aparecen en el Monitor, pero las métricas de cola TX no muestran drops y el benchmark Python se ejecutó sobre la captura real generada.
5. No se midió latencia física end-to-end EEG -> nota -> MIDI OUT.
6. No se midió el coste del navegador WebUI ni la latencia física del UART MIDI.
7. Los resultados temporales son representativos de la configuración evaluada, pero pueden variar si se modifican frecuencia de muestreo, número de canales, tamaño de bloque, carga de UI, transporte MIDI/LED o estrategia de publicación.

## Conclusión

Los benchmarks realizados sobre capturas reales muestran que el sistema dispone de margen temporal amplio tanto en firmware/MCU como en Python/Linux.

En el MCU, el filtrado digital tiene una mediana de aproximadamente 5 µs, mientras que el coste dominante es la publicación por Bridge, con `notify_avg_us` mediano de 3367 µs y máximo de ventana de 11528 µs. Estos valores quedan por debajo del periodo de bloque de 32 ms. Además, la cola TX no acumuló más de un bloque y no se registraron drops.

En Python/Linux, el cálculo live de features espectrales requiere una mediana de 5.2158 ms frente a un presupuesto de 256 ms por hop. El replay completo con hop real requiere aproximadamente 12.56 ms por ciclo de procesamiento, también muy por debajo de los 256 ms disponibles.

Por tanto, en la configuración evaluada, el cuello de botella principal del sistema no se encuentra en el cálculo DSP/sonificación de Python ni en el filtrado del MCU. Los aspectos más críticos para fases posteriores son la calidad de señal, la presencia de artefactos, la estabilidad del montaje bioeléctrico y la validación de latencia física end-to-end EEG -> MIDI OUT.
