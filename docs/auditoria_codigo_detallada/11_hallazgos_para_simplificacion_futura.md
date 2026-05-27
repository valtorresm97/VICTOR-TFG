# 11. Hallazgos para simplificacion futura

No se ha refactorizado nada en esta auditoria. Esta lista prepara la siguiente fase.

| Hallazgo | Archivo/funcion | Tipo | Riesgo actual | Beneficio de simplificar | Prioridad |
| --- | --- | --- | --- | --- | --- |
| Orquestador backend demasiado ancho | `backend_service.py` (`__init__`, `step`, `_build_snapshot`) | Responsabilidad mezclada | Cambios en MIDI/LED/UI pueden afectar RX/DSP | Separar snapshot, music engine y transports | Alta |
| Payload `eeg_block_uV` manual en firmware | `streaming.h::publishPendingBlocks` | Contrato manual rigido | Cambiar `BLOCK_SAMPLES` exige editar lista de argumentos | Generador/plantilla o helper seguro | Alta, con pruebas |
| Config ADS diagnostic por macro | `sketch.ino`, `set_ads_diagnostic_mode.py` | Config compile-time | Requiere recompilar y puede quedar en modo 5 sin querer | Perfil claro por build o documentacion visible | Media |
| `ADS_DIAGNOSTIC_MODE=5` default | `sketch.ino` | Riesgo configuracion | Captura real multicanal no esta activa; CH2-CH4 apagados | Explicitacion por perfil y UI | Media |
| Filtros firmware sin modo raw runtime | `filters.h`, `loop` | Falta control diagnostico | Dificulta comparar raw vs filtrada | Flag seguro raw/filtered con contrato | Media, hardware |
| `BenchStats` mezcla nombres synthetic/real lag | `bench.h`, `loop` | Nombre confuso | `synthetic_lag_events_total` se usa tambien con DRDY real | Renombrar counters con compatibilidad | Baja/media |
| `Receiver.eeg_frame_uV` legacy | `receiver.py` | Legacy | Mantiene ruta no usada | Eliminar tras confirmar no hay firmware viejo | Baja |
| `EEGSignalProcessor` ignora `channel_idx` en available | `available_samples/seconds` | API confusa | Parece multicanal por canal pero devuelve global | Renombrar o documentar | Baja |
| `compute_quality_diagnostics` recalcula PSD para snapshot | `eeg_signal_processor.py` | Coste CPU | Puede duplicar trabajo con features live | Reusar PSD/features si se guarda contexto | Media |
| Quality score heuristico necesita tests | `spectral_quality.py` | Falta test | Cambios de umbral pueden alterar sonificacion | Tests clean/artifact/bad basados en capturas | Alta |
| Generadores musicales tienen muchos helpers privados | `music_bar.py`, `music_note.py` | Funcion larga/estado dificil | Dificil ajustar musicalmente sin romper | Tests musicales y separacion de pitch/rhythm/velocity | Media |
| Controles musicales WebUI acotados sin tests | `backend_service.py`, `web_server.py`, `assets` | Falta test | Root/main/scale ya funcionan, pero un rename puede romper UI/endpoints | Tests HTTP + snapshot para `/music/*` | Media |
| MIDI UART fisico validado, requiere preservar TXINV | `sketch.ino`, `midi_byte_transport.py` | Dependencia hardware | Cambiar UART/polaridad rompe MIDI OUT aunque los bytes sean correctos | Mantener `Serial1`/D1 + `USART_CR2_TXINV`; revalidar en placa si cambia hardware | Alta |
| LED fisico disabled y handler dry-run devuelve false | `sketch.ino`, `led_matrix_transport.py` | Semantica confusa | Transport podria contar fallo aunque handler valido | Definir contrato dry-run vs real | Baja/media |
| `build_validation_docs.py` es monolitico | `python/tools/build_validation_docs.py` | Tool offline grande | Dificil mantener; muchos plots/docs en un archivo | Separar loaders, plots, docs | Baja, offline |
| Escritura JSON offline no atomica en tools | Algunas tools offline | Logica residual | Reports offline podrian quedar a medias si se interrumpe | Usar helper compartido solo si aporta valor | Baja |
| Snapshot schema sin test automatico | `backend_service.py`, `assets/app.js` | Falta test | Renombrar claves rompe UI silenciosamente | Test schema + fixture JS/JSON | Alta |
| Firmware no compilable en entorno Windows actual | Entorno local | Validacion faltante | No se verifica sketch antes de push | Ejecutar build en placa/App Lab | Alta |
| `runtime_config.py` mezcla defaults MIDI/LED/state | `runtime_config.py` | Config central creciente | Puede volverse cajon de sastre | Agrupar por seccion o dataclasses | Baja |
| `app.js` renderiza todo en un archivo | `assets/app.js` | UI monolitica | Cambios visuales pueden tocar panic/piano roll | Separar renderers cuando UI se estabilice | Media |

## Orden recomendado futuro

1. Crear pruebas de contrato para snapshot, `eeg_block_uV`, `event_to_midi_bytes`, LED row packing y quality gate.
2. Extraer de `backend_service.py` la construccion de snapshot a modulo puro testeable.
3. Separar motor musical live de la orquestacion backend.
4. Mantener prueba UART MIDI fisica con TX invertido tras cambios de firmware.
5. Simplificar tools offline grandes sin tocar runtime.
6. Revisar firmware solo con placa y metricas antes/despues.
