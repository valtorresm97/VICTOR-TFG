# 01. Arquitectura global

## Flujo completo

```text
Electrodos
   ↓
ADS1299-4PAG
   ↓ SPI / DRDY / RDATAC
MCU Arduino UNO Q / STM32U585
   ↓ Bridge.notify("eeg_block_uV")
Python receiver/backend en Linux/App Lab
   ↓
EEGSignalProcessor / DSPCore
   ↓
features espectrales + spectral_quality
   ↓
SonificationFeatures
   ↓
MusicSegment / Bar / NoteEvent
   ↓
MidiScheduler
   ↓
MidiByteTransport → Bridge.call("midi_bytes") → MCU → UART MIDI OUT
   ↓
Web UI piano roll
   ↓
LED matrix scroll
```

## Captura de datos real

El ADS1299 se configura desde `sketch/sketch.ino` a traves de `ADS1299Plus`. La ruta real activa por defecto usa `ADS_DIAGNOSTIC_MODE=5`: CH1 activo con BIAS derivado de CH1P+CH1N, CH2-CH4 apagados/cortocircuitados en configuracion de canal, lead-off sense desactivado. El firmware mantiene `NUM_CHANNELS=4` y sigue transmitiendo cuatro columnas para no romper el contrato Python.

DRDY cae a 250 Hz. La ISR `onDrdyFalling()` solo incrementa `drdy_count`. En `loop()`, si hay `pending > 0`, se lee un solo frame RDATAC de 15 bytes, se valida `status & 0xF00000 == 0xC00000`, se reconstruyen cuatro enteros signed 24-bit, se convierten con `LSB_V=2.235e-8`, se aplican filtros MCU y se guardan muestras en bloques de 8.

## Bridge MCU-Python

El firmware espera handshake con `Bridge.call("linux_started")`. Cuando Python responde `true`, el MCU comienza a llenar `TxBlockRing` y publica bloques con:

```text
Bridge.notify("eeg_block_uV", block_idx, first_sample_idx, sample_count, 8 * (status + ch1..ch4))
```

Python registra `Bridge.provide("eeg_block_uV", self.rx.eeg_block_uV)` en `backend_service.py`. `receiver.py` valida `sample_count`, longitud, continuidad de `block_idx`, continuidad de `sample_idx` y prefijo de `status`.

## Backend y DSP

`BackendService.step()` drena hasta 16 bloques por iteracion hacia `EEGSignalProcessor`. El procesador convierte microvoltios a voltios, escribe un ring buffer de 10 s y calcula features cada `FEATURE_HOP_SAMPLES=64` una vez hay ventana de 4 s.

`DSPCore` calcula PSD multitaper por defecto (`NW=2.5`, `K=4`), bandpowers absolutos/relativos, RMS y picos por banda. `compute_spectral_quality()` evalua artefactos, transporte, RMS, pico-pico, 50 Hz, saturacion, flatline y saltos bruscos.

## Sonificacion y MIDI

`SonificationFeatureAdapter` convierte features DSP + quality gate en controles musicales normalizados: `activity`, `calmness`, `tension`, `rhythmic_density`, `register`, `harmonic_stability`, `velocity_factor`, `note_probability`.

`MusicSegmentBuilder` crea un estado musical vivo cada compas. `BarGenerator` genera acorde y slots ritmicos. `NoteGenerator` crea `NoteEvent`. `MidiScheduler` transforma notas en eventos `note_on`/`note_off`, programa `program_change` y ofrece `panic()`.

`MidiByteTransport` convierte `MidiLiveEvent` a bytes MIDI y llama `Bridge.call("midi_bytes", n,b0,b1,b2)`. Por defecto esta desactivado: `EEG_MIDI_LIVE_ENABLED` debe activarse en entorno y el firmware debe compilar `MIDI_UART_ENABLED=1` con `MIDI_SERIAL` verificado.

## Web UI y piano scroll

La UI no es Streamlit: usa `arduino.app_bricks.web_ui.WebUI` y assets estaticos. `web_server.py` expone `/latest` y websocket `eeg_snapshot`. `assets/app.js` renderiza:

- rendimiento RX,
- features y bandpowers,
- diagnostico CH1,
- warnings,
- controles de sonificacion,
- estado MIDI,
- piano roll live desde `snapshot["music"]["recent_notes"]`.

## LED matrix scroll

La matriz LED usa la misma lista `recent_notes` del piano roll web. `led_matrix_visualizer.py` calcula un frame row-major 13x8 con brillo 0..7. `led_matrix_transport.py` lo envia por `Bridge.call("led_matrix_frame", payload)` solo si `EEG_LED_MATRIX_ENABLED=1`.

En firmware, `led_matrix_frame(std::vector<uint8_t> frame)` valida 104 bytes. Si `LED_MATRIX_ENABLED=0`, responde `false` sin dibujar. Si se compila con `LED_MATRIX_ENABLED=1`, usa `Arduino_LED_Matrix`.

## Flujos offline

Las tools CLI leen capturas en `captures/`, recalculan calidad, PSD y features, y generan reports. `build_validation_docs.py` consolida tablas y figuras bajo `docs/validacion_tfg/`. La ruta offline comparte conceptos con live, pero tiene duplicaciones de calculo de PSD/calidad para funcionar sin App Lab ni Bridge.

## Dependencia App Lab

Corren en App Lab:

- `arduino.app_utils.App`,
- `arduino.app_utils.Bridge`,
- `arduino.app_bricks.web_ui.WebUI`,
- RouterBridge MCU-MPU.

Fuera de App Lab funcionan las tools offline que no importan `arduino.*`, con dependencias `numpy` y `scipy`.
