# Spectral validation report

- Capture: 20260523-175959_post_configfix_shorted_inputs
- Condition: post_configfix_shorted_inputs
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 213
- Median quality score: 0.9
- Low-quality/artifact fraction: 0.0

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.0 | 0.9927997361822246 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.0 | 0.003992111615060331 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.0 | 0.0015175307948821295 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.0 | 0.0013910038199323373 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.0 | 0.0004508268886469685 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.0 | 0.0 | 0.03538088650165519 |
| calmness | 0.0 | 0.0 | 0.002107618543256156 |
| tension | 0.0 | 0.0 | 0.3939386492888043 |
| rhythmic_density | 0.0 | 0.0 | 0.16087610347715736 |
| register | 0.2542372881355932 | 0.2542372881355932 | 0.2561703474867453 |
| harmonic_stability | 0.35 | 0.21335294741120134 | 0.35 |
| velocity_factor | 0.3 | 0.3 | 0.3247666205511586 |
| note_probability | 0.15 | 0.15 | 0.27870088278172594 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
