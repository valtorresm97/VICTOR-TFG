# 02. Auditoria firmware / MCU - final-v4

## 1. Objetivo

Este documento explica el firmware de la Arduino UNO Q desde una perspectiva narrativa y de arquitectura. La auditoria funcion por funcion mas exhaustiva esta en:

```text
docs/auditoria_codigo_detallada/01_firmware_funcion_por_funcion.md
docs/auditoria_codigo_detallada/02_ads1299_spi_driver.md
```

Aqui se resume que hace cada bloque del firmware, que configuracion final-v4 esta activa, que contratos no se deben romper y que partes son laterales.

Estado actual de referencia:

```text
Rama integrada: firmware-final-v4
Rama documental: refactor/essential-eeg-midi-plan
```

## 2. Papel del firmware en el sistema

El firmware ejecuta la parte de tiempo real del sistema EEG-MIDI. Sus tareas principales son:

```text
configurar ADS1299
esperar DRDY
leer frames RDATAC por SPI
validar status ADS1299
convertir counts a voltios
filtrar en MCU
convertir a microvoltios
agrupar muestras en bloques de 8
publicar Bridge.notify("eeg_block_uV")
recibir Bridge.call("midi_bytes") desde Python
enviar bytes MIDI por Serial1/D1 con TX invertido
emitir metricas benchmark por Monitor
```

El firmware no calcula PSD, bandpowers ni sonificacion. Esa parte vive en Python.

## 3. Responsabilidades por archivo

| Archivo | Responsabilidad | Criticidad | Lectura final-v4 |
| --- | --- | --- | --- |
| `sketch/sketch.ino` | Firmware principal: Bridge/Monitor, ADS1299, DRDY, filtros, streaming, MIDI UART, LED handler y bench. | Critico | Centro del tiempo real MCU. |
| `sketch/ADS1299Plus/src/ADS1299Plus.*` | Driver alto nivel ADS1299: power-up, comandos, registros, RDATAC y unpack signed 24-bit. | Critico | Protege ID, variante 4ch, status y frames. |
| `sketch/ADS1299Plus/src/ADS1299_Registers.h` | Constantes de comandos, registros, mascaras y defaults ADS1299. | Critico | Cualquier cambio requiere datasheet y prueba. |
| `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.*` | Wrapper SPI 2 MHz, MSBFIRST, SPI_MODE1 y CS manual. | Critico | Capa baja del ADC. |
| `sketch/filters.h` | DC blocker/HP 0.5 Hz, notch 50 Hz, LP 40 Hz y conversion a microvoltios. | Critico | Cambia directamente el espectro que llega a Python. |
| `sketch/streaming.h` | `EegBlockUV`, ring TX y payload `eeg_block_uV`. | Critico | Contrato MCU-Python. |
| `sketch/bench.h` | Contadores de rendimiento, colas, filtros, notify y lag. | Medio/alto | Evidencia temporal MCU sin trafico Bridge extra. |
| `sketch/synthetic.h` | Senal sintetica EEG-like para test sin ADS1299. | Medio | Diagnostico, no evidencia final TFG. |
| `sketch/sketch.yaml` | Dependencias firmware/App Lab. | Medio | Mantiene librerias locales ADS/SPI. |

## 4. Pines y perifericos

| Recurso | Valor final-v4 | Archivo | Observacion |
| --- | --- | --- | --- |
| `PIN_CS` | `D10` | `sketch.ino` | CS ADS1299 activo bajo. |
| `PIN_SCLK` | `SCK` | `sketch.ino` | SPI clock. |
| `PIN_MOSI` | `MOSI` | `sketch.ino` | DIN ADS1299. |
| `PIN_MISO` | `MISO` | `sketch.ino` | DOUT ADS1299. |
| `PIN_DRDY` | `7` | `sketch.ino` | Interrupcion FALLING. No cambiar sin placa. |
| `PIN_START` | `D9` | `sketch.ino` | Se pone HIGH antes de RDATAC. |
| `PIN_RESET` | `D8` | `sketch.ino` | Reset digital ADS1299. |
| `PIN_PWDN` | `D5` | `sketch.ino` | Se mantiene HIGH. |
| SPI | 2 MHz, MSBFIRST, SPI_MODE1 | `ADS1299_SafeSPI.cpp` | Configuracion conservadora validada. |
| Bridge | RouterBridge | `sketch.ino`, `streaming.h` | `call` para handshake/handlers, `notify` para EEG. |
| MIDI UART | `Serial1`/D1 | `sketch.ino` | `MIDI_UART_ENABLED=1`; TX invertido obligatorio. |
| LED Matrix | Arduino_LED_Matrix | `sketch.ino` | Solo dibuja si `LED_MATRIX_ENABLED=1`; final-v4 lo deja en 0. |

## 5. Configuracion ADS1299 final-v4

El ADS1299 esperado es la variante de 4 canales. El driver valida familia ADS1299 y variante 4ch al arrancar.

Parametros relevantes:

```text
ADS_DIAGNOSTIC_MODE=5
CONFIG1 = 250 SPS
CONFIG2 = test interno off
CONFIG3 = referencia interna + BIAS segun modo
Frame RDATAC = 15 bytes = 3 status + 4*3 canales
Status valido = (status & 0xF00000) == 0xC00000
LSB_V = 2.235e-8
```

El modo final de capturas es:

```text
bias_ch1_only_loff_off
```

Interpretacion:

- CH1 es el canal EEG principal.
- BIAS se deriva de CH1P + CH1N.
- CH2-CH4 se apagan/cortocircuitan en configuracion de canal.
- Lead-off sense queda desactivado.
- El payload sigue incluyendo CH1-CH4 por contrato, aunque solo CH1 se interpreta como EEG activo en las capturas finales.

## 6. Secuencia de arranque

La secuencia conceptual en `setup()` es:

```text
Bridge.begin()
Monitor.begin()
registro handlers midi_bytes y led_matrix_row
configuracion MIDI UART + TX invertido
reset de contadores y filtros
configuracion pines ADS1299
safeSpi.begin()
ads.begin()
ads.configureDefaults()
applyAdsDiagnosticMode()
attachInterrupt(DRDY falling)
START high
cmdRDATAC()
```

Punto de deuda tecnica documentado:

```text
sketch.ino llama safeSpi.begin()
ads.begin() vuelve a llamar spi_.begin()
```

El sistema esta validado asi, por lo que no se toca en esta fase. En una simplificacion futura debe revisarse solo con placa y prueba ADS ID/RDATAC/status.

## 7. Loop real de adquisicion

El `loop()` mantiene el flujo de tiempo real:

```text
1. comprobar si Python/Linux esta listo con Bridge.call("linux_started")
2. leer drdy_count acumulado
3. si pending > 0, leer un frame RDATAC
4. reconstruir status + CH1..CH4 signed 24-bit
5. validar status ADS1299
6. convertir raw counts a voltios con LSB_V
7. aplicar filtros MCU por canal
8. convertir a microvoltios enteros
9. llenar TxBlockRing
10. publicar bloques pendientes por Bridge.notify("eeg_block_uV")
11. enviar reportes benchmark por Monitor si toca
```

La ISR `onDrdyFalling()` es deliberadamente minima: solo incrementa `drdy_count`. Esto evita hacer SPI o Bridge dentro de una interrupcion.

## 8. Contrato `eeg_block_uV`

El contrato firmware -> Python es:

```text
Bridge.notify(
  "eeg_block_uV",
  block_idx,
  first_sample_idx,
  sample_count,
  8 * (status, ch1_uV, ch2_uV, ch3_uV, ch4_uV)
)
```

Este contrato implica:

```text
FS_HZ=250
BLOCK_SAMPLES=8
NUM_CHANNELS=4
bloques esperados ~= 31.25 bloques/s
status por muestra
microvoltios enteros
```

No se debe cambiar `BLOCK_SAMPLES`, orden de campos ni numero de canales sin actualizar:

```text
python/eeg_contract.py
python/receiver.py
python/capture_manager.py
tools offline
reportes de validacion
```

La ruta antigua de muestra individual `eeg_frame_uV` queda como compatibilidad historica en Python, no como ruta firmware final-v4.

## 9. Filtros MCU

El firmware aplica filtrado antes de enviar datos a Python:

```text
DC blocker / high-pass 0.5 Hz
notch 50 Hz
low-pass 40 Hz
```

Consecuencia:

- Python recibe una senal ya filtrada.
- `DSPCore` no aplica los filtros EEG principales en el loop live.
- El espectro, quality gate y bandpowers dependen de estos filtros MCU.
- No existe una ruta raw/unfiltered runtime final-v4 para comparar directamente.

Cualquier cambio en filtros exige nuevas capturas y nueva validacion espectral.

## 10. MIDI fisico desde firmware

El firmware expone el handler:

```text
midi_bytes(n, b0, b1, b2)
```

Python llama:

```text
Bridge.call("midi_bytes", n, b0, b1, b2)
```

El firmware envia los bytes por:

```text
Serial1 / D1 / 31250 baudios
```

Punto critico:

```text
USART_CR2_TXINV es obligatorio
```

Sin TX invertido, los bytes pueden ser logicamente correctos pero el circuito MIDI OUT validado no funciona correctamente. Por eso `midiConfigureTxPolarity()` es una funcion critica hardware.

El self-test MIDI del MCU existe, pero permanece apagado:

```text
MIDI_MCU_SELF_TEST_ENABLED=0
```

No debe confundirse con la sonificacion EEG real generada en Python.

## 11. LED matrix

El firmware tambien registra:

```text
led_matrix_row(row_idx, chunk0, chunk1, chunk2)
```

Pero en final-v4:

```text
LED_MATRIX_ENABLED=0
EEG_LED_MATRIX_ENABLED=False
```

La matriz LED es un subsistema lateral. No genera musica, no afecta al DSP y no es necesario para MIDI. Si se activa en el futuro, debe medirse porque puede anadir llamadas Bridge adicionales.

## 12. Benchmarks MCU

El firmware conserva instrumentacion en `bench.h` y reporta por Monitor/App Lab:

```text
[BENCH] EEG_MIDI ...
```

Decision final-v4 importante:

```text
No se envia benchmark MCU por Bridge.
```

Motivo: anadir un canal Bridge para metricas contaminaria el propio canal que se queria medir. En su lugar, se copia el Monitor y se parsea offline con:

```text
python/tools/parse_mcu_bench_monitor.py
```

Metricas relevantes:

- `filt_avg_us`;
- `filt_max_us_win`;
- `notify_avg_us`;
- `notify_max_us_win`;
- `loop_max_us_win`;
- `qmax_global`;
- `drops_total`;
- `pub_burst_global`;
- lag/DRDY;
- tasas de generacion/envio.

El presupuesto temporal del MCU por bloque es:

```text
8 / 250 = 0.032 s = 32 ms
```

Los benchmarks finales muestran que el coste dominante es `Bridge.notify`, no los filtros MCU.

## 13. Enabled por defecto

| Configuracion | Valor final-v4 | Efecto |
| --- | --- | --- |
| `USE_SYNTHETIC` | `0` | Captura real ADS1299. |
| `ADS_DIAGNOSTIC_MODE` | `5` | CH1-only con BIAS CH1P+CH1N, CH2-CH4 apagados y lead-off off. |
| `DEBUG_MONITOR` | `true` | Prints limitados cada 500 muestras y errores. |
| `EEG_STREAMING_NOTIFY_ENABLED` | `1` | Envia bloques EEG por Bridge si MPU listo. |
| `BENCH_NOTIFY_ENABLED` | alias legacy | Compatibilidad: si se define externamente, controla `EEG_STREAMING_NOTIFY_ENABLED`. |
| `BENCH_REPORT_ENABLED` | `1` | Activa informes benchmark por Monitor. |
| `BENCH_REPORT_EVERY_MS` | `5000` | Reporte bench cada 5 s. |
| `LED_MATRIX_ENABLED` | `0` | Handler registrado, pero no dibuja. |
| `MIDI_UART_ENABLED` | `1` | Handler registrado y escribe UART MIDI fisica. |
| `MIDI_SERIAL` | `Serial1` | UART validada en D1/TX. |
| `MIDI_MCU_SELF_TEST_ENABLED` | `0` | Arpegio diagnostico MCU apagado en flujo EEG normal. |

## 14. Riesgos firmware principales

- Cambiar `ADS_DIAGNOSTIC_MODE` cambia la interpretacion de canales y la comparabilidad de capturas.
- Cambiar SPI mode/velocidad puede romper ID, registros o RDATAC.
- Cambiar `LSB_V` o ganancia cambia amplitudes uV, quality gate y features.
- Cambiar filtros MCU cambia el contenido espectral que llega a Python.
- Cambiar `BLOCK_SAMPLES` rompe el contrato `eeg_block_uV`.
- Cambiar `MIDI_SERIAL` o quitar TXINV rompe MIDI fisico.
- Aumentar prints Monitor puede introducir jitter.
- Activar LED puede aumentar carga de Bridge.
- `pending > 1` se cuenta como lag, pero no recupera todos los frames no leidos.
- No hay ruta raw/unfiltered runtime para separar adquisicion cruda y efecto de filtros.
- La doble inicializacion SPI es una deuda tecnica a revisar solo con prueba real.

## 15. Pruebas minimas antes de tocar firmware

Si en el futuro se modifica firmware:

1. Compilar en Arduino App Lab.
2. Confirmar `ADS1299 ID=0x3C` en Monitor.
3. Confirmar modo `bias_ch1_only_loff_off` si se busca comparabilidad final-v4.
4. Confirmar `START + RDATAC` activo.
5. Confirmar status `0xC00000`.
6. Confirmar `rx_frame_rate_hz ~= 250`.
7. Confirmar `rx_block_rate_hz ~= 31.25`.
8. Confirmar `drops_total=0` en benchmark.
9. Probar `/midi/panic` y nota MIDI fisica.
10. Realizar captura corta y revisar `eeg_timeseries.csv`.
11. Si se toca filtro/ADS, repetir validacion espectral.
12. Si se toca Bridge/timing, repetir benchmark MCU/Python.

## 16. Relacion con futura version esencial/UML

En UML principal deben aparecer:

```text
ADS1299Plus / ADS1299_SafeSPI
setup / loop
onDrdyFalling
readFrameRDATAC
filtros MCU
TxBlockRing
Bridge.notify("eeg_block_uV")
midi_bytes
Serial1/D1 TXINV
```

Como laterales:

```text
bench.h / Monitor benchmarks
led_matrix_row
synthetic.h
MIDI_MCU_SELF_TEST
```

Como deuda tecnica a revisar despues:

```text
doble safeSpi.begin()
comentarios historicos sobre ADS mode normal
nombres legacy de macros BENCH_NOTIFY_ENABLED
```

## 17. Conclusion

El firmware final-v4 queda validado como capa de adquisicion y transporte de tiempo real:

```text
ADS1299 real -> filtros MCU -> bloques eeg_block_uV -> Python
Python -> midi_bytes -> Serial1/D1 TXINV -> MIDI OUT fisico
```

Su responsabilidad es capturar y transportar datos de forma estable, no interpretar EEG ni generar musica. La interpretacion espectral, quality gate y sonificacion viven en Python. Para el TFG, este documento sirve como descripcion narrativa del bloque firmware; para cambios de codigo, usar la auditoria detallada funcion por funcion.
