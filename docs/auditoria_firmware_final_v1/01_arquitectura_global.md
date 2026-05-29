# 01. Arquitectura global - final-v4

## 1. Objetivo del documento

Este documento describe la arquitectura global del sistema EEG-MIDI en lenguaje narrativo y transversal. A diferencia de `docs/auditoria_codigo_detallada/`, que enumera funciones y contratos de forma tabular, este archivo busca explicar el funcionamiento completo del sistema de forma util para:

- redaccion del TFG;
- preparacion de diagramas UML;
- comprension de los bloques principales;
- separacion entre flujo runtime, WebUI, capturas, benchmarks y herramientas offline.

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Flujo principal validado EEG -> MIDI

El flujo principal del sistema es:

```text
Electrodos
   ↓
ADS1299-4PAG
   ↓ SPI / DRDY / RDATAC
MCU Arduino UNO Q / STM32U585
   ↓ filtrado MCU + bloques de 8 muestras
Bridge.notify("eeg_block_uV")
   ↓
Python receiver/backend en Linux/App Lab
   ↓
EEGSignalProcessor / DSPCore
   ↓
features espectrales CH1
   ↓
SignalQuality / QualityGate
   ↓
SonificationFeatureAdapter
   ↓
MusicSegmentBuilder / BarGenerator / NoteGenerator
   ↓
MidiScheduler
   ↓
MidiByteTransport
   ↓ Bridge.call("midi_bytes", n, b0, b1, b2)
MCU firmware midi_bytes()
   ↓
Serial1 / D1 / TX invertido
   ↓
MIDI OUT fisico
```

Este es el flujo que debe aparecer como ruta principal en la futura version esencial/UML.

## 3. Captura de datos real desde ADS1299

El ADS1299 se configura desde `sketch/sketch.ino` mediante el driver local `ADS1299Plus` y el wrapper `ADS1299_SafeSPI`.

La configuracion final de capturas comparables en final-v4 es:

```text
ADS_DIAGNOSTIC_MODE=5
ADS_MODE=bias_ch1_only_loff_off
montage=ear_eeg_ch1_only
```

Lectura correcta del modo:

- CH1 queda como canal EEG principal.
- CH1 usa BIAS derivado de CH1P + CH1N.
- CH2-CH4 se conservan en el contrato de datos, pero no deben interpretarse como EEG activo en las capturas finales.
- El lead-off sense queda desactivado para evitar inyeccion diagnostica durante capturas reales.
- El firmware mantiene `NUM_CHANNELS=4` para no romper el contrato Python, CSV, tools y WebUI.

El flujo firmware de adquisicion es:

```text
DRDY falling a 250 Hz
  -> onDrdyFalling() incrementa drdy_count
  -> loop() detecta pending > 0
  -> ADS1299Plus.readFrameRDATAC()
  -> status 24-bit + CH1..CH4 signed 24-bit
  -> validar (status & 0xF00000) == 0xC00000
  -> raw counts * LSB_V
  -> filtros MCU: HP 0.5 Hz + notch 50 Hz + LP 40 Hz
  -> conversion a microvoltios
  -> TxBlockRing agrupa 8 muestras
```

Los parametros criticos son:

```text
FS_HZ=250
NUM_CHANNELS=4
BLOCK_SAMPLES=8
LSB_V=2.235e-8
STATUS_MASK=0xF00000
STATUS_PREFIX=0xC00000
```

## 4. Contrato Bridge MCU -> Python

El firmware no envia muestras individuales en la ruta final-v4. La ruta principal es por bloques:

```text
Bridge.notify(
  "eeg_block_uV",
  block_idx,
  first_sample_idx,
  sample_count,
  8 * (status, ch1_uV, ch2_uV, ch3_uV, ch4_uV)
)
```

Esto significa:

- 8 muestras por bloque;
- 4 canales por muestra;
- status ADS1299 conservado en cada muestra;
- `sample_idx` reconstruible a partir de `first_sample_idx`;
- frecuencia de bloques esperada cercana a `250 / 8 = 31.25 bloques/s`.

Python registra el handler `EEGReceiver.eeg_block_uV()`. Este callback debe ser ligero: valida longitud, continuidad aproximada, status ADS y encola el bloque. No calcula DSP dentro del callback.

La ruta antigua `eeg_frame_uV()` queda como compatibilidad historica y no forma parte del flujo principal final-v4.

## 5. Backend Python y DSP

`python/main.py` crea el backend y la WebUI, y ejecuta un loop periodico. El nucleo de procesamiento esta en `BackendService.step()`.

El backend realiza:

```text
EEGReceiver.drain_blocks_to_processor()
  -> EEGSignalProcessor.add_block_uV()
  -> conversion uV a V
  -> ring buffer multicanal de 10 s
  -> ventana CH1 de 4 s
  -> compute_live_features() cada 64 muestras
```

El presupuesto temporal del DSP live viene dado por:

```text
FEATURE_HOP_SAMPLES = 64
FS_HZ = 250 Hz
64 / 250 = 0.256 s = 256 ms
```

`DSPCore` calcula:

- PSD multitaper;
- bandpowers absolutos y relativos;
- RMS;
- picos espectrales;
- ratios utiles para sonificacion.

El canal principal para features en la sesion final es CH1. CH2-CH4 se mantienen por contrato, pero no deben usarse como evidencia EEG activa en el montaje final CH1-only.

## 6. Calidad de senal y quality gate

La calidad de senal no la decide la herramienta de captura. La calidad se calcula dentro del backend runtime:

```text
compute_quality_diagnostics()
  -> compute_spectral_quality()
```

En la futura version esencial, este bloque debe representarse de forma compacta como:

```text
SignalQuality / QualityGate
```

Su funcion es evitar que ventanas contaminadas o poco fiables muevan la sonificacion de forma no controlada.

`compute_quality_diagnostics()` aporta indicadores como:

- RMS en microvoltios;
- pico-pico;
- saturacion;
- flatline;
- saltos bruscos;
- presencia relativa de 50 Hz;
- waveform reciente para diagnostico visual.

`compute_spectral_quality()` combina estos indicadores con metricas RX y features espectrales para producir:

```text
score
state
gate_factor
valid_for_sonification
warnings
```

Criterio final-v4:

```text
Quality gate se conserva.
No debe fusionarse dentro de DSPCore.
No debe eliminarse en la version simplificada.
```

## 7. Sonificacion EEG -> musica

La sonificacion convierte features EEG y quality gate en controles musicales normalizados mediante `SonificationFeatureAdapter`.

Los nombres reportables final-v4 son:

```text
alpha_drive
beta_gamma_drive
rms_beta_activity
band_driven_density
spectral_register
alpha_stability
rms_band_velocity
band_note_probability
```

Los nombres antiguos:

```text
activity
calmness
tension
rhythmic_density
register
harmonic_stability
velocity_factor
note_probability
```

se consideran aliases legacy internos y no deben usarse como nombres principales en la memoria ni en el UML.

El EEG no decide directamente la tonalidad ni la nota principal. En final-v4:

```text
root_note
main_note
scale_key
```

son controles musicales de usuario/WebUI. El EEG modula actividad, densidad, registro, estabilidad, dinamica y probabilidad de notas.

## 8. Generacion musical y MIDI live

La ruta live principal de musica es:

```text
MusicSegmentBuilder.build_live_segment()
  -> BarGenerator.generate_live_bar()
  -> NoteGenerator.generate_notes_for_bar()
  -> MidiScheduler.schedule_notes()
  -> MidiScheduler.pop_due_events()
  -> MidiByteTransport.send_events()
```

Las rutas:

```text
BarGenerator.generate_bars()
NoteGenerator.generate_notes_for_segment()
```

se consideran compatibilidad/secundarias. No son necesarias para el funcionamiento live final-v4 y no deben aparecer en el UML principal.

`MidiScheduler` mantiene la agenda temporal de eventos `note_on` y `note_off`. Tambien ofrece `panic()` para limpiar cola y notas activas.

`MidiByteTransport` convierte los eventos a bytes MIDI y usa:

```text
Bridge.call("midi_bytes", n, b0, b1, b2)
```

En firmware, el handler `midi_bytes()` envia los bytes por:

```text
Serial1 / D1 / 31250 baudios / TX invertido
```

La inversion TX mediante `USART_CR2_TXINV` es obligatoria para el circuito MIDI OUT N-audio validado.

## 9. WebUI como observador y control musical ligero

La WebUI no es Streamlit. Usa:

```text
python/web_server.py
arduino.app_bricks.web_ui.WebUI
assets/index.html
assets/app.js
assets/styles.css
```

Su papel arquitectonico es:

```text
observador del estado del sistema
control musical ligero
interfaz de operacion y diagnostico visual
```

No debe calcular DSP, no debe acceder al ADS1299 y no debe modificar firmware.

La WebUI consume snapshots desde:

```text
GET /latest
socket eeg_snapshot
```

y muestra:

- estado RX;
- estado de ventana DSP;
- features EEG;
- bandpowers;
- diagnostico de calidad;
- quality gate;
- controles de sonificacion final-v4;
- estado MIDI;
- controles `root`, `main` y `scale`;
- boton panic MIDI;
- piano roll desde `music.recent_notes`.

Acciones esenciales a conservar:

```text
POST /midi/panic
POST /music/config
```

o sus equivalentes actuales:

```text
POST /music/scale/{key}
POST /music/root/{note}
POST /music/main/{note}
```

La WebUI debe simplificarse con especial cuidado en el futuro. Debe seguir siendo funcional, fluida y comprensible para la redaccion del TFG.

## 10. Capturas reales y herramientas de validacion

Las capturas no forman parte del flujo principal EEG->MIDI, pero son esenciales para validar y documentar el sistema.

La tool:

```text
python/tools/capture_eeg_quality.py
```

no captura directamente y no calcula quality gate. Solo escribe:

```text
state/capture_request.json
```

para solicitar al backend vivo que guarde una captura.

El backend, mediante `CaptureManager`, guarda:

```text
eeg_timeseries.csv
metadata.json
quality_report.*
spectral_validation_report.*
windowed_bandpowers.csv
windowed_sonification_features.csv
```

En la sesion final tambien se conservaron datos musicales:

```text
music_snapshots.jsonl
music_notes.csv
music_capture_summary.json
```

Esto permite defender trazabilidad:

```text
senal EEG -> features -> quality gate -> controles de sonificacion -> notas MIDI
```

## 11. Benchmarks

Los benchmarks final-v4 se separan en dos fuentes:

### MCU / firmware

El firmware imprime metricas `[BENCH] EEG_MIDI` por Monitor/App Lab. No se envia un canal adicional por Bridge para no contaminar el canal que se mide.

El parser offline es:

```text
python/tools/parse_mcu_bench_monitor.py
```

Metricas principales:

- tiempos de filtro;
- tiempos de `Bridge.notify`;
- maximo de loop;
- cola TX;
- drops;
- jitter/lag DRDY;
- bursts de publicacion.

### Python / Linux

Los benchmarks Python se ejecutan sobre captura real, principalmente con:

```text
benchmarks/benchmark_real_capture.py
benchmarks/run_all_benchmarks.py
```

La funcion critica medida para DSP live es:

```text
EEGSignalProcessor.compute_live_features()
```

frente al presupuesto de 256 ms por hop.

## 12. LED matrix como subsistema lateral

La matriz LED no forma parte del flujo principal EEG->MIDI validado.

Su ruta es lateral:

```text
music.recent_notes
  -> build_led_matrix_frame()
  -> LedMatrixTransport
  -> Bridge.call("led_matrix_row")
  -> firmware led_matrix_row()
  -> Arduino_LED_Matrix si enabled
```

En final-v4 esta desactivada por defecto:

```text
EEG_LED_MATRIX_ENABLED=False
LED_MATRIX_ENABLED=0
```

Debe quedar fuera del UML principal. Puede documentarse como visualizacion opcional de las notas, igual que el piano roll, pero no como parte necesaria para generar MIDI.

## 13. Flujos offline

Las tools offline permiten analizar capturas, recalcular features, generar figuras y documentar resultados. Son importantes para la memoria, pero no forman parte del tiempo real.

Ejemplos:

```text
validate_spectral_features.py
analyze_eeg_capture.py
build_final_capture_docs_matplotlib.py
build_capture06_enhanced_figures.py
parse_mcu_bench_monitor.py
```

Estas tools deben conservarse como evidencia y soporte del TFG, pero no deben mezclarse con el UML principal EEG->MIDI.

## 14. Dependencia App Lab

El runtime real en placa depende de:

```text
arduino.app_utils.App
arduino.app_utils.Bridge
arduino.app_bricks.web_ui.WebUI
RouterBridge MCU-MPU
```

Fuera de App Lab funcionan principalmente las tools offline que no importan `arduino.*`, con dependencias como:

```text
numpy
scipy
matplotlib
```

## 15. Arquitectura para futura version esencial UML

La futura version esencial debe mostrar:

```text
ADS1299Plus / ADS1299_SafeSPI
  -> sketch loop
  -> TxBlockRing
  -> EEGReceiver
  -> EEGSignalProcessor
  -> DSPCore
  -> SignalQuality / QualityGate
  -> SonificationFeatureAdapter
  -> MusicSegmentBuilder
  -> BarGenerator
  -> NoteGenerator
  -> MidiScheduler
  -> MidiByteTransport
  -> midi_bytes
  -> Serial1/D1 TXINV
```

Como observador/control:

```text
EEGWebServer
  -> snapshot
  -> /midi/panic
  -> /music/config
  -> piano roll
```

Como laterales:

```text
CaptureManager
tools offline
benchmarks
LED matrix
MIDI test endpoints
```

Como compatibilidad/historico a ocultar:

```text
eeg_frame_uV
compute_online_features
generate_bars
generate_notes_for_segment
legacy aliases de sonificacion
comentarios historicos de MIDI/WebUI/firmware
```

## 16. Conclusion

La arquitectura final-v4 queda organizada en un nucleo claro:

```text
adquisicion EEG real -> transporte por bloques -> DSP -> quality gate -> sonificacion -> MIDI fisico
```

Alrededor del nucleo existen herramientas necesarias para operar, validar y documentar:

```text
WebUI
capturas
benchmarks
tools offline
reportajes y figuras
LED opcional
```

Para redactar el TFG, este documento debe usarse como base narrativa. Para refactorizar o simplificar codigo, deben usarse los documentos de `docs/auditoria_codigo_detallada/`, especialmente los mapas de contratos, funciones criticas y hallazgos de simplificacion.
