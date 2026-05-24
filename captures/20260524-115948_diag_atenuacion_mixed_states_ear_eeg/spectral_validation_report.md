# Spectral validation report

- Capture: 20260524-115948_diag_atenuacion_mixed_states_ear_eeg
- Condition: diag_atenuacion_mixed_states_ear_eeg
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 705
- Median quality score: 0.75
- Low-quality/artifact fraction: 0.06950354609929078

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.3658825994605139 | 0.5503431017865204 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.10454123004462842 | 0.18052487703522357 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.04128879633333912 | 0.07811016361189406 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.062030084245561314 | 0.19207374397465823 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.38407011704553456 | 0.577485236123608 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| activity | 0.43133167167381253 | 0.3126423901147682 | 0.5601852250569953 |
| calmness | 0.016695649229192876 | 0.00819505836356445 | 0.03277585385349583 |
| tension | 0.573409368179623 | 0.4469950915145079 | 0.6920467798014475 |
| rhythmic_density | 0.47477589374184326 | 0.3878193002564432 | 0.5917530362969967 |
| register | 0.30640934675368753 | 0.2620795339206042 | 0.3604652070861908 |
| harmonic_stability | 0.15913405248882678 | 0.11372777139509832 | 0.21418350196899757 |
| velocity_factor | 0.6019321701716689 | 0.5188496730803378 | 0.6921296575398966 |
| note_probability | 0.5298207149934747 | 0.46025544020515463 | 0.6234024290375975 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
