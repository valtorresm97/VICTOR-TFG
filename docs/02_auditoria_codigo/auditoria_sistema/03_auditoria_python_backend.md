# 03. Auditoria Python backend - final-v4

## 1. Objetivo

Este documento describe el backend Python de forma narrativa y transversal. La auditoria funcion por funcion mas exhaustiva esta en:

```text
docs/02_auditoria_codigo/funcion_por_funcion/03_python_backend_funcion_por_funcion.md
```

Aqui se explica como Python recibe los bloques EEG, mantiene el buffer, calcula features, aplica quality gate, genera sonificacion, envia MIDI, publica snapshot, sirve la WebUI y gestiona capturas.

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Papel del backend en el sistema

El backend Python es el orquestador del lado Linux/App Lab. Su responsabilidad es conectar el flujo que llega desde el firmware con el procesamiento EEG, la sonificacion, el MIDI fisico, la WebUI y las capturas.

Flujo conceptual:

```text
Bridge.notify("eeg_block_uV") desde MCU
  -> EEGReceiver.eeg_block_uV()
  -> cola de bloques
  -> BackendService.step()
  -> EEGSignalProcessor.add_block_uV()
  -> compute_live_features()
  -> compute_quality_diagnostics()
  -> compute_spectral_quality()
  -> SonificationFeatureAdapter.update()
  -> MusicSegmentBuilder / BarGenerator / NoteGenerator
  -> MidiScheduler
  -> MidiByteTransport
  -> Bridge.call("midi_bytes")
  -> firmware MIDI OUT
```

Ademas, el backend publica un snapshot para WebUI/disco y, si se solicita, guarda capturas mediante `CaptureManager`.

## 3. Estructura principal

| Archivo | Responsabilidad | Estado final-v4 | Lectura para UML |
| --- | --- | --- | --- |
| `main.py` | Crea backend y WebUI, ejecuta `App.run(user_loop=loop)`. | Activo | Entrada App Lab. |
| `backend_service.py` | Orquestador de recepcion, buffer, DSP, quality, sonificacion, MIDI, LED lateral, capturas y snapshots. | Activo critico | Nucleo Python, pero demasiado ancho. |
| `receiver.py` | Handlers Bridge y cola de bloques EEG. | Activo critico | Entrada MCU->Python. |
| `eeg_contract.py` | Constantes y parser del payload `eeg_block_uV`. | Activo critico | Contrato firmware/Python. |
| `eeg_signal_processor.py` | Ring buffer y acceso a DSP. | Activo critico | Buffer EEG + features. |
| `dsp_core.py` | Analisis espectral puro de canal. | Activo critico | DSP/PSD/bandas. |
| `spectral_quality.py` | Quality gate live. | Activo critico | Seguridad musical ante artefactos. |
| `sonification_features.py` | Features EEG -> controles musicales final-v4. | Activo critico | Puente EEG-musica. |
| `midi_live.py` | Scheduler y eventos MIDI. | Activo critico | Agenda temporal y panic. |
| `midi_byte_transport.py` | Envio `Bridge.call("midi_bytes")`. | Activo critico | Salida hacia firmware MIDI. |
| `app_state.py` | Snapshot JSON atomico y estado runtime. | Activo | Estado disco/fallback. |
| `capture_manager.py` | Capturas controladas por JSON desde CLI. | Activo lateral | Validacion, no nucleo MIDI. |
| `web_server.py` | WebUI brick, rutas, socket y controles. | Activo | Observador/control ligero. |
| `led_matrix_*` | Visualizacion LED opcional. | Desactivado por defecto | Lateral, no UML principal. |

No existe `python/dashboard.py` en esta rama. La UI esta implementada como WebUI HTML/CSS/JS en `assets/`.

## 4. Entrada `eeg_block_uV`

`BackendService.__init__()` registra en Bridge:

```text
Bridge.provide("linux_started", self.rx.linux_started)
Bridge.provide("eeg_block_uV", self.rx.eeg_block_uV)
```

El firmware no envia muestras sueltas en la ruta principal final-v4. Envia bloques:

```text
block_idx, first_sample_idx, sample_count,
sample_count * (status, ch1_uV, ch2_uV, ch3_uV, ch4_uV)
```

`receiver.eeg_block_uV()` valida:

- `sample_count > 0` y `<= 8`;
- indices no negativos;
- longitud exacta del payload;
- continuidad de `block_idx`;
- continuidad de `sample_idx`;
- prefijo status `0xC00000`;
- bloques malformados y status invalidos.

Despues encola un `BlockItem` en una `deque(maxlen=512)`. Si la cola se llena, descarta el bloque mas antiguo y contabiliza drops en bloques y frames.

La funcion `eeg_frame_uV()` queda como compatibilidad historica de muestra individual. No es la ruta principal final-v4.

## 5. Drenado hacia DSP y captura lateral

En cada `BackendService.step()` se llama:

```python
self.rx.drain_blocks_to_processor(
    self.proc,
    max_blocks=16,
    block_sink=self.capture_manager.add_block,
)
```

Cada bloque drenado se pasa a dos destinos:

1. `EEGSignalProcessor.add_block_uV(samples)`, que convierte microvoltios a voltios y escribe en el ring buffer.
2. `CaptureManager.add_block(...)`, si hay una captura activa.

Esto significa que capturar no cambia el quality gate ni el DSP. La captura es una rama lateral de escritura a disco sobre los bloques que ya pasan por el backend.

`capture_eeg_quality.py` tampoco captura directamente. Solo escribe `state/capture_request.json` para pedir al backend vivo que guarde una captura.

## 6. Calculo de features y presupuesto temporal

Constantes activas:

| Constante | Valor | Comentario |
| --- | ---: | --- |
| `FS_HZ` | 250 | Debe coincidir con firmware. |
| `NUM_CH` | 4 | Contrato ADS1299-4. |
| `FEATURE_WINDOW_SEC` | 4.0 | 1000 muestras. |
| `FEATURE_HOP_SAMPLES` | 64 | 256 ms. |
| `SNAPSHOT_PUBLISH_PERIOD_SEC` | 0.2 | WebUI a ~5 Hz. |
| `DISK_PUBLISH_PERIOD_SEC` | 1.0 | Snapshot en disco. |

Cuando hay ventana lista, el backend calcula:

```text
compute_live_features(channel_idx=0, psd_method="multitaper")
```

Luego ejecuta:

```text
compute_quality_diagnostics()
_build_quality_rx_delta_metrics()
compute_spectral_quality()
SonificationFeatureAdapter.update()
```

En final-v4, la ruta live principal es `compute_live_features()`. La ruta `compute_online_features()` se considera secundaria y queda fuera del UML principal.

El presupuesto temporal de features es:

```text
64 / 250 = 0.256 s = 256 ms
```

Los benchmarks finales muestran que el coste de `compute_live_features()` queda muy por debajo de ese presupuesto.

## 7. Quality gate

El quality gate vive en runtime y protege la sonificacion:

```text
compute_quality_diagnostics()
  -> compute_spectral_quality()
```

Debe conservarse en la version esencial como bloque compacto:

```text
SignalQuality / QualityGate
```

`compute_quality_diagnostics()` mide:

- RMS;
- pico-pico;
- saturacion;
- flatline;
- saltos;
- componente relativa de 50 Hz;
- waveform reciente.

`compute_spectral_quality()` produce:

```text
score
state
gate_factor
valid_for_sonification
warnings
```

Este bloque no debe fusionarse dentro de `DSPCore`, porque `DSPCore` calcula features y el quality gate decide si esas features son fiables para mover la musica.

## 8. Sonificacion y MIDI desde backend

El backend mantiene estos objetos principales:

```text
SonificationFeatureAdapter
MusicSegmentBuilder
BarGenerator
NoteGenerator
MidiScheduler
MidiByteTransport
```

Ruta live:

```text
SonificationFeatureAdapter.update()
  -> MusicSegmentBuilder.build_live_segment()
  -> BarGenerator.generate_live_bar()
  -> NoteGenerator.generate_notes_for_bar()
  -> MidiScheduler.schedule_notes()
  -> MidiScheduler.pop_due_events()
  -> MidiByteTransport.send_events()
```

`MidiByteTransport` envia:

```text
Bridge.call("midi_bytes", n, b0, b1, b2)
```

hacia el firmware, que finalmente escribe por `Serial1`/D1 con TX invertido.

Configuracion final-v4:

```text
EEG_MIDI_LIVE_ENABLED=True por defecto
MIDI_UART_ENABLED=1 en firmware
midi_bytes existe y esta validado
```

`send_panic()` es esencial. Limpia scheduler y envia mensajes de panic si el transporte esta activo. Tambien existe boton WebUI:

```text
POST /midi/panic
```

## 9. WebUI y snapshot

`_build_snapshot()` publica un diccionario con claves principales:

```text
config
status
rx
features
diagnostics
spectral_quality
capture
sonification
music
midi
led_matrix
performance
errors
```

La WebUI depende directamente de esas claves. Por eso los nombres del snapshot son contrato.

La WebUI permite observar:

- rates RX;
- estado de ventana;
- canales activos/inactivos;
- features y bandpowers;
- diagnostico de calidad;
- quality gate;
- controles de sonificacion;
- estado MIDI;
- piano roll;
- estado de captura.

Y permite accionar:

```text
POST /midi/panic
POST /music/config
POST /music/scale/{key}
POST /music/root/{note}
POST /music/main/{note}
```

En final-v4 ya existen controles WebUI para `root`, `main` y `scale`. Cualquier comentario antiguo que diga lo contrario debe considerarse historico.

La WebUI debe tratarse con cuidado en la futura simplificacion: debe seguir siendo fluida, funcional y comprensible para el TFG.

## 10. Captura y datos persistidos

`capture_manager.py` permite capturas controladas por JSON. La tool externa `capture_eeg_quality.py` solicita la captura; el backend vivo la ejecuta.

Campos CSV principales:

```text
t_capture_sec
timestamp_unix
block_idx
sample_idx
sample_in_block
status
ch1_uV ... ch4_uV
```

`metadata.json` conserva informacion de configuracion, entorno, git, duracion y resumen RX.

En la sesion final se anadieron datos musicales mediante `final_capture_session.py`:

```text
music_snapshots.jsonl
music_notes.csv
music_capture_summary.json
```

Esto permite documentar no solo la senal EEG, sino tambien la salida musical producida por el sistema.

## 11. LED desde backend

LED matrix se gestiona como consumidor lateral de `music.recent_notes`.

```text
_recent_notes
  -> build_led_matrix_frame()
  -> LedMatrixTransport.send_frame()
  -> Bridge.call("led_matrix_row")
```

En final-v4 esta desactivado por defecto:

```text
EEG_LED_MATRIX_ENABLED=False
LED_MATRIX_ENABLED=0
```

No debe aparecer en el UML principal EEG->MIDI salvo como modulo lateral opcional.

## 12. Errores posibles y mitigacion

| Subsistema | Error | Mitigacion actual | Riesgo restante |
| --- | --- | --- | --- |
| Receiver | Bloque malformado | Contador y drop | UI solo muestra resumen; no detiene adquisicion. |
| Receiver | Status invalido | Contador y penalizacion en quality gate | No detiene por si solo la adquisicion. |
| Buffer | Shape incorrecta | Warning y drop | Sin alarma UI directa detallada. |
| DSP | Excepcion en features | Log exception y conserva ultimas features | Puede ocultar fallo si no se revisa log. |
| Quality | Ventana mala | `gate_factor` bajo o 0 | Umbrales empiricos. |
| MIDI | Bridge falla | `failed_events_total`; panic disponible | Debe vigilarse en WebUI. |
| LED | Bridge/frame falla | `failed_frames_total`, `last_error` | Subsistema lateral; no debe afectar MIDI. |
| Captura | App no corre | CLI timeout | Usuario debe arrancar App Lab. |
| WebUI | Snapshot cambia claves | Render puede quedar parcial | Necesario schema/test visual. |

## 13. Deudas y simplificacion futura

Hallazgos principales:

- `backend_service.py` concentra demasiadas responsabilidades.
- El snapshot es un contrato grande sin test automatico formal.
- WebUI y backend deben simplificarse con mucho cuidado.
- `compute_online_features()` queda fuera del flujo principal.
- `eeg_frame_uV()` queda como compatibilidad historica.
- LED matrix es lateral.
- MIDI test loop es diagnostico, no ruta EEG->MIDI.
- Los aliases legacy de sonificacion deben migrarse/ocultarse de forma gradual.

No conviene refactorizar antes de crear tests de contrato para:

```text
eeg_contract.py
snapshot minimo
midi_live.py
midi_byte_transport.py
spectral_quality.py
music config root/main/scale
```

## 14. Relacion con futura version esencial/UML

En el UML principal del backend deben aparecer:

```text
EEGReceiver
EEGSignalProcessor
DSPCore
SignalQuality / QualityGate
SonificationFeatureAdapter
MusicSegmentBuilder
BarGenerator
NoteGenerator
MidiScheduler
MidiByteTransport
EEGWebServer como observador/control ligero
```

Como laterales:

```text
CaptureManager
LedMatrixTransport
MIDI test loop
app_state persistence
runtime_config helpers
tools offline
```

Como compatibilidad/historico a ocultar:

```text
eeg_frame_uV
compute_online_features
aliases legacy de sonificacion
```

## 15. Conclusion

El backend Python final-v4 es la capa que convierte los bloques EEG procedentes del firmware en features espectrales, aplica un quality gate, genera controles de sonificacion, programa eventos MIDI y los envia al firmware para salida MIDI fisica.

Tambien sostiene la WebUI y las capturas, pero estas deben entenderse como observacion, control y validacion alrededor del nucleo EEG->MIDI, no como sustitutos del flujo principal.

