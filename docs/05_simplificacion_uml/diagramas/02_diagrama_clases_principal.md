# 02. Diagrama de clases principal

## Objetivo del diagrama

Representar las clases y estructuras principales que sostienen el runtime EEG->MIDI final-v4.

## Que incluye

- Driver ADS1299 y streaming firmware.
- Modulos conceptuales del runtime firmware/MCU.
- Receiver, buffer, DSP y quality gate.
- Sonificacion, generacion musical, scheduler y transporte MIDI.
- WebUI como consumidor de snapshot y emisor de controles ligeros.

## Que excluye

- Tools offline.
- Benchmarks.
- Capturas experimentales.
- Clases LED, salvo mencion secundaria en notas.
- Funciones legacy y helpers internos.

## Diagrama Mermaid

```mermaid
classDiagram
  class FirmwareRuntime {
    <<module>>
    +setup()
    +loop()
    +onDrdyFalling()
    +applyAdsDiagnosticMode()
    +midi_bytes()
  }

  class ADS1299Plus {
    +NUM_CHANNELS = 4
    +begin()
    +configureDefaults()
    +readFrameRDATAC(status24, chOut)
    +unpack24()
  }

  class ADS1299_SafeSPI {
    +begin()
    +select()
    +xfer()
    +deselect()
  }

  class MCUFilters {
    <<module>>
    +DCBlocker.process()
    +Biquad.process()
    +volts_to_uV_i32()
  }

  class EegBlockUV {
    +block_idx
    +first_sample_idx
    +sample_count
    +status[8]
    +ch_uV[8][4]
  }

  class TxBlockRing {
    +appendSampleToFillBlock()
    +enqueueCompletedBlock()
    +publishPendingBlocks()
  }

  class BridgeContract {
    <<contract>>
    +linux_started()
    +eeg_block_uV()
    +midi_bytes()
  }

  class MidiUartOut {
    <<firmware>>
    +Serial1.write()
    +D1/TX
    +TX invertido
  }

  class BackendService {
    +step()
    +send_panic()
    +update_music_config()
    +get_latest_snapshot()
  }

  class EEGReceiver {
    +eeg_block_uV()
    +drain_blocks_to_processor()
    +get_window_metrics()
  }

  class EEGSignalProcessor {
    +add_block_uV()
    +is_window_ready()
    +compute_live_features()
    +compute_quality_diagnostics()
  }

  class DSPCore {
    +compute_psd()
    +compute_features()
    +compute_bandpower()
  }

  class SpectralQuality {
    +score
    +state
    +valid
    +to_dict()
  }

  class SonificationFeatures {
    +alpha_drive
    +beta_gamma_drive
    +rms_beta_activity
    +band_driven_density
    +to_dict()
  }

  class SonificationFeatureAdapter {
    +update()
    +reset()
  }

  class MusicSegmentBuilder {
    +build_live_segment()
  }

  class MusicSegment {
    +duration_sec
    +rhythm_cadence
    +to_dict()
  }

  class BarGenerator {
    +generate_live_bar()
  }

  class Bar {
    +chord_root_midi
    +chord_pitches
  }

  class NoteGenerator {
    +generate_notes_for_bar()
  }

  class NoteEvent {
    +pitch_midi
    +start_sec
    +duration_sec
    +velocity
  }

  class MidiScheduler {
    +schedule_notes()
    +pop_due_events()
    +panic()
    +get_status()
  }

  class MidiLiveEvent {
    +due_time
    +type
    +channel
    +data1
    +data2
  }

  class MidiByteTransport {
    +send_event()
    +send_events()
    +get_status()
  }

  class EEGWebServer {
    +get_latest()
    +post_midi_panic()
    +post_music_config()
    +publish_snapshot()
  }

  FirmwareRuntime --> ADS1299Plus
  FirmwareRuntime --> MCUFilters
  FirmwareRuntime --> TxBlockRing
  FirmwareRuntime --> BridgeContract
  FirmwareRuntime --> MidiUartOut
  ADS1299Plus --> ADS1299_SafeSPI
  TxBlockRing --> EegBlockUV
  TxBlockRing --> BridgeContract : notify EEG blocks
  MidiByteTransport --> BridgeContract : call midi_bytes
  BridgeContract --> EEGReceiver : eeg_block_uV
  BridgeContract --> MidiUartOut : midi_bytes
  BackendService --> EEGReceiver
  BackendService --> EEGSignalProcessor
  BackendService --> SpectralQuality
  BackendService --> SonificationFeatureAdapter
  BackendService --> MusicSegmentBuilder
  BackendService --> BarGenerator
  BackendService --> NoteGenerator
  BackendService --> MidiScheduler
  BackendService --> MidiByteTransport
  BackendService --> EEGWebServer
  EEGReceiver --> EEGSignalProcessor : drain blocks
  EEGSignalProcessor --> DSPCore
  SpectralQuality --> SonificationFeatureAdapter : quality gate
  SonificationFeatureAdapter --> SonificationFeatures
  MusicSegmentBuilder --> MusicSegment
  BarGenerator --> Bar
  NoteGenerator --> NoteEvent
  MidiScheduler --> MidiLiveEvent
  MidiByteTransport --> MidiLiveEvent
```

## Notas de correspondencia con archivos reales

- `SpectralQuality` es la dataclass de `python/spectral_quality.py`; se crea con `compute_spectral_quality()`.
- `FirmwareRuntime`, `MCUFilters`, `BridgeContract` y `MidiUartOut` son modulos conceptuales para documentacion UML. Representan responsabilidades de `sketch/sketch.ino`, `filters.h`, los contratos Bridge y la salida UART MIDI; no implican que existan como clases C++ reales.
- `SonificationFeatures` conserva alias legacy, pero el UML principal debe usar nombres final-v4.
- `EEGWebServer` no calcula DSP ni musica; solo expone rutas, socket y assets.
- `CaptureManager`, `LedMatrixConfig`, `LedMatrixTransport`, tools offline, benchmarks y capturas quedan fuera del UML principal.

## Advertencias de simplificacion

El diagrama no muestra todas las funciones privadas de `backend_service.py`, `music_bar.py` ni `music_note.py`. Es intencional: para UML principal importa la responsabilidad, no cada helper.
