# 10. Resultados de captura final EEG-MIDI en laboratorio - final-v4

## 1. Objetivo

El objetivo de esta sesion fue documentar una adquisicion real completa del sistema EEG-MIDI en laboratorio, registrando de forma conjunta:

- senal EEG adquirida desde ADS1299 y almacenada en CSV;
- metadatos de captura;
- metricas de calidad y validacion espectral offline;
- controles de sonificacion derivados de features EEG;
- snapshots musicales durante la captura;
- notas musicales generadas durante la sesion.

La sesion se reporta como **evidencia tecnica final del pipeline EEG-MIDI**, no como validacion clinica ni como registro EEG limpio ideal. La senal real presenta periodos utiles y periodos contaminados por artefactos. Esto debe explicarse explicitamente en el TFG: el sistema adquirio datos reales y genero sonificacion coherente durante la sesion, pero la calidad fisiologica de la EEG estuvo condicionada por ruido de red, contacto/electrodos y artefactos fisiologicos o externos.

Este documento pertenece al bloque de validacion final-v4. La sesion se genero originalmente en la rama `docs/capture-protocol`, y sus artefactos se integran ahora como parte de la documentacion final de `firmware-final-v4`.

## 2. Configuracion congelada

| Campo | Valor |
| --- | --- |
| Repositorio | `valtorresm97/VICTOR-TFG` |
| Rama original de captura | `docs/capture-protocol` |
| Commit original de referencia | `bb02e3123309bf712346454c3c9e07fe7c8d1c3e` |
| Rama documental actual | `refactor/essential-eeg-midi-plan` |
| Estado integrado de referencia | `firmware-final-v4` |
| Sujeto anonimo | `s01` |
| Fecha de sesion | `20260528` |
| Montaje | `ear_eeg_ch1_only` |
| Modo ADS | `bias_ch1_only_loff_off` |
| `ADS_DIAGNOSTIC_MODE` | `5` |
| Modelo musical | `modelo_captura_final` |
| Carpeta de capturas | `captures/capturas finales` |

El modo de adquisicion usado corresponde a CH1 activo con montaje ear EEG, BIAS derivado de CH1P/CH1N y lead-off desactivado. CH2-CH4 se conservan en el contrato de datos del sistema, pero no se interpretan como EEG principal en esta sesion.

## 3. Condiciones presentes en la sesion

El listado final contiene siete carpetas de captura. Hay dos prechecks y no aparece una carpeta `05_jaw_artifact_30s` en la salida revisada. Por tanto, el resumen oficial se centra en las condiciones efectivamente presentes:

| Orden | Condicion | Duracion nominal | Carpeta |
| --- | --- | ---: | --- |
| 00 | `precheck_10s` | 10 s | `20260528-144607_s01_20260528_ear_eeg_ch1_only_00_precheck_10s` |
| 00 | `precheck_10s` | 10 s | `20260528-144705_s01_20260528_ear_eeg_ch1_only_00_precheck_10s` |
| 01 | `eyes_open_rest_60s` | 60 s | `20260528-145041_s01_20260528_ear_eeg_ch1_only_01_eyes_open_rest_60s` |
| 02 | `eyes_closed_rest_60s` | 60 s | `20260528-145251_s01_20260528_ear_eeg_ch1_only_02_eyes_closed_rest_60s` |
| 03 | `quiet_rest_60s` | 60 s | `20260528-145448_s01_20260528_ear_eeg_ch1_only_03_quiet_rest_60s` |
| 04 | `blink_artifact_30s` | 30 s | `20260528-145635_s01_20260528_ear_eeg_ch1_only_04_blink_artifact_30s` |
| 06 | `eyes_open_repeat_30s` | 30 s | `20260528-145809_s01_20260528_ear_eeg_ch1_only_06_eyes_open_repeat_30s` |

No se anade captura extra de movimiento corporal a esta sesion.

## 4. Resultado tecnico de adquisicion

Todas las capturas revisadas muestran estabilidad temporal del flujo de adquisicion:

| Condicion | Frecuencia efectiva | Sample gaps | Invalid status | Lectura tecnica |
| --- | ---: | ---: | ---: | --- |
| `00_precheck_10s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `00_precheck_10s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `01_eyes_open_rest_60s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `02_eyes_closed_rest_60s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `03_quiet_rest_60s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `04_blink_artifact_30s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `06_eyes_open_repeat_30s` | 250.00 Hz | 0 | 0 | Transporte estable |

Esto valida la ruta tecnica:

```text
ADS1299 -> MCU -> Bridge -> Python -> CSV -> tools offline
```

La sesion demuestra que el sistema es capaz de sostener la adquisicion real a 250 Hz sin perdidas de muestras ni estados ADS invalidos durante las condiciones registradas.

## 5. Calidad fisiologica y artefactos

La sesion debe interpretarse con cautela desde el punto de vista fisiologico. El hecho de que el sistema capture correctamente no implica que toda la senal sea EEG limpia. La mayoria de condiciones fueron etiquetadas como `dudosa` por los reports automaticos, aunque esto no invalida la sesion como evidencia de integracion.

| Condicion | Diagnostico | RMS global (uV) | PTP global (uV) | 50 Hz ratio | Artifact fraction | Lectura |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `00_precheck_10s` 144607 | `dudosa` | 29.808 | 408 | 0.328539 | 0 | Ruido de red apreciable, amplitud contenida. |
| `00_precheck_10s` 144705 | `dudosa` | 37.4595 | 559 | 0.342103 | 0 | Segundo precheck con ruido de red apreciable. |
| `01_eyes_open_rest_60s` | `dudosa` | 2199.4 | 107661 | 0.000435 | 0.125 | Artefacto transitorio de gran amplitud; no representar como EEG limpio continuo. |
| `02_eyes_closed_rest_60s` | `dudosa` | 58.3981 | 1004 | 0.363277 | 0 | Senal temporalmente estable pero con componente de 50 Hz. |
| `03_quiet_rest_60s` | `dudosa` | 82.7559 | 1168 | 0.338669 | 0.0178571 | Reposo con ruido/artefacto moderado. |
| `04_blink_artifact_30s` | `dudosa` | 67.1179 | 1025 | 0.381423 | 0 | Condicion util como control de artefacto por parpadeo. |
| `06_eyes_open_repeat_30s` | `valida_preliminar` | 1870.1 | 120313 | 0.00138669 | 0.037037 | Mejor diagnostico automatico; contiene eventos transitorios, pero muchas ventanas presentan valores normales. |

La lectura correcta para el TFG es:

- el EEG real no es completamente limpio;
- hay tramos con valores fisiologicamente plausibles, especialmente en ventanas concretas;
- hay artefactos electronicos externos, como ruido de red a 50 Hz;
- hay artefactos fisiologicos internos, como parpadeo, movimiento/contacto o actividad muscular;
- la sonificacion se obtuvo en la mayoria de condiciones porque el pipeline musical se mantuvo activo y registro notas durante la adquisicion.

## 6. Datos musicales registrados

Todas las capturas contienen `music_snapshots.jsonl`, `music_notes.csv` y `music_capture_summary.json`. Esto permite analizar a posteriori la relacion entre senal, features, controles de sonificacion y notas generadas.

| Condicion | Snapshots musicales | Snapshots con notas | Notas deduplicadas |
| --- | ---: | ---: | ---: |
| `00_precheck_10s` 144607 | 24 | 24 | 12 |
| `00_precheck_10s` 144705 | 24 | 24 | 22 |
| `01_eyes_open_rest_60s` | 121 | 121 | 45 |
| `02_eyes_closed_rest_60s` | 121 | 121 | 80 |
| `03_quiet_rest_60s` | 121 | 121 | 72 |
| `04_blink_artifact_30s` | 62 | 62 | 34 |
| `06_eyes_open_repeat_30s` | 62 | 62 | 65 |

La diferencia en numero de notas entre condiciones no debe interpretarse como una conclusion neurofisiologica directa sin control adicional, pero si sirve como evidencia de que la sonificacion funciono durante capturas reales y quedo persistida para analisis posterior.

## 7. Controles reportables de sonificacion

Los reports offline muestran los nombres de contrato corregidos para el TFG:

- `alpha_drive`
- `beta_gamma_drive`
- `rms_beta_activity`
- `band_driven_density`
- `spectral_register`
- `alpha_stability`
- `rms_band_velocity`
- `band_note_probability`

Estos campos sustituyen a nombres abstractos heredados como `calmness`, `tension` o `activity`. La ventaja es que el texto del TFG puede defender el mapeo desde variables EEG espectrales y de amplitud, no desde categorias musicales ambiguas.

## 8. Uso recomendado de cada condicion en el TFG

| Condicion | Uso recomendado |
| --- | --- |
| `00_precheck_10s` | Documentar como comprobacion tecnica breve, sin analisis fisiologico profundo. |
| `01_eyes_open_rest_60s` | Util para mostrar captura real con artefacto transitorio; no usar como ejemplo principal de senal limpia. |
| `02_eyes_closed_rest_60s` | Util para comparar condicion de reposo, senal estable pero contaminada por 50 Hz. |
| `03_quiet_rest_60s` | Util como reposo general y para analizar sonificacion real durante estado quieto. |
| `04_blink_artifact_30s` | Util como condicion de artefacto fisiologico controlado. |
| `06_eyes_open_repeat_30s` | Mejor candidata para figura principal combinada EEG + sonificacion + notas. |

## 9. Documentos y figuras derivados

A partir de este resumen global ya existen documentos especificos por captura y figuras asociadas. La carpeta principal narrativa para el TFG es:

```text
docs/validacion_tfg/reportajes_capturas_s01_20260528/
```

El reportaje global de sesion es:

```text
docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md
```

Las figuras estandar estan en:

```text
docs/validacion_tfg/figures/capturas_finales_s01_20260528_matplotlib/
```

Las figuras enhanced de la captura 06 estan en:

```text
docs/validacion_tfg/figures/capturas_finales_s01_20260528_enhanced/06_eyes_open_repeat_30s/
```

La salida automatica auxiliar esta en:

```text
docs/validacion_tfg/capturas_finales_s01_20260528_matplotlib/
```

El orden recomendado de lectura es:

```text
10_resultados_captura_final_laboratorio.md
reportaje_sesion_final_s01_20260528.md
reportajes_capturas_s01_20260528/
figures/capturas_finales_s01_20260528_enhanced/06_eyes_open_repeat_30s/
```

## 10. Decision final de validez

```text
Validez tecnica: alta.
Validez para demostrar integracion EEG-MIDI: alta.
Validez fisiologica como EEG limpio: parcial.
```

La sesion debe reportarse como una sesion real de laboratorio que valida el funcionamiento del sistema completo, pero reconociendo explicitamente que la senal EEG contiene artefactos y ruido. La contribucion principal de esta sesion es demostrar que el sistema puede:

1. adquirir senal real a 250 Hz;
2. mantener continuidad temporal sin gaps;
3. validar status ADS1299 sin errores;
4. calcular features espectrales;
5. aplicar quality gate;
6. generar controles de sonificacion reportables;
7. producir y registrar notas musicales durante la adquisicion;
8. guardar todos los artefactos necesarios para analisis y representacion posterior.

## 11. Conclusion para memoria

La sesion `s01_20260528` es defendible como evidencia tecnica final de integracion real del sistema EEG-MIDI. No demuestra una adquisicion EEG clinicamente limpia, pero si demuestra que el sistema completo funciona en condiciones reales:

```text
ADS1299 -> firmware -> Bridge -> Python -> DSP -> quality gate -> sonificacion -> notas MIDI registradas
```

Por tanto, en la memoria debe usarse para defender la integracion hardware/software, la trazabilidad de datos y la persistencia de EEG + musica. La interpretacion neurofisiologica debe formularse con cautela y apoyarse siempre en las metricas de calidad y en la documentacion de artefactos.
