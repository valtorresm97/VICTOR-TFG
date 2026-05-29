# Sesion final EEG-MIDI

## Datos fijos

| Campo | Valor |
| --- | --- |
| Sujeto | `s00_home_test` |
| Sesion | `20260528` |
| Hora inicio | `13:50` |
| Hora fin | `PENDIENTE` |
| Entorno | `home` |
| Montage | `ear_eeg_ch1_only` |
| Modelo | `modelo_captura_final` |
| ADS_MODE | `bias_ch1_only_loff_off` |
| Carpeta final | `captures/capturas pruebas casa` |
| Rama | `docs/capture-protocol` |
| Commit | `7ec0ea21605a4e7200491c5a483ea6eabd2ddc84` |
| Dirty state | `dirty` |
| Python | `3.13.5` |

## Electrodos

| Electrodo | Posicion |
| --- | --- |
| CH1P | `mastoide izq` |
| CH1N | `mastoide drch` |
| BIAS/RLD | `muneca izq` |

## Capturas

| Orden | Condicion | Duracion | Carpeta | EEG | Musica | Decision | Comentario |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| 00 | `home_precheck_15s` | 15 s | `captures/capturas pruebas casa/20260528-115131_s00_home_test_20260528_ear_eeg_ch1_only_00_home_precheck_15s` | `eeg_timeseries.csv` | `captures/capturas pruebas casa/20260528-115131_s00_home_test_20260528_ear_eeg_ch1_only_00_home_precheck_15s/music_notes.csv` | `aceptada_prueba` | `Infraestructura OK: EEG, metadata, musica y snapshots guardados; calidad fisiologica dudosa por 50 Hz/amplitud` |
| 01 | `home_eyes_open_30s` | 30 s | `captures/capturas pruebas casa/20260528-115224_s00_home_test_20260528_ear_eeg_ch1_only_01_home_eyes_open_30s` | `eeg_timeseries.csv` | `captures/capturas pruebas casa/20260528-115224_s00_home_test_20260528_ear_eeg_ch1_only_01_home_eyes_open_30s/music_notes.csv` | `aceptada_prueba` | `Ojos abiertos: transporte OK y musica guardada; senal no valida como captura final por amplitud/artefactos` |
| 02 | `home_eyes_closed_30s` | 30 s | `captures/capturas pruebas casa/20260528-115312_s00_home_test_20260528_ear_eeg_ch1_only_02_home_eyes_closed_30s` | `eeg_timeseries.csv` | `captures/capturas pruebas casa/20260528-115312_s00_home_test_20260528_ear_eeg_ch1_only_02_home_eyes_closed_30s/music_notes.csv` | `aceptada_prueba` | `Ojos cerrados: transporte OK y musica guardada; senal fisiologicamente sospechosa por RMS/PTP altos` |
| 03 | `home_blink_15s` | 15 s | `captures/capturas pruebas casa/20260528-115404_s00_home_test_20260528_ear_eeg_ch1_only_03_home_blink_15s` | `eeg_timeseries.csv` | `captures/capturas pruebas casa/20260528-115404_s00_home_test_20260528_ear_eeg_ch1_only_03_home_blink_15s/music_notes.csv` | `aceptada_prueba` | `Parpadeo: artefacto registrado correctamente; no usar como reposo EEG` |

## Cierre

| Campo | Valor |
| --- | --- |
| Hora fin | `13:54` |
| Sesion valida | `parcial` |
| Comentario final | `Primera prueba en casa para validar montaje, musica y guardado de capturas` |





