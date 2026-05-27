# 06. Conclusiones para sonificación

Generado automáticamente por `python/tools/build_validation_docs.py`.

La validación indica que la sonificación debe apoyarse en features relativas y suavizadas, no en potencias absolutas crudas. El `quality gate` debe actuar antes de disparar eventos musicales para evitar que mandíbula, frente o cableado se traduzcan directamente en más notas.

La observación musical posterior indicó que la respuesta sin atenuación podía resultar interesante, pero tendía a repetir pulsos de acordes. En final-v3 esta deuda queda mitigada: la armonía usa periodo mínimo de acorde (`MUSIC_CHORD_MIN_PERIOD_SEC=12.0`), umbral de cambio (`MUSIC_CHORD_CHANGE_THRESHOLD=0.45`) y la melodía usa variedad controlada (`MUSIC_PITCH_VARIETY=0.65`) con salto máximo dependiente de tensión. La separación entre armonía lenta y notas/arpegios ya existe, aunque falta validación musical formal.

La captura final respalda esta estrategia: las ventanas marcadas como baja calidad/artefacto no deberían generar cambios musicales fuertes porque `spectral_quality_score` modula `valid`, `gate_factor`, densidad, velocity y probabilidad de nota antes de que el scheduler reciba nuevos eventos.

Avances final-v3:

- MIDI físico validado con Behringer PRO VS MINI mediante `Serial1`/D1 y TX invertido obligatorio.
- WebUI con controles acotados para root note, main note y escala.
- Escalas disponibles: mayor, menor natural, blues, Spanish Phrygian, Arabic Double Harmonic, harmonic minor, phrygian dominant, minor pentatonic y major pentatonic.
- Panic MIDI disponible desde WebUI.

Matriz de decisiones: [`tables/table_05_sonification_feature_decisions.csv`](tables/table_05_sonification_feature_decisions.csv).
