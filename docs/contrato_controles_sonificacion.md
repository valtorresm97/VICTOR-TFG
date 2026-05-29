# Contrato de controles de sonificacion EEG

## Objetivo

Este documento fija los nombres reportables que deben aparecer en `snapshot`, WebUI, capturas finales y documentacion TFG para los controles de sonificacion derivados de features espectrales EEG.

La regla de esta migracion es: **renombrar el contrato publico sin cambiar el comportamiento musical**. Las formulas, pesos, umbrales, suavizado EMA, quality gate y generacion MIDI deben mantenerse equivalentes a la version anterior.

## Nombres publicos actuales

| Control publico | Lectura TFG | Origen EEG principal | Uso musical equivalente |
| --- | --- | --- | --- |
| `alpha_drive` | Predominio relativo alfa frente a beta | `bandpower_rel.alpha`, `bandpower_rel.beta` | Alias interno antiguo: `calmness` |
| `beta_gamma_drive` | Activacion rapida beta/gamma | `bandpower_rel.beta`, `bandpower_rel.gamma` | Alias interno antiguo: `tension` |
| `rms_beta_activity` | Actividad global por RMS y beta | `rms`, `bandpower_rel.beta`, `bandpower_rel.gamma` | Alias interno antiguo: `activity` |
| `band_driven_density` | Densidad rÃ­tmica por bandas rapidas/RMS | `beta`, `gamma`, `rms_norm`, `alpha_drive` | Antes reportado como `rhythmic_density` |
| `spectral_register` | Registro musical guiado por espectro | `peak_alpha`/`peak_freq`, beta, gamma | Alias interno antiguo: `register` |
| `alpha_stability` | Estabilidad asociada a alfa y baja actividad RMS | `alpha_drive`, `theta`, `rms_norm` | Alias interno antiguo: `harmonic_stability` |
| `rms_band_velocity` | DinÃ¡mica/velocity por RMS y bandas rapidas | `rms_norm`, beta, gamma | Alias interno antiguo: `velocity_factor` |
| `band_note_probability` | Probabilidad de nota por densidad espectral | `band_driven_density` | Alias interno antiguo: `note_probability` |

## Campos legacy

Los nombres antiguos no deben usarse en documentaciÃ³n ni UI nueva:

- `calmness`
- `tension`
- `harmonic_stability`
- `activity`
- `velocity_factor`
- `note_probability`
- `register`

Para evitar romper el motor musical durante la migracion, `SonificationFeatures` mantiene alias internos de solo lectura. Estos alias permiten que el pipeline siga sonando igual aunque algunos modulos internos todavia lean atributos historicos.

## Contrato de snapshot

El snapshot publico debe exponer los nombres nuevos dentro de:

```text
snapshot["sonification"]
```

Ejemplo esperado:

```json
{
  "valid": true,
  "quality_score": 0.91,
  "quality_gate": 1.0,
  "quality_state": "clean",
  "alpha_drive": 0.62,
  "beta_gamma_drive": 0.31,
  "rms_beta_activity": 0.42,
  "band_driven_density": 0.38,
  "spectral_register": 0.47,
  "alpha_stability": 0.66,
  "rms_band_velocity": 0.58,
  "band_note_probability": 0.45
}
```

## Relacion con capturas finales

`python/tools/final_capture_session.py` guarda durante la captura:

- `music_snapshots.jsonl`: snapshots periodicos con `features`, `sonification`, `music` y `midi`.
- `music_notes.csv`: notas deduplicadas extraidas desde `music.recent_notes`.
- `music_capture_summary.json`: resumen de snapshots musicales y notas extraidas.

A partir de esta migracion, `music_snapshots.jsonl` debe contener los nombres nuevos en `sonification` para poder representar posteriormente las graficas EEG junto con controles de sonificacion y notas MIDI.

## Validacion recomendada en placa

```bash
cd /home/arduino/ArduinoApps/eeg_midi
python3 -m py_compile \
  python/sonification_features.py \
  python/music_segment.py \
  python/tools/final_capture_session.py
```

Despues de arrancar App Lab y esperar datos:

```bash
cat state/snapshot.json | python3 -m json.tool | grep -E "alpha_drive|beta_gamma_drive|rms_beta_activity|band_driven_density|spectral_register|alpha_stability|rms_band_velocity|band_note_probability"
```

Durante las capturas finales, comprobar una carpeta final:

```bash
DIR=$(ls -td "captures/capturas finales"/* | head -1)
head -1 "$DIR/music_snapshots.jsonl" | python3 -m json.tool | grep -E "alpha_drive|beta_gamma_drive|rms_beta_activity|band_driven_density|spectral_register|alpha_stability|rms_band_velocity|band_note_probability"
head "$DIR/music_notes.csv"
```



