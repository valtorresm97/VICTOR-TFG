# 06. Auditoria LED matrix / matrix scroll

## Estado general

La matriz LED implementada es un piano scroll compacto sincronizado con el piano roll web. No hay un pipeline musical independiente: Python calcula el frame LED desde `music.recent_notes`, la misma lista usada por `assets/app.js`.

## Arquitectura

```text
NoteGenerator
  ↓
BackendService._remember_recent_notes()
  ↓
recent_notes en snapshot
  ├─ Web UI renderPianoRoll()
  └─ build_led_matrix_frame()
       ↓
     LedMatrixTransport.send_frame()
       ↓
     Bridge.call("led_matrix_frame", payload 13x8)
       ↓
     MCU led_matrix_frame()
       ↓
     Arduino_LED_Matrix.draw()
```

## Parametros LED

| Parametro LED | Valor actual | Archivo | Configurable | Comentario |
| --- | --- | --- | --- | --- |
| Enabled Python | `False` | `led_matrix_visualizer.py` | `EEG_LED_MATRIX_ENABLED` | No llama Bridge si esta desactivado. |
| Enabled firmware | `0` | `sketch.ino` | Macro `LED_MATRIX_ENABLED` | Compila Arduino_LED_Matrix solo si se habilita. |
| Resolucion | `13 x 8` | `led_matrix_visualizer.py`, `sketch.ino` | Env width/height en Python | Firmware espera exactamente 104 bytes. |
| Brillo | `1..7`, default `7` | `led_matrix_visualizer.py` | `EEG_LED_MATRIX_BRIGHTNESS` | Compatible con grayscale 3 bits. |
| Refresh | `8 Hz` | `led_matrix_visualizer.py` | `EEG_LED_MATRIX_REFRESH_HZ` | Limitado a 1..30 Hz. |
| Pitch center | `G4 / 67` default | `backend_service.py`, `led_matrix_visualizer.py` | `EEG_LED_MATRIX_PITCH_CENTER` | Default toma main note. |
| Dynamic center | `False` | `led_matrix_visualizer.py` | `EEG_LED_MATRIX_DYNAMIC_CENTER` | Si true usa mediana de notas. |
| Visible pitch span | `8` | `led_matrix_visualizer.py` | `EEG_LED_MATRIX_VISIBLE_PITCH_SPAN` | Rango vertical. |
| Clip mode | `ignore` | `led_matrix_visualizer.py` | `EEG_LED_MATRIX_CLIP_MODE` | Tambien `saturate`. |
| Note mode | `point` | `led_matrix_visualizer.py` | `EEG_LED_MATRIX_NOTE_MODE` | Tambien `duration`. |
| Max points | `24` | `led_matrix_visualizer.py` | `EEG_LED_MATRIX_MAX_POINTS` | Controla carga/frame. |
| Bridge method | `led_matrix_frame` | ambos | `EEG_LED_MATRIX_BRIDGE_METHOD` en Python | Debe coincidir con firmware. |

## Mapeos

- Eje X: `abs_start` dentro de la ventana reciente (`RECENT_NOTES_WINDOW_SEC=20.0`). Las notas antiguas quedan a la izquierda y las recientes a la derecha.
- Eje Y: pitch MIDI relativo a `pitch_center`; pitches altos suben.
- Centrado: fijo por defecto en `MUSIC_MAIN_NOTE` (`G4`), o dinamico por mediana si se activa.
- Recorte: `ignore` descarta notas fuera del rango vertical; `saturate` las pega al borde.
- Brillo: velocity 0..127 se mapea a intensidad 1..brightness.
- Modo duracion: si `note_mode=duration`, dibuja una linea horizontal desde start hasta end.

## Firmware

`led_matrix_frame(std::vector<uint8_t> frame)`:

- valida longitud `13*8`,
- si `LED_MATRIX_ENABLED=1`: `ledMatrix.draw(frame.data())`,
- si `LED_MATRIX_ENABLED=0`: ignora el frame y devuelve `false`.

La matriz se inicializa en `setup()` solo si se compila con LED habilitado:

- `ledMatrix.begin()`,
- `ledMatrix.setGrayscaleBits(3)`,
- `ledMatrix.clear()`.

## Evitar bloqueo

Protecciones actuales:

- LED desactivado por defecto en Python y firmware.
- Python no llama Bridge si disabled.
- El transporte salta frames identicos.
- Refresh bajo por defecto (8 Hz).
- Payload compacto fijo: 104 bytes.
- El MCU no calcula notas ni historial.

Riesgos restantes:

- `Bridge.call` LED es sincronico y comparte canal con EEG/MIDI.
- No hay panel UI dedicado con `last_error`.
- No hay boton reset/clear LED.
- Python permite width/height via env, pero firmware sigue esperando 13x8.
