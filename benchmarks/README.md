# Benchmarks temporales offline

Infraestructura minima para medir el coste temporal de funciones criticas del pipeline EEG-MIDI sin tocar el firmware, sin mover modulos Python y sin depender de Arduino App Lab.

## Objetivo

Crear un baseline temporal reproducible para detectar regresiones antes de reorganizar el codigo Python en paquetes.

La reorganizacion propuesta en `dsp/`, `sonification/`, `midi/`, `led_matrix/`, `capture/`, `web/` y `tools/` queda aplazada hasta tener:

1. benchmarks offline,
2. tests de contrato,
3. baseline temporal,
4. smoke test en App Lab/placa.

## Que mide

Estos scripts miden rutas offline seguras:

- contrato `eeg_block_uV`, parser y receiver,
- ring buffer de `EEGSignalProcessor`,
- DSP multitaper y features live,
- quality diagnostics,
- sonificacion y MIDI scheduler,
- LED matrix frame/packing con Bridge mock,
- escritura JSON atomica sobre directorio temporal.

## Que no mide todavia

No mide:

- SPI real,
- DRDY real,
- ADS1299 real,
- RouterBridge real,
- UART MIDI fisica,
- LED fisica,
- rendimiento real del navegador,
- latencia fisica EEG -> nota -> MIDI OUT.

Esos benchmarks deben hacerse en una fase posterior con placa y protocolo separado.

## Reutilizacion de codigo existente

La infraestructura reutiliza el criterio de observabilidad ya existente en `sketch/bench.h`: medir tiempos acumulados, maximos y tasas sin alterar el payload EEG.

Tambien replica en Python el generador EEG-like de `sketch/synthetic.h`, que mezcla delta/theta/alpha/beta/gamma, drift, hum de 50 Hz y ruido. Asi los benchmarks DSP usan senales coherentes con el modo sintetico de firmware.

## Uso

Desde la raiz del repo:

```bash
python3 -m py_compile benchmarks/*.py
python3 benchmarks/run_all_benchmarks.py
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
- `_build_snapshot` no se benchmarkea aun porque requiere aislar mejor dependencias de App Lab; se mediran piezas sueltas offline.
- MIDI/LED deben tener coste despreciable frente al DSP.

## Compatibilidad

Los benchmarks insertan `python/` en `sys.path` sin modificar el repo.
Para modulos que importan `arduino.*`, se instala un mock minimo en memoria antes del import. No se llama a hardware real.
