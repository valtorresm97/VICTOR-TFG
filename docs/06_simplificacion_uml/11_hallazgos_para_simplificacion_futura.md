# 11. Hallazgos para simplificacion futura - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Actualizacion final-v4: revisada desde la rama documental `refactor/essential-eeg-midi-plan` contra el estado integrado `firmware-final-v4`.

Este documento no aplica refactor. Sirve como puente hacia la futura rama de simplificacion/UML. Su objetivo es ordenar que se debe conservar, que puede ocultarse en diagramas, que puede limpiarse y que no debe tocarse sin placa.

## 1. Principio general

La version esencial no debe ser una version incompleta ni una version que borre evidencias. Debe ser una version mas explicable del sistema validado:

```text
ADS1299 -> firmware -> Bridge -> Python backend -> DSP -> quality gate -> sonificacion -> MIDI fisico
```

Reglas:

1. No borrar benchmarks, capturas, reportajes ni figuras.
2. No cambiar firmware sin prueba en placa.
3. No cambiar contratos Bridge sin test de parser y prueba App Lab.
4. No quitar panic MIDI.
5. No quitar quality gate.
6. No meter tools offline en el flujo principal UML.
7. No simplificar WebUI sin verificar fluidez, consola y controles musicales.
8. No confundir rutas legacy con rutas live final-v4.

## 2. Nucleo que debe conservarse

En la futura version esencial, este flujo debe mantenerse y aparecer en UML principal:

```text
sketch.setup/loop
  -> ADS1299Plus.readFrameRDATAC
  -> filtros MCU
  -> TxBlockRing.publishPendingBlocks
  -> Bridge.notify("eeg_block_uV")
  -> EEGReceiver.eeg_block_uV
  -> EEGSignalProcessor.add_block_uV
  -> EEGSignalProcessor.compute_live_features
  -> SignalQuality / QualityGate
  -> SonificationFeatureAdapter.update
  -> MusicSegmentBuilder.build_live_segment
  -> BarGenerator.generate_live_bar
  -> NoteGenerator.generate_notes_for_bar
  -> MidiScheduler
  -> MidiByteTransport
  -> Bridge.call("midi_bytes")
  -> firmware midi_bytes
  -> Serial1/D1 con TX invertido
  -> MIDI OUT fisico
```

Tambien deben conservarse como esenciales de operacion:

```text
/midi/panic
/music/config o equivalente root/main/scale
snapshot minimo WebUI
piano roll desde music.recent_notes
```

## 3. Bloques que deben quedar laterales, no borrados

Estos bloques no deben entrar en el UML principal, pero se conservan por validacion, trazabilidad o diagnostico:

```text
CaptureManager
capture_eeg_quality.py
final_capture_session.py
validate_spectral_features.py
analyze_eeg_capture.py
parse_mcu_bench_monitor.py
benchmarks/
docs/validacion_tfg/
figuras/reportajes
LED matrix
MIDI test endpoints
polling fallback WebUI
```

Interpretacion:

- `CaptureManager` es runtime lateral porque guarda datos, pero no calcula quality gate ni sonificacion.
- `capture_eeg_quality.py` es una tool externa de solicitud de captura sobre backend vivo; no captura ni calcula calidad por si sola.
- Las tools offline recalculan/validan, pero no forman parte del tiempo real EEG->MIDI.
- LED matrix es consumidor opcional de `music.recent_notes`, no ruta principal.

## 4. Rutas candidatas a ocultar o eliminar

No eliminar todavia. Primero buscar referencias, crear pruebas y validar.

| Ruta/funcion | Estado actual | Motivo para ocultar/eliminar | Condicion antes de eliminar |
| --- | --- | --- | --- |
| `receiver.eeg_frame_uV()` | Legacy | Ruta antigua de muestra individual; final-v4 usa `eeg_block_uV` | Buscar referencias y probar recepcion por bloques. |
| `EEGSignalProcessor.compute_online_features()` | Secundaria | No es la ruta live benchmarkeada; puede confundir UML | Confirmar que no se usa en backend/tools importantes. |
| `BarGenerator.generate_bars()` | Compatibilidad | Backend live usa `generate_live_bar()` | Buscar referencias y test musical. |
| `NoteGenerator.generate_notes_for_segment()` | Compatibilidad | Backend live usa `generate_notes_for_bar()` | Buscar referencias y test notas. |
| Aliases legacy de `SonificationFeatures` | Compatibilidad interna | TFG/UML deben usar nombres final-v4 | Migrar `MusicSegment` y backend a nombres nuevos antes de quitar. |
| `controlValue()` legacy fallback en `assets/app.js` | Compatibilidad UI | Puede confundir si final-v4 ya solo emite nombres nuevos | Confirmar snapshot final-v4 y probar navegador. |
| MIDI test loop | Diagnostico | No es ruta EEG->MIDI; puede enmascarar sonificacion | Mantener procedimiento de test alternativo o documentado. |
| LED matrix | Lateral opcional | Desactivado por defecto; no necesario para EEG->MIDI | Decidir si se excluye de rama esencial o queda en modulo lateral. |
| Polling fallback WebUI | Robustez | Duplica con WebSocket | Medir fluidez si se simplifica. |

## 5. Comentarios historicos que conviene limpiar

Se detectaron comentarios que no rompen el funcionamiento pero confunden la lectura:

| Zona | Comentario historico | Estado real final-v4 | Accion futura |
| --- | --- | --- | --- |
| `sketch.ino` | Referencias a mantener modo normal `ADS_DIAGNOSTIC_MODE=0` para capturas reales | Capturas finales usan modo 5 `bias_ch1_only_loff_off` | Actualizar comentario sin cambiar macro. |
| `midi_live.py` | Transporte hacia MCU/D1 planteado como futuro | `MidiByteTransport` y `midi_bytes` ya existen y estan validados | Reescribir comentario como ruta actual. |
| `midi_byte_transport.py` | `enabled=False` recomendado hasta tener handler firmware | En final-v4 `midi_bytes` existe y MIDI live esta enabled por defecto | Actualizar comentario. |
| `backend_service.py` | Comentario antiguo indicando que no hay controles WebUI | WebUI expone root/main/scale | Actualizar comentario. |
| Docs antiguas | Referencias a final-v3 como estado principal | final-v4 es la referencia integrada | Mantener historico, no mezclar. |

Estos cambios son buenos candidatos para una primera fase de simplificacion porque no alteran runtime.

## 6. Hallazgos por area

| Hallazgo | Archivo/funcion | Tipo | Riesgo actual | Beneficio de simplificar | Prioridad |
| --- | --- | --- | --- | --- | --- |
| Orquestador backend demasiado ancho | `backend_service.py` (`__init__`, `step`, `_build_snapshot`) | Arquitectura | Cambios en MIDI/LED/UI pueden afectar RX/DSP | Separar conceptualmente snapshot, music engine, quality y transports | Alta |
| Snapshot schema sin test automatico | `backend_service.py`, `assets/app.js` | Contrato UI | Renombrar claves rompe UI silenciosamente | Test schema + fixture JSON | Alta |
| Quality score heuristico necesita tests | `spectral_quality.py` | Seguridad musical | Cambios de umbral alteran sonificacion | Tests clean/artifact/bad basados en capturas | Alta |
| Payload `eeg_block_uV` manual en firmware | `streaming.h::publishPendingBlocks` | Contrato Bridge | Cambiar `BLOCK_SAMPLES` exige editar lista de argumentos | Helper seguro o test de contrato | Alta, con placa |
| MIDI UART fisico depende de TXINV | `sketch.ino`, `midi_byte_transport.py` | Hardware | Cambiar UART/polaridad rompe MIDI OUT | Mantener Serial1/D1 + TXINV y test placa | Alta |
| Doble inicializacion SPI | `sketch.ino` + `ADS1299Plus.begin()` | Deuda tecnica | Puede confundir refactor futuro | Revisar solo con placa; no tocar ahora | Media/alta |
| WebUI poco comprensible para el autor | `assets/app.js`, `index.html`, `web_server.py` | Mantenibilidad/TFG | Dificulta defensa y cambios seguros | Simplificar por bloques, comentarios y schema | Alta |
| Controles musicales WebUI sin tests automaticos | `web_server.py`, `assets/app.js` | UI/operacion | Root/main/scale pueden romperse con renames | Tests HTTP + snapshot | Media/alta |
| `compute_quality_diagnostics()` recalcula PSD para diagnostico | `eeg_signal_processor.py` | Coste CPU | Puede duplicar trabajo con features live | Reusar contexto si se rediseÃ±a | Media |
| Generadores musicales con muchos helpers privados | `music_bar.py`, `music_note.py` | Mantenibilidad | Dificil ajustar musicalmente sin romper | Tests de pitch/rhythm/velocity | Media |
| Config ADS por macro | `sketch.ino`, `set_ads_diagnostic_mode.py` | Configuracion | Requiere recompilar y puede quedar modo no deseado | Perfil visible/documentacion clara | Media |
| `ADS_DIAGNOSTIC_MODE=5` default | `sketch.ino` | Interpretacion | CH2-CH4 no son EEG activo | Documentar y mostrar en snapshot/UI | Media |
| Filtros firmware sin modo raw runtime | `filters.h`, `loop` | Diagnostico | Dificulta comparar raw vs filtrada | Solo valorar si hay necesidad real | Media, hardware |
| `BenchStats` mezcla nombres synthetic/real lag | `bench.h`, `loop` | Nombre confuso | `synthetic_lag_events_total` se usa tambien con DRDY real | Renombrar con compatibilidad si se toca bench | Baja/media |
| LED dry-run devuelve false | `sketch.ino`, `led_matrix_transport.py` | Semantica confusa | Python puede contarlo como fallo si enabled | Definir dry-run vs real | Baja/media |
| `build_validation_docs.py` es monolitico | `python/tools/build_validation_docs.py` | Tool offline | Dificil mantener | Mantener historico; priorizar tools finales | Baja |
| Escritura JSON no atomica en algunas tools offline | Tools varias | Robustez offline | Reports a medias si se interrumpe | Usar helper si aporta valor | Baja |
| `runtime_config.py` crece como cajon de sastre | `runtime_config.py` | Config | Mezcla MIDI/LED/state | Agrupar por secciones/dataclasses | Baja |

## 7. Plan de fases recomendado

### Fase A - Limpieza documental y comentarios sin tocar runtime

Objetivo: mejorar comprension sin riesgo funcional.

Tareas:

1. Limpiar comentarios historicos en MIDI, WebUI y firmware.
2. Actualizar nombres en comentarios a final-v4.
3. Mantener `docs/README.md` y `configuracion_final_v4.md` como entrada principal.
4. No mover imports ni borrar funciones.

Validacion:

```text
git diff claro
py_compile si se toca comentario dentro de .py
sin cambios de comportamiento
```

### Fase B - Tests de contrato antes de refactor

Objetivo: crear red de seguridad.

Tests prioritarios:

1. `eeg_contract.py`: parser `eeg_block_uV`.
2. `midi_live.py`: `event_to_midi_bytes`, panic y scheduler.
3. `midi_byte_transport.py`: mock Bridge `midi_bytes`.
4. `spectral_quality.py`: clean/artifact/bad.
5. Snapshot schema minimo para WebUI.
6. Music config: root/main/scale.
7. WebUI smoke manual: `/latest`, socket, panic, piano roll.

### Fase C - Simplificacion conceptual/UML sin borrar codigo

Objetivo: generar diagramas claros.

Acciones:

1. Crear `docs/propuesta_version_esencial_uml.md`.
2. Dibujar flujo principal EEG->MIDI.
3. Dibujar WebUI como observador/control ligero.
4. Dibujar capturas/benchmarks/tools como laterales.
5. Omitir rutas legacy del UML principal.

### Fase D - Refactor suave con commits pequeÃ±os

Objetivo: mejorar estructura sin romper.

Candidatos:

1. Extraer construccion de snapshot a funcion/modulo testeable.
2. Aislar motor musical live de `BackendService` sin cambiar API.
3. Reordenar WebUI JS por bloques comprensibles.
4. Usar `/music/config` atomico en WebUI.
5. Limpiar fallbacks legacy solo si el snapshot final-v4 ya no los necesita.

### Fase E - Eliminacion real de codigo legacy

Objetivo: reducir codigo solo cuando haya seguridad.

Candidatos:

```text
eeg_frame_uV
compute_online_features
generate_bars
generate_notes_for_segment
legacy aliases
MIDI test loop si se sustituye por diagnostico documentado
LED matrix si se decide excluir de rama esencial
```

Condicion: busqueda de referencias, tests, App Lab smoke y, si afecta MIDI/firmware, prueba en placa.

## 8. WebUI: criterio especial

La WebUI debe tratarse delicadamente porque el usuario no la domina tanto como firmware/DSP y fue generada principalmente por Codex. La simplificacion debe hacerla explicable en el TFG sin perder funcionalidad.

Conservar:

```text
actualizacion live
panic MIDI
root/main/scale
piano roll
estado RX/DSP/calidad/MIDI
nombres final-v4 de sonificacion
```

Reducir u ocultar:

```text
endpoints de test MIDI
fallbacks legacy
LED status si no se usa
metricas excesivas no necesarias para memoria
```

Prohibido en version esencial:

```text
controles ADS/filtros/firmware desde WebUI
controles MIDI enable/LED enable si no hay test fuerte
logica DSP dentro de JS
```

## 9. Reglas de validacion antes/despues

Antes de cualquier simplificacion real:

```bash
python3 -m py_compile python/*.py python/tools/*.py benchmarks/*.py
```

Validaciones funcionales minimas:

1. App Lab arranca.
2. Firmware detecta Linux con `linux_started`.
3. WebUI `/latest` responde.
4. Snapshot tiene RX/features/quality/sonification/music/midi.
5. `rx_frame_rate_hz ~= 250`.
6. `rx_block_rate_hz ~= 31.25`.
7. `window_ready=True` tras 4 s.
8. Panic MIDI funciona.
9. Root/main/scale cambian.
10. Piano roll se actualiza.
11. Captura corta guarda CSV y metadata.
12. Si se toca firmware/MIDI, probar nota real por MIDI OUT.
13. Si se toca DSP/quality, recalcular una captura real.
14. Si se toca timing, repetir benchmark relevante.

## 10. Resultado esperado de la futura version esencial

La futura version esencial debe permitir explicar en la memoria:

```text
1. Como se adquiere EEG desde ADS1299.
2. Como se empaqueta y transporta por Bridge.
3. Como Python calcula features espectrales.
4. Como se decide si la ventana es fiable con quality gate.
5. Como esos rasgos modulan controles musicales.
6. Como se generan notas.
7. Como se programan y envian bytes MIDI.
8. Como la WebUI observa el sistema y permite control musical minimo.
```

Debe dejar fuera del relato principal:

```text
benchmarks detallados
tools offline
generadores de figuras
LED matrix
rutas legacy
endpoints de diagnostico
```

Pero esos elementos deben seguir existiendo como evidencia y soporte tecnico del TFG.



