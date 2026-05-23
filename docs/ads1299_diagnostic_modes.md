# ADS1299 diagnostic modes

Estos modos son pruebas temporales para aislar si las amplitudes en milivoltios
vienen del montaje de electrodos/common-mode o de la cadena ADC/configuracion.

El modo normal no cambia:

```cpp
#define ADS_DIAGNOSTIC_MODE 0
```

Modos disponibles en `sketch/sketch.ino`:

| Valor | Nombre | Uso |
| --- | --- | --- |
| 0 | normal | Captura real INxP-INxN, modo EEG actual |
| 1 | shorted_inputs | MUX interno en corto CH1-CH4, lead-off sense desactivado |
| 2 | test_signal_internal | CONFIG2 test interno + MUX TESTSIG CH1-CH4 |

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
con una señal generada dentro del ADS1299.

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

- Debe aparecer una señal periodica lenta coherente entre canales.
- Si la frecuencia/escala no tienen sentido, revisar CONFIG2, LSB, ganancia y Vref.

## Volver a EEG real

Despues de cada prueba diagnostica, volver a:

```bash
python3 python/tools/set_ads_diagnostic_mode.py normal
```

Compilar/subir de nuevo antes de cualquier captura con electrodos.

## Importante

Estos modos no son mejoras permanentes de adquisicion. Son pruebas controladas.
No deben mezclarse con capturas `head_fp1_fp2_*` porque desconectan la ruta real
de electrodos a nivel de MUX interno del ADS1299.
