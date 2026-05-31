# Propuesta de version esencial EEG-MIDI para UML - final-v4

## 1. Objetivo

La version esencial busca representar de forma didactica el flujo principal EEG->MIDI de final-v4:

```text
ADS1299
-> firmware MCU
-> Bridge eeg_block_uV
-> receiver
-> buffer DSP
-> features
-> quality gate
-> sonificacion
-> scheduler MIDI
-> Bridge midi_bytes
-> UART MIDI OUT
```

Esta propuesta no sustituye a la version final-v4 validada. Es una base documental para una futura rama explicativa o didactica. La version defendible experimentalmente sigue siendo `final-v4` / `firmware-final-v4`, con capturas reales, benchmarks reales en placa y documentacion de validacion TFG.

La rama `refactor/essential-eeg-midi-plan` debe entenderse como rama documental/de planificacion. Si se crea una rama de refactor real, deberia llamarse `refactor/essential-eeg-midi` y partir de una base limpia, con pruebas de contrato antes de tocar runtime.

## 2. Principios de simplificacion

- Conservar el comportamiento principal EEG->MIDI.
- No cambiar contratos Bridge ni nombres de eventos.
- No cambiar `FS_HZ`, `NUM_CH`, `BLOCK_SAMPLES` ni validacion de status.
- No cambiar el MIDI fisico: `midi_bytes`, `Serial1`/D1 y TX invertido siguen siendo criticos.
- No cambiar la WebUI funcional sin validacion de snapshot, endpoints y navegador/App Lab.
- Separar mentalmente runtime, validacion y herramientas offline.
- Reducir complejidad solo despues de tests minimos de contratos.
- Ocultar en UML principal no significa borrar del repositorio.
- No usar benchmarks sinteticos ni resultados de PC como evidencia TFG.
- Mantener `firmware-final-v4` como referencia integrada y trazable.

## 3. Que se mantiene obligatoriamente

### Firmware esencial

| Archivo/bloque | Motivo |
| --- | --- |
| `sketch/sketch.ino` | Entrypoint MCU. Inicializa Bridge, Monitor, ADS1299, handlers `midi_bytes`/`led_matrix_row`, DRDY, filtros, benchmark y loop de adquisicion. |
| `sketch/streaming.h` | Define `BLOCK_SAMPLES=8`, estructura `EegBlockUV`, cola de bloques y emision `Bridge.notify("eeg_block_uV", ...)`. |
| `sketch/filters.h` | Aplica DC blocker/high-pass, notch 50 Hz, low-pass 40 Hz y conversion voltios->microvoltios. |
| `sketch/ADS1299Plus/` | Driver alto nivel ADS1299: comandos, registros, RDATAC, lectura de frames y reconstruccion signed 24-bit. |
| `sketch/ADS1299_SafeSPI/` | Wrapper SPI de bajo nivel: `SPI_MODE1`, `MSBFIRST`, 2 MHz iniciales y control CS. |
| `sketch/sketch.yaml` | Configuracion App Lab/sketch y librerias locales. No convertir librerias locales en dependencias publicas. |

Responsabilidades que deben aparecer en el UML principal:

- inicializacion ADS1299;
- lectura RDATAC condicionada por DRDY;
- validacion basica de `status`;
- conversion counts -> voltios -> microvoltios;
- filtrado MCU si aplica;
- empaquetado de bloques `eeg_block_uV`;
- salida MIDI por `midi_bytes` y UART fisica cuando se represente la ruta completa;
- configuracion App Lab como contenedor de ejecucion, no como logica DSP.

### Python esencial

| Archivo | Papel en runtime | Entra en UML principal | Motivo |
| --- | --- | --- | --- |
| `python/main.py` | Arranque App Lab: crea backend, WebUI y loop periodico. | Si | Punto de entrada runtime. |
| `python/backend_service.py` | Orquestador RX->DSP->quality->sonificacion->MIDI->snapshot. | Si | Centro operativo del pipeline live. |
| `python/receiver.py` | Callback `eeg_block_uV`, parseo, validacion, cola y metricas RX. | Si | Primer consumidor del contrato MCU->Python. |
| `python/eeg_contract.py` | Constantes y parser del contrato EEG. | Si | Fuente Python de `FS_HZ`, `NUM_CH`, `BLOCK_SAMPLES`, `STATUS_PREFIX`. |
| `python/eeg_signal_processor.py` | Buffer circular, conversion uV->V, ventana y features live. | Si | Une recepcion y DSP. |
| `python/dsp_core.py` | DSP puro: PSD, bandpowers, picos, espectrograma. | Si | Calculo cientifico principal. |
| `python/spectral_quality.py` | Quality gate: `clean`, `usable_with_caution`, `artifact_suspected`, `bad`. | Si | Protege la sonificacion frente a ventanas malas. |
| `python/sonification_features.py` | Adaptador features EEG -> controles musicales reportables final-v4. | Si | Traduce features a controles musicales. |
| `python/music_segment.py` | Segmento musical, escala y builder live. | Si | Modelo musical intermedio. |
| `python/music_bar.py` | Generacion de compas y acordes. | Si | Estructura ritmica/armonica. |
| `python/music_note.py` | Generacion de `NoteEvent`. | Si | Produce notas concretas para el scheduler. |
| `python/music_utils.py` | Utilidades de notas y conversion nombre->MIDI. | Secundario | Soporte necesario para configuracion musical. |
| `python/scale_registry.py` | Registro de escalas seleccionables. | Secundario | Soporta root/main/scale WebUI. |
| `python/midi_live.py` | `MidiLiveEvent`, `MidiScheduler`, panic y bytes MIDI. | Si | Scheduler y seguridad MIDI. |
| `python/midi_byte_transport.py` | Envio `Bridge.call("midi_bytes", n, b0, b1, b2)`. | Si | Contrato Python->MCU para MIDI fisico. |
| `python/app_state.py` | Publicacion atomica de snapshot/history en disco. | Secundario | Persistencia runtime y fallback WebUI. |
| `python/runtime_config.py` | Env vars y defaults runtime MIDI/LED/state. | Secundario | Configuracion sin hardcodear todo en backend. |
| `python/web_server.py` | Rutas WebUI, websocket y acciones ligeras. | Si | Observabilidad y controles root/main/scale/panic. |

### WebUI esencial

Mantener:

```text
assets/index.html
assets/app.js
assets/styles.css
```

Controles y vistas minimas:

- `root_note`;
- `main_note`;
- `scale_key`;
- panic MIDI;
- estado de adquisicion;
- estado de features;
- bandpowers relativos;
- controles de sonificacion;
- piano roll minimo desde `music.recent_notes`;
- estado MIDI.

La WebUI es observador/control ligero. No debe contener DSP pesado ni logica de adquisicion.

### Contratos intocables

| Contrato | Valor/forma | Motivo |
| --- | --- | --- |
| `eeg_block_uV` | `Bridge.notify("eeg_block_uV", block_idx, first_sample_idx, sample_count, 8 * (status + ch1_uV + ch2_uV + ch3_uV + ch4_uV))` | Contrato MCU->Python principal. |
| `midi_bytes` | `Bridge.call("midi_bytes", n, b0, b1, b2)` | Contrato Python->MCU para MIDI fisico. |
| Snapshot runtime minimo | `status`, `rx`, `features`, `diagnostics`, `spectral_quality`, `sonification`, `music`, `midi` | Contrato WebUI/disco. |
| `music.recent_notes` | Lista de notas recientes con tiempos absolutos | Fuente del piano roll y LED opcional. |
| `FS_HZ` | `250` | Frecuencia base de adquisicion/DSP. |
| `NUM_CH` | `4` | Contrato ADS1299-4 y payload Python. |
| `BLOCK_SAMPLES` | `8` | 31.25 bloques/s a 250 Hz. |
| `STATUS_PREFIX` | `0xC00000` con mascara `0xF00000` | Validacion basica de frames ADS1299. |

Si uno de estos contratos cambia, la version esencial deja de ser comparable con final-v4.

## 4. Que se puede ocultar, archivar o dejar fuera del UML principal

Elementos candidatos a quedar fuera del UML principal, sin aplicar ningun cambio:

```text
benchmarks/
captures/
docs/validacion_tfg/reportajes*
docs/validacion_tfg/figures*
python/tools/build_*docs*
python/tools/build_*figures*
python/tools/parse_mcu_bench_monitor.py
python/tools/compare_eeg_captures.py
python/tools/validate_spectral_features.py
python/tools/analyze_eeg_capture.py
python/tools/final_capture_session.py
```

No deben borrarse de final-v4. Son evidencia, reproducibilidad o soporte de defensa TFG.

| Opcion | Ventajas | Riesgos | Cuando aplicarla |
| --- | --- | --- | --- |
| A. Dejarlos en el repo, pero fuera del UML principal | Mantiene trazabilidad completa y evita riesgo de rutas rotas. | El repositorio sigue pareciendo grande si no se explica bien. | Opcion recomendada en esta rama documental. |
| B. Moverlos en una futura rama a `archive/validation/` | Clarifica visualmente runtime frente a evidencia. | Rompe enlaces, scripts y referencias si no se hace con cuidado. | Solo despues de mapa de enlaces y revision de docs. |
| C. Mantenerlos como artefactos externos/documentales | Reduce ruido del repo runtime. | Puede perderse trazabilidad local y reproducibilidad. | Solo si existe repositorio/paquete documental estable y enlazado. |

## 5. Que NO debe eliminarse aunque parezca auxiliar

| Archivo | Motivo para conservarlo |
| --- | --- |
| `capture_manager.py` | Runtime lateral de capturas; el backend lo importa y permite trazabilidad experimental. |
| `app_state.py` | Snapshot atomico y fallback de lectura para WebUI/disco. |
| `runtime_config.py` | Centraliza env vars y evita constantes dispersas en backend/LED/MIDI. |
| `spectral_quality.py` | Quality gate esencial para no sonificar ventanas malas con la misma intensidad. |
| `midi_live.py` | Scheduler, eventos, panic y conversion a bytes MIDI. |
| `midi_byte_transport.py` | Unico puente Python->MCU para `midi_bytes`. |
| `scale_registry.py` | Soporta escalas seleccionables de WebUI. |
| `music_utils.py` | Conversion nota musical -> MIDI usada por configuracion root/main. |

## 6. Propuesta de modulos UML

Los paquetes siguientes son logicos. No implican mover archivos.

| Paquete logico | Archivos actuales relacionados | Responsabilidad | UML principal | UML secundario | Fuera de diagramas |
| --- | --- | --- | --- | --- | --- |
| `firmware/acquisition` | `sketch.ino`, `ADS1299Plus/`, `ADS1299_SafeSPI/` | ADS1299, DRDY, SPI, RDATAC, status, raw counts. | Si | No | No |
| `firmware/filtering` | `filters.h` | Filtros MCU y conversion a uV. | Si | No | No |
| `firmware/streaming` | `streaming.h`, `bench.h` | Bloques de 8 muestras y `eeg_block_uV`. | Si | Bench como secundario | No |
| `firmware/midi_uart` | `sketch.ino` handler `midi_bytes` | UART MIDI OUT fisico con TX invertido. | Si | No | No |
| `firmware/diagnostics` | `synthetic.h`, bench, ADS modes, MIDI self-test | Diagnostico y observabilidad. | No | Si | Algunas rutas |
| `python_runtime/bridge_receiver` | `receiver.py`, `eeg_contract.py` | Validar y encolar bloques EEG. | Si | No | No |
| `python_runtime/eeg_buffer` | `eeg_signal_processor.py` | Ring buffer, ventanas y conversion uV->V. | Si | No | No |
| `python_runtime/dsp` | `dsp_core.py` | PSD multitaper, bandpowers y features. | Si | No | No |
| `python_runtime/quality` | `spectral_quality.py` | Quality score/gate. | Si | No | No |
| `python_runtime/sonification` | `sonification_features.py`, `music_segment.py`, `music_bar.py`, `music_note.py`, `music_utils.py`, `scale_registry.py` | Controles musicales, segmentos, compases y notas. | Si | Utilidades como secundario | No |
| `python_runtime/midi` | `midi_live.py`, `midi_byte_transport.py` | Scheduler, panic, bytes MIDI y Bridge `midi_bytes`. | Si | Tests MIDI como secundario | No |
| `python_runtime/web_ui` | `web_server.py`, `assets/` | Snapshot, socket, controles root/main/scale y panic. | Si | Endpoints diagnosticos como secundario | No |
| `python_runtime/state` | `app_state.py`, `runtime_config.py` | Estado persistido y configuracion. | No | Si | No |
| `python_runtime/capture` | `capture_manager.py` | Captura runtime opcional. | No | Si | No |
| `python_runtime/led_matrix` | `led_matrix_visualizer.py`, `led_matrix_transport.py`, handler firmware | Consumidor opcional de `music.recent_notes`. | No | Si | Puede omitirse del UML principal |
| `validation_offline/capture_tools` | `python/tools/capture_eeg_quality.py`, `final_capture_session.py` | Orquestar sesiones y capturas. | No | No | Si |
| `validation_offline/benchmark_tools` | `benchmarks/`, `parse_mcu_bench_monitor.py` | Medir rendimiento real. | No | No | Si |
| `validation_offline/reports` | `docs/validacion_tfg/`, reportajes | Evidencia y narrativas TFG. | No | No | Si |
| `validation_offline/figures` | `docs/validacion_tfg/figures/`, build tools | Figuras reproducibles. | No | No | Si |

## 7. Diagrama de clases propuesto

### UML principal

| Clase / estructura | Archivo | Papel | UML principal/secundario/fuera |
| --- | --- | --- | --- |
| `ADS1299Plus` | `sketch/ADS1299Plus/src/ADS1299Plus.h` | Driver ADS1299 y lectura RDATAC. | Principal |
| `ADS1299_SafeSPI` | `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.h` | SPI seguro y control CS. | Principal |
| `EegBlockUV` | `sketch/streaming.h` | Bloque de 8 muestras en uV. | Principal |
| `TxBlockRing` | `sketch/streaming.h` | Cola y publicacion `eeg_block_uV`. | Principal |
| `BackendService` | `python/backend_service.py` | Orquestador runtime. | Principal |
| `EEGReceiver` | `python/receiver.py` | Callback, validacion y cola EEG. | Principal |
| `EEGSignalProcessor` | `python/eeg_signal_processor.py` | Buffer y features live. | Principal |
| `DSPCore` | `python/dsp_core.py` | PSD y features espectrales. | Principal |
| `SpectralQuality` | `python/spectral_quality.py` | Resultado del quality gate. | Principal |
| `SonificationFeatures` | `python/sonification_features.py` | Controles musicales reportables. | Principal |
| `SonificationFeatureAdapter` | `python/sonification_features.py` | Suavizado/quality gate de controles. | Principal |
| `MusicSegmentBuilder` | `python/music_segment.py` | Construye segmento live desde controles. | Principal |
| `MusicSegment` | `python/music_segment.py` | Estado musical de un segmento/compas. | Principal |
| `BarGenerator` | `python/music_bar.py` | Genera compases y acordes. | Principal |
| `Bar` | `python/music_bar.py` | Compas generado. | Principal |
| `NoteGenerator` | `python/music_note.py` | Genera notas para compas. | Principal |
| `NoteEvent` | `python/music_note.py` | Nota musical abstracta. | Principal |
| `MidiScheduler` | `python/midi_live.py` | Agenda eventos MIDI y panic. | Principal |
| `MidiLiveEvent` | `python/midi_live.py` | Evento MIDI temporizado. | Principal |
| `MidiByteTransport` | `python/midi_byte_transport.py` | Envia bytes por `midi_bytes`. | Principal |
| `EEGWebServer` | `python/web_server.py` | WebUI, socket y endpoints. | Principal |

### UML secundario o fuera

| Clase / estructura | Archivo | Papel | UML principal/secundario/fuera |
| --- | --- | --- | --- |
| `CaptureManager` | `python/capture_manager.py` | Capturas CSV/metadata desde runtime. | Secundario |
| `LedMatrixConfig` | `python/led_matrix_visualizer.py` | Configuracion LED matrix. | Secundario |
| `LedMatrixTransport` | `python/led_matrix_transport.py` | Envio filas LED por Bridge. | Secundario |
| `BenchStats` | `sketch/bench.h` | Metricas MCU. | Secundario |
| Tools CLI | `python/tools/*.py` | Analisis, capturas, figuras y docs. | Fuera del UML principal |
| Benchmark scripts | `benchmarks/*.py` | Benchmarks Python/Linux y capturas reales. | Fuera del UML principal |

## 8. Diagramas de secuencia propuestos

| Diagrama | Actores | Mensajes | Archivos implicados | Omisiones para simplificar |
| --- | --- | --- | --- | --- |
| 1. Arranque del sistema | App Lab, `main.py`, `BackendService`, `Bridge`, `EEGWebServer`, firmware | Crear backend, registrar `linux_started`/`eeg_block_uV`, arrancar WebUI, firmware hace handshake. | `python/main.py`, `backend_service.py`, `web_server.py`, `sketch.ino` | Detalles de logging, disco y test MIDI. |
| 2. Adquisicion EEG | ADS1299, MCU, `TxBlockRing`, Bridge, `EEGReceiver`, `EEGSignalProcessor` | DRDY, `readFrameRDATAC`, filtros, bloque, `eeg_block_uV`, parseo, buffer. | `sketch.ino`, `streaming.h`, `receiver.py`, `eeg_contract.py`, `eeg_signal_processor.py` | Bench detallado y modo sintetico. |
| 3. DSP/features | `BackendService`, `EEGSignalProcessor`, `DSPCore`, `spectral_quality`, `SonificationFeatureAdapter` | Ventana lista, multitaper, bandpowers, diagnostics, quality, controles. | `backend_service.py`, `eeg_signal_processor.py`, `dsp_core.py`, `spectral_quality.py`, `sonification_features.py` | Espectrograma offline y funciones legacy. |
| 4. Sonificacion | `BackendService`, `MusicSegmentBuilder`, `BarGenerator`, `NoteGenerator`, `MidiScheduler` | Crear segmento, compas, notas, program_change, schedule. | `backend_service.py`, `music_segment.py`, `music_bar.py`, `music_note.py`, `midi_live.py` | Generadores legacy y test loop. |
| 5. MIDI fisico | `MidiScheduler`, `MidiByteTransport`, Bridge, firmware `midi_bytes`, UART, DIN/sinte | Pop due events, `event_to_midi_bytes`, `Bridge.call("midi_bytes")`, UART TX invertido. | `midi_live.py`, `midi_byte_transport.py`, `sketch.ino` | Detalles electricos del circuito si hay diagrama hardware separado. |
| 6. Captura opcional | Web/tool, `CaptureManager`, `EEGReceiver`, disco, tools offline | Solicitud de captura, `add_block`, CSV/metadata, analisis offline. | `capture_manager.py`, `python/tools/*`, `benchmarks/`, `docs/validacion_tfg/` | Fuera del UML principal EEG->MIDI. |

## 9. Diagrama de estados propuesto

| Estado UML | Senal/campo real | Significado | Transicion principal |
| --- | --- | --- | --- |
| `boot` | `main.py` crea backend/WebUI | Arranque App Lab Python. | Backend creado y WebUI iniciado. |
| `waiting_linux` | `Bridge.call("linux_started")` / handler `linux_started` | Firmware espera o comprueba Linux. | Handshake OK. |
| `streaming` | `rx.rx_blocks_total > 0` | Llegan bloques `eeg_block_uV`. | Primer bloque recibido. |
| `filling_window` | `status.state=waiting_for_window`, `window_ready=false` | Aun no hay 4 s de ventana DSP. | Buffer alcanza ventana. |
| `features_ready` | `status.state=features_ready`, `window_ready=true` | Hay features live calculadas. | `compute_live_features` OK. |
| `quality_clean` | `spectral_quality.state=clean` | Ventana util para sonificacion plena. | Quality score alto. |
| `quality_caution` | `spectral_quality.state=usable_with_caution` | Sonificacion con cautela/atenuacion. | Penalizaciones moderadas. |
| `artifact_suspected` | `spectral_quality.state=artifact_suspected` | Ventana probablemente contaminada. | Artefacto, RMS o diagnosticos RX. |
| `bad_signal` | `spectral_quality.state=bad` | No conviene generar nueva musica. | Quality gate invalida controles. |
| `music_active` | `music.recent_notes` no vacio, scheduler con eventos | Hay notas generadas y/o en cola. | Sonification valid -> notes scheduled. |
| `midi_panic` | `POST /midi/panic`, `MidiScheduler.panic()` | Seguridad MIDI: All Sound Off / All Notes Off. | Usuario pulsa panic o backend llama panic. |
| `capture_active` | `capture.state=recording` | Captura CSV/metadata activa. | Solicitud capture start. |
| `error` | `errors.*`, `capture.state=error` o contadores de fallo | Fallo parcial de captura, musica o MIDI. | Excepcion o fallo de escritura/envio. |

Campos que conectan estados reales:

- `status.state`;
- `status.window_ready`;
- `spectral_quality.state`;
- `capture.state`;
- `midi.scheduler`, `midi.transport`;
- snapshot runtime publicado por `BackendService._build_snapshot`;
- `music.recent_notes` para piano roll y LED opcional.

## 10. Plan de refactor futuro

| Fase | Objetivo | Archivos tocados | Riesgos | Prueba minima | Rollback |
| --- | --- | --- | --- | --- | --- |
| A. Solo documentacion y diagramas | Congelar comprension final-v4 y UML esencial. | `docs/05_simplificacion_uml/`, opcional `docs/README.md` | Confundir plan con version validada. | `git diff --stat` solo docs permitidos. | Revertir commit documental. |
| B. Tests de contrato minimos | Crear red de seguridad antes de refactor. | Tests para `eeg_contract.py`, `midi_live.py`, snapshot, quality. | Tests estrechos que no cubran placa. | Parser `eeg_block_uV`, panic, bytes MIDI, schema snapshot. | Revertir tests si bloquean sin aportar. |
| C. Separacion logica sin mover archivos | Extraer funciones puras o agrupar responsabilidades internamente. | `backend_service.py`, quizas helpers nuevos. | Romper imports App Lab o snapshot. | `py_compile`, tests contrato, smoke `/latest`. | Revertir commit pequeno. |
| D. WebUI esencial opcional | Hacer UI mas explicable conservando controles minimos. | `assets/`, `web_server.py` | Romper root/main/scale, panic o piano roll. | Navegador/App Lab, endpoints y snapshot fixture. | Revertir assets. |
| E. Mover tools offline si se confirma | Separar validacion de runtime visualmente. | `python/tools/`, `benchmarks/`, docs links | Romper rutas de reportes/figuras. | `rg` de enlaces, ejecutar tool representativa. | Revertir movimiento. |
| F. Limpieza final de imports | Quitar rutas legacy realmente no usadas. | Runtime Python seleccionado | Eliminar alias aun usado. | `rg` referencias, tests, App Lab smoke. | Revertir commit. |
| G. Validacion en placa | Confirmar que EEG->MIDI real sigue vivo. | Solo si hubo cambios funcionales | Timing, Bridge, MIDI fisico, ADS1299. | 250 Hz, 31.25 blk/s, drops 0, panic, nota MIDI real. | Volver a rama final-v4 o commit previo. |

## 11. Riesgos principales

- Romper App Lab por imports.
- Romper Bridge.
- Romper snapshot UI.
- Romper MIDI fisico.
- Perder trazabilidad de capturas.
- Confundir version esencial con version validada.
- Eliminar herramientas necesarias para defensa TFG.
- Cambiar timing sin medir.
- Cambiar firmware sin placa.
- Romper rutas de assets.
- Romper rutas de documentacion.
- Eliminar aliases todavia usados.
- Quitar `capture_manager.py` aunque el backend lo importe.
- Tocar WebUI sin entender resolucion temporal.
- Simplificar sonificacion y perder panic MIDI.

## 12. Recomendacion final

No aplicar refactor todavia.

Primero conviene congelar final-v4 documentada. Despues se puede crear la rama `refactor/essential-eeg-midi`. La primera implementacion debe ocultar o separar documentacion/tools, no tocar adquisicion ni MIDI. La primera rama esencial debe demostrar el mismo flujo EEG->MIDI antes de eliminar cualquier modulo.

La version esencial UML debe explicar mejor el sistema; no debe reducir evidencia, cambiar contratos ni sustituir la version experimentalmente validada.
