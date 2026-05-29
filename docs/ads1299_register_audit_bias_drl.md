# ADS1299Plus register audit and BIAS/DRL test design

Documento activo de referencia para registros ADS1299, BIAS/DRL y decisiones de configuracion analogica.

Estado final-v4:

```text
Rama integrada actual: firmware-final-v4
Modo usado en capturas finales: ADS_DIAGNOSTIC_MODE=5 / bias_ch1_only_loff_off
Canal EEG principal en la sesion final: CH1
CH2-CH4: apagados/conservados solo por contrato de streaming
```

Referencia principal: Texas Instruments ADS1299 datasheet Rev. C, SBAS499C:
https://www.ti.com/lit/ds/sbas499c/sbas499c.pdf

Este documento procede de la fase de auditoria y diseÃ±o BIAS/DRL. La ruta practica del proyecto acabo consolidando el modo `bias_ch1_only_loff_off` para la sesion final de laboratorio. Las pruebas BIAS/DRL descritas aqui siguen siendo utiles como contexto tecnico, pero la evidencia principal del TFG debe leerse en `docs/configuracion_final_v4.md` y `docs/validacion_tfg/`.

## Estado de evidencia del proyecto

- `shorted_inputs`: `rms_uV ~0.94`, `ptp_uV ~18`, 250 Hz, 0 gaps, 0 invalid status.
- `test_signal_internal`: capturado correctamente con timing/status estable.
- Fp1-Fp2 sin BIAS/DRL: amplitudes en mV, pico estable ~21 Hz, sin respuesta alpha fiable.
- BIAS/DRL derivado de CH1P+CH1N permitio avanzar hacia una configuracion mas estable.
- El modo final para capturas comparables fue `bias_ch1_only_loff_off`, apagando CH2-CH4 para evitar entradas no usadas/flotantes.

Conclusion: la cadena digital/ADC basica parece sana. El problema principal apunta
a common-mode/referencia corporal/electrodos. Antes de activar o modificar BIAS/DRL hay que
respetar los bits fijos de CONFIG1/CONFIG3 y validar cada cambio en placa.

## Evaluacion completa de registros usados por ADS1299Plus

| Registro | Direccion | Codigo actual | Valor actual | Datasheet / expectativa | Riesgo | Estado |
| --- | ---: | --- | ---: | --- | --- | --- |
| ID | 0x00 | `readReg(ADS_REG_ID)` | observado `0x3C` | ADS1299-4 esperado, NU_CH=00 | Ninguno | OK |
| CONFIG1 | 0x01 | `ADS_CFG1_MAKE(false,false,ADS_DR_250)` | antes `0x86`, corregido a `0x96` | Bit7=1, bits[4:3] fijos `10`, DR=110. Valor esperado conservador: `0x96` | Bit fijo [4] quedaba a 0; ya se preserva | Corregido |
| CONFIG2 | 0x02 | `ADS_CFG2_TEST_OFF` | `0xC0` | Bits[7:6] fijos `11`; test off | OK para normal. Test interno usa `0xD0` con INT_CAL | OK |
| CONFIG3 | 0x03 | `ADS_CFG3_INTREF_NO_BIAS` | antes `0x88`, corregido a `0xE8` | Bits[6:5] fijos `11`; PD_REFBUF=1; BIASREF_INT=1; PD_BIAS=0. Valor esperado sin BIAS: `0xE8` | Bits fijos [6:5] quedaban a 0. Activar BIAS ahora dara `0xEC` | Corregido |
| LOFF | 0x04 | `ADS_LOFF_DCAC_24nA_31Hz_80pct` | `0x66` | Lead-off 24 nA, 31.2 Hz, umbral 80% | Puede inyectar componente diagnostica; no deberia mezclarse con pruebas BIAS iniciales | Dudoso |
| CH1SET | 0x05 | `ADS_CH_DEFAULT_GAIN24()` | `0x60` | ON, gain 24, MUX normal, SRB2 off | OK para diferencial CH1 | OK |
| CH2SET | 0x06 | igual CH1 o power-down segun modo | `0x60` en normal / apagado en modo 5 | ON en modo general; apagado/cortocircuitado en modo final CH1-only | Si queda flotante puede contaminar diagnosticos | OK con cautela |
| CH3SET | 0x07 | igual CH1 o power-down segun modo | `0x60` en normal / apagado en modo 5 | Igual | Si queda flotante puede contaminar diagnosticos | OK con cautela |
| CH4SET | 0x08 | igual CH1 o power-down segun modo | `0x60` en normal / apagado en modo 5 | Igual | Si queda flotante puede contaminar diagnosticos | OK con cautela |
| CH5SET-CH8SET | 0x09-0x0C | no se escriben | n/a | ADS1299-4 no usa 8 canales | No leer/escribir | OK |
| BIAS_SENSP | 0x0D | depende de modo | `0x00` normal / `0x01` en CH1 BIAS | Selecciona entradas P que contribuyen al BIAS amplifier | Sin derivacion BIAS, cuerpo queda flotante | OK segun modo |
| BIAS_SENSN | 0x0E | depende de modo | `0x00` normal / `0x01` en CH1 BIAS | Selecciona entradas N que contribuyen al BIAS amplifier | Igual | OK segun modo |
| LOFF_SENSP | 0x0F | activo o desactivado segun modo | `0x0F` en defaults / `0x00` en pruebas LOFF off | Habilita lead-off en P | Puede contaminar pruebas de ruido/BIAS | Desactivar para capturas finales |
| LOFF_SENSN | 0x10 | activo o desactivado segun modo | `0x0F` en defaults / `0x00` en pruebas LOFF off | Habilita lead-off en N | Igual | Desactivar para capturas finales |
| LOFF_FLIP | 0x11 | `0x00` | `0x00` | No invierte corriente lead-off | OK | OK |
| LOFF_STATP | 0x12 | solo en STATUS helpers | RO | Estado lead-off P | Util para dashboard/diagnostico futuro | Pendiente observabilidad |
| LOFF_STATN | 0x13 | solo en STATUS helpers | RO | Estado lead-off N | Igual | Pendiente observabilidad |
| GPIO | 0x14 | `ADS_GPIO_ALL_INPUTS` | `0x0F` | GPIO como entrada | OK si no se usan GPIO ADS | OK |
| MISC1 | 0x15 | `0x00` | `0x00` | SRB1 off | OK para diferencial puro; no usar SRB1 en Fp1-Fp2 por ahora | OK |
| MISC2 | 0x16 | no se escribe | n/a | Reservado | Correcto no tocar | OK |
| CONFIG4 | 0x17 | `ADS_CFG4_CONT_LOFF_ON` | `0x00` | continuous conversion, comparadores lead-off ON si PD_LOFF_COMP=0 | Para pruebas BIAS conviene lead-off sense off; comparadores pueden quedar ON sin sense | OK con cautela |

## Correcciones recomendadas antes de BIAS/DRL

No son cambios de filtros ni de arquitectura; son preservacion de bits fijos del
datasheet. Ya aplicado en `sketch/ADS1299Plus/src/ADS1299_Registers.h`:

```cpp
// CONFIG1: bit7=1, bits[4:3]=10, DR=250
ADS_CFG1_MAKE(false, false, ADS_DR_250) -> 0x96

// CONFIG3: bits[6:5]=11, PD_REFBUF=1, BIASREF_INT=1, BIAS off
ADS_CFG3_INTREF_NO_BIAS -> 0xE8

// CONFIG3 con BIAS buffer ON:
0xE8 | ADS_CFG3_PD_BIAS -> 0xEC
```

Riesgo de no corregir: activar BIAS usando el helper actual escribiria un CONFIG3
sin bits fijos [6:5]. Aunque el chip ha funcionado en pruebas, no es una base
limpia para evaluar BIAS/DRL.

## DiseÃ±o de pruebas BIAS/DRL

Suposicion de conexion fisica que debe confirmarse antes de compilar:

- Fp1 -> IN1P.
- Fp2 -> IN1N.
- Electrodo BIAS/DRL dedicado -> BIASOUT mediante la red analogica segura de tu PCB.
- La placa tiene limitacion/proteccion de corriente apropiada para conexion a persona.
- No conectar BIASOUT directamente a una persona si tu PCB no implementa la red prevista.

### Prueba A - baseline normal corregido

Objetivo: separar efecto de bits fijos corregidos de efecto BIAS.

Registros:

- CONFIG1 = `0x96`.
- CONFIG3 = `0xE8`.
- BIAS_SENSP = `0x00`.
- BIAS_SENSN = `0x00`.
- LOFF_SENSP/N = `0x00` para no inyectar lead-off durante esta comparacion.
- CH1SET normal gain 24.

Capturas:

- `head_fp1_fp2_no_bias_loff_off`.
- `quiet_rest_fp1_fp2_no_bias_loff_off`.

Modo firmware implementado:

```bash
python3 python/tools/set_ads_diagnostic_mode.py no_bias_loff_off
```

Criterio:

- Si mV caen mucho solo corrigiendo bits fijos/LOFF off, BIAS no era la primera causa.

### Prueba B - BIAS derivado de CH1 P+N

Objetivo: estabilizar common-mode usando solo el par medido.

Registros:

- CONFIG3 = `0xEC`: referencia interna ON, BIASREF_INT ON, BIAS buffer ON.
- BIAS_SENSP = `0x01`: CH1P contribuye a BIAS derivation.
- BIAS_SENSN = `0x01`: CH1N contribuye a BIAS derivation.
- LOFF_SENSP/N = `0x00` inicialmente.
- CH1SET = normal diferencial, gain 24, SRB2 off.

Capturas:

- `head_fp1_fp2_bias_ch1pn_quiet_rest`.
- `head_fp1_fp2_bias_ch1pn_eyes_open`.
- `head_fp1_fp2_bias_ch1pn_eyes_closed`.

Modo firmware implementado:

```bash
python3 python/tools/set_ads_diagnostic_mode.py bias_ch1pn_loff_off
```

Criterio de exito:

- RMS baja de miles de uV a rango mucho menor.
- Pico ~21 Hz baja o desaparece.
- `ptp_uV` cae drasticamente.
- No aparecen invalid status/gaps.
- 50 Hz no crece de forma dominante.

### Prueba C - CH1-only final-v4

Objetivo: mantener BIAS derivado de CH1P+CH1N y apagar CH2-CH4 para evitar que entradas no usadas/flotantes contaminen el front-end o las metricas.

Modo firmware final-v4:

```bash
python3 python/tools/set_ads_diagnostic_mode.py bias_ch1_only_loff_off
```

Registros/concepto:

- CONFIG3 = `0xEC`: referencia interna ON, BIASREF_INT ON, BIAS buffer ON.
- BIAS_SENSP = `0x01`.
- BIAS_SENSN = `0x01`.
- LOFF_SENSP/N = `0x00`.
- CH1SET = normal diferencial, gain 24.
- CH2-CH4 = apagados/cortocircuitados.

Criterio:

- CH1 es la unica evidencia EEG principal.
- CH2-CH4 no deben interpretarse como EEG.
- `sample_gaps=0` e `invalid_status=0`.
- Si se comparan nuevas capturas con `s01_20260528`, usar este modo.

### Prueba D - BIAS derivado de CH1-CH4 P+N

Objetivo: probar si el promedio common-mode mejora usando todos los canales conectados.

Solo hacer si CH2-CH4 estan fisicamente en estado conocido. Si estan flotantes,
NO usar esta prueba.

Registros:

- CONFIG3 = `0xEC`.
- BIAS_SENSP = `0x0F`.
- BIAS_SENSN = `0x0F`.
- LOFF_SENSP/N = `0x00`.

Criterio:

- Mejor que Prueba B si todos los electrodos/canales son reales y estables.
- Peor que B si CH2-CH4 flotan o meten ruido.

### Prueba E - BIAS measurement

Objetivo: medir BIASIN/BIASREF por MUX para comprobar que el nodo BIAS existe.

Esta prueba no debe mezclarse con captura EEG porque cambia el MUX del canal.

Registros:

- CONFIG3 con BIAS_MEAS=1 si se quiere medir ruta BIAS.
- CH1SET MUX = `ADS_MUX_BIAS_MEAS`.

Criterio:

- Captura diagnostica separada, no interpretarla como EEG.

## Orden recomendado actualizado

Para reproducir el camino de validacion:

1. Confirmar CONFIG1/CONFIG3 con bits fijos preservados.
2. Capturar diagnostico interno `shorted_inputs` o `test_signal_internal` si hay dudas de ADC/SPI/escala.
3. Capturar baseline sin BIAS con LOFF sense off si se evalua montaje nuevo.
4. Activar BIAS CH1P+CH1N.
5. Si CH2-CH4 no se usan, pasar a `bias_ch1_only_loff_off`.
6. Capturar quiet/rest, eyes open, eyes closed y artefactos controlados.
7. Revisar RMS, PTP, 50 Hz, alpha, quality score, sample gaps e invalid status.
8. Solo probar CH1-CH4 en BIAS si esos canales no estan flotantes.

Para final-v4 y futuras capturas comparables con la memoria:

```text
ADS_DIAGNOSTIC_MODE=5
ADS_MODE=bias_ch1_only_loff_off
montage=ear_eeg_ch1_only
```

## Decision final-v4

La decision practica integrada en `firmware-final-v4` es:

- conservar contrato de 4 canales por compatibilidad;
- usar CH1 como canal EEG principal;
- derivar BIAS desde CH1P+CH1N;
- desactivar lead-off sense durante capturas finales;
- apagar/cortocircuitar CH2-CH4 en el modo final de captura;
- no interpretar CH2-CH4 como EEG en la sesion `s01_20260528`.

## Decision pendiente

Antes de modificar el modo analogico en futuras ramas, confirmar:

- Donde esta conectado fisicamente BIASOUT/DRL.
- Si hay electrodo BIAS dedicado y en que posicion se colocara.
- Si CH2-CH4 estaran conectados a electrodos reales o flotantes.
- Si el objetivo es una captura comparable con final-v4 o una prueba diagnostica nueva.

No cambiar registros ADS1299 en la futura version esencial UML. La version esencial debe documentar el modo final, no experimentar con la configuracion analogica.



