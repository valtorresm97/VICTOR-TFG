# 02. Auditoria firmware / MCU

## Responsabilidades por archivo

| Archivo | Responsabilidad | Criticidad |
| --- | --- | --- |
| `sketch/sketch.ino` | Inicializa Bridge/Monitor/ADS1299, configura pines, DRDY, filtros, streaming, MIDI dry-run y LED dry-run. | Critico |
| `sketch/ADS1299Plus/src/ADS1299Plus.*` | Driver alto nivel ADS1299: power-up, comandos, registros, RDATAC, unpack signed 24-bit. | Critico |
| `sketch/ADS1299Plus/src/ADS1299_Registers.h` | Constantes de comandos, registros, mascaras y defaults ADS1299. | Critico |
| `sketch/ADS1299_SafeSPI/src/ADS1299_SafeSPI.*` | Wrapper SPI 2 MHz, MSBFIRST, SPI_MODE1, CS manual. | Critico |
| `sketch/filters.h` | HP/DC blocker 0.5 Hz, notch 50 Hz, LP 40 Hz y conversion a microvoltios. | Critico |
| `sketch/streaming.h` | Bloques `EegBlockUV`, ring TX y payload `eeg_block_uV`. | Critico |
| `sketch/bench.h` | Contadores de rendimiento, colas, filtros, notify y lag. | Medio |
| `sketch/synthetic.h` | Senal sintetica EEG-like para test sin ADS1299. | Medio |
| `sketch/sketch.yaml` | Dependencias firmware/App Lab. | Medio |

## Pines y perifericos

| Recurso | Valor actual | Archivo | Observacion |
| --- | --- | --- | --- |
| `PIN_CS` | `D10` | `sketch.ino` | CS ADS1299 activo bajo. |
| `PIN_SCLK` | `SCK` | `sketch.ino` | SPI clock. |
| `PIN_MOSI` | `MOSI` | `sketch.ino` | DIN ADS1299. |
| `PIN_MISO` | `MISO` | `sketch.ino` | DOUT ADS1299. |
| `PIN_DRDY` | `7` | `sketch.ino` | Interrupcion FALLING. No cambiar. |
| `PIN_START` | `D9` | `sketch.ino` | Se pone HIGH antes de RDATAC. |
| `PIN_RESET` | `D8` | `sketch.ino` | Reset digital. |
| `PIN_PWDN` | `D5` | `sketch.ino` | Se mantiene HIGH. |
| SPI | 2 MHz, MSBFIRST, SPI_MODE1 | `ADS1299_SafeSPI.cpp` | Configuracion inicial conservadora. |
| Bridge | RouterBridge | `sketch.ino`, `streaming.h` | `call` para handshake/handlers, `notify` para EEG. |
| LED Matrix | Arduino_LED_Matrix | `sketch.ino` | Compila solo si `LED_MATRIX_ENABLED=1`. |
| MIDI UART | `MIDI_SERIAL` externo | `sketch.ino` | Compila solo si `MIDI_UART_ENABLED=1` y se define UART. |

## Configuracion ADS1299

- Variante esperada: ADS1299-4; `begin()` exige ID de familia ADS1299 y `NU_CH=00`.
- Frame RDATAC: `3 + 3*4 = 15` bytes.
- Status valido: `STATUS[23:20]=1100b`, validado con `0xF00000`.
- `CONFIG1`: `ADS_CFG1_250SPS`.
- `CONFIG2`: test interno off salvo diagnostico.
- `CONFIG3`: ref interna y BIAS segun modo diagnostico.
- Modo por defecto actual: `ADS_DIAGNOSTIC_MODE=5`, CH1 activo, CH2-CH4 apagados, BIAS CH1P+CH1N, lead-off off.
- `LSB_V=2.235e-8f`, consistente con gain 24 y Vref aproximada 4.5 V.

## Funciones importantes

| Archivo | Funcion | Entrada | Salida | Que hace | Riesgo | Critica |
| --- | --- | --- | --- | --- | --- | --- |
| `sketch.ino` | `setup()` | Ninguna | Ninguna | Inicia Bridge, Monitor, handlers, filtros, ADS1299, ISR, START y RDATAC. | Delays iniciales aceptables; errores bloquean con `while(1)`. | Si |
| `sketch.ino` | `loop()` | DRDY/Bridge | Ninguna | Handshake, lectura real/sintetica, filtrado, enqueue, publish y bench. | `Monitor` y `Bridge.notify` pueden afectar timing. | Si |
| `sketch.ino` | `onDrdyFalling()` | Interrupcion DRDY | Incrementa contador | ISR minima: solo `drdy_count++`. | `drdy_count` no es FIFO; si se acumula se pierde informacion temporal. | Si |
| `sketch.ino` | `applyAdsDiagnosticMode()` | Macro compile-time | `bool` | Programa modos normal/short/test/no-bias/bias/CH1-only. | Cambia registros de adquisicion; requiere trazabilidad. | Si |
| `sketch.ino` | `initFilters()` | Constantes FS/fc | Ninguna | Inicializa HP, notch y LP por canal. | Cambia espectro antes de Python. | Si |
| `sketch.ino` | `midi_bytes()` | `n,b0,b1,b2` | `bool` | Handler Bridge para MIDI; escribe UART solo si habilitada. | Actualmente devuelve `false` por defecto. | Medio |
| `sketch.ino` | `led_matrix_frame()` | `vector<uint8_t>` | `bool` | Valida 104 bytes y dibuja en Arduino_LED_Matrix si habilitado. | Payload grande por Bridge si se sube refresh. | Medio |
| `sketch.ino` | `checkMpuReady()` | Ninguna | `bool` | Llama `linux_started` a Python. | RPC sincronico, pero solo hasta ready a 1 Hz. | Medio |
| `streaming.h` | `appendSampleToFillBlock()` | sample idx, status, uV | Ninguna | Llena bloque de 8 muestras. | Si cambia orden rompe receiver. | Si |
| `streaming.h` | `publishPendingBlocks()` | bench, max bloques | bloques enviados | Publica `eeg_block_uV` con payload fijo. | `Bridge.notify` puede bloquear; se mide. | Si |
| `ADS1299Plus.cpp` | `begin()` | Pines/SPI | `bool` | Power-up, reset, STOP/SDATAC, ID y variante. | Si falla, no arranca. | Si |
| `ADS1299Plus.cpp` | `configureDefaults()` | Ninguna | `bool` | Escribe CONFIG/LOFF/CH/GPIO/CONFIG4. | Defaults afectan senal real. | Si |
| `ADS1299Plus.cpp` | `cmdRDATAC()` | Ninguna | Ninguna | Entra en modo streaming continuo. | WREG/RREG no deben hacerse en RDATAC sin SDATAC. | Si |
| `ADS1299Plus.cpp` | `readFrameRDATAC()` | refs status/ch | `bool` | Lee 15 bytes, unpack 24-bit, valida status sync. | Punto central de adquisicion. | Si |
| `ADS1299Plus.h` | `unpack24()` | 3 bytes | `int32_t` | Reconstruye signed 24-bit con extension de signo. | No tocar: error escala/polaridad. | Si |
| `filters.h` | `DCBlocker::process()` | muestra V | muestra V | Bloquea DC/high-pass. | Puede alterar bajas frecuencias. | Si |
| `filters.h` | `makeNotch()` | f0,fs,r | biquad | Notch 50 Hz. | Interpreta gamma/line noise. | Si |
| `filters.h` | `makeLowpassRBJ()` | fc,fs,Q | biquad | Low-pass 40 Hz. | Gamma 30-50 queda parcialmente limitada. | Si |

## Enabled por defecto

| Configuracion | Valor | Efecto |
| --- | --- | --- |
| `USE_SYNTHETIC` | `0` | Captura real ADS1299. |
| `ADS_DIAGNOSTIC_MODE` | `5` | CH1-only con BIAS CH1P+CH1N y CH2-CH4 apagados. |
| `DEBUG_MONITOR` | `true` | Print cada 500 muestras y errores limitados. |
| `BENCH_NOTIFY_ENABLED` | `true` | Envia bloques EEG por Bridge si MPU listo. |
| `BENCH_REPORT_EVERY_MS` | `5000` | Imprime reporte bench cada 5 s. |
| `LED_MATRIX_ENABLED` | `0` | Handler registrado, pero no dibuja. |
| `MIDI_UART_ENABLED` | `0` | Handler registrado, pero no escribe UART. |

## Riesgos firmware detectados

- `BENCH_NOTIFY_ENABLED` controla streaming, no solo benchmark; el nombre puede confundir.
- No existe `BENCH_REPORT_ENABLED` separado; los reports por Monitor siempre se imprimen cada 5 s.
- `DEBUG_MONITOR=true` implica prints durante adquisicion, aunque espaciados.
- `pending > 1` se cuenta como lag, pero se pierde el numero de frames no leidos como metrica especifica.
- LED y MIDI comparten Bridge con EEG; si se activan sin medir pueden afectar latencia.
- `midi_bytes()` devuelve `false` si UART deshabilitada; el transporte Python puede contar fallos si se activa solo Python.
- No hay ruta raw/unfiltered para separar problemas de adquisicion de filtros MCU.
