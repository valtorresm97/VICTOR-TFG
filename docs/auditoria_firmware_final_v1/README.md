# Auditoria firmware-final-v1 reajustada a final-v4

## Objetivo

Este directorio nacio como una auditoria de la rama `firmware-final-v1`, pero se conserva porque contiene una vision transversal util del sistema: firmware, ADS1299, Bridge, backend Python, DSP, sonificacion, MIDI live, WebUI, LED matrix, herramientas, capturas, configuraciones, redundancias, controles faltantes y criticidad.

Estado actual de lectura:

```text
Rama integrada actual: firmware-final-v4
Rama documental actual: refactor/essential-eeg-midi-plan
```

La auditoria detallada principal final-v4 esta ahora en:

```text
docs/auditoria_codigo_detallada/
```

Por tanto, esta carpeta debe tratarse como una segunda capa de auditoria transversal/historica que se va a reajustar para no contradecir final-v4. No sustituye a:

```text
docs/configuracion_final_v4.md
docs/auditoria_codigo_detallada/09_mapa_contratos_entre_modulos.md
docs/auditoria_codigo_detallada/10_mapa_funciones_criticas.md
docs/auditoria_codigo_detallada/11_hallazgos_para_simplificacion_futura.md
```

## Criterio de reajuste final-v4

Al revisar esta carpeta, aplicar estas reglas:

1. Cambiar referencias a `final-v3` como estado principal por `firmware-final-v4`.
2. Mantener la procedencia historica `firmware-final-v1` solo como contexto.
3. No duplicar en exceso lo ya consolidado en `auditoria_codigo_detallada/`.
4. Actualizar el modo final de capturas:

```text
ADS_DIAGNOSTIC_MODE=5
ADS_MODE=bias_ch1_only_loff_off
montage=ear_eeg_ch1_only
CH1 = canal EEG principal
CH2-CH4 = apagados/conservados por contrato, no interpretados como EEG activo
```

5. Mantener como esenciales:

```text
eeg_block_uV
compute_live_features
SignalQuality / QualityGate
SonificationFeatureAdapter
MidiScheduler
MidiByteTransport
midi_bytes
Serial1/D1 con TX invertido
/midi/panic
/music/config o controles root/main/scale
```

6. Marcar como laterales u offline:

```text
CaptureManager
capture_eeg_quality.py
final_capture_session.py
validate_spectral_features.py
benchmarks/
LED matrix
tools de figuras/reportajes
```

7. Marcar como compatibilidad/historico:

```text
eeg_frame_uV
compute_online_features
generate_bars
generate_notes_for_segment
aliases legacy de sonificacion
comentarios antiguos sobre MIDI futuro/D1/handler
```

## Relacion con la auditoria detallada final-v4

La carpeta `auditoria_codigo_detallada/` ya contiene la revision final-v4 funcion por funcion. Esta carpeta se revisara despues como auditoria transversal para:

- eliminar contradicciones;
- compactar duplicados;
- mantener lo que aporte vision global;
- mover a historico lo que ya este sustituido;
- preparar la futura version esencial/UML.

## Documentos de esta carpeta

| Documento | Contenido | Accion final-v4 recomendada |
| --- | --- | --- |
| `00_inventario_proyecto.md` | Inventario por archivo/familias y capturas. | Actualizar o marcar como resumen transversal si no duplica `00_inventario_actual.md`. |
| `01_arquitectura_global.md` | Flujos end-to-end real, offline, UI, MIDI y LED. | Reajustar a flujo final-v4 y preparar como base de UML. |
| `02_auditoria_firmware_mcu.md` | Firmware, ADS1299, pines, funciones criticas y riesgos. | Alinear con `01_firmware_funcion_por_funcion.md` y `02_ads1299_spi_driver.md`. |
| `03_auditoria_python_backend.md` | Backend, receiver, buffer, snapshot, capture manager. | Alinear con `03_python_backend_funcion_por_funcion.md`. |
| `04_auditoria_dsp_features.md` | DSP, multitaper, bandpowers, quality gate y controles. | Alinear con `04_dsp_eeg_funcion_por_funcion.md`; excluir `compute_online_features` del UML principal. |
| `05_auditoria_sonificacion_midi.md` | Segmentos, barras, notas, scheduler, transporte MIDI. | Alinear con nombres final-v4 y contrato `midi_bytes`. |
| `06_auditoria_led_matrix_scroll.md` | LED matrix 13x8, mapeo, transporte y limites. | Marcar como subsistema lateral/desactivado por defecto. |
| `07_auditoria_web_ui.md` | WebUI, paneles, claves snapshot y riesgos. | Revisar con especial cuidado; hacerla comprensible para TFG sin perder fluidez. |
| `08_auditoria_tools_capturas_docs.md` | Tools CLI, capturas, reports y docs existentes. | Separar tools offline/control de captura del runtime esencial. |
| `09_mapa_configuraciones.md` | Flags/macro/env enabled/disabled. | Actualizar defaults final-v4: MIDI activo, LED desactivado, ADS mode 5. |
| `10_redundancias_y_deuda_tecnica.md` | Duplicaciones y deuda para refactor futuro. | Fusionar criterios con `11_hallazgos_para_simplificacion_futura.md`. |
| `11_controles_faltantes_y_riesgos.md` | Controles que faltan por subsistema. | Revisar porque algunos controles ya existen en final-v4, especialmente WebUI root/main/scale y panic MIDI. |
| `12_mapa_criticidad_refactor.md` | Que tocar y que no tocar sin pruebas. | Alinear con `10_mapa_funciones_criticas.md`. |

## Riesgos principales actualizados antes de simplificar

- Contrato `eeg_block_uV` manual y critico.
- Constantes compartidas firmware/Python/tools: `FS_HZ`, `NUM_CH`, `BLOCK_SAMPLES`, `LSB_V`, status ADS.
- `ADS_DIAGNOSTIC_MODE=5` puede confundirse con adquisicion EEG multicanal; documentar siempre CH1-only.
- `Serial1`/D1 con `USART_CR2_TXINV` es obligatorio para MIDI OUT fisico validado.
- `compute_quality_diagnostics()` y `compute_spectral_quality()` deben conservarse como `SignalQuality / QualityGate`.
- `backend_service.py` concentra demasiadas responsabilidades.
- `assets/app.js` concentra mucho contrato de snapshot y debe simplificarse con cuidado.
- Tools offline y benchmarks no entran en UML principal, pero no deben borrarse porque sostienen la validacion TFG.
- LED matrix esta desactivada por defecto y no forma parte del flujo EEG->MIDI principal.
- Hay comentarios historicos que deben limpiarse en la futura rama simplificada.

## Orden recomendado desde este punto

1. Revisar `00_inventario_proyecto.md` y decidir si se actualiza o se marca como sustituido por `auditoria_codigo_detallada/00_inventario_actual.md`.
2. Revisar `01_arquitectura_global.md` como posible base directa de `docs/propuesta_version_esencial_uml.md`.
3. Reajustar `02` a `08` solo si aportan una vision transversal distinta a la auditoria detallada.
4. Revisar `09_mapa_configuraciones.md` porque puede contener defaults obsoletos.
5. Revisar `10`, `11` y `12` contra los documentos ya actualizados de simplificacion futura.
6. Si un documento queda totalmente duplicado, no borrarlo de entrada: moverlo o marcarlo como historico/sustituido.

## Regla final

Esta carpeta se conserva porque ayuda a entender la evolucion de `firmware-final-v1` a `firmware-final-v4`, pero el estado tecnico actual debe prevalecer en:

```text
docs/configuracion_final_v4.md
docs/auditoria_codigo_detallada/
docs/validacion_tfg/
```
