# 05. Sonificacion y MIDI funcion por funcion - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Re-auditoria final-v4: revisada contra codigo real en `firmware-final-v4` desde la rama documental `refactor/essential-eeg-midi-plan`.

Objetivo de esta re-auditoria: documentar la cadena final EEG features -> controles de sonificacion -> musica -> scheduler MIDI -> transporte `midi_bytes` -> MIDI OUT fisico, con nombres reportables final-v4 y decisiones para futura simplificacion.

## 1. Flujo final-v4

```text
DSP features CH1
  -> compute_spectral_quality()
  -> SonificationFeatureAdapter.update()
  -> SonificationFeatures final-v4
  -> MusicSegmentBuilder.build_live_segment()
  -> BarGenerator.generate_live_bar()
  -> NoteGenerator.generate_notes_for_bar()
  -> MidiScheduler.schedule_notes()
  -> MidiScheduler.pop_due_events()
  -> MidiByteTransport.send_events()
  -> Bridge.call("midi_bytes", n, b0, b1, b2)
  -> firmware midi_bytes()
  -> Serial1 / D1 / TX invertido
  -> MIDI OUT fisico
```

El EEG no decide directamente la tonalidad ni la nota principal. En final-v4, `root_note`, `main_note` y `scale_key` son controles de usuario/WebUI. El EEG modula densidad, registro, dinamica, probabilidad, estabilidad y tension musical.

## 2. Nombres reportables final-v4

En final-v4, la salida publica de sonificacion usa nombres defendibles desde EEG:

| Nombre publico | Alias legacy interno | Uso musical |
| --- | --- | --- |
| `alpha_drive` | `calmness` | Tendencia alfa/reposo, estabilidad relativa. |
| `beta_gamma_drive` | `tension` | Tension/actividad rapida. |
| `rms_beta_activity` | `activity` | Actividad global con RMS, beta y gamma. |
| `band_driven_density` | `rhythmic_density` | Densidad ritmica. |
| `spectral_register` | `register` | Centro/registro melodico. |
| `alpha_stability` | `harmonic_stability` | Estabilidad armonica. |
| `rms_band_velocity` | `velocity_factor` | Dinamica MIDI. |
| `band_note_probability` | `note_probability` | Probabilidad de activar notas. |

Criterio para documentacion y TFG:

```text
Usar siempre los nombres publicos final-v4.
Los alias legacy solo existen para compatibilidad interna y no deben protagonizar el UML principal.
```

## 3. Responsabilidades por modulo

| Modulo | Responsabilidad | No debe hacer | Estado final-v4 |
| --- | --- | --- | --- |
| `sonification_features.py` | Convertir features DSP + quality gate en controles reportables estables | No calcula DSP, no genera notas, no envia MIDI | Esencial. |
| `music_segment.py` | Convertir controles de sonificacion en estado musical de compas | No decide root/main automaticamente; no lee ADS/DSP crudo | Esencial, pero mantiene campos legacy internos. |
| `music_bar.py` | Generar acorde y patron ritmico de 16 slots | No genera bytes MIDI | Esencial. |
| `music_note.py` | Convertir Bar + MusicSegment en `NoteEvent` | No schedulea ni envia MIDI | Esencial. |
| `midi_live.py` | Convertir notas en eventos MIDI programados y aplicar panic | No accede a Bridge ni D1/TX | Esencial. |
| `midi_byte_transport.py` | Convertir eventos a bytes y enviarlos por `Bridge.call("midi_bytes")` | No genera musica | Esencial. |
| `music_utils.py` | Parsear notas tipo C4/F#3/Bb5 a MIDI | No conoce EEG | Utilidad esencial simple. |
| `scale_registry.py` | Construir escalas disponibles para WebUI/backend | No cambia root/main por EEG | Utilidad esencial simple. |

## 4. Funciones y clases re-auditadas

| Archivo | Clase | Funcion | Entrada | Salida | Estado | Que decide | Riesgo musical/tecnico | Test recomendado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sonification_features.py` | `SonificationFeatures` | propiedades legacy | self | alias float | Ninguno | Compatibilidad interna | Pueden ocultar migracion incompleta | Test alias == nombre nuevo. |
| `sonification_features.py` | `SonificationFeatures` | `to_dict()` | self | dict | Ninguno | Serializacion snapshot sin nombres legacy | Cambiar claves rompe UI/reports | Snapshot test. |
| `sonification_features.py` | N/A | `_safe_float/_safe_optional_float` | any | float/None | Ninguno | Sanitiza NaN/Inf | Bajo | NaN test. |
| `sonification_features.py` | N/A | `_clamp01` | float | 0..1 | Ninguno | Limites controles | Bajo | Bordes. |
| `sonification_features.py` | N/A | `_ratio_or_none/_ratio01` | num,den | ratio | Ninguno | Ratios seguros alpha/beta | Bajo | Den cero. |
| `sonification_features.py` | N/A | `_ema` | prev,new,alpha | float | Ninguno | Suavizado | Bajo | Alpha bordes. |
| `sonification_features.py` | N/A | `_norm_freq` | freq | 0..1 | Ninguno | Registro musical por frecuencia | Medio | 0.5/30 Hz. |
| `sonification_features.py` | N/A | `_get_bandpower_rel/_abs` | features | dict bandas | Ninguno | Garantiza delta/theta/alpha/beta/gamma | Medio | Missing bands. |
| `sonification_features.py` | N/A | `_dominant_band` | bp_rel | str/None | Ninguno | Banda dominante | Bajo | Empty. |
| `sonification_features.py` | N/A | `_has_valid_features` | features | bool | Ninguno | Minimo para sonificar | Medio | Missing bp. |
| `sonification_features.py` | N/A | `build_raw_sonification_features` | features, quality | `SonificationFeatures` | Ninguno | Formula controles EEG-reportables | Critico: mapping musical | Tests con features sinteticas/real. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `__init__` | alphas, min baseline | objeto | `_last`, `_rms_baseline_uV` | Parametros EMA/baseline | Medio | Init ranges. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `reset` | Ninguna | Ninguna | Limpia memoria | Reinicio musical | Bajo | Test. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `update` | features, quality | `SonificationFeatures` | Last/baseline | Entrada principal; aplica baseline, quality gate y EMA | Critico live | Test secuencia quality. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `_update_rms_norm` | rms_uV, flag | rms_norm | Baseline | Normalizacion lenta | Medio | Adaptacion con quality mala. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `_apply_rms_norm` | raw, norm | raw | Mutacion raw | Recalcula controles RMS | Medio | Test. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `_apply_quality_gate` | raw | raw | Mutacion raw | Atenua controles si gate baja | Critico seguridad musical | Test gate 0/1. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `_smooth` | raw | raw | Usa `_last` | EMA controles continuos | Medio | Test monotonia. |
| `sonification_features.py` | N/A | `build_sonification_snapshot` | sonif/None | dict | Ninguno | Snapshot UI | Cambiar claves rompe UI | Snapshot test. |
| `music_utils.py` | N/A | `note_name_to_midi` | nota texto | MIDI 0..127 | Ninguno | Parse C4/F#3/Bb5 | Medio | Notas validas/invalidas. |
| `scale_registry.py` | N/A | `build_scale_config` | familia, escala, root | `ScaleConfig` | Ninguno | Escala elegida por backend/WebUI | Root/escala invalidos rompen generacion | Test escalas soportadas. |
| `music_segment.py` | `LiveSegment` | `duration_sec` | self | float | Ninguno | Duracion musical | Bajo | Test. |
| `music_segment.py` | `ScaleConfig` | `contains` | midi | bool | Ninguno | Pertenencia escala | Medio | Test notas. |
| `music_segment.py` | `ScaleConfig` | `nearest_note` | midi | midi | Ninguno | Cuantizacion a escala | Medio | Test cromatico. |
| `music_segment.py` | `MusicSegment` | `to_dict` | self | dict | Ninguno | Snapshot/debug | Bajo | Test enum. |
| `music_segment.py` | `MusicSegmentBuilder` | `_map_density_to_cadence` | density | enum | `_last_cadence` | LOW/MEDIUM/HIGH con histeresis | Medio | Umbrales. |
| `music_segment.py` | `MusicSegmentBuilder` | `_make_live_segment` | t_start,duration | `LiveSegment` | Ninguno | Ventana musical | Bajo | Test. |
| `music_segment.py` | `MusicSegmentBuilder` | `build_live_segment` | sonif, escala, main note, features | `MusicSegment` | `_last_cadence` | Estado musical de compas | Critico | Test valid/invalid y nombres nuevos. |
| `music_bar.py` | `Bar` | dataclass | parametros bar | objeto | Ninguno | Representa acorde/slots | Medio | asdict. |
| `music_bar.py` | `BarGenerator` | `_build_diatonic_triad` | scale, degree | pitches | Ninguno | Acorde triada | Medio | Escala. |
| `music_bar.py` | `BarGenerator` | `_target_degree_raw/_choose_chord_degree` | estabilidad/tension | degree | `_last_degree_idx` | Armonia con histeresis | Medio | Test cambios pequenos. |
| `music_bar.py` | `BarGenerator` | `_target_notes_for_cadence` | cadence | int | Ninguno | Notas por compas | Medio | Cadencias. |
| `music_bar.py` | `BarGenerator` | `_base_slot_weights/_apply_eeg_to_weights` | segment | weights | Ninguno | Pulso y acentos EEG | Medio | Sum/finite. |
| `music_bar.py` | `BarGenerator` | `_weighted_pick_unique` | weights,k | slots | RNG | Seleccion ritmica | Medio | No duplicados. |
| `music_bar.py` | `BarGenerator` | `_build_note_positions` | segment | array | RNG | Slots con notas; slot 0 forzado | Medio | Cadencia. |
| `music_bar.py` | `BarGenerator` | `_build_amplitude_slots` | segment, positions | array | Ninguno | Envolvente musical sintetica, no amplitud EEG real | Medio | Rango. |
| `music_bar.py` | `BarGenerator` | `generate_live_bar` | segment,index | `Bar` | `_last_degree_idx`, RNG | Acorde y patron del compas | Critico musical | Test determinista. |
| `music_bar.py` | `BarGenerator` | `generate_live_bars` | segment,n | list | RNG | Varias barras | Secundario | Smoke. |
| `music_bar.py` | `BarGenerator` | `generate_bars` | segment | list | Ninguno | Wrapper compatibilidad | Ruta legacy; excluir UML principal | No priorizar. |
| `music_note.py` | `NoteEvent` | dataclass | tiempos,pitch,vel | objeto | Ninguno | Nota musical de alto nivel | Medio | Invariantes. |
| `music_note.py` | `NoteGenerator` | `_register_center` | segment | MIDI center | Ninguno | Registro por EEG alrededor de main_note | Medio | Rango. |
| `music_note.py` | `NoteGenerator` | `_scale_pitches_around` | scale,center,span | pitches | Ninguno | Pitches permitidos | Medio | Escala. |
| `music_note.py` | `NoteGenerator` | `_split_chord_and_passing` | pitches,chord | grupos | Ninguno | Chord vs passing | Bajo | Test. |
| `music_note.py` | `NoteGenerator` | `_pitch_target/_choose_pitch` | slot/segment | pitch | RNG/prev pitch | Melodia y tendencia | Medio | Rango/escala. |
| `music_note.py` | `NoteGenerator` | `_pitch_variety_for_segment` | segment | float | Ninguno | Variedad melodica por actividad/tension/probabilidad | Medio | Rango. |
| `music_note.py` | `NoteGenerator` | `_apply_interval_limit` | pitch | pitch | Last pitch | Evita saltos grandes | Medio | Saltos. |
| `music_note.py` | `NoteGenerator` | `_chord_voices` | chord | pitches | Ninguno | Voces de acorde | Bajo | Test. |
| `music_note.py` | `NoteGenerator` | `_velocity_for_slot` | slot/segment/bar | velocity | Ninguno | Dinamica MIDI | Medio | 0..127. |
| `music_note.py` | `NoteGenerator` | `_slot_times/_next_on_slot` | bar/slots | tiempos/slot | Ninguno | Duraciones y enlaces | Medio | No solape raro. |
| `music_note.py` | `NoteGenerator` | `generate_notes_for_bar` | segment,bar,channel,program | list NoteEvent | `_prev_pitch` | Produce notas de compas; ruta live principal | Critico musical | Test no notas fuera escala. |
| `music_note.py` | `NoteGenerator` | `generate_notes_for_segment` | segment,bars | list | `_prev_pitch` | Compatibilidad multi-bar | Ruta secundaria; excluir UML principal | Smoke. |
| `midi_live.py` | `MidiLiveEvent` | `to_dict` | self | dict | Ninguno | Snapshot/transporte | Bajo | Test. |
| `midi_live.py` | N/A | `_clamp_int/_channel/_data7/_event` | valores | evento/valor | Ninguno | Sanitizacion MIDI | Critico | Bordes. |
| `midi_live.py` | N/A | `note_to_live_events` | NoteEvent,time_origin,now | note_on/off | Ninguno | Traduce tiempo musical a monotonic | Critico | Nota tardia/duracion minima. |
| `midi_live.py` | N/A | `notes_to_live_events` | notas | eventos ordenados | Ninguno | Ordena note_off antes de note_on | Critico | Misma hora. |
| `midi_live.py` | N/A | `program_change_event/control_change_event` | datos | evento | Ninguno | Eventos MIDI auxiliares | Medio | Bytes. |
| `midi_live.py` | N/A | `panic_events` | channels | eventos | Ninguno | CC120/CC123 seguridad | Critico | 16 canales. |
| `midi_live.py` | `MidiScheduler` | `schedule_event/events` | eventos | Ninguna | Heap | Inserta y limita cola | Critico | Overflow. |
| `midi_live.py` | `MidiScheduler` | `schedule_notes` | NoteEvents,time_origin | Ninguna | Heap | Programa note_on/off | Critico | Due events. |
| `midi_live.py` | `MidiScheduler` | `panic` | Ninguna | eventos panic | Limpia heap/active | Seguridad | Critico | Test active cleared. |
| `midi_live.py` | `MidiScheduler` | `pop_due_events` | now,lookahead,max | list | Heap/active | Extrae vencidos | Critico para jitter | Test lookahead. |
| `midi_live.py` | `MidiScheduler` | `_track_active_note` | evento | Ninguna | Active notes | Estado aproximado notas | Critico para UI | Test note_on/off/CC. |
| `midi_live.py` | N/A | `event_to_midi_bytes` | event | bytes | Ninguno | Bytes MIDI estandar | Critico para transporte | Test note/program/cc. |
| `midi_byte_transport.py` | `MidiByteTransport` | `__init__/set_enabled` | config | objeto/None | Counters/enabled | Bridge method | Medio | Test disabled. |
| `midi_byte_transport.py` | `MidiByteTransport` | `_bridge_call_succeeded` | result | bool | Ninguno | Compatibilidad retorno Bridge | Medio | Mock retornos. |
| `midi_byte_transport.py` | `MidiByteTransport` | `send_event` | `MidiLiveEvent` | bool | Counters | `Bridge.call("midi_bytes")` | Envia bytes al MCU o dropea | Critico si enabled | Mock Bridge + placa. |
| `midi_byte_transport.py` | `MidiByteTransport` | `send_events` | iterable | int | Counters | `send_event` | Envia lote | Medio | Test. |
| `midi_byte_transport.py` | `MidiByteTransport` | `get_status` | Ninguna | dict | Ninguno | Snapshot | Bajo | Test. |

## 5. Enabled/disabled actual

- `MIDI_LIVE_ENABLED` lee `EEG_MIDI_LIVE_ENABLED`; default `True` en final-v4.
- Firmware `midi_bytes` existe y la UART fisica default es `MIDI_UART_ENABLED=1`.
- MIDI OUT fisico esta validado en `Serial1`/D1 con TX invertido obligatorio para el circuito N-audio.
- Aunque el scheduler genere eventos, `MidiByteTransport` cuenta drops si `enabled=False`.
- `send_panic()` limpia scheduler y envia CC120/CC123 si el transporte esta enabled.
- Panic WebUI existe en `/midi/panic`.
- Los test endpoints MIDI existen, pero son diagnosticos y no deben confundirse con el loop EEG->MIDI.
- La WebUI expone root/main en C3..B5 y escalas `major`, `minor`, `blues`, `spanish`, `arabic`, `harmonic_minor`, `phrygian_dominant`, `minor_pentatonic`, `major_pentatonic`.
- Acordes menos frecuentes: `MUSIC_CHORD_MIN_PERIOD_SEC=12.0` y `MUSIC_CHORD_CHANGE_THRESHOLD=0.45`.
- Mayor variedad melodica: `MUSIC_PITCH_VARIETY=0.65`, `MUSIC_SCALE_RADIUS_SEMITONES=28`, salto maximo 7..16 semitonos segun tension.

## 6. Rutas principales y rutas secundarias

Para version esencial/UML principal, mantener:

```text
SonificationFeatureAdapter.update()
MusicSegmentBuilder.build_live_segment()
BarGenerator.generate_live_bar()
NoteGenerator.generate_notes_for_bar()
MidiScheduler.schedule_notes()
MidiScheduler.pop_due_events()
MidiByteTransport.send_events()
```

Excluir del UML principal o marcar como compatibilidad:

```text
BarGenerator.generate_bars()
NoteGenerator.generate_notes_for_segment()
Alias legacy: activity/calmness/tension/rhythmic_density/register/harmonic_stability/velocity_factor/note_probability
MIDI test loop
MIDI test endpoints
```

No borrar todavia sin busqueda de referencias y prueba en placa.

## 7. Hallazgos para simplificacion futura

| Hallazgo | Impacto | Recomendacion futura |
| --- | --- | --- |
| Nombres publicos nuevos conviven con campos internos legacy en `MusicSegment` | Puede confundir UML y memoria | UML debe mostrar nombres final-v4; internamente se puede migrar mas adelante. |
| `generate_bars()` y `generate_notes_for_segment()` son compatibilidad | No son ruta live principal | Excluir de UML esencial. |
| `midi_live.py` comenta que el transporte a D1 sera futuro | Comentario historico: en final-v4 ya existe `MidiByteTransport` y firmware validado | Limpiar comentario en refactor futuro. |
| `midi_byte_transport.py` comenta que `enabled=False` era recomendado hasta tener handler | Comentario historico: en final-v4 `midi_bytes` existe y MIDI esta enabled por defecto | Limpiar comentario en refactor futuro. |
| `send_test_sequence()` en backend usa sleeps | Diagnostico puede bloquear user_loop | Mantener como diagnostico, no UML principal. |
| Acordes y RNG dependen de estado previo | Reproducibilidad parcial | Para tests, fijar seed o mock RNG. |
| Panic es esencial | Evita notas colgadas | Mantener siempre en version esencial. |
| `MidiByteTransport` interpreta `Bridge.call(None)` como exito | Compatible con App Lab, pero puede ocultar fallo real | Tests con mock + prueba en placa. |

## 8. Riesgos principales

- Cambiar nombres publicos de sonificacion rompe WebUI, capturas y reportes.
- Quitar alias legacy sin migrar `MusicSegment` y `BackendService` puede romper musica.
- Cambiar escala/root/main desde EEG, en vez de usuario, haria menos controlable la sonificacion.
- Aumentar densidad de notas puede saturar Bridge/MIDI.
- Cambiar `midi_bytes` rompe contrato firmware.
- Quitar panic puede dejar notas colgadas.
- Quitar TX invertido o cambiar `Serial1`/D1 rompe MIDI fisico.
- Activar test loop puede enmascarar la sonificacion EEG.

## 9. Pruebas minimas antes de aceptar cambios de sonificacion/MIDI

No aplicar cambios runtime en esta fase documental. Si en el futuro se modifica sonificacion/MIDI:

1. `python3 -m py_compile python/sonification_features.py python/music_segment.py python/music_bar.py python/music_note.py python/midi_live.py python/midi_byte_transport.py`.
2. Test `SonificationFeatures.to_dict()` sin claves legacy.
3. Test quality gate: gate 0 reduce densidad/velocity/probabilidad.
4. Test `MusicSegmentBuilder` con nombres final-v4 y alias legacy.
5. Test `BarGenerator.generate_live_bar()` con seed fija.
6. Test `NoteGenerator.generate_notes_for_bar()` sin notas fuera de escala.
7. Test `MidiScheduler.panic()` limpia cola y notas activas.
8. Test `event_to_midi_bytes()` para note_on, note_off, control_change y program_change.
9. Test `MidiByteTransport` con Bridge mock enabled/disabled.
10. Prueba en placa: `/midi/panic`.
11. Prueba en placa: nota diagnostica por `midi_bytes`.
12. Prueba en placa: sonificacion EEG activa durante captura corta.
13. Si aumenta densidad musical, repetir benchmark/observabilidad Bridge.

## 10. Recomendacion para version esencial UML

UML principal recomendado:

```text
SonificationFeatureAdapter
  -> SonificationFeatures
  -> MusicSegmentBuilder
  -> MusicSegment
  -> BarGenerator
  -> Bar
  -> NoteGenerator
  -> NoteEvent
  -> MidiScheduler
  -> MidiLiveEvent
  -> MidiByteTransport
  -> Bridge.call("midi_bytes")
```

UML secundario/compatibilidad:

```text
generate_bars()
generate_notes_for_segment()
MIDI test loop
MIDI test endpoints
legacy aliases
```

Regla para simplificacion:

```text
Mantener la ruta live estricta.
Ocultar wrappers legacy en los diagramas.
No tocar contrato midi_bytes ni panic.
No presentar test endpoints como parte del flujo EEG->MIDI.
```
