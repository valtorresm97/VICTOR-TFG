# ADS1299 diagnostic modes

Documento activo de referencia para los modos de diagnostico ADS1299 usados durante la validacion del proyecto.

Estado final-v4:

```text
Rama integrada actual: firmware-final-v4
Modo usado en las capturas finales s01_20260528: ADS_DIAGNOSTIC_MODE=5
Nombre: bias_ch1_only_loff_off
```

Importante: el modo `0` sigue siendo el modo normal general `INxP-INxN`, pero no es el modo usado en la sesion final documentada `s01_20260528`. En final-v4, las capturas finales se interpretan con CH1 como canal EEG principal y CH2-CH4 apagados/conservados solo por contrato de streaming.

Estos modos son pruebas temporales para aislar si las amplitudes en milivoltios
vienen del montaje de electrodos/common-mode o de la cadena ADC/configuracion.

## Modos disponibles

Modos disponibles en `sketch/sketch.ino`:

| Valor | Nombre | Uso |
| --- | --- | --- |
| 0 | normal | Captura real general INxP-INxN. No fue el modo final de la sesion `s01_20260528`. |
| 1 | shorted_inputs | MUX interno en corto CH1-CH4, lead-off sense desactivado. |
| 2 | test_signal_internal | CONFIG2 test interno + MUX TESTSIG CH1-CH4. |
| 3 | no_bias_loff_off | Entrada real diferencial, BIAS off, lead-off sense off. |
| 4 | bias_ch1pn_loff_off | Entrada real diferencial, BIAS on derivado de CH1P+CH1N, lead-off sense off. |
| 5 | bias_ch1_only_loff_off | CH1 activo, CH2-CH4 apagados, BIAS CH1P+CH1N, lead-off sense off. Modo usado en capturas finales. |

Para capturas comparables con la sesion final de laboratorio:

```bash
python3 python/tools/set_ads_diagnostic_mode.py bias_ch1_only_loff_off
```

Para volver al modo normal general:

```bash
python3 python/tools/set_ads_diagnostic_mode.py normal
```

## Prueba 1: entradas internas en corto

Objetivo: medir ruido/offset interno de la cadena ADS1299 + SPI + filtros + Bridge,
sin electrodos.

Cambiar temporalmente el modo:

```bash
python3 python/tools/set_ads_diagnostic_mode.py shorted_inputs
```

Compilar/subir desde Arduino App Lab en la UNO Q. Luego ejecutar la app y capturar:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
python3 python/tools/capture_eeg_quality.py --condition shorted_inputs --duration 60
CAPTURE_DIR=$(ls -td captures/*_shorted_inputs | head -1)
python3 python/tools/analyze_eeg_capture.py "$CAPTURE_DIR"
cat "$CAPTURE_DIR/quality_report.md"
```

Lectura esperada:

- Si RMS/pico-pico bajan drasticamente frente a Fp1-Fp2, el ADC/streaming escala
  razonablemente y el problema apunta al montaje/electrodos/common-mode.
- Si sigue en milivoltios, sospechar escala, filtros, configuracion ADS1299 o ruido
  interno inesperado.

## Prueba 2: test signal interno

Objetivo: validar reconstruccion 24-bit, escala, ganancia, CONFIG2, MUX y streaming
con una seÃ±al generada dentro del ADS1299.

Cambiar temporalmente el modo:

```bash
python3 python/tools/set_ads_diagnostic_mode.py test_signal_internal
```

Compilar/subir desde Arduino App Lab. Luego:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
python3 python/tools/capture_eeg_quality.py --condition test_signal_internal --duration 60
CAPTURE_DIR=$(ls -td captures/*_test_signal_internal | head -1)
python3 python/tools/analyze_eeg_capture.py "$CAPTURE_DIR"
cat "$CAPTURE_DIR/quality_report.md"
```

Lectura esperada:

- Debe aparecer una seÃ±al periodica lenta coherente entre canales.
- Si la frecuencia/escala no tienen sentido, revisar CONFIG2, LSB, ganancia y Vref.

## Volver despues de pruebas diagnosticas

Despues de cada prueba diagnostica, volver al modo que corresponda al objetivo:

- Para repetir capturas comparables con final-v4: `bias_ch1_only_loff_off`.
- Para pruebas generales INxP-INxN: `normal`.

Ejemplo para volver al modo final-v4:

```bash
python3 python/tools/set_ads_diagnostic_mode.py bias_ch1_only_loff_off
```

Compilar/subir de nuevo antes de cualquier captura con electrodos.

## Importante

Estos modos no son mejoras permanentes de adquisicion. Son pruebas controladas.
No deben mezclarse con capturas `head_fp1_fp2_*` porque desconectan la ruta real
de electrodos a nivel de MUX interno del ADS1299.

## Prueba BIAS/DRL CH1P+CH1N

Usar solo si `RLD_DRV` esta conectado fisicamente al electrodo RLD/DRL mediante
la red de proteccion/limitacion de corriente de la PCB.

Primero baseline sin BIAS y sin lead-off:

```bash
python3 python/tools/set_ads_diagnostic_mode.py no_bias_loff_off
```

Compilar/subir desde Arduino App Lab. Arrancar la app y capturar:

```bash
python3 python/tools/capture_eeg_quality.py --condition head_fp1_fp2_no_bias_loff_off_quiet_rest --duration 60
CAPTURE_DIR=$(ls -td captures/*_head_fp1_fp2_no_bias_loff_off_quiet_rest | head -1)
python3 python/tools/analyze_eeg_capture.py "$CAPTURE_DIR"
cat "$CAPTURE_DIR/quality_report.md"
```

Despues BIAS/DRL derivado solo de CH1P+CH1N:

```bash
python3 python/tools/set_ads_diagnostic_mode.py bias_ch1pn_loff_off
```

Compilar/subir desde Arduino App Lab. Conectar:

- CH1P = Fp1.
- CH1N = Fp2.
- `RLD_DRV` = electrodo RLD/DRL dedicado.

Capturar:

```bash
python3 python/tools/capture_eeg_quality.py --condition head_fp1_fp2_bias_ch1pn_loff_off_quiet_rest --duration 60
CAPTURE_DIR=$(ls -td captures/*_head_fp1_fp2_bias_ch1pn_loff_off_quiet_rest | head -1)
python3 python/tools/analyze_eeg_capture.py "$CAPTURE_DIR"
cat "$CAPTURE_DIR/quality_report.md"
```

Criterio esperado:

- RMS y pico-pico deben bajar mucho frente al baseline sin BIAS.
- El pico persistente alrededor de 21 Hz debe reducirse o desaparecer.
- `sample gaps` e `invalid status` deben seguir en 0.

Al terminar, volver al modo objetivo. Para final-v4:

```bash
python3 python/tools/set_ads_diagnostic_mode.py bias_ch1_only_loff_off
```

Y compilar/subir de nuevo.

## Prueba CH1 solo, CH2-CH4 apagados

Objetivo: comprobar si canales no usados/flotantes contribuyen al artefacto de
~25 Hz o a las mÃ©tricas.

```bash
python3 python/tools/set_ads_diagnostic_mode.py bias_ch1_only_loff_off
```

Compilar/subir desde Arduino App Lab. Mantener:

- CH1P = electrodo positivo de la prueba.
- CH1N = electrodo negativo de la prueba.
- `RLD_DRV` = electrodo RLD dedicado.

Captura sugerida:

```bash
python3 python/tools/capture_eeg_quality.py --condition bias_ch1_only_fp1_fp2_rld_left_mastoid --duration 60 --timeout-extra 180
DIR=$(ls -td captures/*_bias_ch1_only_fp1_fp2_rld_left_mastoid /app/captures/*_bias_ch1_only_fp1_fp2_rld_left_mastoid 2>/dev/null | head -1)
python3 python/tools/analyze_eeg_capture.py "$DIR"
cat "$DIR/quality_report.md"
```

Comparar la tabla multicanal del informe. CH2-CH4 deberian quedar apagados y no
deben usarse para interpretar EEG.

## Plan candidato: ear EEG CH1-only

Las capturas realizadas indican que el modo mas prometedor, por ahora, es:

- `ADS_DIAGNOSTIC_MODE=5` (`bias_ch1_only_loff_off`).
- CH1P = mastoide/oreja izquierda.
- CH1N = mastoide/oreja derecha.
- `RLD_DRV` = muneca o antebrazo, no cuello/mastoide si aumenta 50 Hz.
- CH2-CH4 apagados; no interpretar sus columnas como EEG.

Motivo: `shorted_inputs` dio ruido interno muy bajo, asi que ADC/SPI/escala no
parecen el problema principal. En cambio, las entradas sin electrodos y Fp1-Fp2
mostraron amplitudes grandes y picos alrededor de 25 Hz. El montaje tipo
ear-EEG con CH1 solo ha mostrado ventanas estables mucho mas limpias, y los
movimientos de mandibula aumentan el artefacto, lo que apunta a EMG/contacto
mas que a fallo digital.

Configurar:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
python3 python/tools/set_ads_diagnostic_mode.py bias_ch1_only_loff_off
```

Compilar/subir desde Arduino App Lab y arrancar la app. Confirmar en Monitor:

```text
ADS1299 DIAG: bias_ch1_only_loff_off (CH1 active, CH2-CH4 powered down, BIAS CH1P+CH1N)
status=0xC00000
```

Capturas recomendadas, una a una:

```bash
python3 python/tools/capture_eeg_quality.py --condition ear_eeg_ch1_only_still_30s --duration 30 --timeout-extra 120
DIR=$(ls -td captures/*_ear_eeg_ch1_only_still_30s /app/captures/*_ear_eeg_ch1_only_still_30s 2>/dev/null | head -1)
python3 python/tools/analyze_eeg_capture.py "$DIR"
cat "$DIR/quality_report.md"
```

```bash
python3 python/tools/capture_eeg_quality.py --condition ear_eeg_ch1_only_eyes_open_60s --duration 60 --timeout-extra 180
OPEN_DIR=$(ls -td captures/*_ear_eeg_ch1_only_eyes_open_60s /app/captures/*_ear_eeg_ch1_only_eyes_open_60s 2>/dev/null | head -1)
python3 python/tools/analyze_eeg_capture.py "$OPEN_DIR"
cat "$OPEN_DIR/quality_report.md"
```

```bash
python3 python/tools/capture_eeg_quality.py --condition ear_eeg_ch1_only_eyes_closed_60s --duration 60 --timeout-extra 180
CLOSED_DIR=$(ls -td captures/*_ear_eeg_ch1_only_eyes_closed_60s /app/captures/*_ear_eeg_ch1_only_eyes_closed_60s 2>/dev/null | head -1)
python3 python/tools/analyze_eeg_capture.py "$CLOSED_DIR"
cat "$CLOSED_DIR/quality_report.md"
```

```bash
python3 python/tools/capture_eeg_quality.py --condition ear_eeg_ch1_only_jaw_movement_30s --duration 30 --timeout-extra 120
JAW_DIR=$(ls -td captures/*_ear_eeg_ch1_only_jaw_movement_30s /app/captures/*_ear_eeg_ch1_only_jaw_movement_30s 2>/dev/null | head -1)
python3 python/tools/analyze_eeg_capture.py "$JAW_DIR"
cat "$JAW_DIR/quality_report.md"
```

Comparar ojos abiertos/cerrados solo si ambas capturas tienen ventanas estables:

```bash
python3 python/tools/compare_eeg_captures.py --open "$OPEN_DIR" --closed "$CLOSED_DIR" --output captures/ear_eeg_ch1_only_open_closed_comparison.json
cat captures/ear_eeg_ch1_only_open_closed_comparison.md
```

Criterio de avance:

- `sample_gaps` = 0 e `invalid_status` = 0.
- RMS global idealmente bajo, pero mirar tambien `CH1 windowed stability`.
- `median_rms_uV` de ventanas cerca de 10-80 uV es una evidencia mejor que el
  RMS global cuando hay algun golpe o movimiento.
- `artifact_window_fraction` debe bajar al fijar cables y evitar mandibula.
- El pico de 25 Hz en reposo no debe dominar; si aparece sobre todo en mandibula,
  tratarlo como EMG/artefacto mecanico.

No activar filtros nuevos ni cambiar ganancia para ocultar estos problemas hasta
tener varias capturas estables comparables.

## Relacion con la sesion final `s01_20260528`

La sesion final de laboratorio usa el criterio CH1-only y se documenta en:

```text
docs/validacion_tfg/10_resultados_captura_final_laboratorio.md
docs/validacion_tfg/reportaje_sesion_final_s01_20260528.md
```

Por tanto, para futuras capturas comparables con la memoria del TFG, el punto de partida recomendado es:

```text
ADS_DIAGNOSTIC_MODE=5
montage=ear_eeg_ch1_only
ADS_MODE=bias_ch1_only_loff_off
```

