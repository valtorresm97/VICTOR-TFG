# 09. Mapa de configuraciones enabled/disabled

Busqueda realizada con `rg` sobre flags, `ENABLED`, `MODE`, `DEBUG`, `BENCH`, `SYNTHETIC`, `LED`, `MIDI_LIVE`, filtros y quality.

| Configuracion | Archivo | Valor actual | Opciones | Que activa | Riesgo | Recomendacion |
| --- | --- | --- | --- | --- | --- | --- |
| `USE_SYNTHETIC` | `sketch/sketch.ino` | `0` | `0/1` | Generador sintetico en firmware. | Si 1, no valida ADS/SPI/DRDY. | Mantener 0 para captura real. |
| `ADS_DIAGNOSTIC_MODE` | `sketch/sketch.ino` | `5` | 0..5 | Config ADS normal/short/test/no-bias/bias/CH1-only. | Cambia hardware pipeline. | Documentar modo en cada captura. |
| `DEBUG_MONITOR` | `sketch/sketch.ino` | `true` | bool | Prints cada 500 muestras y errores. | Puede afectar timing. | Separar de build final si hace falta. |
| `DEBUG_EVERY_N` | `sketch/sketch.ino` | `500` | entero | Frecuencia de prints debug. | Prints excesivos. | Subir o desactivar en pruebas largas. |
| `EEG_STREAMING_NOTIFY_ENABLED` | `sketch/sketch.ino` | `1` | macro 0/1 | Envio EEG por Bridge. | Si se apaga, Python no recibe `eeg_block_uV`. | Mantener activo para captura real. |
| `BENCH_NOTIFY_ENABLED` | `sketch/sketch.ino` | alias legacy | macro 0/1 | Compatibilidad externa: si existe, alimenta `EEG_STREAMING_NOTIFY_ENABLED`. | Nombre historico confuso. | No usar en cambios nuevos. |
| `BENCH_REPORT_ENABLED` | `sketch/sketch.ino` | `1` | macro 0/1 | Activa/desactiva reportes Monitor. | Si hay prints excesivos puede afectar timing. | Apagar para pruebas de latencia si hace falta. |
| `BENCH_REPORT_EVERY_MS` | `sketch/sketch.ino` | `5000` | ms | Periodo de reporte Monitor. | Reportes frecuentes pueden afectar timing. | Mantener 5 s por defecto. |
| `LED_MATRIX_ENABLED` | `sketch/sketch.ino` | `0` | macro 0/1 | Arduino_LED_Matrix en firmware. | Bridge/LED puede cargar loop si activo. | Activar solo tras medir. |
| `MIDI_UART_ENABLED` | `sketch/sketch.ino` | `0` | macro 0/1 | UART MIDI fisica. | Requiere `MIDI_SERIAL`; puede interferir. | No activar sin verificar D1/TX. |
| `MIDI_SERIAL` | `sketch/sketch.ino` | no definido | objeto UART | Puerto fisico MIDI. | Compilacion falla si falta y UART enabled. | Definir solo con placa verificada. |
| `EEG_MIDI_LIVE_ENABLED` | `backend_service.py` | env default `False` | true/false | Transporte MIDI Python. | Si firmware no esta listo, fallos/drops. | Mantener false hasta prueba MIDI fisica. |
| `MIDI_LOOKAHEAD_SEC` | `backend_service.py` | `0.02` | segundos | Adelanto scheduler. | Jitter si demasiado bajo/alto. | Medir con MIDI real. |
| `EEG_LED_MATRIX_ENABLED` | `led_matrix_visualizer.py` | env default `False` | true/false | Transporte LED Python. | Bridge.call extra. | Activar tras bench EEG estable. |
| `EEG_LED_MATRIX_WIDTH` | `led_matrix_visualizer.py` | `13` | 1..64 | Ancho frame Python. | Firmware espera 13; mismatch rompe handler. | No cambiar sin firmware. |
| `EEG_LED_MATRIX_HEIGHT` | `led_matrix_visualizer.py` | `8` | 1..32 | Alto frame Python. | Firmware espera 8. | No cambiar sin firmware. |
| `EEG_LED_MATRIX_PITCH_CENTER` | `led_matrix_visualizer.py` | main note 67 | 0..127 | Centro vertical. | Solo visual. | Configurable seguro. |
| `EEG_LED_MATRIX_DYNAMIC_CENTER` | `led_matrix_visualizer.py` | `False` | bool | Centro por mediana reciente. | Puede mover imagen verticalmente. | Probar con usuarios. |
| `EEG_LED_MATRIX_VISIBLE_PITCH_SPAN` | `led_matrix_visualizer.py` | `8` | 1..64 | Rango vertical. | Notas fuera de rango. | Ajustar segun musica. |
| `EEG_LED_MATRIX_REFRESH_HZ` | `led_matrix_visualizer.py` | `8.0` | 1..30 | Tasa LED. | Bridge overhead. | Mantener bajo. |
| `EEG_LED_MATRIX_BRIGHTNESS` | `led_matrix_visualizer.py` | `7` | 1..7 | Intensidad. | Visual, no timing. | OK. |
| `EEG_LED_MATRIX_MAX_POINTS` | `led_matrix_visualizer.py` | `24` | 1..64 | Puntos por frame. | Saturacion visual/carga. | OK. |
| `EEG_LED_MATRIX_CLIP_MODE` | `led_matrix_visualizer.py` | `ignore` | `ignore/saturate` | Recorte vertical. | Perder notas o saturar bordes. | `ignore` es conservador. |
| `EEG_LED_MATRIX_NOTE_MODE` | `led_matrix_visualizer.py` | `point` | `point/duration` | Punto o duracion. | `duration` mas puntos. | Probar coste si se activa. |
| `EEG_LED_MATRIX_BRIDGE_METHOD` | `led_matrix_visualizer.py` | `led_matrix_frame` | string | Nombre handler. | Mismatch con firmware. | No cambiar salvo coordinado. |
| `FEATURE_WINDOW_SEC` | `backend_service.py` | `4.0` | segundos | Ventana DSP. | Latencia/resolucion. | Critico para features. |
| `FEATURE_HOP_SAMPLES` | `backend_service.py` | `64` | muestras | Hop DSP. | CPU/latencia. | OK. |
| `SNAPSHOT_PUBLISH_PERIOD_SEC` | `backend_service.py` | `0.2` | segundos | UI snapshot. | UI/carga. | OK. |
| `DISK_PUBLISH_PERIOD_SEC` | `backend_service.py` | `1.0` | segundos | Snapshot JSON en disco. | I/O. | OK. |
| Quality gate | `spectral_quality.py` | thresholds fijos | codigo | Atenua/congela sonificacion. | Umbrales empiricos. | Mantener hasta mas capturas. |
| Filtros MCU | `sketch.ino`, `filters.h` | HP 0.5, notch 50, LP 40 | codigo | Filtrado previo a Python. | No hay raw compare. | Agregar modo diagnostico futuro. |
| CH1-only | `ADS_DIAGNOSTIC_MODE=5` | activo | modo 5 | CH1 activo, CH2-CH4 apagados. | Columns CH2-CH4 no son EEG real. | UI/docs deben indicarlo. |
| BIAS/RLD | modo 4/5 | activo en modo 5 | registros CONFIG3/BIAS | Deriva BIAS desde CH1P+CH1N. | Depende conexion fisica segura. | Documentar montaje. |
| Capture mode | `capture_manager.py` | idle | request JSON | Captura CSV. | Memoria crece en `rows` durante captura. | OK para duraciones actuales. |
