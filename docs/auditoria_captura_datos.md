# Auditoria captura-datos

Rama auditada: `captura-datos`, creada desde la rama local real `sonification-pianoscrollui`.

Alcance aplicado: auditoria y herramientas no invasivas. No se han cambiado registros ADS1299, pines, `BLOCK_SAMPLES`, evento Bridge, conversion 24-bit, LSB, ni filtros principales.

Referencias tecnicas usadas:

- Datasheet TI ADS1299/ADS1299-4/ADS1299-6 Rev. C, SBAS499C, especialmente secciones 9.4, 9.5, 9.6, 10 y 11.1: https://www.ti.com/lit/ds/sbas499c/sbas499c.pdf
- Codigo local en `sketch/`, `python/` y `assets/`.

## Auditoria firmware ADS1299 / MCU

| Elemento | Archivo | Funcion/metodo | Configuracion actual | Segun datasheet | Riesgo | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| Pines ADS1299 | `sketch/sketch.ino` | constantes `PIN_*` | CS D10, DRDY 7, START D9, RESET D8, PWDN D5 | Correcto si coincide con PCB/wiring | Cambiarlos rompe hardware | OK |
| SPI | `ADS1299_SafeSPI.cpp` | `begin()` | 2 MHz, MSBFIRST, SPI_MODE1 | SPI compatible; modo 1 es el usado normalmente para ADS1299 | Verificar timing en placa | OK |
| Power-up | `ADS1299Plus.cpp` | `begin()` | espera 5 ms, SPI begin, RESET command, STOP, SDATAC | Tras reset y antes de registros debe evitarse RDATAC para WREG/RREG | Falta validar tiempos exactos de 11.1 en placa | Pendiente de confirmar con datasheet |
| ID | `ADS1299Plus.cpp` | `begin()`, `readDeviceID()` | valida ADS1299 y variante 4 canales; ID observado esperado 0x3C | ID bits incluyen familia y numero de canales | Si ID cambia, no arranca | OK |
| SDATAC antes de WREG | `ADS1299Plus.cpp` | `configureDefaults()` | `cmdStop(); cmdSDATAC();` antes de escribir registros | Necesario porque el dispositivo puede estar en RDATAC | Bajo | OK |
| CONFIG1 | `ADS1299_Registers.h` | `ADS_CFG1_250SPS` | `0x86`: 250 SPS, clock out off, no multiple readback | CONFIG1 requiere bit7=1 y bits4:3=10; DR=110 para 250 SPS | Comentario `DAISY_EN` puede estar semanticamente invertido frente a Rev. C | Dudoso |
| CONFIG2 | `ADS1299_Registers.h` | `ADS_CFG2_TEST_OFF` | test interno desactivado | Test signal se activa con INT_CAL y MUX test | Correcto para captura real | OK |
| CONFIG3 | `ADS1299_Registers.h` | `ADS_CFG3_INTREF_NO_BIAS` | refbuf on, BIASREF_INT on, BIAS off | PD_REFBUF=1 habilita referencia; PD_BIAS=0 apaga bias | Sin BIAS/DRL puede empeorar CMRR en cabeza real | Pendiente de prueba real |
| LOFF | `ADS1299_Registers.h` | `ADS_LOFF_DCAC_24nA_31Hz_80pct` | lead-off AC/DC 24 nA, 31.2 Hz, umbral 80% | Lead-off interno soportado | Puede inyectar componente cercana a bandas EEG si no se interpreta | Dudoso |
| CH1-CH4 | `ADS1299Plus.cpp` | `setChannel()` | canales 1..4 ON, gain 24, mux normal diferencial, SRB2 off | CHnSET permite entrada normal diferencial | CH2-CH4 quedan activos aunque ahora solo se evalua CH1 | OK |
| CH5-CH8 | `ADS1299Plus.h` | `validCh_()` | driver limitado a 4 canales; no escribe CH5-CH8 | ADS1299-4 no tiene 8 canales utiles | No se leen canales inexistentes | OK |
| BIAS derivation | `ADS1299Plus.cpp` | `BIAS_SENSP/N` | 0x00, no se usa BIAS/DRL | Datasheet permite derivacion por canal para BIASOUT | Sin BIAS puede aumentar ruido comun 50 Hz | Pendiente de prueba real |
| START | `sketch.ino` | `setup()` | pin START HIGH tras configurar; no usa `cmdStart()` | START pin alto inicia conversion continua si configurado | Correcto si pin START esta cableado y estable | OK |
| RDATAC | `sketch.ino` | `setup()` | `cmdRDATAC()` tras START | RDATAC entrega frames tras DRDY | Correcto | OK |
| DRDY | `sketch.ino` | ISR `onDrdyFalling()` | interrupcion FALLING, contador volatil | DRDY indica dato listo | `drdy_count` no es FIFO; codigo lee solo un frame y cuenta lag | OK |
| Frame RDATAC | `ADS1299Plus.cpp` | `readFrameRDATAC()` | 3 status + 3*4 canales = 15 bytes | Formato: 24 bits status + 24 bits por canal activo | Correcto para ADS1299-4 | OK |
| Status | `ADS1299Plus.h` | `statusHasSync()` | valida `0xF00000 == 0xC00000` | STATUS[23:20] = 1100b | No expone LOFF en snapshot aun salvo status crudo | OK |
| 24-bit signed | `ADS1299Plus.h` | `unpack24()` | extension de signo por bit 23 | Two's complement de 24 bits | Correcto | OK |
| Counts a uV | `sketch.ino` | loop real | `raw * 2.235e-8 V`, filtros, `*1e6` | Ideal: LSB = Vref / gain / (2^23 - 1) | Debe confirmarse Vref real y gain; el LSB implica Vref aprox 4.5 V con gain 24 | Pendiente de confirmar con datasheet |
| Filtros MCU | `sketch.ino`, `filters.h` | `initFilters()` | HP 0.5 Hz, notch 50 Hz, LP 40 Hz | Filtros externos al ADS1299 | Pueden deformar diagnostico si no existe raw/unfiltered | Pendiente de prueba real |
| Bridge | `streaming.h` | `publishPendingBlocks()` | `Bridge.notify("eeg_block_uV", block, first_idx, count, 8*(status+4ch))` | No aplica al datasheet | Notify puede bloquear; se mide tiempo | OK |
| Monitor prints | `sketch.ino` | debug/bench | prints cada 500 samples y reporte 5 s | No aplica | Exceso puede afectar timing si Monitor lento | Dudoso |
| Handshake Linux | `sketch.ino` | `checkMpuReady()` | `Bridge.call("linux_started")` a 1 Hz hasta listo | No aplica | RPC sincronico fuera de ruta cuando listo | OK |

## Auditoria ADS1299-4PAG vs codigo

| Punto | Esperado ADS1299-4PAG | Codigo actual | Resultado |
| --- | --- | --- | --- |
| Numero de canales | 4 | `ADS1299Plus::NUM_CHANNELS = 4` | OK |
| ID | ADS1299-4 con NU_CH=00; observado 0x3C | `begin()` exige NU_CH=00 | OK |
| Bytes por frame | 3 + 4*3 = 15 | `uint8_t rxBuf[3 + 3 * NUM_CHANNELS]` | OK |
| Status bytes | 3 bytes iniciales | `status24 = rxBuf[0..2]` | OK |
| CH1-CH4 | 4 canales de 24 bits | bucle `i < NUM_CHANNELS` | OK |
| CH5-CH8 | No leer/enviar | no existen en driver actual | OK |
| Firmware envia 4 canales | Si | payload fijo con CH0..CH3 | OK |
| Python espera 4 canales | Si | `NUM_CH = 4`, stride `1 + num_ch` | OK |
| Canal 1 firmware a Python | CH1 ADS -> `ch_uV[0]` -> `ch1_uV`/indice 0 | `channel_idx=0` en DSP | OK |
| Bloques | 8 muestras | `BLOCK_SAMPLES = 8` y receiver espera 8 | OK |

## Auditoria SPI / DRDY / RDATAC

La secuencia real es:

1. `Bridge.begin()` y `Monitor.begin()`.
2. Configuracion de pines ADS1299.
3. `attachInterrupt(DRDY, FALLING)`.
4. `safeSpi.begin()` con SPI mode 1 a 2 MHz.
5. `ads.begin()`: RESET command, STOP, SDATAC, lectura ID.
6. `ads.configureDefaults()`: STOP, SDATAC, WREG de CONFIG/LOFF/CHn/BIAS/LOFF/GPIO/MISC1/CONFIG4.
7. `START` por pin alto, 10 ms.
8. `RDATAC`.
9. En `loop()`, si `drdy_count > 0`, se lee un frame actual. Si `pending > 1`, se cuenta lag y no intenta drenar varios frames.

Estado: razonable y compatible con el datasheet, pendiente de confirmar tiempos exactos y estabilidad real con capturas.

## Auditoria conversion counts -> uV

La conversion actual usa `LSB_V = 2.235e-8`. Con gain 24, esto equivale a una referencia aproximada:

`Vref ~= LSB_V * gain * (2^23 - 1) = 4.499 V`

Esto encaja con referencia interna de 4.5 V del ADS1299, pero debe quedar validado con test signal interno o entrada shorted. La conversion signed 24-bit esta correctamente implementada.

## Auditoria filtros MCU y Python

Firmware:

- DC blocker/high-pass 0.5 Hz.
- Notch 50 Hz.
- Low-pass 40 Hz.
- Salida a Python ya filtrada y en microvoltios enteros.

Python:

- No aplica filtros EEG adicionales al buffer principal.
- `DSPCore.preprocess()` hace detrend lineal y correccion opcional de outliers antes de PSD.
- Multitaper opera sobre la ventana reciente recibida desde MCU.

Riesgo: para validar adquisicion real faltaba persistir raw counts o al menos una ruta diagnostica no filtrada. En esta fase no se modifica firmware para enviar raw; las capturas nuevas documentan que solo hay uV filtrados.

Respuesta tecnica: no conviene anadir mas filtros para "definir mejor" bandas EEG antes de capturar datos reales. Primero hay que medir drift, 50 Hz, saturacion, artefactos de parpadeo/EMG y comparar ojos abiertos/cerrados. Multitaper reduce varianza espectral, pero no sustituye una mitigacion fisica o un filtro antirruido cuando hay contaminacion clara.

## Auditoria analisis espectral multitaper

- Ventana principal: 4 s a 250 Hz = 1000 muestras.
- Resolucion frecuencial teorica: 0.25 Hz.
- Hop de features: 64 muestras = 256 ms.
- Metodo principal: DPSS multitaper, `NW=2.5`, `K=4`.
- Bandas: delta 0.5-4, theta 4-8, alpha 8-13, beta 13-30, gamma 30-50.
- `bandpower_abs`: integra PSD por banda y reescala para aproximar la potencia temporal de la ventana.
- `bandpower_rel`: normaliza por suma de bandas.
- Picos: maximo global y maximo por banda.
- Control actual: evita ventanas <4 muestras, limpia NaN/Inf al publicar JSON, detecta clipping/outliers en `DSPCore`.

Riesgos pendientes:

- La PSD principal usa la senal ya filtrada por MCU, por tanto no permite demostrar si el firmware esta deformando la senal.
- Gamma llega hasta 50 Hz aunque el notch de 50 Hz y LP 40 Hz reducen el extremo alto; interpretar gamma con cautela.
- `bandpower_abs` no debe usarse como calibracion fisica definitiva hasta validar la normalizacion con senal test.

## Herramientas creadas

### Captura real

`python/tools/capture_eeg_quality.py`

Desde el terminal normal de la UNO Q crea una peticion en `state/capture_request.json`.
La app App Lab, mientras esta corriendo, escucha esa peticion y graba los bloques
reales que recibe por `Bridge.notify("eeg_block_uV")`.

Guarda:

- `captures/<timestamp>_<condition>/metadata.json`
- `captures/<timestamp>_<condition>/eeg_timeseries.csv`

Campos CSV:

- `t_capture_sec`
- `timestamp_unix`
- `block_idx`
- `sample_idx`
- `sample_in_block`
- `status`
- `ch1_uV` ... `ch4_uV`

Limitacion declarada: el firmware actual no envia raw counts, asi que `raw_counts_available=false`.

### Analisis offline

`python/tools/analyze_eeg_capture.py`

Genera:

- `quality_report.json`
- `quality_report.md`
- `spectral_summary.csv`

Metricas:

- duracion, fs efectiva, muestras recibidas, gaps.
- invalid status.
- RMS, media, mediana, std, pico-pico, percentiles.
- saturacion estimada frente a rango ADC.
- flatline, saltos bruscos.
- PSD multitaper, bandpowers, picos, potencia 50 Hz y ratio 50 Hz / 1-50 Hz.
- diagnostico preliminar y recomendaciones.

## UI diagnostica

Se anadio seccion `Calidad EEG / Diagnostico ADS1299` con:

- RMS CH1.
- pico-pico.
- offset.
- ratio 50 Hz.
- saturacion.
- saltos bruscos.
- warnings.
- traza temporal reciente CH1.

La UI solo consume `snapshot.diagnostics`; no inicia capturas ni modifica el backend.

## Protocolo de prueba en placa

Actualizar rama:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
git fetch
git checkout captura-datos
git pull
```

Instalar dependencias si fuese necesario:

```bash
python -m pip install -r python/requirements.txt
```

Ejecutar app normal en App Lab para confirmar streaming y UI. Luego ejecutar capturas CLI desde la placa:

```bash
python3 python/tools/capture_eeg_quality.py --condition head_fp1_fp2_eyes_open --duration 60
python3 python/tools/analyze_eeg_capture.py captures/<capture_id>
```

Importante: `capture_eeg_quality.py` requiere que la app App Lab este corriendo en
la misma rama, porque la recepcion Bridge vive dentro de `python/main.py`. El script
CLI solo solicita la captura y espera a que la app la complete.

Capturas recomendadas en orden:

```bash
python3 python/tools/capture_eeg_quality.py --condition head_fp1_fp2_eyes_open --duration 60
python3 python/tools/capture_eeg_quality.py --condition head_fp1_fp2_eyes_closed --duration 60
python3 python/tools/capture_eeg_quality.py --condition blink_test --duration 60
python3 python/tools/capture_eeg_quality.py --condition jaw_movement_test --duration 60
```

Analizar cada captura:

```bash
python3 python/tools/analyze_eeg_capture.py captures/<capture_id>
```

Archivos que debes devolver/subir para analisis:

- `metadata.json`
- `eeg_timeseries.csv`
- `quality_report.json`
- `quality_report.md`
- `spectral_summary.csv`

## Propuestas no aplicadas

No aplicar hasta tener capturas reales:

| Propuesta | Registro/area | Motivo | Riesgo | Requiere aprobacion |
| --- | --- | --- | --- | --- |
| Modo test signal interno | CONFIG2 + CHnSET MUX test | Validar escala y SPI con senal conocida | Cambia entrada real | Si |
| Modo shorted inputs | CHnSET MUX short | Medir ruido interno y offset | Cambia configuracion de canal | Si |
| Ruta raw/unfiltered diagnostica | Firmware + receiver | Separar adquisicion real de filtros MCU | Cambia payload o agrega evento | Si |
| BIAS/DRL | CONFIG3 + BIAS_SENSP/N | Reducir modo comun/50 Hz en cabeza real | Seguridad/conexion fisica | Si |
| Revisar lead-off durante EEG | LOFF/LOFF_SENSP/N/CONFIG4 | Evitar inyeccion/artefacto si molesta | Puede afectar contacto/senal | Si |
| Ajustar notch/LP/gamma | `filters.h`/DSP | Si datos muestran deformacion o ruido | Puede cambiar features | Si |
