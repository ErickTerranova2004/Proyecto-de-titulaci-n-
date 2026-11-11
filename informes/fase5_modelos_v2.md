# Fase 5. Modelo de riesgo de despliegue v2 (dataset de 198 repositorios)

- Datos: `datos_procesados/dataset_riesgo_despliegue_v2.csv` (SHA-256 `34a38c06a07c…`): 4,117 ejecuciones de 195 repositorios; y=1 401 (9.7 %).
- Etiqueta: despliegue a producción no completado (`fase2_variable_objetivo.md`, reglas 7 a 9). Precisión de etiquetas medida a mano en una muestra aleatoria (semilla 2027): 47/49 (IC 95 % Wilson 86,3–98,9 %).
- Evaluación: GroupKFold de 5 pliegues por repositorio. Modelo, calibración y umbral se ajustan solo con los pliegues de entrenamiento (GroupKFold interno de 5).
- Pesos de clase balanceados; probabilidades calibradas (sigmoide).

## 1. Resultados (predicciones fuera de pliegue)

| Modelo | PR-AUC (IC 95 %) | Recall y=1 (IC 95 %) | F1 (IC 95 %) | Brier (IC 95 %) | Precisión (IC 95 %) | ROC-AUC (IC 95 %) |
|---|---:|---:|---:|---:|---:|---:|
| Base: siempre y=0 | 0.086 (0.069–0.108) | 0.000 (0.000–0.000) | 0.000 (0.000–0.000) | 0.088 (0.070–0.109) | 0.000 (0.000–0.000) | 0.439 (0.379–0.515) |
| Regla: wf_ultimo_fallo=1 | 0.289 (0.206–0.388) | 0.521 (0.405–0.622) | 0.496 (0.383–0.593) | 0.071 (0.061–0.083) | 0.473 (0.357–0.575) | 0.717 (0.652–0.772) |
| Random Forest | 0.415 (0.308–0.518) | 0.536 (0.419–0.637) | 0.526 (0.413–0.620) | 0.067 (0.057–0.078) | 0.517 (0.403–0.612) | 0.803 (0.753–0.844) |
| XGBoost | 0.348 (0.248–0.446) | 0.459 (0.353–0.553) | 0.428 (0.323–0.520) | 0.074 (0.062–0.088) | 0.402 (0.296–0.497) | 0.758 (0.705–0.803) |

IC 95 % por bootstrap de repositorios (1.000 réplicas). La línea base predice siempre y=0 (recall y F1 = 0) con probabilidad igual a la tasa de y=1 del entrenamiento; su PR-AUC es la prevalencia.

### Variación entre pliegues (media ± desviación)

| Modelo | PR-AUC | Recall y=1 | F1 | Brier | Precisión | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Base: siempre y=0 | 0.097 ± 0.022 | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.088 ± 0.018 | 0.000 ± 0.000 | 0.500 ± 0.000 |
| Regla: wf_ultimo_fallo=1 | 0.285 ± 0.081 | 0.504 ± 0.102 | 0.481 ± 0.084 | 0.071 ± 0.009 | 0.462 ± 0.078 | 0.720 ± 0.046 |
| Random Forest | 0.416 ± 0.085 | 0.513 ± 0.138 | 0.504 ± 0.111 | 0.067 ± 0.007 | 0.499 ± 0.089 | 0.797 ± 0.049 |
| XGBoost | 0.346 ± 0.076 | 0.442 ± 0.124 | 0.410 ± 0.079 | 0.074 ± 0.010 | 0.397 ± 0.063 | 0.748 ± 0.049 |

## 2. Selección

Diferencia XGBoost − Random Forest: PR-AUC IC 95 % -0.097 a -0.031; Brier IC 95 % +0.0030 a +0.0113.

**Modelo elegido: Random Forest.** La diferencia de PR-AUC XGBoost − Random Forest es -0.068 (IC 95 % -0.097 a -0.031); como XGBoost no es mejor con claridad, se elige Random Forest (regla fijada antes de evaluar).

### Comparación con la regla simple «riesgo alto si la ejecución anterior falló»

Línea base añadida después de ver los resultados, solo como referencia (no cambia la selección): predice y=1 si `wf_ultimo_fallo=1` y usa como probabilidad la tasa de y=1 de cada grupo en los pliegues de entrenamiento (sin ejecución anterior cuenta como 0). Mismos pliegues, métricas e IC que los modelos.

- Random Forest − regla: PR-AUC **+0.126** (IC 95 % +0.072 a +0.173); Brier -0.0039 (IC 95 % -0.0068 a -0.0012; negativo = mejor Random Forest).
- Random Forest supera a la regla: el IC de la diferencia de PR-AUC no incluye 0.
- Recall de la regla 0.521 y precisión 0.473, frente a 0.536 y 0.517 de Random Forest.
- Donde la regla no puede ayudar (ejecución anterior sin fallo o sin ejecución anterior: 3,675 filas, 192 con y=1, tasa 0.052), Random Forest tiene PR-AUC 0.155 y detecta 19 de esos 192 y=1 con su umbral.

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

| Variable | Media de |SHAP| | Al aumentar la variable |
|---|---:|---:|
| num__wf_ultimo_fallo | 0.0972 | ↑ sube el riesgo |
| num__wf_tasa_fallo_prev | 0.0580 | ↑ sube el riesgo |
| num__repo_tasa_fallo_prev | 0.0461 | ↑ sube el riesgo |
| num__wf_horas_desde_ultimo | 0.0173 | ↑ sube el riesgo |
| num__wf_duracion_media_prev_min | 0.0161 | ↑ sube el riesgo |
| num__tiene_pr | 0.0153 | ↓ baja el riesgo |
| num__lineas_anadidas | 0.0148 | ↑ sube el riesgo |
| num__msg_len | 0.0148 | ↓ baja el riesgo |
| num__repo_n_workflows_prev | 0.0148 | ↓ baja el riesgo |
| num__repo_n_prev | 0.0139 | ↓ baja el riesgo |
| num__lineas_borradas | 0.0109 | ↑ sube el riesgo |
| num__msg_ci | 0.0087 | ↑ sube el riesgo |
| num__retraso_commit_run_min | 0.0084 | ↑ sube el riesgo |
| num__wf_n_prev | 0.0084 | ↓ baja el riesgo |
| num__archivos_modificados | 0.0073 | ↑ sube el riesgo |

**Cómo se presentan los factores.** Los valores SHAP describen cómo usa el modelo cada variable en una predicción: son **asociaciones aprendidas de datos históricos, no causas**. Que `tiene_pr=1` baje el riesgo no significa que abrir un pull request evite el fallo; puede reflejar equipos con revisión y CI más maduros. Igual con la actividad del repositorio (`repo_n_prev`, `repo_n_workflows_prev`), que puede funcionar como huella del repositorio. La plataforma los presenta como factores asociados y el planificador avisa de que una estimación más baja no garantiza que el despliegue salga bien.

**Efecto «sigue roto» de `wf_ultimo_fallo`.** Es la variable más importante: si la ejecución anterior del workflow falló, la tasa de y=1 es 47.3% (442 filas); si no, 5.2%. 209 de los 401 y=1 (52%) vienen justo después de un fallo. Los fallos llegan en rachas: mientras la causa (credenciales caducadas, dependencia rota, infraestructura caída) no se arregla, el siguiente intento también falla. Parte de lo que predice el modelo es, por tanto, «el workflow sigue roto», no el riesgo del cambio nuevo. Es útil (avisa de que reintentar sin arreglar la causa probablemente falle), pero es la parte más fácil de predecir; el valor añadido del modelo sobre esa señal se mide en la comparación con la regla simple (sección 2).


Figuras: `figuras/curvas_evaluacion_v2.png`, `figuras/shap_resumen_v2.png`. Detalle por pliegue: `informes/fase5_v2_pliegues.csv`.

## 5. Variables y limitaciones

- 32 variables numéricas y `event`, calculadas con la misma función en el entrenamiento y en la plataforma (`variables_desde_datos`, `backend/riesgo/services/features.py`), solo con información anterior al inicio del despliegue (`backend/riesgo/tests/test_variables_v2.py`).
- Respecto a v1.1: se quita `reejecutado_por_otro` (no se conoce antes del despliegue); `tiene_pr` y `es_reintento` se calculan igual en ambos lados; se añaden el tamaño del cambio y los checks del commit.
- **Vulnerabilidades y cobertura no se pueden obtener** con un token de solo lectura en repositorios de terceros: las alertas de seguridad exigen permisos de administración y la cobertura no la publica GitHub. Las pruebas fallidas se aproximan con los checks del commit y los bugs, solo de forma indirecta, con el mensaje del commit (`informes/fase2_variable_objetivo.md`, sección 7).
- La etiqueta mide si el intento de despliegue a producción se completó, no incidentes posteriores en producción.

## 6. Por qué el PR-AUC de v2 no es comparable con el de v1.1

El PR-AUC de v2 es más bajo que el de v1.1 (0,677 en prueba temporal; 0,613 con GroupKFold), pero **no indica un modelo peor**: miden cosas distintas.

- **Dataset distinto.** v1.1 usa GHALogs (2.392 ejecuciones de 348 repositorios, etiqueta inferida del último paso registrado, 15,8 % de y=1). v2 usa 198 repositorios con despliegues a producción validados a mano, etiquetas observadas con la API de jobs y reglas 7 a 9 (9,7 % de y=1). El PR-AUC depende de la prevalencia: la línea base vale 0,13–0,20 en v1.1 y 0,09 en v2.
- **Validación por repositorio.** La cifra principal de v1.1 viene de una partición temporal: el mismo repositorio está en entrenamiento y en prueba, y el modelo ya conoce su historial. v2 se evalúa solo con repositorios no vistos (GroupKFold anidado), que es como se usará con repositorios nuevos en la plataforma.
- **Fuga en la calibración.** En v1.1 las predicciones de validación se calibraban con `CalibratedClassifierCV(cv=5)`, con pliegues estratificados que no separaban repositorios: el calibrador veía ejecuciones de los mismos repositorios que se evaluaban. En v2 modelo, calibración y umbral se ajustan solo con los pliegues de entrenamiento, con GroupKFold interno por repositorio.
- **Información posterior al despliegue.** v1.1 usaba `reejecutado_por_otro` (solo se sabe después, si alguien reejecuta) y `tiene_pr` contaba pull requests existentes al extraer los datos, aunque se hubieran creado después de la ejecución; `es_reintento` se calculaba distinto en el entrenamiento y en la plataforma. v2 quita la primera y calcula todas con la misma función que la plataforma, solo con lo que existía antes del inicio del despliegue (`backend/riesgo/tests/test_variables_v2.py`).

Por esas tres razones las cifras de v1.1 eran optimistas; las de v2 estiman mejor el rendimiento en repositorios nuevos.

## 7. Umbrales

- **Niveles de riesgo** (los que muestra la plataforma, `predictor.nivel_de`): bajo si la probabilidad calibrada es < 0.097; medio si está entre 0.097 y 0.195; alto si es ≥ 0.195. Se fijan por **riesgo relativo** a la tasa base del entrenamiento (0.097): medio desde la tasa base y alto desde el doble. Es la misma regla de v1 y v1.1, fijada antes de entrenar; no se ajustó con los resultados. Los límites cambian con cada versión porque cambia la tasa base (v1.1: 0,145 y 0,291).
- **Umbral de clasificación** (0.330): el que maximiza F1 en las predicciones internas fuera de pliegue del entrenamiento. Solo se usa para recall, precisión y F1 de este informe; la plataforma lo guarda en los metadatos pero no lo usa.
- **Recomendación «permitir / solicitar revisión».** La plataforma no la decide con un umbral: muestra probabilidad, nivel y factores, y el líder técnico registra la decisión (autorizar, posponer o solicitar revisión). Las recomendaciones de texto salen de los factores, no de un umbral.
