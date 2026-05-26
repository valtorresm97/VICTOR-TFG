# 10. Redundancias y deuda tecnica

No se refactorizo nada. Esta lista documenta deuda para prompts futuros.

| Redundancia/deuda | Archivos afectados | Riesgo | Prioridad | Recomendacion futura |
| --- | --- | --- | --- | --- |
| Constantes EEG repetidas (`FS_HZ`, `NUM_CH`, `BLOCK_SAMPLES`, `LSB_V`, status mask) | `sketch.ino`, `receiver.py`, `capture_manager.py`, tools offline | Resuelto en Python: `receiver.py`, `capture_manager.py`, backend y tools importan `python/eeg_contract.py`. Firmware queda como fuente del payload real. | Alta | Mantener sincronía con firmware si cambian `streaming.h` o ADS1299. |
| Formato `eeg_block_uV` duplicado manualmente | `streaming.h`, `receiver.py`, `capture_manager.py` | Resuelto en Python: evento, longitud, stride, parseo e iteración por muestra viven en `python/eeg_contract.py`; firmware sigue emitiendo el payload real. | Alta | Si cambia `streaming.h`, actualizar el parser central Python en la misma iteración. |
| DSP multitaper implementado en live y offline | `dsp_core.py`, `analyze_eeg_capture.py`, `validate_spectral_features.py`, `build_validation_docs.py` | Resuelto: `analyze_eeg_capture.py`, `validate_spectral_features.py` y `build_validation_docs.py` reutilizan `DSPCore` para PSD multitaper. | Alta | Mantener `DSPCore` como única implementación DPSS/FFT. |
| Quality score duplicado parcialmente | `spectral_quality.py`, `validate_spectral_features.py`, docs | Umbrales/documentacion pueden quedar desalineados. | Media | Centralizar calculo y documentar version. |
| Escritura JSON atomica duplicada | `app_state.py`, `capture_manager.py`, `capture_eeg_quality.py` | Comportamientos distintos ante error. | Baja | Helper comun en futuro. |
| Configuracion por env dispersa | `backend_service.py`, `led_matrix_visualizer.py`, firmware macros | Dificil saber enabled/disabled. | Alta | Crear `config.py` y mapa firmware separado. |
| `BENCH_NOTIFY_ENABLED` mezcla streaming y benchmark | `sketch.ino` | Desactivar "bench" corta streaming. | Alta | Renombrar o separar `STREAMING_ENABLED` y `BENCH_REPORT_ENABLED`. |
| `dashboard.py` esperado por docs iniciales no existe | Prompt/AGENTS vs `web_server.py` + assets | Confusion al auditar UI. | Media | Actualizar docs base a WebUI real. |
| Adafruit NeoPixel declarado pero no usado | `sketch/sketch.yaml` | Dependencia innecesaria. | Baja | Confirmar si legacy; quitar en refactor si no hay matriz externa. |
| `std::vector` en handler firmware LED | `sketch.ino` | Asignacion dinamica/Bridge payload en MCU. | Media | Mantener disabled; evaluar payload fijo si se activa en tiempo real. |
| `USE_SYNTHETIC` bloque parcialmente comentado en setup | `sketch.ino` | Confusion: siempre imprime modo real. | Media | Limpiar en refactor, sin tocar funcionalidad ahora. |
| CH2-CH4 siguen transmitidos aunque modo 5 los apaga | Firmware/Python/UI | Usuarios pueden interpretarlos como EEG. | Media | UI debe etiquetar CH1 activo. |
| Reports/documentos solapados | `docs/resultados_*`, `docs/validacion_*`, `docs/validacion_tfg/*` | Dificil saber cual es definitivo. | Media | Marcar docs definitivos y legacy. |
| `pack_point/unpack_point` no usado por transporte actual | `led_matrix_visualizer.py` | Codigo extra/legacy para posible formato alternativo. | Baja | Mantener hasta decidir formato final. |
| Music generation fija sin controles UI | `backend_service.py`, assets | Cambios requieren editar codigo/env. | Media | Extraer configuracion musical a snapshot/control UI futuro. |
| Panic existe en backend pero no expuesto | `backend_service.py`, `midi_live.py`, assets | Operacion segura incompleta en directo. | Alta | Agregar boton/endpoint panic antes de MIDI fisico. |
| Capturas guardan filas en memoria | `capture_manager.py` | Capturas largas pueden crecer mucho. | Baja/Media | Streaming incremental a CSV si se amplian duraciones. |
| `state/` runtime no versionado pero rutas hardcodeadas | `app_state.py`, `capture_manager.py`, tools | Choques si varias apps corren. | Baja | Namespace por app/branch si hiciera falta. |
