# Plantilla de sesion de captura EEG-MIDI por sujeto

> Copiar este archivo como `docs/04_protocolos_captura/sesiones_captura/<YYYYMMDD>_<subject>_sesion.md` antes o despues de cada sesion. No incluir nombres reales.

## 1. Identificacion anonima

| Campo | Valor |
| --- | --- |
| Sujeto anonimo | `sXX` |
| Fecha de sesion | `YYYY-MM-DD` |
| Hora inicio | `HH:MM` |
| Hora fin | `HH:MM` |
| Operador |  |
| Entorno | `lab_quiet / classroom / home / other` |
| Consentimiento academico informado | `si / no` |
| Observaciones de privacidad |  |

## 2. Version de software y rama

Rellenar desde la placa:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
git branch --show-current
git rev-parse HEAD
git status --short
python3 --version
```

| Campo | Valor |
| --- | --- |
| Rama |  |
| Commit |  |
| Dirty state | `clean / dirty` |
| Python |  |
| App Lab ejecutandose | `si / no` |
| Notas sobre cambios locales |  |

## 3. Configuracion fija de la sesion

| Campo | Valor |
| --- | --- |
| Modelo musical fijo | `final_v3_fixed_model` |
| Root note |  |
| Main note |  |
| Escala |  |
| MIDI fisico conectado | `si / no` |
| Volumen/sintetizador |  |
| LED matrix | `off / on` |
| ADS mode | `bias_ch1_only_loff_off` |
| Frecuencia esperada | `250 Hz` |
| Canales transmitidos | `4` |
| Canal principal usado | `CH1` |

## 4. Montaje de electrodos

| Campo | Valor |
| --- | --- |
| Montaje | `fp1_fp2_ch1_only / ear_eeg_ch1_only / otro` |
| CH1P |  |
| CH1N |  |
| BIAS/RLD |  |
| Tipo de electrodo |  |
| Preparacion de piel |  |
| Contacto inicial | `bueno / dudoso / malo` |
| Cables fijados | `si / no` |
| Observaciones del montaje |  |

## 5. Comprobaciones previas

- [ ] App EEG_MIDI arrancada en App Lab.
- [ ] WebUI accesible.
- [ ] Hay streaming vivo.
- [ ] `window_ready` se activa tras unos segundos.
- [ ] Tasa de frames cercana a 250 Hz.
- [ ] Tasa de bloques cercana a 31.25 Hz.
- [ ] Sin `invalid_status` visible.
- [ ] Sin gaps visibles.
- [ ] RMS plausible.
- [ ] Senal no plana.
- [ ] Senal no saturada.
- [ ] Cables sin tension.
- [ ] Sujeto entiende las consignas.

Notas de precheck:

```text

```

## 6. Capturas realizadas

Usar una fila por captura. No borrar capturas repetidas o descartadas; marcar decision.

| Orden | Condicion | Duracion pedida | Directorio capture | Comando usado | Decision | Motivo |
| --- | --- | ---: | --- | --- | --- | --- |
| 00 | `precheck_10s` | 10 s |  |  | `aceptada / repetida / descartada` |  |
| 01 | `eyes_open_rest_60s` | 60 s |  |  | `aceptada / repetida / descartada` |  |
| 02 | `eyes_closed_rest_60s` | 60 s |  |  | `aceptada / repetida / descartada` |  |
| 03 | `quiet_rest_60s` | 60 s |  |  | `aceptada / repetida / descartada` |  |
| 04 | `blink_artifact_30s` | 30 s |  |  | `aceptada / repetida / descartada` |  |
| 05 | `jaw_artifact_30s` | 30 s |  |  | `aceptada / repetida / descartada` |  |
| 06 | `eyes_open_repeat_30s` | 30 s |  |  | `aceptada / repetida / descartada` |  |

## 7. Comandos usados

Pegar aqui los comandos reales lanzados para la sesion:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
SUBJECT=sXX
SESSION=YYYYMMDD
MONTAGE=fp1_fp2_ch1_only
MODEL=final_v3_fixed_model
OPERATOR=
ADS_MODE=bias_ch1_only_loff_off
NOTE_BASE="subject=${SUBJECT};session=${SESSION};montage=${MONTAGE};model=${MODEL};operator=${OPERATOR};ads_mode=${ADS_MODE}"

# Capturas:

```

## 8. Resumen tecnico por captura

Rellenar despues de ejecutar:

```bash
python3 python/tools/analyze_eeg_capture.py "$DIR"
python3 python/tools/validate_spectral_features.py "$DIR" --channel 0 --window-sec 4 --hop-samples 64
```

| Condicion | invalid_status | sample_gaps | block_gaps | fs efectiva | RMS/ptp plausible | 50 Hz dominante | Ventanas limpias | Observacion |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| `eyes_open_rest_60s` |  |  |  |  | `si/no` | `si/no` |  |  |
| `eyes_closed_rest_60s` |  |  |  |  | `si/no` | `si/no` |  |  |
| `quiet_rest_60s` |  |  |  |  | `si/no` | `si/no` |  |  |
| `blink_artifact_30s` |  |  |  |  | `si/no` | `si/no` |  |  |
| `jaw_artifact_30s` |  |  |  |  | `si/no` | `si/no` |  |  |

## 9. Incidencias observadas

Marcar lo que aplique:

- [ ] Movimiento de cabeza.
- [ ] Parpadeos fuera de condicion.
- [ ] Mandibula apretada en reposo.
- [ ] Habla/risa/tos.
- [ ] Cable movido.
- [ ] Electrodo recolocado.
- [ ] Ruido 50 Hz elevado.
- [ ] Saturacion/clipping.
- [ ] Senal plana.
- [ ] Cambio accidental de modelo/configuracion musical.
- [ ] Otro.

Detalle:

```text

```

## 10. Decision final de sesion

| Campo | Valor |
| --- | --- |
| Sesion valida para evidencia principal | `si / parcial / no` |
| Capturas principales aceptadas |  |
| Capturas descartadas |  |
| Motivo de descarte |  |
| Repetir sujeto | `si / no` |
| Repetir condiciones |  |

Comentario final:

```text

```



