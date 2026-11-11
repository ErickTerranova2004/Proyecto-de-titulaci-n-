# Fase 5. Modelo de riesgo de despliegue v2 (dataset de 198 repositorios)

- Datos: `datos_procesados/dataset_riesgo_despliegue_v2.csv` (SHA-256 `34a38c06a07c…`): 4,117 ejecuciones de 195 repositorios; y=1 401 (9.7 %).
- Etiqueta: despliegue a producción no completado (`fase2_variable_objetivo.md`, reglas 7 a 9). Precisión de etiquetas medida a mano en una muestra aleatoria (semilla 2027): 47/49 (IC 95 % Wilson 86,3–98,9 %).
- Evaluación: GroupKFold de 5 pliegues por repositorio. Modelo, calibración y umbral se ajustan solo con los pliegues de entrenamiento (GroupKFold interno de 5).
- Pesos de clase balanceados; probabilidades calibradas (sigmoide).

## 1. Resultados (predicciones fuera de pliegue)

| Modelo | PR-AUC (IC 95 %) | Recall y=1 (IC 95 %) | F1 (IC 95 %) | Brier (IC 95 %) | Precisión (IC 95 %) | ROC-AUC (IC 95 %) |
|---|---:|---:|---:|---:|---:|---:|
| Base: siempre y=0 | 0.086 (0.069–0.108) | 0.000 (0.000–0.000) | 0.000 (0.000–0.000) | 0.088 (0.070–0.109) | 0.000 (0.000–0.000) | 0.439 (0.379–0.515) |
| Random Forest | 0.415 (0.308–0.518) | 0.536 (0.419–0.637) | 0.526 (0.413–0.620) | 0.067 (0.057–0.078) | 0.517 (0.403–0.612) | 0.803 (0.753–0.844) |
| XGBoost | 0.348 (0.248–0.446) | 0.459 (0.353–0.553) | 0.428 (0.323–0.520) | 0.074 (0.062–0.088) | 0.402 (0.296–0.497) | 0.758 (0.705–0.803) |

IC 95 % por bootstrap de repositorios (1.000 réplicas). La línea base predice siempre y=0 (recall y F1 = 0) con probabilidad igual a la tasa de y=1 del entrenamiento; su PR-AUC es la prevalencia.

### Variación entre pliegues (media ± desviación)

| Modelo | PR-AUC | Recall y=1 | F1 | Brier | Precisión | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Base: siempre y=0 | 0.097 ± 0.022 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.088 ± 0.018 | 0.000 ± 0.000 | 0.500 ± 0.000 |
| Random Forest | 0.416 ± 0.085 | 0.513 ± 0.138 | 0.504 ± 0.111 | 0.067 ± 0.007 | 0.499 ± 0.089 | 0.797 ± 0.049 |
| XGBoost | 0.346 ± 0.076 | 0.442 ± 0.124 | 0.410 ± 0.079 | 0.074 ± 0.010 | 0.397 ± 0.063 | 0.748 ± 0.049 |

## 2. Selección

Diferencia XGBoost − Random Forest: PR-AUC IC 95 % -0.097 a -0.031; Brier IC 95 % +0.0030 a +0.0113.

**Modelo elegido: Random Forest.** La diferencia de PR-AUC XGBoost − Random Forest es -0.068 (IC 95 % -0.097 a -0.031); como XGBoost no es mejor con claridad, se elige Random Forest (regla fijada antes de evaluar).

## 3. Modelo final

Entrenado con todo el dataset. Umbral F1 (fuera de pliegue): 0.330. Niveles de riesgo por riesgo relativo a la tasa base (0.097): bajo < 0.097 ≤ medio < 0.195 ≤ alto.

Tasa de y=1 observada por nivel (predicciones fuera de pliegue del modelo elegido):

| Nivel | Ejecuciones | Tasa de y=1 |
|---|---:|---:|
| bajo | 3251 | 4.3 % |
| medio | 378 | 9.5 % |
| alto | 488 | 46.1 % |

## 4. Explicabilidad (SHAP del modelo final)

TreeExplainer exacto sobre el modelo base. Escala de los valores: probabilidad (del modelo con pesos balanceados, antes de calibrar). La calibración sigmoide es monótona: no cambia el signo ni el orden de las contribuciones. Media del valor SHAP absoluto (asociación aprendida, no causalidad):

| Variable | Media de |SHAP| |
|---|---:|
| num__wf_ultimo_fallo | 0.0972 |
| num__wf_tasa_fallo_prev | 0.0580 |
| num__repo_tasa_fallo_prev | 0.0461 |
| num__wf_horas_desde_ultimo | 0.0173 |
| num__wf_duracion_media_prev_min | 0.0161 |
| num__tiene_pr | 0.0153 |
| num__lineas_anadidas | 0.0148 |
| num__msg_len | 0.0148 |
| num__repo_n_workflows_prev | 0.0148 |
| num__repo_n_prev | 0.0139 |
| num__lineas_borradas | 0.0109 |
| num__msg_ci | 0.0087 |
| num__retraso_commit_run_min | 0.0084 |
| num__wf_n_prev | 0.0084 |
| num__archivos_modificados | 0.0073 |

Figuras: `figuras/curvas_evaluacion_v2.png`, `figuras/shap_resumen_v2.png`. Detalle por pliegue: `informes/fase5_v2_pliegues.csv`.

## 5. Variables y limitaciones

- 32 variables numéricas y `event`, calculadas con la misma función en el entrenamiento y en la plataforma (`variables_desde_datos`, `backend/riesgo/services/features.py`), solo con información anterior al inicio del despliegue (`backend/riesgo/tests/test_variables_v2.py`).
- Respecto a v1.1: se quita `reejecutado_por_otro` (no se conoce antes del despliegue); `tiene_pr` y `es_reintento` se calculan igual en ambos lados; se añaden el tamaño del cambio y los checks del commit.
- **Vulnerabilidades y cobertura no se pueden obtener** con un token de solo lectura en repositorios de terceros: las alertas de seguridad exigen permisos de administración y la cobertura no la publica GitHub. Las pruebas fallidas se aproximan con los checks del commit y los bugs, solo de forma indirecta, con el mensaje del commit (`informes/fase2_variable_objetivo.md`, sección 7).
- La etiqueta mide si el intento de despliegue a producción se completó, no incidentes posteriores en producción.
