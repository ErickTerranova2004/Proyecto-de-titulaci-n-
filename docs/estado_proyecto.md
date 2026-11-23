# Estado del proyecto (para continuar en una sesión nueva)

Tesis: «Plataforma predictiva basada en IA para el riesgo de despliegue de
aplicaciones empresariales». Django/DRF + React/Vite, PostgreSQL, Random
Forest/XGBoost + SHAP, análisis de texto con Claude (Haiku 5.5; Gemini como
alternativa).

Actualizado: 2026-11-23 · rama `feature/100-repos-desplegados` (publicada en
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

### Modelo v2 (activo)
- Random Forest, validación GroupKFold por repositorio: PR-AUC 0,415,
  ROC-AUC 0,803, recall y=1 0,536, precisión 0,517, F1 0,526, Brier 0,067.
  v1 está registrado e inactivo. **v1.1 está oculta** (`est_registro = 'I'`,
  migración 0022): no sale en Modelos, Supervisión, la comparación ni los
  selectores, no se puede activar y `evaluar_sombra` ya no la evalúa; sus
  filas, sus 83 predicciones interactivas, sus 791 en sombra y sus archivos
  se conservan.
- Recomendación automática: nivel alto → «Solicitar revisión previa»;
  bajo/medio → «Permitir el despliegue». El líder técnico la acepta o la
  cambia (se guarda `acepta_recomendacion`).
- La IA solo redacta el texto del análisis (resumen y recomendaciones IA01,
  IA02…). Proveedor `IA_PROVEEDOR=claude|gemini|reglas` (por defecto Claude,
  modelo `CLAUDE_MODELO=claude-haiku-5-5`, clave `CLAUDE_API_KEY`); si falla,
  rechaza o tarda más de `IA_TIMEOUT`, se usa el análisis por reglas (nunca
  Error 500). Las pruebas nunca llaman a una API de pago.
- Supervisión prospectiva: cuenta solo ejecuciones posteriores al corte;
  excluye repos de demostración y de prueba. 1.158 predicciones de lote y
  261 interactivas en la base (17-nov).
- **Evaluación en sombra de v1 y v1.1** (`riesgo/services/sombra.py`,
  comando `evaluar_sombra`, también al final de cada pasada del lote): sin
  activarlos ni llamar a GitHub, predicen las mismas ejecuciones evaluables
  de la supervisión de v2 con las variables guardadas en cada predicción de
  v2; `reejecutado_por_otro` (que v2 no guarda) se rellena con la mediana
  del imputador de cada modelo. Se guardan con `origen = "sombra"` e
  `id_prediccion_base`; el gestor por defecto (`Prediccion.objects`) las
  excluye, así que no salen en historiales, paneles, «Nuevo análisis» ni en
  los conteos (solo `Prediccion.con_sombra` las ve). Modelos → Supervisión
  muestra la comparación (`/api/modelos/comparacion-sombra/`).
- Resultado al 17-nov (791 ejecuciones evaluables, 96 no completadas;
  IC 95 %: Wilson en tasas, bootstrap pareado de 1.000 remuestreos):

  | Versión | Tasa bajo | Tasa medio | Tasa alto | Brier | PR-AUC |
  |---|---|---|---|---|---|
  | v2 | 5,9 % (40/678) | 28,6 % (12/42) | 62,0 % (44/71) | 0,084 [0,068–0,101] | 0,506 [0,410–0,609] |
  | v1.1 | 7,2 % (51/710) | 41,2 % (14/34) | 66,0 % (31/47) | 0,087 [0,070–0,103] | 0,492 [0,397–0,594] |
  | v1 | 9,4 % (70/743) | 35,3 % (6/17) | 64,5 % (20/31) | 0,092 [0,075–0,109] | 0,412 [0,319–0,511] |

  v2 supera a v1 de forma significativa (diferencia de Brier +0,0075
  [0,0025–0,0135] y de PR-AUC −0,094 [−0,149 – −0,043] a favor de v2).
  Frente a v1.1, v2 es mejor en los valores puntuales y detecta más fallos
  en el nivel alto (44 frente a 31), pero los IC de la diferencia incluyen
  el 0 (Brier +0,0026 [−0,0018–0,0073]; PR-AUC −0,014 [−0,053–0,029]):
  no es concluyente. Tabla completa y conclusión en
  `informes/comparacion_sombra_v2.md` (guardado antes de ocultar v1.1);
  desde entonces la comparación de la plataforma muestra v2 y v1.

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
  `revision_dev`, `revision_lider` (contraseñas de prueba en
  `datos_prueba/usuarios_prueba.md`) y `analisis_lote` (cuenta interna del
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
- Migraciones hasta la 0026: `trx_restablecimiento_clave` (0023–0024),
  `trx_informe_cumplimiento` y `trx_descarga_informe` (0025–0026), con los
  mismos nombres ER y columnas de auditoría.
- Diagrama actualizado (23-nov, con las tres tablas anteriores):
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

## 4. Pendientes (por prioridad)

**Alta**
0. **v1 quedó activo el 23-nov a las 10:36** (Modelos → «Activar», cuenta
   `admin`; v2 inactivo). No hay predicciones con v1 desde entonces, pero el
   lote falla en cada pasada («El modelo v1 … no tiene fecha_corte», código
   1 desde las 12:00) y los análisis nuevos usarían v1. Decidir si se
   reactiva v2 (respaldo antes). Exportar la base para compartirla solo
   después de corregirlo.
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
11. `datos_prueba/usuarios_prueba.md` publica en el repositorio (público) las
    contraseñas de prueba de las cuentas `revision_*`, que también vienen en
    el respaldo que se comparte. Cambiarlas antes de exponer la plataforma
    fuera del equipo.
12. Confirmar el punto 5 del 23-nov («Enlace discreto», texto cortado): se
    implementó un enlace «Ver la ejecución en GitHub».
13. Probar en el navegador la navegación con URL (atrás/adelante, F5,
    login con regreso a la dirección pedida); las pruebas automáticas cubren
    la lógica, no el navegador real.

**Hecho del 18 al 23-nov**
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
