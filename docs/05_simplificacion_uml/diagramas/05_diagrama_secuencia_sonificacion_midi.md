# 05. Diagrama de secuencia de sonificacion y MIDI

## Objetivo del diagrama

Mostrar como una ventana EEG con features validas se convierte en notas MIDI y salida fisica.

## Que incluye

- Feature hop.
- DSP live y quality gate.
- Adaptacion de controles de sonificacion.
- Segmento, compas y notas.
- Scheduler MIDI, transporte y `midi_bytes`.
- Panic como ruta de seguridad.

## Que excluye

- Test loop MIDI diagnostico.
- LED matrix.
- Persistencia detallada de snapshot.
- Tools offline de validacion musical.

## Diagrama Mermaid

```mermaid
sequenceDiagram
  participant Backend as BackendService
  participant Proc as EEGSignalProcessor
  participant DSP as DSPCore
  participant Quality as spectral_quality.py
  participant Adapter as SonificationFeatureAdapter
  participant Segment as MusicSegmentBuilder
  participant Bar as BarGenerator
  participant Notes as NoteGenerator
  participant Scheduler as MidiScheduler
  participant Transport as MidiByteTransport
  participant Bridge as Arduino Bridge
  participant MCU as firmware midi_bytes
  participant UART as Serial1/D1 TX invertido

  Backend->>Proc: is_window_ready(4 s)
  alt window ready and FEATURE_HOP_SAMPLES reached
    Backend->>Proc: compute_live_features(channel 0, multitaper)
    Proc->>DSP: compute_features()
    DSP-->>Proc: rms, PSD, bandpowers, peaks
    Proc-->>Backend: features
    Backend->>Proc: compute_quality_diagnostics()
    Backend->>Quality: compute_spectral_quality(features, diagnostics, rx metrics)
    Quality-->>Backend: SpectralQuality.to_dict()
    Backend->>Adapter: update(features, quality)
    Adapter-->>Backend: SonificationFeatures
  end

  alt sonification valid and bar period elapsed
    Backend->>Segment: build_live_segment(sonification, scale, main note)
    Segment-->>Backend: MusicSegment
    Backend->>Bar: generate_live_bar(segment)
    Bar-->>Backend: Bar
    Backend->>Notes: generate_notes_for_bar(segment, bar)
    Notes-->>Backend: NoteEvent list
    Backend->>Scheduler: schedule_program_change once
    Backend->>Scheduler: schedule_notes(notes, time_origin)
    Backend->>Backend: remember recent_notes for WebUI
  end

  Backend->>Scheduler: pop_due_events(now, lookahead)
  Scheduler-->>Backend: MidiLiveEvent list
  Backend->>Transport: send_events(due_events)
  loop each event
    Transport->>Transport: event_to_midi_bytes(event)
    Transport->>Bridge: call("midi_bytes", n, b0, b1, b2)
    Bridge->>MCU: midi_bytes(n, b0, b1, b2)
    MCU->>UART: write bytes at MIDI baud
  end

  opt Panic MIDI
    Backend->>Scheduler: panic()
    Scheduler-->>Backend: All Sound Off + All Notes Off
    Backend->>Transport: send_events(panic events)
  end
```

## Notas de correspondencia con archivos reales

- `FEATURE_WINDOW_SEC=4.0` y `FEATURE_HOP_SAMPLES=64` viven en `backend_service.py`.
- `MUSIC_BAR_SEC=2.0` controla la generacion de compases.
- `MIDI_LOOKAHEAD_SEC=0.02` se usa al extraer eventos vencidos.
- `MidiByteTransport` no genera musica; solo convierte `MidiLiveEvent` a bytes y llama `midi_bytes`.
- El firmware conserva la responsabilidad de escribir por UART fisica.

## Advertencias de simplificacion

El quality gate no modifica adquisicion ni DSP; actua entre features y controles de sonificacion. El panic MIDI debe conservarse aunque se simplifique el resto del relato.
