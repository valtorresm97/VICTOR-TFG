# Spectral validation report

- Capture: 20260528-145448_s01_20260528_ear_eeg_ch1_only_03_quiet_rest_60s
- Condition: s01_20260528_ear_eeg_ch1_only_03_quiet_rest_60s
- Channel: ch1
- Window: 4.0 s
- Hop: 0.256 s
- Windows: 210
- Median quality score: 1.0
- Low-quality/artifact fraction: 0.009523809523809525

## Band Decisions

| Band | Median rel | P95 rel | Decision | Risk |
| --- | ---: | ---: | --- | --- |
| delta | 0.43894757123063655 | 0.669938737553163 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| theta | 0.08567596694970363 | 0.2959856387089061 | USAR SOLO COMO APOYO | puede reflejar drift, parpadeo o movimiento |
| alpha | 0.0571574799388745 | 0.10776504510592111 | NECESITA MAS CAPTURAS | no validada solo por presencia; requiere open/closed robusto |
| beta | 0.09301212839605749 | 0.2008375789637998 | USAR SOLO COMO APOYO | puede aumentar con mandibula/frente/EMG |
| gamma | 0.26606933887502604 | 0.4493114098260989 | NO USAR EN TIEMPO REAL | muy sensible a EMG y ruido en EEG superficial |

## Sonification Controls

| Control | Median | P05 | P95 |
| --- | ---: | ---: | ---: |
| alpha_drive | 0.3603348764837575 | 0.2817262840612439 | 0.4969133768375557 |
| beta_gamma_drive | 0.5500166216261795 | 0.440181986751633 | 0.6052767998549322 |
| rms_beta_activity | 0.2673740279192731 | 0.2153384216600516 | 0.46039486101114585 |
| band_driven_density | 0.23669694203460734 | 0.20079238642522926 | 0.297621694779949 |
| spectral_register | 0.5559752204389148 | 0.47200019860873227 | 0.5976046391215105 |
| alpha_stability | 0.3317636093927523 | 0.27044585101651997 | 0.4524096080004713 |
| rms_band_velocity | 0.5156675731511173 | 0.4700340752579902 | 0.7070008919455415 |
| band_note_probability | 0.3393575536276859 | 0.3106339091401834 | 0.38809735582395916 |

## Interpretation

- Use relative bands and ratios before absolute powers for sonification until session normalization is validated.
- Treat beta/gamma as artifact-sensitive unless jaw/forehead controls remain clean.
- Treat delta/theta as artifact-sensitive when blink, drift, or cable movement is present.
- Alpha requires open/closed comparison before being considered validated.
