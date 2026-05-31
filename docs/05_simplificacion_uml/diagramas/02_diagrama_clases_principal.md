# 02. Diagrama de clases principal

## Objetivo del diagrama

Representar con claridad las clases, estructuras y modulos conceptuales que sostienen el runtime EEG->MIDI final-v4, separando el mundo firmware/MCU del mundo Python/Linux.

La intencion no es convertir cada funcion C++ en una clase real, sino hacer defendible el reparto de responsabilidades en una memoria de ingenieria.

## Que incluye

- Firmware/MCU: runtime del sketch, ADS1299, SPI seguro, filtros MCU, bloques de streaming, contrato Bridge y salida UART MIDI.
- Python/Linux: backend, receiver, buffer EEG, DSP, quality gate, sonificacion, generacion musical, scheduler MIDI, transporte `midi_bytes` y WebUI.
- Una vista resumida de arquitectura por modulos grandes.
- Etiquetas de relacion para los contratos principales: `notify eeg_block_uV`, `call midi_bytes`, `drain blocks`, `compute features`, `apply quality gate`, `schedule notes` y `send bytes`.

## Que excluye

- `CaptureManager`, que queda como runtime lateral de captura.
- `LedMatrixTransport` y LED matrix, que quedan como consumidor opcional de `music.recent_notes`.
- Tools offline.
- Benchmarks.
- Capturas y reportajes experimentales.
- Funciones legacy como `eeg_frame_uV`, `compute_online_features`, `generate_bars` y `generate_notes_for_segment`.
- Helpers privados internos que no aportan claridad al UML principal.

## Diagramas Mermaid

### 2.1 Vista firmware/MCU y contrato Bridge

Lectura: esta vista compacta el firmware en modulos conceptuales. El flujo EEG sale del ADS1299, pasa por filtros y bloque de streaming, y cruza a Python por `eeg_block_uV`. La ruta MIDI vuelve desde Bridge al firmware y termina en UART fisica.

```mermaid
classDiagram
  direction LR

  class ADS1299_SafeSPI {
    +begin()
    +select()
    +xfer()
    +deselect()
  }

  class ADS1299Plus {
    +NUM_CHANNELS = 4
    +begin()
    +configureDefaults()
    +readFrameRDATAC(status24, chOut)
    +unpack24()
  }

  class FirmwareRuntime {
    <<module>>
    +setup()
    +loop()
    +onDrdyFalling()
    +applyAdsDiagnosticMode()
    +midi_bytes()
  }

  class MCUFilters {
    <<module>>
    +DCBlocker.process()
    +Biquad.process()
    +volts_to_uV_i32()
  }

  class TxBlockRing {
    +appendSampleToFillBlock()
    +enqueueCompletedBlock()
    +publishPendingBlocks()
  }

  class EegBlockUV {
    +block_idx
    +first_sample_idx
    +sample_count
    +status[8]
    +ch_uV[8][4]
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

  ADS1299_SafeSPI --> ADS1299Plus : SPI MODE1
  ADS1299Plus --> FirmwareRuntime : RDATAC frame
  FirmwareRuntime --> MCUFilters : filter uV
  MCUFilters --> TxBlockRing : append sample
  TxBlockRing --> EegBlockUV : fill block
  EegBlockUV --> BridgeContract : notify eeg_block_uV
  BridgeContract --> FirmwareRuntime : call midi_bytes
  FirmwareRuntime --> MidiUartOut : send bytes
```

### 2.2 Vista Python runtime EEG->MIDI

Lectura: esta vista muestra el pipeline Python live. `BackendService` orquesta el uso de DSP y quality gate; por eso `DSPCore` no se conecta directamente a `SpectralQuality`. El contrato `midi_bytes` vuelve al firmware mediante `BridgeContract`.

```mermaid
classDiagram
  direction LR

  class BridgeContract {
    <<contract>>
    +linux_started()
    +eeg_block_uV()
    +midi_bytes()
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
    +gate_factor
    +valid_for_sonification
    +to_dict()
  }

  class SonificationFeatureAdapter {
    +update()
    +reset()
  }

  class SonificationFeatures {
    +alpha_drive
    +beta_gamma_drive
    +rms_beta_activity
    +band_driven_density
    +to_dict()
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

  BridgeContract --> EEGReceiver : eeg_block_uV
  EEGReceiver --> EEGSignalProcessor : drain blocks
  EEGSignalProcessor --> DSPCore : compute features
  BackendService --> EEGReceiver : owns
  BackendService --> EEGSignalProcessor : owns
  BackendService --> SpectralQuality : compute quality
  SpectralQuality --> SonificationFeatureAdapter : apply quality gate
  SonificationFeatureAdapter --> SonificationFeatures : normalized controls
  SonificationFeatures --> MusicSegmentBuilder : build segment
  MusicSegmentBuilder --> MusicSegment
  MusicSegment --> BarGenerator : generate bar
  BarGenerator --> Bar
  MusicSegment --> NoteGenerator : generate notes
  Bar --> NoteGenerator
  NoteGenerator --> NoteEvent
  NoteEvent --> MidiScheduler : schedule notes
  MidiScheduler --> MidiLiveEvent : due events
  MidiLiveEvent --> MidiByteTransport : send bytes
  MidiByteTransport --> BridgeContract : call midi_bytes
  BackendService --> EEGWebServer : publish snapshot
```

### 2.3 Vista resumida de arquitectura por modulos

Lectura: esta vista elimina detalle de clases para explicar el sistema en una diapositiva o figura de memoria. La WebUI aparece como rama lateral de observacion y control; no participa en el DSP pesado.

```mermaid
flowchart LR
  firmware["Firmware / MCU\nADS1299 + filtros + streaming"]
  bridge["BridgeContract\nlinux_started / eeg_block_uV / midi_bytes"]
  backend["BackendService\norquestacion runtime"]
  dsp["DSP / Quality\nbuffer + multitaper + gate"]
  sonif["Sonification / Music\ncontroles + compas + notas"]
  midi["MIDI Transport\nscheduler + bytes"]
  midiOut["Firmware MIDI OUT\nSerial1 / D1 / TX invertido"]
  web["WebUI\nsnapshot + panic + root/main/scale"]

  firmware -->|notify eeg_block_uV| bridge
  bridge -->|blocks| backend
  backend -->|compute features| dsp
  dsp -->|apply quality gate| sonif
  sonif -->|schedule notes| midi
  midi -->|call midi_bytes| bridge
  bridge -->|send bytes| midiOut
  backend -.->|snapshot + controls| web
  web -.->|panic + music config| backend
```

## Notas de correspondencia con archivos reales

- `FirmwareRuntime`, `MCUFilters`, `BridgeContract` y `MidiUartOut` son modulos conceptuales para documentacion UML. Representan responsabilidades de `sketch/sketch.ino`, `filters.h`, contratos Bridge y salida UART MIDI; no implican que existan como clases C++ reales.
- `ADS1299Plus`, `ADS1299_SafeSPI`, `EegBlockUV` y `TxBlockRing` si corresponden a clases/estructuras C++ reales o estructuras definidas en headers.
- `BackendService` orquesta RX, DSP, quality, sonificacion, MIDI y snapshot desde `python/backend_service.py`.
- `SpectralQuality` representa el resultado de `compute_spectral_quality()` en `python/spectral_quality.py`; el calculo lo invoca `BackendService` usando features y diagnostics.
- `SonificationFeatures` conserva alias legacy, pero el UML principal prioriza nombres final-v4.
- `EEGWebServer` no calcula DSP ni musica; expone rutas, socket y assets para observar/controlar.
- `MidiByteTransport` no accede a UART directamente; solo llama `Bridge.call("midi_bytes", n, b0, b1, b2)`.

## Advertencias de simplificacion

- Dividir el diagrama en tres vistas evita flechas cruzadas y hace mas defendible cada responsabilidad.
- El UML principal oculta `CaptureManager`, `LedMatrixTransport`, tools offline, benchmarks y capturas porque son laterales o de validacion, no el nucleo EEG->MIDI.
- El diagrama representa dependencias conceptuales y de flujo; no debe usarse como receta para mover archivos o refactorizar codigo.
