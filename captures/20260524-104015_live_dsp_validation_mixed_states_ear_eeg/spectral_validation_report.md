# Spectral validation report

- Capture: 20260524-104015_live_dsp_validation_mixed_states_ear_eeg
- Condition: live_dsp_validation_mixed_states_ear_eeg
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 695
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.1093525179856115

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.4105490519669681 | 0.6523030823380626 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.11187921980013332 | 0.18964014276131974 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.05452492492339165 | 0.11102406020064609 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.0935384700578839 | 0.21041069909186116 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.303852210203833 | 0.44513337832352057 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.3764808365735458 | 0.21411658008685708 | 0.5727949062283018 |
| calmness | 0.02165903596750712 | 0.00837420027345765 | 0.048112797949588594 |
| tension | 0.5566913237295683 | 0.45528343939088173 | 0.7008597923380088 |
| rhythmic_density | 0.43232381944559717 | 0.32076666818203153 | 0.6175528578116509 |
| register | 0.2921753524508478 | 0.2621162630658898 | 0.35423353346364655 |
| harmonic_stability | 0.16900666199183442 | 0.11030650699047478 | 0.22178114823775416 |
| velocity_factor | 0.5635365856014822 | 0.4498816060608 | 0.7009564343598114 |
| note_probability | 0.4958590555564777 | 0.4066133345456253 | 0.6440422862493208 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
