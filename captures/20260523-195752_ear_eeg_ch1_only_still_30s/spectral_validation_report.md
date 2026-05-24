# Spectral validation report

- Capture: 20260523-195752_ear_eeg_ch1_only_still_30s
- Condition: ear_eeg_ch1_only_still_30s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 98
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.0

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.3551889330064449 | 0.4180152763116622 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.08757116464944947 | 0.1263132963912902 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.11523051267514792 | 0.19867696466659096 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.18158219138641235 | 0.22424225077473497 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.2799494905008577 | 0.3499353079819826 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.41271566273894367 | 0.38239379194672407 | 0.4575178173292791 |
| calmness | 0.0428436112541747 | 0.014844561833811396 | 0.06972607530265647 |
| tension | 0.5482390387263059 | 0.4830677071555381 | 0.6631303361548447 |
| rhythmic_density | 0.4543685121288641 | 0.4364814347893636 | 0.5295287034274538 |
| register | 0.31342999987270814 | 0.2989170393317255 | 0.3839396403026341 |
| harmonic_stability | 0.18584291754568572 | 0.12753620750016476 | 0.22130269154193116 |
| velocity_factor | 0.5889009639172607 | 0.567675654362707 | 0.6202624721304953 |
| note_probability | 0.5134948097030914 | 0.499185147831491 | 0.5736229627419631 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
