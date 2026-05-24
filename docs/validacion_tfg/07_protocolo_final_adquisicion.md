# 07. Protocolo final de adquisición

Generado automáticamente por `python/tools/build_validation_docs.py`.

Rama recomendada para diagnóstico final:

```bash
cd /home/arduino/ArduinoApps/eeg_midi
git switch diagnosis/sonificacion-atenuacion-artefactos
git pull --ff-only
```

Después de cambiar de rama se debe ejecutar Run/compile en App Lab. El modo por defecto esperado es `bias_ch1_only_loff_off`.

Montaje recomendado: CH1 activo con electrodos colocados en configuración ear-EEG/mastoides o Fp1-Fp2 según la prueba, BIAS derivado de CH1P+CH1N y RLD/BIAS con contacto estable. Antes de grabar, fijar cables, minimizar movimiento mandibular y verificar que la UI muestra RMS plausible.

Comandos de captura y análisis:

```bash
python3 python/tools/capture_eeg_quality.py --condition final_atenuacion_artefactos_mixed_states --duration 190 --timeout-extra 260
DIR=$(ls -td captures/*_final_atenuacion_artefactos_mixed_states /app/captures/*_final_atenuacion_artefactos_mixed_states 2>/dev/null | head -1)
python3 python/tools/analyze_eeg_capture.py "$DIR"
python3 python/tools/validate_spectral_features.py "$DIR" --channel 0 --window-sec 4 --hop-samples 64
cat "$DIR/quality_report.md"
cat "$DIR/spectral_validation_report.md"
```

Aceptar una captura si no hay sample gaps ni invalid status, la frecuencia efectiva es cercana a 250 Hz, existen ventanas limpias y la fracción de artefactos es compatible con el objetivo. Rechazar o repetir si hay saturación persistente, RMS de mV en la mayoría de ventanas, 50 Hz dominante o señal plana.

Si aparece mucho 50 Hz, revisar contacto, cableado y entorno. Si el RMS o pico-pico es excesivo, repetir con postura quieta y cables fijados. Si alpha no aparece, no forzar conclusión: puede depender del montaje y del sujeto.
