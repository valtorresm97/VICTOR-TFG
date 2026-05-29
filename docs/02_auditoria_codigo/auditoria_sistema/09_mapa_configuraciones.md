# 09. Mapa de configuraciones enabled/disabled - final-v4

## 1. Objetivo

Este documento resume las configuraciones que activan, desactivan o modifican partes del sistema EEG-MIDI. Su valor principal es explicar de forma transversal que esta activo en `firmware-final-v4`, que queda desactivado por defecto, que es peligroso cambiar y que pertenece a runtime, validacion o diagnostico.

La auditoria detallada funcion por funcion esta en:

```text
docs/02_auditoria_codigo/funcion_por_funcion/
```

Este documento debe usarse como mapa narrativo de configuracion para TFG y futura version esencial/UML.

## 2. Defaults principales final-v4

| Bloque | Configuracion | Valor final-v4 | Lectura correcta |
| --- | --- | --- | --- |
| Entrada EEG | `USE_SYNTHETIC` | `0` | Se usa ADS1299 real, no generador sintetico. |
| ADS1299 | `ADS_DIAGNOSTIC_MODE` | `5` | Modo final de capturas: `bias_ch1_only_loff_off`. |
| Canales | CH1-only | activo por modo 5 | CH1 es EEG principal; CH2-CH4 se conservan por contrato, no como EEG activo. |
| Streaming EEG | `EEG_STREAMING_NOTIFY_ENABLED` | `1` | Activa `Bridge.notify("eeg_block_uV")`. |
| Bench MCU | `BENCH_REPORT_ENABLED` | `1` | Reportes por Monitor/App Lab; no anade trafico Bridge. |
| MIDI firmware | `MIDI_UART_ENABLED` | `1` | MIDI fisico activo por `Serial1`/D1. |
| MIDI polaridad | `USART_CR2_TXINV` | obligatorio | TX invertido necesario para circuito MIDI OUT validado. |
| MIDI Python | `EEG_MIDI_LIVE_ENABLED` | `True` por defecto | Transporte live activo hacia `midi_bytes`. |
| LED firmware | `LED_MATRIX_ENABLED` | `0` | LED matrix desactivada por defecto. |
| LED Python | `EEG_LED_MATRIX_ENABLED` | `False` por defecto | No se envia trafico LED por Bridge. |
| DSP window | `FEATURE_WINDOW_SEC` | `4.0` | Ventana de features y quality. |
| DSP hop | `FEATURE_HOP_SAMPLES` | `64` | Presupuesto Python: 256 ms. |
| Snapshot UI | `SNAPSHOT_PUBLISH_PERIOD_SEC` | `0.2` | WebUI recibe estado a ~5 Hz. |
| Snapshot disco | `DISK_PUBLISH_PERIOD_SEC` | `1.0` | Persistencia JSON para fallback/tools. |

## 3. Configuracion firmware/ADS1299

| Configuracion | Archivo | Valor actual | Opciones | Que activa | Riesgo | Recomendacion final-v4 |
| --- | --- | --- | --- | --- | --- | --- |
| `USE_SYNTHETIC` | `sketch/sketch.ino` | `0` | `0/1` | Generador sintetico en firmware. | Si 1, no valida ADS/SPI/DRDY real. | Mantener 0 para capturas y benchmarks finales. |
| `ADS_DIAGNOSTIC_MODE` | `sketch/sketch.ino` | `5` | 0..5 | Config ADS normal/short/test/no-bias/bias/CH1-only. | Cambia hardware pipeline y comparabilidad de capturas. | Mantener 5 para reproducir final-v4; documentar en metadata/sesion. |
| `DEBUG_MONITOR` | `sketch/sketch.ino` | `true` | bool | Prints periodicos y errores. | Puede afectar timing si se abusa. | Mantener rate-limited; no aumentar durante benchmarks. |
| `DEBUG_EVERY_N` | `sketch/sketch.ino` | `500` | entero | Frecuencia de prints debug. | Prints excesivos. | No bajar sin medir. |
| `EEG_STREAMING_NOTIFY_ENABLED` | `sketch/sketch.ino` | `1` | macro 0/1 | Envio EEG por Bridge. | Si se apaga, Python no recibe `eeg_block_uV`. | Mantener activo para runtime. |
| `BENCH_NOTIFY_ENABLED` | `sketch/sketch.ino` | alias legacy | macro 0/1 | Compatibilidad externa; alimenta `EEG_STREAMING_NOTIFY_ENABLED` si existe. | Nombre historico confuso. | No usar en cambios nuevos. |
| `BENCH_REPORT_ENABLED` | `sketch/sketch.ino` | `1` | macro 0/1 | Reportes Monitor `[BENCH] EEG_MIDI`. | Prints excesivos pueden introducir jitter. | Mantener para observabilidad; apagar solo en pruebas de latencia puras. |
| `BENCH_REPORT_EVERY_MS` | `sketch/sketch.ino` | `5000` | ms | Periodo de reporte Monitor. | Periodo bajo aumenta prints. | Mantener 5 s por defecto. |
| `MIDI_UART_ENABLED` | `sketch/sketch.ino` | `1` | macro 0/1 | UART MIDI fisica. | Si se apaga, Python envia pero firmware no saca MIDI. | Mantener 1 en final-v4. |
| `MIDI_SERIAL` | `sketch/sketch.ino` | `Serial1` | objeto UART | Puerto fisico MIDI D1/TX. | Cambiar UART exige revalidar placa/cableado. | Mantener `Serial1`. |
| `USART_CR2_TXINV` | `sketch/sketch.ino` | obligatorio | bit USART1 | Invierte TX. | Sin inversion el circuito N-audio no reproduce correctamente. | No retirar. |
| `MIDI_MCU_SELF_TEST_ENABLED` | `sketch/sketch.ino` | `0` | macro 0/1 | Arpegio diagnostico directo MCU. | Puede tapar o confundirse con sonificacion EEG. | Mantener 0 salvo prueba aislada. |
| `LED_MATRIX_ENABLED` | `sketch/sketch.ino` | `0` | macro 0/1 | Arduino_LED_Matrix en firmware. | Trafico/dibujo LED pueden cargar loop si se activa. | Mantener 0 salvo benchmark LED especifico. |

## 4. Configuracion Python runtime

| Configuracion | Archivo | Valor final-v4 | Opciones | Que activa | Riesgo | Recomendacion final-v4 |
| --- | --- | --- | --- | --- | --- | --- |
| `EEG_MIDI_LIVE_ENABLED` | `backend_service.py` / env | `True` por defecto | true/false | Transporte MIDI Python hacia `midi_bytes`. | Si firmware no tiene handler, habria drops; en final-v4 si lo tiene. | Mantener true. |
| `MIDI_LOOKAHEAD_SEC` | `backend_service.py` | `0.02` | segundos | Adelanto scheduler MIDI. | Muy bajo aumenta jitter; muy alto adelanta eventos. | Mantener salvo medicion musical/latencia. |
| `FEATURE_WINDOW_SEC` | `backend_service.py` | `4.0` | segundos | Ventana DSP live. | Cambia resolucion/latencia/features. | No cambiar sin repetir benchmark y reportes. |
| `FEATURE_HOP_SAMPLES` | `backend_service.py` | `64` | muestras | Cadencia de features. | Cambia CPU/latencia y presupuesto 256 ms. | Mantener en final-v4. |
| `MUSIC_CHORD_MIN_PERIOD_SEC` | `backend_service.py` | `12.0` | 2..120 s | Reduce repeticion de acordes. | Valor bajo reintroduce cambios armonicos excesivos. | Mantener salvo prueba musical. |
| `MUSIC_CHORD_CHANGE_THRESHOLD` | `backend_service.py` | `0.45` | 0.05..2.0 | Permite cambio de acorde si hay cambio suficiente. | Alto congela armonia; bajo repite acordes. | Ajustar solo con escucha y registro. |
| `MUSIC_PITCH_VARIETY` | `backend_service.py` | `0.65` | 0..1 | Variedad melodica entre candidatos cercanos. | Alto puede sonar erratico, bajo repetitivo. | Mantener valor final-v4. |
| `SNAPSHOT_PUBLISH_PERIOD_SEC` | `backend_service.py` | `0.2` | segundos | Snapshot live/WebUI. | Periodo alto empeora fluidez; bajo sube carga. | Mantener para WebUI fluida. |
| `DISK_PUBLISH_PERIOD_SEC` | `backend_service.py` | `1.0` | segundos | Snapshot JSON en disco. | I/O excesivo si baja mucho. | Mantener. |
| Quality gate thresholds | `spectral_quality.py` | fijos en codigo | codigo | Atenua/congela sonificacion. | Umbrales empiricos. | Mantener hasta tener mas capturas. |

## 5. Configuracion WebUI y control musical

La WebUI no cambia firmware ni ADS1299. Solo observa estado y permite control musical ligero.

| Configuracion/accion | Fuente | Estado final-v4 | Uso | Riesgo | Recomendacion |
| --- | --- | --- | --- | --- | --- |
| `root_note` | WebUI/backend | Activo | Tonalidad base elegida por usuario. | Nota invalida rompe escala. | Mantener control. |
| `main_note` | WebUI/backend | Activo | Centro melodico elegido por usuario. | Si se cambia sin panic pueden quedar notas antiguas. | Backend llama panic al actualizar config. |
| `scale_key` | WebUI/backend | Activo | Escala musical. | Escala invalida rompe generacion. | Usar registry. |
| `/music/config` | `web_server.py` | Activo | Actualizacion conjunta root/main/scale. | Menos usado por app.js que endpoints separados. | Preferirlo en simplificacion futura. |
| `/music/root/{note}` | `web_server.py` | Activo | Actualiza root. | Secuencia parcial si falla otra llamada. | Mantener o migrar a `/music/config`. |
| `/music/main/{note}` | `web_server.py` | Activo | Actualiza main. | Secuencia parcial. | Mantener o migrar a `/music/config`. |
| `/music/scale/{key}` | `web_server.py` | Activo | Actualiza escala. | Secuencia parcial. | Mantener o migrar a `/music/config`. |
| `/midi/panic` | `web_server.py` | Activo y esencial | Corta notas colgadas. | No debe eliminarse. | Mantener siempre. |
| `/midi/test-*` | `web_server.py` | Activo diagnostico | Prueba MIDI sin EEG. | Puede confundirse con ruta principal. | Ocultar en UML principal. |
| `socket eeg_snapshot` | `web_server.py` | Activo | Actualizacion live. | Si falla, UI depende de polling. | Mantener. |
| polling fallback | `assets/app.js` | Activo | GET `/latest` cada 400 ms. | Duplica algo de trafico. | Simplificar solo tras medir fluidez. |

## 6. Configuracion LED matrix

LED matrix esta desactivada por defecto y no forma parte del flujo principal EEG->MIDI.

| Configuracion | Archivo | Valor actual | Opciones | Que activa | Riesgo | Recomendacion |
| --- | --- | --- | --- | --- | --- | --- |
| `EEG_LED_MATRIX_ENABLED` | `runtime_config.py` / env | `False` | true/false | Transporte LED Python. | Anade `Bridge.call` extra. | Mantener false salvo prueba LED. |
| `EEG_LED_MATRIX_WIDTH` | `runtime_config.py` | `13` | 1..64 | Ancho frame Python. | Firmware espera 13. | No cambiar sin firmware. |
| `EEG_LED_MATRIX_HEIGHT` | `runtime_config.py` | `8` | 1..32 | Alto frame Python. | Firmware espera 8. | No cambiar sin firmware. |
| `EEG_LED_MATRIX_PITCH_CENTER` | `runtime_config.py` | main note aprox. | 0..127 | Centro vertical. | Solo visual. | Seguro si LED se activa. |
| `EEG_LED_MATRIX_DYNAMIC_CENTER` | `runtime_config.py` | `False` | bool | Centro por mediana reciente. | Puede mover imagen verticalmente. | Mantener false. |
| `EEG_LED_MATRIX_VISIBLE_PITCH_SPAN` | `runtime_config.py` | `8` | 1..64 | Rango vertical. | Notas fuera de rango. | Ajustar solo si LED se usa. |
| `EEG_LED_MATRIX_REFRESH_HZ` | `runtime_config.py` | `8.0` | 1..30 | Tasa LED. | Bridge overhead. | Mantener bajo. |
| `EEG_LED_MATRIX_BRIGHTNESS` | `runtime_config.py` | `7` | 1..7 | Intensidad. | Visual. | OK. |
| `EEG_LED_MATRIX_MAX_POINTS` | `runtime_config.py` | `24` | 1..64 | Puntos por frame. | Saturacion visual/carga. | OK. |
| `EEG_LED_MATRIX_CLIP_MODE` | `runtime_config.py` | `ignore` | `ignore/saturate` | Recorte vertical. | Puede perder notas o saturar bordes. | `ignore` es conservador. |
| `EEG_LED_MATRIX_NOTE_MODE` | `runtime_config.py` | `point` | `point/duration` | Punto o duracion. | `duration` mas puntos/trafico. | Mantener point. |
| `EEG_LED_MATRIX_BRIDGE_METHOD` | `runtime_config.py` | `led_matrix_row` | string | Handler firmware. | Mismatch rompe transporte. | No cambiar salvo coordinado. |

## 7. Configuraciones de captura y validacion

| Configuracion | Fuente | Estado | Que activa | Riesgo | Recomendacion |
| --- | --- | --- | --- | --- | --- |
| Capture mode | `capture_manager.py` | idle por defecto | Captura CSV incremental si hay request | Errores de disco pasan a error | Mantener lateral al runtime. |
| `capture_request.json` | `capture_eeg_quality.py` | externo | Solicita captura al backend vivo | Si backend no corre, no se captura | Usar solo con App Lab viva. |
| `final_capture_session.py` | Tool CLI | offline/control | Sesion final con EEG + musica | Mueve carpetas y lanza procesos | Usar con git limpio. |
| `validate_spectral_features.py` | Tool offline | offline | Recalcula bandpowers/quality/sonificacion | Puede generar outputs masivos | Usar sobre copias o rutas controladas. |
| `parse_mcu_bench_monitor.py` | Tool offline | offline | Parseo de Monitor `[BENCH]` | Depende del formato de log | Conservar logs finales. |

Aclaracion: estas configuraciones no modifican el quality gate runtime. Las tools pueden recalcular calidad offline, pero la decision live de sonificacion ocurre dentro del backend.

## 8. Configuraciones peligrosas de cambiar

| Configuracion | Motivo | Requiere |
| --- | --- | --- |
| `ADS_DIAGNOSTIC_MODE` | Cambia cableado logico, BIAS, lead-off y canales activos | Recompilar/subir firmware, metadata clara y captura de prueba. |
| `FS_HZ` | Afecta firmware, Python, DSP, benchmarks y ejes temporales | Cambio coordinado completo. |
| `NUM_CHANNELS` | Cambia payload, CSV, DSP y UI | Cambio firmware/Python/tools. |
| `BLOCK_SAMPLES` | Cambia `eeg_block_uV`, tasa de bloques y parser | Cambio firmware/Python/tools y benchmark. |
| `LSB_V` o ganancia ADS | Cambia escala uV, quality y features | Validacion de escala. |
| SPI mode/velocidad | Puede romper ADS1299 | Datasheet + prueba ID/RDATAC. |
| Filtros MCU | Cambia espectro antes de Python | Capturas A/B y reportes. |
| `MIDI_SERIAL` / TXINV | Rompe MIDI fisico | Prueba con sintetizador externo. |
| `EEG_MIDI_LIVE_ENABLED` | Puede dejar sin MIDI live | Prueba WebUI/MIDI. |
| Snapshot keys | Rompe WebUI y tools | Schema/test navegador. |
| Quality thresholds | Cambia que ventanas se sonifican | Capturas clean/artifact/bad. |

## 9. Configuraciones para futura version esencial/UML

En el UML principal deben aparecer solo las configuraciones que explican el flujo:

```text
ADS_DIAGNOSTIC_MODE=5
FS_HZ=250
BLOCK_SAMPLES=8
FEATURE_WINDOW_SEC=4.0
FEATURE_HOP_SAMPLES=64
EEG_MIDI_LIVE_ENABLED=True
MIDI_UART_ENABLED=1
Serial1/D1/TXINV
root_note/main_note/scale_key
SignalQuality / QualityGate thresholds
```

Deben quedar laterales:

```text
BENCH_REPORT_ENABLED
capture_request/capture_status
LED matrix env vars
MIDI test endpoints
Tools offline
```

Deben quedar como compatibilidad/historico:

```text
BENCH_NOTIFY_ENABLED
rutas legacy de sonificacion o receiver
comentarios antiguos de MIDI futuro
```

## 10. Conclusion

La configuracion final-v4 queda caracterizada por:

```text
ADS real, modo 5 CH1-only, streaming por bloques activo,
quality gate activo, sonificacion live activa, MIDI fisico activo,
WebUI musical activa, LED desactivado y benchmarks/capturas como laterales de validacion.
```

Esta configuracion es la que debe considerarse punto de partida para redactar el TFG y para preparar la futura version esencial/UML.

