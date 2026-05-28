# Spectral validation report

- Capture: 20260528-145251_s01_20260528_ear_eeg_ch1_only_02_eyes_closed_rest_60s
- Condition: s01_20260528_ear_eeg_ch1_only_02_eyes_closed_rest_60s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 209
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.0

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.40692540549579953 | 0.5338298363752291 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.12077699656858779 | 0.25060385726995926 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.06643639485879373 | 0.11972398149587678 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.11082134120377933 | 0.20237869001719505 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.2648332309316379 | 0.415660371159977 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.38048627201732865 | 0.31541441219719807 | 0.48713757779642003 |
| beta_gamma_drive | 0.5375812754809717 | 0.43373408202291325 | 0.5836851677117801 |
| rms_beta_activity | 0.24950187888018213 | 0.20700754684154815 | 0.357349828575729 |
| band_driven_density | 0.234046472449146 | 0.19842370994690495 | 0.28707821860972044 |
| spectral_register | 0.5478033144254804 | 0.4770666458360782 | 0.5807683504772893 |
| alpha_stability | 0.3707619891176254 | 0.3276828621933495 | 0.4655915282833872 |
| rms_band_velocity | 0.5000435797358131 | 0.45365784820347044 | 0.5982067492701941 |
| band_note_probability | 0.33723717795931685 | 0.308738967957524 | 0.3796625748877763 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
