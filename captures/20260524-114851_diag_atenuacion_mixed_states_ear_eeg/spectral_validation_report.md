# Spectral validation report

- Capture: 20260524-114851_diag_atenuacion_mixed_states_ear_eeg
- Condition: diag_atenuacion_mixed_states_ear_eeg
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 702
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.1396011396011396

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.441542870482571 | 0.6466415884809698 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.12688874277654966 | 0.21426021232465803 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.04794239046527117 | 0.08614597544715795 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.07877638383018376 | 0.20702305246685512 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.2877936664196701 | 0.4330179619187711 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.34982903304452384 | 0.23329538383534906 | 0.5258707117331048 |
| calmness | 0.018962372741445403 | 0.007519487109265181 | 0.0386777437903723 |
| tension | 0.5655431035973206 | 0.43733463265569783 | 0.6647658572011024 |
| rhythmic_density | 0.4222914179670737 | 0.3232637699289571 | 0.5574454595045482 |
| register | 0.29130814665266946 | 0.25870666099865375 | 0.35574514600239143 |
| harmonic_stability | 0.16445009797077403 | 0.1251853615974121 | 0.22295904034534536 |
| velocity_factor | 0.5448803231311667 | 0.46330676868474446 | 0.6681094982131734 |
| note_probability | 0.48783313437365905 | 0.4086110159431658 | 0.5959563676036385 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
