# 01. Firmware funcion por funcion - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Re-auditoria final-v4: revisada contra codigo real en `firmware-final-v4` desde la rama documental `refactor/essential-eeg-midi-plan`.

Objetivo de esta re-auditoria: dejar el firmware documentado segun el estado real integrado con benchmarks y capturas finales, sin modificar firmware.

## 1. Responsabilidad global

`sketch/sketch.ino` ejecuta el tiempo real del STM32U585 en la Arduino UNO Q:

```text
Bridge/Monitor
  -> handlers midi_bytes y led_matrix_row
  -> ADS1299 + SPI seguro
  -> DRDY interrupt
  -> RDATAC
  -> reconstruccion signed 24-bit
  -> counts * LSB_V
  -> filtros MCU
  -> microvoltios
  -> bloques de 8 muestras
  -> Bridge.notify("eeg_block_uV")
  -> benchmark por Monitor
```

Tambien contiene:

- salida MIDI fisica por `Serial1`/D1 con TX invertido;
- handler LED matrix en dry-run si LED esta desactivado;
- modo sintetico para pruebas, no para evidencia final TFG;
- modos diagnosticos ADS1299, incluido el modo final `bias_ch1_only_loff_off`.

## 2. Configuracion critica final-v4

| Elemento | Estado real final-v4 | Riesgo |
| --- | --- | --- |
| Pines ADS1299 | `PIN_CS=D10`, `PIN_DRDY=7`, `PIN_START=D9`, `PIN_RESET=D8`, `PIN_PWDN=D5` | Cambiarlos rompe hardware. |
| SPI ADS1299 | `ADS1299_SafeSPI`, SPI MODE1, MSB first, 2 MHz | Cambiar modo/velocidad exige placa y datasheet. |
| Muestreo | `FS_HZ=250.0f` | Debe coincidir con Python. |
| Escala | `LSB_V=2.235e-8f` | Afecta amplitud uV y validacion fisiologica. |
| Canales | `ADS1299Plus::NUM_CHANNELS == 4` | Contrato Python espera 4 canales. |
| Streaming | `BLOCK_SAMPLES=8`, evento `eeg_block_uV` | Cambiarlo rompe `python/eeg_contract.py`. |
| Modo ADS final | `ADS_DIAGNOSTIC_MODE=5` | CH1 activo, CH2-CH4 apagados/cortocircuitados. |
| Lead-off en capturas finales | Off en modo 5 | Evita inyeccion diagnostica. |
| BIAS final | CH1P + CH1N | No incluir canales flotantes. |
| MIDI UART | `MIDI_UART_ENABLED=1`, `MIDI_SERIAL=Serial1` | Ruta validada por D1/TX. |
| TX invertido | `USART1->CR2 |= USART_CR2_TXINV` | Obligatorio para circuito N-audio. |
| Self-test MIDI MCU | `MIDI_MCU_SELF_TEST_ENABLED=0` | No debe sonar en flujo EEG normal. |
| LED matrix | `LED_MATRIX_ENABLED=0` | Subsistema secundario/desactivado. |
| Benchmark MCU | `BENCH_REPORT_ENABLED=1` | Imprime por Monitor; no aÃ±ade payload Bridge. |
| Streaming notify | `EEG_STREAMING_NOTIFY_ENABLED=1` | Activa `Bridge.notify("eeg_block_uV")`. |
| Sintetico | `USE_SYNTHETIC=0` | No usar como evidencia TFG final. |

Nota documental: en `sketch.ino` queda un comentario historico que dice mantener `ADS_DIAGNOSTIC_MODE` en 0 para capturas reales, pero el valor efectivo final-v4 es 5. Para la sesion final `s01_20260528`, la interpretacion correcta es `ADS_DIAGNOSTIC_MODE=5 / bias_ch1_only_loff_off`.

## 3. Archivos firmware

| Archivo | Responsabilidad | Estado que define/toca | Riesgo |
| --- | --- | --- | --- |
| `sketch/sketch.ino` | Loop real-time, ADS1299, Bridge, MIDI, LED, benchmark | `drdy_count`, `sample_idx`, `txBlocks`, `bench`, filtros, handlers Bridge | Critico: timing, payload, pines, MIDI fisico. |
| `sketch/streaming.h` | Ring de bloques y publicacion Bridge | `TxBlockRing`, `EegBlockUV`, `BLOCK_SAMPLES=8` | Critico: contrato MCU->Python. |
| `sketch/filters.h` | Filtros IIR y conversion V->uV | `DCBlocker`, `Biquad`, notch/LP | Critico: modifica senal. |
| `sketch/bench.h` | Contadores de rendimiento | `BenchStats` | Medio: observabilidad temporal. |
| `sketch/synthetic.h` | Generador EEG-like | RNG y conversion sintetica | Medio: util para pruebas, no evidencia final. |
| `sketch/sketch.yaml` | Librerias App Lab | Dependencias locales y publicas | Critico para build. |
| `sketch/ADS1299Plus/` | Driver ADS1299 | comandos, registros, RDATAC, unpack24 | Critico para ADS/SPI/status. |
| `sketch/ADS1299_SafeSPI/` | SPI seguro | CS/SPI transaction | Critico para ADS1299. |

## 4. Funciones y structs re-auditados

| Archivo | Funcion/struct | Entradas | Salidas | Estado que toca | Que hace | Contratos | Riesgo | Prueba necesaria |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sketch.ino` | `midiConfigureTxPolarity()` | Ninguna | Ninguna | USART1 CR2 | Activa `USART_CR2_TXINV`; deshabilita/rehabilita USART si existe `USART_CR1_UE` | MIDI fisico por Serial1/D1 | Critico: sin inversion el circuito validado no suena | Test con sintetizador y panic. |
| `sketch.ino` | `midiWriteRawByte()` | Byte MIDI | Ninguna | UART `MIDI_SERIAL` | Escribe byte en Serial1 si MIDI esta configurado | `MIDI_SERIAL=Serial1` | Critico si se cambia UART | Test MIDI OUT. |
| `sketch.ino` | `midi_bytes(n,b0,b1,b2)` | Longitud 1..3 y bytes | `bool` | UART `Serial1`/D1 si `MIDI_UART_ENABLED` | Handler Bridge para enviar bytes MIDI al MCU | `Bridge.call("midi_bytes", n,b0,b1,b2)` | TX invertido obligatorio; Monitor imprime solo primeras llamadas y cada 128 llamadas | Test placa con D1/TX invertido y MIDI panic. |
| `sketch.ino` | `led_matrix_row(row_idx,chunk0,chunk1,chunk2)` | Fila y 39 bits en 3 chunks | `bool` | `led_frame_buffer`, `led_rows_received_mask`, LED fisico si enabled | Desempaqueta 13 pixeles de 3 bits por fila | `Bridge.call("led_matrix_row", row,c0,c1,c2)` | Secundario; multiples calls por frame pueden cargar Bridge; con LED off devuelve false | Solo activar si se mide carga LED. |
| `sketch.ino` | `checkMpuReady()` | Ninguna | `bool` | Ninguno | `Bridge.call("linux_started")` para handshake | Python expone `linux_started` | RPC sincronico hasta que Python este listo | Ver que streaming empieza al arrancar Python. |
| `sketch.ino` | `onDrdyFalling()` | ISR pin DRDY | Ninguna | Incrementa `drdy_count` | Marca muestras listas sin hacer SPI en ISR | DRDY activo bajo | Contador no es FIFO; `pending>1` indica lag/perdida temporal | Ver `gen/s~250`, lag bajo. |
| `sketch.ino` | `reportBenchStatsIfDue()` | Timer `millis()` | Prints Monitor | Lee/reset ventana `bench` | Reporta tasas, colas, drops, tiempos filtro/notify/loop | No cambia payload EEG | Monitor puede introducir jitter si se abusa | Parser `parse_mcu_bench_monitor.py`. |
| `sketch.ino` | `initFilters()` | Constantes filtros | Ninguna | Inicializa `hp`, `notch50`, `lp40` | HP 0.5 Hz, notch 50 Hz, LP 40 Hz por canal | Entrada voltios, salida voltios | Cambiar coeficientes cambia DSP fisiologico | Validar con captura real y benchmark. |
| `sketch.ino` | `applyAdsDiagnosticMode()` | Macro `ADS_DIAGNOSTIC_MODE` | `bool` | Registros ADS1299 | Aplica modos normal, short, test, no-bias, BIAS CH1PN y CH1-only | Debe llamarse antes de RDATAC | Critico: puede apagar canales o habilitar BIAS | Confirmar Monitor y captura por modo. |
| `sketch.ino` | `setup()` | Arranque placa | Ninguna | Bridge, Monitor, pines, SPI, ADS, handlers, filtros, UART MIDI | Inicializa sistema, registra handlers, configura ADS, aplica modo diagnostico y arranca RDATAC | Mantiene pines, handler names, modo final-v4 | Critico no tocar sin placa | Compilar y validar ADS ID, DRDY, status, MIDI. |
| `sketch.ino` | `loop()` | Ticks App Lab | Ninguna | Todo el estado runtime | Handshake, lee DRDY, procesa muestras, encola, publica, benchmark | 250 Hz, `eeg_block_uV`, no bloqueo excesivo | Maximo riesgo: timing/adquisicion | Ver rates, drops, status, dashboard, benchmarks. |
| `streaming.h` | `EegBlockUV` | N/A | N/A | Datos de bloque | Guarda `block_idx`, `first_sample_idx`, `sample_count`, status y 4 canales uV | `BLOCK_SAMPLES=8`, 4 canales | Cambiar layout rompe Python | Test parser `eeg_contract.py` + placa. |
| `streaming.h` | `TxBlockRing.resetFillBlock()` | Ninguna | Ninguna | `fill_block`, `next_block_idx` | Prepara bloque actual y asigna `block_idx` | `block_idx` monotono dentro del arranque | Si se reinicia mal se ven saltos | Ver continuidad block_idx. |
| `streaming.h` | `TxBlockRing.resetRing()` | Ninguna | Ninguna | `head/tail/count` | Vacia cola de bloques | Cola circular de 32 bloques | Perder bloques si se llama en streaming | Solo al handshake/reset. |
| `streaming.h` | `TxBlockRing.resetStreamingState()` | Ninguna | Ninguna | Fill + ring | Reset completo de streaming | Usado al inicio y al estar MPU listo | Puede reiniciar indices de bloque | Revisar sample/block continuity. |
| `streaming.h` | `TxBlockRing.enqueueCompletedBlock()` | Bloque completo, bench | `bool` | Ring y contadores | Encola o contabiliza drops | Capacidad 32 | Si se llena, pierde bloques | Validar `drops_total=0`. |
| `streaming.h` | `TxBlockRing.appendSampleToFillBlock()` | `idx`, `status`, `ch_uV[4]` | Ninguna | `fill_block`, ring si lleno | Agrupa 8 muestras | Payload por muestra: status+4 ch | Error rompe sample_count | Validar receiver con bloque completo. |
| `streaming.h` | `TxBlockRing.publishPendingBlocks()` | Bench, max bloques | Bloques enviados | Ring, bench, Bridge | Publica hasta 4 bloques por loop con `Bridge.notify` y mide `notify_dt_us` | Evento `eeg_block_uV`, 43 campos | Critico: payload manual fijo a 8 muestras | Test Python recibe ~31.25 bloques/s. |
| `filters.h` | `round_to_i32()` | Float | `int32_t` | Ninguno | Redondeo half-away-from-zero y saturacion | V->uV int32 | Saturacion mal aplicada altera amplitud | Unit test host si posible. |
| `filters.h` | `volts_to_uV_i32()` | Voltios | uV int32 | Ninguno | Multiplica por 1e6 y redondea | Unidad microvoltios | Escala critica | Comparar con Python. |
| `filters.h` | `DCBlocker.init/process()` | Fc/fs/x | y | `R,x1,y1` | High-pass/DC blocker IIR | Estado por canal | Transitorios iniciales | Prueba seno/drift. |
| `filters.h` | `Biquad.reset/process()` | x | y | `z1,z2` | Filtro IIR DF-II transposed | Coefs normalizados | Inestabilidad si coefs malos | Prueba frecuencia. |
| `filters.h` | `makeNotch()` | f0, fs, r | `Biquad` | Ninguno | Notch 50 Hz | r=0.95 actual | Puede atenuar banda cercana | PSD sintetico 50 Hz. |
| `filters.h` | `makeLowpassRBJ()` | fc, fs, Q | `Biquad` | Ninguno | LP 40 Hz RBJ | Q=0.707 | Afecta gamma | Comparar respuesta. |
| `bench.h` | `BenchStats` | N/A | N/A | Contadores totales/ventana | Metricas de generacion, envio, colas y latencias | No debe controlar streaming | Bajo/medio | Monitor report coherente. |
| `synthetic.h` | `generateSyntheticRaw()` | sample_idx, fs, LSB, array | Llena `ch_raw` | RNG | Genera counts 24-bit por canal | Mismo pipeline posterior que ADS | No valida DRDY/SPI/ADS real | Solo test funcional. |

## 5. Flujo real en `setup()`

1. `Bridge.begin()` y `Monitor.begin()`.
2. Inicializa LED si `LED_MATRIX_ENABLED=1`; por defecto informa dry-run.
3. Inicializa MIDI UART si `MIDI_UART_ENABLED=1`.
4. Activa TX invertido en USART1.
5. Registra handlers `midi_bytes` y `led_matrix_row`.
6. Inicializa benchmark y `TxBlockRing`.
7. Inicializa filtros.
8. En modo real ADS:
   - configura pines DRDY/START/RESET/PWDN;
   - adjunta interrupcion DRDY falling;
   - arranca `ADS1299_SafeSPI`;
   - ejecuta `ads.begin()`;
   - lee ID ADS1299;
   - ejecuta `ads.configureDefaults()`;
   - aplica `applyAdsDiagnosticMode()`;
   - limpia `drdy_count`;
   - sube START;
   - espera 10 ms;
   - ejecuta `cmdRDATAC()`.

## 6. Flujo real en `loop()`

1. Mide `loop_start_us` para benchmark.
2. Si el self-test MIDI MCU esta activo, bombea notas diagnosticas. En final-v4 esta apagado por defecto.
3. Mientras `mpu_ready=false`, consulta `Bridge.call("linux_started")` a 1 Hz.
4. Cuando Python responde, resetea estado de streaming y empieza notifies.
5. En modo real ADS:
   - copia `drdy_count` con interrupciones deshabilitadas;
   - reinicia `drdy_count`;
   - si `pending>1`, contabiliza lag;
   - si `pending>0`, lee un frame RDATAC;
   - si el frame falla, imprime error con rate-limit y sale del loop;
   - incrementa contadores de muestras;
   - por canal aplica `raw * LSB_V -> HP -> notch50 -> LP40 -> uV`;
   - si Python esta listo y streaming esta activo, agrega muestra al bloque.
6. Actualiza maximos de tiempo de loop.
7. Si Python esta listo, publica hasta 4 bloques pendientes con `Bridge.notify("eeg_block_uV")`.
8. Imprime benchmark si toca.

## 7. Contrato `eeg_block_uV`

El contrato firmware->Python esta fijado en `streaming.h`:

```text
Bridge.notify(
  "eeg_block_uV",
  block_idx,
  first_sample_idx,
  sample_count,
  8 * (status, ch1_uV, ch2_uV, ch3_uV, ch4_uV)
)
```

Esto implica:

- 3 campos de cabecera;
- 8 muestras por bloque;
- 5 campos por muestra;
- 43 argumentos totales tras el nombre del evento;
- 4 canales siempre presentes aunque en modo 5 CH2-CH4 no sean EEG activo.

No cambiar `BLOCK_SAMPLES`, orden de campos ni numero de canales sin actualizar y validar:

- `python/eeg_contract.py`;
- `python/receiver.py`;
- `python/capture_manager.py`;
- herramientas offline;
- reportes de validacion.

## 8. Benchmarks MCU final-v4

La instrumentacion MCU esta separada del payload EEG:

- `BENCH_REPORT_ENABLED=1` imprime por Monitor;
- no se crea un canal Bridge adicional para benchmark;
- `parse_mcu_bench_monitor.py` convierte el log `[BENCH] EEG_MIDI` en CSV/JSON/Markdown.

Metricas principales documentadas:

- `gen/s`;
- `sent/s`;
- `blk_enq/s`;
- `blk_sent/s`;
- `filt_avg_us`;
- `filt_max_us_win`;
- `notify_avg_us`;
- `notify_max_us_win`;
- `loop_max_us_win`;
- `qmax_global`;
- `drops_total`;
- `pub_burst_global`.

Interpretacion final-v4:

- presupuesto por bloque = `8 / 250 = 32 ms`;
- el coste dominante observado fue `Bridge.notify`;
- el filtrado MCU fue despreciable frente al presupuesto;
- no se observaron drops en la captura benchmark documentada.

## 9. Riesgos principales

| Riesgo | Motivo | Mitigacion |
| --- | --- | --- |
| Cambiar `BLOCK_SAMPLES` | Payload manual y parser Python dependen de 8 | No tocar sin cambio coordinado. |
| Cambiar pines ADS | Rompe cableado/PCB | Validar fisicamente. |
| Cambiar SPI mode/velocidad | Riesgo RDATAC corrupto | Datasheet + prueba ID/status/captura. |
| Cambiar `LSB_V` | Cambia amplitudes, quality score y reportes | Revalidar escala con test interno/shorted. |
| Cambiar filtros MCU | Cambia espectro que llega a Python | Repetir capturas y benchmarks. |
| Interpretar CH2-CH4 como EEG en modo 5 | Estan apagados/cortocircuitados | Documentar CH1 como canal principal. |
| Quitar TX invertido | MIDI OUT fisico deja de sonar correctamente | Mantener `USART_CR2_TXINV`. |
| Activar LED durante benchmarks | Aumenta trafico Bridge | Medir por separado si se activa. |
| Aumentar prints Monitor | Puede introducir jitter | Mantener logs rate-limited. |
| Refactorizar `sketch.ino` sin placa | Riesgo alto en tiempo real | Hacer cambios pequenos y validar en UNO Q. |

## 10. Pruebas minimas antes de aceptar cambios firmware

No aplicar cambios firmware en esta fase documental. Si en el futuro se modifica firmware, validar:

1. Compilacion App Lab.
2. Monitor: `ADS1299 ID=0x3C`.
3. Monitor: `ADS1299 DIAG: bias_ch1_only_loff_off` si se busca comparabilidad final-v4.
4. Monitor: `START + RDATAC activo`.
5. Python/WebUI: `rx_frame_rate_hz ~= 250`.
6. Python/WebUI: `rx_block_rate_hz ~= 31.25`.
7. `malformed=0` e `invalid_status=0`.
8. Benchmark: `drops_total=0`.
9. MIDI: nota diagnostica y panic por ruta `midi_bytes`.
10. Captura corta: CSV con `sample_idx`, `status`, `ch1_uV..ch4_uV`.
11. Si LED se activa: medir impacto en `notify_max_us`, `loop_max_us` y drops.

## 11. Recomendacion para version esencial UML

En UML principal incluir:

```text
ADS1299Plus
ADS1299_SafeSPI
sketch.ino loop/setup
TxBlockRing
BenchStats como observabilidad
midi_bytes handler
```

Como modulo lateral/secundario:

```text
led_matrix_row handler
Arduino_LED_Matrix
synthetic.h
bench.h
```

El diagrama principal debe mostrar:

```text
DRDY -> readFrameRDATAC -> filtros -> TxBlockRing -> Bridge.notify("eeg_block_uV")
Python -> Bridge.call("midi_bytes") -> Serial1/D1 TXINV -> MIDI OUT
```

No debe presentar LED ni modo sintetico como parte necesaria del flujo EEG->MIDI validado.



