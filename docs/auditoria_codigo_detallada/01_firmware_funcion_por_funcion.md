# 01. Firmware funcion por funcion

## Responsabilidad global

`sketch/sketch.ino` ejecuta el tiempo real del STM32U585: inicia Bridge/Monitor, registra handlers `midi_bytes` y `led_matrix_row`, configura ADS1299, atiende DRDY, lee RDATAC, convierte counts a voltios, aplica filtros MCU, convierte a microvoltios, agrupa bloques y publica `eeg_block_uV`. Tambien mide rendimiento y soporta modo sintetico.

Configuracion critica:

- Pines: `PIN_CS=D10`, `PIN_DRDY=7`, `PIN_START=D9`, `PIN_RESET=D8`, `PIN_PWDN=D5`.
- Muestreo: `FS_HZ=250.0f`.
- Escala: `LSB_V=2.235e-8f`.
- Canales: `ADS1299Plus::NUM_CHANNELS == 4`.
- Streaming: `BLOCK_SAMPLES=8`, evento `eeg_block_uV`.
- Default actual: `ADS_DIAGNOSTIC_MODE=5`, CH1 activo con BIAS derivado de CH1P/CH1N y CH2-CH4 apagados.
- MIDI UART: `MIDI_UART_ENABLED=0` por defecto.
- LED fisico: `LED_MATRIX_ENABLED=0` por defecto.

## Archivos

| Archivo | Responsabilidad | Estado que define/toca | Riesgo |
| --- | --- | --- | --- |
| `sketch.ino` | Loop real-time, ADS, Bridge, MIDI, LED, benchmark | `drdy_count`, `sample_idx`, `txBlocks`, `bench`, filtros, handlers Bridge | Critico: timing, payload, pines. |
| `streaming.h` | Ring de bloques y publicacion Bridge | `TxBlockRing`, `EegBlockUV` | Critico: contrato MCU->Python. |
| `filters.h` | Filtros IIR y conversion V->uV | Estados `DCBlocker`, `Biquad` | Critico: modifica senal. |
| `bench.h` | Contadores de rendimiento | `BenchStats` | Medio: observabilidad. |
| `synthetic.h` | Generador EEG-like | RNG pasado por referencia | Medio: validacion sin ADS. |
| `sketch.yaml` | Librerias App Lab | Dependencias locales y publicas | Critico para build. |

## Funciones y structs

| Archivo | Funcion/struct | Entradas | Salidas | Estado que toca | Que hace | Contratos | Riesgo | Prueba necesaria |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `sketch.ino` | `midi_bytes(n,b0,b1,b2)` | Longitud 1..3 y bytes | `bool` | UART si `MIDI_UART_ENABLED` | Handler Bridge para enviar bytes MIDI al MCU | `Bridge.call("midi_bytes", n,b0,b1,b2)` | Si se activa UART equivocada puede interferir con Bridge | Test placa con UART D1/TX verificada y MIDI panic. |
| `sketch.ino` | `led_matrix_row(row_idx,chunk0,chunk1,chunk2)` | Fila y 39 bits en 3 chunks | `bool` | `led_frame_buffer`, `led_rows_received_mask`, LED fisico si enabled | Desempaqueta 13 pixeles de 3 bits por fila | `Bridge.call("led_matrix_row", row, c0,c1,c2)` | Multiples calls por frame pueden cargar Bridge; con LED off devuelve false | Test con `EEG_LED_MATRIX_ENABLED=1`, verificar sin perdida EEG. |
| `sketch.ino` | `checkMpuReady()` | Ninguna | `bool` | Ninguno | `Bridge.call("linux_started")` para handshake | Python expone `linux_started` | Si se llama demasiado podria bloquear | Ver que streaming empieza al arrancar Python. |
| `sketch.ino` | `onDrdyFalling()` | ISR pin DRDY | Ninguna | Incrementa `drdy_count` | Marca muestras listas sin hacer SPI en ISR | DRDY activo bajo | Contador no es FIFO; pending>1 significa perdida/jitter | Ver `pending>1`, `gen/s~250`. |
| `sketch.ino` | `reportBenchStatsIfDue()` | Timer `millis()` | Prints Monitor | Lee/reset ventana `bench` | Reporta tasas, maximos, colas, DRDY | No cambia payload EEG | Prints excesivos pueden afectar timing | Comparar `BENCH_REPORT_ENABLED=0/1`. |
| `sketch.ino` | `initFilters()` | Constantes filtros | Ninguna | Inicializa `hp`, `notch50`, `lp40` | HP 0.5 Hz, notch 50 Hz, LP 40 Hz por canal | Entrada en voltios, salida voltios | Cambiar coeficientes cambia DSP fisiologico | Validar con captura sintetica y real. |
| `sketch.ino` | `applyAdsDiagnosticMode()` | Macro `ADS_DIAGNOSTIC_MODE` | `bool` | Registros ADS1299 | Aplica modos normal, short, test, BIAS y CH1-only | Debe llamarse antes de RDATAC | Critico: puede apagar canales o habilitar BIAS | Leer registros/ID y capturar cada modo. |
| `sketch.ino` | `setup()` | Arranque placa | Ninguna | Bridge, Monitor, pines, SPI, ADS, handlers, filtros | Inicializa sistema y arranca RDATAC en real | Mantiene pines, handler names, modo diagnostico | Critico no tocar sin placa | Compilar y validar ADS ID 0x3C, DRDY, status. |
| `sketch.ino` | `loop()` | Ticks App Lab | Ninguna | Todo el estado runtime | Handshake, lee DRDY, procesa muestras, encola, publica, benchmark | 250 Hz, no bloqueo, `eeg_block_uV` | Maximo riesgo: timing/adquisicion | Ver rates, drops, status, dashboard. |
| `streaming.h` | `EegBlockUV` | N/A | N/A | Datos de bloque | Guarda `block_idx`, `first_sample_idx`, `sample_count`, status y 4 canales uV | `BLOCK_SAMPLES=8`, 4 canales | Cambiar layout rompe Python | Test parser `eeg_contract.py` + placa. |
| `streaming.h` | `TxBlockRing.resetFillBlock()` | Ninguna | Ninguna | `fill_block`, `next_block_idx` | Prepara bloque actual | `block_idx` monotono | Si se reinicia mal se ven saltos | Ver continuidad block_idx. |
| `streaming.h` | `TxBlockRing.resetRing()` | Ninguna | Ninguna | `head/tail/count` | Vacia cola de bloques | Cola circular de 32 bloques | Perder bloques si se llama en streaming | Solo al handshake/reset. |
| `streaming.h` | `TxBlockRing.resetStreamingState()` | Ninguna | Ninguna | Fill + ring | Reset completo de streaming | Usado al inicio y al estar MPU listo | Puede reiniciar indices | Revisar sample/block continuity. |
| `streaming.h` | `TxBlockRing.enqueueCompletedBlock()` | Bloque completo, bench | `bool` | Ring y contadores | Encola o contabiliza drops | Capacidad 32 | Si se llena, pierde bloques | Simular cola llena. |
| `streaming.h` | `TxBlockRing.appendSampleToFillBlock()` | `idx`, `status`, `ch_uV[4]` | Ninguna | `fill_block`, ring si lleno | Agrupa 8 muestras | Payload por muestra: status+4 ch | Error rompe sample_count | Validar receiver con bloque completo. |
| `streaming.h` | `TxBlockRing.publishPendingBlocks()` | Bench, max bloques | Bloques enviados | Ring, bench, Bridge | Publica hasta 4 bloques por loop con `Bridge.notify` | Evento `eeg_block_uV`, 43 campos | Critico: payload manual duplicado en firmware | Test Python recibe 31.25 bloques/s. |
| `filters.h` | `round_to_i32()` | Float | `int32_t` | Ninguno | Redondeo y saturacion | V->uV int32 | Saturacion mal aplicada altera amplitud | Unit test host si posible. |
| `filters.h` | `volts_to_uV_i32()` | Voltios | uV int32 | Ninguno | Multiplica por 1e6 y redondea | Unidad microvoltios | Escala critica | Comparar con Python. |
| `filters.h` | `DCBlocker.init/process()` | Fc/fs/x | y | `R,x1,y1` | High-pass/DC blocker IIR | Estado por canal | Transitorios iniciales | Prueba seno/drift. |
| `filters.h` | `Biquad.reset/process()` | x | y | `z1,z2` | Filtro IIR DF-II transposed | Coefs normalizados | Inestabilidad si coefs malos | Prueba frecuencia. |
| `filters.h` | `makeNotch()` | f0, fs, r | `Biquad` | Ninguno | Notch 50 Hz | r=0.95 actual | Puede atenuar banda cercana | PSD sintético 50 Hz. |
| `filters.h` | `makeLowpassRBJ()` | fc, fs, Q | `Biquad` | Ninguno | LP 40 Hz RBJ | Q=0.707 | Afecta gamma | Comparar respuesta. |
| `bench.h` | `BenchStats` | N/A | N/A | Contadores totales/ventana | Métricas de generacion, envio, colas y latencias | No debe controlar streaming | Bajo/medio | Monitor report coherente. |
| `synthetic.h` | `xorshift32()` | RNG ref | uint32 | RNG | PRNG simple | Determinista | Bajo | Repetibilidad. |
| `synthetic.h` | `randCentered()` | RNG ref | float [-1,1] | RNG | Ruido blanco | Sintetico | Bajo | Distribucion basica. |
| `synthetic.h` | `clamp24()` | int32 | int32 | Ninguno | Satura al rango ADS 24-bit | ADS signed 24-bit | Bajo | Bordes ADS. |
| `synthetic.h` | `synthEEG_uV()` | t, canal, RNG | uV float | RNG | Mezcla delta/theta/alpha/beta/gamma, drift, 50 Hz, ruido | Solo test | No valida ADS real | Ver bandas esperadas. |
| `synthetic.h` | `uV_to_rawCounts()` | uV, LSB | counts | Ninguno | Convierte uV a counts ADS | Inverso aproximado de escala | Escala sintética | Comparar uV->counts->uV. |
| `synthetic.h` | `generateSyntheticRaw()` | sample_idx, fs, LSB, array | Llena `ch_raw` | RNG | Genera counts 24-bit por canal | Mismo pipeline que ADS posterior | No valida DRDY/SPI | Test modo sintético. |

## Flujo real en `loop()`

1. Comprueba `linux_started` hasta que Python responda.
2. Copia y resetea `drdy_count` con interrupciones deshabilitadas.
3. Si `pending>1`, contabiliza lag; lee solo un frame actual.
4. `ads.readFrameRDATAC(status,ch_raw)` lee 15 bytes y valida sync `0xC00000`.
5. Por canal: `counts * LSB_V -> hp -> notch50 -> lp40 -> volts_to_uV_i32`.
6. Si `mpu_ready && STREAMING_NOTIFY_ENABLED`, agrega muestra al bloque.
7. Cada 8 muestras se encola un `EegBlockUV`.
8. Al final de loop publica hasta 4 bloques pendientes.
9. Reporta benchmark si toca.

## Riesgos principales

- `Bridge.notify` es manual y fija 8 muestras; cambiar `BLOCK_SAMPLES` exige editar firmware y `eeg_contract.py`.
- `drdy_count` no es FIFO real; si sube por encima de 1 se pierde informacion temporal.
- `Monitor.print` en rutas criticas puede introducir jitter.
- `ADS_DIAGNOSTIC_MODE=5` mantiene payload de 4 canales aunque CH2-CH4 esten apagados.
- `midi_bytes` y `led_matrix_row` son handlers registrados aunque los transportes esten disabled por defecto.
