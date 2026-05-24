# Spectral validation report

- Capture: 20260524-122200_final_atenuacion_artefactos_mixed_states
- Condition: final_atenuacion_artefactos_mixed_states
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 702
- Median quality score: 0.9119513160207233
- Low-quality/artifact fraction: 0.1168091168091168

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.36613351314601394 | 0.5037549711385708 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.10788426522036602 | 0.187461415308891 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.04135644540384423 | 0.08610977745844224 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.07775561499584822 | 0.22750848124713613 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.3788580124387747 | 0.5453723656863366 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.3900921424986249 | 0.20656378179965906 | 0.48241430969394444 |
| calmness | 0.016852705297233837 | 0.009329678951883072 | 0.2690747516843122 |
| tension | 0.5766711744347567 | 0.47980650652812784 | 0.6419416228319835 |
| rhythmic_density | 0.4381271579123841 | 0.2159990276677688 | 0.5185798318512302 |
| register | 0.29943137341567994 | 0.26089304243347206 | 0.39627556545953474 |
| harmonic_stability | 0.19214571261126162 | 0.13979894709975343 | 0.3518421692633688 |
| velocity_factor | 0.5730644997490375 | 0.4445946472597614 | 0.6376900167857613 |
| note_probability | 0.5005017263299074 | 0.3227992221342152 | 0.5648638654809841 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
