# 05. Sonificacion y MIDI funcion por funcion

## Flujo

```text
DSP features
  -> compute_spectral_quality
  -> SonificationFeatureAdapter.update
  -> MusicSegmentBuilder.build_live_segment
  -> BarGenerator.generate_live_bar
  -> NoteGenerator.generate_notes_for_bar
  -> MidiScheduler.schedule_notes
  -> MidiByteTransport.send_events
  -> Bridge.call("midi_bytes", n, b0, b1, b2)
```

En final-v3 los controles WebUI/MIDI dinamicos vuelven de forma acotada: `root_note`, `main_note` y `scale_key`. No cambian firmware, transporte ni parametros de densidad; cada cambio reconstruye escala/centro melodico, ejecuta `panic()` si procede y limpia memoria musical para evitar notas colgadas.

## Funciones y clases

| Archivo | Clase | Funcion | Entrada | Salida | Estado | Que decide | Riesgo musical/tecnico | Test recomendado |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sonification_features.py` | `SonificationFeatures` | `to_dict()` | self | dict | Ninguno | Serializacion snapshot | Bajo | asdict. |
| `sonification_features.py` | N/A | `_safe_float/_safe_optional_float` | any | float/None | Ninguno | Sanitiza NaN/Inf | Bajo | NaN test. |
| `sonification_features.py` | N/A | `_clamp01` | float | 0..1 | Ninguno | Limites controles | Bajo | Bordes. |
| `sonification_features.py` | N/A | `_ratio_or_none/_ratio01` | num,den | ratio | Ninguno | Ratios seguros alpha/beta | Bajo | Den cero. |
| `sonification_features.py` | N/A | `_ema` | prev,new,alpha | float | Ninguno | Suavizado | Bajo | Alpha bordes. |
| `sonification_features.py` | N/A | `_norm_freq` | freq | 0..1 | Ninguno | Registro musical por frecuencia | Medio | 0.5/30 Hz. |
| `sonification_features.py` | N/A | `_get_bandpower_rel/_abs` | features | dict bandas | Ninguno | Garantiza delta/theta/alpha/beta/gamma | Medio | Missing bands. |
| `sonification_features.py` | N/A | `_dominant_band` | bp_rel | str/None | Ninguno | Banda dominante | Bajo | Empty. |
| `sonification_features.py` | N/A | `_has_valid_features` | features | bool | Ninguno | Minimo para sonificar | Medio | Missing bp. |
| `sonification_features.py` | N/A | `build_raw_sonification_features` | features, quality | `SonificationFeatures` | Ninguno | activity, calmness, tension, density, register, velocity, probability | Critico: mapping musical | Tests con features sintéticas. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `__init__` | alphas, min baseline | objeto | `_last`, `_rms_baseline_uV` | Parametros EMA/baseline | Medio | Init ranges. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `reset` | Ninguna | Ninguna | Limpia memoria | Reinicio musical | Bajo | Test. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `update` | features, quality | `SonificationFeatures` | Last/baseline | Aplica baseline, quality gate y EMA | Critico live | Test secuencia quality. |
| `sonification_features.py` | `SonificationFeatureAdapter` | `_update_rms_norm` | rms_uV, flag | rms_norm | Baseline | Normalizacion lenta | Medio | Adaptacion. |
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
| `music_segment.py` | `MusicSegmentBuilder` | `__init__/reset` | fs | objeto/None | Estado live | Configura builder | Bajo | Smoke. |
| `music_segment.py` | `MusicSegmentBuilder` | `_map_density_to_cadence` | density | enum | Ninguno | LOW/MEDIUM/HIGH | Medio | Umbrales. |
| `music_segment.py` | `MusicSegmentBuilder` | `_make_live_segment` | t_start,duration | `LiveSegment` | Ninguno | Ventana musical | Bajo | Test. |
| `music_segment.py` | `MusicSegmentBuilder` | `build_live_segment` | sonif, escala, main note, features | `MusicSegment` | Ninguno | Estado musical de compas | Critico para musica | Test valid/invalid. |
| `music_bar.py` | `Bar` | dataclass | parametros bar | objeto | Ninguno | Representa acorde/slots | Medio | asdict. |
| `music_bar.py` | `BarGenerator` | `__init__` | seed, subdivision | objeto | RNG | Reproducibilidad | Medio | Seed determinista. |
| `music_bar.py` | `BarGenerator` | `_build_diatonic_triad` | scale, degree | pitches | Ninguno | Acorde triada | Medio | Escala. |
| `music_bar.py` | `BarGenerator` | `_target_degree_raw/_choose_chord_degree` | estabilidad/tension/segment | degree | RNG | Armonia segun EEG | Medio | Test ranges. |
| `music_bar.py` | `BarGenerator` | `_target_notes_for_cadence` | cadence | int | Ninguno | Densidad notas | Medio | Cadencias. |
| `music_bar.py` | `BarGenerator` | `_base_slot_weights/_apply_eeg_to_weights` | segment | weights | Ninguno | Pulso y acentos EEG | Medio | Sum/finite. |
| `music_bar.py` | `BarGenerator` | `_weighted_pick_unique` | weights,k | slots | RNG | Seleccion ritmica | Medio | No duplicados. |
| `music_bar.py` | `BarGenerator` | `_build_note_positions` | segment | array | RNG | Slots con notas | Medio | Cadencia. |
| `music_bar.py` | `BarGenerator` | `_build_amplitude_slots` | segment, positions | array | RNG | Dinamica por slot | Medio | Rango. |
| `music_bar.py` | `BarGenerator` | `generate_live_bar` | segment,index | `Bar` | RNG | Acorde y patron del compas | Critico musical | Test determinista. |
| `music_bar.py` | `BarGenerator` | `generate_live_bars/generate_bars` | segment,n | list | RNG | Varias barras | Medio | Smoke. |
| `music_note.py` | `NoteEvent` | dataclass | tiempos,pitch,vel | objeto | Ninguno | Nota musical | Medio | Invariantes. |
| `music_note.py` | `NoteGenerator` | `__init__/reset` | seed/rangos | objeto | RNG/last_pitch | Config pitch/velocity | Medio | Determinismo. |
| `music_note.py` | `NoteGenerator` | `_register_center` | segment | MIDI center | Ninguno | Registro por EEG | Medio | Rango. |
| `music_note.py` | `NoteGenerator` | `_scale_pitches_around` | scale,center,span | pitches | Ninguno | Pitches permitidos | Medio | Escala. |
| `music_note.py` | `NoteGenerator` | `_split_chord_and_passing` | pitches,chord | grupos | Ninguno | Chord vs passing | Bajo | Test. |
| `music_note.py` | `NoteGenerator` | `_is_downbeat/_pitch_target/_choose_pitch` | slot/segment | pitch | RNG/last pitch | Melodia y tendencia | Medio | Rango/escala. |
| `music_note.py` | `NoteGenerator` | `_apply_interval_limit` | pitch | pitch | Last pitch | Evita saltos grandes | Medio | Saltos. |
| `music_note.py` | `NoteGenerator` | `_chord_voices` | chord | pitches | Ninguno | Voces acorde | Bajo | Test. |
| `music_note.py` | `NoteGenerator` | `_base_velocity/_velocity_for_slot` | slot/segment | velocity | RNG | Dinamica MIDI | Medio | 0..127. |
| `music_note.py` | `NoteGenerator` | `_slot_times/_next_on_slot` | bar/slots | tiempos/slot | Ninguno | Duraciones y enlaces | Medio | No solape raro. |
| `music_note.py` | `NoteGenerator` | `generate_notes_for_bar` | segment,bar,channel,program | list NoteEvent | Last pitch | Produce notas de compas | Critico musical | Test no notas fuera escala. |
| `music_note.py` | `NoteGenerator` | `generate_notes_for_segment` | segment,bars | list | Last pitch | Ruta multi-bar | Medio | Smoke. |
| `midi_live.py` | `MidiLiveEvent` | `to_dict` | self | dict | Ninguno | Snapshot/transporte | Bajo | Test. |
| `midi_live.py` | N/A | `_clamp_int/_channel/_data7/_event` | valores | evento/valor | Ninguno | Sanitizacion MIDI | Critico | Bordes. |
| `midi_live.py` | N/A | `note_to_live_events` | NoteEvent,time_origin,now | note_on/off | Ninguno | Traduce tiempo musical a monotonic | Critico | Nota tardia/duracion minima. |
| `midi_live.py` | N/A | `notes_to_live_events` | notas | eventos ordenados | Ninguno | Ordena note_off antes de note_on | Critico | Misma hora. |
| `midi_live.py` | N/A | `program_change_event/control_change_event` | datos | evento | Ninguno | Eventos MIDI auxiliares | Medio | Bytes. |
| `midi_live.py` | N/A | `all_notes_off_events/panic_events` | channels | eventos | Ninguno | Seguridad MIDI | Critico | 16 canales. |
| `midi_live.py` | `MidiScheduler` | `__init__/clear` | max_queue | objeto/None | Heap/active_notes | Cola eventos | Critico | Queue. |
| `midi_live.py` | `MidiScheduler` | `schedule_event/events` | eventos | Ninguna | Heap | Inserta y limita cola | Critico | Overflow. |
| `midi_live.py` | `MidiScheduler` | `schedule_notes` | NoteEvents,time_origin | Ninguna | Heap | Programa note_on/off | Critico | Due events. |
| `midi_live.py` | `MidiScheduler` | `schedule_program_change` | program,ch,due | Ninguna | Heap | Programa instrumento | Medio | Test. |
| `midi_live.py` | `MidiScheduler` | `panic` | Ninguna | eventos panic | Limpia heap/active | Seguridad | Critico | Test active cleared. |
| `midi_live.py` | `MidiScheduler` | `pop_due_events` | now,lookahead,max | list | Heap/active | Extrae vencidos | Critico para jitter | Test lookahead. |
| `midi_live.py` | `MidiScheduler` | `_track_active_note` | evento | Ninguna | Active notes | Estado aproximado notas | Critico para UI | Test note_on/off/CC. |
| `midi_live.py` | `MidiScheduler` | `active_notes_count/queued_events_count/get_status` | Ninguna | int/dict | Ninguno | Snapshot MIDI | Bajo | Test. |
| `midi_live.py` | N/A | `event_to_midi_bytes` | event | bytes | Ninguno | Bytes MIDI estandar | Critico para transporte | Test note/program/cc. |
| `midi_byte_transport.py` | `MidiByteTransport` | `__init__/set_enabled` | config | objeto/None | Counters/enabled | Bridge method | Medio | Test disabled. |
| `midi_byte_transport.py` | `MidiByteTransport` | `send_event` | `MidiLiveEvent` | bool | Counters | `Bridge.call` | Envia bytes al MCU o dropea | Critico si enabled | Mock Bridge. |
| `midi_byte_transport.py` | `MidiByteTransport` | `send_events` | iterable | int | Counters | `send_event` | Envia lote | Medio | Test. |
| `midi_byte_transport.py` | `MidiByteTransport` | `get_status` | Ninguna | dict | Ninguno | Snapshot | Bajo | Test. |

## Enabled/disabled actual

- `MIDI_LIVE_ENABLED` lee `EEG_MIDI_LIVE_ENABLED`; default `True` en final-v3.
- Aunque el scheduler genera eventos, `MidiByteTransport` cuenta drops si `enabled=False`.
- Firmware `midi_bytes` existe y la UART fisica default es `MIDI_UART_ENABLED=1`.
- MIDI OUT fisico esta validado en `Serial1`/D1 con TX invertido obligatorio para el circuito N-audio.
- Panic WebUI existe y llama backend; si transporte esta disabled no envia bytes fisicos.
- La WebUI expone root/main en C3..B5 y escalas `major`, `minor`, `blues`, `spanish`, `arabic`, `harmonic_minor`, `phrygian_dominant`, `minor_pentatonic`, `major_pentatonic`.
- Acordes menos frecuentes: `MUSIC_CHORD_MIN_PERIOD_SEC=12.0` y `MUSIC_CHORD_CHANGE_THRESHOLD=0.45`.
- Mayor variedad melodica: `MUSIC_PITCH_VARIETY=0.65`, `MUSIC_SCALE_RADIUS_SEMITONES=28`, salto maximo 7..16 semitonos segun tension.

## Riesgos

- La cola MIDI puede acumular eventos si generacion supera consumo.
- `send_panic()` limpia scheduler aunque transporte este disabled; esto esta bien para evitar estado colgado interno.
- Los controles WebUI musicales ya existen; falta cubrirlos con pruebas de snapshot/endpoints.
- Si se cambia el circuito MIDI OUT, se debe revalidar polaridad: final-v3 asume TX invertido obligatorio.
