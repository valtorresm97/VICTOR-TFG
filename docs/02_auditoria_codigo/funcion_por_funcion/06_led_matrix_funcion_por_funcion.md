# 06. LED matrix funcion por funcion - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Re-auditoria final-v4: revisada contra codigo real en `firmware-final-v4` desde la rama documental `refactor/essential-eeg-midi-plan`.

Objetivo de esta re-auditoria: documentar la matriz LED como subsistema lateral/opcional que visualiza `music.recent_notes`, no como parte necesaria del flujo principal EEG->MIDI.

## 1. Estado final-v4

La matriz LED esta desactivada por defecto tanto en firmware como en Python:

| Capa | Parametro | Valor final-v4 | Consecuencia |
| --- | --- | --- | --- |
| Firmware | `LED_MATRIX_ENABLED` | `0` | El handler `led_matrix_row` valida/desempaqueta, pero devuelve `false` y no dibuja. |
| Python | `EEG_LED_MATRIX_ENABLED` | `False` por defecto | `LedMatrixTransport.send_frame()` no llama a Bridge y cuenta dropped frames. |
| Backend | `_maybe_update_led_matrix()` | Solo actua si `led_matrix_transport.enabled` | Sin LED habilitado no hay trafico Bridge adicional. |
| WebUI | Piano roll | Activo | Usa `music.recent_notes`, misma fuente que podria visualizar la LED. |

Lectura correcta:

```text
La matriz LED no interpreta EEG.
La matriz LED no genera notas.
La matriz LED no envia MIDI.
La matriz LED es solo una visualizacion opcional de music.recent_notes.
```

Para el TFG y la version esencial UML, la ruta principal validada es EEG->MIDI fisico. LED matrix debe tratarse como consumidor lateral opcional.

## 2. Flujo secundario LED

```text
Sonificacion EEG
  -> MusicSegment / Bar / NoteEvent
  -> BackendService._remember_recent_notes()
  -> music.recent_notes
  -> WebUI piano roll
  -> build_led_matrix_frame() si LED enabled
  -> LedMatrixTransport.send_frame()
  -> Bridge.call("led_matrix_row", row_idx, chunk0, chunk1, chunk2)
  -> firmware led_matrix_row()
  -> Arduino_LED_Matrix si LED_MATRIX_ENABLED=1
```

Flujo principal que no depende de LED:

```text
Sonificacion EEG
  -> NoteEvent
  -> MidiScheduler
  -> MidiByteTransport
  -> Bridge.call("midi_bytes")
  -> Serial1/D1 TX invertido
  -> MIDI OUT fisico
```

## 3. Configuracion activa

| Parametro | Default | Fuente | Comentario |
| --- | ---: | --- | --- |
| Enabled Python | `False` | `EEG_LED_MATRIX_ENABLED` | Evita Bridge calls LED por defecto. |
| Enabled firmware | `0` | `LED_MATRIX_ENABLED` | Evita dibujar en Arduino_LED_Matrix por defecto. |
| Width | `13` | `runtime_config.py` | Compatible con Arduino LED Matrix integrada. |
| Height | `8` | `runtime_config.py` | 8 filas; firmware usa mascara de 8 bits. |
| Visible pitch span | `8` | `runtime_config.py` | Rango vertical alrededor del centro. |
| Refresh | `8.0 Hz` | `runtime_config.py` | Limitado para no cargar Bridge. |
| Brightness | `7` | `runtime_config.py` | 3 bits por pixel. |
| Max points | `24` | `runtime_config.py` | Limita trabajo por frame. |
| Clip mode | `ignore` | `runtime_config.py` | Ignora notas fuera de rango vertical. |
| Note mode | `point` | `runtime_config.py` | No pinta duraciones por defecto. |
| Bridge method | `led_matrix_row` | `runtime_config.py` | Handler firmware. |
| Frame format | `rows[height][width]` | `led_matrix_visualizer.py` | Contrato actual con el transporte. |

## 4. Contrato Bridge LED

Contrato Python->MCU:

```text
Bridge.call("led_matrix_row", row_idx, chunk0, chunk1, chunk2)
```

Formato:

- `row_idx`: fila 0..7;
- cada fila tiene 13 pixeles;
- cada pixel usa brillo 0..7;
- 13 pixeles * 3 bits = 39 bits;
- se empaquetan como `chunk0` 16 bits, `chunk1` 16 bits, `chunk2` 7 bits.

Diferencia frente a MIDI:

```text
led_matrix_row es opcional y secundario.
midi_bytes es esencial y validado para MIDI OUT fisico.
```

No mezclar ambos contratos ni usar LED como prueba de MIDI.

## 5. Funciones re-auditadas

| Archivo | Clase/Funcion | Entrada | Salida | Estado | Que hace | Riesgo | Test recomendado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `led_matrix_visualizer.py` | `_safe_float` | any, default | float | Ninguno | Convierte seguro y rechaza NaN/Inf | Bajo | NaN/default. |
| `led_matrix_visualizer.py` | `_safe_int` | any, default | int | Ninguno | Convierte seguro | Bajo | Invalid input. |
| `led_matrix_visualizer.py` | `_clamp` | value,lo,hi | float | Ninguno | Limita rango | Bajo | Bordes. |
| `led_matrix_visualizer.py` | `LedMatrixConfig` | dataclass | config | Inmutable | Config de visualizacion LED | Env mal elegido puede deformar frame | Test config. |
| `led_matrix_visualizer.py` | `LedMatrixConfig.from_env` | default_pitch_center | config | Ninguno | Lee env vars y aplica limites | Si se activa sin placa puede generar trafico Bridge | Test env. |
| `led_matrix_visualizer.py` | `LedMatrixConfig.to_dict` | self | dict | Ninguno | Snapshot config | Bajo | Schema. |
| `led_matrix_visualizer.py` | `_pitch_center` | notes,config | MIDI center | Ninguno | Centro fijo o mediana reciente | Dynamic center puede hacer saltar verticalmente | Test dynamic/static. |
| `led_matrix_visualizer.py` | `_x_for_note` | note,now,window,width | x/None | Ninguno | Posicion temporal dentro de ventana | Notas fuera de ventana se descartan | Test bordes. |
| `led_matrix_visualizer.py` | `_duration_x_end` | note,now,window,width,x | x_end | Ninguno | Final de barra si `note_mode=duration` | Puede alargar visualmente notas | Test duration mode. |
| `led_matrix_visualizer.py` | `_y_for_pitch` | pitch,center,config | y/None | Ninguno | Mapea pitch a fila | `ignore` oculta notas fuera de rango; `saturate` las pega al borde | Test pitch extremos. |
| `led_matrix_visualizer.py` | `_velocity_to_intensity` | velocity,brightness | 0..brightness | Ninguno | Mapea velocity a brillo | Intensidad final se fuerza minimo 1 en notas visibles | Test velocity 0/127. |
| `led_matrix_visualizer.py` | `build_led_matrix_frame` | `recent_notes`, now, window, config | dict con `points` y `rows` | Ninguno | Convierte notas recientes en frame 13x8 | No debe bloquear backend; usa `max_points` | `test_led_matrix_visualizer.py`. |
| `led_matrix_transport.py` | `LedMatrixTransport.__init__` | bridge_method, enabled, width, height | objeto | Counters | Configura transporte | Bajo | Init. |
| `led_matrix_transport.py` | `set_enabled` | bool | None | `enabled` | Activa/desactiva envio | Bajo | Toggle. |
| `led_matrix_transport.py` | `_frame_to_rows` | frame dict | rows validadas | Ninguno | Valida alto/ancho y clampa 0..7 | Critico si frame mal formado | Test malformed. |
| `led_matrix_transport.py` | `_pack_row` | fila 13 valores | chunk0,chunk1,chunk2 | Ninguno | Empaqueta 39 bits | Debe coincidir bit a bit con firmware | Test bit-exact. |
| `led_matrix_transport.py` | `send_frame` | frame dict | bool | Counters, `_last_payload`, Bridge | Si enabled, envia 8 filas; si no, cuenta dropped | Puede cargar Bridge si refresh alto | Mock Bridge + placa. |
| `led_matrix_transport.py` | `get_status` | None | dict | Ninguno | Snapshot transport | Bajo | Schema. |
| `backend_service.py` | `_maybe_update_led_matrix` | now | None | `_last_led_frame_t`, LED counters | Si enabled, construye frame desde `_recent_notes` y llama transporte | Lateral; no debe afectar adquisicion/MIDI | Test enabled false/true. |
| `sketch.ino` | `led_matrix_row` | row,chunks | bool | `led_frame_buffer`, `led_rows_received_mask` | Desempaqueta una fila y dibuja si llegan 8 filas y LED enabled | Devuelve false con LED off; posible carga Bridge si se activa | Dry-run + enabled test. |

## 6. Mapeo visual

- X: `abs_start` dentro de la ventana `now - window_sec .. now`, convertido a `0..width-1`.
- Y: `pitch_midi` relativo a `pitch_center`, o mediana reciente si `dynamic_pitch_center=True`.
- Intensidad: `velocity 0..127` escalada a `brightness`, con minimo 1 para notas visibles.
- `note_mode="point"`: pinta una columna por nota.
- `note_mode="duration"`: pinta varias columnas hasta `abs_end`.
- Puntos duplicados `(x,y)` se eliminan con `occupied`.
- `max_points` limita trabajo por frame.
- `rows` es la unica salida necesaria para el transporte.
- `points` se conserva para debug/visualizacion, pero no es el contrato firmware.

## 7. Observabilidad

El snapshot expone:

```text
led_matrix.config
led_matrix.transport.enabled
led_matrix.transport.bridge_method
led_matrix.transport.sent_frames_total
led_matrix.transport.failed_frames_total
led_matrix.transport.dropped_frames_total
led_matrix.transport.skipped_unchanged_frames_total
led_matrix.transport.sent_bytes_total
led_matrix.transport.last_error
led_matrix.transport.last_point_count
```

La WebUI final-v4 no necesita renderizar estado LED para la memoria. El piano roll web ya cubre la visualizacion principal de notas.

## 8. Hallazgos para simplificacion futura

| Hallazgo | Impacto | Recomendacion futura |
| --- | --- | --- |
| LED no forma parte del flujo EEG->MIDI validado | Puede confundir UML si se pone en el camino principal | Omitir del UML principal o poner como consumidor lateral de `music.recent_notes`. |
| `points` y `rows` coexisten en frame | `rows` es contrato de transporte; `points` es debug | En version esencial, documentar solo `rows` si se simplifica. |
| `LedMatrixConfig.from_env` permite width/height variables | Firmware esta fijado a 13x8 | No exponer cambios de tamano en version esencial. |
| `dynamic_pitch_center` puede mover verticalmente la vista | Visualmente util, pero menos estable | Mantener default false. |
| `note_mode=duration` aumenta pixeles/puntos | Puede cargar mas y saturar visualmente | Mantener default `point`. |
| `send_frame` hace hasta 8 `Bridge.call` por frame | Puede competir con EEG/MIDI en Bridge | Mantener disabled salvo prueba especifica. |
| Firmware devuelve `false` si LED off | Puede contarse como fallo si Python fuerza enabled | Activar Python LED solo si firmware LED tambien esta enabled. |

## 9. Riesgos principales

- Activar LED durante benchmarks altera la carga de Bridge y puede invalidar comparacion temporal.
- Cambiar `width/height` en Python sin cambiar firmware rompe empaquetado/dibujo.
- Cambiar empaquetado 3 bits por pixel rompe `led_matrix_row`.
- Activar `duration` o refresh alto puede generar mas trafico.
- Interpretar LED como evidencia del funcionamiento EEG->MIDI seria incorrecto; es solo visualizacion secundaria.
- Borrar LED sin revisar imports puede romper `backend_service.py`.

## 10. Pruebas minimas antes de aceptar cambios LED

No aplicar cambios runtime en esta fase documental. Si en el futuro se toca LED:

1. `python3 -m py_compile python/led_matrix_visualizer.py python/led_matrix_transport.py python/backend_service.py`.
2. Ejecutar `python python/tools/test_led_matrix_visualizer.py` si esta disponible en placa/entorno.
3. Test frame vacio.
4. Test pitch center fijo.
5. Test clipping ignore/saturate.
6. Test velocity 0/127.
7. Test `_pack_row` bit-exact frente a `led_matrix_row`.
8. Test Python disabled: no Bridge calls.
9. Test firmware disabled: handler devuelve false sin dibujar.
10. Si se activa fisicamente: medir `notify_max_us`, `loop_max_us`, drops y MIDI panic.

## 11. Recomendacion para version esencial UML

UML principal EEG->MIDI:

```text
No incluir LED matrix en el camino principal.
```

UML lateral opcional:

```text
music.recent_notes
  -> LedMatrixConfig
  -> build_led_matrix_frame()
  -> LedMatrixTransport
  -> Bridge.call("led_matrix_row")
  -> led_matrix_row()
```

Regla para simplificacion:

```text
Mantener LED como modulo opcional o excluirlo de la version esencial.
No tocar midi_bytes ni EEG por simplificar LED.
No activar LED durante pruebas de rendimiento salvo benchmark especifico.
```



