# 06. Auditoria LED matrix / matrix scroll - final-v4

## 1. Objetivo

Este documento explica la matriz LED como subsistema lateral del proyecto EEG-MIDI. La auditoria funcion por funcion mas exhaustiva esta en:

```text
docs/02_auditoria_codigo/funcion_por_funcion/06_led_matrix_funcion_por_funcion.md
```

La matriz LED no forma parte del flujo principal EEG->MIDI validado. Es una visualizacion opcional de las notas recientes, sincronizada conceptualmente con el piano roll web.

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Estado general final-v4

La matriz LED implementada es un piano scroll compacto basado en:

```text
music.recent_notes
```

No hay un pipeline musical independiente. Python calcula el frame LED desde la misma lista de notas que usa la WebUI para el piano roll.

Estado por defecto:

```text
EEG_LED_MATRIX_ENABLED=False
LED_MATRIX_ENABLED=0
```

Consecuencia:

- Python no envia frames LED por Bridge por defecto.
- El firmware registra `led_matrix_row`, pero no dibuja si `LED_MATRIX_ENABLED=0`.
- La LED no afecta a benchmarks ni capturas finales.
- La LED no debe aparecer en el UML principal EEG->MIDI.

## 3. Arquitectura lateral

```text
NoteGenerator.generate_notes_for_bar()
  â†“
BackendService._remember_recent_notes()
  â†“
music.recent_notes en snapshot
  â”œâ”€ WebUI renderPianoRoll()
  â””â”€ build_led_matrix_frame()
       â†“
     LedMatrixTransport.send_frame()
       â†“
     Bridge.call("led_matrix_row", row_idx, chunk0, chunk1, chunk2)
       â†“
     MCU led_matrix_row()
       â†“
     Arduino_LED_Matrix.draw() si LED_MATRIX_ENABLED=1
```

La ruta principal MIDI no depende de LED:

```text
NoteEvent
  -> MidiScheduler
  -> MidiByteTransport
  -> Bridge.call("midi_bytes")
  -> Serial1/D1 TXINV
  -> MIDI OUT fisico
```

## 4. Parametros LED

| Parametro LED | Valor final-v4 | Archivo | Configurable | Comentario |
| --- | --- | --- | --- | --- |
| Enabled Python | `False` | `runtime_config.py` / `led_matrix_visualizer.py` | `EEG_LED_MATRIX_ENABLED` | No llama Bridge si esta desactivado. |
| Enabled firmware | `0` | `sketch.ino` | Macro `LED_MATRIX_ENABLED` | El handler no dibuja si esta desactivado. |
| Resolucion | `13 x 8` | Python + firmware | Env width/height en Python | Firmware espera 8 filas de 13 pixeles. |
| Brillo | `1..7`, default `7` | `runtime_config.py` | `EEG_LED_MATRIX_BRIGHTNESS` | Compatible con grayscale 3 bits. |
| Refresh | `8 Hz` | `runtime_config.py` | `EEG_LED_MATRIX_REFRESH_HZ` | Limitado para no cargar Bridge. |
| Pitch center | main note por defecto | backend/config | `EEG_LED_MATRIX_PITCH_CENTER` | Por defecto sigue el centro musical. |
| Dynamic center | `False` | `runtime_config.py` | `EEG_LED_MATRIX_DYNAMIC_CENTER` | Si true usa mediana de notas. |
| Visible pitch span | `8` | `runtime_config.py` | `EEG_LED_MATRIX_VISIBLE_PITCH_SPAN` | Rango vertical. |
| Clip mode | `ignore` | `runtime_config.py` | `EEG_LED_MATRIX_CLIP_MODE` | Tambien `saturate`. |
| Note mode | `point` | `runtime_config.py` | `EEG_LED_MATRIX_NOTE_MODE` | Tambien `duration`. |
| Max points | `24` | `runtime_config.py` | `EEG_LED_MATRIX_MAX_POINTS` | Controla carga/frame. |
| Bridge method | `led_matrix_row` | Python + firmware | `EEG_LED_MATRIX_BRIDGE_METHOD` | Debe coincidir con firmware. |

Regla importante:

```text
Python permite configurar width/height por env,
pero el firmware final-v4 espera 13x8.
```

No cambiar dimensiones sin modificar ambos lados.

## 5. Mapeos visuales

- Eje X: `abs_start` dentro de la ventana reciente (`RECENT_NOTES_WINDOW_SEC=20.0`). Las notas antiguas quedan a la izquierda y las recientes a la derecha.
- Eje Y: `pitch_midi` relativo a `pitch_center`; pitches altos suben.
- Centrado: fijo por defecto en `main_note`, o dinamico por mediana si se activa.
- Recorte: `ignore` descarta notas fuera del rango vertical; `saturate` las pega al borde.
- Brillo: velocity 0..127 se mapea a intensidad `1..brightness`.
- Modo `point`: pinta una celda por nota.
- Modo `duration`: si se activa, dibuja una linea horizontal desde start hasta end.
- `max_points` limita la carga por frame.
- `rows` es el contrato de transporte.
- `points` queda como debug/visualizacion interna.

## 6. Firmware

El handler firmware es:

```text
led_matrix_row(row_idx, chunk0, chunk1, chunk2)
```

Comportamiento:

- valida `row_idx`;
- valida chunks positivos de `16 + 16 + 7` bits;
- reconstruye un framebuffer estatico `13*8` sin `std::vector`;
- acumula filas recibidas;
- si `LED_MATRIX_ENABLED=1`, dibuja al recibir las 8 filas validas;
- si `LED_MATRIX_ENABLED=0`, ignora el frame y devuelve `false`.

La matriz se inicializa en `setup()` solo si se compila con LED habilitado:

```text
ledMatrix.begin()
ledMatrix.setGrayscaleBits(3)
ledMatrix.clear()
```

## 7. Evitar bloqueo

Protecciones actuales:

- LED desactivado por defecto en Python y firmware.
- Python no llama Bridge si disabled.
- El transporte salta frames identicos.
- Refresh bajo por defecto: 8 Hz.
- Payload compacto fijo: 8 llamadas por frame, cada una con 3 chunks.
- El MCU no calcula notas ni historial.
- El LED usa `music.recent_notes`, no reejecuta sonificacion.

Riesgos restantes:

- `Bridge.call` LED es sincronico y comparte canal con EEG/MIDI.
- No hay panel UI dedicado con `last_error` LED.
- No hay boton reset/clear LED.
- Python permite width/height via env, pero firmware espera 13x8.
- Si se activa LED durante benchmarks, los resultados ya no son comparables con los benchmarks final-v4.

## 8. Relacion con WebUI

WebUI y LED comparten la misma fuente conceptual:

```text
music.recent_notes
```

Diferencia:

- WebUI piano roll es la visualizacion principal y esta activa.
- LED matrix es una visualizacion fisica opcional y esta desactivada.

El piano roll debe usarse para explicar la generacion de notas en el TFG. La LED puede mencionarse como extension lateral si interesa, pero no como evidencia principal.

## 9. Pruebas minimas si se activa LED

1. `python3 -m py_compile python/led_matrix_visualizer.py python/led_matrix_transport.py python/backend_service.py`.
2. Ejecutar `python/tools/test_led_matrix_visualizer.py` si esta disponible.
3. Probar frame vacio.
4. Probar pitch center fijo.
5. Probar clipping `ignore/saturate`.
6. Probar velocity 0/127.
7. Validar `_pack_row` frente a `led_matrix_row`.
8. Activar Python LED solo si firmware LED tambien esta habilitado.
9. Medir carga Bridge si se usa junto a MIDI.
10. No comparar benchmarks con LED off contra benchmarks con LED on.

## 10. Relacion con futura version esencial/UML

En UML principal:

```text
No incluir LED matrix en el flujo EEG->MIDI.
```

Como modulo lateral opcional:

```text
music.recent_notes
  -> build_led_matrix_frame()
  -> LedMatrixTransport
  -> Bridge.call("led_matrix_row")
  -> led_matrix_row()
```

Como decision de simplificacion:

```text
Mantener LED como lateral o excluirla de la version esencial.
No tocar midi_bytes, scheduler ni sonificacion para simplificar LED.
No activar LED durante benchmarks salvo prueba especifica.
```

## 11. Conclusion

La matriz LED final-v4 es una extension visual opcional de la sonificacion. No genera notas, no calcula EEG, no envia MIDI y no participa en el flujo principal validado.

Para el TFG, el piano roll WebUI es la representacion principal de las notas generadas. La matriz LED puede documentarse como visualizacion lateral, pero debe permanecer separada del nucleo:

```text
EEG -> DSP -> quality gate -> sonificacion -> MIDI fisico
```

