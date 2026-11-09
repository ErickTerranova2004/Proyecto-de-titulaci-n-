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
- **Excluidas:** ejecuciones exitosas sin paso de despliegue (no hubo intento), fallos en otro job con el despliegue completado (ambiguas), ejecuciones `cancelled`, `skipped` o `action_required`, y ejecuciones que terminaron **sin ningún job** (`startup_failure`, YAML inválido, permisos del workflow…): no llegaron a arrancar, así que no son un intento de despliegue y no cuentan como y = 1. *(Añadido el 2026-11-08 al construir el dataset de repositorios reales; ver `informes/informe_filtrado_repos_reales.md`.)*
- **Solo entornos de producción:** también se excluyen las ejecuciones cuyo despliegue va a un entorno no productivo (staging, dev, test, QA, preview, demo, beta, sandbox, nightly…). Si el workflow despliega a staging y a producción, solo cuenta el despliegue a producción. Un repositorio cuyo workflow no despliega nunca a producción queda fuera del dataset (criterio 2). En la plataforma el entorno se reconoce por el nombre del job o del paso; si el workflow falla antes de cualquier despliegue no se puede saber a qué entorno iba. En el dataset ese caso se resuelve por la rama: solo cuentan las ramas desde las que hubo algún despliegue completado a producción. *(Añadido el 2026-11-08.)*
- **Ejecuciones manuales con entorno indeterminado:** se excluyen las ejecuciones `workflow_dispatch` cuyo entorno de destino no se puede determinar. Son las de un workflow cuyo `workflow_dispatch` tiene un input que elige el entorno (de tipo `environment`, o con nombre como `environment`, `env`, `stage` o `target` y valor libre u opciones no productivas) y en el que ningún job declara un entorno literal ni lo indica en su nombre. También se excluyen las ejecuciones manuales que fallan antes de desplegar cuando un input decide el entorno o si se despliega a producción (p. ej. `deploy_production: true/false`), porque no se sabe si el intento iba a producción. La etiqueta es `excluida_entorno_indeterminado`. Caso de origen: `dimagi/open-chat-studio`, donde la ejecución manual puede elegir `dev` o `prod`. *(Añadido el 2026-11-09 por decisión del autor.)*
- **Entorno resuelto en tiempo de ejecución (regla 7 del dataset):** muchos workflows deciden el entorno al ejecutarse: por la rama (`main` → staging, `production` → prod), por ser o no una *prerelease*, o con la salida de otro job. En el dataset el entorno real se obtiene, por este orden: (1) del entorno que GitHub registró para el job (API de Deployments); (2) de las expresiones `${{ }}` del workflow evaluadas con la rama y el evento de la ejecución; (3) del nombre o el archivo del workflow («Deploy Staging», `deploy-test.yaml`); y (4) de la rama, si su nombre es no productivo (`dev`, `develop`, `staging`, `preprod`…; las excepciones revisadas a mano se documentan en el informe). Además, la regla de la rama del punto anterior se aplica a **todos** los repositorios, así que un fallo antes del despliegue en una rama sin despliegues completados a producción (por ejemplo, la rama de un pull request) no cuenta como y = 1. Esta regla solo restringe: nunca convierte en producción una ejecución que antes no lo era. *(Añadido el 2026-11-09, a raíz de la muestra de validación final de 50 ejecuciones.)*
- **Hosting estático:** publicar archivos estáticos (Cloudflare Pages, Netlify, GitHub Pages, sitio web en S3, Firebase Hosting, Azure Static Web Apps…) no es desplegar una aplicación y no cuenta como despliegue. Si en el workflow también se despliega un backend, cuenta solo ese despliegue; un repositorio que solo publica en hosting estático queda fuera del dataset (criterio 2). *(Añadido el 2026-11-08.)*

## 5. Cambio de alcance (declaración explícita)

El objetivo original era predecir el **fallo real del despliegue**. Con los datos disponibles **no hay evidencia suficiente** para entrenar un modelo con esa etiqueta. La tesis predice en su lugar el **riesgo de que un intento de despliegue no se complete con éxito** en su pipeline de GitHub Actions. Esta etiqueta:
- sí es observable con exactitud;
- incluye fallos de compilación y pruebas dentro del pipeline de despliegue, que también impiden el despliegue;
- **no** mide incidentes en producción posteriores al despliegue.

Las conclusiones de la tesis deben limitarse a este alcance. La estrategia A queda como validación cualitativa. En la plataforma, la API de jobs de GitHub (verificada con ejecuciones de 2026) permite registrar el resultado exacto del paso de despliegue para refinar la etiqueta en el futuro.

## 6. Aplicación de la regla a ejecuciones reales en la plataforma

Al verificar una predicción (`POST /api/predicciones/{id}/verificar/`), la plataforma aplica esta misma regla a la ejecución real. Usa el resultado **exacto de cada paso** que da la API de jobs de GitHub (`backend/riesgo/services/etiquetado.py`). Un paso es de despliegue a producción según estas señales, por orden de prioridad:
1. **El job no está omitido** (`skipped`): sus pasos no cuentan.
2. **Entorno del job:** si el job declara `environment`, ese entorno decide si es producción. Si no lo declara, se usan los nombres del job y del paso, y no deben coincidir con `PATRON_NO_PRODUCCION` (staging, dev, test, preview, demo, beta…).
3. **Acción o comando de despliegue conocido** en el `uses` o el `run` del paso: `deploy-cloudrun`, `amazon-ecs-deploy-task-definition`, `webapps-deploy`, `gcloud run deploy`, `sam deploy`, `helm upgrade`, etc. Se descartan las variantes `--dry-run` y `plan`.
4. **Nombre del paso:** debe contener un verbo de despliegue (`Workflow.patron_paso_despliegue`) y no ser un paso auxiliar (dry-run, versión, URL, instalación, setup, status, matriz de despliegue…).

Tampoco cuentan las variantes que no despliegan: `--dry-run`, `plan` y `ansible-playbook --syntax-check` o `--check`. `PATRON_NO_PRODUCCION` reconoce además `preprod`, `nonprod`, `acceptance`, `pull_request`, los sufijos camelCase (`reserveRecAdminTest`) y los entornos de una sola sigla (`at`, `acc`, `tst`). Si falla un job que declara un entorno no productivo (por ejemplo, «Deploy Dev» con `environment: DEV`), la ejecución se excluye como no productiva y no cuenta como y = 1. *(Regla 7, 2026-11-09.)*

En todos los casos, los pasos de hosting estático no cuentan. Se reconocen por el paso (nombre, `uses` o `run`) o por el nombre del job, como en un job «Deploy to Cloudflare Pages» cuyo paso «Deploy» usa `wrangler-action`. *(Ajuste del 2026-11-09, a raíz de la segunda muestra de 30 ejecuciones y=0.)*

La API de jobs de GitHub no devuelve el `environment` del job ni el `uses`/`run` de cada paso. El script del dataset los toma del YAML del workflow; la plataforma, por ahora, solo dispone de los nombres.

| `etiqueta` | `subtipo_etiqueta` | y | Condición |
|---|---|:-:|---|
| `despliegue_completado` | — | 0 | Workflow `success` y algún paso de despliegue en `success` |
| `despliegue_no_completado` | `antes_del_despliegue` | 1 | Workflow `failure` sin ningún paso de despliegue en `success` |
| `despliegue_no_completado` | `en_paso_de_despliegue` | 1 | El paso que falló es un paso de despliegue |
| `despliegue_no_completado` | `posterior_mismo_job` | 1 | Falló un paso posterior a un despliegue exitoso del mismo job |
| `excluida_ambigua` | — | — | Falló otro job y el despliegue terminó bien (caso novu) |
| `excluida_sin_intento` | — | — | Workflow `success` sin paso de despliegue en `success` |
| `excluida_otro_resultado` | — | — | `cancelled`, `skipped`, `action_required`… |
| `excluida_sin_jobs` | — | — | Workflow `failure` sin ningún job: no llegó a arrancar (`startup_failure`, YAML inválido…) |
| `excluida_no_produccion` | — | — | Solo se desplegó, o falló el despliegue, en un entorno no productivo (job o paso con staging, dev, test, preview, demo, beta…), o falló un job con un entorno no productivo |
| `excluida_entorno_indeterminado` | — | — | Solo en el dataset: ejecución manual (`workflow_dispatch`) cuyo entorno de destino no se puede determinar (ver sección 4) |

La etiqueta se llama **"despliegue no completado"**, nunca "fallo real de despliegue". Solo el subtipo `en_paso_de_despliegue` aporta evidencia directa de un fallo *durante* el despliegue. Guardar ese subtipo es lo que permitirá, con el tiempo, construir la etiqueta de fallo real que hoy no existe en los datos públicos.

Diferencia con el entrenamiento: en GHALogs el paso fallido se **infería** (último paso registrado). En la plataforma se **observa** con la API de jobs. Por eso las etiquetas de la plataforma son más precisas que las del dataset de entrenamiento.
