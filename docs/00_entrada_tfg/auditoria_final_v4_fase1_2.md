# Auditoria final-v4 - fases 1 y 2

Rama base auditada: `firmware-final-v4`.

Rama de trabajo creada para esta auditoria documental: `refactor/essential-eeg-midi-plan`.

Objetivo de este documento: cerrar las fases 1 y 2 antes de entrar en la fase 3 con supervision. No se reorganiza la documentacion, no se elimina nada, no se toca firmware, no se toca runtime Python, no se tocan assets, no se tocan capturas y no se tocan benchmarks.

## 1. Alcance aplicado

Se ha revisado el estado integrado actual del proyecto despues de fusionar:

- benchmarks reales en placa procedentes de `docs/final-v3-audit-update`;
- capturas finales, reportajes y figuras procedentes de `docs/capture-protocol`;
- rama gemela final `firmware-final-v4`.

La auditoria se detiene antes de la fase 3. La fase 3 debera decidir, con supervision, como reorganizar y actualizar la seccion documental.

## 2. Fase 1 - Lectura obligatoria realizada

### 2.1 Documentos raiz y reglas de proyecto

Revisados:

- `AGENTS.md`
- `README.md` cuando aplica como entrada general del repositorio.
- `docs/README.md` cuando aplica como indice documental.

Observacion principal: `AGENTS.md` sigue siendo util como documento normativo de pines, hardware y flujo general, pero contiene formulaciones historicas como `futura generacion MIDI` o `dashboard web` que deben revisarse en fase 3 porque el MIDI fisico y la WebUI ya estan implementados y validados.

### 2.2 Documentacion de configuracion final

Revisado:

- `docs/configuracion_final_v3.md`

Hallazgo principal:

- Existe `docs/configuracion_final_v3.md`.
- No existe todavia `docs/configuracion_final_v4.md`.
- El documento v3 ya describe correctamente muchos aspectos reales del sistema, pero sus ramas de referencia siguen siendo v3/documentales anteriores.

Accion para fase 3:

- Crear `docs/configuracion_final_v4.md` como documento resumen de la rama integrada.
- Decidir si `docs/configuracion_final_v3.md` se conserva como historico o se actualiza con aviso de reemplazo.

### 2.3 Auditorias de codigo detalladas

Revisada la familia documental:

- `docs/02_auditoria_codigo/funcion_por_funcion/00_inventario_actual.md`
- `docs/02_auditoria_codigo/funcion_por_funcion/01_firmware_funcion_por_funcion.md`
- `docs/02_auditoria_codigo/funcion_por_funcion/02_ads1299_spi_driver.md`
- `docs/02_auditoria_codigo/funcion_por_funcion/03_python_backend_funcion_por_funcion.md`
- `docs/02_auditoria_codigo/funcion_por_funcion/04_dsp_eeg_funcion_por_funcion.md`
- `docs/02_auditoria_codigo/funcion_por_funcion/05_sonificacion_midi_funcion_por_funcion.md`
- `docs/02_auditoria_codigo/funcion_por_funcion/06_led_matrix_funcion_por_funcion.md`
- `docs/02_auditoria_codigo/funcion_por_funcion/07_web_server_assets_funcion_por_funcion.md`
- `docs/02_auditoria_codigo/funcion_por_funcion/08_tools_cli_funcion_por_funcion.md`
- `docs/01_arquitectura_sistema/09_mapa_contratos_entre_modulos.md`
- `docs/01_arquitectura_sistema/10_mapa_funciones_criticas.md`
- `docs/02_auditoria_codigo/funcion_por_funcion/11_hallazgos_para_simplificacion_futura.md`

Hallazgo principal:

- La estructura de auditorias es muy valiosa y no conviene borrarla.
- Varias auditorias siguen nombrando `final-v3` o ramas antiguas, aunque el contenido tecnico sigue siendo aprovechable.
- `11_hallazgos_para_simplificacion_futura.md` ya apunta exactamente a la fase futura de simplificacion/UML y debe usarse como base para `docs/propuesta_version_esencial_uml.md`.

### 2.4 Documentacion de benchmarks reales

Revisado:

- `docs/validacion_tfg/09_benchmarks_rendimiento_placa.md`
- `benchmarks/`
- `benchmarks/results/`
- `benchmarks/reports/`
- `python/tools/parse_mcu_bench_monitor.py`

Hallazgos principales:

- El documento de benchmarks esta integrado en `firmware-final-v4`.
- La validacion temporal usa capturas reales y placa UNO Q/Linux, no PC ni senales sinteticas.
- El benchmark Python usa `benchmarks/run_all_benchmarks.py` sobre `eeg_timeseries.csv` real.
- El benchmark MCU usa logs reales `[BENCH] EEG_MIDI` copiados del Monitor y parseados automaticamente.
- El documento todavia referencia como rama de ejecucion `docs/final-v3-audit-update`, lo cual es historicamente correcto para el origen de los resultados, pero debe contextualizarse en fase 3 dentro de `firmware-final-v4`.

### 2.5 Documentacion de capturas finales

Revisado:

- `docs/04_protocolos_captura/protocolo_capturas_multiusuario.md`
- `docs/04_protocolos_captura/templates/plantilla_sesion_sujeto.md`
- `docs/validacion_tfg/10_resultados_captura_final_laboratorio.md`
- `docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md`
- `docs/validacion_tfg/reportajes_capturas_s01_20260528/`
- `docs/validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib/`
- `docs/validacion_tfg/figures/capturas_finales_s01_20260528_enhanced/`
- `captures/capturas finales/`
- `captures/capturas pruebas casa/`

Hallazgos principales:

- La sesion final `s01_20260528` esta integrada.
- La sesion se documenta correctamente como evidencia tecnica de integracion EEG-MIDI, no como EEG clinico limpio.
- `docs/validacion_tfg/10_resultados_captura_final_laboratorio.md` todavia cita rama `docs/capture-protocol` y un commit historico. En fase 3 habra que decidir si se conserva como procedencia o se actualiza con nota de integracion en `firmware-final-v4`.

### 2.6 Codigo firmware revisado

Revisado:

- `sketch/sketch.ino`
- `sketch/streaming.h`
- `sketch/filters.h`
- `sketch/bench.h`
- `sketch/ADS1299Plus/src/ADS1299Plus.h`
- `sketch/ADS1299Plus/src/ADS1299Plus.cpp`
- `sketch/ADS1299Plus/src/ADS1299_Registers.h`
- `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.h`
- `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.cpp`

Hallazgos principales:

- `ADS_DIAGNOSTIC_MODE` esta en `5` por defecto.
- `USE_SYNTHETIC=0`.
- `MIDI_UART_ENABLED=1`.
- `LED_MATRIX_ENABLED=0`.
- `EEG_STREAMING_NOTIFY_ENABLED=1`.
- `BENCH_REPORT_ENABLED=1`.
- `MIDI_SERIAL=Serial1`.
- `USART_CR2_TXINV` es obligatorio si el UART MIDI esta habilitado.
- `Bridge.provide_safe("midi_bytes", midi_bytes)` y `Bridge.provide_safe("led_matrix_row", led_matrix_row)` estan registrados en firmware.
- La ruta de streaming EEG sigue usando `Bridge.notify("eeg_block_uV")`.

### 2.7 Codigo Python runtime revisado

Revisado:

- `python/main.py`
- `python/backend_service.py`
- `python/receiver.py`
- `python/eeg_contract.py`
- `python/eeg_signal_processor.py`
- `python/dsp_core.py`
- `python/spectral_quality.py`
- `python/sonification_features.py`
- `python/music_segment.py`
- `python/music_bar.py`
- `python/music_note.py`
- `python/music_utils.py`
- `python/scale_registry.py`
- `python/midi_live.py`
- `python/midi_byte_transport.py`
- `python/capture_manager.py`
- `python/app_state.py`
- `python/runtime_config.py`
- `python/web_server.py`
- `python/led_matrix_visualizer.py`
- `python/led_matrix_transport.py`

Hallazgos principales:

- `python/eeg_contract.py` centraliza el contrato EEG: `FS_HZ=250`, `NUM_CH=4`, `BLOCK_SAMPLES=8`, `STATUS_PREFIX=0xC00000`, `LSB_V=2.235e-8`.
- `backend_service.py` registra `linux_started` y `eeg_block_uV`.
- `FEATURE_WINDOW_SEC=4.0` y `FEATURE_HOP_SAMPLES=64`.
- El backend mantiene `CaptureManager` integrado.
- El snapshot contiene `config`, `status`, `rx`, `features`, `diagnostics`, `spectral_quality`, `capture`, `sonification`, `music`, `midi`, `led_matrix`, `performance`, `errors`.
- `sonification_features.py` ya expone nombres reportables nuevos: `alpha_drive`, `beta_gamma_drive`, `rms_beta_activity`, `band_driven_density`, `spectral_register`, `alpha_stability`, `rms_band_velocity`, `band_note_probability`.
- Los nombres antiguos (`activity`, `calmness`, `tension`, etc.) existen como alias internos de solo lectura.

### 2.8 WebUI revisada

Revisado:

- `python/web_server.py`
- `assets/index.html`
- `assets/app.js`
- `assets/styles.css`

Hallazgos principales:

- La UI real no es Streamlit.
- `web_server.py` usa `arduino.app_bricks.web_ui.WebUI`.
- Rutas confirmadas: `/status`, `/latest`, `/midi/panic`, `/midi/test-*`, `/music/config`, `/music/scale/{key}`, `/music/root/{note}`, `/music/main/{note}`.
- `assets/index.html` muestra controles reportables nuevos de sonificacion y controles musicales root/main/scale.
- El piano roll live sigue basado en `music.recent_notes`.

## 3. Fase 2 - Verificacion del estado real final-v4

| Elemento | Estado esperado | Estado encontrado | Documento/codigo relacionado | Accion para fase 3 |
| --- | --- | --- | --- | --- |
| Rama base | `firmware-final-v4` como estado integrado | Confirmado como base de esta auditoria | ramas remotas creadas en conversacion previa | Mantener como rama congelada integrada |
| Rama de trabajo | Crear rama documental sin refactor | Creada `refactor/essential-eeg-midi-plan` | GitHub branch | Continuar fase 3 aqui |
| Documento final-v4 | Deberia existir `docs/configuracion_final_v4.md` | No existe todavia | `docs/configuracion_final_v3.md` existe | Crear en fase 3 con supervision |
| Documento final-v3 | Debe quedar historico o migrado | Existe y sigue diciendo `Configuracion final v3` | `docs/configuracion_final_v3.md` | Decidir si actualizar, duplicar o marcar historico |
| Arquitectura EEG-MIDI | ADS1299 -> MCU -> Bridge -> Python -> DSP -> sonificacion -> MIDI | Confirmada | `AGENTS.md`, `backend_service.py`, `sketch.ino` | Actualizar narrativa a final-v4 |
| ADS1299 | ADS1299-4PAG / 4 canales por contrato | Confirmado por `NUM_CH=4` y `ADS1299Plus::NUM_CHANNELS==4` | `eeg_contract.py`, `sketch.ino` | Mantener contrato en docs |
| Modo ADS | Captura final usa CH1-only con BIAS | `ADS_DIAGNOSTIC_MODE=5` por defecto | `sketch.ino` | Documentar riesgo: CH2-CH4 no son EEG activo |
| Canales transmitidos | 4 columnas por compatibilidad | Confirmado | `streaming.h`, `eeg_contract.py` | Explicar CH2-CH4 como contrato, no evidencia EEG |
| Frecuencia | 250 Hz | Confirmado `FS_HZ=250` en Python y `250.0f` en firmware | `eeg_contract.py`, `sketch.ino` | Mantener |
| Bloques | 8 muestras | Confirmado `BLOCK_SAMPLES=8` | `streaming.h`, `eeg_contract.py` | Mantener |
| Status ADS | Prefijo `0xC00000` con mascara `0xF00000` | Confirmado | `eeg_contract.py` | Mantener |
| Streaming MCU-Python | `Bridge.notify("eeg_block_uV")` | Confirmado | `streaming.h` | Mantener como contrato intocable |
| Parser Python | Parser centralizado | Confirmado en `parse_eeg_block_values` | `eeg_contract.py` | Mantener |
| Handshake | `linux_started` | Confirmado | `backend_service.py`, `sketch.ino` | Mantener |
| Backend | Orquestador unico | Confirmado | `backend_service.py` | En propuesta UML, separar logicamente sin mover aun |
| Feature window | 4.0 s | Confirmado | `backend_service.py` | Mantener |
| Feature hop | 64 muestras | Confirmado | `backend_service.py` | Mantener |
| Presupuesto Python | 256 ms | Confirmado documentalmente | `09_benchmarks_rendimiento_placa.md` | Mantener |
| Presupuesto MCU | 32 ms por bloque | Confirmado documentalmente | `09_benchmarks_rendimiento_placa.md` | Mantener |
| DSP | Multitaper y bandpowers | Confirmado | `dsp_core.py`, docs auditoria | Mantener |
| Quality gate | `compute_spectral_quality` | Confirmado | `backend_service.py`, `spectral_quality.py` | Mantener como esencial |
| Sonificacion nombres nuevos | Nombres reportables nuevos | Confirmado en `sonification_features.py` y WebUI | `sonification_features.py`, `assets/index.html` | Actualizar docs que sigan con nombres legacy |
| Alias legacy | Deben existir solo como compatibilidad interna | Confirmado | `sonification_features.py` | No borrar aun |
| WebUI | HTML/CSS/JS con WebUI Brick, no Streamlit | Confirmado | `web_server.py`, `assets/index.html` | Corregir docs obsoletos si los hay |
| Controles WebUI | Root, main, scale, panic | Confirmado | `web_server.py`, `assets/index.html` | Mantener como controles minimos |
| MIDI fisico | Serial1/D1 con TX invertido | Confirmado | `sketch.ino`, docs v3 | Mantener como critico |
| MIDI handler | `midi_bytes` | Confirmado | `sketch.ino`, `midi_byte_transport.py` | Mantener contrato |
| MIDI panic | Endpoint y backend | Confirmado | `web_server.py`, `backend_service.py` | Mantener |
| LED matrix | Desactivada por defecto | Confirmado `LED_MATRIX_ENABLED=0` y env Python | `sketch.ino`, backend | Documentar como secundario |
| Benchmarks reales | Integrados | Confirmado | `docs/validacion_tfg/09_benchmarks_rendimiento_placa.md`, `benchmarks/` | Actualizar rama de contexto a final-v4 sin perder historial |
| Capturas finales | Integradas | Confirmado | `docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md`, `captures/capturas finales/` | Mantener y organizar con supervision |
| Resultados laboratorio | Integrados | Confirmado | `docs/validacion_tfg/10_resultados_captura_final_laboratorio.md` | Actualizar referencia de rama/commit en fase 3 |
| Herramientas offline | Presentes | Confirmado | `python/tools/`, `benchmarks/` | No borrar; marcar como validacion/offline en version esencial |

## 4. Incoherencias detectadas para fase 3

Estas incoherencias no se han corregido todavia. Se dejan preparadas para revisarlas punto por punto.

### 4.1 `docs/configuracion_final_v4.md` no existe

La rama integrada actual es `firmware-final-v4`, pero el resumen principal sigue siendo `docs/configuracion_final_v3.md`.

Accion sugerida en fase 3:

- Crear `docs/configuracion_final_v4.md`.
- Mantener `docs/configuracion_final_v3.md` como historico o marcarlo como reemplazado.

### 4.2 Referencias de rama antiguas en documentos de resultados

Documentos afectados:

- `docs/validacion_tfg/09_benchmarks_rendimiento_placa.md` referencia `docs/final-v3-audit-update` como rama de ejecucion.
- `docs/validacion_tfg/10_resultados_captura_final_laboratorio.md` referencia `docs/capture-protocol` como rama de captura.

Interpretacion:

- Esas referencias son correctas como procedencia historica.
- Pero en final-v4 deben contextualizarse como artefactos integrados dentro de `firmware-final-v4`.

Accion sugerida:

- No borrar la procedencia.
- AÃ±adir una nota de integracion final-v4.

### 4.3 Nombres de sonificacion legacy vs nombres reportables

Estado real del codigo:

- Publicos/reportables: `alpha_drive`, `beta_gamma_drive`, `rms_beta_activity`, `band_driven_density`, `spectral_register`, `alpha_stability`, `rms_band_velocity`, `band_note_probability`.
- Legacy internos: `activity`, `calmness`, `tension`, `rhythmic_density`, `register`, `harmonic_stability`, `velocity_factor`, `note_probability` como alias.

Documentos afectados:

- Algunos documentos de benchmarks todavia mencionan nombres legacy como estado del informe.
- Documentos de capturas ya usan nombres reportables nuevos.

Accion sugerida:

- En fase 3, al actualizar docs, distinguir claramente entre:
  - contrato publico final-v4;
  - alias internos para compatibilidad;
  - terminologia historica de resultados previos.

### 4.4 AGENTS.md contiene lenguaje historico

`AGENTS.md` sigue hablando de futura generacion MIDI y dashboard web en terminos anteriores.

Accion sugerida:

- Actualizarlo con cuidado solo si se decide que `AGENTS.md` debe reflejar final-v4.
- No cambiar reglas tecnicas de pines/contratos sin validacion.

### 4.5 Comentario de firmware sobre `ADS_DIAGNOSTIC_MODE=0`

En `sketch.ino` el comentario dice mantener en 0 para capturas reales, pero el valor por defecto actual es 5.

Interpretacion:

- El comentario es historico/general.
- El estado final de capturas usa modo 5: CH1-only con BIAS y CH2-CH4 apagados.

Accion sugerida:

- En fase 3, documentar la diferencia entre modo real general y modo final de captura usado para el TFG.
- No cambiar el firmware sin placa.

## 5. Componentes esenciales detectados para futura version UML

La version esencial futura deberia representar solo el flujo principal, pero sin eliminar aun herramientas ni artefactos.

### 5.1 Firmware esencial

- `sketch/sketch.ino`
- `sketch/streaming.h`
- `sketch/filters.h`
- `sketch/ADS1299Plus/`
- `sketch/ADS1299_SafeSPI/`
- `sketch/sketch.yaml`

### 5.2 Python runtime esencial

- `python/main.py`
- `python/backend_service.py`
- `python/receiver.py`
- `python/eeg_contract.py`
- `python/eeg_signal_processor.py`
- `python/dsp_core.py`
- `python/spectral_quality.py`
- `python/sonification_features.py`
- `python/music_segment.py`
- `python/music_bar.py`
- `python/music_note.py`
- `python/music_utils.py`
- `python/scale_registry.py`
- `python/midi_live.py`
- `python/midi_byte_transport.py`
- `python/app_state.py`
- `python/runtime_config.py`
- `python/web_server.py`

### 5.3 WebUI esencial

- `assets/index.html`
- `assets/app.js`
- `assets/styles.css`

### 5.4 Secundario/no principal para UML, pero no borrar todavia

- `benchmarks/`
- `captures/`
- `docs/validacion_tfg/reportajes_*`
- `docs/validacion_tfg/figures/`
- `python/tools/`
- `python/capture_manager.py`
- `python/led_matrix_visualizer.py`
- `python/led_matrix_transport.py`

Nota: `capture_manager.py` y LED estan integrados en `backend_service.py`, asi que aunque no sean el centro del diagrama UML principal, no deben eliminarse sin plan de separacion y pruebas.

## 6. Contratos intocables identificados

- `Bridge.notify("eeg_block_uV")`
- `Bridge.call("midi_bytes", n, b0, b1, b2)`
- `Bridge.call("led_matrix_row", row_idx, chunk0, chunk1, chunk2)`
- `FS_HZ=250`
- `NUM_CH=4`
- `BLOCK_SAMPLES=8`
- `STATUS_PREFIX=0xC00000`
- `STATUS_MASK=0xF00000`
- `LSB_V=2.235e-8`
- CSV de capturas con `sample_idx`, `status`, `ch1_uV..ch4_uV`
- Snapshot con `config/status/rx/features/diagnostics/spectral_quality/capture/sonification/music/midi/led_matrix/performance/errors`
- `music.recent_notes`
- Endpoints `/latest`, `/status`, `/midi/panic`, `/music/*`

## 7. Proxima fase recomendada

La fase 3 debe hacerse con supervision y en este orden:

1. Decidir estrategia documental general.
2. Crear `docs/configuracion_final_v4.md`.
3. Decidir si `docs/configuracion_final_v3.md` queda como historico o se actualiza.
4. Actualizar referencias de ramas antiguas sin perder trazabilidad.
5. Normalizar nombres de sonificacion en documentos.
6. Revisar `docs/README.md` como indice.
7. Revisar auditorias detalladas solo despues de decidir estructura.
8. No tocar codigo runtime ni firmware.

## 8. Estado final de esta auditoria

Completado:

- Fase 1: lectura y contraste de documentos/codigo clave.
- Fase 2: verificacion del estado real final-v4.
- Rama documental creada: `refactor/essential-eeg-midi-plan`.
- Documento creado: `docs/00_entrada_tfg/00_entrada_tfg/auditoria_final_v4_fase1_2.md`.

No realizado:

- No se ha iniciado fase 3.
- No se ha reorganizado documentacion.
- No se ha creado `docs/configuracion_final_v4.md`.
- No se ha creado `docs/propuesta_version_esencial_uml.md`.
- No se ha tocado firmware.
- No se ha tocado runtime Python.
- No se ha tocado WebUI.
- No se han tocado capturas, benchmarks, reports ni figuras.





