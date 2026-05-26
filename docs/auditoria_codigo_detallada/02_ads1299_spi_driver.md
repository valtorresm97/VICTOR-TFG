# 02. ADS1299 y SPI driver

## Separacion de responsabilidades

- `ADS1299_SafeSPI` solo controla SPI, CS y timing bajo.
- `ADS1299Plus` conoce comandos, registros, defaults, helpers y lectura de frames.
- `ADS1299_Registers.h` contiene mapa de registros, comandos, mascaras y constructores de bytes.
- La aplicacion (`sketch.ino`) decide modo diagnostico, filtros, Bridge y benchmark.

## Contratos criticos

| Contrato | Valor actual | Archivo | Riesgo |
| --- | --- | --- | --- |
| Canales | `NUM_CHANNELS=4` | `ADS1299Plus.h` | Cambiar rompe frame size y payload Python. |
| Frame RDATAC 4ch | `3 + 3*4 = 15 bytes` | `ADS1299Plus.h/cpp` | Lectura desalineada invalida status/canales. |
| Status sync | `(status & 0xF00000) == 0xC00000` | `ADS1299_Registers.h` | Si no se valida, se procesan frames corruptos. |
| SPI | 2 MHz, MSBFIRST, MODE1 | `ADS1299_SafeSPI.cpp` | Modo incorrecto rompe ID/RDATAC. |
| ID esperado | ADS1299 con variante 4ch (`0x3C` observado) | `ADS1299Plus::begin()` | Si falla, se detiene config. |

## Funciones y metodos

| Archivo | Clase | Metodo/Funcion | Entrada | Salida | Registro/Comando ADS1299 | Riesgo | Critico |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `begin()` | Ninguna | Ninguna | SPI MODE1 2 MHz | Modo/velocidad incorrectos rompen comunicacion | Si |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `end()` | Ninguna | Ninguna | `SPI.endTransaction/end` | Bajo | Medio |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `select()` | Ninguna | Ninguna | CS low | CS fuera de timing rompe transaccion | Si |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `deselect()` | Ninguna | Ninguna | CS high | CS prematuro corta transaccion | Si |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `xfer(data)` | Byte | Byte recibido | `SPI.transfer` | Critico para comandos y datos | Si |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `waitDecode()` | Ninguna | Ninguna | tSDECODE >= 4 tCLK | Insuficiente delay puede ignorar comandos | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | Constructor | SPI ref, pines | Objeto | N/A | Bajo | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `pinStartHigh/Low()` | Ninguna | Ninguna | Pin START | Controla conversiones | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `pinResetPulse()` | Ninguna | Ninguna | RESET pin | Reset mal temporizado deja chip indeterminado | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `pinPowerDown(activeLow)` | bool | Ninguna | PWDN | Puede apagar ADC | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `begin()` | Ninguna | bool | RESET, STOP, SDATAC, RREG ID | Inicializacion ADS y verificacion 4ch | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `configureDefaults()` | Ninguna | bool | CONFIG1/2/3/LOFF/CHn/BIAS/LOFF/GPIO/CONFIG4 | Define modo base de adquisicion | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `end()` | Ninguna | Ninguna | STOP, SDATAC | Parada segura | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdWakeup()` | Ninguna | Ninguna | `0x02` | Timing comando | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdStandby()` | Ninguna | Ninguna | `0x04` | Puede pausar ADC | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdReset()` | Ninguna | Ninguna | `0x06` | Reset borra config | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdStart()` | Ninguna | Ninguna | `0x08` | Conversion start por comando | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdStop()` | Ninguna | Ninguna | `0x0A` | Conversion stop | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdRDATAC()` | Ninguna | Ninguna | `0x10` | Activa streaming continuo | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdSDATAC()` | Ninguna | Ninguna | `0x11` | Necesario antes de registros | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdRDATA()` | Ninguna | Ninguna | `0x12` | Lectura puntual | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `writeOne_/readOne_()` | addr/value | bool/value | WREG/RREG | No validan addr; depende de llamada correcta | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `writeBurst_/readBurst_()` | addr, buffer, n | bool | WREG/RREG burst | `n` debe ser >=1 | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `writeReg/readReg` | addr/value | bool/value | Wrapper | Exponen API publica | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `writeRegs/readRegs` | addr, buffer, n | bool | Wrapper burst | Offline/config | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setDataRate()` | DR bits | bool | CONFIG1 DR | Cambia FS; exige actualizar Python | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setClockOut()` | bool | bool | CONFIG1 CLK_EN | Relevante multi-chip | Bajo |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setDaisyEnable()` | bool | bool | CONFIG1 DAISY_EN | No usado; daisy puede romper frame | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setChannel()` | ch, byte | bool | CHnSET | Puede apagar/cambiar mux/gain | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `powerDownChannel()` | ch, bool | bool | CHnSET PD | Afecta canales visibles | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setChannelGain()` | ch, gain | bool | CHnSET gain | Cambia escala real; LSB podria no cuadrar | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setChannelMux()` | ch, mux | bool | CHnSET mux | Cambia fuente de senal | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setSRB2()/enableSRB1()` | bool | bool | CHnSET/MISC1 | Cambia referencia analogica | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `useInternalRef()` | bool | bool | CONFIG3 PD_REFBUF | Escala/estabilidad | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `useBiasInternalRef()` | bool | bool | CONFIG3 BIASREF_INT | BIAS/RLD | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `enableBiasBuffer()` | bool | bool | CONFIG3 PD_BIAS | Activa driver BIAS | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `routeBiasSense()` | bool | bool | CONFIG3 BIAS_LOFF_SENS | Lead-off por BIAS | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `enableBiasMeasure()` | bool | bool | CONFIG3 BIAS_MEAS | Diagnostico BIAS | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `configureLeadOff()` | byte | bool | LOFF | Inyeccion lead-off | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `enableLeadOffSenseP/N()` | mask | bool | LOFF_SENSP/N | Puede inyectar corriente en electrodos | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setLeadOffFlip()` | mask | bool | LOFF_FLIP | Diagnostico contacto | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setSingleShot()` | bool | bool | CONFIG4 SINGLE_SHOT | Rompe RDATAC continuo si se usa mal | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `enableLoffComparators()` | bool | bool | CONFIG4 PD_LOFF_COMP | Afecta status lead-off | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setBiasDeriveP/N()` | mask | bool | BIAS_SENSP/N | Lazo BIAS; usar con montaje correcto | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `readFrameRDATAC()` | refs status/chOut | bool | Lectura 15 bytes RDATAC | Critico: unpack24 y status sync | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `readDataOnDemand()` | refs status/chOut | bool | RDATA + 15 bytes | Diagnostico | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `readDeviceID()` | ref id | bool | RREG ID | Verifica chip | Si |
| `ADS1299Plus.h` | `ADS1299Plus` | `statusHasSync()` | status24 | bool | `ADS_STATUS_SYNC_MASK` | Parser de frame | Si |
| `ADS1299Plus.h` | `ADS1299Plus` | `statusLoffP/N/GPIO()` | status24 | byte | STATUS fields | Diagnostico | Medio |
| `ADS1299Plus.h` | `ADS1299Plus` | `unpack24()` | 3 bytes | int32 | 24-bit signed | Critico para amplitud | Si |
| `ADS1299_Registers.h` | N/A | `ADS_CFG*_MAKE`, `ADS_CH_MAKE`, masks | Campos | byte/mask | Registros ADS | Datasheet-sensitive | Si |
| `ADS1299_Registers.h` | N/A | `ADS_ClipMaskToChannels()` | mask,nchan | mask | Canal mask | Evita bits fuera de variante | Medio |
| `ADS1299_Registers.h` | N/A | `ADS_IsLeadOffP/N()` | stat, ch | bool | LOFF_STATP/N | Diagnostico contacto | Bajo |
| `ADS1299_Registers.h` | N/A | `ADS_CH_DEFAULT_GAIN24()` | Ninguna | byte CHnSET | CHnSET gain24 normal | Base captura real | Si |

## Observaciones tecnicas

- `begin()` exige que el ID sea ADS1299 y que `NU_CH` indique variante de 4 canales; esto protege el contrato de 15 bytes.
- `readFrameRDATAC()` retorna `false` si `rdatacActive_` no esta activo o si el status no tiene sync.
- `configureDefaults()` activa lead-off sense para canales activos, pero `applyAdsDiagnosticMode()` puede desactivarlo despues.
- El modo actual `ADS_DIAG_BIAS_CH1_ONLY_LOFF_OFF` reconfigura CH1 activo y CH2-CH4 power-down/short, sin cambiar el payload de 4 canales.
- El calculo de LSB no vive en el driver, sino en `sketch.ino` y `eeg_contract.py`; si cambia ganancia/referencia hay que coordinar escala.
