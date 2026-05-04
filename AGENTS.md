# AGENTS.md — EEG-MIDI System / Arduino UNO Q / ADS1299 / Python DSP

## 1. Objetivo general del proyecto

Este repositorio contiene una aplicación completa EEG-MIDI para Arduino UNO Q.

El sistema captura señales EEG mediante un ADC ADS1299-4PAG conectado al microcontrolador STM32U585 del Arduino UNO Q, procesa parte de la señal en firmware, transmite bloques de datos al microprocesador Qualcomm QRB2210 mediante Arduino RouterBridge y después procesa, visualiza y prepara los datos para una futura etapa de sonificación/MIDI desde Python.

El objetivo final es construir una interfaz cerebro-computador orientada a sonificación de ondas cerebrales:

```text
Electrodos EEG
→ ADS1299-4PAG
→ SPI
→ STM32U585
→ filtrado/preprocesado MCU
→ Bridge MCU→MPU
→ Qualcomm/Linux
→ Python receiver
→ DSP EEG
→ dashboard web
→ futura generación MIDI

## 2. Hardware y arquitectura

### Hardware principal

- Arduino UNO Q.
- MCU: STM32U585.
- MPU: Qualcomm QRB2210 ejecutando Linux/App Lab.
- ADC: ADS1299 / ADS1299-4PAG de Texas Instruments.
- Canales actuales esperados: 4.
- Frecuencia objetivo: 250 muestras/s por canal.
- Comunicación ADC → MCU: SPI.
- Comunicación MCU → MPU: Arduino_RouterBridge.
- Aplicación Python en App Lab para recepción, DSP y dashboard.

### Pines firmware actuales

```cpp
PIN_CS    = D10
PIN_SCLK  = SCK
PIN_MOSI  = MOSI
PIN_MISO  = MISO
PIN_DRDY  = 7
PIN_START = D9
PIN_RESET = D8
PIN_PWDN  = D5

No cambiar estos pines salvo que la tarea lo pida explícitamente y se explique el motivo.

Arquitectura funcional

Electrodos EEG
→ ADS1299-4PAG
→ SPI RDATAC
→ STM32U585
→ reconstrucción de muestras 24-bit
→ conversión a voltios
→ filtros MCU
→ conversión a microvoltios
→ bloques EEG
→ Bridge.notify("eeg_block_uV")
→ Qualcomm/Linux
→ Python receiver
→ DSP
→ dashboard web
→ futura generación MIDI


eeg_midi/
├── AGENTS.md
├── app.yaml
├── python/
│   ├── main.py
│   ├── receiver.py
│   ├── backend_service.py
│   ├── app_state.py
│   ├── dsp_core.py
│   ├── eeg_signal_processor.py
│   ├── dashboard.py
│   └── requirements.txt
└── sketch/
    ├── sketch.ino
    ├── bench.h
    ├── filters.h
    ├── streaming.h
    ├── synthetic.h
    ├── sketch.yaml
    ├── ADS1299Plus/
    │   ├── library.properties
    │   └── src/
    │       ├── ADS1299Plus.h
    │       ├── ADS1299Plus.cpp
    │       └── ADS1299_Registers.h
    └── ADS1299_SafeSPI/
        ├── library.properties
        └── src/
            ├── ADS1299_SafeSPI.h
            └── ADS1299_SafeSPI.cpp

 
  
Papel de cada bloque
app.yaml

Define el perfil Arduino App Lab, la plataforma arduino:zephyr y las librerías necesarias.

Debe mantener las librerías locales:

- dir: ADS1299Plus
- dir: ADS1299_SafeSPI

No convertir estas librerías locales en dependencias públicas tipo ADS1299Plus@latest.

sketch/sketch.ino

Firmware principal del STM32U585.

Responsabilidades:

Inicializar Bridge y Monitor.
Inicializar ADS1299.
Configurar pines.
Gestionar DRDY.
Leer frames RDATAC.
Convertir raw counts a voltios.
Aplicar filtros.
Convertir a microvoltios.
Agrupar datos en bloques.
Publicar bloques mediante Bridge.
Medir rendimiento.

Este archivo es crítico para tiempo real. Evitar código bloqueante dentro de loop().

ADS1299Plus

Driver de alto nivel para el ADS1299.

Responsabilidades:

Comandos SPI ADS1299.
Reset, START, STOP, RDATAC, SDATAC, RDATA.
Lectura/escritura de registros.
Configuración de CONFIG1/2/3/4.
Configuración CHnSET.
Gestión BIAS, lead-off, SRB.
Lectura de frames.
Reconstrucción de datos 24-bit firmados.

No mezclar lógica de filtros, Bridge o Python en este driver.

ADS1299_SafeSPI

Wrapper SPI de bajo nivel.

Responsabilidades:

SPI.begin().
SPISettings.
Modo SPI.
Orden de bits.
Control CS.
SPI.transfer.

El ADS1299 debe usar:

SPI_MODE1
MSBFIRST
2 MHz inicialmente

ADS1299_Registers.h

Mapa de registros, comandos, máscaras y helpers del ADS1299.

Contiene los bytes de configuración por defecto. Cambiar con extrema precaución.

filters.h

Filtros MCU:

DC blocker / high-pass.
Notch 50 Hz.
Low-pass 40 Hz.
Conversión voltios → microvoltios.

No usar filtros para ocultar problemas de adquisición. Para validación, debe poder compararse señal raw o señal sin filtrar si se añade un modo diagnóstico.

streaming.h

Define el formato de bloque enviado del MCU al Qualcomm.

Formato actual:

Bridge.notify("eeg_block_uV", ...)

block_idx
first_sample_idx
sample_count
8 × (
  status ADS1299
  ch1_uV
  ch2_uV
  ch3_uV
  ch4_uV
)

No cambiar este formato sin actualizar también el receiver Python.

bench.h

Métricas de rendimiento.

Debe servir para:

Tasa de adquisición.
Tasa de envío.
Tiempo de filtros.
Tiempo de Bridge.notify.
Drops de cola.
Jitter.
Frames inválidos.
Eventos pending > 1.

No confundir benchmark con streaming. Activar benchmark no debe cambiar el payload EEG.

synthetic.h

Generador de señal sintética EEG-like.

Sirve para probar:

Filtros.
Streaming.
Bridge.
Python receiver.
DSP.
Dashboard.

No valida:

ADS1299 real.
DRDY.
SPI.
Electrodos.
BIAS.
Lead-off.
python/receiver.py

Recibe eventos eeg_block_uV desde Bridge.

Debe parsear el formato definido en streaming.h.

Responsabilidades esperadas:

Recibir bloques.
Validar tamaño.
Reconstruir muestras.
Detectar saltos de sample_idx.
Medir tasa de recepción.
Entregar datos al pipeline DSP.
python/dsp_core.py

Funciones DSP.

Responsabilidades típicas:

PSD.
Bandpower.
Ventanas.
Welch/periodogram/multitaper si existe.
Bandas EEG: delta, theta, alpha, beta, gamma.

Debe permanecer independiente del dashboard.

python/eeg_signal_processor.py

Gestión de buffers, ventanas y extracción de features EEG.

Debe recibir muestras ya reconstruidas por el receiver.

python/backend_service.py

Orquestador backend.

Debe conectar:


receiver
→ buffers
→ DSP
→ estado compartido
→ dashboard

python/app_state.py

Estado compartido, snapshots, historial o persistencia temporal.

Debe evitar condiciones de carrera y estructuras inconsistentes.

python/dashboard.py

Interfaz web.

Debe mostrar:

Señal temporal si existe.
Bandpowers.
Métricas de recepción.
Estado de adquisición.
Tasas.
Warnings.

No debe contener lógica pesada de adquisición ni DSP principal.

python/main.py

Punto de entrada de la app Python.

Debe iniciar backend, receiver y dashboard según la arquitectura App Lab.

5. Estado técnico actual conocido

El hardware ya ha demostrado:

ADS1299 detectado por SPI.
ID leído: 0x3C.
Variante esperada: ADS1299-4.
DRDY correcto en pin 7.
START + RDATAC activos.
Frames válidos observados:
status=0xC00000.
Captura real ya genera muestras.
El problema actual está en estabilizar loop, métricas, impresión y posterior streaming.

El firmware ya ha demostrado:

ADS1299 → SPI → MCU → frame válido
MCU → Bridge.notify → Qualcomm/Python
Python receiver → DSP → dashboard


6. Flujo de datos exacto
6.1 Etapa ADC

El ADS1299 entrega frames RDATAC:

3 bytes status
3 bytes canal 1
3 bytes canal 2
3 bytes canal 3
3 bytes canal 4

15 bytes/frame
STATUS[23:20] = 1100b

Por tanto, en firmware:

(status & 0xF00000) == 0xC00000

6.2 Reconstrucción 24-bit

Cada canal se reconstruye como entero firmado de 24 bits con extensión de signo a int32_t.

No romper esta lógica:

uint32_t u = (b0 << 16) | (b1 << 8) | b2;
if (u & 0x00800000UL) u |= 0xFF000000UL;
return (int32_t)u;
6.3 Escala

El firmware usa:

LSB_V = 2.235e-8f

y calcula:

float v = ch_raw * LSB_V;

Después convierte:

microvoltios = volts_to_uV_i32(v);
6.4 Filtrado MCU

Cadena actual:

raw counts
→ voltios
→ high-pass/DC blocker 0.5 Hz
→ notch 50 Hz
→ low-pass 40 Hz
→ microvoltios int32
6.5 Streaming

Bloques de 8 muestras:

BLOCK_SAMPLES = 8

A 250 Hz:

31.25 bloques/s

Payload por bloque:

block_idx
first_sample_idx
sample_count
status0, ch0_0, ch0_1, ch0_2, ch0_3
...
status7, ch7_0, ch7_1, ch7_2, ch7_3



7. Reglas de modificación
Reglas generales
Hacer cambios pequeños y revisables.
No hacer refactors grandes sin justificación técnica.
No cambiar varios subsistemas en un mismo cambio si no es necesario.
Mantener compatibilidad con Arduino App Lab.
Mantener código legible, comentado y sin redundancias.
No introducir delays innecesarios en loop().
No bloquear el loop de adquisición.
No usar prints excesivos durante adquisición real.
No duplicar lógica entre firmware y Python.
No cambiar nombres de eventos Bridge sin actualizar ambos lados.


Firmware

No cambiar sin permiso:

ADS1299Plus::NUM_CHANNELS == 4
PIN_DRDY = 7
BLOCK_SAMPLES = 8
Bridge.notify("eeg_block_uV", ...)

Cualquier cambio en formato de datos debe incluir actualización coordinada en Python.

Python

Separar responsabilidades:

receiver.py             → recepción y parseo
dsp_core.py             → DSP puro
eeg_signal_processor.py → buffer/features
backend_service.py      → orquestación
dashboard.py            → presentación
app_state.py            → estado
main.py                 → arranque

No poner DSP pesado en dashboard.py.

No poner lógica de UI en dsp_core.py.

8. Estilo de código esperado
C++ / Arduino
Código simple y explícito.
Nombres claros.
Comentarios donde haya hardware, timing o decisiones del datasheet.
Evitar prints dentro de rutas críticas.
Evitar asignaciones dinámicas en loop.
Evitar delays en adquisición.
Mantener estructuras fijas.
Usar tipos explícitos: uint32_t, int32_t, uint8_t.
Medir antes de optimizar.
Python
Separación clara entre recepción, procesamiento, estado y UI.
Type hints cuando aporten claridad.
Docstrings en funciones importantes.
Evitar dependencias pesadas innecesarias.
Evitar bloquear el hilo de recepción.
No recalcular DSP si no hay datos nuevos.
Manejar errores sin romper la app completa.
Mantener compatibilidad con App Lab.
Comentarios

Los comentarios deben explicar:

por qué se hace algo
qué restricción de hardware existe
qué formato se espera
qué riesgo se evita

Evitar comentarios que solo repiten el código.

9. Rendimiento y tiempo real

La adquisición ADS1299 debe cumplir:

250 muestras/s por canal
4 ms entre muestras

El loop debe ser lo más ligero posible.

Riesgos principales:

Monitor.print excesivo.
Bridge.call síncrono en adquisición.
Bridge.notify demasiado frecuente.
Procesamiento DSP pesado en MCU.
Lecturas SPI fuera de DRDY.
Acumulación de drdy_count.
Intentar leer muchos frames cuando pending > 1.

Regla importante:

drdy_count no es una FIFO de muestras.
Si pending > 1, leer solo un frame actual y registrar pérdida/jitter.
10. Bridge y comunicación MCU → MPU

Distinguir claramente:

Bridge.call("linux_started")

y:

Bridge.notify("eeg_block_uV", ...)

Bridge.call es handshake/RPC síncrono.

Bridge.notify es el mecanismo de streaming de datos EEG por bloques.

No confundir BENCH_NOTIFY_ENABLED con benchmark general.

BENCH_NOTIFY_ENABLED

controla si se envían bloques EEG por Bridge.

No controla si se imprime benchmark.

Si se necesita controlar impresión benchmark, usar una variable separada:

BENCH_REPORT_ENABLED
11. Validación esperada
Validación firmware ADS1299

Comprobar:

ADS1299 ID = 0x3C
status = 0xC00000
gen/s ≈ 250
frames inválidos mínimos
pending > 1 bajo o contabilizado
sin bloqueo por Monitor
sin saturación del loop
Validación streaming

Con BENCH_NOTIFY_ENABLED=true:

sent/s ≈ 250
blk_sent/s ≈ 31.25
queue drops = 0
Python recibe eeg_block_uV
sample_idx sin saltos inesperados
Validación Python

Comprobar:

rx sample rate ≈ 250 Hz
rx block rate ≈ 31.25 Hz
buffer estable
features actualizadas
dashboard fluido
sin stutter excesivo
12. Pruebas antes de aceptar cambios

Cada cambio propuesto debe indicar:

Archivos modificados.
Motivo técnico.
Riesgo que reduce.
Posibles efectos secundarios.
Cómo probar en UNO Q.
Qué salida esperada ver en Monitor/dashboard.

No aceptar cambios que solo “parecen limpiar” si pueden romper timing o formato.

13. Prioridades del desarrollo
Prioridad 1 — Captura real estable
ADS1299.
DRDY.
RDATAC.
Frames válidos.
Tasa 250 Hz.
Prioridad 2 — Streaming robusto
Bloques de 8.
Bridge notify.
Python receiver.
Detección de pérdidas.
Prioridad 3 — DSP Python
Ventanas.
PSD.
Bandpowers.
Métricas.
Preparación para MIDI.
Prioridad 4 — Dashboard
Visualización clara.
Métricas útiles.
No bloquear backend.
UI fluida.
Prioridad 5 — MIDI / sonificación
Mapear features EEG a eventos MIDI.
Mantener baja latencia.
Evitar falsas detecciones por ruido.
14. Cómo debe trabajar el agente

Antes de modificar:

Leer este archivo.
Revisar los archivos afectados.
Explicar arquitectura relevante.
Proponer cambios mínimos.
Esperar confirmación si el cambio es grande.

Al modificar:

Mantener cambios pequeños.
Evitar redundancias.
Mantener comentarios técnicos útiles.
No tocar archivos no relacionados.
No cambiar contratos entre firmware y Python sin actualizar ambos lados.

Después de modificar:

Resumir cambios.
Indicar pruebas.
Indicar riesgos restantes.
Indicar siguiente paso recomendado.
15. Convenciones de commits

Usar commits claros:

Stabilize ADS1299 DRDY acquisition
Add benchmark report toggle
Improve EEG block receiver validation
Add sample loss metrics
Refactor dashboard presentation only

Evitar commits genéricos como:

fix
changes
update
final
16. Cosas que NO debe hacer el agente
No cambiar pines sin permiso.
No sustituir toda la arquitectura.
No mezclar firmware, Python y dashboard en una misma modificación grande.
No eliminar el modo sintético.
No eliminar benchmarks.
No ocultar errores de frame.
No cambiar Bridge.notify("eeg_block_uV") sin actualizar receiver.py.
No asumir que los datos son correctos sin validar status.
No asumir que Python recibe 250 Hz sin medirlo.
No usar código bloqueante en adquisición real.
No introducir dependencias Python innecesarias.


## 17. Knowledge updates / confirmed facts

This section stores only durable facts discovered during development.

Rules:
- Add only facts that affect future development.
- Do not paste long logs.
- Do not duplicate code.
- Prefer short bullets.
- Include date and context.
- If a fact becomes obsolete, update or remove it.

### 2026-05-04 — ADS1299 bring-up

- ADS1299-4PAG detected by SPI with ID `0x3C`.
- Real DRDY pin on current wiring is `PIN_DRDY = 7`.
- Valid RDATAC frames observed with `status = 0xC00000`.
- `drdy_count` is not a FIFO. If `pending > 1`, read one current frame and count a lag/loss event.
- `BENCH_NOTIFY_ENABLED` controls Bridge EEG block publishing, not benchmark printing.




