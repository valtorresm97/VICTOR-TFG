# LED matrix piano scroll

Documento activo secundario de referencia para la visualizacion LED tipo piano scroll.

Estado final-v4:

```text
Rama integrada actual: firmware-final-v4
Estado por defecto firmware: LED_MATRIX_ENABLED=0
Estado por defecto Python: EEG_LED_MATRIX_ENABLED=0
Rol: visualizacion secundaria de music.recent_notes, no ruta principal EEG->MIDI
```

La version final-v4 valida el flujo EEG->MIDI fisico y la WebUI. La matriz LED queda documentada como subsistema opcional/desactivado por defecto. No debe incluirse como requisito del flujo principal ni como evidencia central del TFG.

## Objetivo

La matriz LED representa fisicamente las mismas notas que alimentan el piano
roll de la Web UI. La matriz no interpreta EEG: recibe una vista compacta de
`music.recent_notes`, que ya contiene las notas generadas por la sonificacion.

Flujo secundario:

```text
EEG features
   â†“
MusicSegment
   â†“
Bar
   â†“
NoteEvent[]
   â†“
MidiScheduler
   â†“
recent_notes / snapshot
   â†“
Web UI piano roll
   â†“
LED matrix piano scroll opcional
   â†“
Bridge.call("led_matrix_row", row_idx, chunk0, chunk1, chunk2)
   â†“
Arduino_LED_Matrix si LED_MATRIX_ENABLED=1
```

Flujo principal final-v4, que no depende de la matriz:

```text
EEG features
  -> sonification_features
  -> MusicSegment / NoteEvent
  -> MidiScheduler
  -> MidiByteTransport
  -> Bridge.call("midi_bytes")
  -> Serial1/D1 con TX invertido
  -> MIDI OUT fisico
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
- Control: Python calcula el frame; el MCU recibe filas empaquetadas y dibuja.
- Restricciones final-v4: `LED_MATRIX_ENABLED` queda a `0` por defecto en firmware y
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
- La matriz LED reutiliza esa misma fuente si se activa.

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
- `refresh_rate_hz = 8`: tasa conservadora para no cargar Bridge/backend.

Tambien existe `clip_mode=saturate` para fijar notas extremas al borde.

## Arquitectura elegida

Se eligio Python calcula frame y MCU dibuja frame compacto.

Motivos:

- Sincronia directa con la Web UI: ambas vistas usan `recent_notes`.
- Carga MCU minima: no calcula pitch, tiempo ni historial.
- Bridge limitado: 13x8 = 104 bytes logicos por frame, enviados como 8 filas
  empaquetadas de tamano fijo a una tasa configurable.
- El transporte evita reenviar frames identicos, reduciendo trafico cuando no
  cambia la representacion musical.
- Depuracion ligera: el snapshot mantiene solo configuracion y contadores LED,
  no el framebuffer completo.
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
EEG_LED_MATRIX_REFRESH_HZ=8
EEG_LED_MATRIX_BRIGHTNESS=7
EEG_LED_MATRIX_CLIP_MODE=ignore
EEG_LED_MATRIX_NOTE_MODE=point
EEG_LED_MATRIX_BRIDGE_METHOD=led_matrix_row
```

Firmware:

```cpp
#define LED_MATRIX_ENABLED 0
```

Para probar la matriz fisica, compilar con `LED_MATRIX_ENABLED=1` y arrancar
Python con `EEG_LED_MATRIX_ENABLED=1`. No activar hasta confirmar que
`Arduino_LED_Matrix` esta disponible en el entorno UNO Q/App Lab.

## Bridge

Handler aÃ±adido:

```text
Bridge.call("led_matrix_row", row_idx, chunk0, chunk1, chunk2)
```

Cada fila contiene 13 pixeles con brillo 0..7. Python empaqueta esos
`13 * 3 = 39` bits en tres chunks positivos (`16 + 16 + 7` bits), evitando
payload dinamico en el MCU.

El handler valida fila y chunks. Si `LED_MATRIX_ENABLED=0`,
devuelve `false` y no dibuja; sirve como dry-run seguro.

Este handler no sustituye ni modifica el contrato MIDI:

```text
Bridge.call("midi_bytes", n, b0, b1, b2)
```

## Observabilidad

El snapshot aÃ±ade:

- `led_matrix.config`
- `led_matrix.transport.enabled`
- `led_matrix.transport.sent_frames_total`
- `led_matrix.transport.failed_frames_total`
- `led_matrix.transport.last_error`

La Web UI no renderiza preview ni estado LED para no penalizar la pagina. La
observabilidad queda disponible en el snapshot JSON/logs si se necesita
depurar.

## Limitaciones

- La activacion fisica queda pendiente de prueba en UNO Q real.
- El modo minimo dibuja puntos. Existe `note_mode=duration`, pero el modo por
  defecto evita saturar la matriz con barras largas.
- Si hay muchas notas simultaneas, se limita por `EEG_LED_MATRIX_MAX_POINTS`.
- Si una nota sale por arriba/abajo, por defecto se ignora sin romper.
- No forma parte de la evidencia principal de benchmarks/capturas finales.
- No debe activarse durante benchmarks temporales salvo que se quiera medir explicitamente la carga adicional de LED.

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

## Relacion con la version esencial UML

Para la version esencial EEG->MIDI, la matriz LED debe aparecer como modulo secundario u opcional, no como parte del flujo principal.

En diagramas UML principales, puede omitirse o colocarse como consumidor lateral de:

```text
music.recent_notes
```

No debe condicionar los diagramas de adquisicion, DSP, sonificacion ni MIDI fisico.



