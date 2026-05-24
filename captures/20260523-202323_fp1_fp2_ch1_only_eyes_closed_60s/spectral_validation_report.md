# Spectral validation report

- Capture: 20260523-202323_fp1_fp2_ch1_only_eyes_closed_60s
- Condition: fp1_fp2_ch1_only_eyes_closed_60s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 208
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.15865384615384615

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.4993290584310144 | 0.7158608694635408 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.09414443324774857 | 0.17730157173735386 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.04356522358161345 | 0.08136148163369775 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.06407442543922816 | 0.24325208957431396 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.28053396104619155 | 0.37804039770790204 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.3017755716775573 | 0.24291612257403827 | 0.6307523998432901 |
| calmness | 0.017276645002098738 | 0.0061427081756799985 | 0.033156920196111175 |
| tension | 0.5525066850654561 | 0.44757945548513467 | 0.7082832583653368 |
| rhythmic_density | 0.3785964275771647 | 0.3297282280019199 | 0.6564195718027493 |
| register | 0.29906670088494763 | 0.2672986132994895 | 0.34177621346856135 |
| harmonic_stability | 0.16774036966890368 | 0.10667807481599013 | 0.2123673428861093 |
| velocity_factor | 0.5112429001742901 | 0.4700412858018269 | 0.7415266798903031 |
| note_probability | 0.4528771420617318 | 0.41378258240153587 | 0.6751356574421997 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
