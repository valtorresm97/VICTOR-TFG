# Validacion de bandas EEG para sonificacion

Fecha: 2026-05-24

Rama: `captura-datos`

## 1. Resumen ejecutivo

La fase anterior dejo validada de forma preliminar la adquisicion real:
ADS1299-4PAG detectado, `status=0xC00000`, `sample_idx` sin saltos, frecuencia
efectiva de 250 Hz, ruido interno muy bajo en `shorted_inputs` y mejora clara al
usar BIAS/RLD.

Esta fase se centra en una pregunta diferente: si las bandas EEG que alimentan
la sonificacion son fisiologicamente robustas y utiles.

En la copia local de PC no hay aun carpetas reales de captura: `captures/` solo
contiene `.gitkeep`. Por tanto, esta entrega deja auditado el pipeline y anade
herramientas no invasivas para analizar los CSV reales cuando se suban desde la
placa. Las conclusiones fisiologicas definitivas deben ejecutarse sobre las
carpetas reales completas.

## 2. Que queda validado de la captura anterior

Validado preliminarmente:

- ADS1299 responde con `ID=0x3C`.
- RDATAC y `DRDY` funcionan.
- Frame valido con prefijo `status=0xC00000`.
- 250 Hz efectivos.
- `shorted_inputs` con ruido interno muy bajo.
- `test_signal_internal` estable.
- BIAS/RLD reduce amplitud y ruido de red frente a sin BIAS.
- `bias_ch1_only_loff_off` es la configuracion mas limpia para validacion.
- Montajes ear-EEG y Fp1-Fp2 pueden producir ventanas plausibles si el contacto
  y los cables estan controlados.

No validado aun:

- Robustez fisiologica de alpha/beta/theta/delta/gamma para sonificacion final.
- Alfa ojos cerrados de forma fiable.
- Uso seguro de beta/gamma sin contaminacion EMG.
- Uso de peak frequency como control musical estable.

## 3. Que se valida ahora

Se valida el procesado espectral:

- ventana y hop,
- PSD multitaper,
- bandpowers absolutas y relativas,
- picos por banda,
- estabilidad temporal por ventanas,
- contaminacion por 50 Hz,
- contaminacion por artefactos,
- robustez de features usadas por `sonification_features.py`.

## 4. Auditoria del pipeline espectral

Diagrama real:

```text
eeg_block_uV
   â†“
receiver/backend
   â†“
EEGSignalProcessor.add_block_uV()
   â†“
uV â†’ V
   â†“
ring buffer multicanal
   â†“
ventana temporal reciente, normalmente 4 s
   â†“
DSPCore.compute_features()
   â†“
preprocess: detrend + deteccion/interpolacion de outliers
   â†“
PSD multitaper
   â†“
bandpower_abs / bandpower_rel / peaks
   â†“
SonificationFeatureAdapter
   â†“
activity / calmness / tension / rhythmic_density / register /
harmonic_stability / velocity_factor / note_probability
   â†“
sonificacion
```

Detalles auditados:

| Punto | Estado actual | Evaluacion |
| --- | --- | --- |
| Entrada DSP | `eeg_block_uV` desde Bridge | Correcto |
| Unidad recibida | microvoltios | Correcto |
| Unidad interna Python | voltios (`add_block_uV` multiplica por `1e-6`) | Correcto |
| Filtrado Python | no hay filtros principales adicionales | Correcto para no ocultar adquisicion |
| Filtrado previo | firmware: DC/high-pass, notch 50 Hz, low-pass 40 Hz | Debe recordarse al interpretar gamma/50 Hz |
| Canal live | canal 0 / CH1 | Correcto para CH1-only |
| Frecuencia | `FS_HZ=250` | Coherente con capturas |
| Ventana live | `FEATURE_WINDOW_SEC=4.0` | Adecuada para theta/alpha/beta; limitada para delta baja |
| Hop live | `FEATURE_HOP_SAMPLES=64` | ~0.256 s, buen refresco con alto solape |
| PSD | multitaper | Adecuado |
| Time-bandwidth | `NW=2.5` | Razonable |
| Tapers | `2*NW-1 = 4` | Razonable |
| Resolucion FFT | 250/1000 = 0.25 Hz | Buena para alpha/theta/beta |
| Bandpower abs | integra PSD por banda y reescala a potencia temporal | Util, pero necesita normalizacion por sesion |
| Bandpower rel | cada banda / suma de bandas | Mejor para sonificacion que absolutos |
| Picos por banda | maximo PSD dentro de cada banda | Dudosos en ventanas ruidosas |
| NaN/Inf | `_safe_float` en sonificacion, checks basicos en DSP | Aceptable, mejorable con quality flag |

## 5. Auditoria del metodo multitaper

Multitaper tiene sentido porque reduce leakage y varianza del periodograma en
ventanas cortas, usando varios tapers DPSS en lugar de una sola ventana. Es
preferible a un periodograma simple para estimar bandpowers live con ruido real.

No resuelve:

- mal contacto de electrodos,
- EMG de mandibula/frente,
- parpadeos,
- saturacion,
- 50 Hz fuerte,
- drift o movimiento de cables,
- una captura no fisiologica.

Tabla de ventanas:

| Ventana | Resolucion aprox | Latencia/respuesta | Bandas afectadas | Uso recomendado |
| --- | ---: | --- | --- | --- |
| 2 s | 0.50 Hz | rapida | alpha/beta bien; delta pobre | UI rapida, deteccion de artefacto |
| 4 s | 0.25 Hz | equilibrada | theta/alpha/beta bien; delta limitada | live sonificacion actual |
| 6 s | 0.17 Hz | mas lenta | mejora delta/theta | validacion offline o controles lentos |
| 8 s | 0.125 Hz | lenta | mejor estabilidad baja frecuencia | analisis offline, no respuesta musical rapida |

ConclusiÃ³n: 4 s es un buen compromiso para sonificacion. Para validar alfa y
bandas lentas conviene comparar tambien 6-8 s offline.

## 6. Definicion de bandas EEG en codigo

Rangos usados en `DSPCore` y herramientas:

| Banda | Rango en codigo | Rango tipico | Adecuada para este sistema | Riesgos |
| --- | ---: | ---: | --- | --- |
| delta | 0.5-4 Hz | 0.5-4 Hz | Solo apoyo | drift, movimiento, parpadeo |
| theta | 4-8 Hz | 4-8 Hz | Solo apoyo | somnolencia vs movimiento/artefacto |
| alpha | 8-13 Hz | 8-13 Hz | Candidata, necesita open/closed robusto | puede no verse en Fp1-Fp2/ear EEG |
| beta | 13-30 Hz | 13-30 Hz | Usar con cautela | EMG frontal/mandibula |
| gamma | 30-50 Hz | >30 Hz | No usar como control principal por ahora | EMG, ruido, low-pass 40 Hz en firmware |

## 7. Analisis de capturas reales

En esta copia local no hay CSV reales. La herramienta creada analizara cada
captura real cuando este disponible:

```bash
python3 python/tools/validate_spectral_features.py captures/
```

Para cada captura genera:

```text
captures/<capture_id>/
  spectral_validation_report.md
  spectral_validation_report.json
  windowed_bandpowers.csv
  windowed_sonification_features.csv
  psd_multitaper.csv
```

Y si se ejecuta sobre `captures/` completo:

```text
captures/comparisons/
  spectral_feature_robustness.md
  spectral_feature_robustness.csv
  spectral_feature_robustness.json
```

Tabla a completar tras subir datos reales:

| Captura | Condicion | Calidad temporal | Calidad espectral | Bandas utiles | Bandas dudosas | Artefactos | Conclusion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pendiente | pendiente de subir CSV | pendiente | pendiente | pendiente | pendiente | pendiente | pendiente |

## 8. Comparacion ojos abiertos vs ojos cerrados

La comparacion global anterior mostro que el alfa no quedaba validado de forma
clara en las capturas pegadas por shell. Esto no invalida la adquisicion:
Fp1-Fp2 y ear-EEG no son montajes occipitales, y pueden no mostrar el aumento
alfa clasico con ojos cerrados.

Criterio final:

- `ALFA VALIDADO`: aumenta `alpha_abs` o `alpha_rel` en ojos cerrados en la
  mayoria de ventanas limpias, con pico alfa 8-13 Hz y sin aumento de artefacto.
- `ALFA DUDOSO`: hay aumento relativo pero no absoluto, o pocas ventanas limpias.
- `ALFA NO VALIDADO`: no aumenta o aumenta junto a artefactos.

Estado actual: `ALFA DUDOSO` hasta analizar CSV completos por ventanas.

## 9. Validacion preliminar de cada banda

| Banda | Estado preliminar | Motivo |
| --- | --- | --- |
| delta | dudosa/apoyo | puede representar drift, parpadeo o movimiento |
| theta | dudosa/apoyo | puede ser util si ventana limpia, pero necesita control de artefacto |
| alpha | candidata | no validada aun por open/closed robusto |
| beta | apoyo con cautela | sensible a EMG frontal/mandibula |
| gamma | no usar por ahora | muy sensible a EMG y limitada por low-pass firmware |

## 10. Validacion de features espectrales

| Feature | Plausibilidad fisiologica | Estabilidad temporal | Sensibilidad a artefactos | Utilidad sonificacion | Decision |
| --- | --- | --- | --- | --- | --- |
| delta_abs | baja-media | dudosa | alta | baja | NO USAR EN TIEMPO REAL |
| theta_abs | media | dudosa | media-alta | apoyo | USAR SOLO COMO APOYO |
| alpha_abs | media | pendiente | media | calma si se valida | NECESITA MAS CAPTURAS |
| beta_abs | media | dudosa | alta | tension si calidad buena | USAR SOLO COMO APOYO |
| gamma_abs | baja | dudosa | muy alta | artefacto/diagnostico | NO USAR EN TIEMPO REAL |
| delta_rel | media | mejor que abs | alta | slow_power con cautela | USAR SOLO COMO APOYO |
| theta_rel | media | mejor que abs | media | calma/flujo con cautela | USAR CON SUAVIZADO |
| alpha_rel | media-alta | pendiente | media | calmness | NECESITA MAS CAPTURAS |
| beta_rel | media | variable | alta | activity/tension | USAR CON SUAVIZADO |
| gamma_rel | baja | variable | muy alta | evitar | NO USAR EN TIEMPO REAL |
| alpha/beta | razonable | pendiente | media | calma/tension relativa | NECESITA MAS CAPTURAS |
| beta/(alpha+beta) | razonable | aceptable con calidad | alta ante EMG | tension | USAR CON SUAVIZADO |
| theta/alpha | dudosa | pendiente | media | diagnostico | USAR SOLO COMO APOYO |
| slow_power | razonable | depende de artefactos | alta ante drift/blink | calma lenta | USAR SOLO COMO APOYO |
| fast_power | razonable | sensible | alta ante EMG | actividad | USAR CON SUAVIZADO |
| RMS | muy util | buena | alta ante movimiento | intensidad/actividad | USAR CON QUALITY GATE |
| peak_freq | dudosa | puede saltar | alta | registro si estable | USAR SOLO COMO APOYO |
| peak_alpha | util si se valida | pendiente | media | registro/calma | NECESITA MAS CAPTURAS |

## 11. Validacion de `sonification_features.py`

| Control sonificacion | Formula actual | Features base | Validez real | Riesgo | Propuesta |
| --- | --- | --- | --- | --- | --- |
| activity | `0.55*fast_power + 0.45*rms_norm` | beta+gamma+rms | parcialmente valida | EMG sube activity | mantener con quality gate |
| calmness | `alpha*(1-beta/(alpha+beta))` | alpha/beta | pendiente | alpha no validada | mantener como candidata |
| tension | `0.80*beta/(alpha+beta)+0.20*gamma` | beta/gamma | dudosa | EMG | reducir peso gamma si se aprueba |
| rhythmic_density | `0.65*activity+0.35*tension` | activity/tension | parcialmente valida | artefactos aumentan densidad | congelar si mala calidad |
| register | peak_alpha o peak_freq normalizado | picos | dudosa | picos saltan | usar con suavizado fuerte |
| harmonic_stability | `0.65*calmness+0.35*(1-tension)` | alpha/beta/gamma | pendiente | depende de alpha/gamma | mantener diagnostico |
| velocity_factor | `0.30+0.70*activity` | activity | parcialmente valida | movimiento aumenta velocity | quality gate |
| note_probability | `0.15+0.80*rhythmic_density` | density | parcialmente valida | artefactos aumentan notas | quality gate/histeresis |

## 12. Metrica de robustez propuesta

La herramienta nueva calcula una primera version offline:

```text
quality_score = combinacion de:
- features finitas,
- ausencia de gaps,
- RMS en rango plausible,
- pico-pico no artefactado,
- 50 Hz bajo.
```

Propuesta para live:

```text
spectral_quality_score =
  no_saturation
  + rms_plausible
  + low_50hz
  + low_artifact_score
  + sample_gaps_zero
  + finite_bandpowers
  + stable_recent_features
```

Uso recomendado: congelar o suavizar controles musicales cuando
`spectral_quality_score` sea bajo.

## 13. Scripts creados

Nuevo script:

```bash
python3 python/tools/validate_spectral_features.py captures/
```

Opciones:

```bash
python3 python/tools/validate_spectral_features.py captures/<capture_id> --channel 0
python3 python/tools/validate_spectral_features.py captures/ --window-sec 4 --hop-samples 64
python3 python/tools/validate_spectral_features.py captures/ --window-sec 8 --hop-samples 250
```

El script:

- lee CSV reales,
- usa `DSPCore`,
- usa `SonificationFeatureAdapter`,
- exporta bandpowers por ventana,
- exporta features de sonificacion por ventana,
- calcula PSD multitaper,
- genera informe JSON/Markdown,
- genera resumen agregado.

## 14. Cambios realizados

Cambios no invasivos:

- se anadio `python/tools/validate_spectral_features.py`;
- se documento esta auditoria en `docs/validacion_bandas_eeg_sonificacion.md`.

No se han cambiado:

- filtros principales,
- bandas EEG del pipeline live,
- formulas de sonificacion,
- ganancia,
- registros ADS1299,
- formato `eeg_block_uV`.

## 15. Features recomendadas para sonificacion final

Matriz preliminar:

| Parametro musical | Feature actual | Mantener | Feature recomendada | Motivo |
| --- | --- | --- | --- | --- |
| actividad general | fast_power + RMS | si | RMS normalizado + beta_rel suavizada | robusto, sensible a estado/artefacto |
| densidad ritmica | activity+tension | si con gate | activity filtrada por calidad | evita notas por artefactos |
| calma | alpha vs beta | pendiente | alpha_rel si se valida; si no, low beta + RMS bajo | alpha no validada aun |
| tension | beta/(alpha+beta)+gamma | ajustar luego | beta/(alpha+beta), gamma muy bajo peso | gamma probablemente EMG |
| registro | peak_alpha/peak_freq | cautela | peak_alpha solo si estable; si no alpha/beta lento | peak_freq salta |
| estabilidad armonica | calmness/tension | pendiente | score lento con EMA fuerte | depende de alpha/beta |
| velocity | activity | si con gate | RMS_norm + beta_rel suavizada | musicalmente estable |
| probabilidad nota | rhythmic_density | si con gate | density con histeresis/calidad | evita cascadas por movimiento |
| cambio acorde | no consolidado | pendiente | cambios lentos de alpha/beta/quality | debe ser lento |

## 16. Capturas adicionales necesarias

Subir desde la placa al repo al menos:

```text
captures/20260523-175959_post_configfix_shorted_inputs/
captures/20260523-195752_ear_eeg_ch1_only_still_30s/
captures/20260523-200925_ear_eeg_ch1_only_eyes_open_60s/
captures/20260523-201055_ear_eeg_ch1_only_eyes_closed_60s/
captures/20260523-201321_ear_eeg_ch1_only_jaw_movement_30s/
captures/20260523-202120_fp1_fp2_ch1_only_quiet_30s/
captures/20260523-202208_fp1_fp2_ch1_only_eyes_open_60s/
captures/20260523-202323_fp1_fp2_ch1_only_eyes_closed_60s/
captures/20260523-202451_fp1_fp2_ch1_only_forehead_blink_artifact_30s/
```

Cada carpeta debe incluir `eeg_timeseries.csv`, `metadata.json` y, si existen,
`quality_report.json/md`.

## 17. Protocolo tras subir capturas

En PC o placa:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
python3 python/tools/validate_spectral_features.py captures/ --channel 0 --window-sec 4 --hop-samples 64
```

Comparar tambien ventana lenta:

```bash
python3 python/tools/validate_spectral_features.py captures/ --channel 0 --window-sec 8 --hop-samples 250
```

Luego revisar:

```bash
cat captures/comparisons/spectral_feature_robustness.md
```

## 18. Proximos pasos

1. Subir las carpetas reales de `captures/`.
2. Ejecutar `validate_spectral_features.py`.
3. Revisar bandas por ventana, no solo globales.
4. Clasificar alpha como validado/dudoso/no validado.
5. Confirmar si beta/gamma suben en mandibula/frente.
6. Proponer, con datos, una primera version de `spectral_quality_score` live.
7. Solo despues tocar formulas de sonificacion si procede.

## 19. Checklist final

```text
[x] Se auditÃ³ `dsp_core.py`.
[x] Se auditÃ³ `eeg_signal_processor.py`.
[x] Se auditÃ³ `sonification_features.py`.
[x] Se verificÃ³ mÃ©todo multitaper.
[x] Se verificÃ³ resoluciÃ³n de frecuencia.
[x] Se verificÃ³ ventana/hop.
[x] Se verificaron bandas EEG definidas en cÃ³digo.
[ ] Se analizaron CSV reales de captures/.
[ ] Se comparÃ³ ojos abiertos vs ojos cerrados si habÃ­a datos.
[ ] Se evaluÃ³ alpha_rel y alpha_abs.
[ ] Se evaluÃ³ beta/gamma frente a EMG.
[ ] Se evaluÃ³ delta/theta frente a parpadeos/drift.
[ ] Se evaluÃ³ ruido 50 Hz.
[ ] Se evaluÃ³ estabilidad temporal por ventanas.
[x] Se clasificÃ³ cada banda como usable/dudosa/no usable preliminarmente.
[x] Se validaron controles de `sonification_features.py` por auditorÃ­a.
[x] Se propuso matriz final EEG feature â†’ sonificaciÃ³n preliminar.
[x] No se modificÃ³ el pipeline principal sin justificaciÃ³n.
[x] Se dejaron claras las capturas adicionales necesarias.
```





