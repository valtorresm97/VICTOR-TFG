# LED matrix piano scroll

## Objetivo

La matriz LED representa fisicamente las mismas notas que alimentan el piano
roll de la Web UI. La matriz no interpreta EEG: recibe una vista compacta de
`music.recent_notes`, que ya contiene las notas generadas por la sonificacion.

Flujo real:

```text
EEG features
   ↓
MusicSegment
   ↓
Bar
   ↓
NoteEvent[]
   ↓
MidiScheduler
   ↓
recent_notes / snapshot
   ↓
Web UI piano roll
   ↓
LED matrix piano scroll
   ↓
Bridge.call("led_matrix_frame", frame_bytes)
   ↓
Arduino_LED_Matrix
```

## Auditoria LED matrix

- Documentacion previa en el repositorio: no habia documento especifico de
  matriz LED.
- `sketch/sketch.yaml` declaraba `Adafruit NeoPixel (1.15.4)`, pero no habia
  codigo que inicializara NeoPixel/FastLED/HUB75/RGB ni pines asignados.
- La referencia aportada usa `Arduino_LED_Matrix` y `RouterBridge`, con frames
  row-major y brillo cuantizado 0..7 mediante `matrix.setGrayscaleBits(3)`.
- Resolucion implementada por defecto: 13x8, siguiendo la referencia del
  painter (`AppFrame.create_empty()` usa `height=8`, `width=13`).
- Pines: no aplica en esta version porque `Arduino_LED_Matrix` es la matriz
  integrada/gestionada por libreria. No se han tocado pines ADS1299 ni MIDI.
- Control: Python calcula el frame; el MCU solo recibe bytes y dibuja.
- Restricciones: `LED_MATRIX_ENABLED` queda a `0` por defecto en firmware y
  `EEG_LED_MATRIX_ENABLED=0` por defecto en Python. La activacion fisica queda
  pendiente de probar en UNO Q.

## Pipeline de notas auditado

- `music_note.py` define `NoteEvent` con `t_start`, `t_end`, `pitch_midi`,
  `velocity`, `channel` y `program`.
- `backend_service.py` genera barras musicales desde `MusicSegmentBuilder`,
  `BarGenerator` y `NoteGenerator`.
- `MidiScheduler` recibe esas notas para programar eventos MIDI live.
- `_remember_recent_notes()` guarda las ultimas notas en
  `music.recent_notes`, con tiempos absolutos `abs_start`/`abs_end`.
- `assets/app.js::renderPianoRoll()` usa `music.recent_notes`, calcula una
  ventana temporal `now - recent_notes_window_sec`, dibuja el tiempo en X y
  el pitch en Y.

## Mapeo visual

La matriz reutiliza la misma ventana temporal que la UI:

```text
x_led = round(((abs_start - (now - window_sec)) / window_sec) * (width - 1))
```

Esto hace que las notas antiguas queden a la izquierda y las nuevas avancen
hacia la derecha, igual que el piano roll actual de la Web UI.

El eje Y usa pitch MIDI centrado:

```text
y_led = (height - 1) / 2 - (pitch_midi - pitch_center) * scale
```

Por defecto:

- `pitch_center = MUSIC_MAIN_NOTE` (`G4`, MIDI 67 en esta rama).
- `visible_pitch_span = 8`.
- `clip_mode = ignore`: notas fuera del rango vertical no se dibujan.
- `brightness = 7`: compatible con `Arduino_LED_Matrix` en 3 bits.

Tambien existe `clip_mode=saturate` para fijar notas extremas al borde.

## Arquitectura elegida

Se eligio Python calcula frame y MCU dibuja frame compacto.

Motivos:

- Sincronia directa con la Web UI: ambas vistas usan `recent_notes`.
- Carga MCU minima: no calcula pitch, tiempo ni historial.
- Bridge limitado: 13x8 = 104 bytes por frame a una tasa configurable.
- Depuracion sencilla: el snapshot incluye `led_matrix.frame.rows`.
- Activacion segura: si `EEG_LED_MATRIX_ENABLED=0`, no se llama al Bridge.

Alternativas descartadas para esta version minima:

- Enviar `NoteEvent` al MCU y mantener framebuffer en firmware: mas estado y
  mas riesgo de interferir con adquisicion.
- Enviar animaciones largas: innecesario para piano scroll live y aumenta RAM.
- Mezclar con MIDI OUT: la matriz usa handler Bridge separado y no toca UART.

## Configuracion

Variables Python:

```bash
EEG_LED_MATRIX_ENABLED=0
EEG_LED_MATRIX_WIDTH=13
EEG_LED_MATRIX_HEIGHT=8
EEG_LED_MATRIX_PITCH_CENTER=67
EEG_LED_MATRIX_DYNAMIC_CENTER=0
EEG_LED_MATRIX_VISIBLE_PITCH_SPAN=8
EEG_LED_MATRIX_REFRESH_HZ=12
EEG_LED_MATRIX_BRIGHTNESS=7
EEG_LED_MATRIX_CLIP_MODE=ignore
EEG_LED_MATRIX_NOTE_MODE=point
EEG_LED_MATRIX_BRIDGE_METHOD=led_matrix_frame
```

Firmware:

```cpp
#define LED_MATRIX_ENABLED 0
```

Para probar la matriz fisica, compilar con `LED_MATRIX_ENABLED=1` y arrancar
Python con `EEG_LED_MATRIX_ENABLED=1`. No activar hasta confirmar que
`Arduino_LED_Matrix` esta disponible en el entorno UNO Q/App Lab.

## Bridge

Handler añadido:

```text
Bridge.call("led_matrix_frame", frame_bytes)
```

`frame_bytes` contiene `width * height` bytes en orden row-major, brillo 0..7.

El handler valida que el tamaño sea 104 bytes. Si `LED_MATRIX_ENABLED=0`,
devuelve `false` y no dibuja; sirve como dry-run seguro.

## Observabilidad

El snapshot añade:

- `led_matrix.config`
- `led_matrix.transport.enabled`
- `led_matrix.transport.sent_frames_total`
- `led_matrix.transport.failed_frames_total`
- `led_matrix.transport.last_error`
- `led_matrix.frame.rows`
- `led_matrix.frame.points`

La Web UI muestra estado, frames enviados, errores y un preview 13x8.

## Limitaciones

- La activacion fisica queda pendiente de prueba en UNO Q real.
- El modo minimo dibuja puntos. Existe `note_mode=duration`, pero el modo por
  defecto evita saturar la matriz con barras largas.
- Si hay muchas notas simultaneas, se limita por `EEG_LED_MATRIX_MAX_POINTS`.
- Si una nota sale por arriba/abajo, por defecto se ignora sin romper.

## Pruebas realizadas

Pruebas simuladas esperadas:

```bash
python python/tools/test_led_matrix_visualizer.py
python -m py_compile python/*.py
python -m py_compile python/tools/*.py
```

Validaciones cubiertas por el test:

- lista vacia no rompe;
- centrado vertical por `pitch_center`;
- clipping vertical;
- movimiento X de izquierda a derecha;
- `velocity` afecta brillo;
- `clip_mode=saturate` mantiene notas extremas visibles.
