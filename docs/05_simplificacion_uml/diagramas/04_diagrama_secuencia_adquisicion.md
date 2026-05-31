# 04. Diagrama de secuencia de adquisicion

## Objetivo del diagrama

Describir la secuencia runtime desde DRDY del ADS1299 hasta la entrada de bloques en el buffer DSP Python.

## Que incluye

- DRDY/RDATAC.
- Reconstruccion y filtrado MCU.
- Cola `TxBlockRing`.
- `Bridge.notify("eeg_block_uV")`.
- Parser/validacion Python.
- Drenado al `EEGSignalProcessor`.

## Que excluye

- Generacion MIDI.
- Capturas offline y benchmarks.
- Logs detallados de Monitor.
- Modo sintetico.

## Diagrama Mermaid

```mermaid
sequenceDiagram
  participant ADS as ADS1299
  participant MCU as sketch.ino
  participant Driver as ADS1299Plus
  participant Filters as filters.h
  participant Ring as TxBlockRing
  participant Bridge as Arduino Bridge
  participant RX as EEGReceiver
  participant Contract as eeg_contract.py
  participant Backend as BackendService
  participant Proc as EEGSignalProcessor

  ADS->>MCU: DRDY falling edge
  MCU->>Driver: readFrameRDATAC(status, ch_raw[4])
  Driver-->>MCU: status24 + signed 24-bit samples
  MCU->>MCU: validate STATUS_PREFIX mask
  MCU->>Filters: counts -> volts -> filter chain -> uV
  Filters-->>MCU: ch_uV[4]
  MCU->>Ring: appendSampleToFillBlock(sample_idx, status, ch_uV)
  alt sample_count == 8
    Ring->>Ring: enqueueCompletedBlock()
  end
  MCU->>Ring: publishPendingBlocks(max 4)
  Ring->>Bridge: notify("eeg_block_uV", block_idx, first_sample_idx, sample_count, vals)
  Bridge->>RX: eeg_block_uV(...)
  RX->>Contract: parse_eeg_block_values(sample_count, vals)
  Contract-->>RX: statuses + samples
  RX->>RX: validate continuity + status + queue metrics
  Backend->>RX: drain_blocks_to_processor(proc, block_sink)
  RX->>Proc: add_block_uV(samples)
  RX-->>Backend: drained blocks, drained frames
```

## Notas de correspondencia con archivos reales

- `BLOCK_SAMPLES` vale `8` en `sketch/streaming.h` y `python/eeg_contract.py`.
- Python valida longitud, `sample_count`, continuidad por indices y status.
- `drdy_count` no debe interpretarse como FIFO de muestras; si hay acumulacion, el firmware registra perdida/jitter.
- El backend tambien pasa bloques al `CaptureManager` como ruta lateral.

## Advertencias de simplificacion

El diagrama omite detalles de `BenchStats`, `pending > 1`, latencias de `Bridge.notify` y prints Monitor. Esos elementos son observabilidad, no contrato funcional principal.
