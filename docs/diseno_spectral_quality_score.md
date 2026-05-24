# Diseno y justificacion de `spectral_quality_score`

Fecha: 2026-05-24

Rama: `captura-datos`

## 1. Objetivo

`spectral_quality_score` es una capa de control de calidad para decidir si una
ventana reciente de EEG debe usarse para mover la sonificacion en tiempo real.

No cambia:

- adquisicion ADS1299,
- filtros firmware,
- filtros principales Python,
- definicion de bandas EEG,
- metodo multitaper,
- formato `eeg_block_uV`.

Si la calidad es baja, no se intenta "convertir" el artefacto en EEG. Se atenuan
o congelan los controles musicales mas sensibles.

## 2. Por que es necesario

Las pruebas reales demostraron tres hechos:

1. La adquisicion puede ser limpia:
   - ear-EEG quieto: RMS mediano ~12 uV.
   - ear-EEG ojos cerrados: RMS mediano ~9-10 uV.
   - Fp1-Fp2 ojos abiertos: RMS mediano ~30 uV.

2. Los artefactos pueden ser enormes:
   - mandibula en captura mixta: RMS mediano ~2332 uV.
   - ventanas malas ~60 %.

3. La sonificacion actual responde a esas features:
   - mandibula aumenta `activity`, `tension` y `note_probability`.

Por tanto, sin quality gate, una mandibula o un movimiento de frente podria
interpretarse musicalmente como "mas actividad cerebral".

## 3. Criterios usados

El score empieza en `1.0` y resta penalizaciones. Se limita a `[0, 1]`.
Las penalizaciones de transporte se calculan con deltas entre ventanas de
features. Es decir, un error antiguo queda registrado en las metricas totales,
pero no mantiene la sonificacion castigada indefinidamente si la recepcion se
recupera.

| Criterio | Umbral | Justificacion |
| --- | --- | --- |
| Ventana no lista | -0.50 | No hay suficientes muestras para PSD fiable |
| Bandpowers ausentes/NaN/Inf | -0.50 | Features espectrales no confiables |
| `status` ADS1299 invalido | -0.35 | Riesgo de problema SPI/frame |
| Perdidas/drops/malformed recientes | -0.25 | Riesgo de discontinuidad temporal en la ventana de features |
| Saturacion ADC | hasta -0.60 | Clipping invalida amplitud/espectro |
| Flatline | -0.35 | Senal congelada o entrada no fisiologica |
| RMS < 3 uV | -0.10 | Puede ser short/flatline o contacto no real |
| RMS > 120 uV | rampa hasta -0.35 | Por encima del rango habitual limpio observado |
| RMS > 200 uV | -0.25 adicional | Rango compatible con artefacto fuerte |
| PTP > 2500 uV | rampa hasta -0.30 | Golpes/transitorios amplios |
| PTP > 5000 uV | -0.20 adicional | Artefacto muy probable |
| 50 Hz ratio > 0.25 | rampa hasta -0.30 | Ruido de red empieza a dominar |
| Saltos abruptos | hasta -0.25 | Movimiento/cable/contacto |
| gamma_rel > 0.55 | -0.15 | Posible EMG/ruido de alta frecuencia |
| slow_power > 0.85 con RMS > 80 uV | -0.20 | Posible drift/parpadeo/movimiento |

## 4. Justificacion empirica de umbrales

Los umbrales salen de las capturas reales de esta conversacion:

| Condicion | RMS mediano aprox | Interpretacion |
| --- | ---: | --- |
| `shorted_inputs` | ~0 uV | prueba interna, no EEG |
| ear-EEG quieto | ~12 uV | reposo limpio |
| ear-EEG ojos abiertos/cerrados | ~9-11 uV | reposo limpio |
| Fp1-Fp2 quiet/open | ~29-30 uV | plausible, mas ruido |
| captura mixta reposo | ~45-55 uV | plausible, mas variabilidad |
| artefacto frente/parpadeo | ~174 uV | artefacto moderado |
| mandibula | >200 uV y hasta mV | artefacto fuerte |

Por eso:

- 3 uV se usa como limite inferior sospechoso.
- 120 uV marca la entrada progresiva en zona dudosa.
- 200 uV marca artefacto probable.
- 5000 uV de pico-pico marca transitorio fuerte.
- 0.25 de ratio 50 Hz se usa porque Fp1-Fp2 ya empieza a verse dominado por red
  cerca de ese valor, aunque no siempre invalida toda la ventana.

## 5. Estados

| Score | Estado | Accion |
| ---: | --- | --- |
| >= 0.85 | `clean` | usar features normalmente |
| 0.70-0.85 | `usable_with_caution` | usar con atenuacion leve |
| 0.50-0.70 | `artifact_suspected` | atenuar fuertemente |
| < 0.50 | `bad` | no generar nueva sonificacion |

El campo `gate_factor` resume la accion musical:

| Estado | gate_factor |
| --- | ---: |
| clean | 1.0 |
| usable_with_caution | 0.75 |
| artifact_suspected | 0.35 |
| bad | 0.0 |

## 6. Como afecta a sonificacion

El gate no modifica los bandpowers ni el DSP. Solo se aplica despues, en
`SonificationFeatureAdapter`.

Si la calidad baja:

- reduce `activity`,
- reduce `rhythmic_density`,
- reduce `velocity_factor`,
- reduce `note_probability`,
- lleva `tension` y `harmonic_stability` hacia valores neutros,
- evita actualizar el baseline de RMS con ventanas malas,
- si score < 0.50, marca la feature como no valida para que no se genere musica
  nueva desde esa ventana.

Por el suavizado EMA, los valores visibles no saltan de golpe a cero: tienden
hacia niveles minimos/neutros. La marca `valid=False` es la que debe impedir que
esa ventana cree nuevos eventos musicales.

Esto evita que el artefacto produzca mas notas o mas intensidad musical.

## 7. Por que no basta con filtrar mas

Un filtrado mas robusto puede ayudar, pero no puede resolver todos los artefactos:

- Parpadeos y movimiento ocular aparecen en delta/theta, bandas EEG reales.
- Mandibula y frente pueden ocupar beta/gamma, tambien bandas usadas por EEG.
- Movimiento de cable/contacto produce transitorios de baja frecuencia.
- 50 Hz puede atenuarse con notch, pero si entra fuerte puede contaminar el
  entorno espectral y modular bandpowers.
- Un filtro no distingue si 10 Hz viene de alfa fisiologico o de un artefacto
  mecanico periodico.

Por eso el enfoque correcto es:

```text
adquisicion estable
→ filtros razonables
→ PSD multitaper
→ bandpowers
→ spectral_quality_score
→ gate de sonificacion
```

No se descarta mejorar filtros en el futuro, pero no deben usarse para ocultar
una senal mala ni para validar artificialmente bandas.

## 8. Posibles mejoras futuras de filtrado manteniendo la logica DSP

Sin cambiar la logica principal de obtencion de features, se podrian estudiar:

1. Notch 50 Hz parametrico o adaptativo si el ratio 50 Hz vuelve a subir.
2. Rechazo de ventanas con transitorios antes de calcular bandpowers live.
3. Winsor/interpolacion de outliers mas conservadora.
4. Comparativa Welch vs multitaper para diagnostico, no para sustituir aun.
5. Bandpowers robustas por mediana de subventanas.
6. Quality-aware smoothing: si calidad baja, aumentar EMA o congelar.

Estas propuestas requieren pruebas A/B con CSV reales antes de entrar en
produccion.

## 9. Archivos modificados

- `python/spectral_quality.py`
- `python/backend_service.py`
- `python/sonification_features.py`

## 10. Validacion esperada en placa

Despues de `git pull`:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
python3 -m py_compile python/spectral_quality.py python/sonification_features.py python/backend_service.py
```

Arrancar App Lab y comprobar en snapshot/UI/estado que aparece:

```text
spectral_quality.score
spectral_quality.state
spectral_quality.gate_factor
spectral_quality.warnings
sonification.quality_score
sonification.quality_gate
```

Repetir protocolo mixto:

- En reposo: `score` cercano a 1.
- En mandibula: `score` debe caer.
- Durante artefacto: `note_probability`, `velocity_factor` y `rhythmic_density`
  deben atenuarse.
- En recuperacion: `score` debe volver a subir.

## 11. Decision de diseno

Se implementa primero como una capa conservadora de seguridad, no como una
reescritura del DSP ni como cambio de bandas. Esto permite justificar en el TFG
que la sonificacion se basa en features EEG plausibles y que los artefactos no
se transforman directamente en eventos musicales.
