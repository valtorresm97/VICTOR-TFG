# Spectral validation report

- Capture: 20260528-104617_bench_real_rest_60s
- Condition: bench_real_rest_60s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 208
- Median quality score: 0.973713910301748
- Low-quality/artifact fraction: 0.17307692307692307

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.36266674403662946 | 0.5104047835515579 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.09891380696894171 | 0.2076688935829143 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.050492805030157725 | 0.11355785884323397 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.10760619840250361 | 0.3402163844186763 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.33433089884872225 | 0.46776460225163147 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.273136308780265 | 0.16083548587244278 | 0.3677913305914138 |
| calmness | 0.31166239606294704 | 0.22427587937511198 | 0.42150095669689136 |
| tension | 0.5760869913897868 | 0.5199402583552029 | 0.6612351686706058 |
| rhythmic_density | 0.24965313416264404 | 0.12346774238239583 | 0.3020014409406688 |
| register | 0.5849689002062456 | 0.5419176525251704 | 0.6360550419095934 |
| harmonic_stability | 0.30656270970216865 | 0.24101909495545623 | 0.4038465599716571 |
| velocity_factor | 0.510983100165548 | 0.4373937045775613 | 0.61512065184526 |
| note_probability | 0.34972250733011523 | 0.24877419390591668 | 0.391601152752535 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
