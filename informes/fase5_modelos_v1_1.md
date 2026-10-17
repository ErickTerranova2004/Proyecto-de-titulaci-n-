# Fase 5. Modelos de riesgo de despliegue (v1.1)

- Datos: `datos_procesados/dataset_riesgo_despliegue_v1_1.csv` | entrenamiento: 1,794 filas (14.5 % positivos) | prueba temporal: 598 filas (19.6 % positivos).
- Etiqueta: despliegue no completado (ver `fase2_variable_objetivo.md`).
- Todas las probabilidades están calibradas (sigmoide, validación agrupada por repositorio).

## Comparación v1 vs v1.1

Métricas recalculadas con cada modelo guardado sobre la partición temporal de prueba de su propio dataset. Los datasets no son iguales, así que las diferencias reflejan sobre todo la corrección de las etiquetas, no una mejora del modelo.

| Indicador | v1 | v1.1 |
|---|---:|---:|
| Modelo seleccionado (misma regla de selección) | Árbol de decisión | Random Forest |
| Filas etiquetadas | 2,825 | 2,392 |
| Filas ambiguas conservadas (excluidas del entrenamiento) | 0 | 591 |
| Repositorios | 414 | 348 |
| Workflows | 684 | 525 |
| % de fallos (y = 1) | 19.6 % | 15.8 % |
| Filas de prueba | 707 | 598 |
| % de fallos en prueba | 23.5 % | 19.6 % |
| PR-AUC (prueba) | 0.687 | 0.677 |
| ROC-AUC (prueba) | 0.840 | 0.835 |
| PR-AUC sin workflows que siempre fallan | 0.440 | 0.359 |
| Tasa base sin workflows que siempre fallan | 17.4 % | 12.7 % |
| Tasa de fallos observada en nivel bajo (ejecuciones) | 11.4 % (536) | 8.0 % (462) |
| Tasa de fallos observada en nivel medio (ejecuciones) | 46.4 % (97) | 34.5 % (58) |
| Tasa de fallos observada en nivel alto (ejecuciones) | 81.1 % (74) | 76.9 % (78) |

## 1. Selección del modelo (solo entrenamiento, validación cruzada agrupada por repositorio)

| Modelo | PR-AUC | ROC-AUC | Brier |
|---|---:|---:|---:|
| Base: tasa de fallos (Dummy) | 0.132 | 0.450 | 0.125 |
| Regresión logística | 0.562 | 0.842 | 0.085 |
| Árbol de decisión | 0.566 | 0.823 | 0.083 |
| Random Forest | 0.586 | 0.843 | 0.080 |
| LightGBM | 0.550 | 0.830 | 0.088 |
| Regla: tasa de fallos previa del workflow | 0.556 | 0.833 | 0.092 |

**Seleccionado por PR-AUC: Random Forest.** La selección se hizo sin usar el conjunto de prueba. Las diferencias de PR-AUC entre regresión logística, árbol, Random Forest y LightGBM en esta validación son pequeñas frente a la variabilidad esperable con este tamaño de muestra; el modelo seleccionado no se cambia tras ver los resultados de prueba para evitar sesgo de selección. (El ROC-AUC del Dummy difiere de 0,5 porque cada pliegue predice una constante distinta.)

## 2. Evaluación en la partición temporal de prueba

El umbral de clasificación se eligió maximizando F1 en las predicciones fuera de pliegue del entrenamiento.

| Modelo | PR-AUC | ROC-AUC | Brier | Precision | Recall | F1 | MCC | Balanced acc. | Accuracy | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Base: tasa de fallos (Dummy) | 0.196 | 0.500 | 0.160 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 | 0.804 | 481.000 | 0.000 | 117.000 | 0.000 |
| Regresión logística | 0.691 | 0.854 | 0.106 | 0.679 | 0.632 | 0.655 | 0.575 | 0.780 | 0.870 | 446.000 | 35.000 | 43.000 | 74.000 |
| Árbol de decisión | 0.709 | 0.837 | 0.097 | 0.883 | 0.453 | 0.599 | 0.579 | 0.719 | 0.881 | 474.000 | 7.000 | 64.000 | 53.000 |
| Random Forest | 0.677 | 0.835 | 0.098 | 0.716 | 0.624 | 0.667 | 0.594 | 0.782 | 0.878 | 452.000 | 29.000 | 44.000 | 73.000 |
| LightGBM | 0.694 | 0.834 | 0.102 | 0.812 | 0.479 | 0.602 | 0.561 | 0.726 | 0.876 | 468.000 | 13.000 | 61.000 | 56.000 |
| Regla: tasa de fallos previa del workflow | 0.615 | 0.794 | 0.109 | 0.885 | 0.462 | 0.607 | 0.586 | 0.723 | 0.883 | 474.000 | 7.000 | 63.000 | 54.000 |

- Random Forest: PR-AUC 0.677 (IC 95 % bootstrap 0.589–0.761); ROC-AUC 0.835 (IC 95 % 0.787–0.881).
- Regla de historial: PR-AUC 0.615 (IC 95 % 0.531–0.701).
- Matriz de confusión (Random Forest, umbral 0.233): TN=452, FP=29, FN=44, TP=73.
- Por qué la exactitud no basta: un modelo que siempre predice 'completado' obtiene una exactitud de 0.804 y no detecta ningún fallo.

## 3. Generalización a repositorios no vistos (GroupKFold, todo el dataset)

- Random Forest: PR-AUC 0.613, ROC-AUC 0.834 (tasa base 0.158).
- Regla de historial: PR-AUC 0.573, ROC-AUC 0.821.

## 4. Ablación: sin variables de historial

- Random Forest sin historial: PR-AUC 0.309, ROC-AUC 0.652 (prueba temporal).

## 4b. Sensibilidad: sin workflows que fallan siempre

Se excluyen de la evaluación las ejecuciones de workflows cuyas ejecuciones observadas fallaron todas (configuración rota persistente). La exclusión solo se aplica a la evaluación; el indicador usa información futura y no es una variable del modelo.

| Modelo | Filas | Tasa base | PR-AUC | ROC-AUC |
|---|---:|---:|---:|---:|
| Random Forest | 551 | 0.127 | 0.359 | 0.734 |
| Regresión logística | 551 | 0.127 | 0.367 | 0.767 |
| LightGBM | 551 | 0.127 | 0.332 | 0.730 |
| Regla: tasa de fallos previa del workflow | 551 | 0.127 | 0.282 | 0.669 |

## 5. Niveles de riesgo

Definidos por riesgo relativo frente a la tasa base de entrenamiento (0.145): **bajo** si p < 0.145; **medio** si 0.145 ≤ p < 0.291 (hasta 2 veces la tasa base); **alto** si p ≥ 0.291. La validación en prueba muestra la tasa de fallos observada en cada nivel:

| Nivel | Ejecuciones | Tasa de fallos observada |
|---|---:|---:|
| bajo | 462 | 8.0 % |
| medio | 58 | 34.5 % |
| alto | 78 | 76.9 % |

## 6. Explicabilidad (SHAP, conjunto de prueba)

Media del valor SHAP absoluto (contribución a la predicción del modelo, no causalidad):

| Variable | Media de |SHAP| |
|---|---:|
| num__wf_tasa_fallo_prev | 0.0575 |
| num__wf_ultimo_fallo | 0.0535 |
| num__repo_tasa_fallo_prev | 0.0246 |
| cat__event_schedule | 0.0097 |
| num__wf_duracion_media_prev_min | 0.0092 |
| num__wf_n_prev | 0.0085 |
| num__retraso_commit_run_min | 0.0060 |
| num__missingindicator_wf_horas_desde_ultimo | 0.0050 |
| num__missingindicator_wf_duracion_media_prev_min | 0.0050 |
| num__repo_n_workflows_prev | 0.0047 |
| num__msg_len | 0.0045 |
| num__dia_semana | 0.0041 |
| num__missingindicator_wf_tasa_fallo_prev | 0.0040 |
| num__repo_n_prev | 0.0040 |
| num__missingindicator_wf_ultimo_fallo | 0.0038 |

Figuras: `figuras/curvas_evaluacion_v1_1.png`, `figuras/shap_resumen_v1_1.png`.

## 7. Limitaciones

- Dataset pequeño (pocos miles de filas) y periodo corto (jul–nov 2023): intervalos de confianza amplios.
- Historial limitado a un máximo de 5 ejecuciones por workflow en GHALogs.
- Sin métricas del cambio de código (churn); se incorporarán con la API de GitHub.
- La etiqueta mide si el intento de despliegue se completó, no incidentes en producción.
