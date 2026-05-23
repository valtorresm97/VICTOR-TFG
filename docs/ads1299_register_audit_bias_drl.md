# ADS1299Plus register audit and BIAS/DRL test design

Referencia principal: Texas Instruments ADS1299 datasheet Rev. C, SBAS499C:
https://www.ti.com/lit/ds/sbas499c/sbas499c.pdf

Estado de evidencia del proyecto:

- `shorted_inputs`: `rms_uV ~0.94`, `ptp_uV ~18`, 250 Hz, 0 gaps, 0 invalid status.
- `test_signal_internal`: capturado correctamente con timing/status estable.
- Fp1-Fp2 sin BIAS/DRL: amplitudes en mV, pico estable ~21 Hz, sin respuesta alpha fiable.

Conclusion: la cadena digital/ADC basica parece sana. El problema principal apunta
a common-mode/referencia corporal/electrodos. Antes de activar BIAS/DRL hay que
corregir o al menos discutir bits fijos de CONFIG1/CONFIG3.

## Evaluacion completa de registros usados por ADS1299Plus

| Registro | Direccion | Codigo actual | Valor actual | Datasheet / expectativa | Riesgo | Estado |
| --- | ---: | --- | ---: | --- | --- | --- |
| ID | 0x00 | `readReg(ADS_REG_ID)` | observado `0x3C` | ADS1299-4 esperado, NU_CH=00 | Ninguno | OK |
| CONFIG1 | 0x01 | `ADS_CFG1_MAKE(false,false,ADS_DR_250)` | antes `0x86`, corregido a `0x96` | Bit7=1, bits[4:3] fijos `10`, DR=110. Valor esperado conservador: `0x96` | Bit fijo [4] quedaba a 0; ya se preserva | Corregido |
| CONFIG2 | 0x02 | `ADS_CFG2_TEST_OFF` | `0xC0` | Bits[7:6] fijos `11`; test off | OK para normal. Test interno usa `0xD0` con INT_CAL | OK |
| CONFIG3 | 0x03 | `ADS_CFG3_INTREF_NO_BIAS` | antes `0x88`, corregido a `0xE8` | Bits[6:5] fijos `11`; PD_REFBUF=1; BIASREF_INT=1; PD_BIAS=0. Valor esperado sin BIAS: `0xE8` | Bits fijos [6:5] quedaban a 0. Activar BIAS ahora dara `0xEC` | Corregido |
| LOFF | 0x04 | `ADS_LOFF_DCAC_24nA_31Hz_80pct` | `0x66` | Lead-off 24 nA, 31.2 Hz, umbral 80% | Puede inyectar componente diagnostica; no deberia mezclarse con pruebas BIAS iniciales | Dudoso |
| CH1SET | 0x05 | `ADS_CH_DEFAULT_GAIN24()` | `0x60` | ON, gain 24, MUX normal, SRB2 off | OK para Fp1-Fp2 diferencial | OK |
| CH2SET | 0x06 | igual CH1 | `0x60` | ON, gain 24, normal | CH2-CH4 activos aunque no se analizan | OK |
| CH3SET | 0x07 | igual CH1 | `0x60` | ON, gain 24, normal | Puede aportar common-mode a BIAS si se deriva de todos | OK con cautela |
| CH4SET | 0x08 | igual CH1 | `0x60` | ON, gain 24, normal | Igual | OK con cautela |
| CH5SET-CH8SET | 0x09-0x0C | no se escriben | n/a | ADS1299-4 no usa 8 canales | No leer/escribir | OK |
| BIAS_SENSP | 0x0D | `writeReg(...,0x00)` | `0x00` | Selecciona entradas P que contribuyen al BIAS amplifier | Sin derivacion BIAS, cuerpo queda flotante | Pendiente BIAS |
| BIAS_SENSN | 0x0E | `writeReg(...,0x00)` | `0x00` | Selecciona entradas N que contribuyen al BIAS amplifier | Igual | Pendiente BIAS |
| LOFF_SENSP | 0x0F | active mask CH1-CH4 | `0x0F` | Habilita lead-off en P | Puede contaminar pruebas de ruido/BIAS | Desactivar para pruebas BIAS iniciales |
| LOFF_SENSN | 0x10 | active mask CH1-CH4 | `0x0F` | Habilita lead-off en N | Igual | Desactivar para pruebas BIAS iniciales |
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

## Diseño de pruebas BIAS/DRL

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

### Prueba C - BIAS derivado de CH1-CH4 P+N

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

### Prueba D - BIAS measurement

Objetivo: medir BIASIN/BIASREF por MUX para comprobar que el nodo BIAS existe.

Esta prueba no debe mezclarse con captura EEG porque cambia el MUX del canal.

Registros:

- CONFIG3 con BIAS_MEAS=1 si se quiere medir ruta BIAS.
- CH1SET MUX = `ADS_MUX_BIAS_MEAS`.

Criterio:

- Captura diagnostica separada, no interpretarla como EEG.

## Orden recomendado

1. Corregir CONFIG1/CONFIG3 bits fijos.
2. Compilar normal, capturar baseline sin BIAS con LOFF sense off.
3. Activar BIAS CH1P+CH1N.
4. Capturar quiet/rest, eyes open, eyes closed.
5. Revisar tabla multicanal de `quality_report.md`.
6. Probar `bias_ch1_only_loff_off` para apagar CH2-CH4 y descartar entradas flotantes.
7. Comparar RMS, ptp, peak 25 Hz, alpha y 50 Hz.
8. Solo probar CH1-CH4 en BIAS si esos canales no estan flotantes.

## Decision pendiente

Antes de implementar los modos BIAS en firmware, confirma:

- Donde esta conectado fisicamente BIASOUT/DRL.
- Si hay electrodo BIAS dedicado y en que posicion lo colocaras.
- Si CH2-CH4 estan conectados a electrodos reales o flotantes.
- Si quieres primero aplicar la correccion de bits fijos CONFIG1/CONFIG3.
