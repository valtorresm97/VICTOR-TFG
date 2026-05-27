# Benchmarks temporales en placa

Infraestructura minima para medir el coste temporal de funciones criticas del pipeline EEG-MIDI **en la UNO Q/Linux**, usando capturas reales guardadas en `captures/`.

La senal sintetica queda solo como smoke test secundario. El caso principal debe ser una captura real generada por la app en placa.

## Objetivo

Crear un baseline temporal reproducible del rendimiento real de la placa antes de reorganizar el codigo Python en paquetes.

La reorganizacion propuesta en `dsp/`, `sonification/`, `midi/`, `led_matrix/`, `capture/`, `web/` y `tools/` queda aplazada hasta tener:

1. benchmarks sobre captura real en placa,
2. benchmarks sinteticos solo como control rapido,
3. tests de contrato,
4. baseline temporal,
5. smoke test en App Lab/placa.

## Flujo recomendado en placa

Desde la UNO Q, con la app App Lab funcionando y recibiendo datos reales:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
python3 python/tools/capture_eeg_quality.py --condition bench_real_rest_60s --duration 60 --timeout-extra 180
CAPTURE_DIR=$(ls -td captures/*_bench_real_rest_60s /app/captures/*_bench_real_rest_60s 2>/dev/null | head -1)
python3 benchmarks/run_all_benchmarks.py --capture-dir "$CAPTURE_DIR"
```

Si ya existe una captura reciente:

```bash
python3 benchmarks/run_all_benchmarks.py --latest-capture
```

Para una prueba rapida de desarrollo:

```bash
python3 benchmarks/run_all_benchmarks.py --latest-capture --max-blocks 200
```

## Que mide sobre captura real

`benchmark_real_capture.py` lee `eeg_timeseries.csv`, reconstruye los bloques reales por `block_idx` y mide:

- `parse_eeg_block_values` sobre payload real,
- replay de todos los bloques reales en `EEGReceiver.eeg_block_uV`,
- replay de todos los bloques reales en `EEGSignalProcessor.add_block_uV`,
- `compute_live_features` sobre la ultima ventana real de 4 s,
- `compute_quality_diagnostics` sobre la ultima ventana real,
- `DSPCore.compute_features` aislado sobre datos reales,
- replay simulando hop real de `FEATURE_HOP_SAMPLES=64`.

Esto mide el rendimiento del Python de la placa con datos reales ya capturados por ADS1299/firmware/Bridge.

## Que mide el smoke test sintetico

Los benchmarks sinteticos solo sirven para comprobar que el harness funciona aunque no haya captura disponible. Reutilizan la idea de `sketch/synthetic.h`: delta/theta/alpha/beta/gamma, drift, hum 50 Hz y ruido.

No sustituyen a la medicion en placa con captura real.

## Que no mide todavia

No mide directamente:

- tiempo SPI real,
- ISR DRDY real,
- coste exacto de `Bridge.notify` en firmware,
- UART MIDI fisica,
- LED fisica,
- rendimiento real del navegador,
- latencia fisica EEG -> nota -> MIDI OUT.

Para esos puntos se debe usar `sketch/bench.h`, Monitor/App Lab y pruebas hardware separadas.

## Reutilizacion de codigo existente

La infraestructura reutiliza el criterio de observabilidad de `sketch/bench.h`: medir tiempos acumulados, maximos y tasas sin alterar el payload EEG.

Tambien reutiliza el formato de captura ya existente:

```text
eeg_timeseries.csv:
  t_capture_sec,timestamp_unix,block_idx,sample_idx,sample_in_block,status,ch1_uV..ch4_uV
```

## Uso general

Desde la raiz del repo:

```bash
python3 -m py_compile benchmarks/*.py
python3 benchmarks/run_all_benchmarks.py --latest-capture
```

Los resultados se guardan en:

```text
benchmarks/results/<timestamp>_benchmark_results.json
benchmarks/results/<timestamp>_benchmark_results.csv
benchmarks/reports/<timestamp>_benchmark_report.md
```

## Interpretacion

Al principio los resultados son baseline, no pass/fail rigido.

Criterios orientativos:

- `EEGReceiver.eeg_block_uV` debe ser ultraligera.
- `compute_live_features` debe quedar claramente por debajo del hop live: 64 muestras a 250 Hz, aproximadamente 256 ms.
- El replay completo de una captura real no representa tiempo por muestra, sino coste de reprocesar una captura completa en placa.
- MIDI/LED deben tener coste despreciable frente al DSP.

## Compatibilidad

Los benchmarks insertan `python/` en `sys.path` sin modificar el repo.
Para modulos que importan `arduino.*`, se instala un mock minimo en memoria antes del import. No se llama a hardware real desde los benchmarks offline.
