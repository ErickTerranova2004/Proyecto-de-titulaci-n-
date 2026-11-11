# Filtrado de repositorios reales con despliegues reales

Generado el 2026-11-11 por [`scripts/filtrar_repos_reales.py`](../scripts/filtrar_repos_reales.py) con la API de GitHub (solo lectura). **No se ha cargado nada en la plataforma ni en su base de datos.**

**No se alcanza el mínimo de 200: 198 repositorios válidos** (meta 250, mínimo 200).

## Totales

- Repositorios: 198
- Ejecuciones terminadas en los últimos 6 meses (desde 2026-05-11): 27753
- **Antes del tope** (hasta 100 ejecuciones más recientes por repositorio, regla de la fase 2; criterio 2): 5970 → y=0 (completado) 5298 (88.7 %) · y=1 (no completado) 672 (11.3 %). Excluidas por la regla: 7384.
- **Dataset final, tope de 50 ejecuciones más recientes por repositorio** (para que ningún repo domine una clase): 4123 → y=0 (completado) 3722 (90.3 %) · y=1 (no completado) 401 (9.7 %). Excluidas por la regla: 4070.
- Repositorios con ambas clases en el dataset final: 102; con 10 o más ejecuciones etiquetadas: 146.
- Ejecuciones excluidas por no tener ningún job (no llegaron a arrancar; no son un intento de despliegue): 116 antes del tope y 75 con el tope, en 15 repositorios (número de jobs verificado en 198 de 198 repositorios). Las proporciones anteriores ya las descuentan.
- Repositorios marcados como atípicos: 97 (ver sección «Atípicos»).
- **Dataset de entrenamiento** (repositorios excluidos del entrenamiento: 1): 197 repositorios; 4123 → y=0 (completado) 3722 (90.3 %) · y=1 (no completado) 401 (9.7 %).

## Ejecuciones excluidas por no tener ningún job

Según `informes/fase2_variable_objetivo.md` (sección 4, «Excluidas»), una ejecución que termina sin ningún job (startup_failure, YAML inválido, permisos del workflow...) no es un intento de despliegue: no cuenta como y=1 y se excluye del dataset.

| Repositorio | Excluidas (historial) | Excluidas (tope de 50) |
|---|---:|---:|
| cultpodcasts/RedditPodcastPoster | 74 | 50 |
| Vacademy-io/vacademy_edtech_platform | 7 | 0 |
| kusitms-com/api.kusitms.com | 7 | 7 |
| MickaelFontes/noplp-stats | 6 | 6 |
| contrapunk-audio/contrapunk | 4 | 0 |
| ConservationInternational/resilienceatlas | 4 | 4 |
| opensafely/open-pathology | 3 | 3 |
| ReseauEntourage/entourage-ror | 2 | 0 |
| burningmantech/ranger-ims-go | 2 | 0 |
| OWASP/threat-dragon | 2 | 2 |
| noi-techpark/opendatahub-timeseries-api | 1 | 1 |
| pcraig3/hols | 1 | 1 |
| italia/graph-italia | 1 | 1 |
| google/neuroglancer | 1 | 0 |
| redhat-openshift-ecosystem/pullsar | 1 | 0 |

## Criterios aplicados

1. **Aplicación real en uso** (revisión manual de descripción, topics, README, web, contribuidores e historial): se excluyen tutoriales, cursos, tareas, plantillas, demos, proyectos de práctica o portafolio, sandbox y proyectos de tesis o académicos (toda la organización Tesis-2026).
2. **Despliegue real** según `informes/fase2_variable_objetivo.md`: el workflow tiene un paso que despliega a un entorno de aplicación y ese paso se ejecutó al menos una vez (API de jobs). Se excluyen GitHub Pages, clústeres efímeros (kind, minikube, k3d, localstack), workflows que solo despliegan previews de pull requests y repos donde el paso nunca se ejecutó.
3. **Actividad genuina**: al menos 20 commits y 60 días de historial; se excluyen workflows con más de la mitad de ejecuciones programadas o repetidas sobre el mismo commit y repos con más del 80 % de commits automáticos.
4. **Diversidad**: máximo 5 repositorios por organización o autor y ninguna plataforma (proveedor) por encima del 30 % del total.
5. **Volumen**: al menos 10 ejecuciones terminadas en 6 meses; se priorizan los repos con ambas clases (y=0 e y=1) y con 10 o más ejecuciones etiquetadas.
- Se omiten los repositorios ya registrados en la plataforma o del dataset de entrenamiento anterior (GHALogs), para que el conjunto sea nuevo.

## Estrategia de búsqueda y tasa de válidos por lote

- **Estrategia 1 (lotes 1 a 7).** Búsqueda de código de 33 acciones o comandos de despliegue (Cloud Run, App Engine, ECS, Lambda, Azure, Kubernetes, Fly.io, Railway, Render, Heroku, Vercel, Cloudflare, servidores propios…), perfilado alternando plataformas y revisión manual priorizada por señales de uso real. La tasa bajó en los lotes que vinieron de páginas profundas de las búsquedas y de plataformas como Railway y Render, donde predominan proyectos personales, de portafolio o de cursos.
- **Estrategia 2 (desde el lote 8).** Solo acciones de despliegue a producción (amazon-ecs-deploy-task-definition, deploy-cloudrun, azure/webapps-deploy, azure/k8s-deploy, `helm upgrade`, appleboy/ssh-action y Ansible), buscadas también junto a «production» y «environment»; Railway y Render se dejan de buscar. **Prefiltro antes de perfilar** (API GraphQL, sin gastar cuota de perfilado): dueño de tipo Organization, más de 365 días entre la creación y el último push y al menos 3 contribuidores. Se perfilan primero los repositorios con más deployments registrados en entornos de producción (API de Deployments). Así entran sistemas de gobiernos, universidades, ONG y empresas, con el máximo de 5 por organización. La revisión manual (criterio 1) se mantiene igual.
- La revisión salta perfiles de plataformas que ya alcanzaron el 30 % del mínimo de 200 y de organizaciones con 5 aprobados, y empieza por las plataformas con menos repositorios.

| Lote | Estrategia | Válidos / revisados | Tasa | Origen principal |
|---:|---|---:|---:|---|
| 1 | 1 | 27 / 50 | 54 % | búsquedas anteriores (50) |
| 2 | 1 | 18 / 50 | 36 % | Google Cloud (23), búsquedas anteriores (20), AWS (7) |
| 3 | 1 | 6 / 50 | 12 % | Google Cloud (39), AWS (11) |
| 4 | 1 | 14 / 50 | 28 % | Servidor propio (14), Cloudflare (11), Kubernetes (5) |
| 5 | 1 | 19 / 50 | 38 % | Servidor propio (8), Cloudflare (6), Fly.io (5) |
| 6 | 1 | 16 / 50 | 32 % | Cloudflare (17), Servidor propio (11), Kubernetes (5) |
| 7 | 1 | 9 / 50 | 18 % | Railway (13), Render (11), Fly.io (10) |
| 8 | 2 | 33 / 50 | 66 % | Servidor propio (12), Kubernetes (10), AWS (10) |
| 9 | 2 | 36 / 50 | 72 % | AWS (18), Servidor propio (10), Kubernetes (7) |
| 10 | 2 | 28 / 50 | 56 % | AWS (20), Servidor propio (14), Google Cloud (8) |
| 11 | 2 | 14 / 50 | 28 % | Servidor propio (35), Cloudflare (6), Azure (3) |
| 12 | 2 | 29 / 48 | 60 % | Kubernetes (24), AWS (14), Servidor propio (6) |
| 13 | 2 | 24 / 31 | 77 % | Fly.io (12), Heroku (7), Kubernetes (5) |
| **Total E1** | 1 | **109 / 350** | **31.1 %** | |
| **Total E2** | 2 | **164 / 279** | **58.8 %** | |

## Verificaciones de la regla de etiquetado

- **YAML del commit de cada ejecución (regla 5).** Hasta la regla 4 se leía el YAML actual del workflow. Había 360 ejecuciones en 7 repositorios cuyo YAML podía ser distinto del actual. Al leer el YAML de su commit, solo 12 se recalcularon (todas de andrewda/inthesoup); el resto tenía el mismo YAML.
- **Hosting estático.** Comparación con la regla 3 de los repositorios aprobados: solo bmlt-enabled/bmlt-server se quedó sin y=0 por esta regla (sus 16 «despliegues» eran publicaciones estáticas). Otros cuatro perdieron sus y=0 por otras causas: solana-playground (falso positivo «App Engine version tag»), pagopa/oneidentity y kiruna-labs/petal (señales de la regla 4) y elsa-backend (solo staging). En la regla 6, sbmagar13/recipe-jar también salió por hosting estático (job «Deploy to Cloudflare Pages»).
- **Segunda muestra de 30 ejecuciones y=0 (semilla 2026).** Para cada una se listaron los pasos que la regla cuenta como despliegue a producción y la señal usada (environment, acción conocida o nombre). 26 eran correctas. Dos falsos positivos se corrigieron en la **regla 6**: el nombre del job también marca el hosting estático (recipe-jar) y «matrix» es un paso auxiliar (hms-dbmi-cellenics/iac: solo se generó la matriz y el despliegue se omitió). Con la regla 6 cambió la y de 64 ejecuciones (52 de recipe-jar y 12 de cellenics/iac). Los otros dos casos eran de gemini-hlsw (lucuma-apps y lucuma-odb), que desde CI solo despliegan a development; los dos se excluyeron por el criterio 2. Las pruebas de la regla 6 están en `backend/riesgo/tests/test_etiquetado.py`.
- **Ejecuciones manuales con entorno indeterminado.** La regla excluyó 246 ejecuciones. Diez repositorios se quedaron sin y=0 y salieron: FHIR/genomics-operations, Opetushallitus/tutu-kasittely, bcgov/dep-public, department-for-transport-BODS/publish-devolved-bus-registration-data, lAnubisl/LostFilmTorrentsFeed, pagopa/developer-portal-cms, remails-com/remails, rit-sse/WebsiteTheSSEquel, techmatters/hrm y zenGate-Global/winter-backend-cardano (226 → 216 válidos).
- **Regla 7 (entorno real de cada ejecución).** Se re-evaluaron todas las ejecuciones etiquetadas de los 279 aprobados. Se mantuvieron 5562 y=0 y 726 y=1. Salieron: 1402 y=1 de ramas sin ningún despliegue completado a producción (sobre todo PR y ramas de trabajo), 1017 y=0 y 263 y=1 cuyo despliegue iba a un entorno no productivo (environment de GitHub o expresión evaluada: 447 + 47), de workflows no productivos (386 + 132) o de ramas no productivas (184 + 84), 157 y=0 en las que ningún paso desplegaba a producción (p. ej. ansible `--syntax-check`). De las manuales excluidas por la regla anterior, 234 siguen con entorno indeterminado al re-evaluarlas. La regla 7 solo restringe: 11 ejecuciones ambiguas de UMNET-perfSONAR/pssid-gui2 que pasaban a y=1 se dejaron excluidas. Doce repositorios se quedaron sin y=0 y salieron (216 → 204): AllenNeuralDynamics/zombie (`publish_dev.yml`), PRX/Infrastructure (`deploy-terra-stag.yml`), inu-appcenter/inu-portal-server (`cicd-dev.yml`), pongstylin/tactics y tornotron/echno-web (workflows de staging/test), bcgov/reserve-rec-admin (entorno `reserveRecAdminTest`), UTDNebula/api-tools (rama `develop`), naturebase-app/tnc-blue-carbon-cost-tool (rama `staging`), NewWave4Org/NewWave4.org-frontend-new y ministryofjustice/CFO-DataManagementSystem (environment no productivo), cbg-ethz/WisePulse y Cour-de-cassation/judilibre-search (ansible `--syntax-check`).
- **Muestra de validación final.** Encontró un error: obbyworld/obby despliega solo a Cloudflare Pages con `cloudflare/wrangler-action` y el comando `pages deploy` en el input `command`, que el filtro de hosting estático no leía. Se excluyó por el criterio 2 (204 → 203) y el script ahora añade los inputs `command`/`args` de cada paso al texto que revisa ese filtro. Se buscó el mismo caso en los 204 workflows: solo obby lo tenía (google/neuroglancer ya excluía sus pasos de Firebase Hosting por el nombre).
- **Regla 8 y exclusiones por el criterio 2 (2026-11-11).** Al verificar el dataset de variables v2 aparecieron errores que la muestra de la regla 7 no vio. (1) **Cinco repositorios cuyo workflow no despliega a producción**, excluidos: egovernments/Citizen-Complaint-Resolution-System (`local-setup-ci.yaml`: `ansible-playbook` contra `localhost`), usegalaxy-eu/infrastructure-playbook (`tpv.yml`: `ansible-playbook --connection=local`), ccrma/webchuck-ide (el despliegue a producción está comentado; solo despliega la rama `dev`), sillsdev/web-xforge (`e2e-tests.yml`: pruebas de extremo a extremo con un playbook contra `localhost`) y UMNET-perfSONAR/pssid-gui2 (`ci.yml`: pruebas y escaneo de CVE; el paso «Build the images this deployment ships» no despliega). (2) **Pasos que GitHub añade alrededor de una acción** («Build owner/acción@v» de las acciones de Docker, «Pre …», «Post …») ya no cuentan como despliegue: se ejecutan aunque el paso real se omita con `if:`. Mismo cambio en la plataforma (`backend/riesgo/services/etiquetado.py`) con pruebas. En el dataset solo cambió el subtipo de 3 fallos de PROCOLLAB-github/procollab (`posterior_mismo_job` → `antes_del_despliegue`); los y=0 falsos por un paso «Build» venían de webchuck-ide. (3) **Pull requests**: un fallo antes del despliegue en un pull request se excluye si, con el YAML de su commit, el despliegue está limitado a push, a una rama o a una etiqueta (3 filas: ekzhang/sshx y ImCa0/just-laws, pull requests desde ramas de fork llamadas main/master). (4) **Retención de GitHub**: al re-etiquetar, 75 ejecuciones ya no tenían pasos (56) o se habían borrado (19); conservan la etiqueta de la regla 7, calculada cuando los pasos existían, y quedan marcadas (`regla8_sin_datos`). Resultado: 203 → **198 repositorios válidos** (197 en el entrenamiento, 195 con filas en el tope de 50) y 4.123 ejecuciones (y=1 9,7 %). No se reabrió la búsqueda (decisión del autor).
- **Tope por plataforma (criterio 4).** En el dataset final AWS tiene 52 de 198 repositorios (26,3 %), por debajo del 30 %; la siguiente es Google Cloud con 36 (18,2 %). Había más aprobados de AWS, y la selección dejó fuera los excedentes con ese motivo.

## Validación manual de etiquetas (métrica de calidad del dataset)

Muestras aleatorias del dataset final (tope de 50) de 25 ejecuciones y=0 y 25 y=1 (semillas 7 y 2027), más una muestra dirigida a los casos de riesgo (semilla 11). Cada etiqueta se comprobó a mano con los jobs, los pasos, el log del paso de despliegue (y=0) o del paso fallido (y=1) y el YAML del workflow. Una etiqueta es correcta si la ejecución es un intento de despliegue **a producción** y el resultado (completado / no completado) es el que dice la etiqueta. Los logs de más de 90 días ya no están disponibles; en esos casos se usaron los pasos y el YAML.

| Regla | y=0 correctas | y=1 correctas | Precisión total | IC 95 % (Wilson) |
|---|---:|---:|---:|---:|
| Regla 6 (semilla 7, antes de corregir) | 13/25 (52 %) | 11/25 (44 %) | **24/50 (48 %)** | 34.8 – 61.5 % |
| Regla 7 (semilla 7) | 24/25 (96 %) | 25/25 (100 %) | **49/50 (98 %)** | 89.5 – 99.6 % |
| Regla 8 (semilla 2027, nueva muestra aleatoria) | 25/25 (100 %) | 22/24 (92 %) | **47/49 (96 %)** | 86.3 – 98.9 % |

El intervalo de Wilson se usa porque la proporción está cerca de 1 y la muestra es pequeña: el intervalo normal (Wald) daría un límite superior por encima del 100 %. Las muestras aleatorias son estratificadas (25 y=0 y 25 y=1), así que el total pondera igual ambas clases. En la muestra de la regla 8 un caso no se pudo verificar (la ejecución se borró de GitHub) y no cuenta en el denominador; contándolo como error, la precisión sería 47/50 (94 %).

**Las precisiones miden el dataset tal como estaba al tomar cada muestra.** Los errores encontrados se corrigieron después (exclusión del repositorio o regla nueva), pero la estimación no se recalcula como si fueran aciertos: el valor que describe la calidad del dataset final es el de la última muestra aleatoria (semilla 2027).

Errores con la regla 6 (semilla 7, antes de corregir):

- ejecución de pull_request: el despliegue estaba condicionado a la rama principal y no hubo intento (9)
- entorno reserveRecAdminTest (workflow deploy-test) (3)
- pull_request con `ansible-playbook --syntax-check`: no despliega (1)
- workflow «Deploy Staging» (secretos STAGING_ENV) aunque declara environment production (1)
- release prerelease (v5.3.0-rc3): el job «Determine ENV» elige el entorno `at`, no prod (1)
- workflow de calidad: `ansible-playbook --syntax-check`, no despliega (1)
- workflow «Staging (IITM)» desde la rama development (1)
- rama preprod: despliega con Env=preprod (1)
- rama staging: el job get-environment elige staging (1)
- rama main despliega a staging; producción solo desde la rama production (1)
- rama develop: el environment se evalúa a staging (1)
- rama dev: despliega al namespace de desarrollo (1)
- pull_request: falló el despliegue de vista previa (environment pull_request) (1)
- falló el job «Deploy Dev» (environment DEV); el intento iba a desarrollo (1)
- workflow «Deploy Staging» (1)
- ejecución manual con input deploy_production: no se sabe si iba a producción (1)

Errores con la regla 7 (semilla 7):

- El paso «Deploy» es wrangler-action con `pages deploy dist` (Cloudflare Pages, hosting estático; criterio 2). El comando va en el input `command`, que el filtro de hosting estático no leía. (1)

Errores con la regla 8 (semilla 2027, nueva muestra aleatoria):

- pull_request desde una rama de fork llamada main/master: el despliegue está limitado a push, no hubo intento (corregido con la regla de pull requests) (1)
- pssid-gui2: el workflow `ci.yml` no despliega; el paso «Build the images this deployment ships» no es un despliegue (repositorio excluido, criterio 2) (1)

### Muestra dirigida (semilla 11, regla 8)

Busca los dos errores que la muestra aleatoria no detectó: ejecuciones de pull request y ejecuciones cuyo job usa una acción de Docker (paso «Build owner/acción@v»). No es representativa del dataset: mide la precisión en esos subconjuntos de riesgo.

| Grupo | Correctas | Precisión | IC 95 % (Wilson) |
|---|---:|---:|---:|
| Filas de pull_request (todas las del dataset: 20) | 11/20 | 55 % | 34.2 – 74.2 % |
| Filas con despliegue por acción de Docker (25 de 332) | 25/25 | 100 % | 86.7 – 100.0 % |
| **Total** | 36/45 | 80 % | 66.2 – 89.1 % |

Errores de la muestra dirigida:

- pssid-gui2: el workflow `ci.yml` no despliega; el paso «Build the images this deployment ships» no es un despliegue (repositorio excluido, criterio 2) (6)
- pull_request desde una rama de fork llamada main/master: el despliegue está limitado a push, no hubo intento (corregido con la regla de pull requests) (3)

La primera muestra mostró que la regla 6 no resolvía el entorno real de muchas ejecuciones (decidido por la rama, la release o la salida de otro job) y que la regla de la rama solo se aplicaba a 9 repositorios. La **regla 7** corrige esas causas sin cambiar los criterios (ver `informes/fase2_variable_objetivo.md`, sección 4) y la segunda muestra, tomada con la misma semilla sobre el dataset corregido, mide la calidad del dataset final. Su único error (obby, hosting estático) se corrigió excluyendo el repositorio. Además, un caso con la y correcta tiene el subtipo equivocado: en burningmantech/ranger-ims-go el paso que falla despliega el entorno `training` después de desplegar producción (debería ser `posterior_mismo_job`); el subtipo no se usa como variable objetivo.

Al construir las variables del dataset v2 se encontraron errores que esa muestra no vio (repositorios de CI que no despliegan y pasos «Build owner/acción@v» contados como despliegue). La **regla 8** los corrige (ver «Verificaciones») y se validó con una muestra aleatoria nueva (semilla 2027) y una muestra dirigida (semilla 11). El detalle de cada caso está en `informes/validacion_etiquetas_regla6.json`, `…regla7.json`, `…regla8_aleatoria.json` y `…regla8_dirigida.json`.

## Decisiones del autor (2026-11-09)

1. **Ampliación de la búsqueda (lote 13): aprobada.** La estrategia 2 se amplió con acciones de despliegue de plataformas con menos repositorios (flyctl, App Engine, Cloud Functions, Container Apps, Azure Functions, DigitalOcean App Platform, Heroku, `kubectl set image` y `gcloud run deploy`). No cambia ningún criterio.
2. **govuk-one-login (txma-audit y txma-ticf-integration): se mantienen excluidos.** Su workflow publica en las cuentas build/dev de GOV.UK One Login y la promoción a producción la hace AWS CodePipeline, fuera de GitHub Actions. El despliegue a producción no es observable en los datos, así que no se puede etiquetar (criterio 2).
3. **Ejecuciones manuales con entorno indeterminado: se excluyen.** Una ejecución `workflow_dispatch` cuyo entorno de destino no se puede determinar se excluye (`excluida_entorno_indeterminado`). La regla está en `informes/fase2_variable_objetivo.md`, sección 4. Caso de origen: dimagi/open-chat-studio (input `dev`/`prod`), que en sus 100 últimas ejecuciones no tiene ninguna manual.
4. **Dataset congelado (2026-11-10).** Los 203 repositorios y el tope de 50 ejecuciones por repositorio quedan fijos. No se hace curva de aprendizaje; `informes/orden_repos_curva.csv` se conserva solo como registro del orden de selección.
5. **Corrección de etiquetas antes de entrenar (2026-11-11, opción A).** Se excluyen por el criterio 2 los repositorios que no despliegan a producción, se corrige el etiquetador (pasos «Build/Pre/Post» de GitHub, también en la plataforma), se re-etiqueta con la API y se revisan a mano solo los repositorios de mayor riesgo. **No se reabre la búsqueda**: se acepta el número de repositorios que quede (198, por debajo del mínimo de 200). Se quita `rama_bot` del modelo v2 (constante en el dataset).
6. **Variables del modelo v2 (2026-11-10).** Se quita `reejecutado_por_otro` (no se conoce antes del despliegue). `tiene_pr` (el commit pertenece a un pull request creado antes del despliegue) y `es_reintento` (intento posterior al primero o el mismo workflow ya terminó una ejecución con ese commit) se calculan igual en el entrenamiento y en la plataforma. Se añaden el tamaño del cambio (archivos modificados, líneas añadidas y borradas) y las pruebas fallidas, aproximadas con los checks del mismo commit que terminaron antes del inicio del despliegue, sin los del propio workflow. **Vulnerabilidades y cobertura no se pueden obtener** con un token de solo lectura en repositorios de terceros (alertas de seguridad con permisos de administración; cobertura fuera de GitHub). Detalle en `informes/fase2_variable_objetivo.md`, sección 7.

## Base de datos de la plataforma (2026-11-10)

- Respaldo con `pg_dump` (formato custom) antes de cualquier cambio, guardado fuera del repositorio (`tesis_respaldos/riesgo_despliegue_20261110_171702_antes_0009.dump`).
- Migraciones 0009 (etiqueta `excluida_no_produccion`) y 0010 (nuevo patrón de paso de despliegue) aplicadas. El patrón de los workflows registrados se actualizó en 672 de 672 (todos tenían el patrón por defecto de la migración 0001; no había patrones personalizados).
- Cruce de `riesgo_repositorio` (437) con los 203 repositorios del dataset, por nombre y por `github_id`: **0 en ambos**, 437 solo en la plataforma y 203 solo en el dataset (los 198 actuales son un subconjunto: tampoco tienen ninguno en común; detalle en `informes/cruce_plataforma_dataset_v2.json`). Origen de los 437: 404 del dataset GHALogs v1.1 (alta 2026-10-20), 30 casos de prueba de `datos_prueba/casos_prueba_30.json` (2026-10-27), el repositorio de demostración y 2 altas manuales sin fuente (Azure-Samples/azure-search-openai-demo y openfoodfacts/openfoodfacts-server).

### Decisiones del autor sobre la plataforma (se aplican cuando v2 esté entrenado y activo)

1. **404 repositorios de GHALogs:** `est_registro='I'` (inactivos), sin borrarlos.
2. **30 casos de prueba:** se marcan como repositorios de prueba y se excluyen de las métricas y los dashboards, igual que el repositorio de demostración.
3. **Azure-Samples/azure-search-openai-demo y openfoodfacts/openfoodfacts-server:** `est_registro='I'`.
4. **Repositorio de demostración** (ErickTerranova2004/demo-despliegue-riesgo): sin cambios.
5. **Requisito técnico:** el modelo `Repositorio` aún no tiene `est_registro` ni un indicador de prueba (solo `es_demostracion`). Hará falta una migración que añada `est_registro` (A/I, por defecto 'A') y el indicador de prueba, y que las vistas que hoy excluyen la demostración excluyan también los de prueba e ignoren los inactivos. Antes de aplicarla, un respaldo nuevo con `pg_dump`.

## Decisiones pendientes

1. **Excepciones de rama de la regla 7.** Solo Explorer-Consulting/SchoolFeedBackWebAPI: la rama `develop` despliega al slot «Production» de Azure Functions. Con la regla 7, los demás repos cuya única rama de despliegue tiene nombre no productivo (dev, develop, staging…) salen del dataset. Si alguno despliega de verdad a producción desde esa rama, habría que añadirlo a `RAMAS_PRODUCCION_EXCEPCION`.
2. **Push de la rama** `feature/100-repos-desplegados` (requiere al autor).

## Decisión metodológica: separación por repositorio

- La separación entrenamiento/prueba es **por repositorio**: todas las ejecuciones de un mismo repositorio quedan en el mismo conjunto. Así el modelo se evalúa con proyectos que no vio y se evita la fuga de información entre ejecuciones del mismo repo (mismo historial, mismos patrones de fallo).
- Curva de aprendizaje (pendiente de ejecutar): [orden_repos_curva.csv](orden_repos_curva.csv) asigna a cada repositorio un orden aleatorio reproducible (semilla 42). Los subconjuntos de 50, 100, 150, 200 y 250 repos son los primeros N de ese orden (columna `entra_desde_n`), de modo que cada subconjunto contiene al anterior.

## Conteo por plataforma

| Plataforma | Repos | % |
|---|---:|---:|
| AWS | 52 | 26.3 |
| Google Cloud | 36 | 18.2 |
| Kubernetes | 28 | 14.1 |
| Fly.io | 25 | 12.6 |
| Servidor propio | 20 | 10.1 |
| Azure | 11 | 5.6 |
| Heroku | 9 | 4.5 |
| DigitalOcean | 6 | 3.0 |
| Vercel | 6 | 3.0 |
| Cloudflare | 5 | 2.5 |

## Conteo por organización (más de un repositorio)

| Organización | Repos |
|---|---:|
| FINTLabs | 5 |
| con2 | 3 |
| redhat-openshift-ecosystem | 3 |
| CBIIT | 3 |
| OpenConceptLab | 2 |
| estuary | 2 |
| ServiceCanada | 2 |
| Health-Education-England | 2 |
| ourresearch | 2 |
| SuffolkLITLab | 2 |
| sil-org | 2 |
| RockefellerArchiveCenter | 2 |
| bcgov | 2 |

Organizaciones distintas: 179.

## Atípicos

Se mantienen en la lista, marcados con ⚠, cuando: (a) sus fallos tienen una sola causa ajena al pipeline; (b) tras excluir las ejecuciones sin jobs les quedan menos de 5 ejecuciones válidas en el dataset final; o (c) en el dataset final tienen una sola clase (solo y=0 o solo y=1). Para los que solo tienen y=1 se indica la causa dominante de sus fallos y, si el 80 % o más de sus y=1 tienen la misma causa (workflow roto, secreto expirado, error de configuración), se propone excluirlos del entrenamiento.

### Excluidos del entrenamiento

- ⛔ **cultpodcasts/RedditPodcastPoster**: No aporta ninguna ejecución válida al dataset final: sus 50 ejecuciones más recientes no tienen jobs.

### Propuestos para excluir del entrenamiento (pendiente de aprobación)

- Ninguno.

### Todos los atípicos

- **ConservationInternational/resilienceatlas**: Tras excluir sus 4 ejecuciones sin jobs le quedan 3 válidas en el dataset final (tope de 50; y=0 2, y=1 1) y 5 en el historial completo: menos de 5.
- **bakaphp/kanvas-ecosystem-api**: Una sola clase en el dataset final: solo y=0 (50).
- **cdklabs/aws-cdk-notices**: Una sola clase en el dataset final: solo y=0 (50).
- **ourresearch/openalex-api-proxy**: Una sola clase en el dataset final: solo y=0 (50).
- **thewca/worldcubeassociation.org**: Una sola clase en el dataset final: solo y=0 (50).
- **michelecoppi/guess_the_player_from_the_path**: Una sola clase en el dataset final: solo y=0 (49).
- **nothink-jp/suzumina.click**: Una sola clase en el dataset final: solo y=0 (49).
- **pharmacosmos-dev/pharma-crm-backend**: Una sola clase en el dataset final: solo y=0 (49).
- **forem/forem**: Una sola clase en el dataset final: solo y=0 (47).
- **b10cks/cms**: Una sola clase en el dataset final: solo y=0 (45).
- **SuffolkLITLab/LITEfile**: Una sola clase en el dataset final: solo y=0 (44).
- **basedosdados/website**: Una sola clase en el dataset final: solo y=0 (41).
- **gamedevpl/www.gamedev.pl**: Una sola clase en el dataset final: solo y=0 (36).
- **ImCa0/just-laws**: Una sola clase en el dataset final: solo y=0 (31).
- **chrismuha/pineneedledesigns.website**: Una sola clase en el dataset final: solo y=0 (29).
- **OpenConceptLab/oclmap**: Una sola clase en el dataset final: solo y=0 (28).
- **ReactiveCircus/kstreamlined-backend**: Una sola clase en el dataset final: solo y=0 (28).
- **devlead/BitbucketPipelinesShield**: Una sola clase en el dataset final: solo y=0 (25).
- **HHS/OPRE-OPS**: Una sola clase en el dataset final: solo y=0 (24).
- **RetellAI/retell-typescript-sdk**: Una sola clase en el dataset final: solo y=0 (24).
- **sue445/regional-rb-calendar**: Una sola clase en el dataset final: solo y=0 (24).
- **alphavantage/alpha_vantage_mcp**: Una sola clase en el dataset final: solo y=0 (21).
- **bramp/myip**: Una sola clase en el dataset final: solo y=0 (21).
- **Open-Earth-Foundation/CityCatalyst**: Una sola clase en el dataset final: solo y=0 (20).
- **allcll/allcll-frontend**: Una sola clase en el dataset final: solo y=0 (19).
- **Choice-of-Law-Dataverse/cold-web-app**: Una sola clase en el dataset final: solo y=0 (19).
- **PJECZ/pjecz-hercules-flask**: Una sola clase en el dataset final: solo y=0 (19).
- **opensearch-project/oscar-ai-bot**: Una sola clase en el dataset final: solo y=0 (18).
- **oslokommune/okdata-token-service**: Una sola clase en el dataset final: solo y=0 (18).
- **ourresearch/parseland-lib**: Una sola clase en el dataset final: solo y=0 (18).
- **linuxfoundation/insights**: Una sola clase en el dataset final: solo y=0 (17).
- **nulib/dc-api-v2**: Una sola clase en el dataset final: solo y=0 (17).
- **TrafeX/clipboard.ninja**: Una sola clase en el dataset final: solo y=0 (17).
- **CodeForPhilly/benefit-decision-toolkit**: Una sola clase en el dataset final: solo y=0 (16).
- **OSU-Sustainability-Office/energy-dashboard**: Una sola clase en el dataset final: solo y=0 (16).
- **PRX/github-toolkit**: Una sola clase en el dataset final: solo y=0 (16).
- **openforis/fra-platform**: Una sola clase en el dataset final: solo y=0 (14).
- **sil-org/app-monitoring-archiver**: Una sola clase en el dataset final: solo y=0 (14).
- **ristekoss/susunjadwal-frontend**: Una sola clase en el dataset final: solo y=0 (13).
- **Stars-and-Stripes-Honor-Flight/sshf-api**: Una sola clase en el dataset final: solo y=0 (13).
- **aquario-ufpb/aquario**: Una sola clase en el dataset final: solo y=0 (12).
- **auth0/openidconnect-playground**: Una sola clase en el dataset final: solo y=0 (12).
- **con2/kompassi**: Una sola clase en el dataset final: solo y=0 (12).
- **flock-community/flock-eco-workday**: Una sola clase en el dataset final: solo y=0 (12).
- **RockefellerArchiveCenter/digital_ingest_webhook**: Una sola clase en el dataset final: solo y=0 (12).
- **benvinegar/counterscale**: Una sola clase en el dataset final: solo y=0 (11).
- **Lumos-Programming/lumos-web**: Una sola clase en el dataset final: solo y=0 (11).
- **puiiyuen/badges**: Una sola clase en el dataset final: solo y=0 (11).
- **Ribbit-Network/api**: Una sola clase en el dataset final: solo y=0 (11).
- **SuffolkLITLab/EfileProxyServer**: Una sola clase en el dataset final: solo y=0 (11).
- **29th/personnel-v3**: Una sola clase en el dataset final: solo y=0 (10).
- **git-for-windows/gfw-helper-github-app**: Una sola clase en el dataset final: solo y=0 (10).
- **haskellweekly/haskellweekly**: Una sola clase en el dataset final: solo y=0 (10).
- **MickaelFontes/noplp-stats**: Una sola clase en el dataset final: solo y=0 (10).
- **sil-org/cloudflare-scanner**: Una sola clase en el dataset final: solo y=0 (10).
- **b-partners/geo-jobs**: Una sola clase en el dataset final: solo y=0 (9).
- **brave/store-brave-com**: Una sola clase en el dataset final: solo y=0 (9).
- **OWASP/threat-dragon**: Una sola clase en el dataset final: solo y=0 (9).
- **asyncapi/cli**: Una sola clase en el dataset final: solo y=0 (8).
- **globe-swiss/phaenonet-functions**: Una sola clase en el dataset final: solo y=0 (8).
- **Makespace/members-app**: Una sola clase en el dataset final: solo y=0 (8).
- **wri/project-zeno-deploy**: Una sola clase en el dataset final: solo y=0 (8).
- **codeforboston/home-energy-analysis-tool**: Una sola clase en el dataset final: solo y=0 (7).
- **data-mermaid/mermaid-api**: Una sola clase en el dataset final: solo y=0 (7).
- **italia/graph-italia**: Una sola clase en el dataset final: solo y=0 (7).
- **moneyadviceservice/frontend**: Una sola clase en el dataset final: solo y=0 (7).
- **redhat-openshift-ecosystem/operator-pipelines**: Una sola clase en el dataset final: solo y=0 (7).
- **aghjones/goal-bot**: Una sola clase en el dataset final: solo y=0 (6).
- **broadinstitute/PrimerCast**: Una sola clase en el dataset final: solo y=0 (5).
- **quarkusio/search.quarkus.io**: Una sola clase en el dataset final: solo y=0 (5).
- **RockefellerArchiveCenter/digitized_image_notifications**: Una sola clase en el dataset final: solo y=0 (5).
- **Asing1001/MovieRater**: Una sola clase en el dataset final: solo y=0 (4).
- **cascadiaquakes/CRESCENT-CVM-WEB**: Una sola clase en el dataset final: solo y=0 (4).
- **defikarte/defikarte.ch**: Una sola clase en el dataset final: solo y=0 (4).
- **google/neuroglancer**: Una sola clase en el dataset final: solo y=1 (4). Causa dominante de los fallos: Fallos de CI variados: build de la documentación (10), npm ci (10), pruebas E2E del proyecto de ejemplo (4) y errores de tipos de TypeScript; ninguna causa supera el 32 %. Tras excluir sus 1 ejecuciones sin jobs le quedan 4 válidas en el dataset final (tope de 50; y=0 0, y=1 4) y 11 en el historial completo: menos de 5.
- **infanf/myanili**: Una sola clase en el dataset final: solo y=0 (4).
- **meerkat-events/meerkat**: Una sola clase en el dataset final: solo y=0 (4).
- **bcgov/klamm**: Una sola clase en el dataset final: solo y=0 (3).
- **emerald-legacy/emeralddb**: Una sola clase en el dataset final: solo y=0 (3).
- **redhat-openshift-ecosystem/pipeline-metrics**: Una sola clase en el dataset final: solo y=0 (3).
- **redhat-openshift-ecosystem/pullsar**: Una sola clase en el dataset final: solo y=0 (3). Tras excluir sus 1 ejecuciones sin jobs le quedan 3 válidas en el dataset final (tope de 50; y=0 3, y=1 0) y 7 en el historial completo: menos de 5.
- **utahudot/udot-atspm**: Una sola clase en el dataset final: solo y=0 (3).
- **bcgov/sso-realm-registry**: Una sola clase en el dataset final: solo y=0 (2).
- **estuary/ui**: Una sola clase en el dataset final: solo y=0 (2).
- **hms-dbmi-cellenics/iac**: Una sola clase en el dataset final: solo y=0 (2).
- **boostorg/website-v2**: Una sola clase en el dataset final: solo y=0 (1).
- **CBIIT/nci-webtools-ccr-cprosite**: Una sola clase en el dataset final: solo y=0 (1).
- **CBIIT/nci-webtools-ccr-microarray**: Una sola clase en el dataset final: solo y=0 (1).
- **CBIIT/nci-webtools-dceg-classification**: Una sola clase en el dataset final: solo y=0 (1).
- **FINTLabs/fint-flyt-frontend**: Una sola clase en el dataset final: solo y=0 (1).
- **frontendnetwork/veganify**: Una sola clase en el dataset final: solo y=0 (1).
- **instantdb/instant**: Una sola clase en el dataset final: solo y=0 (1).
- **PA-NIHR-CRN/dte-study-api**: Una sola clase en el dataset final: solo y=0 (1).
- **Vauhtijuoksu/vauhtijuoksu-api**: Una sola clase en el dataset final: solo y=0 (1).
- **cultpodcasts/RedditPodcastPoster**: 74 de sus 78 ejecuciones fallidas terminaron sin ningún job: el workflow deploy.yml no llegó a arrancar (archivo de workflow inválido). Con la regla de la fase 2 esas 74 quedan excluidas y no cuentan como y=1. Una sola clase en el dataset final: ninguna ejecución válida. Tras excluir sus 74 ejecuciones sin jobs le quedan 0 válidas en el dataset final (tope de 50; y=0 0, y=1 0) y 26 en el historial completo: menos de 5.
- **OpenHistoricalMap/ohm-deploy**: Una sola clase en el dataset final: ninguna ejecución válida.
- **OpenReferralUK/oruk-validator**: Una sola clase en el dataset final: ninguna ejecución válida.

## Lista final

Las columnas y=0 / y=1 y % fallos corresponden al dataset final (tope de 50 ejecuciones); entre paréntesis, con el historial completo (hasta 100).

| # | Repositorio | Organización | Plataforma | Ejec. 6 meses | y=0 / y=1 | % fallos | Evidencia |
|---|---|---|---|---:|---|---:|---|
| 1 | [29th/personnel-v3](https://github.com/29th/personnel-v3/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | 29th | DigitalOcean · App Platform | 12 | 10 / 0 (10 / 0) | 0 | Sistema de gestión de personal en uso por la comunidad 29th Infantry Division (29th.org); DigitalOcean. |
| 2 | [accept-io/midas](https://github.com/accept-io/midas/blob/HEAD/.github/workflows/deploy.yaml) | accept-io | Azure · Container Apps | 15 | 10 / 1 (10 / 1) | 9 | Producto de la empresa Accept (accept.io) para gobernanza de decisiones automatizadas; Azure Container Apps. |
| 3 | [aghjones/goal-bot](https://github.com/aghjones/goal-bot/blob/HEAD/.github/workflows/ci.yml) ⚠ atípico | aghjones | AWS · Elastic Beanstalk | 13 | 6 / 0 (6 / 0) | 0 | Bot en servicio @nhl_goal_bot (Twitter) que publica goles de la NHL; Elastic Beanstalk. |
| 4 | [allcll/allcll-frontend](https://github.com/allcll/allcll-frontend/blob/HEAD/.github/workflows/build-deploy.yml) ⚠ atípico | allcll | Servidor propio · SSH | 26 | 19 / 0 (19 / 1) | 0 | Servicio en producción allcll.kr para la inscripción de asignaturas en la Universidad Sejong, 7 contribuidores; SSH. |
| 5 | [AllenNeuralDynamics/aind-qc-portal](https://github.com/AllenNeuralDynamics/aind-qc-portal/blob/HEAD/.github/workflows/tag_and_publish_main.yml) | AllenNeuralDynamics | AWS · ECS | 33 | 30 / 4 (30 / 4) | 12 | Portal de control de calidad del Allen Institute (qc.allenneuraldynamics.org); AWS ECS. |
| 6 | [alliance-genome/agr_curation](https://github.com/alliance-genome/agr_curation/blob/HEAD/.github/workflows/github-release-build-and-deploy.yml) | alliance-genome | AWS · Elastic Beanstalk | 42 | 27 / 1 (27 / 1) | 4 | Sistema de curación de Alliance of Genome Resources (10480 commits); Elastic Beanstalk. |
| 7 | [alphavantage/alpha_vantage_mcp](https://github.com/alphavantage/alpha_vantage_mcp/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | alphavantage | AWS · SAM / Lambda | 162 | 21 / 0 (44 / 0) | 0 | Servidor MCP oficial de Alpha Vantage en producción (mcp.alphavantage.co); despliega en AWS con SAM. |
| 8 | [andrewda/inthesoup](https://github.com/andrewda/inthesoup/blob/HEAD/.github/workflows/deploy.yaml) | andrewda | Google Cloud · App Engine | 14 | 11 / 6 (11 / 6) | 35 | Aplicación pública inthesoup.xyz para pilotos (aproximaciones IFR); despliega en App Engine. |
| 9 | [aquario-ufpb/aquario](https://github.com/aquario-ufpb/aquario/blob/HEAD/.github/workflows/production.yml) ⚠ atípico | aquario-ufpb | Vercel · Vercel | 12 | 12 / 0 (12 / 0) | 0 | Plataforma en uso por estudiantes y profesores del Centro de Informática de la UFPB (aquarioufpb.com), 24 contribuidores; Vercel. |
| 10 | [Asing1001/MovieRater](https://github.com/Asing1001/MovieRater/blob/HEAD/.github/workflows/build.yml) ⚠ atípico | Asing1001 | Google Cloud · Cloud Run | 27 | 4 / 0 (4 / 15) | 0 | Sitio en producción mvrater.com (calificaciones de películas en Taiwán), 555 commits; Cloud Run. |
| 11 | [asusoda/platform](https://github.com/asusoda/platform/blob/HEAD/.github/workflows/cd.yml) | asusoda | Servidor propio · SSH | 36 | 24 / 5 (24 / 8) | 17 | Plataforma compartida en producción para los clubes de informática de ASU (platform.thesoda.io), 18 contribuidores; SSH. |
| 12 | [asyncapi/cli](https://github.com/asyncapi/cli/blob/HEAD/.github/workflows/release-server-api.yml) ⚠ atípico | asyncapi | DigitalOcean · App Platform | 11 | 8 / 0 (8 / 0) | 0 | Despliega la Server API de AsyncAPI en DigitalOcean App Platform (79 contribuidores). |
| 13 | [auth0/openidconnect-playground](https://github.com/auth0/openidconnect-playground/blob/HEAD/.github/workflows/production.yaml) ⚠ atípico | auth0 | Vercel · Vercel | 12 | 12 / 0 (12 / 0) | 0 | Herramienta pública de Auth0 en producción (openidconnect.net) para explorar el flujo OpenID Connect; Vercel. |
| 14 | [b-partners/geo-jobs](https://github.com/b-partners/geo-jobs/blob/HEAD/.github/workflows/cd-scheduler.yml) ⚠ atípico | b-partners | AWS · CloudFormation | 288 | 9 / 0 (24 / 0) | 0 | Servicio de la empresa BPartners (11 contribuidores, 2640 commits); despliega pilas en CloudFormation. |
| 15 | [b10cks/cms](https://github.com/b10cks/cms/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | b10cks | AWS · ECS | 138 | 45 / 0 (88 / 0) | 0 | CMS de la empresa b10cks (b10cks Cloud); AWS ECS. |
| 16 | [bakaphp/kanvas-ecosystem-api](https://github.com/bakaphp/kanvas-ecosystem-api/blob/HEAD/.github/workflows/ec2-deploy.yaml) ⚠ atípico | bakaphp | Servidor propio · rsync | 879 | 50 / 0 (100 / 0) | 0 | API del producto Kanvas de la empresa Bakaphp, 19 contribuidores; despliegue por rsync. |
| 17 | [basedosdados/website](https://github.com/basedosdados/website/blob/HEAD/.github/workflows/cd-prod.yaml) ⚠ atípico | basedosdados | Kubernetes · Helm | 49 | 41 / 0 (41 / 0) | 0 | Sitio y plataforma de datos abiertos Base dos Dados (basedosdados.org), 30 contribuidores; Helm. |
| 18 | [bcgov/klamm](https://github.com/bcgov/klamm/blob/HEAD/.github/workflows/build-and-deploy.yml) ⚠ atípico | bcgov | Kubernetes · Helm | 17 | 3 / 0 (3 / 0) | 0 | Herramienta de captura de datos del Gobierno de Columbia Británica; Helm. |
| 19 | [bcgov/sso-realm-registry](https://github.com/bcgov/sso-realm-registry/blob/HEAD/.github/workflows/publish-image.yml) ⚠ atípico | bcgov | Kubernetes · Helm | 14 | 2 / 0 (2 / 0) | 0 | Registro de realms del servicio SSO del Gobierno de Columbia Británica; Helm. |
| 20 | [beda-software/fhir-emr](https://github.com/beda-software/fhir-emr/blob/HEAD/.github/workflows/main.yml) | beda-software | Servidor propio · SSH | 77 | 46 / 3 (52 / 3) | 6 | EMR basado en FHIR de la empresa Beda Software, 26 contribuidores; despliega en su servidor por SSH. |
| 21 | [benvinegar/counterscale](https://github.com/benvinegar/counterscale/blob/HEAD/.github/workflows/cd.yaml) ⚠ atípico | benvinegar | Cloudflare · Workers | 11 | 11 / 0 (11 / 0) | 0 | Analítica web open source (2180 estrellas) con su instancia desplegada en Cloudflare Workers. |
| 22 | [bikebrigade/dispatch](https://github.com/bikebrigade/dispatch/blob/HEAD/.github/workflows/deploy.production.yml) | bikebrigade | Fly.io · Fly.io | 35 | 33 / 1 (33 / 1) | 3 | Software de despacho en producción de la ONG Bike Brigade (Toronto), 16 contribuidores; Fly.io. |
| 23 | [bjorn-ali-goransson/built-in-saudi](https://github.com/bjorn-ali-goransson/built-in-saudi/blob/HEAD/.github/workflows/deploy-functions.yml) | bjorn-ali-goransson | Google Cloud · Cloud Functions | 81 | 34 / 1 (60 / 1) | 3 | Sitio público de utilidades en línea built-in-saudi.com, 834 commits; Cloud Functions. |
| 24 | [bokralabs/mizan](https://github.com/bokralabs/mizan/blob/HEAD/.github/workflows/deploy.yml) | bokralabs | DigitalOcean · App Platform | 12 | 9 / 3 (9 / 3) | 25 | Plataforma cívica de transparencia mizanmasr.com (Egipto); DigitalOcean App Platform. |
| 25 | [boostorg/website-v2](https://github.com/boostorg/website-v2/blob/HEAD/.github/workflows/actions-gcp.yaml) ⚠ atípico | boostorg | Kubernetes · Helm | 1743 | 1 / 0 (2 / 0) | 0 | Sitio Django de Boost en producción (boost.org), 34 contribuidores; Helm. |
| 26 | [bramp/myip](https://github.com/bramp/myip/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | bramp | Google Cloud · App Engine | 21 | 21 / 0 (21 / 0) | 0 | Aplicación web pública ip.bramp.net ('What's My IP'), en servicio desde hace años; despliega en App Engine. |
| 27 | [brave/store-brave-com](https://github.com/brave/store-brave-com/blob/HEAD/.github/workflows/build-deploy.yml) ⚠ atípico | brave | AWS · ECS | 29 | 9 / 0 (9 / 0) | 0 | Tienda en producción store.brave.com; AWS ECS. |
| 28 | [broadinstitute/PrimerCast](https://github.com/broadinstitute/PrimerCast/blob/HEAD/.github/workflows/docker.yml) ⚠ atípico | broadinstitute | Google Cloud · Cloud Run | 126 | 5 / 0 (5 / 0) | 0 | Herramienta de diseño de cebadores del Broad Institute; Cloud Run. |
| 29 | [burningmantech/ranger-ims-go](https://github.com/burningmantech/ranger-ims-go/blob/HEAD/.github/workflows/deploy.yml) | burningmantech | AWS · ECS | 83 | 44 / 2 (64 / 17) | 4 | Sistema de gestión de incidentes en uso por los Black Rock Rangers (Burning Man); AWS ECS. |
| 30 | [carbonplan/offsets-db-api](https://github.com/carbonplan/offsets-db-api/blob/HEAD/.github/workflows/fly.yml) | carbonplan | Fly.io · Fly.io | 69 | 4 / 1 (4 / 5) | 20 | API pública OffsetsDB de CarbonPlan (ONG); Fly.io. |
| 31 | [cascadiaquakes/CRESCENT-CVM-WEB](https://github.com/cascadiaquakes/CRESCENT-CVM-WEB/blob/HEAD/.github/workflows/main.yml) ⚠ atípico | cascadiaquakes | AWS · CDK | 111 | 4 / 0 (4 / 0) | 0 | Aplicación en producción cvm.cascadiaquakes.org del centro CRESCENT; AWS CDK. |
| 32 | [CBIIT/nci-webtools-ccr-cprosite](https://github.com/CBIIT/nci-webtools-ccr-cprosite/blob/HEAD/.github/workflows/deploy-infrastructure.yml) ⚠ atípico | CBIIT | AWS · CDK | 10 | 1 / 0 (1 / 0) | 0 | Sitio del NCI en producción (cprosite.ccr.cancer.gov); AWS CDK. |
| 33 | [CBIIT/nci-webtools-ccr-microarray](https://github.com/CBIIT/nci-webtools-ccr-microarray/blob/HEAD/.github/workflows/deploy-infrastructure.yml) ⚠ atípico | CBIIT | AWS · CDK | 28 | 1 / 0 (1 / 0) | 0 | Aplicación MAAP del NCI (maap.ccr.cancer.gov); AWS CDK. |
| 34 | [CBIIT/nci-webtools-dceg-classification](https://github.com/CBIIT/nci-webtools-dceg-classification/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | CBIIT | AWS · ECS | 11 | 1 / 0 (1 / 0) | 0 | Herramienta SOCcer del NCI (soccer.nci.nih.gov); AWS ECS. |
| 35 | [cdklabs/aws-cdk-notices](https://github.com/cdklabs/aws-cdk-notices/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | cdklabs | AWS · CloudFormation | 99 | 50 / 0 (94 / 0) | 0 | Servicio de avisos que consume la CLI de AWS CDK, 37 contribuidores; despliega la pila en CloudFormation. |
| 36 | [chloerei/geeknote](https://github.com/chloerei/geeknote/blob/HEAD/.github/workflows/ci.yml) | chloerei | Fly.io · Fly.io | 111 | 25 / 4 (41 / 6) | 14 | Plataforma comunitaria de blogs en producción geeknote.net; Fly.io. |
| 37 | [Choice-of-Law-Dataverse/cold-web-app](https://github.com/Choice-of-Law-Dataverse/cold-web-app/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | Choice-of-Law-Dataverse | Azure · Container Apps | 19 | 19 / 0 (19 / 0) | 0 | Base de conocimiento en producción cold.global (Universidad de Lucerna, premio ORD 2025); Azure Container Apps. |
| 38 | [chrismuha/pineneedledesigns.website](https://github.com/chrismuha/pineneedledesigns.website/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | chrismuha | Servidor propio · SSH | 29 | 29 / 0 (29 / 0) | 0 | Tienda en línea de la empresa Pine Needle Designs, 7 contribuidores; SSH. |
| 39 | [clementine-player/Website](https://github.com/clementine-player/Website/blob/HEAD/.github/workflows/www.yml) | clementine-player | Google Cloud · App Engine | 40 | 36 / 4 (36 / 4) | 10 | Sitio y servicios web en producción del reproductor Clementine; App Engine. |
| 40 | [codeforboston/home-energy-analysis-tool](https://github.com/codeforboston/home-energy-analysis-tool/blob/HEAD/.github/workflows/heat-stack.yml) ⚠ atípico | codeforboston | Fly.io · Fly.io | 285 | 7 / 0 (15 / 0) | 0 | Calculadora en uso por los asesores de HeatSmart Alliance, 44 contribuidores; Fly.io. |
| 41 | [CodeForPhilly/benefit-decision-toolkit](https://github.com/CodeForPhilly/benefit-decision-toolkit/blob/HEAD/.github/workflows/deploy-builder-api.yml) ⚠ atípico | CodeForPhilly | Google Cloud · Cloud Run | 16 | 16 / 0 (16 / 0) | 0 | Herramienta cívica en producción bdtoolkit.org de Code for Philly; Cloud Run. |
| 42 | [Cog-Creators/Red-GitHubBot](https://github.com/Cog-Creators/Red-GitHubBot/blob/HEAD/.github/workflows/deploy.yaml) | Cog-Creators | Fly.io · Fly.io | 50 | 40 / 3 (40 / 7) | 7 | Bot de GitHub en servicio para el repositorio de Red-DiscordBot; Fly.io. |
| 43 | [con2/edegal](https://github.com/con2/edegal/blob/HEAD/.github/workflows/v4.yaml) | con2 | Kubernetes · Helm | 110 | 37 / 5 (77 / 9) | 12 | Galerías en producción conikuvat.fi y larppikuvat.fi; despliegue en Kubernetes (producción). |
| 44 | [con2/kompassi](https://github.com/con2/kompassi/blob/HEAD/.github/workflows/cicd.yaml) ⚠ atípico | con2 | Kubernetes · Helm | 160 | 12 / 0 (20 / 0) | 0 | Sistema de gestión de eventos en producción kompassi.eu, 30 contribuidores; Helm. |
| 45 | [con2/larpit-fi](https://github.com/con2/larpit-fi/blob/HEAD/.github/workflows/cicd.yaml) | con2 | Kubernetes · Helm | 72 | 43 / 2 (60 / 4) | 4 | Archivo comunitario en producción larpit.fi; Helm. |
| 46 | [ConservationInternational/resilienceatlas](https://github.com/ConservationInternational/resilienceatlas/blob/HEAD/.github/workflows/titiler_cogs_deployment.yaml) ⚠ atípico | ConservationInternational | AWS · SAM / Lambda | 20 | 2 / 1 (2 / 3) | 33 | Resilience Atlas de Conservation International, 22 contribuidores; SAM. |
| 47 | [contrapunk-audio/contrapunk](https://github.com/contrapunk-audio/contrapunk/blob/HEAD/.github/workflows/ci.yml) | contrapunk-audio | Fly.io · Fly.io | 340 | 7 / 2 (23 / 2) | 22 | Aplicación web de Contrapunk (contrapunk.com) para improvisación musical; despliega con flyctl en Fly.io. |
| 48 | [cosmik-network/semble](https://github.com/cosmik-network/semble/blob/HEAD/.github/workflows/fly-prod-deploy.yml) | cosmik-network | Fly.io · Fly.io | 164 | 42 / 7 (89 / 7) | 14 | Red social de investigación en producción (semble.so); Fly.io. |
| 49 | [cultpodcasts/RedditPodcastPoster](https://github.com/cultpodcasts/RedditPodcastPoster/blob/HEAD/.github/workflows/deploy.yml) ⛔ excluido del entrenamiento | cultpodcasts | Azure · Functions | 384 | 0 / 0 (22 / 4) | 0 | Plataforma de cultpodcasts.com (indexación, API pública y publicación en redes); Azure Functions. |
| 50 | [custom-twemoji/custom-twemoji-api](https://github.com/custom-twemoji/custom-twemoji-api/blob/HEAD/.github/workflows/google.yml) | custom-twemoji | Google Cloud · App Engine | 11 | 8 / 3 (8 / 3) | 27 | API pública en servicio customtwemoji.com; App Engine. |
| 51 | [dailybruin/flamingo](https://github.com/dailybruin/flamingo/blob/HEAD/.github/workflows/test_and_deploy.yml) | dailybruin | Kubernetes · kubectl | 17 | 14 / 4 (14 / 7) | 22 | Frontend de dailybruin.com (periódico estudiantil de UCLA), 35 contribuidores; Kubernetes. |
| 52 | [danielroe/nuxt.fyi](https://github.com/danielroe/nuxt.fyi/blob/HEAD/.github/workflows/deploy.yml) | danielroe | Fly.io · Fly.io | 107 | 41 / 9 (79 / 21) | 18 | Servicio en producción nuxt.fyi que detecta sitios Nuxt en Bluesky; despliega el escáner en Fly.io (production). |
| 53 | [data-mermaid/mermaid-api](https://github.com/data-mermaid/mermaid-api/blob/HEAD/.github/workflows/deploy-cdk.yml) ⚠ atípico | data-mermaid | AWS · CDK | 149 | 7 / 0 (11 / 1) | 0 | API de MERMAID (Wildlife Conservation Society), 15 contribuidores; AWS CDK. |
| 54 | [DataDrivenSustainabilitySolutions/off-key](https://github.com/DataDrivenSustainabilitySolutions/off-key/blob/HEAD/.github/workflows/deploy-production.yml) | DataDrivenSustainabilitySolutions | Servidor propio · Ansible | 544 | 9 / 2 (25 / 13) | 18 | Plataforma de detección de anomalías en producción (aberration.app), 7 contribuidores; Ansible. |
| 55 | [defikarte/defikarte.ch](https://github.com/defikarte/defikarte.ch/blob/HEAD/.github/workflows/deploy-backend.yml) ⚠ atípico | defikarte | Azure · Functions | 11 | 4 / 0 (4 / 0) | 0 | Mapa de desfibriladores de Suiza en producción (defikarte.ch); Azure Functions. |
| 56 | [devlead/BitbucketPipelinesShield](https://github.com/devlead/BitbucketPipelinesShield/blob/HEAD/.github/workflows/CakeSdk.yml) ⚠ atípico | devlead | Azure · Functions | 59 | 25 / 0 (28 / 0) | 0 | Servicio público de badges de estado de Bitbucket Pipelines; Azure Functions. |
| 57 | [digital-land/digital-land-lambda](https://github.com/digital-land/digital-land-lambda/blob/HEAD/.github/workflows/deploy.yml) | digital-land | AWS · Lambda | 15 | 5 / 2 (5 / 2) | 29 | Funciones Lambda de la infraestructura de digital-land (gobierno del Reino Unido). |
| 58 | [dimagi/open-chat-studio](https://github.com/dimagi/open-chat-studio/blob/HEAD/.github/workflows/deploy.yml) | dimagi | AWS · ECS | 1046 | 25 / 2 (53 / 2) | 7 | Plataforma Open Chat Studio de Dimagi, 54 contribuidores; AWS ECS. |
| 59 | [domits1/Domits](https://github.com/domits1/Domits/blob/HEAD/.github/workflows/deploy.yml) | domits1 | AWS · Lambda | 283 | 49 / 1 (99 / 1) | 2 | Plataforma de gestión hotelera Domits, 74 contribuidores; AWS Lambda. |
| 60 | [DRC-UA/infoportal](https://github.com/DRC-UA/infoportal/blob/HEAD/.github/workflows/deploy-client.yml) | DRC-UA | Azure · App Service | 118 | 39 / 6 (78 / 13) | 13 | Aplicación de la misión humanitaria de DRC en Ucrania (infoportal-ua.drc.ngo); Azure App Service. |
| 61 | [dreamwidth/dreamwidth](https://github.com/dreamwidth/dreamwidth/blob/HEAD/.github/workflows/worker22-deploy.yml) | dreamwidth | AWS · ECS | 108 | 4 / 1 (54 / 1) | 20 | Plataforma Dreamwidth en producción, 64 contribuidores; AWS ECS. |
| 62 | [EastsidePreparatorySchool/epschedule](https://github.com/EastsidePreparatorySchool/epschedule/blob/HEAD/.github/workflows/deploy.yml) | EastsidePreparatorySchool | Google Cloud · App Engine | 10 | 9 / 1 (9 / 1) | 10 | App de horarios en uso por Eastside Preparatory School (epschedule.com), 20 contribuidores; App Engine. |
| 63 | [eigenweltlabs/legaloss](https://github.com/eigenweltlabs/legaloss/blob/HEAD/.github/workflows/deploy.yml) | eigenweltlabs | Google Cloud · Cloud Run | 47 | 43 / 4 (43 / 4) | 9 | Índice comunitario en producción legal-oss.com con reseñas y estadísticas; Cloud Run. |
| 64 | [ekzhang/sshx](https://github.com/ekzhang/sshx/blob/HEAD/.github/workflows/ci.yaml) | ekzhang | Fly.io · Fly.io | 16 | 1 / 1 (1 / 1) | 50 | Servicio de terminal colaborativa en producción sshx.io (7710 estrellas); Fly.io. |
| 65 | [emerald-legacy/emeralddb](https://github.com/emerald-legacy/emeralddb/blob/HEAD/.github/workflows/main.yml) ⚠ atípico | emerald-legacy | Heroku · Heroku | 50 | 3 / 0 (3 / 0) | 0 | Base de datos de cartas en producción emeralddb.org (Legend of the Five Rings); Heroku. |
| 66 | [Enterprise-CMCS/macpro-appian-connector](https://github.com/Enterprise-CMCS/macpro-appian-connector/blob/HEAD/.github/workflows/deploy.yml) | Enterprise-CMCS | AWS · CDK | 45 | 28 / 5 (28 / 6) | 15 | Conector de datos de producción de CMS (gobierno de EE. UU.); AWS CDK. |
| 67 | [estuary/flow](https://github.com/estuary/flow/blob/HEAD/.github/workflows/deploy-config-encryption.yaml) | estuary | Google Cloud · Cloud Run | 220 | 35 / 1 (64 / 1) | 3 | Plataforma de datos de la empresa Estuary (estuary.dev), 63 contribuidores; Cloud Run. |
| 68 | [estuary/ui](https://github.com/estuary/ui/blob/HEAD/.github/workflows/main.yml) ⚠ atípico | estuary | Google Cloud · Cloud Run | 955 | 2 / 0 (5 / 0) | 0 | Dashboard de producción de la empresa Estuary (dashboard.estuary.dev), 15 contribuidores; despliega en Cloud Run. |
| 69 | [Explorer-Consulting/SchoolFeedBackWebAPI](https://github.com/Explorer-Consulting/SchoolFeedBackWebAPI/blob/HEAD/.github/workflows/gimi_develop_feedback-api.yml) | Explorer-Consulting | Azure · Functions | 48 | 22 / 21 (22 / 21) | 49 | Sistema de encuestas escolares de la consultora Explorer Consulting, 14 contribuidores; Azure Functions. |
| 70 | [fairbanksio/f5news](https://github.com/fairbanksio/f5news/blob/HEAD/.github/workflows/deploy.yml) | fairbanksio | AWS · Serverless Framework | 69 | 36 / 10 (55 / 10) | 22 | Agregador de noticias en producción (f5.news); Serverless Framework. |
| 71 | [fajita-io/fajita](https://github.com/fajita-io/fajita/blob/HEAD/.github/workflows/deploy.yml) | fajita-io | Vercel · Vercel | 87 | 17 / 31 (18 / 67) | 65 | Servicio de monitorización fajita.io; despliega producción en Vercel. |
| 72 | [finite-sample/rmcp](https://github.com/finite-sample/rmcp/blob/HEAD/.github/workflows/deploy.yml) | finite-sample | Google Cloud · Cloud Run | 61 | 49 / 1 (55 / 11) | 2 | Servidor MCP de análisis estadístico (216 estrellas) con instancia desplegada en Cloud Run. |
| 73 | [FINTLabs/fint-flyt-frontend](https://github.com/FINTLabs/fint-flyt-frontend/blob/HEAD/.github/workflows/MD.yaml) ⚠ atípico | FINTLabs | Kubernetes · AKS / Kubernetes | 65 | 1 / 0 (3 / 0) | 0 | Frontend de FINT Flyt, plataforma de integración con archivos de los condados de Noruega; AKS. |
| 74 | [FINTLabs/fint-kontroll-assignment-catalog](https://github.com/FINTLabs/fint-kontroll-assignment-catalog/blob/HEAD/.github/workflows/MD.yaml) | FINTLabs | Kubernetes · AKS / Kubernetes | 63 | 32 / 5 (37 / 8) | 14 | Catálogo de asignaciones de FINT Kontroll (condados de Noruega); AKS. |
| 75 | [FINTLabs/fint-kontroll-role-factory](https://github.com/FINTLabs/fint-kontroll-role-factory/blob/HEAD/.github/workflows/MD.yaml) | FINTLabs | Kubernetes · AKS / Kubernetes | 37 | 32 / 1 (32 / 1) | 3 | Servicio de FINT (TI de los condados noruegos) en Kubernetes (AKS). |
| 76 | [FINTLabs/fint-kontroll-user-catalog](https://github.com/FINTLabs/fint-kontroll-user-catalog/blob/HEAD/.github/workflows/MD.yaml) | FINTLabs | Kubernetes · AKS / Kubernetes | 28 | 18 / 4 (18 / 4) | 18 | Catálogo de usuarios de FINT Kontroll (condados de Noruega); AKS. |
| 77 | [FINTLabs/fint-kunde-portal-frontend-v2](https://github.com/FINTLabs/fint-kunde-portal-frontend-v2/blob/HEAD/.github/workflows/CD.yaml) | FINTLabs | Kubernetes · AKS / Kubernetes | 39 | 37 / 1 (37 / 3) | 3 | Portal de clientes de FINT, plataforma de integración de los condados de Noruega; AKS. |
| 78 | [flock-community/flock-eco-workday](https://github.com/flock-community/flock-eco-workday/blob/HEAD/.github/workflows/gcp.yml) ⚠ atípico | flock-community | Google Cloud · Cloud Run | 440 | 12 / 0 (17 / 0) | 0 | Aplicación de gestión de personal en uso en la empresa Flock, 19 contribuidores; Cloud Run. |
| 79 | [forem/forem](https://github.com/forem/forem/blob/HEAD/.github/workflows/cd.yml) ⚠ atípico | forem | Heroku · Heroku | 1008 | 47 / 0 (90 / 0) | 0 | Forem, la plataforma de dev.to, 427 contribuidores; Heroku (el dataset solo cuenta producción). |
| 80 | [fre5h/rnokpp-telegram-bot](https://github.com/fre5h/rnokpp-telegram-bot/blob/HEAD/.github/workflows/ci.yml) | fre5h | AWS · Lambda | 16 | 6 / 10 (6 / 10) | 62 | Bot de Telegram público en servicio (decodifica el RNOKPP ucraniano); AWS Lambda. |
| 81 | [frontendnetwork/veganify](https://github.com/frontendnetwork/veganify/blob/HEAD/.github/workflows/release.yml) ⚠ atípico | frontendnetwork | Kubernetes · kubectl | 41 | 1 / 0 (1 / 0) | 0 | Aplicación web en producción (veganify.app), 19 contribuidores; Kubernetes. |
| 82 | [gamedevpl/www.gamedev.pl](https://github.com/gamedevpl/www.gamedev.pl/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | gamedevpl | Google Cloud · Cloud Run | 2067 | 36 / 0 (67 / 0) | 0 | Plataforma de juegos en producción (www.gamedev.pl), 33 contribuidores; Cloud Run. |
| 83 | [git-for-windows/gfw-helper-github-app](https://github.com/git-for-windows/gfw-helper-github-app/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | git-for-windows | Azure · Functions | 10 | 10 / 0 (10 / 0) | 0 | GitHub App en producción que automatiza el proyecto Git for Windows; Azure Functions. |
| 84 | [github-copilot-resources/copilot-metrics-viewer](https://github.com/github-copilot-resources/copilot-metrics-viewer/blob/HEAD/.github/workflows/deploy_to_ghcr.yml) | github-copilot-resources | Azure · App Service | 33 | 26 / 1 (26 / 1) | 4 | Visor de métricas de Copilot (648 estrellas); despliega en Azure Web App con environment production. |
| 85 | [globe-swiss/phaenonet-functions](https://github.com/globe-swiss/phaenonet-functions/blob/HEAD/.github/workflows/deploy-function.yml) ⚠ atípico | globe-swiss | Google Cloud · Cloud Functions | 25 | 8 / 0 (8 / 0) | 0 | Funciones de la plataforma de observación PhaenoNet de GLOBE Suiza; Cloud Functions. |
| 86 | [google/neuroglancer](https://github.com/google/neuroglancer/blob/HEAD/.github/workflows/build.yml) ⚠ atípico | google | Google Cloud · App Engine | 602 | 0 / 4 (3 / 8) | 100 | Visor de datos volumétricos de Google (66 contribuidores); el job deploy publica en App Engine solo con push a master. |
| 87 | [govote-sh/govote](https://github.com/govote-sh/govote/blob/HEAD/.github/workflows/fly-deploy.yml) | govote-sh | Fly.io · Fly.io | 22 | 19 / 3 (19 / 3) | 14 | Servicio público por SSH (govote.sh) de información electoral; Fly.io. |
| 88 | [haskellweekly/haskellweekly](https://github.com/haskellweekly/haskellweekly/blob/HEAD/.github/workflows/ci.yaml) ⚠ atípico | haskellweekly | AWS · CloudFormation | 102 | 10 / 0 (26 / 0) | 0 | Aplicación del newsletter y podcast haskellweekly.news, 52 contribuidores; despliega en AWS solo desde main. |
| 89 | [Health-Education-England/TIS-SYNC](https://github.com/Health-Education-England/TIS-SYNC/blob/HEAD/.github/workflows/ci-cd-workflow.yml) | Health-Education-England | AWS · ECS | 10 | 4 / 4 (4 / 4) | 50 | Servicio TIS de Health Education England (NHS); AWS ECS. |
| 90 | [Health-Education-England/TIS-TCS](https://github.com/Health-Education-England/TIS-TCS/blob/HEAD/.github/workflows/ci-cd-workflow.yml) | Health-Education-England | AWS · ECS | 29 | 4 / 10 (4 / 10) | 71 | TIS Core Services de Health Education England (NHS), 36 contribuidores; AWS ECS. |
| 91 | [HelmholtzAI-Consultants-Munich/oligo-designer-toolsuite-front-end](https://github.com/HelmholtzAI-Consultants-Munich/oligo-designer-toolsuite-front-end/blob/HEAD/.github/workflows/deploy_stack.yml) | HelmholtzAI-Consultants-Munich | Servidor propio · Ansible | 17 | 6 / 11 (6 / 11) | 65 | Aplicación web ODT Cloud de Helmholtz AI en vista previa pública, 11 contribuidores; Ansible. |
| 92 | [HHS/OPRE-OPS](https://github.com/HHS/OPRE-OPS/blob/HEAD/.github/workflows/prod_fe_build_and_deploy.yml) ⚠ atípico | HHS | Azure · Container Apps | 36 | 24 / 0 (24 / 0) | 0 | Sistema de gestión de portafolio de OPRE (HHS, gobierno de EE. UU.), 17133 commits; Azure Container Apps. |
| 93 | [hms-dbmi-cellenics/iac](https://github.com/hms-dbmi-cellenics/iac/blob/HEAD/.github/workflows/deploy-changed-cf.yaml) ⚠ atípico | hms-dbmi-cellenics | AWS · CloudFormation | 30 | 2 / 0 (2 / 0) | 0 | Infraestructura y GitOps de la plataforma Cellenics (Harvard Medical School); CloudFormation. |
| 94 | [ImCa0/just-laws](https://github.com/ImCa0/just-laws/blob/HEAD/.github/workflows/main.yml) ⚠ atípico | ImCa0 | Servidor propio · SSH | 58 | 31 / 0 (36 / 3) | 0 | Biblioteca pública de leyes chinas en producción (justlaws.cn, 791 estrellas); despliega por SSH. |
| 95 | [infanf/myanili](https://github.com/infanf/myanili/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | infanf | Google Cloud · Cloud Run | 38 | 4 / 0 (4 / 0) | 0 | Cliente web/PWA de MyAnimeList en producción (myani.li), 1218 commits; despliega en Cloud Run. |
| 96 | [instantdb/instant](https://github.com/instantdb/instant/blob/HEAD/.github/workflows/js.yml) ⚠ atípico | instantdb | Fly.io · Fly.io | 2477 | 1 / 0 (1 / 0) | 0 | Plataforma InstantDB (instantdb.com, 10 561 estrellas); despliega su servidor MCP remoto en Fly.io. |
| 97 | [italia/graph-italia](https://github.com/italia/graph-italia/blob/HEAD/.github/workflows/release.yml) ⚠ atípico | italia | Kubernetes · Helm | 192 | 7 / 0 (11 / 0) | 0 | Servicio Graph Italia del gobierno italiano (Developers Italia); Helm. |
| 98 | [jlab-sensing/ENTS-backend](https://github.com/jlab-sensing/ENTS-backend/blob/HEAD/.github/workflows/deploy.yml) | jlab-sensing | AWS · ECS | 66 | 31 / 5 (31 / 44) | 14 | Servicio de visualización de sensores en producción (dirtviz.jlab.ucsc.edu), 28 contribuidores; AWS ECS. |
| 99 | [KCSU/store](https://github.com/KCSU/store/blob/HEAD/.github/workflows/backend.yml) | KCSU | Google Cloud · Cloud Run | 16 | 15 / 1 (15 / 1) | 6 | Tienda de entradas en uso por el KCSU (store.kcsu.org.uk); Cloud Run. |
| 100 | [kglw-dot-net/tapes](https://github.com/kglw-dot-net/tapes/blob/HEAD/.github/workflows/deploy-production.yml) | kglw-dot-net | Fly.io · Fly.io | 20 | 16 / 2 (16 / 2) | 11 | Aplicación de streaming de conciertos en producción (Gizz Tapes); Fly.io (el dataset solo cuenta producción). |
| 101 | [kusitms-com/api.kusitms.com](https://github.com/kusitms-com/api.kusitms.com/blob/HEAD/.github/workflows/CD.yaml) | kusitms-com | Heroku · Heroku | 22 | 15 / 1 (15 / 1) | 6 | Backend del sitio oficial de la asociación KUSITMS (kusitms.com), 11 contribuidores; Heroku. |
| 102 | [lc-tut/tut-bus](https://github.com/lc-tut/tut-bus/blob/HEAD/.github/workflows/api-deploy.yml) | lc-tut | Google Cloud · App Engine | 20 | 11 / 7 (11 / 7) | 39 | App de horarios de autobús en uso en la Universidad Tecnológica de Tokio (tut-bus.lcn.ad.jp), 9 contribuidores; App Engine. |
| 103 | [linuxfoundation/insights](https://github.com/linuxfoundation/insights/blob/HEAD/.github/workflows/public-api-deploy.yaml) ⚠ atípico | linuxfoundation | Kubernetes · kubectl | 18 | 17 / 0 (17 / 0) | 0 | LFX Insights de la Linux Foundation (insights.linuxfoundation.org); Kubernetes. |
| 104 | [LucasDEVBA/BAUSA](https://github.com/LucasDEVBA/BAUSA/blob/HEAD/.github/workflows/deploy-functions.yml) | LucasDEVBA | Google Cloud · Cloud Functions | 43 | 30 / 2 (30 / 2) | 6 | Sitio público y plataforma de la empresa BAUSA (bolsaatletausa.com); Cloud Functions. |
| 105 | [Lumos-Programming/lumos-web](https://github.com/Lumos-Programming/lumos-web/blob/HEAD/.github/workflows/deploy-cloudrun-release.yaml) ⚠ atípico | Lumos-Programming | Google Cloud · Cloud Run | 16 | 11 / 0 (11 / 0) | 0 | Sitio y plataforma de miembros en uso del círculo Lumos (Universidad Nacional de Yokohama), 15 contribuidores; Cloud Run. |
| 106 | [Makespace/members-app](https://github.com/Makespace/members-app/blob/HEAD/.github/workflows/cicd.yml) ⚠ atípico | Makespace | Fly.io · Fly.io | 1193 | 8 / 0 (21 / 0) | 0 | App de miembros en uso por Cambridge Makespace (app.makespace.org), 18 contribuidores; Fly.io. |
| 107 | [makutamoto/mojacoder](https://github.com/makutamoto/mojacoder/blob/HEAD/.github/workflows/main.yml) | makutamoto | AWS · CDK | 17 | 13 / 2 (13 / 2) | 13 | Sitio en producción mojacoder.app para publicar problemas de programación competitiva; AWS CDK. |
| 108 | [MAPSuio/peoply-frontend](https://github.com/MAPSuio/peoply-frontend/blob/HEAD/.github/workflows/ci.yml) | MAPSuio | DigitalOcean · App Platform | 622 | 15 / 1 (28 / 1) | 6 | Calendario de eventos en uso en el Departamento de Informática de la UiO (peoply.app), 15 contribuidores; DigitalOcean. |
| 109 | [mbeher2200/DarkHours](https://github.com/mbeher2200/DarkHours/blob/HEAD/.github/workflows/deploy.yml) | mbeher2200 | AWS · CDK | 355 | 3 / 1 (13 / 3) | 25 | Aplicación pública darkhours.app para planificar astrofotografía; AWS CDK. |
| 110 | [meerkat-events/meerkat](https://github.com/meerkat-events/meerkat/blob/HEAD/.github/workflows/continous-deployment.yml) ⚠ atípico | meerkat-events | Fly.io · Fly.io | 150 | 4 / 0 (8 / 0) | 0 | Herramienta de preguntas para conferencias usada por la Ethereum Foundation (Devcon); Fly.io. |
| 111 | [michelecoppi/guess_the_player_from_the_path](https://github.com/michelecoppi/guess_the_player_from_the_path/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | michelecoppi | Google Cloud · Cloud Run | 190 | 49 / 0 (98 / 1) | 0 | Bot de Telegram en servicio con juego diario, clasificaciones y eventos; Cloud Run. |
| 112 | [MickaelFontes/noplp-stats](https://github.com/MickaelFontes/noplp-stats/blob/HEAD/.github/workflows/deploy.yaml) ⚠ atípico | MickaelFontes | Google Cloud · App Engine | 261 | 10 / 0 (18 / 1) | 0 | Aplicación pública noplp-stats.fr con estadísticas del programa NOPLP, 945 commits; App Engine. |
| 113 | [ministryofjustice/laa-fee-calculator](https://github.com/ministryofjustice/laa-fee-calculator/blob/HEAD/.github/workflows/ci_cd.yml) | ministryofjustice | Kubernetes · kubectl | 171 | 10 / 1 (15 / 3) | 9 | Calculadora de honorarios de la Legal Aid Agency (Ministerio de Justicia del Reino Unido); Kubernetes. |
| 114 | [moneyadviceservice/frontend](https://github.com/moneyadviceservice/frontend/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | moneyadviceservice | Heroku · Heroku | 26 | 7 / 0 (7 / 0) | 0 | Herramientas del Money Advice Service (moneyhelper.org.uk, gobierno del Reino Unido), 73 contribuidores; Heroku. |
| 115 | [mozilla/probe-scraper](https://github.com/mozilla/probe-scraper/blob/HEAD/.github/workflows/build-test-deploy.yml) | mozilla | Google Cloud · Cloud Functions | 193 | 13 / 1 (25 / 2) | 7 | Servicio de telemetría de Mozilla en producción, 77 contribuidores; Cloud Functions. |
| 116 | [moztechCEE/ecom-accounting-system-](https://github.com/moztechCEE/ecom-accounting-system-/blob/HEAD/.github/workflows/deploy-cloudrun-backend.yml) | moztechCEE | Google Cloud · Cloud Run | 60 | 21 / 4 (21 / 5) | 16 | Sistema contable en uso por la empresa (multiempresa, multimoneda), 645 commits; Cloud Run. |
| 117 | [noi-techpark/opendatahub-timeseries-api](https://github.com/noi-techpark/opendatahub-timeseries-api/blob/HEAD/.github/workflows/main.yml) | noi-techpark | Kubernetes · Helm | 75 | 11 / 1 (21 / 1) | 8 | API de movilidad del Open Data Hub (NOI Techpark), 18 contribuidores; Helm. |
| 118 | [nothink-jp/suzumina.click](https://github.com/nothink-jp/suzumina.click/blob/HEAD/.github/workflows/deploy-functions.yml) ⚠ atípico | nothink-jp | Google Cloud · Cloud Functions | 193 | 49 / 0 (99 / 0) | 0 | Sitio comunitario en producción suzumina.click (autenticación con Discord, botones de audio); Cloud Functions. |
| 119 | [nulib/dc-api-v2](https://github.com/nulib/dc-api-v2/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | nulib | AWS · SAM / Lambda | 61 | 17 / 0 (18 / 1) | 0 | API de las colecciones digitales de las bibliotecas de Northwestern University (api.dc.library.northwestern.edu); SAM. |
| 120 | [Oatmeal-Farm-Network/oatmealfarmnetwork-in](https://github.com/Oatmeal-Farm-Network/oatmealfarmnetwork-in/blob/HEAD/.github/workflows/deploy-cloud-run.yml) | Oatmeal-Farm-Network | Google Cloud · Cloud Run | 19 | 16 / 3 (16 / 3) | 16 | Frontend de la plataforma de la empresa Oatmeal Farm Network (oatmealfarmnetwork.com), 7 contribuidores; Cloud Run. |
| 121 | [ocftw/open-star-ter-village](https://github.com/ocftw/open-star-ter-village/blob/HEAD/.github/workflows/deploy.yml) | ocftw | Fly.io · Fly.io | 35 | 26 / 3 (26 / 3) | 10 | Juego en línea de Open Culture Foundation Taiwán (openstartervillage.ocf.tw), 13 contribuidores; Fly.io. |
| 122 | [Open-Earth-Foundation/CityCatalyst](https://github.com/Open-Earth-Foundation/CityCatalyst/blob/HEAD/.github/workflows/hiap-meed-tag.yml) ⚠ atípico | Open-Earth-Foundation | Kubernetes · kubectl | 22 | 20 / 0 (20 / 0) | 0 | Plataforma climática para ciudades en producción (citycatalyst.openearth.org), 25 contribuidores; Kubernetes. |
| 123 | [opencap-org/opencap-api](https://github.com/opencap-org/opencap-api/blob/HEAD/.github/workflows/ecr.yml) | opencap-org | AWS · ECS | 12 | 10 / 2 (10 / 2) | 17 | API de OpenCap que sirve la web app.opencap.ai y la app iOS; AWS ECS. |
| 124 | [OpenConceptLab/oclmap](https://github.com/OpenConceptLab/oclmap/blob/HEAD/.github/workflows/build.yml) ⚠ atípico | OpenConceptLab | AWS · ECS | 195 | 28 / 0 (55 / 2) | 0 | OCL Mapper (Open Concept Lab), herramienta de mapeo de terminología médica; AWS ECS. |
| 125 | [OpenConceptLab/oclweb2](https://github.com/OpenConceptLab/oclweb2/blob/HEAD/.github/workflows/build.yml) | OpenConceptLab | AWS · ECS | 57 | 38 / 5 (40 / 25) | 12 | TermBrowser v2 de Open Concept Lab, en uso; AWS ECS. |
| 126 | [openforis/fra-platform](https://github.com/openforis/fra-platform/blob/HEAD/.github/workflows/heroku-production.js.yml) ⚠ atípico | openforis | Heroku · Heroku | 15 | 14 / 0 (14 / 0) | 0 | Plataforma de la Evaluación de Recursos Forestales (FRA) de la FAO, 22 contribuidores; Heroku. |
| 127 | [OpenHistoricalMap/ohm-deploy](https://github.com/OpenHistoricalMap/ohm-deploy/blob/HEAD/.github/workflows/deploy-k3s-cluster.yaml) ⚠ atípico | OpenHistoricalMap | Kubernetes · Helm | 95 | 0 / 0 (1 / 1) | 0 | Despliegue a staging y producción de OpenHistoricalMap.org; Helm (el dataset solo cuenta producción). |
| 128 | [OpenReferralUK/oruk-validator](https://github.com/OpenReferralUK/oruk-validator/blob/HEAD/.github/workflows/ci.yml) ⚠ atípico | OpenReferralUK | Heroku · Heroku | 180 | 0 / 0 (4 / 0) | 0 | API y validador de Open Referral UK para directorios de servicios públicos; Heroku. |
| 129 | [opensafely/open-pathology](https://github.com/opensafely/open-pathology/blob/HEAD/.github/workflows/cd.yaml) | opensafely | DigitalOcean · App Platform | 47 | 34 / 4 (34 / 4) | 11 | Aplicación de OpenSAFELY (beta.openpathology.net), 7 contribuidores; DigitalOcean App Platform. |
| 130 | [opensearch-project/oscar-ai-bot](https://github.com/opensearch-project/oscar-ai-bot/blob/HEAD/.github/workflows/deploy-prod.yml) ⚠ atípico | opensearch-project | AWS · CDK | 23 | 18 / 0 (18 / 0) | 0 | Asistente de operaciones en servicio del proyecto OpenSearch; CDK. |
| 131 | [OpenSID/pantau](https://github.com/OpenSID/pantau/blob/HEAD/.github/workflows/deploy_rilis.yml) | OpenSID | Servidor propio · SSH | 13 | 12 / 2 (12 / 2) | 14 | PantauSID, servicio de monitoreo del uso de OpenSID en Indonesia, 22 contribuidores; SSH. |
| 132 | [oslokommune/okdata-token-service](https://github.com/oslokommune/okdata-token-service/blob/HEAD/.github/workflows/deploy-prod.yml) ⚠ atípico | oslokommune | AWS · SAM / Lambda | 19 | 18 / 0 (18 / 0) | 0 | API de tokens de la plataforma de datos de la Municipalidad de Oslo; SAM. |
| 133 | [OSU-Sustainability-Office/energy-dashboard](https://github.com/OSU-Sustainability-Office/energy-dashboard/blob/HEAD/.github/workflows/API-deploy.yml) ⚠ atípico | OSU-Sustainability-Office | AWS · SAM / Lambda | 16 | 16 / 0 (16 / 0) | 0 | Panel de energía en producción de la Universidad Estatal de Oregón; SAM. |
| 134 | [ourresearch/openalex-api-proxy](https://github.com/ourresearch/openalex-api-proxy/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | ourresearch | Cloudflare · Workers | 113 | 50 / 0 (99 / 0) | 0 | Proxy de producción de la API de OpenAlex (OurResearch); Cloudflare Workers. |
| 135 | [ourresearch/parseland-lib](https://github.com/ourresearch/parseland-lib/blob/HEAD/.github/workflows/aws.yml) ⚠ atípico | ourresearch | AWS · ECS | 331 | 18 / 0 (57 / 0) | 0 | Servicio de análisis de OurResearch desplegado en AWS ECS (environment production). |
| 136 | [OWASP/threat-dragon](https://github.com/OWASP/threat-dragon/blob/HEAD/.github/workflows/push.yaml) ⚠ atípico | OWASP | Heroku · Heroku | 22 | 9 / 0 (9 / 0) | 0 | Herramienta de modelado de amenazas de OWASP (94 contribuidores) desplegada como aplicación web en Heroku. |
| 137 | [PA-NIHR-CRN/dte-study-api](https://github.com/PA-NIHR-CRN/dte-study-api/blob/HEAD/.github/workflows/bpor_rms_build.yml) ⚠ atípico | PA-NIHR-CRN | AWS · ECS | 90 | 1 / 0 (1 / 0) | 0 | API del servicio de voluntarios de investigación del NIHR (Reino Unido); AWS ECS. |
| 138 | [pandorabox-io/pandorabox.io](https://github.com/pandorabox-io/pandorabox.io/blob/HEAD/.github/workflows/deployment.yml) | pandorabox-io | Servidor propio · Ansible | 19 | 8 / 4 (8 / 4) | 33 | Configuración del servidor de juego en servicio pandorabox.io; Ansible. |
| 139 | [pcraig3/hols](https://github.com/pcraig3/hols/blob/HEAD/.github/workflows/main.yml) | pcraig3 | Google Cloud · Cloud Run | 12 | 8 / 2 (8 / 2) | 20 | API y web pública canada-holidays.ca (feriados de Canadá) desplegada en Cloud Run con push a main. |
| 140 | [pharmacosmos-dev/pharma-crm-backend](https://github.com/pharmacosmos-dev/pharma-crm-backend/blob/HEAD/.github/workflows/prod-ci-cd.yml) ⚠ atípico | pharmacosmos-dev | Servidor propio · SSH | 320 | 49 / 0 (99 / 0) | 0 | Backend de Pharma Go para la gestión de farmacias de Pharmacosmos; SSH. |
| 141 | [PJECZ/pjecz-hercules-flask](https://github.com/PJECZ/pjecz-hercules-flask/blob/HEAD/.github/workflows/gcloud-app-deploy.yaml) ⚠ atípico | PJECZ | Google Cloud · App Engine | 19 | 19 / 0 (19 / 0) | 0 | Sistema web Hércules del Poder Judicial del Estado de Coahuila; App Engine. |
| 142 | [playfulprogramming/hoof](https://github.com/playfulprogramming/hoof/blob/HEAD/.github/workflows/fly.yml) | playfulprogramming | Fly.io · Fly.io | 81 | 42 / 4 (67 / 4) | 9 | Servicios backend en producción del sitio Playful Programming (API y cola de tareas); Fly.io. |
| 143 | [PREreview/stats](https://github.com/PREreview/stats/blob/HEAD/.github/workflows/ci.yml) | PREreview | Fly.io · Fly.io | 742 | 13 / 17 (23 / 18) | 57 | Aplicación en producción stats.prereview.org de la ONG PREreview; Fly.io. |
| 144 | [PROCOLLAB-github/procollab](https://github.com/PROCOLLAB-github/procollab/blob/HEAD/.github/workflows/deploy.yml) | PROCOLLAB-github | Servidor propio · rsync | 62 | 47 / 1 (57 / 4) | 2 | Plataforma social en producción app.procollab.ru; rsync. |
| 145 | [PRX/github-toolkit](https://github.com/PRX/github-toolkit/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | PRX | AWS · SAM / Lambda | 18 | 16 / 0 (16 / 0) | 0 | GitHub App en uso por la organización PRX; SAM. |
| 146 | [puiiyuen/badges](https://github.com/puiiyuen/badges/blob/HEAD/.github/workflows/cd.yaml) ⚠ atípico | puiiyuen | Cloudflare · Workers | 11 | 11 / 0 (11 / 0) | 0 | Servicio público de badges (badges.peiyuan.ch); Cloudflare Workers. |
| 147 | [puzzlenetwork/puzzle-swap](https://github.com/puzzlenetwork/puzzle-swap/blob/HEAD/.github/workflows/deploy.yml) | puzzlenetwork | Heroku · Heroku | 23 | 14 / 2 (14 / 3) | 12 | Frontend del exchange descentralizado Puzzle Swap, 10 contribuidores; Heroku. |
| 148 | [PythonistasBR/bot](https://github.com/PythonistasBR/bot/blob/HEAD/.github/workflows/fly.yml) | PythonistasBR | Fly.io · Fly.io | 12 | 11 / 2 (11 / 2) | 15 | Bot de Telegram en servicio de la comunidad Python Brasil, 11 contribuidores; Fly.io. |
| 149 | [quarkusio/search.quarkus.io](https://github.com/quarkusio/search.quarkus.io/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | quarkusio | Kubernetes · Helm | 48 | 5 / 0 (5 / 0) | 0 | Backend de búsqueda en producción de los sitios de Quarkus; Helm (OpenShift). |
| 150 | [ReactiveCircus/kstreamlined-backend](https://github.com/ReactiveCircus/kstreamlined-backend/blob/HEAD/.github/workflows/ci.yml) ⚠ atípico | ReactiveCircus | Google Cloud · Cloud Run | 111 | 28 / 0 (48 / 1) | 0 | API GraphQL de las apps móviles KStreamlined; Cloud Run. |
| 151 | [REAN-Foundation/rean-bot-wrapper](https://github.com/REAN-Foundation/rean-bot-wrapper/blob/HEAD/.github/workflows/prod-ci-cd.yml) | REAN-Foundation | AWS · ECS | 11 | 9 / 1 (9 / 1) | 10 | Servicios del chatbot de salud de la REAN Foundation (WhatsApp y Telegram); AWS ECS. |
| 152 | [redhat-openshift-ecosystem/operator-pipelines](https://github.com/redhat-openshift-ecosystem/operator-pipelines/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | redhat-openshift-ecosystem | Servidor propio · Ansible | 145 | 7 / 0 (15 / 0) | 0 | Pipelines de certificación de operadores de Red Hat en servicio, 48 contribuidores; Ansible. |
| 153 | [redhat-openshift-ecosystem/pipeline-metrics](https://github.com/redhat-openshift-ecosystem/pipeline-metrics/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | redhat-openshift-ecosystem | Servidor propio · Ansible | 12 | 3 / 0 (3 / 0) | 0 | Servicio de métricas de los pipelines de certificación de Red Hat; Ansible. |
| 154 | [redhat-openshift-ecosystem/pullsar](https://github.com/redhat-openshift-ecosystem/pullsar/blob/HEAD/.github/workflows/ci-cd.yaml) ⚠ atípico | redhat-openshift-ecosystem | Servidor propio · Ansible | 69 | 3 / 0 (7 / 0) | 0 | Aplicación de estadísticas de uso de operadores de OpenShift (Red Hat); Ansible. |
| 155 | [remix-run/remix-website](https://github.com/remix-run/remix-website/blob/HEAD/.github/workflows/deploy.production.yml) | remix-run | Fly.io · Fly.io | 117 | 45 / 1 (84 / 7) | 2 | Sitio y aplicación remix.run (servidor Remix), 60 contribuidores; Fly.io. |
| 156 | [replicatedhq/ttl.sh](https://github.com/replicatedhq/ttl.sh/blob/HEAD/.github/workflows/deploy.yml) | replicatedhq | Servidor propio · Ansible | 17 | 16 / 4 (16 / 4) | 20 | Registro público de imágenes ttl.sh en servicio (Replicated); Ansible. |
| 157 | [ReseauEntourage/entourage-ror](https://github.com/ReseauEntourage/entourage-ror/blob/HEAD/.github/workflows/master.yml) | ReseauEntourage | Heroku · Heroku | 124 | 45 / 5 (77 / 14) | 10 | Backend de la red solidaria Entourage (ONG), 16 contribuidores; Heroku. |
| 158 | [RetellAI/retell-typescript-sdk](https://github.com/RetellAI/retell-typescript-sdk/blob/HEAD/.github/workflows/deploy-mcp-server.yml) ⚠ atípico | RetellAI | AWS · ECS | 26 | 24 / 0 (24 / 0) | 0 | Despliega el servidor MCP de producción de Retell AI en AWS ECS (environment production). |
| 159 | [Ribbit-Network/api](https://github.com/Ribbit-Network/api/blob/HEAD/.github/workflows/ci.yml) ⚠ atípico | Ribbit-Network | Fly.io · Fly.io | 50 | 11 / 0 (11 / 0) | 0 | API pública de mediciones de CO2 de Ribbit Network; Fly.io. |
| 160 | [ristekoss/susunjadwal-frontend](https://github.com/ristekoss/susunjadwal-frontend/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | ristekoss | Vercel · Vercel | 13 | 13 / 0 (13 / 0) | 0 | Planificador de horarios en uso en la Universitas Indonesia (susunjadwal.cs.ui.ac.id), 39 contribuidores; Vercel. |
| 161 | [RockefellerArchiveCenter/digital_ingest_webhook](https://github.com/RockefellerArchiveCenter/digital_ingest_webhook/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | RockefellerArchiveCenter | AWS · Lambda | 24 | 12 / 0 (12 / 0) | 0 | Webhook en producción del Rockefeller Archive Center para Archivematica; AWS Lambda. |
| 162 | [RockefellerArchiveCenter/digitized_image_notifications](https://github.com/RockefellerArchiveCenter/digitized_image_notifications/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | RockefellerArchiveCenter | AWS · Lambda | 10 | 5 / 0 (5 / 0) | 0 | Servicio de notificaciones de digitalización del Rockefeller Archive Center; Lambda. |
| 163 | [ruby-no-kai/sponsor-app](https://github.com/ruby-no-kai/sponsor-app/blob/HEAD/.github/workflows/ci.yml) | ruby-no-kai | AWS · Lambda | 22 | 12 / 6 (12 / 10) | 33 | CRM de patrocinios en uso por RubyKaigi (sponsorships.rubykaigi.org); AWS Lambda. |
| 164 | [RunOnFlux/flux-domain-manager](https://github.com/RunOnFlux/flux-domain-manager/blob/HEAD/.github/workflows/main.yml) | RunOnFlux | Servidor propio · Ansible | 30 | 26 / 1 (26 / 1) | 4 | Servicio de dominios y balanceo en producción de la red Flux, 14 contribuidores; Ansible. |
| 165 | [ScriptureHabit/scripture-habit](https://github.com/ScriptureHabit/scripture-habit/blob/HEAD/.github/workflows/ci.yml) | ScriptureHabit | Vercel · Vercel | 880 | 19 / 6 (39 / 9) | 24 | Aplicación web en producción scripturehabit.app, 8 contribuidores y 1876 commits; Vercel. |
| 166 | [SecondRobotics/SecondWebsite](https://github.com/SecondRobotics/SecondWebsite/blob/HEAD/.github/workflows/django.yml) | SecondRobotics | Servidor propio · SSH | 12 | 6 / 2 (6 / 2) | 25 | Sitio Django en producción de los eventos de Second Robotics (secondrobotics.org) con marcadores; SSH. |
| 167 | [ServiceCanada/feedback-cron](https://github.com/ServiceCanada/feedback-cron/blob/HEAD/.github/workflows/main.yml) | ServiceCanada | Kubernetes · AKS / Kubernetes | 25 | 18 / 3 (18 / 3) | 14 | Proceso de comentarios de páginas de Canada.ca (Service Canada); AKS. |
| 168 | [ServiceCanada/feedback-viewer](https://github.com/ServiceCanada/feedback-viewer/blob/HEAD/.github/workflows/main.yml) | ServiceCanada | Kubernetes · AKS / Kubernetes | 26 | 20 / 1 (20 / 1) | 5 | Aplicación de Service Canada (gobierno de Canadá) para revisar comentarios; Kubernetes (AKS). |
| 169 | [sil-org/app-monitoring-archiver](https://github.com/sil-org/app-monitoring-archiver/blob/HEAD/.github/workflows/ci.yml) ⚠ atípico | sil-org | AWS · CDK | 35 | 14 / 0 (14 / 0) | 0 | Servicio interno de SIL que archiva resultados de monitorización; AWS CDK. |
| 170 | [sil-org/cloudflare-scanner](https://github.com/sil-org/cloudflare-scanner/blob/HEAD/.github/workflows/ci.yml) ⚠ atípico | sil-org | AWS · CDK | 23 | 10 / 0 (10 / 0) | 0 | Servicio interno de SIL que revisa registros de Cloudflare y avisa por correo; AWS CDK. |
| 171 | [Sophon/FightingNerd](https://github.com/Sophon/FightingNerd/blob/HEAD/.github/workflows/deploy-bot-immediate.yml) | Sophon | Fly.io · Fly.io | 67 | 48 / 2 (63 / 5) | 4 | Bot de Discord en servicio con apps en Play Store y App Store (datos de juegos de lucha); Fly.io. |
| 172 | [Stars-and-Stripes-Honor-Flight/sshf-api](https://github.com/Stars-and-Stripes-Honor-Flight/sshf-api/blob/HEAD/.github/workflows/cloudrun-promote-prd.yml) ⚠ atípico | Stars-and-Stripes-Honor-Flight | Google Cloud · Cloud Run | 13 | 13 / 0 (13 / 0) | 0 | API de operaciones de la ONG Stars and Stripes Honor Flight; Cloud Run. |
| 173 | [sue445/regional-rb-calendar](https://github.com/sue445/regional-rb-calendar/blob/HEAD/.github/workflows/build.yml) ⚠ atípico | sue445 | Google Cloud · Cloud Functions | 100 | 24 / 0 (46 / 0) | 0 | Calendario en servicio de los grupos regionales de Ruby, 19 contribuidores; Cloud Functions. |
| 174 | [SuffolkLITLab/EfileProxyServer](https://github.com/SuffolkLITLab/EfileProxyServer/blob/HEAD/.github/workflows/fly-prod-release.yml) ⚠ atípico | SuffolkLITLab | Fly.io · Fly.io | 11 | 11 / 0 (11 / 0) | 0 | Proxy de presentación electrónica judicial en servicio (Suffolk LIT Lab); Fly.io. |
| 175 | [SuffolkLITLab/LITEfile](https://github.com/SuffolkLITLab/LITEfile/blob/HEAD/.github/workflows/fly-deploy.yml) ⚠ atípico | SuffolkLITLab | Fly.io · Fly.io | 124 | 44 / 0 (85 / 0) | 0 | Aplicación de presentación electrónica del Suffolk LIT Lab; Fly.io. |
| 176 | [sugaroverflow/timetable](https://github.com/sugaroverflow/timetable/blob/HEAD/.github/workflows/deploy-production.yml) | sugaroverflow | DigitalOcean · App Platform | 56 | 46 / 4 (50 / 6) | 8 | Aplicación comunitaria Topic (topic.forum) para organizar sesiones; DigitalOcean App Platform. |
| 177 | [thecourseforum/theCourseForum2](https://github.com/thecourseforum/theCourseForum2/blob/HEAD/.github/workflows/aws.yml) | thecourseforum | AWS · ECS | 59 | 29 / 7 (29 / 7) | 19 | Sitio en producción thecourseforum.com usado por estudiantes de UVA, 102 contribuidores; despliega en AWS ECS. |
| 178 | [thegreenwebfoundation/carbon-txt-validator](https://github.com/thegreenwebfoundation/carbon-txt-validator/blob/HEAD/.github/workflows/run-deploy.yml) | thegreenwebfoundation | Servidor propio · Ansible | 13 | 12 / 1 (12 / 1) | 8 | Validador de carbon.txt en servicio de la Green Web Foundation; Ansible. |
| 179 | [thewca/worldcubeassociation.org](https://github.com/thewca/worldcubeassociation.org/blob/HEAD/.github/workflows/deploy-nextjs.yml) ⚠ atípico | thewca | AWS · ECS | 128 | 50 / 0 (97 / 2) | 0 | Sitio en producción de la World Cube Association, 148 contribuidores; ECS. |
| 180 | [Tiameds-pvt-ltd/Lab-automation](https://github.com/Tiameds-pvt-ltd/Lab-automation/blob/HEAD/.github/workflows/build-deploy.yml) | Tiameds-pvt-ltd | AWS · ECS | 18 | 9 / 20 (9 / 20) | 69 | Sistema de automatización de laboratorios de la empresa Tiameds; ECS. |
| 181 | [TrafeX/clipboard.ninja](https://github.com/TrafeX/clipboard.ninja/blob/HEAD/.github/workflows/deploy.yaml) ⚠ atípico | TrafeX | Vercel · Vercel | 184 | 17 / 0 (37 / 0) | 0 | Servicio público clipboard.ninja, con app en Play Store; Vercel. |
| 182 | [TrigpointingUK/platform](https://github.com/TrigpointingUK/platform/blob/HEAD/.github/workflows/forum-build.yml) | TrigpointingUK | AWS · ECS | 10 | 4 / 1 (4 / 1) | 20 | Plataforma comunitaria trigpointing.uk (20 años); AWS ECS. |
| 183 | [trylinky/linky](https://github.com/trylinky/linky/blob/HEAD/.github/workflows/ci.yml) | trylinky | Cloudflare · Workers | 22 | 12 / 3 (12 / 3) | 20 | Servicio en producción lin.ky (constructor de páginas personales); Cloudflare Workers, entorno Production. |
| 184 | [tuist/tuist](https://github.com/tuist/tuist/blob/HEAD/.github/workflows/omada-deployment.yml) | tuist | Kubernetes · Helm | 48 | 28 / 2 (28 / 2) | 7 | Servidor de la plataforma Tuist (tuist.dev, 5861 estrellas); Helm. |
| 185 | [Twisted-Artists-Guild/tag-web](https://github.com/Twisted-Artists-Guild/tag-web/blob/HEAD/.github/workflows/deploy_tag-www.yml) | Twisted-Artists-Guild | Azure · App Service | 70 | 45 / 4 (59 / 6) | 8 | Frontend de la plataforma TwistedArtistsGuild.com, 6 contribuidores; Azure App Service. |
| 186 | [twohoursonelife/dictator](https://github.com/twohoursonelife/dictator/blob/HEAD/.github/workflows/deploy.yml) | twohoursonelife | Fly.io · Fly.io | 19 | 12 / 5 (12 / 5) | 29 | Bot de Discord en servicio de la comunidad del juego Two Hours One Life; Fly.io. |
| 187 | [utahudot/udot-atspm](https://github.com/utahudot/udot-atspm/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | utahudot | Google Cloud · Cloud Run | 26 | 3 / 0 (3 / 0) | 0 | Sistema ATSPM del Departamento de Transporte de Utah; Cloud Run. |
| 188 | [Vacademy-io/vacademy_edtech_platform](https://github.com/Vacademy-io/vacademy_edtech_platform/blob/HEAD/.github/workflows/docker-publish-voice-bot-service.yml) | Vacademy-io | Kubernetes · kubectl | 259 | 44 / 3 (83 / 5) | 6 | Plataforma LMS en producción (vacademy.io), 22 contribuidores; Kubernetes. |
| 189 | [vapor/penny-bot](https://github.com/vapor/penny-bot/blob/HEAD/.github/workflows/deploy.yml) | vapor | AWS · Lambda | 35 | 26 / 4 (26 / 4) | 13 | Bot de Discord en servicio para la comunidad Vapor; AWS Lambda. |
| 190 | [VATSIM-Radar/vatsim-radar](https://github.com/VATSIM-Radar/vatsim-radar/blob/HEAD/.github/workflows/publish.yaml) | VATSIM-Radar | Kubernetes · Helm | 61 | 32 / 1 (38 / 5) | 3 | Servicio de monitorización de tráfico en producción vatsim-radar.com, 59 contribuidores; Helm. |
| 191 | [Vauhtijuoksu/vauhtijuoksu-api](https://github.com/Vauhtijuoksu/vauhtijuoksu-api/blob/HEAD/.github/workflows/ci.yaml) ⚠ atípico | Vauhtijuoksu | Kubernetes · Helm | 75 | 1 / 0 (2 / 0) | 0 | API del evento benéfico de speedrunning Vauhtijuoksu (Finlandia); Helm en Kubernetes. |
| 192 | [VectorInstitute/aieng-bot](https://github.com/VectorInstitute/aieng-bot/blob/HEAD/.github/workflows/deploy-dashboard.yml) | VectorInstitute | Google Cloud · Cloud Run | 16 | 13 / 3 (13 / 7) | 19 | Bot en uso por el Vector Institute para mantener sus repositorios de AI Engineering; Cloud Run. |
| 193 | [vicharanashala/vibe](https://github.com/vicharanashala/vibe/blob/HEAD/.github/workflows/deploy-backend-all.yml) | vicharanashala | Google Cloud · Cloud Run | 83 | 33 / 2 (54 / 2) | 6 | Plataforma de aprendizaje ViBe en uso, 68 contribuidores; Cloud Run. |
| 194 | [voces/emoji-sheep-tag](https://github.com/voces/emoji-sheep-tag/blob/HEAD/.github/workflows/shard.yml) | voces | Fly.io · Fly.io | 18 | 17 / 4 (17 / 7) | 19 | Juego multijugador en el navegador alojado de forma persistente (est.w3x.io); Fly.io. |
| 195 | [vrk-kpa/opendata](https://github.com/vrk-kpa/opendata/blob/HEAD/.github/workflows/prod.yml) | vrk-kpa | AWS · CDK | 17 | 14 / 2 (14 / 2) | 12 | Portal nacional de datos abiertos de Finlandia (avoindata.fi), 67 contribuidores; AWS CDK. |
| 196 | [wevm/frog](https://github.com/wevm/frog/blob/HEAD/.github/workflows/main.yml) | wevm | Cloudflare · Workers | 93 | 45 / 1 (74 / 2) | 2 | Producto de wevm en producción (frog.fm); despliega la app en Cloudflare Workers. |
| 197 | [wri/project-zeno-deploy](https://github.com/wri/project-zeno-deploy/blob/HEAD/.github/workflows/deploy.yaml) ⚠ atípico | wri | Kubernetes · Helm | 170 | 8 / 0 (8 / 0) | 0 | Despliegue del proyecto Zeno del World Resources Institute (staging y producción); Helm. |
| 198 | [xsnippet/xsnippet-infra](https://github.com/xsnippet/xsnippet-infra/blob/HEAD/.github/workflows/cd.yaml) | xsnippet | Servidor propio · Ansible | 10 | 3 / 7 (3 / 7) | 70 | Despliegue de producción de xsnippet.org (API y web); Ansible. |

## Excluidos

Total con motivo registrado: 768 (no se listan los descartados solo por tener menos de 10 ejecuciones en 6 meses: 4949).

### Por motivo

- ningún paso despliega a un entorno de aplicación (o solo previews de PR): 120
- historial de commits insuficiente (menos de 20 commits o de 60 días): 101
- ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100): 75
- despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack): 42
- más del 80 % de los commits recientes son automáticos (bots): 38
- más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle: 30
- Proyecto de curso universitario (SoPra FS26, Universidad de Zúrich).: 9
- Biblioteca o herramienta; el workflow solo despliega su sitio de documentación.: 9
- Máximo de 5 por organización: de FINTLabs se eligen los 5 con más ejecuciones.: 7
- Proyecto personal de un solo autor sin evidencia de usuarios.: 5
- YAML sin jobs: 4
- Las ejecuciones recientes se omitieron (skipped): el despliegue no se ejecuta.: 3
- Sin README ni descripción: no se puede confirmar que esté en uso.: 3
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; su 'producción' es GitHub Pages y el despliegue por SSH va solo a stage.: 2
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow build-deploy-k8s-dev-hetzner.yml despliega a dev.: 2
- Sitio de documentación.: 2
- Proyecto de portafolio de un solo autor sin evidencia de usuarios.: 2
- Framework; el workflow solo despliega su documentación (Cloudflare Pages).: 2
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow staging.yml despliega a staging.: 2
- Biblioteca de componentes Vue; el despliegue es de su sitio de documentación.: 2
- Criterio 2 (solo producción): el workflow publica en las cuentas build/dev de GOV.UK One Login; la promoción a producción la hace AWS CodePipeline fuera de GitHub Actions.: 2
- Sitio de documentación estático.: 2
- Proyecto de portafolio sin evidencia de usuarios.: 2
- Las 15 ejecuciones recientes se omitieron (skipped): el despliegue no se ejecuta.: 2
- El despliegue es a hosting estático (Cloudflare Pages o similar), equivalente a GitHub Pages.: 2
- Proyecto de curso (Diplomado de desarrollo Fullstack, Universidad Católica Boliviana).: 1
- Proyecto de curso universitario (código de curso 1ASI0657, grupo 3).: 1
- Sitio de marketing, no una aplicación.: 1
- Proyecto de 78 días sin evidencia de usuarios; las 13 ejecuciones fallaron.: 1
- Proyecto de laboratorio académico con tema de portafolio ('A Yotsuya-lab project', topic kojira-portfolio).: 1
- El workflow candidato solo despliega la página de inicio.: 1
- Evaluación de curso (EP3 DevOps).: 1
- Proyecto personal de un solo autor (78 días) sin evidencia de usuarios.: 1
- Un solo contribuidor sin evidencia de usuarios; las 93 ejecuciones recientes fallaron.: 1
- Proyecto de equipo de un curso de DevOps (AET-DevOps26).: 1
- Producto para que terceros lo instalen; el workflow despliega su instancia de demostración en Heroku.: 1
- Sitio de documentación de cursos (VitePress).: 1
- Aplicación de finanzas personales del autor; 49 de 52 ejecuciones fallidas.: 1
- Sin README ni descripción: no se puede confirmar el uso.: 1
- Criterio 2 (solo producción): el workflow candidato despliega al sandbox (build-deploy-k8s-sandbox-hetzner.yml).: 1
- Simulador personal sin web pública ni evidencia de usuarios.: 1
- El servicio alojado se cerró ('The hosted service ... is shut down').: 1
- Plataforma de automatización personal ('Personal automation and monitoring platform').: 1
- El workflow candidato hace un backup (release.yml); no despliega una aplicación.: 1
- Proyecto de portafolio de un solo autor (modelo de scoring con sección de resultados).: 1
- Biblioteca de guardrails; el workflow despliega una función auxiliar (appa-yell), no una aplicación en uso.: 1
- El workflow candidato solo valida los playbooks (ansible-lint y --syntax-check); no despliega.: 1
- Un solo autor y dominio de pruebas (duckdns): sin evidencia de uso.: 1
- Proyecto de 3 personas en un dominio pages.dev, sin evidencia de usuarios.: 1
- Aplicación de ejemplo de un taller de AWS.: 1
- Proyecto de una comunidad de aprendizaje (AWS User Group Manizales) de 84 días sin evidencia de usuarios.: 1
- Proyecto de una comunidad de aprendizaje (AWS User Group Manizales) de 75 días.: 1
- Biblioteca Kotlin; el Worker desplegado es su sitio de documentación.: 1
- Sin web ni evidencia de usuarios.: 1
- Instancia de demostración (demo.backstage.io).: 1
- Sitio de documentación o estático, no una aplicación. (Hugo): 1
- Criterio 2 (solo producción): según el README solo corre en el namespace dev de OpenShift.: 1
- Proyecto personal de un solo autor.: 1
- Proyecto de portafolio con demo; las 88 ejecuciones recientes fallaron.: 1
- Colección de roles de Ansible; el workflow prueba el despliegue de clústeres, no despliega una aplicación.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega staging.checkmate.so y demo.checkmate.so (el job deploy-prod es la demo).: 1
- Galería de demostraciones (demo.bokeh.org).: 1
- El workflow candidato empaqueta el chart de Helm (prerelease); no despliega.: 1
- Herramientas de automatización de blogs; 99 de 100 ejecuciones fallidas.: 1
- Generador de documentación (herramienta); lo desplegado es su sitio estático.: 1
- Sitio web de contenidos de un centro universitario, no una aplicación.: 1
- Proyecto personal de un solo autor (61 commits, 95 días) sin evidencia de usuarios.: 1
- Herramienta de línea de comandos (changelogs y versiones); el despliegue es auxiliar.: 1
- SDK en etapa inicial (20 commits, 71 días), no una aplicación en uso.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job deploy-staging despliega a staging.: 1
- Prototipo declarado ('Frontend-only prototype').: 1
- Proyecto de curso (CS618) con el README de la plantilla de Vite.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega a dev o qa (ramas *_dev y *_qa; sus 100 deployments registrados son dev y qa).: 1
- El despliegue a producción está comentado en el workflow (`node.js.yml`) y solo despliega la rama `dev` (rsync); las y=0 venían del paso «Build burnett01/rsync-deployments», que no despliega (criterio 2). Detectado al verificar el dataset v2.: 1
- Infraestructura de cuentas de AWS (landing zone), no una aplicación.: 1
- Sin web ni evidencia de uso de la aplicación desplegada.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega a staging e integration.: 1
- Implementación de un protocolo; el despliegue en Fly.io es un relay de demostración.: 1
- Plantilla de administración (template).: 1
- Herramientas internas sin evidencia pública de la organización ni de usuarios.: 1
- Ejemplo/plantilla ('Production-quality example for Elixir/Phoenix').: 1
- El workflow candidato solo despliega la documentación (Cloudflare Pages).: 1
- Instalador; el workflow prueba la instalación, no despliega una aplicación en uso.: 1
- Toolkit de investigación; el despliegue por rsync es de su sitio de documentación.: 1
- Aplicaciones de ejemplo (sample apps).: 1
- Proyecto de equipo sin evidencia de usuarios (121 commits).: 1
- Agregador personal para el sitio del autor (damo.io), no una aplicación con usuarios.: 1
- Proyecto de 2 personas sin evidencia de uso; las 27 ejecuciones recientes fallaron.: 1
- Aplicación de referencia de Datadog sin evidencia de uso en producción.: 1
- Proyecto personal sin README ni evidencia de uso (34 commits).: 1
- Proyecto de un grupo de estudio (DDD 12.ª generación, equipo web 1).: 1
- Sitio de portafolio personal.: 1
- Proyecto de equipo de un club de formación (Depromeet, 17.ª generación).: 1
- Biblioteca de constructs de CDK, no una aplicación.: 1
- Plantilla (template repository).: 1
- Sin web ni evidencia de uso; las 15 ejecuciones recientes fallaron.: 1
- Complemento de Thunderbird; el despliegue por rsync es de su sitio web.: 1
- Mod de Minecraft; el despliegue en Vercel es de su wiki.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow dashboard-dev.yml despliega al entorno playground.: 1
- Plataforma para ejecutar bots propios; no hay evidencia de una instancia en uso.: 1
- Contenido declarado como generado por IA y ritmo atípico (1542 commits en 164 días); lo desplegado es el sitio.: 1
- Sitio web estático y el workflow candidato publica en staging.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega el entorno beta de la web.: 1
- Aplicación de aprendizaje/demostración de la organización dwyl; las 13 ejecuciones recientes fallaron.: 1
- Rol de Ansible (herramienta); el workflow lo prueba, no despliega una aplicación.: 1
- Sin README; proyecto personal de un solo autor (82 días).: 1
- Sitio web informativo de un consorcio de investigación, no una aplicación.: 1
- El workflow del dataset (`local-setup-ci.yaml`) es CI: ejecuta `ansible-playbook` contra `localhost` (`-c local`) para probar los playbooks; no despliega a producción (criterio 2). Detectado al verificar el dataset v2 (filas de pull_request con y=0).: 1
- Criterio 2 (solo producción): el workflow despliega instancias de prueba por rama, no producción.: 1
- Proyecto personal (trading simulado) con la mayoría de ejecuciones omitidas.: 1
- Utilidad pequeña (37 commits) sin web ni evidencia de usuarios.: 1
- Ejercicio del curso Full Stack Open.: 1
- El README no corresponde al proyecto desplegado: no se puede confirmar qué es ni que esté en uso.: 1
- El workflow candidato (docs-deploy.yml) solo despliega la documentación, no la aplicación.: 1
- Tablero Kanban genérico sin evidencia de usuarios (frontend en una URL de Vercel autogenerada).: 1
- Sin web ni evidencia de usuarios; README de configuración del entorno de desarrollo.: 1
- Organización de un solo contribuidor sin evidencia de usuarios; frontend en una URL de Vercel autogenerada.: 1
- Sitio de documentación o estático, no una aplicación. (MkDocs): 1
- Aplicación de aprendizaje de un solo autor (93 días), probable proyecto de estudiante.: 1
- Proyecto de ingeniería inversa de un juego; el despliegue publica un build estático para el navegador.: 1
- Organización de ejemplos de Facebook (fbsamples): entorno de exploración del SDK.: 1
- Sitio web de contenidos del laboratorio, no una aplicación.: 1
- Juego educativo; el despliegue publica un build estático WebGL.: 1
- Entorno de desarrollo del AIDS Data Repository, no la aplicación desplegada.: 1
- Biblioteca Kotlin; el workflow solo despliega su sitio web.: 1
- El job candidato (publish-docs) solo publica la documentación.: 1
- Demostración de un pipeline CI/CD para una app Node.js de ejemplo.: 1
- Aplicación que se ejecuta solo en el navegador; el despliegue publica un frontend estático.: 1
- Microservicio de un proyecto de webshop de formación, sin evidencia de usuarios.: 1
- Sitio estático (Zola).: 1
- El workflow candidato solo despliega previews (entorno preview).: 1
- Sin README ni web: no se puede confirmar el uso.: 1
- Apuntes de un curso de GCP (lote 'gcp8ambatch').: 1
- Criterio 2 (solo producción): el workflow del dataset solo despliega a las apps de Heroku observe-dev-* y explore-gemini-dev (entorno «development»); producción se promueve fuera del workflow. Detectado en la muestra de y=0 con semilla 2026.: 1
- Criterio 2 (solo producción): el workflow del dataset solo despliega a las apps de Heroku *-dev (entorno «development»); producción se promueve fuera del workflow. Detectado en la muestra de y=0 con semilla 2026.: 1
- Criterio 2 (solo producción): la organización despliega desde CI solo a development (ver lucuma-apps y lucuma-odb) y el 92 % de las ejecuciones se omiten.: 1
- Sitio web estático (Hugo) del proyecto Goa, no una aplicación.: 1
- Sitio de documentación o estático, no una aplicación.: 1
- Fuentes de documentación estática de GroupDocs.Viewer.: 1
- Proyecto de aficionados sin dominio propio ni evidencia de usuarios.: 1
- Proyecto de curso universitario (sopra-fs26, Universidad de Zúrich).: 1
- Proyecto de un solo autor reciente sin evidencia de usuarios.: 1
- Sitio web personal.: 1
- Sistema de diseño y sitio de contenidos (taxonomía visual), no una aplicación.: 1
- Repositorio de práctica sin README ni descripción (28 commits).: 1
- El workflow candidato restaura un backup (restore.yaml); no despliega la aplicación.: 1
- El workflow candidato solo despliega la landing page.: 1
- Sitio de documentación estático (VuePress).: 1
- Criterio 2 (hosting estático): el workflow solo despliega el frontend a Cloudflare Pages, no una aplicación.: 1
- Landing page estática (Astro).: 1
- README mínimo: no se puede confirmar que la aplicación esté en uso.: 1
- Herramientas que se ejecutan solo en el navegador; el despliegue publica un sitio estático sin backend.: 1
- Script personal que genera un JSON con las publicaciones del autor.: 1
- Criterio 2 (solo producción): el workflow candidato es deploy-to-staging.yml (environment staging).: 1
- Sin README ni descripción; un solo autor y 90 días: no hay evidencia de aplicación en uso.: 1
- Proyecto personal de un solo autor sin web ni evidencia de usuarios.: 1
- Aplicación de macOS; el despliegue es de su sitio de documentación.: 1
- Receptor web que se ejecuta en el dispositivo; el despliegue publica archivos estáticos.: 1
- API de ejemplo de formación (taller mecánico) sin usuarios reales.: 1
- El despliegue es la demo pública (demo.lvelup.info).: 1
- Proyecto experimental con el acceso público pausado ('public acquisition paused').: 1
- Proyecto teórico personal (texto sobre potencial humano), no una aplicación en uso.: 1
- Aplicación de escritorio y biblioteca; el workflow despliega un sitio auxiliar, no la aplicación.: 1
- Sitio estático de contenidos (Astro).: 1
- El despliegue en Fly.io es la demo pública (demo.portkey.page).: 1
- Artefactos de instalación (imágenes y charts), no una aplicación desplegada.: 1
- Sitio de juego hecho con un amigo, declarado 'vibe-coded'; no es una aplicación en uso.: 1
- Blog, no una aplicación.: 1
- Sitio de documentación y blog de Leaning Technologies, no una aplicación.: 1
- Sin web ni descripción del uso: no se puede confirmar que esté en producción.: 1
- Framework CSS; el despliegue es de su sitio de documentación.: 1
- Herramienta que se ejecuta solo en el navegador; el despliegue publica un build estático sin backend.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega al entorno Preview de Fly.io.: 1
- Proyecto de equipo estudiantil (46 commits, 73 días) sin evidencia de usuarios.: 1
- El job candidato publica el chart de Helm; no despliega a un entorno de aplicación.: 1
- Sin README ni descripción útil; proyecto personal de 2 personas sin evidencia de uso.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job deploy-test despliega al entorno de test.: 1
- Bibliotecas; lo desplegado es su app de demostración y documentación.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job dev-deploy despliega a dev.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow deploy_staging.yml despliega a staging.: 1
- Fork extendido de sshx sin evidencia de usuarios; las 21 ejecuciones fallaron.: 1
- Proyecto de equipo de 180 días sin evidencia de usuarios (probable proyecto académico).: 1
- Sitio web oficial de contenidos de Milvus, no una aplicación.: 1
- Actividad atípica: los últimos 100 commits se hicieron en un solo día (30 de bots) con un único autor.: 1
- Página de documentación de un paquete, no una aplicación.: 1
- Criterio 2: el workflow despliega a un entorno de demostración (job deploy-demo, App Engine de demostración), no a producción. Corregido el 2026-11-08 tras analizar sus fallos.: 1
- Documentación de MODX Revolution, no una aplicación.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow despliega el servidor de desarrollo (ServerDev).: 1
- Publica paquetes binarios en un servidor de descargas; no despliega una aplicación.: 1
- Sitio estático de contenidos (Hugo) de MoodleBox.: 1
- Proyecto integrador de curso.: 1
- Aplicación de liga privada sin web pública ni evidencia de usuarios.: 1
- Ritmo de commits atípico (3168 commits en 170 días, unos 19 diarios).: 1
- Producto autoalojado; el workflow candidato solo despliega su sitio web (deploy-website.yml).: 1
- Herramienta académica de un grupo de investigación sin web ni evidencia de uso.: 1
- Aplicación de escritorio; Ansible prepara entornos de compilación en CI.: 1
- Sitio web de contenidos de una iglesia (README de plantilla de Turborepo).: 1
- Proyecto de 72 días sin contribuidores registrados ni evidencia de usuarios.: 1
- App de Android; el despliegue es de su sitio web.: 1
- El workflow candidato solo sube la versión preliminar de la documentación.: 1
- Documentación de Nebari, no una aplicación.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job deploy-dev despliega a dev.: 1
- Sitio web y blog personal.: 1
- Proyecto de equipo sin web ni evidencia de usuarios.: 1
- Aplicación sin web ni evidencia de usuarios (proyecto personal).: 1
- Experimento personal de un agente de IA que apuesta, no una aplicación con usuarios.: 1
- Repositorio promocional con las 13 ejecuciones recientes fallidas; no hay despliegue completado.: 1
- Software que instalan terceros; el Ansible del workflow no despliega un servicio propio.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job deploy-test-scw despliega al entorno test.: 1
- Código de ejemplo de conferencias.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega a un entorno sandbox de Elastic Beanstalk.: 1
- Módulo/biblioteca; el despliegue en Vercel es de su documentación o playground.: 1
- Despliega solo a Cloudflare Pages (hosting estático): el paso «Deploy» usa wrangler-action con `pages deploy dist`. Detectado en la muestra de validación final (criterio 2).: 1
- Sitio estático (Gatsby).: 1
- Biblioteca; el despliegue en Fly.io es de su sitio y ejemplos.: 1
- Proyecto fusionado en otro repositorio y en proceso de archivo.: 1
- Proyecto personal sin web ni evidencia de usuarios (65 commits).: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow deploy_nightly.yml publica la versión nightly.: 1
- Declarado sin publicar ('not released!').: 1
- Repositorio de distribución de versiones premium, no una aplicación desplegada.: 1
- SDK de un protocolo (biblioteca); el workflow despliega servidores intermediarios del laboratorio, no una aplicación en uso.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow docker-stg.yaml despliega a staging.: 1
- Plantilla de despliegue de Django.: 1
- Sistema de notas de uso personal ('個人用').: 1
- Herramienta de instalación de oVirt.: 1
- Herramienta local; el workflow solo despliega el sitio web.: 1
- Planificador personal sin web ni evidencia de usuarios.: 1
- Sin descripción del producto ni evidencia de usuarios (README apunta a localhost).: 1
- Sitio de documentación (VitePress).: 1
- Framework de robótica; el despliegue es auxiliar, no la aplicación.: 1
- El workflow candidato construye imágenes AMI; no despliega una aplicación.: 1
- Herramienta de línea de comandos; el despliegue es de su sitio.: 1
- Proyecto personal de 2 personas sin web ni evidencia de usuarios (64 commits).: 1
- Sitio de documentación de Plausible Analytics (Docusaurus).: 1
- Blog de contenidos educativos, no una aplicación.: 1
- Proyecto de hackathon (Hack2Skill); todas las ejecuciones fallidas.: 1
- Proyecto de aficionados de 3 personas en una URL de Vercel autogenerada.: 1
- Proyecto personal de un solo autor (120 días) sin evidencia de usuarios.: 1
- Biblioteca; el despliegue es del showcase (demostración).: 1
- Biblioteca de componentes; el workflow despliega el showcase (demostración).: 1
- Las 32 ejecuciones recientes se omitieron (skipped): el despliegue no se ejecuta; 65 días de historia.: 1
- Software para que terceros lo instalen (self-hosted); el workflow no despliega un servicio propio en producción.: 1
- App de un solo autor generada con Anvil (80 días) sin evidencia de usuarios.: 1
- Documentación de Pupil Labs, no una aplicación.: 1
- Herramienta de pruebas de interoperabilidad; el despliegue sube un sitio de resultados.: 1
- MVP interno declarado ('Internal MVP') en una URL de Vercel autogenerada.: 1
- Proyecto de portafolio ('demonstrating modern backend development practices'), un solo autor.: 1
- Proyecto de equipo sin evidencia de usuarios; 27 de 28 ejecuciones recientes fallidas.: 1
- El Ansible del workflow monta el entorno de pruebas e2e en CI, no despliega.: 1
- Framework; el despliegue es de su sitio web/documentación.: 1
- Sistema operativo; el workflow candidato solo despliega las guías en el servidor web.: 1
- Sin README; sitio web de contenidos.: 1
- Genera y publica sitios de documentación, no una aplicación.: 1
- Proyecto demostrativo de patrones de microservicios ('to show a case'); además todas las ejecuciones se omiten.: 1
- Módulo de Nuxt; el despliegue es de su documentación.: 1
- Herramienta (stack de Ansible para WordPress); el workflow la prueba.: 1
- Proyecto de hackathon (EVE Hackathon).: 1
- Aplicación personal; la instancia desplegada es la demo.: 1
- Proyecto de curso (WBD).: 1
- Herramienta de instalación con Ansible; el workflow la prueba.: 1
- Proyecto de portafolio; las 38 ejecuciones recientes fallaron.: 1
- El despliegue es a hosting estático (Cloudflare Pages), equivalente a GitHub Pages.: 1
- Proyecto de un programa escolar de startups ('4세대 스타트업 프로젝트').: 1
- Demo ('Production demo on Azure') de 77 días.: 1
- Reproductor local; el despliegue es a hosting estático (Cloudflare Pages).: 1
- Prototipo de investigación de un solo contribuidor presentado como demo ('Live Demo').: 1
- Actividad no genuina: 1847 ejecuciones en 6 meses con solo 88 commits en total; README basado en un ejemplo de neuroglancer.: 1
- El workflow del dataset (`e2e-tests.yml`) son pruebas de extremo a extremo: instala Ansible y ejecuta `dev-server.playbook.yml --limit localhost` en el runner (environment `e2e_tests`); no despliega a producción (criterio 2). Revisión dirigida de workflows con nombre e2e/test/local.: 1
- README por defecto de create-next-app: no se puede confirmar el uso.: 1
- YAML no legible: 1
- Sistema de diseño (biblioteca de componentes y su documentación).: 1
- Proyecto individual sin web propia; no se pudo confirmar que esté en uso.: 1
- Herramienta de aprovisionamiento de estaciones de trabajo.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; publica la versión nightly.: 1
- Demos y aplicaciones de ejemplo de springdoc-openapi (README: 'Live demos and sample applications').: 1
- Portal de documentación de Nokia SR Linux, no una aplicación.: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job publish-test despliega al entorno de integración (int.yml).: 1
- Sin web ni evidencia de usuarios; 2 autores.: 1
- Declarado solo para desarrollo ('APENAS PARA DESENVOLVIMENTO').: 1
- Sitio estático de contenidos (manual en línea con VuePress), no una aplicación.: 1
- Sitio estático de materiales de curso universitario.: 1
- Sitio vitrina estático (Astro).: 1
- organización de tesis/proyectos académicos (Tesis-2026): 1
- Sitio estático (Jekyll) de un grupo universitario.: 1
- El workflow candidato solo despliega la documentación.: 1
- Lenguaje de programación personal ('It's mine'); no es una aplicación en uso.: 1
- Proyecto de 88 días sin evidencia de usuarios; todas las ejecuciones fallidas.: 1
- Sitio de un curso universitario (Universidad Tongji).: 1
- Sitio de fans no oficial de un autor; proyecto personal.: 1
- Herramienta (scripts de Ansible para VPN); el workflow la prueba.: 1
- README mínimo: no se puede confirmar qué es ni que esté en uso.: 1
- Prototipo de I+D declarado ('Early R&D').: 1
- Proyecto de tesis de grado (DATN: 'Đồ án tốt nghiệp').: 1
- Sitio de documentación del repositorio de paquetes de nginx.: 1
- El workflow del dataset (`ci.yml`) es CI (pruebas, validación de configuración y escaneo de CVE de las imágenes); no despliega. Las y=0 venían del paso «Build the images this deployment ships», que la regla tomaba por despliegue por la palabra «deployment» (criterio 2). Detectado en la muestra de validación dirigida (semilla 11).: 1
- Sitio de contenidos de un club, hecho por un club estudiantil de desarrollo (URL de Vercel autogenerada).: 1
- El workflow del dataset (`tpv.yml`) ejecuta `ansible-playbook --connection=local` en el runner para probar la configuración TPV en pull requests; no despliega a producción (criterio 2). Detectado al verificar el dataset v2.: 1
- Sistema de diseño (componentes y documentación), no una aplicación.: 1
- README por defecto de create-next-app; las 13 ejecuciones recientes fallaron.: 1
- Piloto personal del hogar con actividad atípica (4620 commits en 139 días).: 1
- Sitio de documentación de la API (api.vapor.codes), no una aplicación.: 1
- Recursos de diseño (CSS) y su pipeline de publicación, no una aplicación.: 1
- Declarado fuera de producción ('not in production').: 1
- Plantilla de proyecto AWS («trying to deploy website»).: 1
- Plugin de WordPress (biblioteca).: 1
- Sitio de marketing, blog y documentación.: 1
- El despliegue es de la documentación en hosting estático (Cloudflare Pages).: 1
- Backend del sitio de cumpleaños personal del autor.: 1
- Proyecto de 178 días en una URL de Vercel autogenerada, sin evidencia de usuarios.: 1
- Plantilla inicial ('Blueprint for a new Dextinity project').: 1
- Plantilla de aplicación ('Serverless App scaffold') en una URL de Vercel autogenerada.: 1
- Gestor de descargas de escritorio; el despliegue en Workers es de su documentación.: 1
- Proyecto de aprendizaje/portafolio ('the first app I built after learning Vue').: 1
- Construye imágenes de máquinas virtuales (OVA/AMI), no despliega una aplicación.: 1
- Proyecto de equipo estudiantil en una URL de Heroku autogenerada.: 1
- Herramienta personal de un solo autor (101 días) sin web pública declarada.: 1
- Herramienta; el workflow candidato solo despliega su sitio.: 1
- Proyecto de curso universitario (Software Practical Course, Universidad de Zúrich, 2026).: 1
- Sitio estático de contenidos (Astro + Markdown) sobre RTOS, no una aplicación.: 1
- Proyecto personal; las 40 ejecuciones recientes fallaron.: 1
- Depurador de escritorio; el despliegue es a hosting estático (Cloudflare Pages).: 1
- Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job deploy_dev despliega a dev.: 1
- Documentación oficial de Zettlr, no una aplicación.: 1

### Detalle

| Repositorio | Motivo |
|---|---|
| 0Mouse0/task-manager | Proyecto de curso (Diplomado de desarrollo Fullstack, Universidad Católica Boliviana). |
| 0xjeffro/astroclaw | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| 1ASI0657-2510-3586-Grupo3-EcoMovil/back-end-micro | Proyecto de curso universitario (código de curso 1ASI0657, grupo 3). |
| 1EdTech/openbadges-specification | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| 2060-io/hologram.zone-website | Sitio de marketing, no una aplicación. |
| 21Kurse/Lerp-Engine | Proyecto de 78 días sin evidencia de usuarios; las 13 ejecuciones fallaron. |
| 428lab/debug-shrine | Proyecto de laboratorio académico con tema de portafolio ('A Yotsuya-lab project', topic kojira-portfolio). |
| a-type/biscuits | El workflow candidato solo despliega la página de inicio. |
| abhishek-khadse/Trinetra-Sec | Proyecto personal de un solo autor sin evidencia de usuarios. |
| AbrahamSilverhand/EP3-DevOps | Evaluación de curso (EP3 DevOps). |
| aclemons/koinobori | más del 80 % de los commits recientes son automáticos (bots) |
| acteng/ate-api | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| activescott/serverless-aws-static-file-handler | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| adamjq/production-ready-serverless-nestjs | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| adcontextprotocol/adcp | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| ADFC-Hamburg/adfc-ansible | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| adii4040/chaiLM | Proyecto personal de un solo autor (78 días) sin evidencia de usuarios. |
| Adimac93/built-with-ai | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| Adithya-Adi/syncline | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| adorsys/status-list-server | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| ae-utbm/sith | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Aerotalk/EdgeStone_Backend | Un solo contribuidor sin evidencia de usuarios; las 93 ejecuciones recientes fallaron. |
| AET-DevOps26/team-devoops | Proyecto de equipo de un curso de DevOps (AET-DevOps26). |
| aeternity/superhero-ui | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; su 'producción' es GitHub Pages y el despliegue por SSH va solo a stage. |
| Aguafrommars/TheIdServer | Producto para que terceros lo instalen; el workflow despliega su instancia de demostración en Heroku. |
| Ahmed-Gamil-osman/763 | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| ai-on-gke/website | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| AI-READI/fairhub-pipeline | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| aiskendi/pencarimovie-server | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| aisystant/docs | Sitio de documentación de cursos (VitePress). |
| AkaWalle/VAI-DE-PIX | Aplicación de finanzas personales del autor; 49 de 52 ejecuciones fallidas. |
| AldaniP/Bookstore | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| AleksanderObuchowski/LabNotes | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| alexlipa91/nutmeg-flutter | Sin README ni descripción: no se puede confirmar el uso. |
| alfredshingai/SokoData | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| algoproclub/algopro-ide | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| alkem-io/client-web | Criterio 2 (solo producción): el workflow candidato despliega al sandbox (build-deploy-k8s-sandbox-hetzner.yml). |
| alkem-io/notifications | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow build-deploy-k8s-dev-hetzner.yml despliega a dev. |
| alkem-io/server | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow build-deploy-k8s-dev-hetzner.yml despliega a dev. |
| AllenNeuralDynamics/zombie | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| AltioraLabs/CapForge | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| Amith-Ganta/multimodal-rag-guardrails | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| anandav/PaperTrade | Simulador personal sin web pública ni evidencia de usuarios. |
| AnasAslam1908/url-shortener | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| anchapin/portkit | El servicio alojado se cerró ('The hosted service ... is shut down'). |
| andipaetzold/zwiftmap | más del 80 % de los commits recientes son automáticos (bots) |
| andreipradan/mainframe | Plataforma de automatización personal ('Personal automation and monitoring platform'). |
| andrewm4894/anomstack | YAML sin jobs |
| aniketjha348/intercept | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| AniMeaux/website | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| ankaboot-source/supabase-selfhost-ops | El workflow candidato hace un backup (release.yml); no despliega una aplicación. |
| Ankitmina25/FundRooms | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| anna-gubler/sopra-fs26-group-01-server | Proyecto de curso universitario (SoPra FS26, Universidad de Zúrich). |
| ansible/ansible.platform | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| antmicro/verible-indexer | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| AntonioAlbaladejo/credit-risk-engine | Proyecto de portafolio de un solo autor (modelo de scoring con sección de resultados). |
| anujaj13/ProjectPortfolio | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| anuzdevops/devops-ec2-deploy | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| aoibht/client-demonstration | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| apache/dolphinscheduler | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| arc42/trainings.arc42.org-site | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| archestra-ai/OpenAPPA | Biblioteca de guardrails; el workflow despliega una función auxiliar (appa-yell), no una aplicación en uso. |
| archi2305/DevWorkSpaceX | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| arehh04/travel-recovery-os | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| arturo-lang/pkgr.art | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| arusso-aboutcloud/Entra-Tracker | más del 80 % de los commits recientes son automáticos (bots) |
| Arx-Game/arxii | El workflow candidato solo valida los playbooks (ansible-lint y --syntax-check); no despliega. |
| ASL-LEX/SignTag | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Aurora-site/aurora | Un solo autor y dominio de pruebas (duckdns): sin evidencia de uso. |
| autosec-network/eaas | Proyecto de 3 personas en un dominio pages.dev, sin evidencia de usuarios. |
| AVIgo89/demo-cicd | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| aws-samples/aws-fault-injection-simulator-workshop-v2 | Aplicación de ejemplo de un taller de AWS. |
| aws-samples/sample-spec-driven-presentation-maker | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| aws-ug-manizales/Skorify_Backend | Proyecto de una comunidad de aprendizaje (AWS User Group Manizales) de 84 días sin evidencia de usuarios. |
| aws-ug-manizales/Skorify_Data | Proyecto de una comunidad de aprendizaje (AWS User Group Manizales) de 75 días. |
| Ayfri/Kore | Biblioteca Kotlin; el Worker desplegado es su sitio de documentación. |
| azrtydxb/Promptforge | Sin web ni evidencia de usuarios. |
| backstage/demo | Instancia de demostración (demo.backstage.io). |
| badges/shields | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| badgeteam/website | Sitio de documentación o estático, no una aplicación. (Hugo) |
| Balamurali-ai/Prajna | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| basicmachines-co/docs.basicmemory.com | Sitio de documentación. |
| bbondy/go-brianbondy | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| bcgov/biohubbc | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| bcgov/dep-public | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| bcgov/eagle-api | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| bcgov/eao-nginx | Criterio 2 (solo producción): según el README solo corre en el namespace dev de OpenShift. |
| bcgov/reserve-rec-admin | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| bcgov/traction | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| bcgov/weather-archive | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| BCochofelHomelab/homelab-proxmox-core | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| benwalsh/ealta | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| bervProject/InvitationAPI | más del 80 % de los commits recientes son automáticos (bots) |
| bervProject/tell-me-everything-api | Proyecto personal de un solo autor. |
| better-notify/better-notify | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| bifravst/aws-cdk-lambda-helpers | más del 80 % de los commits recientes son automáticos (bots) |
| bifravst/rest-echo | más del 80 % de los commits recientes son automáticos (bots) |
| bimvocado/Masil | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| binary-coffee-dev/dcs-frontend | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| bkfeinberg/route-forecast | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| bkumars22/SupplyChainPlatformProject | Proyecto de portafolio con demo; las 88 ejecuciones recientes fallaron. |
| blackfyre/wga | Las ejecuciones recientes se omitieron (skipped): el despliegue no se ejecuta. |
| bluebanquise/bluebanquise | Colección de roles de Ansible; el workflow prueba el despliegue de clústeres, no despliega una aplicación. |
| bluewave-labs/Checkmate | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega staging.checkmate.so y demo.checkmate.so (el job deploy-prod es la demo). |
| bmlt-enabled/bmlt-server | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| bokeh/demo.bokeh.org | Galería de demostraciones (demo.bokeh.org). |
| boltffi/boltffi | Biblioteca o herramienta; el workflow solo despliega su sitio de documentación. |
| bouine-cache/bouine | El workflow candidato empaqueta el chart de Helm (prerelease); no despliega. |
| bpowers/simlin | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| BrightSoftwares/blogpost-tools | Herramientas de automatización de blogs; 99 de 100 ejecuciones fallidas. |
| brokenhandsio/kiln | Generador de documentación (herramienta); lo desplegado es su sitio estático. |
| brown-ccv/cbc-website | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| brown-ccv/ccv-website | Sitio web de contenidos de un centro universitario, no una aplicación. |
| BruceAlmighty97/osai-trader | Proyecto personal de un solo autor (61 commits, 95 días) sin evidencia de usuarios. |
| bruits/sampo | Herramienta de línea de comandos (changelogs y versiones); el despliegue es auxiliar. |
| bzkf/fhir-to-lakehouse | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| bzkf/obds-to-fhir | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| cacaviana/petraplatform | SDK en etapa inicial (20 commits, 71 días), no una aplicación en uso. |
| calendar-team/calendar-frontend | más del 80 % de los commits recientes son automáticos (bots) |
| camthink-ai/wiki-documents | Sitio de documentación. |
| canada-ca/navigator | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job deploy-staging despliega a staging. |
| cannawen/dota-gsi-discord-bot | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| catalyst-cooperative/eel-hole | Prototipo declarado ('Frontend-only prototype'). |
| catholicbatman/CS618-videos | Proyecto de curso (CS618) con el README de la plantilla de Vite. |
| cbg-ethz/WisePulse | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| CBIIT/nci-webtools-dceg-ctb | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega a dev o qa (ramas *_dev y *_qa; sus 100 deployments registrados son dev y qa). |
| CCIP-App/Portal | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| ccrma/webchuck-ide | El despliegue a producción está comentado en el workflow (`node.js.yml`) y solo despliega la rama `dev` (rsync); las y=0 venían del paso «Build burnett01/rsync-deployments», que no despliega (criterio 2). Detectado al verificar el dataset v2. |
| cds-snc/cds-aws-lz | Infraestructura de cuentas de AWS (landing zone), no una aplicación. |
| CEckelberry/cole-resume-website | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| CENIA-DEV/multilingual-translator-app | Sin web ni evidencia de uso de la aplicación desplegada. |
| ChainSafe/forest-website | más del 80 % de los commits recientes son automáticos (bots) |
| ChernegaSergiy/moment-of-honor-content | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| ChhabhayaManan/Crime-Intelligence-System | Proyecto de portafolio de un solo autor sin evidencia de usuarios. |
| chrisns/linkedin-newsletter-rss | más del 80 % de los commits recientes son automáticos (bots) |
| chrisns/repomanager | más del 80 % de los commits recientes son automáticos (bots) |
| ChurchApps/Api | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| cilium/ariane | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| cisagov/XFD | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega a staging e integration. |
| CKStudentCouncil/Legislation | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| ckuijjer/expatcinema.com | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| cloudflare/moq-rs | Implementación de un protocolo; el despliegue en Fly.io es un relay de demostración. |
| CMSgov/bcda-app | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Code-4-Community/branch | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| codedthemes/berry-free-angular-admin-template | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| codedthemes/berry-free-react-admin-template | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| codedthemes/berry-free-vuetify-vuejs-admin-template | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| codedthemes/datta-able-free-react-admin-template | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| codedthemes/mantis-free-vuetify-vuejs-admin-template | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| codedthemes/materially-free-react-admin-template | Plantilla de administración (template). |
| codeforamerica/vita-min | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| codykayak/AiBhive | Herramientas internas sin evidencia pública de la organización ni de usuarios. |
| cogini/phoenix_container_example | Ejemplo/plantilla ('Production-quality example for Elixir/Phoenix'). |
| ColoredCow/portal | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Commit451/skyhook | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| compdemocracy/polis | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| concord-consortium/rigse | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| conda-forge/conda-forge-webservices | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| connve/flowgen | El workflow candidato solo despliega la documentación (Cloudflare Pages). |
| consuldemocracy/installer | Instalador; el workflow prueba la instalación, no despliega una aplicación en uso. |
| corderogerardo/noofficelocation | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| CornellNLP/ConvoKit | Toolkit de investigación; el despliegue por rsync es de su sitio de documentación. |
| counsel-health/counsel-studio-example-apps | Aplicaciones de ejemplo (sample apps). |
| Cour-de-cassation/judilibre-search | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| creativeprojects/resticprofile | Biblioteca o herramienta; el workflow solo despliega su sitio de documentación. |
| crhntr/playground | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| cubeplexai/cubeloop | Framework; el workflow solo despliega su documentación (Cloudflare Pages). |
| cybozu-go/neco-gcp | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| Dahllyuhrah-Dahllyuhk/BE | Proyecto de equipo sin evidencia de usuarios (121 commits). |
| dahyorr/DevUtils | YAML sin jobs |
| dairussi/SolidarityConnection | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| dam5s/somanyfeeds.fs | Agregador personal para el sitio del autor (damo.io), no una aplicación con usuarios. |
| dante-gpu/dantegpu-core | Proyecto de 2 personas sin evidencia de uso; las 27 ejecuciones recientes fallaron. |
| dasch-swiss/dsp-repository | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| dash0hq/otelbin | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| databendlabs/helm-charts | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| DataDog/stickerlandia | Aplicación de referencia de Datadog sin evidencia de uso en producción. |
| DataIntegrationGroup/DataIntegrationEngine | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| DataIntegrationGroup/OcotilloUI | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| DataLinkDC/dinky | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| Dayvhiid/CareerPilot | Proyecto personal sin README ni evidencia de uso (34 commits). |
| DDD-Community/DDD-12-GROWIT-BE | Proyecto de un grupo de estudio (DDD 12.ª generación, equipo web 1). |
| DedRozs/FullStackPortfolio | Sitio de portafolio personal. |
| deep-learning-indaba/Baobab | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow staging.yml despliega a staging. |
| deepple-dev/deepple-api | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| DemocracyClub/dc-data-baker | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| department-for-transport-BODS/publish-devolved-bus-registration-data | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| depromeet/globber-client | Proyecto de equipo de un club de formación (Depromeet, 17.ª generación). |
| derekantrican/ytsubs | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| dev-protocol/khaos-functions | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| developmentseed/eoapi-cdk | Biblioteca de constructs de CDK, no una aplicación. |
| developmentseed/eoapi-template | Plantilla (template repository). |
| devmount/devmount.com | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| devmount/SongDrive | Sin web ni evidencia de uso; las 15 ejecuciones recientes fallaron. |
| devmount/third-stats | Complemento de Thunderbird; el despliegue por rsync es de su sitio web. |
| Diamondstar-Mods/Minecraft-Command-Maker | Mod de Minecraft; el despliegue en Vercel es de su wiki. |
| diconium/ethereal-nexus | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow dashboard-dev.yml despliega al entorno playground. |
| dievri/az-micro-app | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| digital-technologies-teachers-aotearoa/ams | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| dima74/Wikipedia-Yofication | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| diogomatoschaves/MyCryptoBot | Plataforma para ejecutar bots propios; no hay evidencia de una instancia en uso. |
| dip497/hivemind | Contenido declarado como generado por IA y ritmo atípico (1542 commits en 164 días); lo desplegado es el sitio. |
| ditatompel/insights | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| DIVD-NL/web-www-v2 | Sitio web estático y el workflow candidato publica en staging. |
| DivyaAI-Engineer/RFP_draft_agent | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| DivyanshBodhale/Wanderlust-DevOps- | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| dkplusui/dk-plus-ui | Biblioteca de componentes Vue; el despliegue es de su sitio de documentación. |
| docknetwork/dock-substrate | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| docwho2/java-chime-voicesdk-sma | más del 80 % de los commits recientes son automáticos (bots) |
| DogerRain/HelloCoder | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| dorylab/dory | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega el entorno beta de la web. |
| dperez4787/linear-example | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| duhitsahmad/pearls-aqi-predictor-final | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| dump-hr/futsal-app | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| dwyl/auth | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| dwyl/imgup | Aplicación de aprendizaje/demostración de la organización dwyl; las 13 ejecuciones recientes fallaron. |
| dxe/adb | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| ebbba-org/ansible-role-bigbluebutton | Rol de Ansible (herramienta); el workflow lo prueba, no despliega una aplicación. |
| eclipse-basyx/charts | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| edenmmn4-eng/eden-sovereign | Sin README; proyecto personal de un solo autor (82 días). |
| Eduhn26/Truco-Paulista2026 | Proyecto personal de un solo autor sin evidencia de usuarios. |
| eegmanylabs/eegmanylabs-org | Sitio web informativo de un consorcio de investigación, no una aplicación. |
| egovernments/Citizen-Complaint-Resolution-System | El workflow del dataset (`local-setup-ci.yaml`) es CI: ejecuta `ansible-playbook` contra `localhost` (`-c local`) para probar los playbooks; no despliega a producción (criterio 2). Detectado al verificar el dataset v2 (filas de pull_request con y=0). |
| elan-ev/tobira | Criterio 2 (solo producción): el workflow despliega instancias de prueba por rama, no producción. |
| elsa-hanke/elsa-backend | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| ENDARTStudios/Auto-Trader | Proyecto personal (trading simulado) con la mayoría de ejecuciones omitidas. |
| ensolabs/webflow-markdown | Utilidad pequeña (37 commits) sin web ni evidencia de usuarios. |
| Enterprise-CMCS/managed-care-review | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| ericvanm/fullstack_open_par11_based_part6 | Ejercicio del curso Full Stack Open. |
| espoon-voltti/nutakortti | más del 80 % de los commits recientes son automáticos (bots) |
| espoon-voltti/vekkuli | más del 80 % de los commits recientes son automáticos (bots) |
| eternidad475/luks-professional | El README no corresponde al proyecto desplegado: no se puede confirmar qué es ni que esté en uso. |
| ever-co/ever-works | Las ejecuciones recientes se omitieron (skipped): el despliegue no se ejecuta. |
| everycure-org/matrix | El workflow candidato (docs-deploy.yml) solo despliega la documentación, no la aplicación. |
| fabrica-bayarea/Sprint-Tracker | Tablero Kanban genérico sin evidencia de usuarios (frontend en una URL de Vercel autogenerada). |
| fabrica-bayarea/Tutor | Sin web ni evidencia de usuarios; README de configuración del entorno de desarrollo. |
| facereguniversal/face-reg | Organización de un solo contribuidor sin evidencia de usuarios; frontend en una URL de Vercel autogenerada. |
| Fachschaftsrat-Informatik-FH-Dortmund/fsrfb4.de-mkdocs | Sitio de documentación o estático, no una aplicación. (MkDocs) |
| fahadysf/nova-ve | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| farrrahhh/AplikasiPembelajaranASD | Aplicación de aprendizaje de un solo autor (93 días), probable proyecto de estudiante. |
| Fatal1ty/mashumaro | Biblioteca o herramienta; el workflow solo despliega su sitio de documentación. |
| FatalDecomp/ROLLER | Proyecto de ingeniería inversa de un juego; el despliegue publica un build estático para el navegador. |
| fbsamples/fbrell | Organización de ejemplos de Facebook (fbsamples): entorno de exploración del SDK. |
| FelidaeFundConservation/wildepod.org | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| FernandoMartinez018/itinerarios-itinerary-service | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| Fez248/running-hackathon | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| fgosc/fgosccalc | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| FHIR/genomics-operations | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| fielddaylab/fielddaysite | Sitio web de contenidos del laboratorio, no una aplicación. |
| fielddaylab/wake | Juego educativo; el despliegue publica un build estático WebGL. |
| filiphsps/commerce | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| finnishtransportagency/viite | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| FINTLabs/fint-adapter-felles-kodeverk | Máximo de 5 por organización: de FINTLabs se eligen los 5 con más ejecuciones. |
| FINTLabs/fint-admin-portal-frontend-v2 | Máximo de 5 por organización: de FINTLabs se eligen los 5 con más ejecuciones. |
| FINTLabs/fint-betaling-backend | Máximo de 5 por organización: de FINTLabs se eligen los 5 con más ejecuciones. |
| FINTLabs/fint-kontroll-device-catalog | Máximo de 5 por organización: de FINTLabs se eligen los 5 con más ejecuciones. |
| FINTLabs/fint-kontroll-resource-catalog | Máximo de 5 por organización: de FINTLabs se eligen los 5 con más ejecuciones. |
| FINTLabs/fint-kontroll-role-catalog | Máximo de 5 por organización: de FINTLabs se eligen los 5 con más ejecuciones. |
| FINTLabs/fint-kontroll-user-factory | Máximo de 5 por organización: de FINTLabs se eligen los 5 con más ejecuciones. |
| fjelltopp/adx_develop | Entorno de desarrollo del AIDS Data Repository, no la aplicación desplegada. |
| flirtual/flirtual | más del 80 % de los commits recientes son automáticos (bots) |
| flock-community/aigentic | Biblioteca Kotlin; el workflow solo despliega su sitio web. |
| flock-community/wirespec | El job candidato (publish-docs) solo publica la documentación. |
| FoundOne1/docker-app-repo | Demostración de un pipeline CI/CD para una app Node.js de ejemplo. |
| fraarrmat11/MS-SIMULATION | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| franciscovaleromartin/graphmycode | Aplicación que se ejecuta solo en el navegador; el despliegue publica un frontend estático. |
| FredrikAlmen93/Mail-Service | Microservicio de un proyecto de webshop de formación, sin evidencia de usuarios. |
| freelawproject/doctor | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| fribyte-code/fribyte.no | Sitio estático (Zola). |
| frostbase-dev/frostbase | El workflow candidato solo despliega previews (entorno preview). |
| furkankly/rataflow | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| furkankly/zoetrope | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| gardenlinux/gardenlinux-nvidia-installer | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| garrying/OCADU-Illustration-Theme | más del 80 % de los commits recientes son automáticos (bots) |
| Garudex-Labs/caracal | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| GauthierRobert/Koval | Sin README ni descripción: no se puede confirmar que esté en uso. |
| GDATASoftwareAG/vaas-helm | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| gdg-hongik-univ/gdsc-server | Sin README ni web: no se puede confirmar el uso. |
| geekzter/azure-minecraft-docker | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| geesaladurgaakhil/gcp8ambatch | Apuntes de un curso de GCP (lote 'gcp8ambatch'). |
| gemini-hlsw/lucuma-apps | Criterio 2 (solo producción): el workflow del dataset solo despliega a las apps de Heroku observe-dev-* y explore-gemini-dev (entorno «development»); producción se promueve fuera del workflow. Detectado en la muestra de y=0 con semilla 2026. |
| gemini-hlsw/lucuma-odb | Criterio 2 (solo producción): el workflow del dataset solo despliega a las apps de Heroku *-dev (entorno «development»); producción se promueve fuera del workflow. Detectado en la muestra de y=0 con semilla 2026. |
| gemini-hlsw/scheduler | Criterio 2 (solo producción): la organización despliega desde CI solo a development (ver lucuma-apps y lucuma-odb) y el 92 % de las ejecuciones se omiten. |
| getsentry/firetower | más del 80 % de los commits recientes son automáticos (bots) |
| goadesign/goa.design | Sitio web estático (Hugo) del proyecto Goa, no una aplicación. |
| govtech-bb/infra-prototypes | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| govuk-one-login/lambda-frontend-starter | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| govuk-one-login/txma-audit | Criterio 2 (solo producción): el workflow publica en las cuentas build/dev de GOV.UK One Login; la promoción a producción la hace AWS CodePipeline fuera de GitHub Actions. |
| govuk-one-login/txma-ticf-integration | Criterio 2 (solo producción): el workflow publica en las cuentas build/dev de GOV.UK One Login; la promoción a producción la hace AWS CodePipeline fuera de GitHub Actions. |
| grcengineering/gigachad-grc | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| groupdocs-redaction/GroupDocs.Redaction-Docs | Sitio de documentación estático. |
| groupdocs-signature/GroupDocs.Signature-Docs | Sitio de documentación o estático, no una aplicación. |
| groupdocs-viewer/GroupDocs.Viewer-Docs | Fuentes de documentación estática de GroupDocs.Viewer. |
| groupdocs-watermark/GroupDocs.Watermark-Docs | Sitio de documentación estático. |
| GscDtAnalytic/LedgerCopilot | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| GuardBench/guardbench-backend | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| guy-dav/ci_cd_basic_project | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| h36yang/Avalon-Engine-V2 | Proyecto de aficionados sin dominio propio ni evidencia de usuarios. |
| HackRU/HackRU-Backend | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| hamcoh/sopra-fs26-group-07-server | Proyecto de curso universitario (sopra-fs26, Universidad de Zúrich). |
| hardbyte/netchecks | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| HarpyTech/fintrackr | Proyecto de un solo autor reciente sin evidencia de usuarios. |
| heediq/heediq-infra | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| hello-nrfcloud/backend | más del 80 % de los commits recientes son automáticos (bots) |
| hello-nrfcloud/map-backend | más del 80 % de los commits recientes son automáticos (bots) |
| hello-ulises/ulises.us | Sitio web personal. |
| Helpful-Places/dtpr | Sistema de diseño y sitio de contenidos (taxonomía visual), no una aplicación. |
| henryonai/saas-backend-v2 | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| hernangonzalez93/Test_Enhancement | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| hetznercloud/hcloud-cloud-controller-manager | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| himanshu003388/Stadium_IQ | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| HLTech/judge-d | más del 80 % de los commits recientes son automáticos (bots) |
| hongsoohyuk/kotlin-spring | Repositorio de práctica sin README ni descripción (28 commits). |
| hotline-webring/hotline-webring | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| hounna19/babi | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| huettenbau-oberi/website | El workflow candidato restaura un backup (restore.yaml); no despliega la aplicación. |
| hunmer/mira | El workflow candidato solo despliega la landing page. |
| HXMAN76/git0 | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| hyggg222/ise-quiz-drill | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| HyperBDR/docs | Sitio de documentación estático (VuePress). |
| IATI/validator-services | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| Icehunter/dune-admin | Criterio 2 (hosting estático): el workflow solo despliega el frontend a Cloudflare Pages, no una aplicación. |
| icerpc/hello | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| igou-io/igou-ansible | más del 80 % de los commits recientes son automáticos (bots) |
| ilios/lti-server | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| IlliaSytchevv/LogisticsPlatform | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| ilogs-mx/landing-page | Landing page estática (Astro). |
| ilteoood/sesamo-backend | README mínimo: no se puede confirmar que la aplicación esté en uso. |
| InBrowserApp/InBrowserApp | Herramientas que se ejecutan solo en el navegador; el despliegue publica un sitio estático sin backend. |
| InKCre/impl-ts | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| inline-chat/inline | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| Innovar-Healthcare/bridgelink-container | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| insideout10/wordlift-plugin | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| inu-appcenter/inu-portal-server | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| ipeirotis-org/scholar_update | Script personal que genera un JSON con las publicaciones del autor. |
| ipfs/service-worker-gateway | Criterio 2 (solo producción): el workflow candidato es deploy-to-staging.yml (environment staging). |
| irfanadziri/respond-io-devops-assessment | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| ishaan-arora-1/gumby | Sin README ni descripción; un solo autor y 90 días: no hay evidencia de aplicación en uso. |
| ivanoskytan/temuka-main-api-service | Proyecto personal de un solo autor sin web ni evidencia de usuarios. |
| JabRef/JabRefOnline | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| jamiedavenport/capd | Aplicación de macOS; el despliegue es de su sitio de documentación. |
| jamktiko/cooked | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| janosrusiczki/rusiczki.net | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| janzarsky/scout-planner | más del 80 % de los commits recientes son automáticos (bots) |
| JasperFx/polecat | Biblioteca o herramienta; el workflow solo despliega su sitio de documentación. |
| JasperVanDenBosch/electrotime | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| JaVi57860eR/WlVIZC1Y | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| jaydee829/shelfwright | Proyecto personal de un solo autor sin evidencia de usuarios. |
| jellyfin/jellyfin-chromecast | Receptor web que se ejecuta en el dispositivo; el despliegue publica archivos estáticos. |
| jenkauppila/mechanic_shop_api | API de ejemplo de formación (taller mecánico) sin usuarios reales. |
| jfortner8/archive-api | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| JGtm/LevelUp | El despliegue es la demo pública (demo.lvelup.info). |
| jlesquembre/clj-nix | Biblioteca o herramienta; el workflow solo despliega su sitio de documentación. |
| johntoby/borderless-items-manager | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| jonasbisang/sopra-fs26-group36-server | Proyecto de curso universitario (SoPra FS26, Universidad de Zúrich). |
| JoseScript7/Tara | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| jtaeubrich/Spielanalyse | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| justfreshsky-jpg/CAPRSearch | Proyecto experimental con el acceso público pausado ('public acquisition paused'). |
| Jwongjs/MediSage | Proyecto de portafolio sin evidencia de usuarios. |
| k0rdent/kof | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| kalbasit/ncps | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| karlitos1337/5d | Proyecto teórico personal (texto sobre potencial humano), no una aplicación en uso. |
| kernelci/kernelci-project | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| keyteki/keyteki | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| kguardian-dev/kguardian | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| khill1269/servalsheets | Las 15 ejecuciones recientes se omitieron (skipped): el despliegue no se ejecuta. |
| khoingodev/Sfinity_MobileApp | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| Kiln-AI/Kiln | Aplicación de escritorio y biblioteca; el workflow despliega un sitio auxiliar, no la aplicación. |
| kiruna-labs/petal | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| kkcc2013-arch/mineGo | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| knowsex/knowsex.github.io | Sitio estático de contenidos (Astro). |
| kodehat/portkey | El despliegue en Fly.io es la demo pública (demo.portkey.page). |
| konflux-ci/integration-service | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| konjoinfinity/songscraper | Las 15 ejecuciones recientes se omitieron (skipped): el despliegue no se ejecuta. |
| KrChiranjeevi/e-commerce | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| Kuadrant/kuadrant-operator | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| kubeshop/testkube-thirdparty-artifacts | Artefactos de instalación (imágenes y charts), no una aplicación desplegada. |
| kwaroran/Risuai | El despliegue es a hosting estático (Cloudflare Pages o similar), equivalente a GitHub Pages. |
| kyanHarnum/asf-stac-duckdb | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| Kyguyog/Knowwhere | Sitio de juego hecho con un amigo, declarado 'vibe-coded'; no es una aplicación en uso. |
| lalith-99/nimbus-app | Proyecto de portafolio de un solo autor sin evidencia de usuarios. |
| LalitMaganti/syntaqlite | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| laminlabs/lamin-blog | Blog, no una aplicación. |
| lAnubisl/LostFilmTorrentsFeed | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| last9/mithai | Framework; el workflow solo despliega su documentación (Cloudflare Pages). |
| le8433622/vifixa-ai-business-package | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| leaningtech/labs | Sitio de documentación y blog de Leaning Technologies, no una aplicación. |
| learningeconomy/LearnCard | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| ledaibk45/dinky | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| Legal-Terminus/legalterminus | Sin web ni descripción del uso: no se puede confirmar que esté en producción. |
| liguobao/HouseSearch | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| lism-css/core | Framework CSS; el despliegue es de su sitio de documentación. |
| liun777/sopra-fs26-group-26-server | Proyecto de curso universitario (SoPra FS26, Universidad de Zúrich). |
| LiveSplit/LiveSplitOne | Herramienta que se ejecuta solo en el navegador; el despliegue publica un build estático sin backend. |
| livrasand/gitGost | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega al entorno Preview de Fly.io. |
| LMol-4/freewrite-web | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| loaighoraba/dashboard | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| LocalNewsImpact/MizzouNewsCrawler | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| localstack-samples/localstack-swag-store | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| localstack-samples/sample-loan-broker-stepfunctions-lambda | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| Los-Ingenieros-Del-Prompt/Auth_Azar_Cafetero | Proyecto de equipo estudiantil (46 commits, 73 días) sin evidencia de usuarios. |
| lsst/qserv | El job candidato publica el chart de Helm; no despliega a un entorno de aplicación. |
| luanaf4/cloud-serverless-checkpoint1 | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| lumigo-io/opentelemetry-java-distro | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| M-873/AutoOD | Proyecto personal de un solo autor sin evidencia de usuarios. |
| MaciejBuczek/gm-toolset | Sin README ni descripción útil; proyecto personal de 2 personas sin evidencia de uso. |
| Manavarya09/AAN | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| MaricBoris/sopra-fs26-group-14-server | Proyecto de curso universitario (SoPra FS26, Universidad de Zúrich). |
| MarioDiekmann/NewsInsight | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| marsyg/TraceDiff | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| martinellich/jtaf4 | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job deploy-test despliega al entorno de test. |
| mathematica-pub/frontend-shared-packages | Bibliotecas; lo desplegado es su app de demostración y documentación. |
| Mathoelz/CollectionHub | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| matryer/xbar | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| MaxenceRault/biirb | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| MaxVast/contact-form-app | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| mc-wiki/mcw-calc | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| mecanica-dm/mecanicadm-k8s-v3 | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| memser-spaceport/pln-directory-portal | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job dev-deploy despliega a dev. |
| Menschlichkeit-Osterreich/menschlichkeit-oesterreich | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Metaculus/metaculus | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow deploy_staging.yml despliega a staging. |
| metaplex-foundation/kinobi | Biblioteca o herramienta; el workflow solo despliega su sitio de documentación. |
| metilda-uw/metilda | YAML sin jobs |
| MEYD-605/maw-board | Fork extendido de sshx sin evidencia de usuarios; las 21 ejecuciones fallaron. |
| mhuy07092004/Real-Estate-Valuation-Narrative-Generator | Proyecto de equipo de 180 días sin evidencia de usuarios (probable proyecto académico). |
| MiCHaeLjerEmI50928aS/US7x7HXY | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| MigrationGFA/businesslms | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| milvus-io/milvus.io | Sitio web oficial de contenidos de Milvus, no una aplicación. |
| ministryofjustice/CFO-DataManagementSystem | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| mishrasanjeev/grantex | Actividad atípica: los últimos 100 commits se hicieron en un solo día (30 de bots) con un único autor. |
| moaidmoatasem/cherenkov-professional | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| mobitouchOS/MaIN.Docs | Página de documentación de un paquete, no una aplicación. |
| mobs-lab/epistorm-dashboard | Criterio 2: el workflow despliega a un entorno de demostración (job deploy-demo, App Engine de demostración), no a producción. Corregido el 2026-11-08 tras analizar sus fallos. |
| mocky-balboa/mocky-balboa | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| modelpack/model-csi-driver | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| modx-pro/Docs | Documentación de MODX Revolution, no una aplicación. |
| moeru-ai/airi | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow despliega el servidor de desarrollo (ServerDev). |
| moetayuko/openwrt-passwall-build | Publica paquetes binarios en un servidor de descargas; no despliega una aplicación. |
| MonsJovis/monsjovis.com | más del 80 % de los commits recientes son automáticos (bots) |
| moodlebox/moodlebox.net | Sitio estático de contenidos (Hugo) de MoodleBox. |
| MoritzDav/sopra-fs26-group-04-server | Proyecto de curso universitario (SoPra FS26, Universidad de Zúrich). |
| morningstarxcdcode/ZeroDayRadar | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| MotoRepSystem/Proyecto_de_integrador_-aplicaci-n_web- | Proyecto integrador de curso. |
| movahedan/monobun | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| mpw5/wheres-my-vds-team | Aplicación de liga privada sin web pública ni evidencia de usuarios. |
| mrmartineau/Otter | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| msantoria/mlb-prediction-app | Ritmo de commits atípico (3168 commits en 170 días, unos 19 diarios). |
| msgbyte/tianji | Producto autoalojado; el workflow candidato solo despliega su sitio web (deploy-website.yml). |
| MuhammmadAwais/Integri-Admin-Panel | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| MukundaKatta/voiceagent | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| MyersResearchGroup/SeqImprove | Herramienta académica de un grupo de investigación sin web ni evidencia de uso. |
| MythTV/mythtv | Aplicación de escritorio; Ansible prepara entornos de compilación en CI. |
| myungmoon-dev/luv | Sitio web de contenidos de una iglesia (README de plantilla de Turborepo). |
| Nahtuna/Finvista | Proyecto de 72 días sin contribuidores registrados ni evidencia de usuarios. |
| NaoDekoNeko/thesis-rag-microservice | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| natinael96/sinq | App de Android; el despliegue es de su sitio web. |
| nationalarchives/ds-caselaw-ingester | más del 80 % de los commits recientes son automáticos (bots) |
| naturebase-app/tnc-blue-carbon-cost-tool | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| nearai/cloud-api | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| nebari-dev/jhub-apps | El workflow candidato solo sube la versión preliminar de la documentación. |
| nebari-dev/nebari-docs | Documentación de Nebari, no una aplicación. |
| Necmttn/livetrace | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| neizsche/canihavesex.today | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| NelsonMeier/sopra-fs26-group-34-server | Proyecto de curso universitario (SoPra FS26, Universidad de Zúrich). |
| Netcracker/qubership-jaeger | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| NewWave4Org/NewWave4.org-frontend-new | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| ngutech21/vipr-wallet | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job deploy-dev despliega a dev. |
| nhoizey/nicolas-hoizey.com | Sitio web y blog personal. |
| Ni3een/CORTEXAI-Multi-Ai-Agent | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| nicolas-vmaria/SmartCart | Proyecto de equipo sin web ni evidencia de usuarios. |
| nicolasances/tome | Aplicación sin web ni evidencia de usuarios (proyecto personal). |
| Nicool4s19/Devops-Front | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| niemiecjakub/no-more-bets | Experimento personal de un agente de IA que apuesta, no una aplicación con usuarios. |
| NIH-NCPI/locutus | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| niklaserikssoon/K5U1-niklas | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| nirholas/crypto-vision | Repositorio promocional con las 13 ejecuciones recientes fallidas; no hay despliegue completado. |
| nix-community/noogle | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| NNTmux/newznab-tmux | Software que instalan terceros; el Ansible del workflow no despliega un servicio propio. |
| noddle-dev/noddle-draw | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| noi-techpark/opendatahub-timeseries-writer | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job deploy-test-scw despliega al entorno test. |
| nokia-steward/SReXperts | Código de ejemplo de conferencias. |
| nomadkaraoke/karaoke-gen | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| nornagon/cdda-guide | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| Northeastern-Electric-Racing/FinishLine | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; despliega a un entorno sandbox de Elastic Beanstalk. |
| nuxt-modules/shopify | Módulo/biblioteca; el despliegue en Vercel es de su documentación o playground. |
| OasisDEX/summerfi-monorepo | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| obbyworld/obby | Despliega solo a Cloudflare Pages (hosting estático): el paso «Deploy» usa wrangler-action con `pages deploy dist`. Detectado en la muestra de validación final (criterio 2). |
| OE-Japan/oe-japan-cms | Sitio estático (Gatsby). |
| ogrodnek/pyview | Biblioteca; el despliegue en Fly.io es de su sitio y ejemplos. |
| ohcnetwork/leaderboard | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| OIerDb-ng/OIerDb-data-generator | Proyecto fusionado en otro repositorio y en proceso de archivo. |
| omarwae64/762 | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| Omiiii04/IITB-Hackathon | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| OnTime-SE-G/ontime-g2 | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| ooni/devops | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| ooye-sanket/oyeswap | Proyecto personal sin web ni evidencia de usuarios (65 commits). |
| open-ews/open-ews | más del 80 % de los commits recientes son automáticos (bots) |
| Open-Finance-Lab/AgenticTrading | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| OpenCircuits/OpenCircuits | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow deploy_nightly.yml publica la versión nightly. |
| OpenConceptLab/oclweb3 | Declarado sin publicar ('not released!'). |
| OpenSID/rilis-premium | Repositorio de distribución de versiones premium, no una aplicación desplegada. |
| openwallet-foundation-labs/tsp | SDK de un protocolo (biblioteca); el workflow despliega servidores intermediarios del laboratorio, no una aplicación en uso. |
| OpenZeppelin/ui-builder | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow docker-stg.yaml despliega a staging. |
| Opetushallitus/aoe | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| Opetushallitus/tutu-kasittely | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| opszero/template-helm-django | Plantilla de despliegue de Django. |
| orbital-skylab/skylab-backend | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| organic-san/skynote-cards | Sistema de notas de uso personal ('個人用'). |
| oskarissimus/korczak-xyz | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| oslokommune/okdata-maskinporten-api | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| OsProgramadores/op-website-hugo | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| ostat/gridfinity_extended_openscad | El despliegue es a hosting estático (Cloudflare Pages o similar), equivalente a GitHub Pages. |
| otwcode/otwarchive | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| oVirt/ovirt-hosted-engine-setup | Herramienta de instalación de oVirt. |
| OxyHQ/Homiio | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| ozgunbal/ozgunbal-website | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| pagopa/developer-portal-cms | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| pagopa/oneidentity | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| panguard-ai/panguard-ai | Herramienta local; el workflow solo despliega el sitio web. |
| papesce/balanced-work-life | Planificador personal sin web ni evidencia de usuarios. |
| paulthanson082-glitch/friendly-outlaw | Sin descripción del producto ni evidencia de usuarios (README apunta a localhost). |
| pawtograder/platform | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| pelazas/renderpr | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| PenguLoader/docs | Sitio de documentación (VitePress). |
| Peppy-bot/peppy | Framework de robótica; el despliegue es auxiliar, no la aplicación. |
| percona/pmm | El workflow candidato construye imágenes AMI; no despliega una aplicación. |
| perldoc-jp/perldoc.jp | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| persistentepiphany/preventine_healthcare_hackathon | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| pgr866/msc-soccer-project | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| pivoshenko/kasetto | Herramienta de línea de comandos; el despliegue es de su sitio. |
| Pixie2468/dearai-backend | Proyecto personal de 2 personas sin web ni evidencia de usuarios (64 commits). |
| piyush1457/DocAiApp-AI-Powered-Document-Multimedia-Q-A | Proyecto de portafolio sin evidencia de usuarios. |
| pkmariya/learn-rag | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| plabayo/rama | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| plausible/docs | Sitio de documentación de Plausible Analytics (Docusaurus). |
| playfulprogramming/playfulprogramming | Blog de contenidos educativos, no una aplicación. |
| plenoai/pleno-anonymize | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| pomerium/verify | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| pongstylin/tactics | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| potomak/drawbang | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| pramit091104/Hack2Skill-Repo | Proyecto de hackathon (Hack2Skill); todas las ejecuciones fallidas. |
| Predictaball/predictaball | Proyecto de aficionados de 3 personas en una URL de Vercel autogenerada. |
| PreethamNimmagadda02/CareerOps | Proyecto personal de un solo autor (120 días) sin evidencia de usuarios. |
| primefaces-extensions/primefaces-extensions | Biblioteca; el despliegue es del showcase (demostración). |
| primefaces/primefaces | Biblioteca de componentes; el workflow despliega el showcase (demostración). |
| Prince364133/adhocx | Las 32 ejecuciones recientes se omitieron (skipped): el despliegue no se ejecuta; 65 días de historia. |
| print-Ram/Vaidhyashala | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| PrivadoID/issuer-node | Software para que terceros lo instalen (self-hosted); el workflow no despliega un servicio propio en producción. |
| PROCEED-Labs/proceed | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Programmer-Shubh/Programmer-Shubh-rapython | App de un solo autor generada con Anvil (80 días) sin evidencia de usuarios. |
| progwise/timebook | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| projectsplit/SplitServer | Sin README ni descripción: no se puede confirmar que esté en uso. |
| PRX/classy-toolkit | más del 80 % de los commits recientes son automáticos (bots) |
| PRX/cloudwatch-toolkit | más del 80 % de los commits recientes son automáticos (bots) |
| PRX/Infrastructure | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| PRX/zendesk-toolkit | más del 80 % de los commits recientes son automáticos (bots) |
| pubky/pubky-app | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Pulse-Omerlo/Pulse | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| pupil-labs/pupil-docs | Documentación de Pupil Labs, no una aplicación. |
| python-poetry/website | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| pythoncanarias/pycan-web | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| quan1918/task-management-system | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| quic-interop/quic-interop-runner | Herramienta de pruebas de interoperabilidad; el despliegue sube un sitio de resultados. |
| QwikDev/qwik | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| radcrew/real-estate-consultant | MVP interno declarado ('Internal MVP') en una URL de Vercel autogenerada. |
| raduplacinta99/TrimURL | Proyecto de portafolio ('demonstrating modern backend development practices'), un solo autor. |
| rajat3470/OurBlock | Proyecto de equipo sin evidencia de usuarios; 27 de 28 ejecuciones recientes fallidas. |
| ral-facilities/datagateway | El Ansible del workflow monta el entorno de pruebas e2e en CI, no despliega. |
| RamSuryaCH/cloudpulse-aws | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| remails-com/remails | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| rememberiran/rememberofx | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| remorses/spiceflow | Framework; el despliegue es de su sitio web/documentación. |
| remoweirich/sopra-fs26-group-15-server | Proyecto de curso universitario (SoPra FS26, Universidad de Zúrich). |
| replane-dev/replane | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Rest-coder-academy/trca | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| rewiringamerica/api.rewiringamerica.org | más del 80 % de los commits recientes son automáticos (bots) |
| ridatadiscoverycenter/riddc-dashboard | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| RIOT-OS/RIOT | Sistema operativo; el workflow candidato solo despliega las guías en el servidor web. |
| RIOT-OS/riot-os.org | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| rism-digital/rism.info | Sin README; sitio web de contenidos. |
| rit-sse/WebsiteTheSSEquel | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| rlule15/azure-cloud-resume | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| RockefellerArchiveCenter/docs-build | Genera y publica sitios de documentación, no una aplicación. |
| ROCm/aiter | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| rodrigorodrigues/microservices-design-patterns | Proyecto demostrativo de patrones de microservicios ('to show a case'); además todas las ejecuciones se omiten. |
| rohanesor/classpod | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| romhml/compodium | Módulo de Nuxt; el despliegue es de su documentación. |
| RonewaOnly/AgriStream_ST10157545_Practium | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| RonyOz/personal-fintracker-mvp | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| roots/trellis | Herramienta (stack de Ansible para WordPress); el workflow la prueba. |
| RootstockCollective/dao-frontend | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| rosariozambrana/modulo3-Backend | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| rsksmart/rbtc-faucet | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| rtdevx-aws-apps/ecs-demo-1 | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| rubberdok/indok-web | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| runvendo/vendo | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| rustydb/sentinel | Proyecto de hackathon (EVE Hackathon). |
| Sabyasachi-Seal/Sabyasachi-Seal | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| sakazuki-org/sakazuki | Aplicación personal; la instancia desplegada es la demo. |
| saketh169/WBD-Deployment | Proyecto de curso (WBD). |
| SalgueroAgus/teros_challenge | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| SalishSeaCast/salishsea-site | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| saltyorg/Saltbox | Herramienta de instalación con Ansible; el workflow la prueba. |
| Sam-Razavi/rostid | Proyecto de portafolio; las 38 ejecuciones recientes fallaron. |
| samuelcolvin/python-devtools | Biblioteca o herramienta; el workflow solo despliega su sitio de documentación. |
| Sanket-HP/devops-fastapi-assignment | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| SanthoshMly/Enterprise-DevSecOps-Pipeline | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| sanwebinfo/og-image | más del 80 % de los commits recientes son automáticos (bots) |
| sarim751/SCD-Assignment-2-RAHBAR | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| Sayhi-bzb/CharDesk | El despliegue es a hosting estático (Cloudflare Pages), equivalente a GitHub Pages. |
| sbmagar13/recipe-jar | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| sc2in/PolicyPress | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| School-of-Company/Gwangju-talent-festival-Server-V2 | Proyecto de un programa escolar de startups ('4세대 스타트업 프로젝트'). |
| SciPub-TTS/SciPub-TTS-BE | Demo ('Production demo on Azure') de 77 días. |
| Sea-Shell/gogear-api | más del 80 % de los commits recientes son automáticos (bots) |
| Sea-Shell/sortarr | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| sebrandon1/bps-operator | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| seethroughlab/familiar | Reproductor local; el despliegue es a hosting estático (Cloudflare Pages). |
| SensorsConnect/IoT-Agentic-Search-Engine | Prototipo de investigación de un solo contribuidor presentado como demo ('Live Demo'). |
| sethum-VS/PressPlay | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| seung-lab/ng-extend | Actividad no genuina: 1847 ejecuciones en 6 meses con solo 88 commits en total; README basado en un ejemplo de neuroglancer. |
| Shrinet82/decision-trace | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| SIDDHANTCOOKIE/wot-pay | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| sillsdev/web-xforge | El workflow del dataset (`e2e-tests.yml`) son pruebas de extremo a extremo: instala Ansible y ejecuta `dev-server.playbook.yml --limit localhost` en el runner (environment `e2e_tests`); no despliega a producción (criterio 2). Revisión dirigida de workflows con nombre e2e/test/local. |
| simplyblock/sbcli | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| slaterlaura/Sistema-Rastreabilidade-EUDR | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| SmartOperatingBlock/digitaltwins-event-endpoint | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| SmartX-Team/dreamai-portal | README por defecto de create-next-app: no se puede confirmar el uso. |
| solana-playground/solana-playground | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| SolarisCulture/sopra-fs26-group-25-server | Proyecto de curso universitario (SoPra FS26, Universidad de Zúrich). |
| somatechlat/somabrain | YAML no legible |
| somleng/somleng | más del 80 % de los commits recientes son automáticos (bots) |
| somosgented/aura-design-system | Sistema de diseño (biblioteca de componentes y su documentación). |
| SonyaJane/dropped-kerb-mapper | Proyecto individual sin web propia; no se pudo confirmar que esté en uso. |
| sovereign-nature/deep | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| sparkfabrik/archlinux-ansible-provisioner | Herramienta de aprovisionamiento de estaciones de trabajo. |
| Specy/genshin-music | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; publica la versión nightly. |
| spiffe/java-spiffe | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| spoo-me/spoo | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| springdoc/springdoc-openapi-demos | Demos y aplicaciones de ejemplo de springdoc-openapi (README: 'Live demos and sample applications'). |
| sqlfluff/sqlfluff-online | más del 80 % de los commits recientes son automáticos (bots) |
| srl-labs/learn-srlinux | Portal de documentación de Nokia SR Linux, no una aplicación. |
| Stars-and-Stripes-Honor-Flight/sshf-ui | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| step-security/secure-repo | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job publish-test despliega al entorno de integración (int.yml). |
| streckeisen-dev/MyCVHub | Sin web ni evidencia de usuarios; 2 autores. |
| stryker-mutator/stryker-dashboard | más del 80 % de los commits recientes son automáticos (bots) |
| studiometa/js-toolkit | Biblioteca o herramienta; el workflow solo despliega su sitio de documentación. |
| suap-ava-suite/djangoapp-painel_ava | Declarado solo para desarrollo ('APENAS PARA DESENVOLVIMENTO'). |
| SukkaW/Friends | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| SunnyEkb/sunny_backend | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| superhero-com/superhero-wallet | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; su 'producción' es GitHub Pages y el despliegue por SSH va solo a stage. |
| surgent-dev/surgent | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| SUSTech-CRA/sustech-online-ng | Sitio estático de contenidos (manual en línea con VuePress), no una aplicación. |
| SwissDataScienceCenter/renku-blog | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| sws2apps/sws2apps-console | más del 80 % de los commits recientes son automáticos (bots) |
| TAK-NZ/utils-infra | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Taklif-AI/taklif.ai | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| Tanvir4801/YS-Trackify | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| taylorsprecher/connectable-pathways | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| Team-Commonly/commonly | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| TeamDevDev/www.developerdevelopment.com | Sitio estático de materiales de curso universitario. |
| techmatters/hrm | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| TejusR/DO-tiny-url | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| TelesCoop/iarbre | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| TelesCoop/TelesCoop-site-vitrine | Sitio vitrina estático (Astro). |
| temporaerhaus/website | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| Terra-Creator-Association/aneot | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| Tesis-2026/zenda_backend_app | organización de tesis/proyectos académicos (Tesis-2026) |
| TevBenji/OAuth-2.1-MCP-Gateway | Proyecto personal de un solo autor sin evidencia de usuarios. |
| th3cyb3rhub/TheCyberHub | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| thenervelab/hippius-s3 | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| TheoreticalAstrophysicsGroup/TheoreticalAstrophysicsGroup.github.io | Sitio estático (Jekyll) de un grupo universitario. |
| TheRestartProject/restarters.net | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| ThetaStation/ThetaStation | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| thundersquared/infrastructure | más del 80 % de los commits recientes son automáticos (bots) |
| tiangolo/library-skills | El workflow candidato solo despliega la documentación. |
| tiansivive/yap | Lenguaje de programación personal ('It's mine'); no es una aplicación en uso. |
| TicketRushPlatform/TicketRushPlatform_User_Service | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| timothylee58/MIFCG-AI | Proyecto de 88 días sin evidencia de usuarios; todas las ejecuciones fallidas. |
| tldraw/tldraw | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| Tmgilliam/scalable-sim-framework | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| tobiasgaitan/Bot-TiendaLasMotos | Sin README ni descripción: no se puede confirmar que esté en uso. |
| TomasinoWeb/tomasinoWebR101 | YAML sin jobs |
| Tongji-High-level-Language-Programming/Website | Sitio de un curso universitario (Universidad Tongji). |
| tornotron/echno-web | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| totto2727-org/lapriere-website | Sitio de fans no oficial de un autor; proyecto personal. |
| tough-dev-school/education-backend | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| tough-dev-school/lms-frontend-v2 | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| trailofbits/algo | Herramienta (scripts de Ansible para VPN); el workflow la prueba. |
| trento-project/web | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| triax/hub | README mínimo: no se puede confirmar qué es ni que esté en uso. |
| trindadetiago/map.art | Prototipo de I+D declarado ('Early R&D'). |
| tryethernal/ethernal | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| TryGhost/gscan | más del 80 % de los commits recientes son automáticos (bots) |
| TuNoCode123/DATN | Proyecto de tesis de grado (DATN: 'Đồ án tốt nghiệp'). |
| twin-digital/opus | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| TylorMayfield/digitalocean-nextjs-pr-previews | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| u-sb/nginx-docs | Sitio de documentación del repositorio de paquetes de nginx. |
| uidaholib/spec-lumber | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| UMNET-perfSONAR/pssid-gui2 | El workflow del dataset (`ci.yml`) es CI (pruebas, validación de configuración y escaneo de CVE de las imágenes); no despliega. Las y=0 venían del paso «Build the images this deployment ships», que la regla tomaba por despliegue por la palabra «deployment» (criterio 2). Detectado en la muestra de validación dirigida (semilla 11). |
| un-fao/exact-django-webapp | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| UNDP-Data/geohub | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| Unleash/helm-charts | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| UoaWDCC/aucc | Sitio de contenidos de un club, hecho por un club estudiantil de desarrollo (URL de Vercel autogenerada). |
| USBGuard/usbguard | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| usegalaxy-eu/infrastructure-playbook | El workflow del dataset (`tpv.yml`) ejecuta `ansible-playbook --connection=local` en el runner para probar la configuración TPV en pull requests; no despliega a producción (criterio 2). Detectado al verificar el dataset v2. |
| ustaxcourt/website-wagtail | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Utdanningsdirektoratet/designsystem | Sistema de diseño (componentes y documentación), no una aplicación. |
| UTDNebula/api-tools | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| UzairOrganization/allTask | README por defecto de create-next-app; las 13 ejecuciones recientes fallaron. |
| vaam-apps/vpay | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| Valar05/home-center | Piloto personal del hogar con actividad atípica (4620 commits en 139 días). |
| validityBase/dagster-portfolio-sample | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| vantage-sh/ec2instances.info | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| vapor/api-docs | Sitio de documentación de la API (api.vapor.codes), no una aplicación. |
| vapor/design | Recursos de diseño (CSS) y su pipeline de publicación, no una aplicación. |
| Vauhtijuoksu/wwwauhtijuoksu-cms | Declarado fuera de producción ('not in production'). |
| VectorInstitute/aieng-template-cloudrun-vllm | más del 80 % de los commits recientes son automáticos (bots) |
| VectorInstitute/implementation-catalog | más del 80 % de los commits recientes son automáticos (bots) |
| VegaFederal/VegaWebAWS | Plantilla de proyecto AWS («trying to deploy website»). |
| vektor-inc/vk-blocks | Plugin de WordPress (biblioteca). |
| VentsislavKostadinov/cognito-app-backend | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| verseles/codewalk | Las ejecuciones recientes se omitieron (skipped): el despliegue no se ejecuta. |
| vertica/vertica-sql-go | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| verygoodplugins/automem-website | Sitio de marketing, blog y documentación. |
| VibeTensor/attestix | El despliegue es de la documentación en hosting estático (Cloudflare Pages). |
| vicharanashala/ajrasakha | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| Victor-Kipruto-Rop/birthday_backend | Backend del sitio de cumpleaños personal del autor. |
| VictorNaitoon/RokeyManagement | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| vinicius-ma/fiap-f4sub-service-sales | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| Virelis/Stellar-Guard | Proyecto de 178 días en una URL de Vercel autogenerada, sin evidencia de usuarios. |
| Virtual-Hospitals-Africa/virtual-hospitals-africa | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| vivid-planet/dextinity-starter | Plantilla inicial ('Blueprint for a new Dextinity project'). |
| Vizzuality/esa | Plantilla de aplicación ('Serverless App scaffold') en una URL de Vercel autogenerada. |
| Vizzuality/mangrove-atlas | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| WadEazrIE3907L/Wv4IUIfIY | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| warpdl/warpdl | Gestor de descargas de escritorio; el despliegue en Workers es de su documentación. |
| watanabe-tsubasa/26-agent-hack-trial | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| wayofdev/docker-php-base | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| wayofdev/docker-php-dev | más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle |
| wazeerc/PrevueMD | Proyecto de aprendizaje/portafolio ('the first app I built after learning Vue'). |
| wazuh/wazuh-virtual-machines | Construye imágenes de máquinas virtuales (OVA/AMI), no despliega una aplicación. |
| WeBankFinTech/fes-design | Biblioteca de componentes Vue; el despliegue es de su sitio de documentación. |
| weedguetmildort/motivation_exploring_platform | Proyecto de equipo estudiantil en una URL de Heroku autogenerada. |
| weirdgloop/osrs-dps-calc | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| WelchsGrape/IIDXTierTable | Herramienta personal de un solo autor (101 días) sin web pública declarada. |
| wevisdemo/parliament-watch | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el workflow staging.yml despliega a staging. |
| WilliamTatendaJose/stylists-center | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| WillPresley/scribenode-podcast-transcription | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| wrenlift/hatch | Herramienta; el workflow candidato solo despliega su sitio. |
| wunderio/charts | despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack) |
| Xantibody/raizawa-blog | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| xieyuschen/gopls-mcp | Biblioteca o herramienta; el workflow solo despliega su sitio de documentación. |
| YacinD/fargate-memos-deployment | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| Yan-Lue/sopra-fs26-group-24-server | Proyecto de curso universitario (Software Practical Course, Universidad de Zúrich, 2026). |
| yanke4/sopra-fs26-group-23-server | Proyecto de curso universitario (SoPra FS26, Universidad de Zúrich). |
| yasar-pathan/attendify-charusat | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| yashahirrao31/talentsync-ai | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| yiruyang2025/vello-server | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| youuu199/phyat-paing | historial de commits insuficiente (menos de 20 commits o de 60 días) |
| yplam/osrtos | Sitio estático de contenidos (Astro + Markdown) sobre RTOS, no una aplicación. |
| yudai142/FloorMap | Proyecto personal; las 40 ejecuciones recientes fallaron. |
| ZathuraDbg/ZathuraDbg | Depurador de escritorio; el despliegue es a hosting estático (Cloudflare Pages). |
| zeekman/Cross-Border-Payment-App-for-Africa | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| zenGate-Global/winter-backend-cardano | ningún despliegue completado (y=0) en las ejecuciones revisadas (hasta 100) |
| zerodytrash/TikTok-Live-Connector | ningún paso despliega a un entorno de aplicación (o solo previews de PR) |
| zesty-io/manager-ui | Criterio 2 (solo producción): el workflow del dataset no despliega a producción; el job deploy_dev despliega a dev. |
| Zettlr/zettlr-docs | Documentación oficial de Zettlr, no una aplicación. |
