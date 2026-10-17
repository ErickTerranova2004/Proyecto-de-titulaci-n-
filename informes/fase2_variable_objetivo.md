# Fase 2. Definición de la variable objetivo

Fecha: 2026-10-15. Evidencia: `informes/informe_niveles_despliegue.md`,
`informes/runs_*.md`, `deploy_runs_niveles.csv`.

## 1. Tipos de fallo y evidencia necesaria

| Tipo de fallo | Qué significa | Evidencia necesaria | ¿Observable en los datos? |
|---|---|---|---|
| Fallo de pruebas | Una prueba automatizada no pasa | Resultado del paso de pruebas | Solo en parte: GHALogs registra los pasos ejecutados, pero no su resultado |
| Fallo de compilación | El código o la imagen no se construyen | Resultado del paso de build | Solo en parte (igual que el anterior) |
| Fallo de publicación de artefacto | No se sube el paquete o la imagen | Resultado del paso de push/publish | Solo en parte |
| Fallo de ejecución de workflow | `conclusion = failure` del workflow completo | `metadata.conclusion` | **Sí, exacto** (GHALogs y GADFPD) |
| Fallo real durante el despliegue | El paso que actualiza el entorno falla o no se estabiliza | Resultado del paso de despliegue o log completo | **Solo inferido**: 169 casos, 6 con evidencia alta |
| Incidente posterior al despliegue | La aplicación desplegada falla en producción | Monitorización, incidentes, *rollbacks* | **No**: ningún dataset lo contiene |

## 2. Hallazgos que obligan a no usar `conclusion = failure` como etiqueta de despliegue

- `stratospheric-dev/stratospheric`: 5 de 5 ejecuciones `failure` por fallos de compilación; el despliegue nunca se ejecutó.
- `novuhq/novu` (producción): 5 de 5 ejecuciones `failure`, aunque el despliegue a producción en la UE y en EE. UU. terminó bien. El fallo venía de un job de pruebas E2E mal configurado.
- `elastic/elasticsearch` docs-deploy (GADFPD, API de jobs): `failure` por `vale-report` (revisión de estilo), con `deploy-preview` en `success`.
- `chainsafe/gossamer` (staging, ECS): 4 fallos en los que el despliegue duró unos 31 minutos, frente a 3 minutos en el éxito (espera de estabilidad agotada). Es un **fallo real de despliegue**.

## 3. Estrategias de etiquetado comparadas

| Estrategia | Positivos disponibles | Fiabilidad de la etiqueta | Alineación con el tema | Decisión |
|---|---:|---|---|---|
| A. Fallo real dentro del paso de despliegue | 169 (105 de workflows que fallan siempre; 6 con evidencia alta) | Baja-media (inferida) | Máxima | **Insuficiente para entrenar.** Se usa como análisis de casos |
| B. Intento de despliegue no completado en workflows verificados de despliegue a aplicaciones | ~600 | Alta para "no completado" | Alta: mide si el despliegue llegó a completarse | **Recomendada** |
| C. Fallo de cualquier workflow de CI (GHALogs/GADFPD) | 91.163 / 8.671 | Alta | Baja: predice fallos de CI, no de despliegue | Descartada como objetivo principal |
| D. Incidentes posteriores al despliegue | 0 | — | Máxima | Imposible con los datos disponibles |

## 4. Definición adoptada (estrategia B)

**Unidad:** un intento de ejecución (`run_id` + `run_attempt`) de un workflow que, según `log_insights`, ejecuta pasos reales de despliegue a un entorno de aplicación. Se excluyen GitHub Pages, los clústeres efímeros de prueba (kind, minikube, k3d, localstack) y las vistas previas de pull requests.

**Variable objetivo `y` (despliegue no completado):**
- `y = 0`: el paso de despliegue se ejecutó y el workflow terminó en `success`.
- `y = 1`: el intento no se completó. El workflow falló antes de llegar al despliegue (compilación o pruebas del pipeline), durante el despliegue o en un paso posterior del mismo job.
- **Excluidas:** ejecuciones exitosas sin paso de despliegue (no hubo intento), fallos en otro job con el despliegue completado (ambiguas), y ejecuciones `cancelled`, `skipped` o `action_required`.

## 5. Cambio de alcance (declaración explícita)

El objetivo original era predecir el **fallo real del despliegue**. Con los datos disponibles **no hay evidencia suficiente** para entrenar un modelo con esa etiqueta. La tesis predice en su lugar el **riesgo de que un intento de despliegue no se complete con éxito** en su pipeline de GitHub Actions. Esta etiqueta:
- sí es observable con exactitud;
- incluye fallos de compilación y pruebas dentro del pipeline de despliegue, que también impiden el despliegue;
- **no** mide incidentes en producción posteriores al despliegue.

Las conclusiones de la tesis deben limitarse a este alcance. La estrategia A queda como validación cualitativa. En la plataforma, la API de jobs de GitHub (verificada con ejecuciones de 2026) permite registrar el resultado exacto del paso de despliegue para refinar la etiqueta en el futuro.

## 6. Aplicación de la regla a ejecuciones reales en la plataforma

Al verificar una predicción (`POST /api/predicciones/{id}/verificar/`), la plataforma aplica esta misma regla a la ejecución real. Usa el resultado **exacto de cada paso** que da la API de jobs de GitHub (`backend/riesgo/services/etiquetado.py`). Un paso se considera de despliegue si su nombre coincide con `Workflow.patron_paso_despliegue`.

| `etiqueta` | `subtipo_etiqueta` | y | Condición |
|---|---|:-:|---|
| `despliegue_completado` | — | 0 | Workflow `success` y algún paso de despliegue en `success` |
| `despliegue_no_completado` | `antes_del_despliegue` | 1 | Workflow `failure` sin ningún paso de despliegue en `success` |
| `despliegue_no_completado` | `en_paso_de_despliegue` | 1 | El paso que falló es un paso de despliegue |
| `despliegue_no_completado` | `posterior_mismo_job` | 1 | Falló un paso posterior a un despliegue exitoso del mismo job |
| `excluida_ambigua` | — | — | Falló otro job y el despliegue terminó bien (caso novu) |
| `excluida_sin_intento` | — | — | Workflow `success` sin paso de despliegue en `success` |
| `excluida_otro_resultado` | — | — | `cancelled`, `skipped`, `action_required`… |

La etiqueta se llama **"despliegue no completado"**, nunca "fallo real de despliegue". Solo el subtipo `en_paso_de_despliegue` aporta evidencia directa de un fallo *durante* el despliegue. Guardar ese subtipo es lo que permitirá, con el tiempo, construir la etiqueta de fallo real que hoy no existe en los datos públicos.

Diferencia con el entrenamiento: en GHALogs el paso fallido se **infería** (último paso registrado). En la plataforma se **observa** con la API de jobs. Por eso las etiquetas de la plataforma son más precisas que las del dataset de entrenamiento.
