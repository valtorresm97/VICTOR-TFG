# Spectral validation report

- Capture: 20260523-201055_ear_eeg_ch1_only_eyes_closed_60s
- Condition: ear_eeg_ch1_only_eyes_closed_60s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 210
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.0

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.3685304070305137 | 0.5739488899426342 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.11013117862499534 | 0.20898739047566933 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.15793975225541973 | 0.27656400846698204 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.1373969108516795 | 0.19672603238666422 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.16258309376181307 | 0.2746239717292902 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.27618742351681436 | 0.21379573960262568 | 0.3736115537301514 |
| calmness | 0.09007429289862615 | 0.02499457919619022 | 0.17487964941508224 |
| tension | 0.39999747489566684 | 0.29258823609966095 | 0.5984646541265092 |
| rhythmic_density | 0.3408057962655155 | 0.2571612149410279 | 0.40227067318290627 |
| register | 0.30240171448318254 | 0.2728554410393707 | 0.35470558879286385 |
| harmonic_stability | 0.26803698628252526 | 0.1567850273676264 | 0.36439654122114623 |
| velocity_factor | 0.49333119646177004 | 0.449657017721838 | 0.5615280876111061 |
| note_probability | 0.4226446370124125 | 0.3557289719528224 | 0.47181653854632505 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
