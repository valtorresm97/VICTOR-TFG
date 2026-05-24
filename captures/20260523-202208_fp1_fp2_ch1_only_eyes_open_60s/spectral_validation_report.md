# Spectral validation report

- Capture: 20260523-202208_fp1_fp2_ch1_only_eyes_open_60s
- Condition: fp1_fp2_ch1_only_eyes_open_60s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 211
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.0

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.43192071823746164 | 0.6135552469857112 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.0779193594403659 | 0.17164393622983984 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.04116538767820229 | 0.07658031341000501 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.1327917207723399 | 0.23475376686082824 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.30602688973264064 | 0.4353897338952493 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.4141440539925501 | 0.3582680564490112 | 0.4661392485366683 |
| calmness | 0.010192672815388742 | 0.005262280265729797 | 0.025866388073699113 |
| tension | 0.6675555033005147 | 0.5511911279035917 | 0.7423822026611271 |
| rhythmic_density | 0.49773361024037893 | 0.4532616016374466 | 0.5634639829830673 |
| register | 0.2809801684334556 | 0.25950047965054945 | 0.32715351875580734 |
| harmonic_stability | 0.12317046621946981 | 0.09454812235959291 | 0.17268315001144463 |
| velocity_factor | 0.5899008377947851 | 0.550787639514308 | 0.6262974739756679 |
| note_probability | 0.5481868881923032 | 0.5126092813099573 | 0.6007711863864539 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
