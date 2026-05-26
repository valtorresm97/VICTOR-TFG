# 05. Auditoria sonificacion y MIDI

## Diagrama

```text
SonificationFeatures
   ↓
MusicSegmentBuilder
   ↓
BarGenerator
   ↓
NoteGenerator
   ↓
NoteEvent
   ↓
MidiScheduler
   ↓
MidiLiveEvent
   ↓
event_to_midi_bytes
   ↓
MidiByteTransport
   ↓
Bridge.call("midi_bytes")
   ↓
MCU handler midi_bytes
   ↓
UART TX/D1 si MIDI_UART_ENABLED=1
   ↓
MIDI OUT PCB
```

## Modulos

| Modulo | Clase/funcion | Que hace | Estado |
| --- | --- | --- | --- |
| `sonification_features.py` | `SonificationFeatures` | Dataclass con controles musicales y trazabilidad DSP. | Activo |
| `sonification_features.py` | `SonificationFeatureAdapter` | RMS baseline, quality gate y EMA. | Activo |
| `music_segment.py` | `MusicSegmentBuilder` | Crea estado musical live y cadencia con histeresis. | Activo |
| `music_bar.py` | `BarGenerator` | Genera acorde diatonico, slots y envolvente musical. | Activo |
| `music_note.py` | `NoteGenerator` | Genera `NoteEvent`, pitch diatonico, velocity y duracion. | Activo |
| `midi_live.py` | `MidiScheduler` | Heap de eventos live, pop due, active notes y panic. | Activo |
| `midi_live.py` | `event_to_midi_bytes()` | Convierte eventos a bytes MIDI estandar. | Activo |
| `midi_byte_transport.py` | `MidiByteTransport` | Llama `Bridge.call("midi_bytes", n,b0,b1,b2)`. | Activo, disabled por defecto |

## Configuracion musical fija actual

| Configuracion | Valor | Archivo |
| --- | --- | --- |
| Compas live | `MUSIC_BAR_SEC=2.0` | `backend_service.py` |
| Canal MIDI | `0` | `backend_service.py` |
| Programa | `0` | `backend_service.py` |
| Root note | `C4` | `backend_service.py` |
| Main note | `G4` | `backend_service.py` |
| Escala | `Diatonic / Major (Ionian)` | `backend_service.py` |
| Notas recientes max | `96` | `backend_service.py` |
| Ventana piano roll | `20.0 s` | `backend_service.py` |
| Lookahead MIDI | `0.02 s` | `backend_service.py` |

## MIDI live

Tipos soportados:

- `note_on`
- `note_off`
- `program_change`
- `control_change`

Mensajes de seguridad:

- `all_notes_off_events()`: CC 123 por canal.
- `panic_events()`: CC 120 All Sound Off + CC 123 All Notes Off por canal.
- `BackendService.send_panic()`: envia panic si transporte habilitado.
- `BackendService.stop()`: llama `send_panic()`.

Limitaciones:

- Existe boton Web UI de panic y endpoint `POST /midi/panic` conectado a `send_panic()`.
- El firmware no implementa panic propio; solo reenvia bytes si UART habilitada.
- `MIDI_UART_ENABLED=0` por defecto y exige definir `MIDI_SERIAL`.

## Jitter y drops

`MidiScheduler.pop_due_events(now, lookahead_sec=0.02, max_events=64)` extrae eventos vencidos con un pequeno adelanto. El transporte cuenta:

- `sent_events_total`
- `failed_events_total`
- `sent_bytes_total`
- `dropped_events_total`

Si `EEG_MIDI_LIVE_ENABLED=False`, los eventos se descartan intencionadamente y se contabilizan como dropped para observabilidad.

## Piano scroll

El piano roll web no lee MIDI real; usa `music.recent_notes`, rellenado por `_remember_recent_notes()` justo despues de generar notas. Esto permite ver la intencion musical aunque el transporte MIDI fisico este desactivado.

## Enabled/disabled

| Capa | Flag | Default | Resultado |
| --- | --- | --- | --- |
| Python MIDI | `EEG_MIDI_LIVE_ENABLED` | `False` | Scheduler activo, transporte descarta. |
| Firmware MIDI | `MIDI_UART_ENABLED` | `0` | Handler registrado, no escribe UART y devuelve `false`. |
| UART fisica | `MIDI_SERIAL` | No definida | Requerida solo si `MIDI_UART_ENABLED=1`. |

## Riesgos

- Activar Python MIDI sin activar firmware UART provoca llamadas Bridge cuyo handler devuelve `false`.
- Activar firmware UART sin verificar objeto serial D1/TX puede interferir con Bridge/Monitor.
- El scheduler puede generar eventos aunque la calidad sea mala si quedan eventos ya programados de una ventana anterior.
- Falta una accion manual de panic desde UI.
- La densidad musical depende de quality gate, pero no existe limite global de notas por segundo mas alla de slots/compas y `max_events`.
