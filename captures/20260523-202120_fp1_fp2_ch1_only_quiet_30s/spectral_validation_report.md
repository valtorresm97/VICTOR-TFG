# Spectral validation report

- Capture: 20260523-202120_fp1_fp2_ch1_only_quiet_30s
- Condition: fp1_fp2_ch1_only_quiet_30s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 99
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.0

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.3813590517713734 | 0.6122685097055189 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.1196470375725704 | 0.15705402213372643 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.05437256815934472 | 0.10146390324771097 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.15126335762100956 | 0.20049322029905103 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.2988758783435356 | 0.3673014702269582 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.4090569790533375 | 0.30891318036589815 | 0.4418320350488035 |
| calmness | 0.01394014709372976 | 0.007576592602170786 | 0.04065199172311521 |
| tension | 0.6608061743447038 | 0.5340972514317244 | 0.6903769860372658 |
| rhythmic_density | 0.4959975047168602 | 0.41868851108885663 | 0.5234766280622526 |
| register | 0.28503630473494596 | 0.2571048750019101 | 0.34175254345413186 |
| harmonic_stability | 0.12720764022487488 | 0.11409932799459901 | 0.19148156781330045 |
| velocity_factor | 0.5863398853373363 | 0.5162392262561288 | 0.6092824245341625 |
| note_probability | 0.5467980037734883 | 0.48495080887108544 | 0.5687813024498022 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
