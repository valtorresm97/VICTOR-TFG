# Captura `03_quiet_rest_60s` - reposo quieto

## 1. Objetivo de la condicion

La condicion de reposo quieto se plantea como un estado basal general: el sujeto permanece sentado, sin hablar, con mandibula relajada y sin movimientos voluntarios. Su funcion es comprobar si el sistema puede sostener una adquisicion y una sonificacion durante una condicion real mantenida.

Esta captura no debe interpretarse como control fisiologico perfecto. Su valor principal es tecnico y experimental: muestra continuidad del pipeline durante 60 segundos de reposo.

## 2. Datos tecnicos

| Campo | Valor |
| --- | --- |
| Carpeta | `captures/capturas finales/20260528-145448_s01_20260528_ear_eeg_ch1_only_03_quiet_rest_60s` |
| Diagnostico | `dudosa` |
| Frecuencia efectiva | `250.00 Hz` |
| Sample gaps | `0` |
| Invalid status | `0` |
| RMS CH1 | `82.7559 uV` |
| Pico-pico CH1 | `1168 uV` |
| Ratio 50 Hz | `0.338669` |
| Fraccion de ventanas con artefacto | `0.0178571` |
| Notas deduplicadas | `72` |

El transporte fue estable. La seÃ±al presenta ruido/artefacto moderado, pero no muestra los picos extremos de la condicion `01_eyes_open_rest_60s`.

## 3. EEG temporal CH1

![EEG temporal](../figures/capturas_finales_s01_20260528_matplotlib/20260528-145448_s01_20260528_ear_eeg_ch1_only_03_quiet_rest_60s/eeg_ch1_temporal.png)

La grafica temporal permite evaluar si el sujeto mantuvo un estado relativamente estable. Tambien permite detectar transitorios o cambios de amplitud que puedan afectar a los bandpowers.

## 4. Bandpowers relativos

![Bandpowers relativos](../figures/capturas_finales_s01_20260528_matplotlib/20260528-145448_s01_20260528_ear_eeg_ch1_only_03_quiet_rest_60s/bandpowers_relativos.png)

Esta figura muestra la evolucion de delta, theta, alpha, beta y gamma en ventanas sucesivas. En reposo quieto, los cambios en bandpowers deben leerse como comportamiento del sistema bajo condiciones reales, no como marcador clinico.

## 5. Controles de sonificacion

![Controles de sonificacion](../figures/capturas_finales_s01_20260528_matplotlib/20260528-145448_s01_20260528_ear_eeg_ch1_only_03_quiet_rest_60s/controles_sonificacion.png)

Los controles de sonificacion permiten explicar que la musica surge de variables normalizadas y suavizadas. La condicion de reposo es una de las mas utiles para observar si estos controles se mantienen en rangos razonables durante una captura sostenida.

## 6. Calidad de seÃ±al y quality gate

![Calidad de seÃ±al y gate](../figures/capturas_finales_s01_20260528_matplotlib/20260528-145448_s01_20260528_ear_eeg_ch1_only_03_quiet_rest_60s/calidad_senal_quality_gate.png)

Esta figura permite comprobar si las ventanas usadas para sonificacion se mantienen en una zona aceptable o si deben interpretarse con cautela. En esta captura, el diagnostico sigue siendo dudoso por ruido de red, aunque la continuidad temporal del sistema es correcta.

## 7. Notas musicales generadas

![Notas musicales](../figures/capturas_finales_s01_20260528_matplotlib/20260528-145448_s01_20260528_ear_eeg_ch1_only_03_quiet_rest_60s/notas_musicales.png)

Se registraron 72 notas deduplicadas. Esto confirma que la salida musical se produjo durante la condicion de reposo, con persistencia suficiente para analisis posterior.

## 8. ConclusiÃ³n para el TFG

Esta condicion es adecuada como evidencia de pipeline sostenido durante reposo. Debe redactarse con cautela, reconociendo que la calidad EEG fue dudosa por ruido y artefactos moderados, pero que el sistema tecnico se comporto correctamente.

Frase sugerida:

> Durante el reposo quieto, el sistema mantuvo adquisicion continua sin gaps ni estados invalidos y registro una salida musical sostenida. La condicion se considera valida como evidencia de integracion tecnica, aunque la interpretacion fisiologica queda limitada por ruido de red y variabilidad de amplitud.



