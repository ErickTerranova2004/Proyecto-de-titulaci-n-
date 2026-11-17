# Evaluación en sombra: v2 frente a v1.1 y v1

Fecha: 2026-11-17. Fuente: `GET /api/modelos/comparacion-sombra/`
(`backend/riesgo/services/supervision.py`, `comparacion()`), datos de la base
de la plataforma.

## Método

- **Ejecuciones**: las 791 ejecuciones evaluables (etiqueta
  `despliegue_completado` o `despliegue_no_completado`) de la supervisión de
  v2: posteriores a su fecha de corte (2026-11-09T16:09:30Z), sin repositorios de
  demostración ni de los casos de prueba. 96 no completadas
  (tasa base 12,1 %).
- **Mismas ejecuciones y mismas variables** para los tres modelos. v1 y v1.1
  no se activaron ni consultaron GitHub: predijeron con las variables ya
  guardadas en cada predicción de v2 (`origen = "sombra"`,
  `id_prediccion_base`, comando `evaluar_sombra`). La única variable de v1 y
  v1.1 que v2 no guarda, `reejecutado_por_otro`, se rellenó con la mediana
  de entrenamiento de cada modelo (imputador de su pipeline).
- **Niveles**: cada modelo con sus propios límites de riesgo:

| Versión | Límite medio | Límite alto |
|---|---|---|
| v2 | 9,7 % | 19,5 % |
| v1.1 | 14,5 % | 29,1 % |
| v1 | 18,3 % | 36,5 % |

- **IC 95 %**: Wilson para las tasas por nivel; bootstrap pareado
  (1000 remuestreos de las mismas ejecuciones, semilla fija)
  para Brier, PR-AUC y sus diferencias.

## Resultados

Tasa de despliegues no completados por nivel (no completados / ejecuciones
del nivel) [IC 95 %], Brier (menor es mejor) y PR-AUC (mayor es mejor):

| Versión | Modelo | Nivel bajo | Nivel medio | Nivel alto | Brier [IC 95 %] | PR-AUC [IC 95 %] |
|---|---|---|---|---|---|---|
| **v2** (activo) | Random Forest | 5,9 % (40/678) [4,4 % – 7,9 %] | 28,6 % (12/42) [17,2 % – 43,6 %] | 62,0 % (44/71) [50,3 % – 72,4 %] | 0,084 [0,068 – 0,101] | 0,506 [0,410 – 0,609] |
| v1.1 (en sombra) | Random Forest | 7,2 % (51/710) [5,5 % – 9,3 %] | 41,2 % (14/34) [26,4 % – 57,8 %] | 66,0 % (31/47) [51,7 % – 77,8 %] | 0,087 [0,070 – 0,103] | 0,492 [0,397 – 0,594] |
| v1 (en sombra) | Árbol de decisión | 9,4 % (70/743) [7,5 % – 11,7 %] | 35,3 % (6/17) [17,3 % – 58,7 %] | 64,5 % (20/31) [46,9 % – 78,9 %] | 0,092 [0,075 – 0,109] | 0,412 [0,319 – 0,511] |

Diferencia con v2 sobre los mismos remuestreos (un Brier positivo y una
PR-AUC negativa significan que v2 es mejor):

| Comparación | Diferencia de Brier [IC 95 %] | Diferencia de PR-AUC [IC 95 %] |
|---|---|---|
| v1.1 − v2 | +0,0026 [−0,0018 – +0,0073] | −0,0136 [−0,0528 – +0,0291] |
| v1 − v2 | +0,0075 [+0,0025 – +0,0135] | −0,0944 [−0,1486 – −0,0429] |

## Conclusión

- **v2 supera a v1** de forma significativa en las dos métricas: los IC
  95 % de las diferencias de Brier y de PR-AUC no incluyen el 0. v2 además
  separa mejor los niveles: su nivel bajo tiene menos fallos (5,9 % frente
  a 9,4 %) y su nivel alto reúne más fallos (44 de 96 frente a 20).
- **Frente a v1.1, v2 es mejor en los valores puntuales** (Brier 0,084
  frente a 0,087; PR-AUC 0,506 frente a 0,492) y concentra más fallos en el
  nivel alto (44 frente a 31) con un nivel bajo más limpio (5,9 % frente a
  7,2 %), **pero la diferencia no es concluyente**: los IC 95 % de las
  diferencias incluyen el 0. Con 96 fallos no hay potencia suficiente para
  afirmar que v2 sea mejor que v1.1; sí que no es peor en ninguna métrica.
- La elección de v2 se apoya, además, en su validación por repositorio
  (GroupKFold, repositorios no vistos) y en el dataset v2.0, que v1.1 no
  tuvo.

## Nota

Tras este informe, v1.1 se ocultó en la plataforma (`est_registro = 'I'`,
migración 0022): ya no aparece en Modelos, Supervisión ni en la
comparación. Sus filas, sus predicciones (interactivas y en sombra) y sus
archivos (`modelos/modelo_riesgo_v1_1*`) se conservan.
