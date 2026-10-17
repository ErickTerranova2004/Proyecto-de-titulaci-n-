# Fase 5. Modelos de riesgo de despliegue

- Datos: `datos_procesados/dataset_riesgo_despliegue.csv` | entrenamiento: 2,118 filas (18.3 % positivos) | prueba temporal: 707 filas (23.5 % positivos).
- Etiqueta: despliegue no completado (ver `fase2_variable_objetivo.md`).
- Todas las probabilidades están calibradas (sigmoide, validación agrupada por repositorio).

## 1. Selección del modelo (solo entrenamiento, validación cruzada agrupada por repositorio)

| Modelo | PR-AUC | ROC-AUC | Brier |
|---|---:|---:|---:|
| Base: tasa de fallos (Dummy) | 0.160 | 0.418 | 0.151 |
| Regresión logística | 0.581 | 0.836 | 0.103 |
| Árbol de decisión | 0.598 | 0.814 | 0.103 |
| Random Forest | 0.584 | 0.830 | 0.101 |
| LightGBM | 0.569 | 0.811 | 0.109 |
| Regla: tasa de fallos previa del workflow | 0.559 | 0.820 | 0.113 |

**Seleccionado por PR-AUC: Árbol de decisión.** La selección se hizo sin usar el conjunto de prueba. Las diferencias de PR-AUC entre regresión logística, árbol, Random Forest y LightGBM en esta validación son pequeñas frente a la variabilidad esperable con este tamaño de muestra; el modelo seleccionado no se cambia tras ver los resultados de prueba para evitar sesgo de selección. (El ROC-AUC del Dummy difiere de 0,5 porque cada pliegue predice una constante distinta.)

## 2. Evaluación en la partición temporal de prueba

El umbral de clasificación se eligió maximizando F1 en las predicciones fuera de pliegue del entrenamiento.

| Modelo | PR-AUC | ROC-AUC | Brier | Precision | Recall | F1 | MCC | Balanced acc. | Accuracy | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Base: tasa de fallos (Dummy) | 0.235 | 0.500 | 0.182 | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 | 0.765 | 541.000 | 0.000 | 166.000 | 0.000 |
| Regresión logística | 0.738 | 0.868 | 0.115 | 0.700 | 0.590 | 0.641 | 0.545 | 0.756 | 0.844 | 499.000 | 42.000 | 68.000 | 98.000 |
| Árbol de decisión | 0.687 | 0.840 | 0.129 | 0.738 | 0.458 | 0.565 | 0.490 | 0.704 | 0.835 | 514.000 | 27.000 | 90.000 | 76.000 |
| Random Forest | 0.733 | 0.852 | 0.114 | 0.648 | 0.711 | 0.678 | 0.574 | 0.796 | 0.842 | 477.000 | 64.000 | 48.000 | 118.000 |
| LightGBM | 0.743 | 0.856 | 0.113 | 0.771 | 0.548 | 0.641 | 0.566 | 0.749 | 0.856 | 514.000 | 27.000 | 75.000 | 91.000 |
| Regla: tasa de fallos previa del workflow | 0.596 | 0.773 | 0.136 | 0.798 | 0.404 | 0.536 | 0.488 | 0.686 | 0.836 | 524.000 | 17.000 | 99.000 | 67.000 |

- Árbol de decisión: PR-AUC 0.687 (IC 95 % bootstrap 0.618–0.746); ROC-AUC 0.840 (IC 95 % 0.800–0.874).
- Regla de historial: PR-AUC 0.596 (IC 95 % 0.520–0.668).
- Matriz de confusión (Árbol de decisión, umbral 0.239): TN=514, FP=27, FN=90, TP=76.
- Por qué la exactitud no basta: un modelo que siempre predice 'completado' obtiene una exactitud de 0.765 y no detecta ningún fallo.

## 3. Generalización a repositorios no vistos (GroupKFold, todo el dataset)

- Árbol de decisión: PR-AUC 0.639, ROC-AUC 0.834 (tasa base 0.196).
- Regla de historial: PR-AUC 0.567, ROC-AUC 0.805.

## 4. Ablación: sin variables de historial

- Árbol de decisión sin historial: PR-AUC 0.526, ROC-AUC 0.705 (prueba temporal).

## 4b. Sensibilidad: sin workflows que fallan siempre

Se excluyen de la evaluación las ejecuciones de workflows cuyas ejecuciones observadas fallaron todas (configuración rota persistente). La exclusión solo se aplica a la evaluación; el indicador usa información futura y no es una variable del modelo.

| Modelo | Filas | Tasa base | PR-AUC | ROC-AUC |
|---|---:|---:|---:|---:|
| Árbol de decisión | 655 | 0.174 | 0.440 | 0.778 |
| Regresión logística | 655 | 0.174 | 0.530 | 0.815 |
| Random Forest | 655 | 0.174 | 0.511 | 0.793 |
| LightGBM | 655 | 0.174 | 0.541 | 0.798 |
| Regla: tasa de fallos previa del workflow | 655 | 0.174 | 0.361 | 0.684 |

## 5. Niveles de riesgo

Definidos por riesgo relativo frente a la tasa base de entrenamiento (0.183): **bajo** si p < 0.183; **medio** si 0.183 ≤ p < 0.365 (hasta 2 veces la tasa base); **alto** si p ≥ 0.365. La validación en prueba muestra la tasa de fallos observada en cada nivel:

| Nivel | Ejecuciones | Tasa de fallos observada |
|---|---:|---:|
| bajo | 536 | 11.4 % |
| medio | 97 | 46.4 % |
| alto | 74 | 81.1 % |

## 6. Explicabilidad (SHAP, conjunto de prueba)

Media del valor SHAP absoluto (contribución a la predicción del modelo, no causalidad):

| Variable | Media de |SHAP| |
|---|---:|
| num__wf_tasa_fallo_prev | 0.1232 |
| num__repo_tasa_fallo_prev | 0.0408 |
| num__missingindicator_wf_horas_desde_ultimo | 0.0260 |
| num__wf_n_prev | 0.0145 |
| num__wf_ultimo_fallo | 0.0100 |
| num__wf_horas_desde_ultimo | 0.0082 |
| num__retraso_commit_run_min | 0.0075 |
| num__rama_principal | 0.0043 |
| num__wf_duracion_media_prev_min | 0.0035 |
| num__msg_fix | 0.0000 |
| num__msg_feat | 0.0000 |
| num__msg_merge | 0.0000 |
| num__msg_lineas | 0.0000 |
| num__msg_len | 0.0000 |
| num__msg_revert | 0.0000 |

Figuras: `figuras/curvas_evaluacion.png`, `figuras/shap_resumen.png`.

## 7. Limitaciones

- Dataset pequeño (pocos miles de filas) y periodo corto (jul–nov 2023): intervalos de confianza amplios.
- Historial limitado a un máximo de 5 ejecuciones por workflow en GHALogs.
- Sin métricas del cambio de código (churn); se incorporarán con la API de GitHub.
- La etiqueta mide si el intento de despliegue se completó, no incidentes en producción.
