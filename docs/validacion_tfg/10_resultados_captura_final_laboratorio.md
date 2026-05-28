# Resultados de captura final EEG-MIDI en laboratorio

## 1. Objetivo

El objetivo de esta sesión fue documentar una adquisición real completa del sistema EEG-MIDI en laboratorio, registrando de forma conjunta:

- señal EEG adquirida desde ADS1299 y almacenada en CSV;
- metadatos de captura;
- métricas de calidad y validación espectral offline;
- controles de sonificación derivados de features EEG;
- snapshots musicales durante la captura;
- notas musicales generadas durante la sesión.

La sesión se reporta como **evidencia técnica final del pipeline EEG-MIDI**, no como validación clínica ni como registro EEG limpio ideal. La señal real presenta periodos útiles y periodos contaminados por artefactos. Esto debe explicarse explícitamente en el TFG: el sistema adquirió datos reales y generó sonificación coherente durante la sesión, pero la calidad fisiológica de la EEG estuvo condicionada por ruido de red, contacto/electrodos y artefactos fisiológicos o externos.

## 2. Configuración congelada

| Campo | Valor |
| --- | --- |
| Repositorio | `valtorresm97/VICTOR-TFG` |
| Rama | `docs/capture-protocol` |
| Commit de referencia | `bb02e3123309bf712346454c3c9e07fe7c8d1c3e` |
| Sujeto anónimo | `s01` |
| Fecha de sesión | `20260528` |
| Montaje | `ear_eeg_ch1_only` |
| Modo ADS | `bias_ch1_only_loff_off` |
| Modelo musical | `modelo_captura_final` |
| Carpeta de capturas | `captures/capturas finales` |

El modo de adquisición usado corresponde a CH1 activo con montaje ear EEG, BIAS derivado de CH1P/CH1N y lead-off desactivado. CH2-CH4 no se interpretan como EEG principal en esta sesión.

## 3. Condiciones presentes en la sesión

El listado final contiene siete carpetas de captura. Hay dos prechecks y no aparece una carpeta `05_jaw_artifact_30s` en la salida revisada. Por tanto, el resumen oficial se centra en las condiciones efectivamente presentes:

| Orden | Condición | Duración nominal | Carpeta |
| --- | --- | ---: | --- |
| 00 | `precheck_10s` | 10 s | `20260528-144607_s01_20260528_ear_eeg_ch1_only_00_precheck_10s` |
| 00 | `precheck_10s` | 10 s | `20260528-144705_s01_20260528_ear_eeg_ch1_only_00_precheck_10s` |
| 01 | `eyes_open_rest_60s` | 60 s | `20260528-145041_s01_20260528_ear_eeg_ch1_only_01_eyes_open_rest_60s` |
| 02 | `eyes_closed_rest_60s` | 60 s | `20260528-145251_s01_20260528_ear_eeg_ch1_only_02_eyes_closed_rest_60s` |
| 03 | `quiet_rest_60s` | 60 s | `20260528-145448_s01_20260528_ear_eeg_ch1_only_03_quiet_rest_60s` |
| 04 | `blink_artifact_30s` | 30 s | `20260528-145635_s01_20260528_ear_eeg_ch1_only_04_blink_artifact_30s` |
| 06 | `eyes_open_repeat_30s` | 30 s | `20260528-145809_s01_20260528_ear_eeg_ch1_only_06_eyes_open_repeat_30s` |

No se añade captura extra de movimiento corporal a esta sesión.

## 4. Resultado técnico de adquisición

Todas las capturas revisadas muestran estabilidad temporal del flujo de adquisición:

| Condición | Frecuencia efectiva | Sample gaps | Invalid status | Lectura técnica |
| --- | ---: | ---: | ---: | --- |
| `00_precheck_10s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `00_precheck_10s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `01_eyes_open_rest_60s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `02_eyes_closed_rest_60s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `03_quiet_rest_60s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `04_blink_artifact_30s` | 250.00 Hz | 0 | 0 | Transporte estable |
| `06_eyes_open_repeat_30s` | 250.00 Hz | 0 | 0 | Transporte estable |

Esto valida la ruta técnica:

```text
ADS1299 -> MCU -> Bridge -> Python -> CSV -> tools offline
```

La sesión demuestra que el sistema es capaz de sostener la adquisición real a 250 Hz sin pérdidas de muestras ni estados ADS inválidos durante las condiciones registradas.

## 5. Calidad fisiológica y artefactos

La sesión debe interpretarse con cautela desde el punto de vista fisiológico. El hecho de que el sistema capture correctamente no implica que toda la señal sea EEG limpia. La mayoría de condiciones fueron etiquetadas como `dudosa` por los reports automáticos, aunque esto no invalida la sesión como evidencia de integración.

| Condición | Diagnóstico | RMS global (uV) | PTP global (uV) | 50 Hz ratio | Artifact fraction | Lectura |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `00_precheck_10s` 144607 | `dudosa` | 29.808 | 408 | 0.328539 | 0 | Ruido de red apreciable, amplitud contenida. |
| `00_precheck_10s` 144705 | `dudosa` | 37.4595 | 559 | 0.342103 | 0 | Segundo precheck con ruido de red apreciable. |
| `01_eyes_open_rest_60s` | `dudosa` | 2199.4 | 107661 | 0.000435 | 0.125 | Artefacto transitorio de gran amplitud; no representar como EEG limpio continuo. |
| `02_eyes_closed_rest_60s` | `dudosa` | 58.3981 | 1004 | 0.363277 | 0 | Señal temporalmente estable pero con componente de 50 Hz. |
| `03_quiet_rest_60s` | `dudosa` | 82.7559 | 1168 | 0.338669 | 0.0178571 | Reposo con ruido/artefacto moderado. |
| `04_blink_artifact_30s` | `dudosa` | 67.1179 | 1025 | 0.381423 | 0 | Condición útil como control de artefacto por parpadeo. |
| `06_eyes_open_repeat_30s` | `valida_preliminar` | 1870.1 | 120313 | 0.00138669 | 0.037037 | Mejor diagnóstico automático; contiene eventos transitorios, pero muchas ventanas presentan valores normales. |

La lectura correcta para el TFG es:

- el EEG real no es completamente limpio;
- hay tramos con valores fisiológicamente plausibles, especialmente en ventanas concretas;
- hay artefactos electrónicos externos, como ruido de red a 50 Hz;
- hay artefactos fisiológicos internos, como parpadeo, movimiento/contacto o actividad muscular;
- la sonificación se obtuvo en la mayoría de condiciones porque el pipeline musical se mantuvo activo y registró notas durante la adquisición.

## 6. Datos musicales registrados

Todas las capturas contienen `music_snapshots.jsonl`, `music_notes.csv` y `music_capture_summary.json`. Esto permite analizar a posteriori la relación entre señal, features, controles de sonificación y notas generadas.

| Condición | Snapshots musicales | Snapshots con notas | Notas deduplicadas |
| --- | ---: | ---: | ---: |
| `00_precheck_10s` 144607 | 24 | 24 | 12 |
| `00_precheck_10s` 144705 | 24 | 24 | 22 |
| `01_eyes_open_rest_60s` | 121 | 121 | 45 |
| `02_eyes_closed_rest_60s` | 121 | 121 | 80 |
| `03_quiet_rest_60s` | 121 | 121 | 72 |
| `04_blink_artifact_30s` | 62 | 62 | 34 |
| `06_eyes_open_repeat_30s` | 62 | 62 | 65 |

La diferencia en número de notas entre condiciones no debe interpretarse como una conclusión neurofisiológica directa sin control adicional, pero sí sirve como evidencia de que la sonificación funcionó durante capturas reales y quedó persistida para análisis posterior.

## 7. Controles reportables de sonificación

Los reports offline muestran los nombres de contrato corregidos para el TFG:

- `alpha_drive`
- `beta_gamma_drive`
- `rms_beta_activity`
- `band_driven_density`
- `spectral_register`
- `alpha_stability`
- `rms_band_velocity`
- `band_note_probability`

Estos campos sustituyen a nombres abstractos heredados como `calmness`, `tension` o `activity`. La ventaja es que el texto del TFG puede defender el mapeo desde variables EEG espectrales y de amplitud, no desde categorías musicales ambiguas.

## 8. Uso recomendado de cada condición en el TFG

| Condición | Uso recomendado |
| --- | --- |
| `00_precheck_10s` | Documentar como comprobación técnica breve, sin análisis fisiológico profundo. |
| `01_eyes_open_rest_60s` | Útil para mostrar captura real con artefacto transitorio; no usar como ejemplo principal de señal limpia. |
| `02_eyes_closed_rest_60s` | Útil para comparar condición de reposo, señal estable pero contaminada por 50 Hz. |
| `03_quiet_rest_60s` | Útil como reposo general y para analizar sonificación real durante estado quieto. |
| `04_blink_artifact_30s` | Útil como condición de artefacto fisiológico controlado. |
| `06_eyes_open_repeat_30s` | Mejor candidata para figura principal combinada EEG + sonificación + notas. |

## 9. Decisión final de validez

```text
Validez técnica: alta.
Validez para demostrar integración EEG-MIDI: alta.
Validez fisiológica como EEG limpio: parcial.
```

La sesión debe reportarse como una sesión real de laboratorio que valida el funcionamiento del sistema completo, pero reconociendo explícitamente que la señal EEG contiene artefactos y ruido. La contribución principal de esta sesión es demostrar que el sistema puede:

1. adquirir señal real a 250 Hz;
2. mantener continuidad temporal sin gaps;
3. validar status ADS1299 sin errores;
4. calcular features espectrales;
5. generar controles de sonificación reportables;
6. producir y registrar notas musicales durante la adquisición;
7. guardar todos los artefactos necesarios para análisis y representación posterior.

## 10. Próximo paso documental

A partir de este resumen global se generarán documentos específicos por captura, con figuras asociadas:

- señal EEG temporal CH1;
- bandpowers relativos por ventana;
- controles de sonificación por ventana;
- notas musicales / piano roll offline;
- figura combinada EEG + sonificación + música.

Los prechecks se documentarán de forma breve. Las condiciones `01`, `02`, `03`, `04` y `06` tendrán documentación más detallada, porque son las condiciones reportables de la sesión.
