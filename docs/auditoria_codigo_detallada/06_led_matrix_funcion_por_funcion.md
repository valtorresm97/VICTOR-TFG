# 06. LED matrix funcion por funcion

## Estado actual

La matriz fisica esta desactivada por defecto. Python calcula frames desde `recent_notes` y, si se activa, `LedMatrixTransport` envia filas 13x8 empaquetadas al handler firmware `led_matrix_row`. Tras eliminar redundancias, la salida unica del visualizer es `rows`; ya no existe `packed_points`.

## Configuracion

| Parametro | Default | Fuente | Comentario |
| --- | --- | --- | --- |
| Enabled | `False` | `EEG_LED_MATRIX_ENABLED` | Evita Bridge calls LED por defecto. |
| Width | 13 | `runtime_config.py` | Compatible Arduino LED Matrix. |
| Height | 8 | `runtime_config.py` | 8 filas; firmware usa mask uint8. |
| Brightness | 1..7 | Env | 3 bits por pixel. |
| Refresh | default runtime | Env | Limitado antes de enviar. |
| Frame format | `rows[height][width]` | `led_matrix_visualizer.py` | Unico contrato actual. |

## Funciones

| Archivo | Funcion | Entrada | Salida | Estado | Formato de frame | Riesgo | Test recomendado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `led_matrix_visualizer.py` | `_safe_float` | any | float | Ninguno | N/A | Bajo | NaN/default. |
| `led_matrix_visualizer.py` | `_safe_int` | any | int | Ninguno | N/A | Bajo | Invalid input. |
| `led_matrix_visualizer.py` | `_clamp` | value,lo,hi | float | Ninguno | N/A | Bajo | Bordes. |
| `led_matrix_visualizer.py` | `LedMatrixConfig.from_env` | default pitch | config | Ninguno | Config dict | Env mal parseado puede deformar frame | Test env. |
| `led_matrix_visualizer.py` | `LedMatrixConfig.to_dict` | self | dict | Ninguno | Snapshot config | Bajo | Schema. |
| `led_matrix_visualizer.py` | `_pitch_center` | notes,config | MIDI center | Ninguno | N/A | Si dinamico oscila, frame salta verticalmente | Test dynamic/static. |
| `led_matrix_visualizer.py` | `_x_for_note` | note,now,window,width | x/None | Ninguno | Punto | Tiempo absoluto fuera de ventana se descarta | Test bordes. |
| `led_matrix_visualizer.py` | `_duration_x_end` | note,now,window,width,x | x_end | Ninguno | Punto/duracion | Duracion mal calculada alarga notas | Test duration mode. |
| `led_matrix_visualizer.py` | `_y_for_pitch` | pitch,center,config | y/None | Ninguno | Punto | Clip ignore/saturate cambia visibilidad | Test out-of-range. |
| `led_matrix_visualizer.py` | `_velocity_to_intensity` | velocity,brightness | 0..brightness | Ninguno | Pixel 3-bit | Intensidad 0 se eleva a 1 despues | Test velocity. |
| `led_matrix_visualizer.py` | `build_led_matrix_frame` | recent_notes, now, window_sec, config | dict frame | Ninguno | `points`, `rows` | Contrato principal LED; no debe bloquear backend | `test_led_matrix_visualizer.py`. |
| `led_matrix_transport.py` | `LedMatrixTransport.__init__` | bridge_method,enabled,width,height | objeto | Counters | N/A | Bajo | Init. |
| `led_matrix_transport.py` | `set_enabled` | bool | None | `enabled` | N/A | Bajo | Toggle. |
| `led_matrix_transport.py` | `_frame_to_rows` | frame | rows validadas | Ninguno | `rows` | Critico: valida dimensiones e intensidad 0..7 | Test malformed. |
| `led_matrix_transport.py` | `_pack_row` | list 13 valores | chunk0,chunk1,chunk2 | Ninguno | 13*3=39 bits | Debe coincidir con firmware unpack | Test bit-exact. |
| `led_matrix_transport.py` | `send_frame` | frame | bool | Counters, `_last_payload`, Bridge | 8 llamadas `led_matrix_row` | Puede cargar Bridge si refresh alto | Mock Bridge + placa. |
| `led_matrix_transport.py` | `get_status` | None | dict | Ninguno | Snapshot | Bajo | Schema. |
| `sketch.ino` | `led_matrix_row` | row,chunks | bool | `led_frame_buffer`, mask, LED fisico | Chunks positivos 16/16/7 bits | Handler devuelve false si disabled; Bridge puede contarlo fallo | Prueba dry-run y enabled. |

## Mapeo

- X: `abs_start` dentro de ventana `now - window_sec .. now`, convertido a 0..width-1.
- Y: pitch MIDI relativo a `pitch_center` o mediana reciente si `dynamic_pitch_center=True`.
- Intensidad: velocity 0..127 escalada a `brightness`, minimo 1 para notas visibles.
- `note_mode="duration"` pinta varias columnas hasta `abs_end`.
- Puntos duplicados `(x,y)` se eliminan con `occupied`.
- `max_points` limita trabajo por frame.

## Riesgos

- Si `EEG_LED_MATRIX_ENABLED=1`, cada frame genera hasta 8 `Bridge.call`; vigilar `rx lost/drops`.
- Firmware solo dibuja si `LED_MATRIX_ENABLED=1`; si no, handler valida y devuelve false.
- Cambiar width/height por env debe coordinarse con firmware si se usa matriz fisica Arduino 13x8.
