# 05. Auditoria sonificacion y MIDI - final-v4

## 1. Objetivo

Este documento explica la cadena de sonificacion y MIDI en lenguaje narrativo para la memoria del TFG. La auditoria funcion por funcion mas exhaustiva esta en:

```text
docs/auditoria_codigo_detallada/05_sonificacion_midi_funcion_por_funcion.md
```

Aqui se describe como los rasgos EEG ya calculados se convierten en controles musicales, como se generan notas, como se programan eventos MIDI y como finalmente se envian bytes al firmware para la salida MIDI fisica.

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Diagrama principal final-v4

La ruta live principal es:

```text
features EEG + SignalQuality / QualityGate
   ↓
SonificationFeatureAdapter.update()
   ↓
SonificationFeatures final-v4
   ↓
MusicSegmentBuilder.build_live_segment()
   ↓
BarGenerator.generate_live_bar()
   ↓
NoteGenerator.generate_notes_for_bar()
   ↓
NoteEvent
   ↓
MidiScheduler.schedule_notes()
   ↓
MidiScheduler.pop_due_events()
   ↓
MidiLiveEvent
   ↓
event_to_midi_bytes()
   ↓
MidiByteTransport.send_events()
   ↓
Bridge.call("midi_bytes", n, b0, b1, b2)
   ↓
MCU handler midi_bytes()
   ↓
Serial1 / D1 / 31250 baudios / TX invertido
   ↓
MIDI OUT fisico
```

Esta es la ruta que debe aparecer en el UML principal.

## 3. Papel de la sonificacion

La sonificacion no intenta diagnosticar clinicamente el EEG. Su funcion es transformar rasgos espectrales y de amplitud en parametros musicales en tiempo real.

El EEG no decide directamente la tonalidad ni la nota principal. En final-v4:

```text
root_note
main_note
scale_key
```

son controles de usuario/WebUI. El EEG modula:

- densidad ritmica;
- registro melodico;
- actividad/dinamica;
- estabilidad armonica;
- tension relativa;
- probabilidad de notas;
- suavizado temporal.

El quality gate actua antes de la generacion musical para atenuar o bloquear ventanas no fiables.

## 4. Modulos principales

| Modulo | Clase/funcion | Que hace | Estado final-v4 | UML principal |
| --- | --- | --- | --- | --- |
| `sonification_features.py` | `SonificationFeatures` | Dataclass con controles de sonificacion reportables y trazabilidad DSP. | Activo | Si |
| `sonification_features.py` | `SonificationFeatureAdapter` | RMS baseline, quality gate, normalizacion y EMA. | Activo | Si |
| `music_segment.py` | `MusicSegmentBuilder.build_live_segment()` | Crea estado musical live y cadencia con histeresis. | Activo | Si |
| `music_bar.py` | `BarGenerator.generate_live_bar()` | Genera acorde diatonico, slots y envolvente musical. | Activo | Si |
| `music_note.py` | `NoteGenerator.generate_notes_for_bar()` | Genera `NoteEvent`, pitch diatonico, velocity y duracion. | Activo | Si |
| `midi_live.py` | `MidiScheduler` | Heap de eventos live, pop due, active notes y panic. | Activo | Si |
| `midi_live.py` | `event_to_midi_bytes()` | Convierte eventos a bytes MIDI estandar. | Activo | Si |
| `midi_byte_transport.py` | `MidiByteTransport` | Llama `Bridge.call("midi_bytes", n,b0,b1,b2)`. | Activo por defecto final-v4 | Si |
| `music_utils.py` | `note_name_to_midi()` | Convierte notas tipo C4/F#4/Bb3 a MIDI. | Activo | Utilidad |
| `scale_registry.py` | `build_scale_config()` | Construye escalas disponibles. | Activo | Utilidad |

Rutas secundarias/compatibilidad:

```text
BarGenerator.generate_bars()
NoteGenerator.generate_notes_for_segment()
```

Estas rutas no son necesarias para el funcionamiento live final-v4 porque el backend usa `generate_live_bar()` y `generate_notes_for_bar()`.

## 5. Controles de sonificacion final-v4

Los nombres publicos y defendibles para el TFG son:

| Control final-v4 | Alias legacy interno | Interpretacion | Uso musical |
| --- | --- | --- | --- |
| `alpha_drive` | `calmness` | Peso relativo de alfa y reposo espectral | Estabilidad/reposo. |
| `beta_gamma_drive` | `tension` | Actividad rapida beta/gamma | Tension armonica/sincopa. |
| `rms_beta_activity` | `activity` | RMS normalizado + beta/gamma | Actividad, densidad y dinamica. |
| `band_driven_density` | `rhythmic_density` | Combinacion de actividad y tension | Densidad ritmica. |
| `spectral_register` | `register` | Frecuencia/pico normalizado | Registro melodico. |
| `alpha_stability` | `harmonic_stability` | Estabilidad por alfa frente a tension | Estabilidad armonica. |
| `rms_band_velocity` | `velocity_factor` | Actividad RMS/bandas | Velocity MIDI. |
| `band_note_probability` | `note_probability` | Densidad/bandas | Probabilidad de generar notas. |

Regla final-v4:

```text
Usar nombres final-v4 en memoria, figuras, reportes y UML.
Mantener aliases legacy solo como compatibilidad interna hasta migracion segura.
```

## 6. Configuracion musical actual

| Configuracion | Valor final-v4 | Archivo | Comentario |
| --- | --- | --- | --- |
| Compas live | `MUSIC_BAR_SEC=2.0` | `backend_service.py` | Unidad musical de generacion. |
| Periodo minimo de acorde | `MUSIC_CHORD_MIN_PERIOD_SEC=12.0` | `backend_service.py` | Evita cambios armonicos demasiado frecuentes. |
| Umbral cambio acorde | `MUSIC_CHORD_CHANGE_THRESHOLD=0.45` | `backend_service.py` | Cambios solo si el estado musical cambia suficiente. |
| Canal MIDI | `9` interno = canal MIDI 10 | `backend_service.py` | Canal de salida usado por la sonificacion. |
| Programa | `0` | `backend_service.py` | Programa MIDI base. |
| Root note | `C4` por defecto | `backend_service.py` / WebUI | Control de usuario. |
| Main note | `G4` por defecto | `backend_service.py` / WebUI | Centro melodico. |
| Escala | `major` por defecto | `backend_service.py`, `scale_registry.py` | Escala seleccionable. |
| Escalas WebUI | major, minor, blues, spanish, arabic, harmonic_minor, phrygian_dominant, minor_pentatonic, major_pentatonic | backend/WebUI | Opciones de control musical. |
| Variedad melodica | `MUSIC_PITCH_VARIETY=0.65` | `backend_service.py` | Evita repeticion excesiva. |
| Radio escala | `MUSIC_SCALE_RADIUS_SEMITONES=28` | `backend_service.py` | Rango de busqueda de pitches. |
| Notas recientes max | `96` | `backend_service.py` | Piano roll y LED lateral. |
| Ventana piano roll | `20.0 s` | `backend_service.py` | Visualizacion WebUI. |
| Lookahead MIDI | `0.02 s` | `backend_service.py` | Compensa scheduling. |

## 7. MIDI live

Tipos soportados:

- `note_on`;
- `note_off`;
- `program_change`;
- `control_change`.

Mensajes de seguridad:

- `all_notes_off_events()`: CC 123 por canal;
- `panic_events()`: CC 120 All Sound Off + CC 123 All Notes Off por canal;
- `BackendService.send_panic()`: envia panic si transporte habilitado;
- `BackendService.stop()`: llama `send_panic()`;
- WebUI: `POST /midi/panic` conectado a `send_panic()`.

El firmware no interpreta musicalmente los bytes. Solo recibe `midi_bytes()` y los reenvia por UART MIDI fisica.

## 8. Transporte MIDI fisico

Configuracion final-v4:

```text
EEG_MIDI_LIVE_ENABLED=True
MIDI_UART_ENABLED=1
MIDI_SERIAL=Serial1
TX invertido obligatorio con USART_CR2_TXINV
```

El transporte completo es:

```text
MidiByteTransport
  -> Bridge.call("midi_bytes", n, b0, b1, b2)
  -> firmware midi_bytes()
  -> Serial1/D1
  -> circuito MIDI OUT
```

El MIDI OUT fisico fue validado con `Serial1`/D1 y TX invertido. Cambiar UART, polaridad o circuito exige repetir validacion fisica.

## 9. Jitter, lookahead y drops

`MidiScheduler.pop_due_events(now, lookahead_sec=0.02, max_events=64)` extrae eventos vencidos con un pequeno adelanto.

El transporte cuenta:

- `sent_events_total`;
- `failed_events_total`;
- `sent_bytes_total`;
- `dropped_events_total`;
- `last_error`.

Si `EEG_MIDI_LIVE_ENABLED=False`, los eventos pueden generarse pero se descartan intencionadamente y se contabilizan como `dropped_events_total`. En final-v4, el valor por defecto es `True`.

El quality gate impide generar nuevos compases con ventanas malas, pero puede haber eventos ya programados de una ventana anterior. Por eso existe panic MIDI.

## 10. Piano roll y controles WebUI

El piano roll web no lee el puerto MIDI fisico. Usa:

```text
music.recent_notes
```

que se rellena mediante `_remember_recent_notes()` justo despues de generar notas. Esto permite ver la intencion musical aunque el transporte MIDI fisico estuviera desactivado.

La WebUI permite cambiar:

```text
root_note
main_note
scale_key
```

El cambio pasa por `BackendService.update_music_config()`, envia panic si procede, reconstruye `ScaleConfig`, resetea memoria musical y vacia notas recientes.

Estas acciones no modifican firmware, no cambian ADS1299 y no activan/desactivan el transporte MIDI.

## 11. Enabled/disabled

| Capa | Flag | Default final-v4 | Resultado |
| --- | --- | --- | --- |
| Python MIDI | `EEG_MIDI_LIVE_ENABLED` | `True` | Scheduler activo, transporte envia por Bridge. |
| Firmware MIDI | `MIDI_UART_ENABLED` | `1` | Handler registrado, escribe UART y devuelve `true`. |
| UART fisica | `MIDI_SERIAL` | `Serial1` | D1/TX validado con TX invertido obligatorio. |
| Loop test Python | `EEG_MIDI_TEST_LOOP_AUTOSTART` | `False` | La prueba MIDI no tapa la sonificacion EEG al arrancar. |
| Self-test MCU | `MIDI_MCU_SELF_TEST_ENABLED` | `0` | Arpegio firmware apagado por defecto. |

## 12. Rutas diagnosticas y laterales

No forman parte del flujo principal EEG->MIDI:

```text
POST /midi/test-note*
POST /midi/test-sequence*
POST /midi/test-loop/*
MIDI_MCU_SELF_TEST_ENABLED
generate_bars()
generate_notes_for_segment()
LED matrix basada en recent_notes
```

Estas rutas pueden ser utiles para diagnostico, pero no deben aparecer como parte principal de la arquitectura UML.

## 13. Riesgos

- Cambiar UART, circuito o polaridad exige repetir validacion fisica MIDI.
- Quitar panic MIDI puede dejar notas colgadas.
- Aumentar densidad musical puede saturar Bridge o generar exceso de eventos.
- El scheduler puede mantener eventos ya programados aunque una ventana posterior sea mala.
- Cambiar nombres publicos de sonificacion rompe WebUI, capturas, reportes y figuras.
- Quitar aliases legacy sin migrar `MusicSegment`/backend puede romper la generacion musical.
- Activar test loop o self-test puede confundirse con sonificacion EEG real.
- Los endpoints musicales WebUI necesitan tests de contrato para evitar desincronizar `assets/app.js` y `web_server.py`.

## 14. Pruebas minimas si se toca sonificacion/MIDI

1. `python3 -m py_compile python/sonification_features.py python/music_segment.py python/music_bar.py python/music_note.py python/midi_live.py python/midi_byte_transport.py`.
2. Test `SonificationFeatures.to_dict()` con nombres final-v4.
3. Test gate 0: reduce densidad, velocity y probabilidad.
4. Test `MusicSegmentBuilder` con root/main/scale validos.
5. Test `BarGenerator.generate_live_bar()` con seed fija.
6. Test `NoteGenerator.generate_notes_for_bar()` sin notas fuera de escala.
7. Test `MidiScheduler.panic()` limpia cola y active notes.
8. Test `event_to_midi_bytes()` para note_on, note_off, CC y program change.
9. Test `MidiByteTransport` con Bridge mock.
10. Prueba en placa: `/midi/panic`.
11. Prueba en placa: nota diagnostica por `midi_bytes`.
12. Prueba en placa: sonificacion EEG durante captura corta.
13. Si cambia densidad musical o lookahead, revisar benchmarks/Bridge.

## 15. Relacion con futura version esencial/UML

En UML principal deben aparecer:

```text
SonificationFeatureAdapter
SonificationFeatures final-v4
MusicSegmentBuilder.build_live_segment
BarGenerator.generate_live_bar
NoteGenerator.generate_notes_for_bar
MidiScheduler
MidiLiveEvent
event_to_midi_bytes
MidiByteTransport
Bridge.call("midi_bytes")
firmware midi_bytes
Serial1/D1 TXINV
```

Deben quedar laterales o diagnosticos:

```text
generate_bars
generate_notes_for_segment
MIDI test endpoints
MIDI test loop
MIDI MCU self-test
LED matrix
legacy aliases
```

## 16. Conclusion

La sonificacion final-v4 convierte rasgos EEG ya filtrados y evaluados por quality gate en controles musicales normalizados. Estos controles generan segmentos, compases y notas MIDI, que se programan temporalmente y se envian al firmware mediante `midi_bytes` para salir fisicamente por MIDI OUT.

Para el TFG, la idea clave es:

```text
EEG features + quality gate -> controles musicales -> notas MIDI -> salida fisica validada
```

La salida musical debe interpretarse como sonificacion experimental de rasgos EEG, no como diagnostico clinico.
