# 09. Validacion temporal del procesamiento en placa - final-v4

## Objetivo

Este documento recoge los resultados de benchmark temporal obtenidos en la placa Arduino UNO Q/Linux durante la fase final de validacion del sistema EEG-MIDI. Su objetivo es servir como base para la seccion de validacion y resultados del TFG, mostrando si el firmware del MCU y el procesamiento Python ejecutado en Linux disponen de margen suficiente para operar en tiempo real.

Los benchmarks se realizaron originalmente en la rama de documentacion/validacion `docs/final-v3-audit-update` y sus artefactos se integraron despues en la linea documental final-v4. Por tanto, los datos numericos deben leerse como evidencia temporal real de placa conservada dentro del estado integrado actual:

```text
firmware-final-v4
```

A diferencia de las pruebas sinteticas o de PC, esta validacion se realizo sobre capturas reales adquiridas por el sistema completo:

```text
ADS1299 -> SPI/RDATAC -> firmware MCU -> filtros MCU -> Bridge.notify("eeg_block_uV") -> Python -> DSPCore -> quality gate -> sonificacion
```

El analisis no pretende validar fisiologicamente la senal EEG por si solo. Su finalidad principal es evaluar el coste computacional real del pipeline en la placa usando datos capturados por el hardware.

## Configuracion interpretativa final-v4

La configuracion de referencia actual del sistema es:

```text
ADS_DIAGNOSTIC_MODE=5
ADS_MODE=bias_ch1_only_loff_off
montage=ear_eeg_ch1_only
CH1 = canal EEG principal
CH2-CH4 = conservados por contrato, no EEG activo en la sesion final
MIDI fisico = Serial1/D1 con TX invertido
LED matrix = desactivada por defecto
```

Los benchmarks temporales miden rendimiento de firmware/Python. No deben mezclarse con la validacion fisiologica de capturas multi-condicion, que se documenta en `10_resultados_captura_final_laboratorio.md` y en los reportajes de `s01_20260528`.

## Por que el margen temporal de Python es de 256 ms

El calculo de caracteristicas espectrales en Python no se ejecuta para cada muestra individual recibida. El backend mantiene un buffer temporal y calcula nuevas caracteristicas cuando se acumula un avance minimo de muestras, definido por:

```text
FEATURE_HOP_SAMPLES = 64
FS_HZ = 250 Hz
```

Esto significa que, aunque la ventana analizada para extraer las caracteristicas espectrales es de 4 s, la actualizacion de dichas caracteristicas se produce cada 64 muestras nuevas. Con una frecuencia de muestreo de 250 Hz, el tiempo fisico correspondiente a 64 muestras es:

```text
64 muestras / 250 muestras/s = 0.256 s = 256 ms
```

Por tanto, 256 ms es el presupuesto temporal aproximado disponible para completar un ciclo de procesamiento live antes de que llegue la siguiente actualizacion de features. Dentro de ese ciclo se incluyen las operaciones relevantes del lado Python/Linux: recepcion del bloque, actualizacion del buffer, calculo de caracteristicas espectrales, diagnostico de calidad y adaptacion de los controles de sonificacion.

La interpretacion del benchmark se basa en comparar el tiempo medido de las funciones criticas con esos 256 ms. Si `compute_live_features` o el ciclo completo de procesamiento quedan claramente por debajo de ese valor, el sistema dispone de margen temporal para operar en tiempo real. En las pruebas realizadas, los tiempos medidos se situan en el orden de 5-13 ms, por lo que el procesamiento Python/Linux queda muy por debajo del presupuesto temporal disponible.

## Metodologia de adquisicion de benchmarks

La metodologia se diseno para que los resultados fueran trazables y reproducibles dentro del repositorio. El criterio principal fue medir el sistema real ejecutandose en la placa, sin sustituir la entrada por senales sinteticas y sin anadir trafico extra al transporte principal.

### Principios de la prueba

1. Ejecutar los benchmarks en la Arduino UNO Q/Linux, no en PC.
2. Usar capturas reales generadas por la aplicacion y almacenadas en `captures/`.
3. Medir el coste Python/Linux sobre datos reales ya adquiridos por el hardware.
4. Conservar las metricas existentes del firmware/MCU sin modificar el transporte `Bridge.notify("eeg_block_uV")`.
5. Guardar todos los artefactos en `benchmarks/results/`, `benchmarks/reports/` y `captures/`.
6. Versionar en Git los resultados y los informes generados.

### Codigo utilizado o creado para esta validacion

| Archivo | Tipo | Funcion dentro de la validacion |
| --- | --- | --- |
| `python/tools/capture_eeg_quality.py` | Herramienta existente de captura | Solicita al backend una captura real durante una duracion definida y genera una carpeta `captures/<timestamp>_<condition>/`. |
| `benchmarks/benchmark_core.py` | Codigo creado para benchmarks | Utilidades comunes de medicion temporal, resumen estadistico y escritura de resultados JSON/CSV/Markdown. |
| `benchmarks/benchmark_real_capture.py` | Codigo creado para benchmarks | Lee `eeg_timeseries.csv`, reconstruye bloques reales por `block_idx` y mide funciones criticas Python sobre la captura real. |
| `benchmarks/run_all_benchmarks.py` | Codigo creado para benchmarks | Ejecuta el conjunto de benchmarks Python/Linux sobre una captura real y guarda resultados en `benchmarks/results/` y `benchmarks/reports/`. |
| `python/tools/parse_mcu_bench_monitor.py` | Codigo creado para benchmarks MCU | Parsea el Monitor/App Lab con bloques `[BENCH] EEG_MIDI` y genera CSV/JSON/Markdown con metricas del firmware. |
| `sketch/bench.h` | Instrumentacion firmware existente | Define contadores y acumuladores de rendimiento del MCU: muestras, bloques, notify, tiempos de filtro, loop, cola TX, drops y lag. |
| `sketch/sketch.ino` | Firmware principal | Imprime periodicamente en Monitor/App Lab los bloques `[BENCH] EEG_MIDI` sin anadir trafico extra por Bridge. |

### Procedimiento de captura Python/Linux

La captura real se tomo con la aplicacion App Lab en ejecucion y el backend activo. El comando utilizado fue equivalente a:

```bash
python3 python/tools/capture_eeg_quality.py \
  --condition bench_real_rest_60s_mcu \
  --duration 60 \
  --timeout-extra 180
```

Esta herramienta no genera una senal artificial. Tampoco calcula el quality gate. En su lugar, solicita al backend que grabe los datos reales que ya llegan desde el evento `eeg_block_uV`. El resultado es una carpeta de captura con, como minimo:

```text
captures/<timestamp>_<condition>/
  eeg_timeseries.csv
  metadata.json
```

El archivo `eeg_timeseries.csv` contiene las muestras recibidas por Python, agrupadas por bloque y con columnas de estado y canales en microvoltios. Ese CSV es la fuente de entrada de los benchmarks Python/Linux.

### Procedimiento de benchmark Python/Linux

Una vez generada la captura, el benchmark se ejecuto sobre el CSV real:

```bash
python3 benchmarks/run_all_benchmarks.py \
  --capture-dir "$CAPTURE_DIR" \
  --tag "real_capture_${CONDITION}_${TS}"
```

Internamente, `benchmark_real_capture.py` realiza los siguientes pasos:

1. Lee `eeg_timeseries.csv`.
2. Agrupa las filas por `block_idx`.
3. Reconstruye bloques reales compatibles con el contrato `eeg_block_uV`.
4. Mide el parser `parse_eeg_block_values` sobre payload real.
5. Reinyecta bloques reales en `EEGReceiver.eeg_block_uV`.
6. Reinyecta bloques reales en `EEGSignalProcessor.add_block_uV`.
7. Calcula `compute_live_features` sobre una ventana real de 4 s.
8. Calcula `compute_quality_diagnostics` sobre la misma ventana.
9. Mide `DSPCore.compute_features` de forma aislada.
10. Simula el replay completo con hop real de 64 muestras.

Los resultados se guardan automaticamente en:

```text
benchmarks/results/<timestamp>_<tag>_benchmark_results.json
benchmarks/results/<timestamp>_<tag>_benchmark_results.csv
benchmarks/reports/<timestamp>_<tag>_benchmark_report.md
```

### Procedimiento de benchmark firmware/MCU

El lado MCU ya imprimia metricas de rendimiento en el Monitor/App Lab mediante los bloques `[BENCH] EEG_MIDI`. Se decidio no anadir un nuevo evento `Bridge.notify("mcu_bench")`, porque eso habria introducido trafico adicional en el mismo transporte que se queria evaluar.

Por ese motivo, el procedimiento elegido fue:

1. Mantener el firmware sin cambios durante la adquisicion.
2. Copiar manualmente del Monitor/App Lab los bloques `[BENCH] EEG_MIDI` generados durante la prueba.
3. Guardar el texto original en:

```text
benchmarks/reports/<TS>_<CONDITION>_firmware_bench_monitor.log
```

4. Parsear automaticamente ese log con:

```bash
python3 python/tools/parse_mcu_bench_monitor.py \
  "benchmarks/reports/${TS}_${CONDITION}_firmware_bench_monitor.log" \
  --condition "$CONDITION" \
  --out-csv "benchmarks/results/${TS}_${CONDITION}_mcu_bench.csv" \
  --out-json "benchmarks/results/${TS}_${CONDITION}_mcu_bench.json" \
  --out-md "benchmarks/reports/${TS}_${CONDITION}_mcu_bench_report.md"
```

El parser extrae las metricas de las lineas `rate`, `time`, `queue`, `jitter`, `DRDY`, `total` y `peak`, generando una tabla por ventanas y un resumen estadistico. De esta forma, aunque la copia inicial del Monitor sea manual, la transformacion a datos tabulados es automatica y reproducible.

### Artefactos conservados

| Tipo de artefacto | Ruta |
| --- | --- |
| Captura real | `captures/<timestamp>_<condition>/` |
| Resultados Python/Linux en JSON/CSV | `benchmarks/results/*benchmark_results.json`, `benchmarks/results/*benchmark_results.csv` |
| Informe Python/Linux en Markdown | `benchmarks/reports/*benchmark_report.md` |
| Log crudo MCU copiado del Monitor | `benchmarks/reports/*firmware_bench_monitor.log` |
| CSV/JSON de metricas MCU | `benchmarks/results/*mcu_bench.csv`, `benchmarks/results/*mcu_bench.json` |
| Informe MCU en Markdown | `benchmarks/reports/*mcu_bench_report.md` |
| Snapshot/logs finales del backend | `benchmarks/reports/*snapshot_final.json`, `benchmarks/reports/*backend_stdout_final.log` |

Esta organizacion permite relacionar cada resultado temporal con la captura real que lo origino y con el estado del sistema durante la prueba.

## Rama, commits y entorno

Los benchmarks se ejecutaron originalmente en la rama:

```text
docs/final-v3-audit-update
```

En el estado actual, esos artefactos se conservan dentro de la documentacion integrada final-v4. No se han regenerado los datos numericos en esta fase; solo se ha reajustado el relato documental para que sea coherente con `firmware-final-v4`.

Artefactos principales:

| Elemento | Valor |
| --- | --- |
| Commit con parser de monitor MCU | `163dce7 Add MCU monitor benchmark parser` |
| Commit con primera captura de benchmark Python | `9f305a9 Capture board benchmark results` |
| Commit con captura MCU + Python | `5514fd9 Capture board benchmark results with MCU monitor metrics` |
| Commit con documentacion MCU + Python | `8406e61 Include MCU benchmark results in board validation document` |
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

| Captura | Condicion | Uso |
| --- | --- | --- |
| `captures/20260528-104617_bench_real_rest_60s` | `bench_real_rest_60s` | Benchmark inicial Python/Linux sobre captura real. |
| `captures/20260528-111723_bench_real_rest_60s_mcu` | `bench_real_rest_60s_mcu` | Benchmark completo con resultados MCU copiados del Monitor y benchmark Python/Linux sobre la misma captura. |

La primera captura genero 14272 muestras en 1784 bloques, sin gaps de bloque, sin gaps de muestra, sin status ADS1299 invalidos y sin bloques malformados. La segunda captura genero 14368 muestras en 1796 bloques y se uso para completar la validacion con metricas del firmware/MCU.

## Criterios temporales de referencia

### Python/Linux

El backend calcula caracteristicas espectrales con:

```text
FEATURE_HOP_SAMPLES = 64
FS_HZ = 250 Hz
```

Por tanto, el tiempo disponible entre actualizaciones de features es:

```text
64 / 250 = 0.256 s = 256 ms
```

Este valor se usa como referencia para valorar si el calculo live de Python dispone de margen suficiente.

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

Este valor se usa como referencia orientativa para interpretar el coste de filtrado, publicacion por Bridge y maximos de loop del MCU.

## Resultados Python/Linux sobre captura real

### Primera ejecucion: `bench_real_rest_60s`

| Benchmark | Funcion | Escenario | Mediana ms | P95 ms | Max ms | Interpretacion |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `real_capture.parse_eeg_block_values.first_block` | `parse_eeg_block_values` | Primer bloque real | 0.0489 | 0.0502 | 0.1404 | Coste despreciable del parser por bloque. |
| `real_capture.receiver_replay_all_blocks` | `EEGReceiver.eeg_block_uV` | Replay de toda la captura | 162.6736 | 252.6365 | 318.8870 | Tiempo de reprocesar 1784 bloques completos; no es tiempo por bloque live. |
| `real_capture.buffer_replay_all_blocks` | `EEGSignalProcessor.add_block_uV` | Replay de toda la captura al ring buffer | 74.6253 | 75.5110 | 75.9692 | Tiempo de reinyectar toda la captura; no es tiempo por bloque live. |
| `real_capture.compute_live_features.final_window` | `EEGSignalProcessor.compute_live_features` | Ventana real final de 4 s | 5.4151 | 10.4633 | 23.1306 | Benchmark critico del calculo live. Muy por debajo de 256 ms. |
| `real_capture.compute_quality_diagnostics.final_window` | `EEGSignalProcessor.compute_quality_diagnostics` | Diagnostico sobre ventana real de 4 s | 5.9687 | 7.3465 | 8.2549 | Coste bajo del diagnostico de calidad. |
| `real_capture.dsp_core_compute_features.final_window` | `DSPCore.compute_features` | DSP aislado sobre ventana real de 4 s | 5.2113 | 6.3767 | 7.3927 | Coste bajo del calculo espectral multitaper. |
| `real_capture.live_feature_sweep_replay` | `replay_blocks_with_feature_hop` | Replay con hop real de 64 muestras | 2630.2501 | 2642.7249 | 2644.4776 | Reprocesa toda la captura, con 208 llamadas de features. |

### Segunda ejecucion: `bench_real_rest_60s_mcu`

| Benchmark | Funcion | Escenario | Mediana ms | P95 ms | Max ms | Interpretacion |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `real_capture.parse_eeg_block_values.first_block` | `parse_eeg_block_values` | Primer bloque real | 0.0492 | 0.0516 | 0.1084 | Coste despreciable del parser por bloque. |
| `real_capture.receiver_replay_all_blocks` | `EEGReceiver.eeg_block_uV` | Replay de 1796 bloques | 169.4442 | 245.3876 | 329.4355 | Tiempo de reprocesar toda la captura; no es tiempo por bloque live. |
| `real_capture.buffer_replay_all_blocks` | `EEGSignalProcessor.add_block_uV` | Replay de 1796 bloques al ring buffer | 76.1546 | 76.3177 | 76.3869 | Ingesta completa de la captura al buffer. |
| `real_capture.compute_live_features.final_window` | `EEGSignalProcessor.compute_live_features` | Ventana real final de 4 s | 5.2158 | 6.4103 | 6.9831 | Calculo live principal. Muy por debajo de 256 ms. |
| `real_capture.compute_quality_diagnostics.final_window` | `EEGSignalProcessor.compute_quality_diagnostics` | Diagnostico sobre ventana real de 4 s | 6.0806 | 8.1642 | 9.4764 | Coste bajo frente al hop. |
| `real_capture.dsp_core_compute_features.final_window` | `DSPCore.compute_features` | DSP aislado sobre ventana real de 4 s | 5.1967 | 6.2634 | 6.5716 | Coste estable del calculo espectral. |
| `real_capture.live_feature_sweep_replay` | `replay_blocks_with_feature_hop` | Replay con hop real de 64 muestras | 2624.4660 | 2635.7004 | 2640.8206 | Reprocesa toda la captura, con 209 llamadas de features. |

## Interpretacion Python/Linux

La funcion critica `EEGSignalProcessor.compute_live_features` presento en la segunda ejecucion:

| Metrica | Valor |
| --- | ---: |
| Mediana | 5.2158 ms |
| P95 | 6.4103 ms |
| Maximo | 6.9831 ms |
| Presupuesto temporal por hop | 256 ms |

Porcentaje aproximado del presupuesto temporal:

| Caso | Calculo | Resultado |
| --- | --- | ---: |
| Mediana | 5.2158 / 256 | 2.0 % |
| P95 | 6.4103 / 256 | 2.5 % |
| Maximo | 6.9831 / 256 | 2.7 % |

La primera ejecucion ya mostraba margen amplio, con un maximo de 23.1306 ms, equivalente aproximadamente al 9.0 % del presupuesto de 256 ms. La segunda ejecucion confirma el resultado con tiempos todavia mas estables. Por tanto, el calculo DSP/sonificacion en Python no constituye un cuello de botella temporal.

El replay completo con hop real de la segunda captura proceso 209 llamadas de features en 2624.4660 ms de mediana:

```text
2624.4660 ms / 209 â‰ˆ 12.56 ms/ciclo
```

Frente a los 256 ms disponibles por hop:

```text
12.56 / 256 â‰ˆ 4.9 %
```

Este ciclo incluye entrada de bloques, calculo de features, diagnostico de calidad y adaptacion de sonificacion. El resultado confirma que el pipeline Python mantiene amplio margen temporal incluso al reproducir la logica de hop real sobre una captura completa.

## Benchmarks del firmware/MCU

Para no alterar el transporte real de la aplicacion, no se anadio ningun `Bridge.notify` adicional para exportar metricas del MCU. En su lugar, se copio el log original del Monitor/App Lab y se parseo automaticamente con `python/tools/parse_mcu_bench_monitor.py`. De este modo, el benchmark del MCU conserva el comportamiento real del firmware: adquisicion, filtrado, cola TX y publicacion de bloques EEG mediante el `Bridge.notify("eeg_block_uV")` ya existente.

El informe MCU parseo:

| Metrica | Valor |
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
| `notify_max_global_us` | 11587 Âµs |
| `loop_max_global_us` | 32494 Âµs |

### Resumen por ventanas del MCU

| Metrica MCU | Min | Mediana | Media | Max | Interpretacion |
| --- | ---: | ---: | ---: | ---: | --- |
| `gen/s` | 222.750 | 240.200 | 238.646 | 240.800 | Tasa de muestras generadas proxima a 240 Hz en mediana durante esta prueba. |
| `sent/s` | 222.350 | 240.000 | 238.651 | 241.600 | Tasa de muestras publicadas similar a la generada. |
| `blk_sent/s` | 27.790 | 30.000 | 29.830 | 30.200 | Aproximadamente 30 bloques/s de 8 muestras. |
| `filt_avg_us` | 5.010 | 5.050 | 5.065 | 5.200 | Filtrado digital extremadamente ligero. |
| `filt_max_us_win` | 14 | 15 | 14.798 | 17 | Maximo de filtrado por ventana muy bajo. |
| `notify_avg_us` | 3219.890 | 3367.250 | 3592.776 | 5741.420 | Coste medio de publicacion por Bridge por bloque. |
| `notify_eff_us/sample` | 402.490 | 420.905 | 449.097 | 717.680 | Coste efectivo por muestra al repartir el notify del bloque. |
| `notify_max_us_win` | 7297 | 7666 | 7859.511 | 11528 | Maximo por ventana del envio Bridge. |
| `qmax_win` | 1 | 1 | 1 | 1 | La cola TX no acumulo mas de un bloque. |
| `drops_win` | 0 | 0 | 0 | 0 | No hubo drops de cola TX en ninguna ventana parseada. |
| `lag_win` | 4 | 5 | 11.649 | 83 | Eventos de DRDY pendientes/catch-up; existen picos aislados. |
| `sample_iter_max_us_win` | 273 | 277 | 277.894 | 289 | Maximo por iteracion de muestra bajo. |
| `loop_max_us_win` | 9409 | 10829 | 10674.106 | 12886 | Maximo de loop por ventana por debajo de 13 ms. |
| `pub_burst_win` | 1 | 1 | 1 | 1 | El firmware publico como maximo un bloque por rafaga. |

### Interpretacion MCU

El filtrado del MCU tiene un coste despreciable frente al periodo de muestreo: `filt_avg_us` se mantiene alrededor de 5 Âµs y el maximo por ventana de filtrado no supera 17 Âµs. El coste dominante del lado MCU no es el filtrado, sino la publicacion de bloques mediante Bridge, con `notify_avg_us` mediano de 3367.250 Âµs y maximo de ventana de 11528 Âµs.

Incluso ese maximo de `notify_max_us_win` queda por debajo del periodo asociado a un bloque de 8 muestras:

```text
11528 Âµs = 11.528 ms < 32 ms
```

El maximo de loop por ventana fue 12886 Âµs, tambien inferior a 32 ms:

```text
12886 Âµs = 12.886 ms < 32 ms
```

La cola TX se mantuvo controlada:

```text
qmax_global = 1
drops_total = 0
pub_burst_global = 1
```

Esto indica que el firmware no acumulo backlog significativo ni descarto bloques durante las ventanas analizadas. La tasa mediana de publicacion fue de 30 bloques/s, coherente con bloques de 8 muestras en una adquisicion cercana a 240 Hz efectiva durante esta prueba.

Los picos de `lag_win` muestran que existen ventanas con interrupciones DRDY pendientes o catch-up, con maximo 83. Sin embargo, estos picos no se tradujeron en drops de cola TX ni en crecimiento de backlog. Ademas, la captura Python asociada conservo continuidad suficiente para ejecutar el benchmark sobre 1796 bloques y 14368 frames.

## Comparacion conjunta MCU + Python/Linux

| Parte del sistema | Metrica critica | Resultado | Presupuesto/Referencia | Conclusion |
| --- | --- | ---: | ---: | --- |
| MCU | `filt_avg_us` mediano | 5.050 Âµs | 4000 Âµs por muestra a 250 Hz | Coste de filtrado despreciable. |
| MCU | `notify_avg_us` mediano | 3367.250 Âµs | 32 ms por bloque de 8 muestras | Publicacion Bridge asumible. |
| MCU | `notify_max_us_win` maximo | 11528 Âµs | 32 ms por bloque de 8 muestras | Pico inferior al periodo de bloque. |
| MCU | `loop_max_us_win` maximo | 12886 Âµs | 32 ms por bloque de 8 muestras | Loop maximo de ventana con margen. |
| MCU | `drops_total` | 0 | 0 esperado | Sin perdidas por cola TX. |
| MCU | `qmax_global` | 1 | Cola estable | Sin acumulacion significativa. |
| Python/Linux | `compute_live_features` mediano | 5.2158 ms | 256 ms por hop | Coste muy bajo. |
| Python/Linux | `compute_live_features` maximo | 6.9831 ms | 256 ms por hop | Amplio margen temporal. |
| Python/Linux | ciclo replay con hop real | 12.56 ms/ciclo | 256 ms por hop | Pipeline Python completo con margen. |

La validacion conjunta indica que el sistema dispone de margen tanto en el MCU como en Python/Linux. En el MCU, el filtrado es muy ligero y la publicacion por Bridge no provoca crecimiento de cola ni drops. En Python/Linux, el calculo espectral, diagnostico de calidad y adaptacion de sonificacion quedan muy por debajo del hop de 256 ms.

## Validacion espectral complementaria

La validacion espectral de la primera captura proceso 208 ventanas con ventana de 4.0 s y hop de 0.256 s. La calidad espectral mediana fue 0.974, con una fraccion de ventanas de baja calidad o artefacto del 17.3 %.

Decisiones por banda:

| Banda | Mediana relativa | P95 relativo | Decision |
| --- | ---: | ---: | --- |
| delta | 0.363 | 0.510 | Usar solo como apoyo. |
| theta | 0.099 | 0.208 | Usar solo como apoyo. |
| alpha | 0.050 | 0.114 | Necesita mas capturas. |
| beta | 0.108 | 0.340 | Usar solo como apoyo. |
| gamma | 0.334 | 0.468 | No usar en tiempo real como indicador fisiologico directo. |

Estas conclusiones no afectan a la validez temporal del benchmark, pero si son relevantes para interpretar la sonificacion. La captura confirma que las bandas relativas y ratios son mas defendibles que las potencias absolutas, y que beta/gamma deben tratarse con cautela por sensibilidad a artefactos.

## Relacion con los controles de sonificacion final-v4

En la documentacion inicial de benchmarks se hablaba de nombres internos antiguos como:

```text
activity, calmness, tension, rhythmic_density, register,
harmonic_stability, velocity_factor, note_probability
```

En final-v4 esos nombres ya no deben usarse como nombres principales de redaccion. La nomenclatura reportable actual es:

| Nombre final-v4 | Alias legacy interno | Interpretacion reportable |
| --- | --- | --- |
| `rms_beta_activity` | `activity` | Actividad global asociada a RMS y bandas rapidas. |
| `alpha_drive` | `calmness` | Peso relativo de alfa/reposo espectral. |
| `beta_gamma_drive` | `tension` | Activacion relativa beta/gamma, con cautela por EMG/artefactos. |
| `band_driven_density` | `rhythmic_density` | Densidad ritmica derivada de actividad y bandas. |
| `spectral_register` | `register` | Registro melodico asociado a frecuencia/pico dominante. |
| `alpha_stability` | `harmonic_stability` | Estabilidad armonica asociada a alpha frente a tension rapida. |
| `rms_band_velocity` | `velocity_factor` | Intensidad MIDI derivada de RMS y bandas. |
| `band_note_probability` | `note_probability` | Probabilidad de generar nota a partir de densidad y bandas. |

Este cambio de nombres no altera los resultados temporales del benchmark. Solo hace que la explicacion sea coherente con el estado final-v4, WebUI, reportajes y figuras actuales.

## Limitaciones

1. La validacion temporal se ha realizado sobre capturas reales concretas, no sobre una bateria estadistica extensa de sujetos y condiciones.
2. Las capturas contienen artefactos transitorios, por lo que no deben usarse por si solas para extraer conclusiones fisiologicas fuertes.
3. Los benchmarks MCU se obtuvieron copiando el Monitor/App Lab para no anadir trafico extra por Bridge. El copiado manual se mitigo usando un parser automatico que genera CSV/JSON/Markdown.
4. El log MCU incluye lineas de diagnostico como `Frame invalido / error sincronÃ­a`. Estas incidencias aparecen en el Monitor, pero las metricas de cola TX no muestran drops y el benchmark Python se ejecuto sobre la captura real generada.
5. No se midio latencia fisica end-to-end EEG -> nota -> MIDI OUT.
6. No se midio el coste del navegador WebUI ni la latencia fisica del UART MIDI.
7. Los resultados temporales son representativos de la configuracion evaluada, pero pueden variar si se modifican frecuencia de muestreo, numero de canales, tamano de bloque, carga de UI, transporte MIDI/LED o estrategia de publicacion.
8. Los benchmarks temporales no sustituyen a la validacion experimental de capturas finales multi-condicion.

## Conclusion

Los benchmarks realizados sobre capturas reales muestran que el sistema dispone de margen temporal amplio tanto en firmware/MCU como en Python/Linux.

En el MCU, el filtrado digital tiene una mediana de aproximadamente 5 Âµs, mientras que el coste dominante es la publicacion por Bridge, con `notify_avg_us` mediano de 3367 Âµs y maximo de ventana de 11528 Âµs. Estos valores quedan por debajo del periodo de bloque de 32 ms. Ademas, la cola TX no acumulo mas de un bloque y no se registraron drops.

En Python/Linux, el calculo live de features espectrales requiere una mediana de 5.2158 ms frente a un presupuesto de 256 ms por hop. El replay completo con hop real requiere aproximadamente 12.56 ms por ciclo de procesamiento, tambien muy por debajo de los 256 ms disponibles.

Por tanto, en la configuracion evaluada, el cuello de botella principal del sistema no se encuentra en el calculo DSP/sonificacion de Python ni en el filtrado del MCU. Los aspectos mas criticos para fases posteriores son la calidad de senal, la presencia de artefactos, la estabilidad del montaje bioelectrico y la validacion de latencia fisica end-to-end EEG -> MIDI OUT.



