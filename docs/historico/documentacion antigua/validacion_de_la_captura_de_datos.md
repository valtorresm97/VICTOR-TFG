# Validacion de la captura de datos EEG

Fecha de cierre de fase: 2026-05-23

Rama de trabajo: `captura-datos`

## Objetivo

Esta fase se centro en validar que la adquisicion EEG real con Arduino UNO Q y
ADS1299-4PAG funciona de forma fiable antes de seguir modificando sonificacion,
filtros o mapeos MIDI.

El criterio principal no fue "mejorar por intuicion", sino obtener evidencia de:

- ADS1299 detectado y comunicando por SPI.
- Frames RDATAC coherentes.
- `DRDY` respetado.
- Frecuencia efectiva cercana a 250 Hz.
- `sample_idx` sin saltos.
- `status` ADS1299 valido.
- Conversion a microvoltios plausible.
- Separacion entre adquisicion limpia, ruido de red, artefactos musculares y
  problemas de contacto/cables.

## Mejoras realizadas

### Rama y flujo de trabajo

- Se creo y trabajo en la rama `captura-datos`.
- Se subieron los cambios a GitHub para que la placa UNO Q pudiera hacer
  `git pull` desde `/home/arduino/ArduinoApps/eeg_midi`.
- Se mantuvo la regla de no cambiar filtros principales ni configuracion critica
  sin datos reales.

### Herramientas de captura

Se creo un flujo de captura real en `captures/` basado en peticiones desde shell
y grabacion por la app App Lab en ejecucion:

- `python/tools/capture_eeg_quality.py`
- `python/capture_manager.py`
- integracion con `python/backend_service.py`

El problema inicial fue que el shell normal de la placa no tenia el modulo
`arduino`. Se resolvio haciendo que el script de captura escriba una solicitud
en `state/capture_request.json`, y que la app App Lab, que si tiene el entorno
Arduino, ejecute la grabacion real.

Cada captura guarda:

- `metadata.json`
- `eeg_timeseries.csv`
- `quality_report.json`
- `quality_report.md`
- `spectral_summary.csv`

### Herramientas de analisis

Se creo y amplio:

- `python/tools/analyze_eeg_capture.py`
- `python/tools/compare_eeg_captures.py`

Metricas principales implementadas:

- duracion observada,
- frecuencia efectiva,
- muestras recibidas,
- saltos de muestra,
- `status` invalido,
- RMS,
- media,
- pico-pico,
- percentiles,
- saturacion,
- saltos abruptos,
- flatline,
- PSD multitaper,
- bandpowers,
- pico espectral,
- potencia relativa de 50 Hz.

Mas adelante se anadio una mejora clave: metricas por ventanas de 2 s con salto
de 1 s. Esto resulto necesario porque algunas capturas tenian ventanas limpias
de EEG pero quedaban penalizadas por un golpe o artefacto breve.

Nuevas metricas de estabilidad:

- `median_rms_uV`
- `p95_rms_uV`
- `best_window_rms_uV`
- `median_ptp_uV`
- `p95_ptp_uV`
- `artifact_window_fraction`

Este cambio permite distinguir:

- captura limpia sostenida,
- captura limpia con artefactos transitorios,
- captura dominada por movimiento/EMG.

### Correcciones ADS1299 importantes

Se revisaron registros frente al datasheet del ADS1299 y se corrigio la
preservacion de bits fijos/reservados:

- `CONFIG1` para 250 SPS debe preservar los bits fijos y quedar como `0x96`,
  no `0x86`.
- `CONFIG3` sin BIAS debe quedar como `0xE8`, no `0x88`.
- `CONFIG3` con BIAS activo debe quedar como `0xEC`, no `0x8C`.

Estas correcciones quedaron documentadas en:

- `docs/ads1299_register_audit_bias_drl.md`

Referencias usadas:

- ADS1299 datasheet, seccion 9.6.1.2, registro `CONFIG1`, tabla 13.
- ADS1299 datasheet, seccion 9.6.1.4, registro `CONFIG3`, tabla 15.

### Modos diagnosticos ADS1299

Se anadieron modos controlados seleccionables con:

```bash
python3 python/tools/set_ads_diagnostic_mode.py <modo>
```

Modos usados:

| Modo | Uso |
| --- | --- |
| `normal` | configuracion normal |
| `shorted_inputs` | entradas internas en corto |
| `test_signal_internal` | test interno ADS1299 |
| `no_bias_loff_off` | entradas reales, BIAS off, lead-off off |
| `bias_ch1pn_loff_off` | entradas reales, BIAS derivado de CH1P+CH1N |
| `bias_ch1_only_loff_off` | solo CH1 activo, CH2-CH4 apagados, BIAS CH1P+CH1N |

La documentacion esta en:

- `docs/ads1299_diagnostic_modes.md`

## Balance de capturas

### 1. Validacion interna: ADC/SPI/escala

#### `shorted_inputs`

Resultado final tras correcciones:

| Metrica CH1 | Valor |
| --- | ---: |
| RMS | 0.115 uV |
| Pico-pico | 4 uV |
| Sample gaps | 0 |
| Invalid status | 0 |

Interpretacion:

La cadena ADS1299 -> SPI -> firmware -> Bridge -> Python -> analisis funciona.
El ruido interno en corto es muy bajo. Esto descarta como causa principal de los
problemas iniciales un fallo grave de SPI, escala o transporte.

#### `test_signal_internal`

Resultado:

- captura estable,
- sample rate correcto,
- sin saltos,
- sin `status` invalido.

Interpretacion:

El test interno confirma que el ADS1299 puede generar una senal periodica y que
el pipeline la transporta. No debe interpretarse como EEG real.

### 2. Capturas iniciales Fp1-Fp2 sin estrategia BIAS/RLD adecuada

Las primeras capturas con Fp1-Fp2 dieron amplitudes muy altas:

- RMS de varios cientos a miles de microvoltios,
- pico-pico de decenas de milivoltios en algunos casos,
- picos repetidos alrededor de 21-25 Hz,
- sensibilidad fuerte al movimiento/contacto.

Interpretacion:

No era una captura EEG limpia. Los datos apuntaban a combinacion de:

- ausencia inicial de control de modo comun,
- cables/electrodos actuando como antena,
- contacto variable,
- artefactos musculares/frontales,
- canales no usados flotantes influyendo en diagnostico multicanal.

### 3. Activacion BIAS/RLD

Comparacion significativa:

| Captura | RMS CH1 | Pico-pico CH1 | 50 Hz ratio | Comentario |
| --- | ---: | ---: | ---: | --- |
| sin BIAS, lead-off off | 2107.84 uV | 56322 uV | 0.271 | mala, ruido/red dominante |
| BIAS CH1P+CH1N, lead-off off | 305.84 uV | 1413 uV | 0.00055 | mejora clara |

Interpretacion:

La conexion `RLD_DRV` y el uso de BIAS/DRL son necesarios. La reduccion de 50 Hz
y amplitud fue demasiado grande como para atribuirla a casualidad.

### 4. Pruebas de posicion RLD

Se probaron varias posiciones:

| Montaje | Resultado |
| --- | --- |
| RLD mastoide izquierda | mejor que sin BIAS, pero variable |
| RLD mastoide derecha | mala en varias pruebas |
| RLD muneca/antebrazo | mas prometedora y repetible |
| RLD cuello/mastoide con mejor contacto | no mejoro; aumento 50 Hz/amplitud |

Conclusion practica:

La opcion mas estable hasta ahora es `RLD_DRV` en muneca o antebrazo. Para las
pruebas finales no conviene moverlo si la senal ya es estable.

### 5. Montaje ear-EEG CH1-only

Configuracion:

- `ADS_DIAGNOSTIC_MODE=5`
- `IN1P = mastoide/oreja izquierda`
- `IN1N = mastoide/oreja derecha`
- `RLD_DRV = muneca/antebrazo`
- CH2-CH4 apagados.

Este montaje fue el primero en producir reposo limpio y repetible.

#### Captura `ear_eeg_ch1_only_still_30s`

| Metrica CH1 | Valor |
| --- | ---: |
| RMS global | 11.99 uV |
| RMS mediano por ventana | 12.00 uV |
| P95 RMS ventana | 14.64 uV |
| Mejor ventana | 8.20 uV |
| Pico-pico global | 159 uV |
| Artefactos por ventana | 0 % |
| Sample gaps | 0 |
| Invalid status | 0 |

Valoracion:

Captura muy buena. Es la primera evidencia fuerte de EEG plausible en reposo.

#### Captura `ear_eeg_ch1_only_eyes_open_60s`

| Metrica CH1 | Valor |
| --- | ---: |
| RMS global | 32.26 uV |
| RMS mediano por ventana | 11.40 uV |
| P95 RMS ventana | 105.87 uV |
| Pico-pico global | 1946 uV |
| 50 Hz ratio | 0.013 |
| Artefactos por ventana | 0 % |

Valoracion:

Captura aceptable. La mediana por ventanas muestra reposo limpio aunque hubo
algun evento que elevo el RMS global.

#### Captura `ear_eeg_ch1_only_eyes_closed_60s`

| Metrica CH1 | Valor |
| --- | ---: |
| RMS global | 32.26 uV |
| RMS mediano por ventana | 9.62 uV |
| P95 RMS ventana | 16.18 uV |
| Pico-pico global | 2651 uV |
| 50 Hz ratio | 0.016 |
| Artefactos por ventana | 0 % |

Valoracion:

Captura limpia y estable. No hubo aumento claro de alfa absoluta frente a ojos
abiertos, pero esto no invalida la adquisicion: en montaje tipo mastoides/ear EEG
no se espera necesariamente una respuesta alfa occipital clara.

#### Captura `ear_eeg_ch1_only_jaw_movement_30s`

| Metrica CH1 | Valor |
| --- | ---: |
| RMS global | 214.57 uV |
| RMS mediano por ventana | 224.39 uV |
| P95 RMS ventana | 327.71 uV |
| Pico-pico global | 1741 uV |
| Artefactos por ventana | 66.7 % |

Valoracion:

Control positivo de artefacto muscular. La senal responde claramente al
movimiento de mandibula. Esto es bueno para validacion: el sistema distingue
reposo limpio de actividad muscular.

### 6. Montaje Fp1-Fp2 con CH1-only y BIAS/RLD

Configuracion:

- `ADS_DIAGNOSTIC_MODE=5`
- `IN1P = Fp1`
- `IN1N = Fp2`
- `RLD_DRV = muneca/antebrazo`
- CH2-CH4 apagados.

Este montaje fue mucho mejor que las primeras pruebas Fp1-Fp2.

#### Captura `fp1_fp2_ch1_only_quiet_30s`

| Metrica CH1 | Valor |
| --- | ---: |
| RMS global | 50.31 uV |
| RMS mediano por ventana | 29.88 uV |
| P95 RMS ventana | 117.71 uV |
| Mejor ventana | 17.67 uV |
| Pico-pico global | 2826 uV |
| 50 Hz ratio | 0.120 |
| Artefactos por ventana | 0 % |

Valoracion:

Fp1-Fp2 ya es plausible en reposo si el montaje esta bien hecho. Hay mas 50 Hz
que en ear-EEG, pero la amplitud por ventanas es razonable.

#### Captura `fp1_fp2_ch1_only_eyes_open_60s`

| Metrica CH1 | Valor |
| --- | ---: |
| RMS global | 30.52 uV |
| RMS mediano por ventana | 29.15 uV |
| P95 RMS ventana | 39.55 uV |
| Pico-pico global | 640 uV |
| 50 Hz ratio | 0.264 |
| Artefactos por ventana | 0 % |

Valoracion:

Buena amplitud y estabilidad, pero 50 Hz relativamente dominante. Esto sugiere
que la captura es util, aunque conviene mejorar cableado/contacto antes de usar
bandpowers finos.

#### Captura `fp1_fp2_ch1_only_eyes_closed_60s`

| Metrica CH1 | Valor |
| --- | ---: |
| RMS global | 859.72 uV |
| RMS mediano por ventana | 37.35 uV |
| P95 RMS ventana | 2657.62 uV |
| Pico-pico global | 45684 uV |
| Artefactos por ventana | 8.93 % |

Valoracion:

No se debe aceptar globalmente como limpia por el pico-pico enorme, pero si
contiene muchas ventanas plausibles. Sirve como ejemplo de por que se anadieron
metricas por ventanas: una captura puede tener senal buena y a la vez artefactos
transitorios fuertes.

#### Captura `fp1_fp2_ch1_only_forehead_blink_artifact_30s`

| Metrica CH1 | Valor |
| --- | ---: |
| RMS global | 174.99 uV |
| RMS mediano por ventana | 108.35 uV |
| P95 RMS ventana | 333.09 uV |
| Pico-pico global | 3124 uV |
| Artefactos por ventana | 33.3 % |

Valoracion:

Control positivo de artefacto frontal/parpadeo/movimiento. Confirma que Fp1-Fp2
es sensible a movimientos de frente y parpadeo, como se espera fisiologicamente.

## Mejores capturas obtenidas

Ordenadas por valor de validacion:

1. `ear_eeg_ch1_only_still_30s`
   - RMS mediano 12.00 uV.
   - Artefactos 0 %.
   - Pico-pico 159 uV.
   - Mejor evidencia de reposo limpio.

2. `ear_eeg_ch1_only_eyes_closed_60s`
   - RMS mediano 9.62 uV.
   - P95 RMS 16.18 uV.
   - Artefactos 0 %.
   - Muy estable.

3. `ear_eeg_ch1_only_eyes_open_60s`
   - RMS mediano 11.40 uV.
   - Artefactos 0 %.
   - Valida para comparacion, aunque no mostro alfa absoluta mayor con ojos cerrados.

4. `fp1_fp2_ch1_only_eyes_open_60s`
   - RMS mediano 29.15 uV.
   - P95 RMS 39.55 uV.
   - Artefactos 0 %.
   - Buena amplitud, con 50 Hz aun relevante.

5. `fp1_fp2_ch1_only_quiet_30s`
   - RMS mediano 29.88 uV.
   - Artefactos 0 %.
   - Plausible, pero con mas ruido de red.

## Configuracion final mas prometedora

La configuracion mas prometedora al cierre de esta fase es:

```text
ADS1299 DIAG: bias_ch1_only_loff_off
CH1 activo
CH2-CH4 apagados
BIAS derivado de CH1P + CH1N
Lead-off sense apagado
RLD_DRV conectado a muneca o antebrazo
```

Montaje recomendado para senal fina:

```text
IN1P = mastoide/oreja izquierda
IN1N = mastoide/oreja derecha
RLD_DRV = muneca o antebrazo
```

Montaje Fp1-Fp2 tambien es ya plausible si:

```text
IN1P = Fp1
IN1N = Fp2
RLD_DRV = muneca o antebrazo
mandibula y frente relajadas
cables inmoviles
```

## Consideraciones necesarias para llegar a la senal fina

1. Usar BIAS/RLD.
   Sin BIAS, el ruido y amplitud eran muy superiores.

2. Apagar canales no usados.
   CH2-CH4 flotantes contaminaban la interpretacion multicanal. En validacion
   actual solo CH1 debe considerarse EEG.

3. Desactivar lead-off sense durante capturas de calidad.
   Evita inyecciones/efectos no deseados mientras no se este midiendo impedancia.

4. Usar metricas por ventanas.
   RMS global y pico-pico global pueden quedar dominados por un unico movimiento.

5. Diferenciar senal limpia de artefacto.
   El sistema responde a mandibula/frente/parpadeo con aumentos claros, lo cual
   confirma sensibilidad fisiologica pero tambien exige control postural.

6. No usar el aumento alfa como unica validacion.
   En ear-EEG o Fp1-Fp2 no es obligatorio ver una respuesta alfa occipital clara.
   La validez debe basarse primero en amplitud, estabilidad, timing, ausencia de
   saturacion y comportamiento ante artefactos controlados.

7. No cambiar filtros ni ganancia todavia.
   Ya se ha conseguido senal plausible. Antes de tocar filtros, conviene repetir
   capturas y comparar bajo el mismo montaje.

## Estado tecnico al cierre

Se considera validado de forma preliminar:

- ADS1299 detectado (`ID=0x3C`).
- RDATAC activo.
- `status=0xC00000` en capturas validas.
- Sample rate efectivo 250 Hz.
- Capturas sin gaps.
- Capturas sin `status` invalido.
- Ruta ADC/SPI/Bridge/Python funcional.
- Escala en microvoltios plausible por `shorted_inputs` y capturas reales.
- BIAS/RLD necesario y efectivo.
- CH1-only es la configuracion mas limpia.
- Ear-EEG y Fp1-Fp2 pueden producir ventanas EEG plausibles.

No queda validado aun:

- Que las bandas EEG sean fisiologicamente robustas para sonificacion final.
- Que el aumento alfa ojos cerrados sea detectable en este montaje.
- Que Fp1-Fp2 sea estable en sesiones largas sin artefactos.
- Que un notch/filtro adicional sea necesario o conveniente.
- Que se pueda reactivar multicanal sin problemas de canales flotantes.

## Proximos pasos recomendados

1. Mantener `bias_ch1_only_loff_off`.
2. Repetir 3 veces:
   - ear-EEG quieto 60 s,
   - Fp1-Fp2 quieto 60 s,
   - Fp1-Fp2 parpadeo/frente 30 s.
3. Reanalizar todas con metricas por ventanas.
4. Crear una tabla comparativa automatica entre capturas.
5. Ajustar el analizador para que controles de artefacto se etiqueten como
   `artefacto_confirmado`.
6. Solo despues decidir si hace falta:
   - notch adicional,
   - cambio de filtros,
   - cambio de ganancia,
   - reactivacion controlada de mas canales.

## Conclusion

La captura de datos ha pasado de senales iniciales no plausibles, con amplitudes
excesivas y picos persistentes, a capturas con ventanas estables dentro del rango
esperable de EEG. La mejor senal obtenida hasta ahora es la de tipo ear-EEG con
CH1-only, BIAS activo y RLD en muneca/antebrazo. En reposo presenta RMS de ventana
alrededor de 10-12 uV y 0 % de artefactos, y cuando se introducen movimientos
bruscos o mandibula/frente, la senal cambia claramente.

Por tanto, la adquisicion real puede considerarse preliminarmente plausible. El
foco de la siguiente fase debe ser repetir estabilidad, clasificar artefactos y
evitar modificar filtros o registros hasta tener comparativas suficientes.



