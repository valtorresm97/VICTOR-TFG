# Resultados de validacion espectral con capturas reales

Fecha: 2026-05-24

Rama: `captura-datos`

Commit de capturas analizadas: `91899a6`

## Resumen ejecutivo

Se analizaron las capturas reales subidas desde la UNO Q con:

```bash
python python/tools/validate_spectral_features.py captures --channel 0 --window-sec 4 --hop-samples 64
```

La validacion se hizo con ventanas de 4 s y salto de 64 muestras, equivalente a
la cadencia live de features del backend. La conclusion principal es:

- La captura y el procesado espectral son suficientemente estables para empezar
  una sonificacion basada en features robustas.
- En montaje ear-EEG, `alpha` queda validada preliminarmente: aumenta claramente
  con ojos cerrados frente a ojos abiertos.
- En montaje Fp1-Fp2, `alpha` no queda validada: el cambio es pequeno y no
  robusto por ventanas.
- `beta` y `gamma` no deben usarse como controles principales sin quality gate:
  son sensibles a EMG/movimiento y gamma es especialmente dudosa.
- `delta/theta/slow_power` deben usarse con cautela: suben mucho en mandibula y
  artefactos frontales, por lo que pueden representar movimiento/drift.
- Las features mas defendibles para sonificacion ahora mismo son:
  `quality_score`, RMS normalizado, `alpha_rel` en ear-EEG, `alpha/beta`,
  `beta/(alpha+beta)` con suavizado, y controles lentos derivados de bandas
  relativas.

## Capturas analizadas

| Captura | Condicion |
| --- | --- |
| `20260523-175959_post_configfix_shorted_inputs` | entradas internas en corto |
| `20260523-195752_ear_eeg_ch1_only_still_30s` | ear-EEG reposo quieto |
| `20260523-200925_ear_eeg_ch1_only_eyes_open_60s` | ear-EEG ojos abiertos |
| `20260523-201055_ear_eeg_ch1_only_eyes_closed_60s` | ear-EEG ojos cerrados |
| `20260523-201321_ear_eeg_ch1_only_jaw_movement_30s` | ear-EEG mandibula |
| `20260523-202120_fp1_fp2_ch1_only_quiet_30s` | Fp1-Fp2 quieto |
| `20260523-202208_fp1_fp2_ch1_only_eyes_open_60s` | Fp1-Fp2 ojos abiertos |
| `20260523-202323_fp1_fp2_ch1_only_eyes_closed_60s` | Fp1-Fp2 ojos cerrados |
| `20260523-202451_fp1_fp2_ch1_only_forehead_blink_artifact_30s` | Fp1-Fp2 frente/parpadeo |

## Calidad espectral global

| Captura | Calidad mediana | Ventanas malas | RMS mediano uV | 50 Hz mediano | Conclusion |
| --- | ---: | ---: | ---: | ---: | --- |
| shorted_inputs | 0.90 | 0.0 % | 0.00 | 0.0007 | cadena digital/ADC sana |
| ear still | 1.00 | 0.0 % | 11.67 | 0.142 | limpia |
| ear open | 1.00 | 0.0 % | 11.34 | 0.092 | limpia |
| ear closed | 1.00 | 0.0 % | 9.46 | 0.062 | limpia |
| ear jaw | 0.49 | 68.4 % | 223.96 | 0.001 | artefacto muscular claro |
| Fp1-Fp2 quiet | 1.00 | 0.0 % | 28.90 | 0.168 | plausible, mas 50 Hz |
| Fp1-Fp2 open | 1.00 | 0.0 % | 30.13 | 0.158 | plausible, 50 Hz relevante |
| Fp1-Fp2 closed | 1.00 | 15.9 % | 38.11 | 0.176 | contiene ventanas buenas y artefactos |
| Fp1-Fp2 artifact | 0.86 | 28.9 % | 174.35 | 0.036 | control de artefacto frontal |

## Validacion de alfa

### Ear-EEG

Comparacion de ventanas buenas, ojos cerrados frente a ojos abiertos:

| Metrica | Ojos cerrados | Ojos abiertos | Ratio/diferencia |
| --- | ---: | ---: | ---: |
| `alpha_abs` mediana | 1.36e-11 | 6.85e-12 | 1.99x |
| `alpha_rel` mediana | 0.1579 | 0.0640 | 2.47x |
| ventanas con `alpha_abs_closed > alpha_abs_open` | | | 82.4 % |
| ventanas con `alpha_rel_closed > alpha_rel_open` | | | 97.1 % |

Conclusion: `ALFA VALIDADO PRELIMINARMENTE` para ear-EEG.

La validacion es preliminar porque solo hay una pareja open/closed, pero el
efecto es fuerte, la calidad de ventanas es 1.0 y no coincide con aumento de
artefactos.

### Fp1-Fp2

Comparacion de ventanas buenas, ojos cerrados frente a ojos abiertos:

| Metrica | Ojos cerrados | Ojos abiertos | Ratio/diferencia |
| --- | ---: | ---: | ---: |
| `alpha_abs` mediana | 1.35e-11 | 1.32e-11 | 1.02x |
| `alpha_rel` mediana | 0.0441 | 0.0412 | 1.07x |
| ventanas con `alpha_abs_closed > alpha_abs_open` | | | 53.1 % |
| ventanas con `alpha_rel_closed > alpha_rel_open` | | | 49.1 % |

Conclusion: `ALFA NO VALIDADO` para Fp1-Fp2 con estas capturas.

Esto es coherente con el montaje frontal: Fp1-Fp2 es util para ver parpadeo,
frente y estado general, pero no es el mejor montaje para alfa occipital.

## Validacion beta/gamma frente a EMG

En ear-EEG mandibula:

- RMS mediano sube de ~11 uV en reposo a ~224 uV.
- Calidad mediana baja a 0.49.
- 68.4 % de ventanas quedan como baja calidad/artefacto.
- La distribucion espectral se desplaza sobre todo a baja frecuencia por el
  movimiento, pero la captura confirma que el sistema es muy sensible a EMG y
  movimiento.

En Fp1-Fp2 frente/parpadeo:

- RMS mediano sube a 174 uV.
- Ventanas malas: 28.9 %.
- `slow_power_rel` mediano sube a 0.906.
- `fast_power_rel` baja a 0.088.

Conclusion:

- `beta` puede usarse solo como apoyo y con suavizado.
- `gamma` no debe usarse como control principal en tiempo real.
- Cualquier aumento brusco de RMS o caida de quality debe congelar o atenuar
  controles musicales derivados de beta/gamma.

## Validacion delta/theta

`slow_power_rel = delta + theta`:

| Condicion | Slow power mediano |
| --- | ---: |
| ear open | 0.497 |
| ear closed | 0.508 |
| ear jaw | 0.969 |
| Fp1-Fp2 open | 0.511 |
| Fp1-Fp2 closed | 0.589 |
| Fp1-Fp2 artifact | 0.906 |

Conclusion:

Delta/theta son muy sensibles a movimiento, parpadeo, frente y mandibula. No
deben controlar cambios musicales bruscos por si solas. Pueden usarse como
componente lento de calma o estado basal solo cuando `quality_score` sea alto y
RMS este en rango plausible.

## Validacion de 50 Hz

El 50 Hz no domina las capturas ear-EEG open/closed:

- ear open: 0.092 mediano.
- ear closed: 0.062 mediano.

Fp1-Fp2 tiene mas 50 Hz:

- Fp1-Fp2 quiet: 0.168.
- Fp1-Fp2 open: 0.158.
- Fp1-Fp2 closed: 0.176.

Conclusion:

Ear-EEG es mejor para validacion espectral fina. Fp1-Fp2 es usable, pero con
mayor vigilancia del ruido de red.

## Validacion de controles de sonificacion

| Control | Estado con datos reales | Riesgo | Recomendacion |
| --- | --- | --- | --- |
| `activity` | util pero sensible | RMS/fast_power sube con artefactos | usar con `quality_score` |
| `calmness` | prometedor en ear-EEG | depende de alpha validada | usar en ear-EEG, validar mas sesiones |
| `tension` | dudoso | beta/gamma/EMG | reducir peso gamma en propuesta futura |
| `rhythmic_density` | usable con gate | sube con artefactos | congelar si calidad baja |
| `register` | dudoso | peak_freq puede saltar | suavizado fuerte o usar alpha estable |
| `harmonic_stability` | prometedor pero indirecto | depende de calmness/tension | usar lento |
| `velocity_factor` | usable con gate | movimiento aumenta velocity | limitar con quality |
| `note_probability` | usable con gate | artefactos generan notas | histeresis/calidad |

## Decisiones por feature

| Feature | Decision |
| --- | --- |
| RMS | USAR CON QUALITY GATE |
| `alpha_rel` ear-EEG | USAR CON SUAVIZADO |
| `alpha_abs` ear-EEG | USAR SOLO CON NORMALIZACION POR SESION |
| `alpha_rel` Fp1-Fp2 | NO USAR COMO VALIDACION DE ALFA |
| `alpha/beta` | USAR CON SUAVIZADO, especialmente ear-EEG |
| `beta_rel` | USAR SOLO COMO APOYO |
| `gamma_rel` | NO USAR EN TIEMPO REAL por ahora |
| `delta_rel` | USAR SOLO COMO APOYO |
| `theta_rel` | USAR SOLO COMO APOYO |
| `slow_power` | USAR SOLO CON QUALITY GATE |
| `fast_power` | USAR CON SUAVIZADO Y QUALITY GATE |
| `peak_freq` | NO USAR SOLO |
| `peak_alpha` | NECESITA MAS CAPTURAS |
| `quality_score` | USAR |

## Matriz propuesta EEG feature -> sonificacion

| Parametro musical | Feature actual | Mantener | Feature recomendada | Motivo |
| --- | --- | --- | --- | --- |
| actividad general | `fast_power + rms_norm` | si | RMS_norm + beta_rel suavizada + quality gate | responde, pero artefactos suben RMS |
| densidad ritmica | `activity + tension` | si con control | activity si `quality_score > 0.7` | evita densidad por movimiento |
| calma | `alpha*(1-beta_ratio)` | si en ear-EEG | alpha_rel ear-EEG + alpha/beta | alfa validada en ear-EEG |
| tension | beta/gamma | ajustar | beta/(alpha+beta), gamma peso minimo | gamma no robusta |
| registro | peak alpha/freq | cautela | peak_alpha solo si estable; si no alpha_rel lento | peak_freq global salta |
| estabilidad armonica | calmness/tension | si lento | EMA fuerte + quality gate | musicalmente estable |
| velocity | activity | si con limite | RMS_norm suavizado | fisiologico pero sensible |
| probabilidad nota | rhythmic_density | si con gate | density + histeresis | evita cascadas por artefacto |

## Cambios no aplicados todavia

No se modificaron:

- filtros principales,
- bandas EEG,
- formulas de sonificacion live,
- ganancia,
- registros ADS1299,
- formato de streaming.

## Proximos pasos

1. Repetir ear-EEG open/closed al menos 2 sesiones mas.
2. Repetir Fp1-Fp2 open/closed con cables inmoviles y RLD igual.
3. Implementar, con aprobacion, `spectral_quality_score` live.
4. Congelar o atenuar sonificacion cuando quality sea baja.
5. Proponer reduccion del peso de gamma en `tension`.
6. Crear comparador automatico open/closed por ventanas para que no dependa de
   calculos manuales.

## Checklist

```text
[x] Se auditó `dsp_core.py`.
[x] Se auditó `eeg_signal_processor.py`.
[x] Se auditó `sonification_features.py`.
[x] Se verificó método multitaper.
[x] Se verificó resolución de frecuencia.
[x] Se verificó ventana/hop.
[x] Se verificaron bandas EEG definidas en código.
[x] Se analizaron CSV reales de captures/.
[x] Se comparó ojos abiertos vs ojos cerrados si había datos.
[x] Se evaluó alpha_rel y alpha_abs.
[x] Se evaluó beta/gamma frente a EMG.
[x] Se evaluó delta/theta frente a parpadeos/drift.
[x] Se evaluó ruido 50 Hz.
[x] Se evaluó estabilidad temporal por ventanas.
[x] Se clasificó cada banda como usable/dudosa/no usable.
[x] Se validaron controles de `sonification_features.py`.
[x] Se propuso matriz final EEG feature → sonificación.
[x] No se modificó el pipeline principal sin justificación.
[x] Se dejaron claras las capturas adicionales necesarias.
```
