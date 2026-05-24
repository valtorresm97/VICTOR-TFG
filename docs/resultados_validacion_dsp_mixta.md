# Resultados de validacion DSP en captura mixta

Fecha: 2026-05-24

Captura analizada:

```text
captures/20260524-104015_live_dsp_validation_mixed_states_ear_eeg/
```

## Objetivo

Validar el comportamiento del DSP espectral en funcionamiento real continuo,
con una unica captura larga que contiene varios estados fisiologicos y
artefactos controlados.

Protocolo ejecutado:

```text
0:00-0:30   ojos abiertos, reposo
0:30-1:00   ojos cerrados, reposo
1:00-1:20   mandibula suave/controlada
1:20-1:50   recuperacion
1:50-2:10   parpadeos/frente controlada
2:10-2:40   recuperacion
2:40-3:10   ojos cerrados otra vez
```

Analisis:

```bash
python3 python/tools/analyze_eeg_capture.py "$DIR"
python3 python/tools/validate_spectral_features.py "$DIR" --channel 0 --window-sec 4 --hop-samples 64
```

Adicionalmente se segmentaron los CSV generados:

- `windowed_bandpowers.csv`
- `windowed_sonification_features.csv`

## Calidad general

La captura completa tiene:

| Metrica | Valor |
| --- | ---: |
| Duracion observada | 181.86 s |
| Frecuencia efectiva | 250.00 Hz |
| Muestras recibidas | 45464 |
| Sample gaps | 0 |
| Invalid status | 0 |
| RMS global CH1 | 757.65 uV |
| RMS mediano 2 s | 50.84 uV |
| Mejor ventana | 8.43 uV |
| Artefactos 2 s | 10 % |
| Median spectral quality 4 s | 1.0 |
| Low-quality/artifact windows 4 s | 10.94 % |

Interpretacion:

La cadena de adquisicion y DSP se mantiene estable durante una captura larga.
Los valores globales se elevan por los tramos de artefacto, pero las ventanas
limpias vuelven a rangos plausibles.

## Resumen por segmentos

| Segmento | Ventanas | Calidad | Ventanas malas | RMS uV | alpha_rel | beta_rel | gamma_rel | slow | fast | activity | calmness | tension | note_prob |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ojos abiertos 1 | 110 | 1.00 | 0.0 % | 49.00 | 0.0586 | 0.1160 | 0.3345 | 0.4747 | 0.4579 | 0.4236 | 0.0222 | 0.6003 | 0.5525 |
| ojos cerrados 1 | 117 | 1.00 | 0.0 % | 53.14 | 0.0701 | 0.0967 | 0.2986 | 0.5379 | 0.4010 | 0.3671 | 0.0265 | 0.5377 | 0.4851 |
| mandibula | 78 | 0.40 | 60.3 % | 2332.31 | 0.0349 | 0.1346 | 0.1434 | 0.6693 | 0.2910 | 0.4962 | 0.0155 | 0.6448 | 0.5814 |
| recuperacion 1 | 117 | 0.82 | 11.1 % | 58.60 | 0.0459 | 0.0654 | 0.2879 | 0.6093 | 0.3463 | 0.2487 | 0.0172 | 0.5471 | 0.4369 |
| parpadeo/frente | 78 | 0.75 | 0.0 % | 47.57 | 0.0528 | 0.0750 | 0.3292 | 0.5351 | 0.4075 | 0.3383 | 0.0242 | 0.5339 | 0.4754 |
| recuperacion 2 | 118 | 0.75 | 0.0 % | 48.21 | 0.0545 | 0.1000 | 0.3333 | 0.5055 | 0.4319 | 0.3888 | 0.0187 | 0.5728 | 0.5162 |
| ojos cerrados 2 | 77 | 1.00 | 20.8 % | 44.72 | 0.0711 | 0.0863 | 0.2707 | 0.5532 | 0.3589 | 0.4081 | 0.0339 | 0.5020 | 0.5041 |

## Observaciones clave

### 1. El DSP detecta claramente mandibula/EMG

Comparando mandibula contra recuperacion 1:

| Metrica | Mandibula | Recuperacion 1 | Cambio |
| --- | ---: | ---: | ---: |
| RMS uV | 2332.31 | 58.60 | 39.8x |
| Quality score | 0.40 | 0.82 | baja fuerte |
| Ventanas malas | 60.3 % | 11.1 % | aumenta claro |
| Tension | 0.6448 | 0.5471 | aumenta |
| Note probability | 0.5814 | 0.4369 | aumenta |

Conclusion: el DSP y la metrica de calidad detectan correctamente un tramo de
artefacto muscular/movimiento. Esto valida que el sistema puede distinguir
reposo de contaminacion fuerte.

### 2. Alfa sube en ojos cerrados, pero menos que en capturas separadas

Comparacion contra ojos abiertos iniciales:

| Comparacion | alpha_rel ratio | RMS ratio | Calidad |
| --- | ---: | ---: | --- |
| ojos cerrados 1 / ojos abiertos 1 | 1.20x | 1.09x | 1.0 vs 1.0 |
| ojos cerrados 2 / ojos abiertos 1 | 1.21x | 0.91x | 1.0 vs 1.0 |

Conclusion: en esta captura mixta hay aumento de alpha_rel con ojos cerrados,
pero solo alrededor de 20 %. Es coherente con alfa preliminar, no tan fuerte
como la comparacion separada ear open/closed, donde alpha_rel aumento 2.47x.

Interpretacion probable:

- La captura mixta tiene cambios de postura/estado y transiciones.
- Las ventanas de 4 s con solape mezclan parcialmente estados cercanos.
- El montaje ear-EEG puede mostrar alfa, pero la respuesta no siempre sera
  grande en cada ensayo.

### 3. Parpadeo/frente no se marco tan fuerte como mandibula

El tramo de parpadeo/frente mostro:

- RMS mediano 47.57 uV.
- Quality score 0.75.
- Ventanas malas 0 % segun umbral actual.
- 50 Hz alto en ese tramo y recuperacion 2.

Conclusion: el protocolo de parpadeo/frente en esta captura fue menos agresivo
que el control previo Fp1-Fp2. Para detectar parpadeo con ear-EEG puede hacer
falta un criterio adicional basado en baja frecuencia/forma temporal, no solo
RMS y pico-pico.

### 4. Los controles de sonificacion responden, pero necesitan quality gate

Durante mandibula:

- `activity` aumenta a 0.496.
- `tension` aumenta a 0.645.
- `note_probability` aumenta a 0.581.

Esto confirma que, si se usaran directamente, los artefactos podrian generar
mas actividad musical. Por tanto, antes de sonificacion final conviene usar un
`spectral_quality_score` live para congelar o atenuar controles cuando la
calidad baje.

## Validacion del DSP live

| Aspecto | Resultado | Estado |
| --- | --- | --- |
| Duracion larga sin fallos | 181.86 s | OK |
| Sample gaps | 0 | OK |
| Invalid status | 0 | OK |
| Ventanas limpias recuperadas tras artefacto | si | OK |
| Deteccion mandibula | muy clara | OK |
| Alfa ojos cerrados | aumenta moderadamente | VALIDADO PRELIMINAR |
| Parpadeo/frente en ear-EEG | menos claro | DUDOSO |
| Controles musicales sin quality gate | sensibles a artefacto | NECESITA MEJORA |

## Decision

El DSP espectral queda validado preliminarmente para funcionamiento real
continuo:

- Calcula features durante varios minutos sin romperse.
- Responde a estados reales.
- Detecta artefactos fuertes.
- Permite recuperar ventanas limpias despues de artefactos.

Pero antes de estudiar parametros musicales finales se recomienda implementar
una capa live de calidad:

```text
spectral_quality_score
quality gate
freeze/attenuate sonification when quality is low
```

## Proximos pasos

1. Crear una metrica live de calidad espectral en el backend.
2. Exponerla en snapshot/UI.
3. Usarla para congelar o reducir:
   - activity,
   - tension,
   - rhythmic_density,
   - note_probability,
   cuando haya artefacto.
4. Repetir captura mixta y comprobar que los controles musicales no se disparan
   durante mandibula/frente.
5. Despues pasar al estudio de parametros de sonificacion.
