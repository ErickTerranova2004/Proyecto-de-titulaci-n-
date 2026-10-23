# Evaluación experimental, amenazas a la validez y conclusiones

Versión vigente: **dataset y modelo v1.1** (activo en la plataforma). La versión v1 se conserva sin modificar para trazabilidad: `datos_procesados/dataset_riesgo_despliegue_v1.csv`, `modelos/modelo_riesgo_v1.*` e `informes/fase5_modelos_v1.md`.

## 1. Diseño experimental (idéntico en v1 y v1.1)

- **Etiqueta:** intento de despliegue no completado (ver `informes/fase2_variable_objetivo.md`).
- **Particiones:** temporal (75 % más antiguo para entrenamiento y 25 % más reciente para prueba). Como análisis adicional, validación cruzada agrupada por repositorio.
- **Modelos candidatos:** Dummy (tasa base), regla de historial, regresión logística, árbol de decisión, Random Forest y LightGBM. Todos con calibración sigmoide y semilla 42.
- **Selección:** mayor PR-AUC en validación cruzada agrupada dentro del entrenamiento. El conjunto de prueba no interviene.
- **Umbral:** el que maximiza F1 en las predicciones fuera de pliegue del entrenamiento.
- **Niveles de riesgo:** bajo si p es menor que la tasa base de entrenamiento; medio si está entre 1 y 2 veces esa tasa; alto si es 2 veces o más.
- **Reproducibilidad comprobada:** `train_models.py`, con el parámetro de versión añadido, reproduce v1 con métricas idénticas.

## 2. Error de etiquetado detectado en v1

### Descripción

Varias reglas de inclusión y etiquetado de v1 dependían de **información que solo existe si la ejecución avanzó**, es decir, del propio resultado. La auditoría completa está en `informes/informe_calidad_dataset_v1_1.md`.

| Regla de v1 | ¿Depende del resultado? | Filas de v1 afectadas | y = 1 | y = 0 |
|---|---|---:|---:|---:|
| Entorno efímero decidido por ejecución | Sí | 63 | 60 | 3 |
| Intención de despliegue inferida del propio resultado (fallo sin paso de despliegue → y = 1; éxito sin paso → excluido) | Sí | 229 | 229 | 0 |
| Ejecución sin `log_insights` tratada como "sin paso de despliegue" | Sí | 52 | 52 | 0 |
| Fallo en otro job con el despliegue completado → borrado | Sí; inevitable (etiqueta desconocida) | 36 (excluidas) | — | — |
| Excluir `cancelled`, `skipped` y `action_required` | Sí; inevitable (sin etiqueta) | 23 (excluidas) | — | — |
| Selección de workflows: alguna ejecución llegó a desplegar | Sí, a nivel de workflow | no medible | — | — |
| Vista previa por evento o ruta; deduplicación; variables de historial | No | — | — | — |

Las tres primeras reglas solo podían mover filas hacia **y = 1**. Por eso v1 sobrestimaba la tasa de fallos: un éxito sin paso de despliegue se descartaba, mientras que un fallo en la misma situación contaba como positivo.

### Cómo se detectó

Al registrar en la plataforma los workflows del dataset (`validar_workflows_dataset`), 22 workflows no tenían ninguna ejecución con despliegue en un entorno de aplicación. Al revisarlos se vio que solo desplegaban en clústeres efímeros de prueba y que sus filas en v1 eran todas y = 1 (fallos ocurridos antes de crear el clúster). A partir de ese caso se auditaron todas las reglas preguntando, para cada una, si la decisión usaba información que solo existe cuando la ejecución avanza.

### Cómo se corrigió (`build_dataset_v1_1.py`)

1. **El entorno se clasifica por workflow.** Un workflow es efímero si *cualquiera* de sus ejecuciones crea un clúster de prueba, y es vista previa si su ruta lo indica. Es un criterio conservador: un workflow que hace pruebas en kind y además despliega en producción se excluye.
2. **La intención de despliegue se decide sin mirar el propio resultado.** Una ejecución es un intento si *otra* ejecución del mismo workflow y del mismo contexto (evento + rama, o "tag") ejecutó un paso de despliegue (*leave-one-out*). Si ninguna otra ejecución del contexto despliega, se excluye, sea éxito o fallo. Si no hay ninguna otra ejecución en ese contexto, se marca como ambigua.
3. **Las ejecuciones sin `log_insights` se marcan como ambiguas.**
4. **Los casos ambiguos se conservan** en el dataset (columnas `ambiguo` y `motivo_ambiguo`, con y vacío) y se excluyen del entrenamiento: 591 filas.

Las variables predictoras, la partición, los candidatos, la selección, la calibración y los umbrales no cambian.

### Efecto (recalculado con los modelos guardados; `informes/fase5_modelos_v1_1.md`)

| Indicador | v1 | v1.1 |
|---|---:|---:|
| Modelo seleccionado (misma regla) | Árbol de decisión | Random Forest |
| Filas etiquetadas | 2.825 | 2.392 |
| Filas ambiguas conservadas | 0 | 591 |
| Repositorios | 414 | 348 |
| % de fallos | 19,6 % | 15,8 % |
| PR-AUC (prueba) | 0,687 (tasa base 0,235) | 0,677 (tasa base 0,196) |
| PR-AUC sin workflows que siempre fallan | 0,440 (tasa base 0,174) | 0,359 (tasa base 0,127) |
| Tasa de fallos observada: nivel bajo / medio / alto | 11,4 % / 46,4 % / 81,1 % | 8,0 % / 34,5 % / 76,9 % |
| PR-AUC sin variables de historial (ablación) | 0,526 | 0,309 |

Interpretación:
- La tasa de fallos de v1 estaba **inflada** en unos 4 puntos por reglas que dependían del resultado.
- La capacidad del modelo relativa a la tasa base se mantiene: 3,5 veces la tasa base en v1.1 frente a 2,9 en v1. Los niveles de riesgo siguen separando bien (8 % frente a 77 %).
- La mayor diferencia aparece en la **ablación**. Sin historial, v1 obtenía 0,526 y v1.1 solo 0,309. **Gran parte de la señal que v1 atribuía al contexto del commit era un artefacto del etiquetado**: los fallos tempranos de ramas y eventos que nunca despliegan se contaban como positivos. En v1.1 la predicción depende casi por completo del historial reciente de fallos.
- En v1.1 la regla de selección eligió Random Forest. En la prueba, el árbol obtiene un PR-AUC algo mayor (0,709), pero el modelo **no se cambió** tras ver la prueba.

## 3. Resultados de v1.1 (prueba temporal: 598 intentos, 19,6 % de positivos)

| Modelo | PR-AUC | ROC-AUC | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| Base (Dummy) | 0,196 | 0,500 | 0,000 | 0,000 | 0,000 |
| Regla: tasa de fallos previa | 0,615 | 0,794 | 0,885 | 0,462 | 0,607 |
| **Random Forest (seleccionado)** | **0,677** (IC 95 %: 0,589–0,761) | **0,835** | 0,716 | 0,624 | 0,667 |
| Regresión logística | 0,691 | 0,854 | 0,679 | 0,632 | 0,655 |
| Árbol de decisión | 0,709 | 0,837 | 0,883 | 0,453 | 0,599 |
| LightGBM | 0,694 | 0,834 | 0,812 | 0,479 | 0,602 |

- **Repositorios no vistos (GroupKFold):** Random Forest PR-AUC 0,613 frente a 0,573 de la regla (tasa base 0,158).

## 4. Amenazas a la validez

**Validez de constructo**
- La etiqueta mide si el intento de despliegue terminó o no, no si hubo un fallo dentro del paso de despliegue ni un incidente posterior.
- La detección de pasos de despliegue depende de patrones conocidos. Los despliegues mediante scripts propios no se detectan.

**Validez interna**
- **Sesgo de selección de workflows (no corregido):** solo entran workflows con al menos una ejecución que llegó a desplegar. Corregirlo requiere el YAML histórico de unos 1.300 workflows mediante la API con token.
- La intención de despliegue se infiere de las demás ejecuciones del mismo contexto. Esas ejecuciones pueden estar correlacionadas con la evaluada (por ejemplo, en workflows que siempre fallan): 148 filas etiquetadas de v1.1 son de este tipo.
- 591 filas ambiguas (20 % del total) quedan fuera del entrenamiento. Si su resultado real difiere sistemáticamente del de las filas etiquetadas, la muestra de entrenamiento está sesgada.
- La prevalencia cambia entre entrenamiento (14,5 %) y prueba (19,6 %).

**Validez externa**
- Repositorios de código abierto, no empresariales; periodo de 4,5 meses de 2023.
- La prueba temporal cubre pocos días, porque GHALogs guarda las 5 ejecuciones más recientes de cada workflow.
- En producción, el historial se obtiene de la API (hasta 4 ejecuciones previas). Es una aproximación a la distribución de entrenamiento.

**Validez de conclusión**
- Muestra pequeña (2.392 filas etiquetadas). Los intervalos de confianza de PR-AUC tienen una amplitud de unos ±0,09.
- Las diferencias entre los modelos candidatos están dentro de esa variabilidad.

## 5. Conclusiones vinculadas a los objetivos

1. **Identificar datos para estimar el riesgo de despliegue.** `conclusion = failure` no equivale a un fallo de despliegue. Además, las reglas que deciden qué ejecución es un intento de despliegue deben ser independientes de su resultado; si no, inflan los fallos (v1 los inflaba en unos 4 puntos). Ningún dataset público disponible permite etiquetar con fiabilidad los fallos dentro del paso de despliegue ni los incidentes en producción.
2. **Entrenar un modelo predictivo.** Con información disponible antes de la ejecución, el modelo v1.1 alcanza un PR-AUC de 0,677, unas 3,5 veces la tasa base, y supera a una regla basada solo en el historial (0,615). La señal procede casi por completo del historial reciente de fallos del workflow y del repositorio. **Esto demuestra capacidad para predecir si un intento de despliegue se completará, no para reducir fallos en producción.**
3. **Explicar las predicciones.** SHAP muestra los factores de cada predicción y las recomendaciones se vinculan a ellos mediante un código de regla.
4. **Plataforma.** El prototipo funcional (Django, React y GitHub; con SQLite en desarrollo y PostgreSQL pendiente) cuenta con roles, acceso por repositorio, trazabilidad completa, versiones del modelo y 37 pruebas automatizadas.

## 6. Trabajo futuro

- Obtener el YAML histórico por `head_sha` (con token) para eliminar el sesgo de selección y determinar la intención de despliegue a partir de las condiciones del workflow.
- Acumular etiquetas observadas con la API de jobs mediante la verificación de predicciones (subtipo `en_paso_de_despliegue`).
- Añadir métricas del cambio (archivos y líneas) y reentrenar con datos recientes y repositorios empresariales.
- Añadir ESLint al frontend con un script `npm run lint` (hoy solo se verifica con `npm run build`).
- Avisos de asignaciones con la aplicación cerrada (correo configurado o notificaciones push) y fecha de última sincronización por repositorio.
