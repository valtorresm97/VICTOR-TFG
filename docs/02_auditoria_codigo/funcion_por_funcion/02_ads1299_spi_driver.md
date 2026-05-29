# 02. ADS1299 y SPI driver - final-v4

Rama auditada originalmente: `eliminacion-redudancias`.

Actualizacion final-v3: contrastada contra `codex/direct-band-sonification` y `firmware-final-v3`.

Re-auditoria final-v4: revisada contra codigo real en `firmware-final-v4` desde la rama documental `refactor/essential-eeg-midi-plan`.

Objetivo de esta re-auditoria: documentar con precision el driver ADS1299, el wrapper SPI, el mapa de registros, la lectura RDATAC y el modo final `bias_ch1_only_loff_off`, sin modificar codigo.

## 1. Separacion de responsabilidades

| Componente | Responsabilidad | No debe hacer |
| --- | --- | --- |
| `ADS1299_SafeSPI` | Control bajo de SPI, CS, `SPISettings(2000000, MSBFIRST, SPI_MODE1)` y transferencia byte a byte | No conoce registros ni semantica EEG. |
| `ADS1299Plus` | Comandos ADS1299, acceso a registros, defaults, helpers analogicos y lectura de frames RDATAC/RDATA | No calcula microvoltios ni filtros. |
| `ADS1299_Registers.h` | Mapa de registros, comandos, mascaras y constructores de bytes | No ejecuta SPI. |
| `sketch.ino` | Decide modo diagnostico, pines, filtros, Bridge, benchmark, MIDI y LED | No debe duplicar parsing de registros salvo decisiones de modo. |
| `python/eeg_contract.py` | Parser Python del payload ya convertido a microvoltios | No conoce SPI ni registros ADS. |

## 2. Contratos criticos final-v4

| Contrato | Valor actual | Archivo | Riesgo |
| --- | --- | --- | --- |
| Canales soportados por driver | `NUM_CHANNELS=4` | `ADS1299Plus.h` | Cambiar rompe frame size, payload firmware y parser Python. |
| Frame RDATAC 4ch | `3 + 3*4 = 15 bytes` | `ADS1299Plus.h/cpp` | Lectura desalineada invalida status/canales. |
| Status sync | `(status & 0xF00000) == 0xC00000` | `ADS1299_Registers.h`, `ADS1299Plus.h` | Si no se valida, se procesan frames corruptos. |
| SPI | 2 MHz, MSBFIRST, MODE1 | `ADS1299_SafeSPI.cpp` | Modo incorrecto rompe ID/RDATAC. |
| ID observado | `0x3C` | Monitor/validacion | Confirma ADS1299-4 esperado. |
| Variante aceptada | `NU_CH=00` | `ADS1299Plus::begin()` | Si no es 4ch, `begin()` falla. |
| CONFIG1 default | `ADS_CFG1_250SPS` con bits fijos preservados | `ADS1299Plus.h`, `ADS1299_Registers.h` | Cambiar DR exige sincronizar `FS_HZ`. |
| CONFIG2 default | `ADS_CFG2_TEST_OFF` | `ADS1299Plus.h` | Test interno solo en modo diagnostico. |
| CONFIG3 default | `ADS_CFG3_INTREF_NO_BIAS` | `ADS1299Plus.h` | BIAS se activa despues en modos diagnosticos/finales. |
| Modo final de capturas | `ADS_DIAGNOSTIC_MODE=5` | `sketch.ino` | CH1 activo, CH2-CH4 apagados/cortocircuitados. |
| Lead-off final | desactivado en modo 5 | `applyAdsDiagnosticMode()` | Evita inyeccion diagnostica durante capturas finales. |
| BIAS final | derivado de CH1P+CH1N | `applyAdsDiagnosticMode()` | No incluir canales flotantes. |

## 3. Secuencia real de arranque ADS1299

En final-v4 el arranque completo se reparte entre `sketch.ino` y `ADS1299Plus`:

```text
sketch.setup()
  -> safeSpi.begin()
  -> ads.begin()
       -> spi_.begin()
       -> cmdReset()
       -> cmdStop()
       -> cmdSDATAC()
       -> readReg(ID)
       -> validar ADS1299 y variante 4ch
  -> ads.configureDefaults()
       -> STOP + SDATAC
       -> CONFIG1/2/3/LOFF
       -> CH1-CH4 default gain24 normal
       -> BIAS derivation off
       -> LOFF sense activo por defecto
       -> GPIO/MISC1/CONFIG4
  -> applyAdsDiagnosticMode()
       -> modo 5 final-v4: CONFIG2 off, CONFIG3 BIAS on, BIAS CH1P+CH1N, LOFF sense off, CH2-CH4 off/short
  -> START high
  -> cmdRDATAC()
```

Observacion de re-auditoria:

- `sketch.ino` llama `safeSpi.begin()` antes de `ads.begin()`.
- `ADS1299Plus::begin()` vuelve a llamar `spi_.begin()`.
- El sistema esta validado asi, por tanto no se modifica en esta fase.
- Para un refactor futuro, esta doble inicializacion SPI debe revisarse con cuidado, porque `SPI.beginTransaction()` normalmente conviene balancearlo con `endTransaction()`.

## 4. Funciones y metodos

| Archivo | Clase | Metodo/Funcion | Entrada | Salida | Registro/Comando ADS1299 | Riesgo | Critico |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `begin()` | Ninguna | Ninguna | `SPI.beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE1))` | Modo/velocidad incorrectos rompen comunicacion. Doble llamada actual esta validada pero debe revisarse antes de refactor | Si |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `end()` | Ninguna | Ninguna | `SPI.endTransaction/end` | Bajo | Medio |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `select()` | Ninguna | Ninguna | CS low | CS fuera de timing rompe transaccion | Si |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `deselect()` | Ninguna | Ninguna | CS high | CS prematuro corta transaccion | Si |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `xfer(data)` | Byte | Byte recibido | `SPI.transfer` | Critico para comandos y datos | Si |
| `ADS1299_SafeSPI.cpp` | `ADS1299_SafeSPI` | `waitDecode()` | Ninguna | Ninguna | tSDECODE >= 4 tCLK | Disponible pero no usado de forma central; `ADS1299Plus.cpp` usa `ads_wait_decode()` | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | Constructor | SPI ref, pines | Objeto | N/A | Bajo | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `pinStartHigh/Low()` | Ninguna | Ninguna | Pin START | Controla conversiones | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `pinResetPulse()` | Ninguna | Ninguna | RESET pin | Reset mal temporizado deja chip indeterminado | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `pinPowerDown(activeLow)` | bool | Ninguna | PWDN | Puede apagar ADC | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `begin()` | Ninguna | bool | RESET, STOP, SDATAC, RREG ID | Inicializacion ADS y verificacion 4ch | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `configureDefaults()` | Ninguna | bool | CONFIG1/2/3/LOFF/CHn/BIAS/LOFF/GPIO/CONFIG4 | Define modo base antes del modo diagnostico/final | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `end()` | Ninguna | Ninguna | STOP, SDATAC, SPI end | Parada segura | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdWakeup()` | Ninguna | Ninguna | `0x02` | Timing comando | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdStandby()` | Ninguna | Ninguna | `0x04` | Puede pausar ADC | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdReset()` | Ninguna | Ninguna | `0x06` | Reset borra config; espera 20 us | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdStart()` | Ninguna | Ninguna | `0x08` | Conversion start por comando, aunque final-v4 usa START pin high antes de RDATAC | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdStop()` | Ninguna | Ninguna | `0x0A` | Conversion stop | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdRDATAC()` | Ninguna | Ninguna | `0x10` | Activa streaming continuo y `rdatacActive_=true` | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdSDATAC()` | Ninguna | Ninguna | `0x11` | Necesario antes de escribir/leer registros | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `cmdRDATA()` | Ninguna | Ninguna | `0x12` | Lectura puntual | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `writeOne_/readOne_()` | addr/value | bool/value | WREG/RREG | No emiten SDATAC automaticamente; el llamador debe asegurar no estar en RDATAC | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `writeBurst_/readBurst_()` | addr, buffer, n | bool | WREG/RREG burst | `n` debe ser >=1; sin validacion de rango | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `writeReg/readReg` | addr/value | bool/value | Wrapper | Exponen API publica | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `writeRegs/readRegs` | addr, buffer, n | bool | Wrapper burst | Offline/config | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `setDataRate()` | DR bits | bool | CONFIG1 DR | Cambia FS; exige actualizar firmware/Python/docs | Si |
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
| `ADS1299Plus.cpp` | `ADS1299Plus` | `readFrameRDATAC()` | refs status/chOut | bool | Lectura 15 bytes RDATAC | Critico: requiere `rdatacActive_`, unpack24 y status sync | Si |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `readDataOnDemand()` | refs status/chOut | bool | RDATA + 15 bytes | Diagnostico; valida status sync | Medio |
| `ADS1299Plus.cpp` | `ADS1299Plus` | `readDeviceID()` | ref id | bool | RREG ID | Verifica chip | Si |
| `ADS1299Plus.h` | `ADS1299Plus` | `statusHasSync()` | status24 | bool | `ADS_STATUS_SYNC_MASK` | Parser de frame | Si |
| `ADS1299Plus.h` | `ADS1299Plus` | `statusLoffP/N/GPIO()` | status24 | byte | STATUS fields | Diagnostico | Medio |
| `ADS1299Plus.h` | `ADS1299Plus` | `unpack24()` | 3 bytes | int32 | 24-bit signed | Critico para amplitud | Si |
| `ADS1299_Registers.h` | N/A | `ADS_CFG*_MAKE`, `ADS_CH_MAKE`, masks | Campos | byte/mask | Registros ADS | Datasheet-sensitive | Si |
| `ADS1299_Registers.h` | N/A | `ADS_ClipMaskToChannels()` | mask,nchan | mask | Canal mask | Evita bits fuera de variante | Medio |
| `ADS1299_Registers.h` | N/A | `ADS_IsLeadOffP/N()` | stat, ch | bool | LOFF_STATP/N | Diagnostico contacto | Bajo |
| `ADS1299_Registers.h` | N/A | `ADS_CH_DEFAULT_GAIN24()` | Ninguna | byte CHnSET | CHnSET gain24 normal | Base captura real | Si |

## 5. Registros y valores relevantes

| Registro | Uso final-v4 | Comentario |
| --- | --- | --- |
| `ID` | Se lee en `begin()` y se loguea tambien en `sketch.ino` | Debe identificar ADS1299 y variante 4 canales. |
| `CONFIG1` | 250 SPS, sin daisy, sin clock out | Helpers preservan bits fijos `0x90`. |
| `CONFIG2` | Test off en modo final; test interno solo en modo 2 | No activar test interno durante capturas reales. |
| `CONFIG3` | Referencia interna + BIAS on en modo 5 | Helpers preservan bits fijos `0x60`. |
| `LOFF` | Default definido, pero lead-off sense se desactiva en modo 5 | Evita inyeccion durante capturas finales. |
| `CH1SET` | Activo, gain 24, MUX normal | Canal EEG principal final. |
| `CH2SET-CH4SET` | Apagados/cortocircuitados en modo 5 | No interpretar como EEG. |
| `BIAS_SENSP/N` | `ADS_MASK_CH1` en modo 5 | BIAS derivado de CH1P+CH1N. |
| `LOFF_SENSP/N` | `0x00` en modo 5 | Lead-off sense off. |
| `GPIO` | Entradas | Sin uso funcional principal. |
| `MISC1` | SRB1 off | Diferencial puro. |
| `CONFIG4` | Continuous conversion | No single-shot. |

## 6. RDATAC y parseo de frame

`readFrameRDATAC()` hace:

1. Comprueba `rdatacActive_`.
2. Baja CS.
3. Lee 15 bytes con `SPI.transfer(0x00)`.
4. Sube CS.
5. Reconstruye `status24` con los tres primeros bytes.
6. Reconstruye CH1-CH4 con `unpack24()`.
7. Devuelve `statusHasSync(status24)`.

Riesgos:

- Leer antes de DRDY puede devolver frame viejo o inconsistente.
- Leer con SPI mode incorrecto corrompe status.
- Cambiar a 6/8 canales exige cambiar `BYTES_PER_FRAME_4CH`, `NUM_CHANNELS`, payload, Python y docs.
- Si `rdatacActive_` esta false, el driver devuelve false y el loop no procesa muestra.

## 7. Observaciones tecnicas de la re-auditoria

- `begin()` exige que el ID sea ADS1299 y que `NU_CH` indique variante de 4 canales; esto protege el contrato de 15 bytes.
- `readFrameRDATAC()` retorna `false` si `rdatacActive_` no esta activo o si el status no tiene sync.
- `configureDefaults()` activa lead-off sense para canales activos, pero `applyAdsDiagnosticMode()` lo desactiva despues en los modos BIAS/CH1-only.
- El modo final `ADS_DIAG_BIAS_CH1_ONLY_LOFF_OFF` reconfigura CH1 activo y CH2-CH4 power-down/short, sin cambiar el payload de 4 canales.
- El calculo de LSB no vive en el driver, sino en `sketch.ino` y `python/eeg_contract.py`; si cambia ganancia/referencia hay que coordinar escala.
- `writeReg/readReg` no fuerzan `SDATAC` por si mismos. La secuencia segura es responsabilidad del llamador. `configureDefaults()` si ejecuta `cmdStop()` + `cmdSDATAC()` antes de escribir registros.
- `ADS1299_SafeSPI::waitDecode()` existe, pero `ADS1299Plus.cpp` usa su propio `ads_wait_decode()`. No es urgente cambiarlo, pero es una redundancia a considerar en una refactorizacion futura.
- La doble llamada `safeSpi.begin()` + `ads.begin()->spi_.begin()` debe considerarse deuda tecnica leve, no error demostrado, porque los benchmarks/capturas validaron el sistema asi.

## 8. Riesgos para futuras modificaciones

| Cambio | Riesgo | Validacion requerida |
| --- | --- | --- |
| Cambiar `NUM_CHANNELS` | Rompe frame y payload Python | Firmware + `eeg_contract.py` + capturas + WebUI. |
| Cambiar SPI mode/velocidad | Status invalido o ID incorrecto | Leer ID, RDATAC, status `0xC00000`, benchmark. |
| Cambiar CONFIG1 DR | Frecuencia real ya no seria 250 Hz | Actualizar `FS_HZ` en firmware/Python y repetir benchmarks. |
| Cambiar ganancia | `LSB_V` deja de ser valido | Recalcular escala y validar test interno/shorted. |
| Activar lead-off sense en capturas finales | Puede inyectar componentes de diagnostico | Capturas A/B y analisis espectral. |
| Incluir CH2-CH4 en BIAS sin electrodos reales | Puede introducir ruido/common-mode | Solo probar si canales estan conectados y estables. |
| Cambiar SRB1/SRB2 | Cambia referencia analogica | Validacion fisiologica completa. |
| Mover SDATAC/WREG/RDATAC | Riesgo de escribir registros en modo continuo | Revisar datasheet y probar en placa. |
| Reorganizar SafeSPI/ADS1299Plus | Riesgo de timings/CS | Compilar, ID, RDATAC, benchmark. |

## 9. Pruebas minimas del driver

Para aceptar cambios en driver ADS/SPI:

1. Compilar en Arduino App Lab.
2. Monitor: `ADS1299 ID=0x3C`.
3. Monitor: `ADS1299 DIAG: bias_ch1_only_loff_off` si se quiere comparabilidad final-v4.
4. Monitor: `START + RDATAC activo`.
5. Captura corta con `sample_gaps=0`.
6. `invalid_status=0`.
7. Status prefijo `0xC00000`.
8. `rx_frame_rate_hz ~= 250`.
9. `rx_block_rate_hz ~= 31.25`.
10. Benchmark MCU sin `drops_total`.
11. Si se toca escala/gain, repetir test interno y `shorted_inputs`.

## 10. Recomendacion para version esencial UML

En el UML principal, representar el driver como dos capas:

```text
ADS1299_SafeSPI
  -> select/deselect/xfer/SPISettings
ADS1299Plus
  -> begin/configureDefaults/apply mode/readFrameRDATAC/unpack24/statusHasSync
```

Y separarlo de:

```text
sketch.ino
  -> decide modo final-v4
  -> aplica filtros
  -> empaqueta Bridge
```

No incluir en el UML principal:

- todas las pruebas de BIAS measurement;
- todos los helpers no usados en runtime final;
- modos sinteticos como ruta principal.

Pero si deben quedar documentados como capacidades diagnosticas y riesgos de modificacion.



