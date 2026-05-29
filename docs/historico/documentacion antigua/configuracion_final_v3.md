# Configuracion final v3

Documento resumen para el estado final-v3 del sistema EEG-MIDI. Consolida la arquitectura real observada en codigo y las auditorias vigentes. No cambia firmware ni runtime.

Ramas relevantes:

- `firmware-final-v3`: rama congelada de referencia final.
- `codex/direct-band-sonification`: rama experimental con sonificacion directa por bandas y controles musicales WebUI.
- `docs/final-v3-audit-update`: rama documental de esta actualizacion.

## Arquitectura general

```text
Electrodos EEG
  -> ADS1299-4PAG
  -> SPI RDATAC / DRDY
  -> STM32U585 en Arduino UNO Q
  -> filtros MCU y conversion a uV
  -> Bridge.notify("eeg_block_uV")
  -> Python EEGReceiver
  -> EEGSignalProcessor / DSPCore
  -> spectral_quality_score
  -> SonificationFeatureAdapter
  -> MusicSegment / Bar / NoteEvent
  -> MidiScheduler / MidiByteTransport
  -> Bridge.call("midi_bytes")
  -> Serial1 / D1 / TX invertido
  -> MIDI OUT DIN5
  -> sintetizador fisico
```

La WebUI se alimenta del snapshot Python y muestra adquisicion, DSP, calidad, sonificacion, MIDI, controles musicales y piano roll.

## Firmware

Archivo principal: `sketch/sketch.ino`.

Configuracion critica:

- ADS1299-4PAG esperado, `ADS1299Plus::NUM_CHANNELS == 4`.
- `PIN_DRDY = 7`, `PIN_START = D9`, `PIN_RESET = D8`, `PIN_PWDN = D5`, `PIN_CS = D10`.
- SPI ADS1299: `SPI_MODE1`, `MSBFIRST`, 2 MHz.
- Frecuencia objetivo: 250 Hz.
- `ADS_DIAGNOSTIC_MODE=5` por defecto: CH1 activo con BIAS derivado de CH1P+CH1N, CH2-CH4 apagados/cortocircuitados, lead-off off.
- Filtros MCU: high-pass/DC blocker 0.5 Hz, notch 50 Hz, low-pass 40 Hz.
- `EEG_STREAMING_NOTIFY_ENABLED=1`.
- `BENCH_REPORT_ENABLED=1`, separado del streaming EEG.

La ISR de DRDY solo incrementa `drdy_count`. Si `pending > 1`, el firmware lee un frame actual y contabiliza lag; `drdy_count` no se trata como FIFO de muestras.

## Streaming

Contrato MCU -> Python:

- Evento: `Bridge.notify("eeg_block_uV", ...)`.
- Bloques de `BLOCK_SAMPLES=8`.
- Cabecera: `block_idx`, `first_sample_idx`, `sample_count`.
- Por muestra: `status`, `ch1_uV`, `ch2_uV`, `ch3_uV`, `ch4_uV`.
- Status valido ADS1299: `(status & 0xF00000) == 0xC00000`.

Python centraliza el parser y constantes en `python/eeg_contract.py`. Cualquier cambio de `streaming.h` debe actualizar `receiver.py`/`eeg_contract.py` en la misma iteracion.

## Python backend

`python/backend_service.py` orquesta:

- registro de `linux_started` y `eeg_block_uV`;
- drenaje de bloques hacia `EEGSignalProcessor`;
- capturas CSV incrementales mediante `CaptureManager`;
- calculo de features cada `FEATURE_HOP_SAMPLES=64` con ventana de 4 s;
- quality gate;
- generacion musical;
- scheduler/transporte MIDI;
- snapshot WebUI/disco.

El snapshot incluye `config`, `status`, `rx`, `features`, `diagnostics`, `spectral_quality`, `capture`, `sonification`, `music`, `midi`, `led_matrix`, `performance` y `errors`.

## DSP

`DSPCore` es la fuente principal para PSD multitaper live/offline. El pipeline usa:

- buffer en voltios desde muestras uV;
- PSD multitaper;
- bandpowers absolutos y relativos;
- picos por delta/theta/alpha/beta/gamma;
- RMS y diagnosticos de calidad de ventana.

Las tools offline de validacion reutilizan `DSPCore` y `compute_spectral_quality()` para mantener comparables los informes y el backend live.

## Spectral quality

`python/spectral_quality.py` calcula `spectral_quality_score`, `state`, `gate_factor`, warnings y penalizaciones.

Estados principales:

- `clean`: usa features normalmente.
- `usable_with_caution`: atenuacion leve.
- `artifact_suspected`: atenuacion fuerte.
- `bad`: no generar nueva sonificacion.

No modifica bandpowers ni filtros. Se aplica despues del DSP en `SonificationFeatureAdapter` para atenuar actividad, densidad, velocity, probabilidad de nota y estabilidad armonica cuando la ventana no es fiable.

## Sonificacion

Mapeo final-v3:

- `activity`: RMS normalizado + beta relativa.
- `calmness`: alpha y estabilidad espectral.
- `tension`: beta/gamma, actividad y baja estabilidad.
- `rhythmic_density`: densidad de notas por compas.
- `register`: centro melodico alrededor de `main_note`.
- `harmonic_stability`: tendencia a reposo armonico.
- `velocity_factor`: dinamica MIDI.
- `note_probability`: probabilidad de activar slots ritmicos.

Ajustes musicales recientes:

- `MUSIC_BAR_SEC=2.0`.
- `MUSIC_CHORD_MIN_PERIOD_SEC=12.0` para acordes menos frecuentes.
- `MUSIC_CHORD_CHANGE_THRESHOLD=0.45` para evitar cambios por pequenas variaciones.
- `MUSIC_LOW_NOTES_PER_BAR=2`, `MUSIC_MEDIUM_NOTES_PER_BAR=6`, `MUSIC_HIGH_NOTES_PER_BAR=11`.
- `MUSIC_PITCH_VARIETY=0.65`, `MUSIC_SCALE_RADIUS_SEMITONES=28`.
- Saltos melodicos maximos de 7 a 16 semitonos segun tension.

Escalas disponibles: major, natural minor, minor blues, Spanish Phrygian, Arabic Double Harmonic, harmonic minor, phrygian dominant, minor pentatonic y major pentatonic.

## MIDI fisico

Validado con Behringer PRO VS MINI.

Ruta:

```text
Python MidiByteTransport
  -> Bridge.call("midi_bytes", n, b0, b1, b2)
  -> firmware midi_bytes()
  -> Serial1 / D1 / USART1_TX
  -> TX invertido
  -> circuito N-audio MIDI OUT
  -> DIN5 / sintetizador
```

Politica final:

- `MIDI_UART_ENABLED=1` por defecto.
- `MIDI_SERIAL=Serial1`.
- `USART_CR2_TXINV` obligatorio; sin inversion el circuito validado no reproduce correctamente.
- `MIDI_MCU_SELF_TEST_ENABLED=0` por defecto.
- `EEG_MIDI_LIVE_ENABLED=True` por defecto en Python.
- El loop diagnostico Python no autoinicia por defecto.

## WebUI

`python/web_server.py` usa `arduino.app_bricks.web_ui.WebUI`.

Rutas principales:

- `GET /status`.
- `GET /latest`.
- websocket `eeg_snapshot`.
- `POST /midi/panic`.
- endpoints diagnosticos `/midi/test-*`.
- `POST /music/config`.
- `POST /music/scale/{key}`.
- `POST /music/root/{note}`.
- `POST /music/main/{note}`.

Controles disponibles:

- root note C3..B5;
- main note C3..B5;
- escala;
- panic MIDI;
- piano roll live;
- metricas RX/DSP/MIDI;
- estado de canales y `ADS_DIAGNOSTIC_MODE`.

No hay controles WebUI para habilitar/deshabilitar MIDI/LED, iniciar capturas, cambiar filtros MCU ni cambiar parametros internos de densidad.

## Riesgos y limitaciones actuales

- `ADS_DIAGNOSTIC_MODE=5` transmite cuatro columnas, pero solo CH1 representa EEG activo.
- No existe modo raw/unfiltered runtime para comparar contra filtros MCU.
- MIDI, LED y EEG comparten Bridge; medir latencia/drops si aumenta la carga MIDI/LED.
- Falta panic autonomo en firmware si Python/App Lab se cae.
- Falta test automatico de snapshot WebUI y endpoints `/music/*`.
- Falta medicion formal EEG -> feature -> nota -> MIDI OUT.
- `spectral_quality_score` es empirico; debe recalibrarse con mas capturas y usuarios.
- LED matrix sigue deshabilitado por defecto en firmware.

## Validacion recomendada en UNO Q

1. Confirmar Monitor: `ADS1299 ID=0x3C`, `START + RDATAC activo`, status prefijo `0xC00000`.
2. Confirmar benchmark: `gen/s ~= 250`, `blk_sent/s ~= 31.25`, drops de cola 0.
3. Confirmar Python/WebUI: `rx_frame_rate_hz ~= 250`, `rx_block_rate_hz ~= 31.25`, `malformed=0`, `invalid_status=0`.
4. Confirmar WebUI: `ADS_DIAGNOSTIC_MODE=5`, CH1 activo y CH2-CH4 apagados.
5. Confirmar MIDI: panic funciona y una nota/secuencia diagnostica suena por D1/TX invertido.
6. Confirmar sonificacion: con calidad baja no se generan cambios musicales fuertes; al recuperarse la calidad vuelve la generacion.



