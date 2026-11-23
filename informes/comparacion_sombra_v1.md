# Evaluación en sombra: v2 frente a v1 (registro histórico)

Fecha: 2026-11-23. Fuente: `GET /api/modelos/comparacion-sombra/`
(`backend/riesgo/services/supervision.py`, `comparacion()`), datos de la base
de la plataforma. Se guarda como registro antes de retirar v1 de la
plataforma (v1 y v1.1 pasan a `est_registro = 'I'`; sus predicciones se
conservan). La comparación anterior con v1.1 está en
`informes/comparacion_sombra_v2.md` (17-nov, 791 ejecuciones).

## Método

- **Ejecuciones**: las 1.423 ejecuciones evaluables (etiqueta `despliegue_completado` o `despliegue_no_completado`) de la
  supervisión de v2: posteriores a su fecha de corte (2026-11-09T16:09:30Z),
  sin repositorios de demostración ni de los casos de prueba. 193 no completadas (tasa base 13,6 %).
- **Mismas ejecuciones y mismas variables** para los dos modelos: v1 predijo
  en sombra con las variables guardadas en cada predicción de v2 (`origen =
  "sombra"`, `id_prediccion_base`), sin activarse ni consultar GitHub.
  `reejecutado_por_otro`, que v2 no guarda, se rellenó con la mediana de
  entrenamiento de v1.
- **Niveles**: cada modelo con sus propios límites de riesgo:

| Versión | Límite medio | Límite alto |
|---|---|---|
| v2 | 9,7 % | 19,5 % |
| v1 | 18,3 % | 36,5 % |

- **IC 95 %**: Wilson para las tasas por nivel; bootstrap pareado
  (1000 remuestreos de las mismas ejecuciones, semilla fija)
  para Brier, PR-AUC y sus diferencias.

## Resultados

Tasa de despliegues no completados por nivel (no completados / ejecuciones
del nivel) [IC 95 %], Brier (menor es mejor) y PR-AUC (mayor es mejor):

| Versión | Modelo | Nivel bajo | Nivel medio | Nivel alto | Brier [IC 95 %] | PR-AUC [IC 95 %] |
|---|---|---|---|---|---|---|
| **v2** (activo) | Random Forest | 5,3 % (64/1197) [4,2 % – 6,8 %] | 30,3 % (20/66) [20,6 % – 42,2 %] | 68,1 % (109/160) [60,6 % – 74,8 %] | 0,082 [0,071 – 0,093] | 0,631 [0,556 – 0,698] |
| v1 (en sombra) | Árbol de decisión | 10,3 % (137/1333) [8,8 % – 12,0 %] | 37,5 % (12/32) [22,9 % – 54,7 %] | 75,9 % (44/58) [63,5 % – 85,0 %] | 0,095 [0,083 – 0,107] | 0,525 [0,448 – 0,597] |

Diferencia v1 − v2 (mismos remuestreos) [IC 95 %]:

- Brier: +0,0125 [+0,0077 – +0,0171] (positiva = v1 peor calibrado).
- PR-AUC: −0,106 [−0,145 – −0,065] (negativa = v1 ordena peor el riesgo).

## Conclusión

Con 1.423 ejecuciones reales posteriores al corte, v2 supera a v1 de forma
significativa en Brier y en PR-AUC: ningún IC de la diferencia incluye el 0.
v2 concentra más fallos en el nivel alto (109 frente a 44) y deja menos en el nivel bajo
(5,3 % frente a 10,3 %). Desde el 23-nov la comparación de la plataforma es
Random Forest (v2) frente a XGBoost entrenado con el mismo dataset v2.
