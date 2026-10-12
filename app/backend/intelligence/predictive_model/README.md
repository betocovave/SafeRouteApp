# Modelo predictivo futuro

La version inicial utiliza reglas explicables en `../risk_algorithm/rules.json`.
No se carga el modelo entrenado con datos sinteticos de los prototipos.
Un modelo futuro con Scikit-learn debe recibir factores geoespaciales anonimizados,
devolver exposicion estimada y version, y registrar conjunto de entrenamiento,
evaluacion temporal y espacial, calibracion y criterios de activacion antes de sustituir las reglas.
