# Estado del proyecto (para continuar en una sesión nueva)

Tesis: «Plataforma predictiva basada en IA para el riesgo de despliegue de
aplicaciones empresariales». Django/DRF + React/Vite, PostgreSQL, Random
Forest/XGBoost + SHAP, análisis de texto con Claude (Haiku 5.5; Gemini como
alternativa).

Actualizado: 2026-11-23 (tarde) · rama `feature/100-repos-desplegados` (publicada en
`origin`, **sin merge a `main`**).

## 1. Reglas acordadas (obligatorias)

1. **Responder siempre en español.**
2. **Nunca imprimir el `.env`** (`backend/.env`). Los valores se leen solo
   dentro del comando, sin mostrarlos:
   `v(){ grep "^$1=" backend/.env | cut -d= -f2- | tr -d '\r'; }`.
3. **Commit sí; push y merge solo cuando se pidan.** Nunca merge a `main`
   sin orden expresa. Antes de cada push: comprobar que no se suben `.env`,
   `logs/`, respaldos (`*.dump`), PDF ni secretos (tokens, claves,
   contraseñas). El repositorio de GitHub es **público**.
4. **Respaldo antes de tocar la base de datos**: `pg_dump -Fc` en
   `C:\Users\Administrator\Desktop\tesis_respaldos\` (fuera del repositorio)
   antes de cualquier migración o cambio de datos.
5. **Migraciones**: ensayarlas primero en una copia restaurada del respaldo
   (aplicar, revertir, volver a aplicar), luego en la base real.
6. **Tarea programada**: desactivarla antes de migrar y reactivarla al
   terminar (ver §5).
7. **Dataset congelado**: no reabrir la búsqueda de repositorios ni cambiar
   las reglas de etiquetado sin aprobación.
8. **Cambios grandes por etapas** y esperar aprobación entre etapas cuando
   así se pida.
9. Pruebas antes de cada commit: `venv\Scripts\python.exe manage.py test
   riesgo` (backend) y `npm test` + `npx vite build` (frontend).

## 2. Estado actual

### Dataset v2.0
- `datos_procesados/dataset_riesgo_despliegue_v2.csv`: 4.117 ejecuciones de
  198 repositorios reales (401 con y = 1, despliegue no completado).
- Etiquetas: y = 0 `despliegue_completado`, y = 1 `despliegue_no_completado`;
  el resto (`excluida_*`) no se evalúa. Etiquetado con los jobs de la API y
  el YAML del workflow en el commit de cada ejecución
  (`riesgo/services/etiquetado.py`, `verificacion.py`).
- Fecha de corte (última ejecución del entrenamiento):
  **2026-11-09T16:09:30Z** (`modelos/modelo_riesgo_v2.json`).

### Modelos: Random Forest (principal) y XGBoost (alternativo)
Los dos modelos de la propuesta, entrenados con el dataset v2 (misma fecha
de corte y mismas variables). Se puede elegir cualquiera en cada análisis.

| Versión | Modelo | Rol | Validación GroupKFold (PR-AUC / Brier) | Despliegues reales al 23-nov (PR-AUC / Brier, 1.423 ejecuciones) |
|---|---|---|---|---|
| `v2` | Random Forest | Principal (activo; lo usa el lote) | 0,415 / 0,067 | 0,631 [0,556–0,698] / 0,082 [0,071–0,093] |
| `v2-xgb` | XGBoost | Alternativo (en sombra en el lote) | 0,348 / 0,074 | 0,570 [0,489–0,640] / 0,089 [0,078–0,101] |

- Diferencia XGBoost − Random Forest con despliegues reales: Brier +0,0065
  [+0,0040 – +0,0091], PR-AUC −0,061 [−0,092 – −0,032]: Random Forest es
  mejor de forma significativa; confirma la selección del entrenamiento
  (`informes/fase5_modelos_v2.md` §9).
- XGBoost: `entrenar_modelos_v2.py --alternativo-xgboost` (mismo
  procedimiento que el principal, reproducible), archivos
  `modelos/modelo_riesgo_v2_xgb.*`, registrado con
  `registrar_modelo --modelo v2-xgb --sin-activar` (23-nov). Mismos límites
  de nivel (tasa base 0,097 y el doble). Sus factores SHAP se presentan en
  puntos de probabilidad, como los de Random Forest (explicador
  intervencional sobre la probabilidad, con 200 filas del dataset de fondo;
  `predictor._cargar`).
- **v1 y v1.1 retiradas** (`est_registro = 'I'`; v1.1 migración 0022, v1
  migración 0029, 23-nov): no salen en Modelos, Supervisión, Comparación ni
  selectores, no se pueden activar y el lote ya no las evalúa en sombra. Sus
  filas, predicciones y archivos se conservan. Registros de sus
  comparaciones: `informes/comparacion_sombra_v2.md` (v1.1, 17-nov) y
  `informes/comparacion_sombra_v1.md` (v1, 23-nov: v2 mejor de forma
  significativa en 1.423 ejecuciones).
- **Elección en cada análisis** («Nuevo análisis» y Planificador): Random
  Forest (por defecto), XGBoost o «Comparar ambos». Todo el análisis
  (probabilidad, nivel con los límites de ese modelo, recomendación,
  factores SHAP y texto de la IA) sale del modelo elegido y se guarda con él
  (`id_version_modelo`). «Comparar ambos» crea los dos análisis ocultos
  (`est_registro = 'I'`, el segundo enlazado al primero con
  `id_prediccion_base`); el autor elige el oficial
  (`POST /api/predicciones/{id}/oficial/`) y solo ese lo ve el líder. El
  modelo se muestra en el detalle, historiales (con filtro «Modelo»),
  pendientes, informes de cumplimiento y PDF.
- **Cambiar el principal**: solo en Modelos, escribiendo el nombre de la
  versión; queda en `trx_activacion_modelo`. El principal solo decide el
  modelo por defecto de cada análisis: **el lote, la sombra y la comparación
  usan siempre Random Forest** (`modelos.modelo_lote()`). Solo el
  administrador cambia el principal (desarrollador y líder reciben 403).
- **Disponible para análisis** (Modelos, solo administrador;
  `mae_version_modelo.es_disponible_analisis`, migraciones 0030–0031):
  qué modelos ofrecen «Nuevo análisis» y el Planificador. Random Forest
  (modelo del lote) y el principal siempre están disponibles; un modelo no
  disponible no puede ser principal. Con un solo modelo disponible no se
  muestra el selector y se usa el principal. El backend rechaza un modelo
  no disponible (400 `modelo_no_disponible`). Cada cambio queda en
  `trx_disponibilidad_modelo` (quién, cuándo y a qué valor; visible en el
  admin de Django, de solo lectura). No hay acción de desactivar y
  el admin de Django es de solo lectura para las versiones. El panel del
  administrador avisa en rojo si el activo no tiene fecha de corte o es de
  un corte anterior al más reciente.
- Recomendación automática: nivel alto → «Solicitar revisión previa»;
  bajo/medio → «Permitir el despliegue». El líder técnico la acepta o la
  cambia (se guarda `acepta_recomendacion`).
- La IA solo redacta el texto del análisis (resumen y recomendaciones IA01,
  IA02…). Proveedor `IA_PROVEEDOR=claude|gemini|reglas` (por defecto Claude,
  modelo `CLAUDE_MODELO=claude-haiku-5-5`, clave `CLAUDE_API_KEY`); si falla,
  rechaza o tarda más de `IA_TIMEOUT`, se usa el análisis por reglas (nunca
  Error 500). Con «Comparar ambos» se redactan dos textos. Las pruebas nunca
  llaman a una API de pago.
- Supervisión prospectiva: cuenta solo ejecuciones posteriores al corte;
  excluye repos de demostración y de prueba y los análisis no elegidos de
  «Comparar ambos».
- **Evaluación en sombra** (`riesgo/services/sombra.py`, comando
  `evaluar_sombra`, también al final de cada pasada del lote): la versión
  visible no activa (XGBoost) predice las mismas ejecuciones evaluables de
  la supervisión del principal con las variables guardadas, sin llamar a
  GitHub. Se guardan con `origen = "sombra"` e `id_prediccion_base`; el
  gestor por defecto las excluye. El 23-nov se crearon las 1.423 de las
  ejecuciones ya evaluadas. Modelos → Comparación muestra Random Forest
  frente a XGBoost (`/api/modelos/comparacion-sombra/`).

### Plataforma
- 229 repositorios activos (198 del dataset v2 + 1 de demostración
  `ErickTerranova2004/demo-despliegue-riesgo` + 30 de casos de prueba);
  406 inactivos (históricos de GHALogs y otros), se conservan con su historial.
- «Nuevo análisis»: los repos con commits pendientes de desplegar salen
  primero («N commits pendientes») y rellenan SHA, rama y evento; aviso 409
  si el commit ya se desplegó o se está desplegando (se puede continuar).
- Resultado real: ya no hay botón «Verificar resultado real». La vista del
  análisis indica que se verifica automáticamente: al abrirla empieza el
  seguimiento en la página (consulta cada 30 s, hasta 2 h; se puede
  detener) y cada pasada del lote enlaza los pendientes. Se enlaza la
  primera ejecución terminada del mismo workflow y commit que empiece
  después del análisis (ignora las `skipped`).
- Workflows (administrador): por defecto solo los de repositorios activos;
  la casilla «Incluir repositorios inactivos» muestra también los demás. Los
  contadores indican a qué alcance corresponden.
- Usuarios activos: `admin` (superusuario), `revision_admin`,
  `revision_dev`, `revision_lider` (listadas en
  `datos_prueba/usuarios_prueba.md`, sin contraseñas: se restablecen por
  correo) y `analisis_lote` (cuenta interna del
  lote: sin rol ni contraseña utilizable; **no eliminarla**). Las cuentas
  `prueba_*` se eliminaron y su historial pasó a las `revision_*` del mismo
  rol.
- «Último acceso» se registra al iniciar sesión (`riesgo/sesion.py`).
- El administrador puede eliminar cuentas con historial traspasándolo a otra
  cuenta activa del mismo rol o administradora (`transferir_a` no numérico →
  400).
- **Navegación con URL** (`frontend/src/rutas.js`, `navegacion.jsx`,
  `estadoUrl.js`; API History, sin React Router): una ruta por pantalla
  (`/panel`, `/nuevo-analisis`, `/planificador`, `/historial`,
  `/analisis/<id>`, `/pendientes`, `/informes`, `/informes/<id>`, `/usuarios`,
  `/workflows`, `/modelos`, `/integraciones`, `/restablecer/<uid>/<token>`);
  atrás/adelante y F5 funcionan; filtros, orden y página van en la dirección.
  Sin sesión se pide el login y se vuelve a la dirección pedida; sin permiso
  se va al panel del rol. El enlace antiguo `?informe=<id>` redirige a
  `/informes/<id>`. Vite con `appType: "spa"` (también en `vite preview`).
- **Filtros uniformes** (backend, junto con la paginación) en Mi historial,
  Historial del equipo, Historial de análisis y Pendientes: desde/hasta
  (dd/mm/aaaa), nivel, decisión (la última; no en Pendientes), repositorio,
  orden, origen (solo administrador) y «Quitar filtros». Informes recibidos y
  de cumplimiento: desde/hasta, nivel de riesgo actual, resultado del cambio
  (bajó/se mantuvo/subió, comparando niveles), decisión final (incluida
  «Pendiente»), repositorio y orden.
- **Paginación en el backend** opcional (`?pagina=N&por_pagina=25|50|100`,
  `riesgo/paginacion.py`); tablas largas con barra horizontal arriba y
  encabezados fijos.
- **Restablecimiento de contraseña por correo** (Gmail con contraseña de
  aplicación; enlace de una hora y un solo uso; auditoría en
  `trx_restablecimiento_clave`).
- **Informe de cumplimiento** del desarrollador al líder técnico
  (`trx_informe_cumplimiento`, descargas en PDF/otros formatos registradas en
  `trx_descarga_informe`). Las decisiones solo se toman sobre análisis de
  desarrolladores (el líder no ve los del lote).
- **Planificador**: último análisis preseleccionado (`?analisis=<id>`),
  escenarios desde hoy, «Mejores ventanas» desde mañana
  (`PLANIFICADOR_DIAS_VENTANAS`) con «Mejor opción» y diferencia en puntos,
  sin el cuadro amarillo; nota de la hora UTC bajo «Variables de tiempo».
- **Nuevo análisis**: si el commit ya se desplegó, tarjeta azul informativa
  («Este cambio ya se desplegó hoy a las 10:05 y terminó correctamente.»),
  sin número de ejecución ni términos en inglés, con enlace discreto «Ver la
  ejecución en GitHub» (interpretación del texto cortado «Enlace discreto»;
  pendiente de confirmar).

### Base de datos y diagrama ER
- Nombres del ER (`docs/modelo_er.png`): tablas `mae_`, `trx_`, `int_`
  (migraciones 0016–0018, y 0021 para la columna de la 0020); índices y restricciones `pk_/fk_/uk_/ck_/ix_/sq_`;
  vistas de solo lectura `seg_usuario`, `seg_grupo`, `int_usuario_grupo`,
  `seg_token` sobre las tablas de Django (`auth_*`, que se mantienen).
- Auditoría (migración 0019, `riesgo/auditoria.py`): `est_registro`
  (char(1), A/I, sin borrado lógico), `usu_creacion`, `fec_creacion`,
  `usu_modificacion`, `fec_modificacion` en las 11 tablas propias; se llenan
  en todas las vías de escritura (middleware para la API, `ComandoAuditado`
  para los comandos, `sistema` fuera de ambos).
- Migración 0020: origen `sombra` y `trx_prediccion.id_prediccion_base`
  (única con `id_version_modelo`: una sombra por versión y predicción).
- `backend/riesgo/tests/test_esquema_er.py` compara la base con el ER
  columna por columna.
- Migraciones hasta la 0031: `trx_restablecimiento_clave` (0023–0024),
  `trx_informe_cumplimiento` y `trx_descarga_informe` (0025–0026),
  `trx_activacion_modelo` (0027–0028), con los mismos nombres ER y columnas
  de auditoría; 0029 solo oculta v1 (datos); 0030–0031:
  `es_disponible_analisis` y `trx_disponibilidad_modelo` (diagrama ER
  regenerado el 23-nov).
- Diagrama actualizado (23-nov, con las cuatro tablas anteriores):
  `docs/modelo_er_actualizado.drawio` y `.png`, generados con
  `backend\venv\Scripts\python.exe scripts\generar_diagrama_er.py --png`.
- Equivalencias y diferencias documentadas en `docs/arquitectura.md`.

### Tarea programada (análisis en lote)
- Tarea `tesis\analizar_lote` del Programador de tareas, cada 4 h desde las
  00:00, también con batería; la lanza oculta
  `scripts\analizar_lote_oculto.vbs` → `scripts\analizar_lote.cmd`.
  Log diario en `logs\lote_AAAAMMDD.log` (cada pasada termina con
  `=== Codigo de salida 0 (…)`).
- Cada pasada: (1) enlaza análisis interactivos pendientes (30 días),
  (2) analiza ejecuciones nuevas posteriores al corte (listado incremental,
  ETag; se salta las ya enlazadas a un análisis interactivo), (3) actualiza
  los commits pendientes por workflow, (4) crea las predicciones en sombra
  que falten (sin llamadas a GitHub). Gasto típico: 10–40 llamadas a la API
  (+ cientos de 304 sin coste).
- Comprobar: `Get-ScheduledTaskInfo -TaskPath "\tesis\" -TaskName analizar_lote`.
  Desactivar/activar: `Disable-ScheduledTask` / `Enable-ScheduledTask`
  (mismos parámetros).

### Levantar la plataforma
`powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo.ps1`
(`-RedLocal` para abrirla desde el celular). Detiene lo que escuche en 8000
y 5174 (con netstat), aplica migraciones y abre backend y frontend en dos
ventanas. Requiere PostgreSQL encendido. El usuario la gestiona: no
arrancarla desde el asistente.

### Compartir el proyecto con otra persona
- Manual paso a paso: `docs/manual_instalacion.md`.
- `scripts\exportar_datos.ps1`: `pg_dump -Fc` con fecha en
  `..\tesis_respaldos\` (se niega a escribir dentro del repositorio; sin
  sesiones ni tokens). `scripts\importar_datos.ps1 -Respaldo <archivo>`: crea
  la base si no existe, se detiene si ya tiene datos (`-Reemplazar` la
  respalda antes), `pg_restore --no-owner --no-privileges` y `migrate`.
  Probados el 23-nov restaurando en una base de ensayo (mismos conteos).
- El respaldo se comparte **solo por un medio privado**, nunca por GitHub.
  Cada persona crea su `backend\.env` con sus propias claves.
- Fuera del repositorio y no necesarios para usar la plataforma:
  `informes/cache_filtrado/` (≈ 49 MB; solo para reconstruir el dataset v2)
  y `Datos/runs.json.gz` (Zenodo; solo v1/v1.1).
- `DJANGO_SECRET_KEY` renovada el 23-nov (cierra las sesiones del admin de
  Django e invalida los enlaces de restablecimiento pendientes; las sesiones
  de la plataforma usan tokens de DRF guardados en la base y no dependen de
  esa clave).

### Respaldos recientes (`tesis_respaldos\`)
- `riesgo_despliegue_20261112_002918_antes_nombres_er.dump`
- `riesgo_despliegue_20261112_005202_antes_auditoria.dump`
- `riesgo_despliegue_20261112_033644_antes_quitar_prueba.dump`
- `riesgo_despliegue_20261117_103250_antes_sombra.dump`
- `riesgo_despliegue_20261117_105450_antes_ocultar_v1_1.dump`
- `riesgo_despliegue_20261120_165221_antes_desactivar_prueba.dump`
- `riesgo_despliegue_20261120_174326_antes_informe_cumplimiento.dump`
- `riesgo_despliegue_20261120_195916_antes_limpiar_repos_inactivos.dump`
- `riesgo_despliegue_20261123_130149_antes_reactivar_v2_c.dump`
- `riesgo_despliegue_20261123_131341_antes_activacion_modelo.dump`
- `riesgo_despliegue_20261123_132420_antes_ocultar_v1.dump`
- `riesgo_despliegue_20261123_132730_antes_registrar_xgboost.dump`
- `riesgo_despliegue_20261123_154254_antes_sombra_xgboost.dump`
- `riesgo_despliegue_20261123_160523_antes_volver_a_random_forest.dump`
- `riesgo_despliegue_20261123_161545_antes_corregir_lote_xgboost.dump`
- `riesgo_despliegue_20261123_163026_antes_regenerar_texto_ia.dump`
- `riesgo_despliegue_20261123_163610_antes_disponibilidad_modelo.dump`

### Limpieza de repositorios inactivos (20-nov-2026)

**Por qué estaban ahí.** Al cargar el dataset GHALogs v1.1 (20-oct-2026) sus
workflows se dieron por validados automáticamente («Validado automáticamente a
partir del dataset final de la tesis…»). La regla de entonces comprobaba que
el workflow ejecutara pasos reales de despliegue, pero **no el entorno**: no
distinguía producción de staging, dev, QA, previews o demos, y se le escapó
algún GitHub Pages. Al activar v2 esos 436 repositorios pasaron a
`est_registro='I'`, pero sus workflows siguieron activos y validados, y los
171 análisis interactivos hechos sobre ellos (cuenta admin, 20 a 30-oct)
seguían saliendo en el historial del administrador (p. ej. `deploy-staging.yml`
de avrae/avrae, `deploy-pages.yml` de bdunderscore/modular-avatar y
`dev-deploy-inbound-mail.yml` de novuhq/novu).

**Corrección** (`manage.py limpiar_repos_inactivos`, sin borrar nada; sin
`--aplicar` solo informa y es idempotente):
1. `est_registro='I'` en lo que cuelga de los repositorios inactivos: 641
   workflows, 171 análisis interactivos, 3 decisiones/asignaciones, 499 enlaces
   análisis–ejecución y 3 accesos. No había informes de cumplimiento ni
   análisis en lote o en sombra en esos repositorios (el lote solo analiza los
   repositorios activos del dataset v2).
2. Ningún análisis de un repositorio inactivo sale en los historiales,
   paneles, pendientes, asignaciones ni en el Planificador
   (`permissions.predicciones_visibles` filtra el repositorio activo). Los
   análisis en lote y en sombra se conservarían igualmente para la historia
   del modelo (supervisión y comparación en sombra no usan ese filtro).
3. `despliegue_validado=False` en los 107 workflows que por el nombre no son de
   producción (staging, stage, stg, pages, dev, develop, preview, qa, uat,
   sandbox, demo, o solo pruebas sin palabra de despliegue), salvo si el
   nombre también dice prod/production/live. Excepciones comprobadas como
   producción: el repositorio de demostración, `mozilla/probe-scraper`
   (`build-test-deploy.yml`), `dailybruin/flamingo` (`test_and_deploy.yml`) y
   `Explorer-Consulting/SchoolFeedBackWebAPI` (`gimi_develop_feedback-api.yml`:
   se dispara con `develop` pero despliega al slot `Production`). Los 107 eran
   de repositorios inactivos.
4. Respaldo previo: `riesgo_despliegue_20261120_195916_antes_limpiar_repos_inactivos.dump`.

## 3. Decisiones tomadas

| Decisión | Motivo |
|---|---|
| Mantener las tablas de usuarios de Django y exponer `seg_*` como vistas | Cambiar el modelo de usuario a mitad del proyecto obliga a rehacer migraciones, usuarios y tokens |
| `est_registro` sin borrado lógico ('E') | Cambiaría el comportamiento de todas las consultas y de las restricciones únicas |
| La IA (Claude; antes Gemini) solo redacta el análisis | La probabilidad, el nivel, los factores SHAP y la recomendación son del modelo |
| Lote: no analizar ejecuciones ya enlazadas a un análisis interactivo | Un despliegue no debe contar dos veces en la supervisión |
| Lote cada 4 h (no cada hora) | Las variables se reconstruyen al inicio de cada ejecución: la frecuencia no cambia el resultado y ahorra cuota |
| No filtrar repositorios en «Nuevo análisis»; avisar del commit ya desplegado | «Desplegado» depende del commit; la mayoría despliega con cada push |
| Cuentas con historial: eliminar solo traspasándolo | Conservar trazabilidad y métricas |
| Análisis de demostración y de prueba fuera de las métricas | No son validación del modelo |
| v1 y v1.1 se comparan en sombra, sin activarlos | Mismas ejecuciones y mismas variables para los tres modelos; activar otro modelo cambiaría los análisis de los usuarios |
| Las predicciones en sombra se excluyen en el gestor por defecto | Ninguna consulta existente puede contarlas como análisis de usuarios por descuido |
| Ocultar v1.1 en lugar de borrarla | Hay predicciones que la referencian (PROTECT) y la comparación en sombra queda documentada en el informe |
| Sin botón «Verificar resultado real» | La verificación ya es automática (página y lote); el botón confundía |
| Los análisis de repositorios inactivos no salen en las vistas de los roles | Eran del dataset v1.1 validado sin regla de entorno; se conservan (est_registro='I') para la auditoría y la historia del modelo |
| Navegación con la API History, sin React Router | Sin dependencias nuevas; las rutas son pocas y fijas |
| Filtros y paginación en el backend | Con paginación, filtrar en el navegador solo vería una página |
| «Resultado del cambio» de los informes por nivel, no por probabilidad | Es lo que ve el líder; una variación pequeña de probabilidad no es una mejora |
| El respaldo de la base nunca va a GitHub | El repositorio es público y la base tiene cuentas, correos y contraseñas cifradas |
| Random Forest principal y XGBoost alternativo (los dos elegibles) | Son los dos modelos de la propuesta; la regla de selección y los despliegues reales favorecen a Random Forest |
| «Comparar ambos» guarda los dos análisis ocultos hasta elegir el oficial | El líder decide sobre un solo análisis y la supervisión no cuenta dos veces el mismo despliegue |
| Sin columna nueva para el par de «Comparar ambos» | Se reutiliza `id_prediccion_base` (como en sombra): sin migración de esquema ni cambio del ER |
| Admin de Django de solo lectura para las versiones del modelo | Allí se podía desactivar un modelo sin confirmación ni registro |

## 4. Pendientes (por prioridad)

**Alta**
1. **Merge de `feature/100-repos-desplegados` a `main`**: todo está
   publicado en la rama; esperar orden expresa.
2. **Demostración con despliegues reales**: analizar EfileProxyServer
   (`fly-prod-release.yml`, evento `release`, rama `v1.5.4`) y lumos-web
   (`deploy-cloudrun-release.yaml`, rama `v2.0.25`) con el SHA de la cabeza
   de `main` justo antes de su próxima release; el lote enlaza el resultado.
3. **Confirmar con el tutor el cambio de variable objetivo**: de «fallo real
   en producción» a «despliegue no completado en el pipeline». Justificación
   en `informes/fase2_variable_objetivo.md` §5 (no hay evidencia suficiente
   para etiquetar incidentes en producción; la nueva etiqueta es observable
   con exactitud y no mide incidentes posteriores al despliegue).
4. **Justificación escrita de por qué no se integraron Jira y SonarQube**
   (propuesta, funcionalidad 1): redactarla como limitación del alcance y
   trabajo futuro.

**Media**
5. **Error del etiquetado con `\bplan\b`**: `PATRON_NO_DESPLIEGA` marca
   «no despliega» una variable `plan.txt` dentro de un script de despliegue
   (caso built-in-saudi). Corregirlo afecta al dataset congelado: requiere
   aprobación.
6. Actualizar el informe de supervisión de v2 en la tesis con los datos que
   sigue sumando el lote, incluida la comparación en sombra con v1 y v1.1.
7. **Redactar el capítulo de resultados de la tesis**: dataset v2.0, modelo
   v2 (validación GroupKFold), validación prospectiva con el lote,
   limitaciones y uso de herramientas de IA.

**Baja**
8. Análisis 683 y 686 del repo de demostración: siguen pendientes de su
   resultado real (fuera de métricas); se enlazan solos si se despliega la
   demo.
9. Etiquetas `sin_intento` restantes del lote (128 tras el re-etiquetado):
   revisar si alguna es sospechosa.
10. `datos_prueba/casos_prueba_30.md` nombra a las cuentas `prueba_*`
    eliminadas (registro histórico; se dejó tal cual).
11. Probar en el navegador «Comparar ambos» (elegir el oficial, también al
    atender una asignación) y el selector de modelo del Planificador; las
    pruebas automáticas cubren la API y el renderizado.
12. Probar en el navegador la navegación con URL (atrás/adelante, F5,
    login con regreso a la dirección pedida); las pruebas automáticas cubren
    la lógica, no el navegador real.

**Hecho del 18 al 23-nov**
- **Correcciones del 23-nov (tarde)**: «Comparar ambos» con resumen de la
  diferencia arriba y los dos modelos lado a lado (uno debajo del otro en
  pantallas estrechas); sin el mensaje técnico de la tasa por nivel (ahora
  se muestra la tasa real del modelo con despliegues verificados, desde 20
  casos); factores SHAP de XGBoost en puntos de probabilidad (gráfico y texto
  de la IA). Incidente: entre las 15:59 y las 16:00 `revision_admin` dejó
  XGBoost como principal y la pasada del lote de las 16:00 analizó 32
  ejecuciones con XGBoost; se volvió a Random Forest (16:05, respaldo
  `..._160523_antes_volver_a_random_forest.dump`), esas 32 se rehicieron
  con Random Forest y las de XGBoost pasaron a ser su sombra (respaldo
  `..._161545_antes_corregir_lote_xgboost.dump`), y el lote usa ya siempre
  Random Forest. Los tres análisis interactivos de XGBoost de esa prueba
  (5994, 5995, 5997) tienen los factores recalculados en probabilidad y el
  texto de IA regenerado con Claude (16:30; respaldo
  `..._163026_antes_regenerar_texto_ia.dump`): ya no cita log-odds. «Comparar ambos» falló en
  esa prueba porque el backend no se había reiniciado (corría desde las
  13:12); la pantalla ahora lo avisa.
- **Dos modelos (23-nov, tarde)**: registro de la comparación v2 frente a
  v1 (`informes/comparacion_sombra_v1.md`); v1 retirada (migración 0029);
  XGBoost del dataset v2 registrado como alternativo; elección del modelo en
  cada análisis y en el Planificador, «Comparar ambos» con análisis oficial,
  modelo visible en todas las pantallas y el PDF, filtro «Modelo»; XGBoost
  en sombra (1.423 creadas) y comparación con despliegues reales; admin de
  Django de solo lectura para las versiones. Respaldos:
  `..._132420_antes_ocultar_v1.dump`,
  `..._132730_antes_registrar_xgboost.dump`,
  `..._154254_antes_sombra_xgboost.dump`.
- **Incidente 23-nov**: v1 quedó activo a las 10:36 (Modelos → «Activar»,
  cuenta `admin`); la pasada del lote de las 12:00 falló («El modelo v1 … no
  tiene fecha_corte») y no se hizo ninguna predicción con v1. Respaldo
  `..._130149_antes_reactivar_v2_c.dump`; v2 reactivado a las 13:01; pasada
  manual del lote 13:02–13:13 terminada con código 0 (38 analizadas, 126
  sombras de v1 que faltaban).
- **Para que no se repita** (migraciones 0027–0028, respaldo
  `..._131341_antes_activacion_modelo.dump`): las versiones sin fecha de
  corte (v1) no tienen botón «Activar» y la API las rechaza; activar otra
  exige escribir su nombre; cada activación queda en `trx_activacion_modelo`
  (quién, cuándo, versión anterior, pantalla o comando); el panel del
  administrador avisa si el activo no es la versión más reciente con fecha de
  corte (`riesgo/services/modelos.py`, `/api/resumen-admin/` → `modelo`).
- Contraseñas quitadas de `datos_prueba/usuarios_prueba.md` (se restablecen
  por correo).
- Restablecimiento de contraseña por correo, filtros por fecha dd/mm/aaaa,
  informe de cumplimiento, paginación en el backend, limpieza de
  repositorios inactivos, navegación con URL, filtros uniformes, mejoras del
  Planificador y del aviso de commit desplegado (ver §2 Plataforma).
- `iniciar_demo.ps1`: detecta con netstat todos los procesos del puerto (con
  dos backends a la vez `Get-NetTCPConnection` solo devolvía uno).
- Datos de los casos de prueba desactivados; Vite 5.4.21.
- Scripts para compartir la base, manual de instalación para otra persona,
  `DJANGO_SECRET_KEY` nueva y diagrama ER con las tablas nuevas (23-nov).

**Hecho el 17-nov**
- Claude (Haiku 5.5) redacta el análisis; los tokens y la duración de cada
  llamada se guardan en `jsn_analisis_ia.uso`.
- Script `scripts\analisis_programados.cmd` (análisis interactivos reales
  repartidos en el tiempo, como `revision_dev`). Hoy hubo dos ejecuciones
  solapadas (08:50 y 10:03): 43 análisis (ids 1388–1430), 18 commits
  analizados dos veces. Se detuvo a las 10:32 con 21 de 40.
- Evaluación en sombra, verificación automática sin botón y filtro de
  repositorios inactivos en Workflows (arriba).
- v1.1 oculta (migración 0022) tras guardar
  `informes/comparacion_sombra_v2.md`.
- Incidente 10:56: v1 quedó activa desde Modelos → «Activar» (usuario
  `revision_admin`, en el backend antiguo de las 8:49). Se reactivó v2 a las
  10:59 (respaldo `..._105926_antes_reactivar_v2.dump`); no se hizo ninguna
  predicción con v1 en ese intervalo. Se repitió a las 11:04:56 (otra
  activación de v1 desde el mismo botón); v2 se reactivó a las 11:06
  (respaldo `..._antes_reactivar_v2_b.dump`), sin predicciones con v1. Se
  probó una confirmación en el botón y se quitó a pedido del usuario.

**Hecho el 12-nov**
- Error boundary en React (`frontend/src/limiteErrores.js`): un error al
  renderizar una sección muestra un aviso con «Reintentar» y «Recargar la
  página» en lugar de dejar la interfaz en blanco; el menú sigue disponible
  y el aviso se reinicia al cambiar de sección. Hay un segundo límite
  alrededor de toda la aplicación (`main.jsx`). Prueba:
  `frontend/tests/limiteErrores.test.js`.
