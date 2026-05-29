# 06. Conclusiones para sonificación

Generado automáticamente por `python/tools/build_validation_docs.py`.

La validación indica que la sonificación debe apoyarse en features relativas y suavizadas, no en potencias absolutas crudas. El `quality gate` debe actuar antes de disparar eventos musicales para evitar que mandíbula, frente o cableado se traduzcan directamente en más notas.

La observación musical posterior indica que la respuesta sin atenuación puede resultar interesante, pero tiende a repetir pulsos de acordes. Esto no se atribuye al DSP, sino a la lógica musical: falta duración mínima de acordes, histéresis y separación entre armonía lenta y notas/arpegios.

La captura final respalda esta estrategia: pendiente de ventanas fueron marcadas como baja calidad/artefacto y por tanto no deberían generar cambios musicales fuertes.

Matriz de decisiones: [`tables/table_05_sonification_feature_decisions.csv`](tables/table_05_sonification_feature_decisions.csv).
