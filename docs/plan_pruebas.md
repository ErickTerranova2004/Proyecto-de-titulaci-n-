# Plan de pruebas

## 1. Pruebas automatizadas del backend (`manage.py test riesgo`)

Resultado del 2026-10-17, con la migración `0003` (disponibilidad de workflows en GitHub) y el **modelo v1.1 (Random Forest) activo**: **44 pruebas, todas correctas** (`Ran 44 tests ... OK`).

### Variables, seguridad y recomendaciones (`test_features.py`)

| ID | Prueba | Tipo |
|---|---|---|
| T01 | Historial del workflow: solo las 4 previas más recientes | Unitaria |
| T02 | Excluye ejecuciones futuras o en curso (sin fuga de información) | Unitaria |
| T03 | Historial del repositorio por workflow | Unitaria |
| T04 | Variables del commit (mensaje, autor bot, rama, retraso) | Unitaria |
| T05 | El filtro de registros oculta tokens de GitHub | Seguridad |
| T06 | La recomendación solo aparece si el factor aumenta el riesgo, y guarda el código de la regla | Unitaria |

### Regla de etiquetado del resultado real (`test_etiquetado.py`)

| ID | Prueba |
|---|---|
| T07 | Éxito con paso de despliegue → `despliegue_completado` |
| T08 | Éxito sin paso de despliegue → `excluida_sin_intento` |
| T09 | Fallo antes del despliegue → `despliegue_no_completado` / `antes_del_despliegue`, con el paso fallido |
| T10 | Fallo en el paso de despliegue → subtipo `en_paso_de_despliegue` |
| T11 | Fallo posterior en el mismo job → subtipo `posterior_mismo_job` |
| T12 | Fallo en otro job con el despliegue completado (caso novu) → `excluida_ambigua` |
| T13 | Ejecución cancelada → `excluida_otro_resultado` |

### Modelo de datos (`test_modelo_datos.py`)

| ID | Prueba |
|---|---|
| T14 | `EjecucionWorkflow`: único por (`run_id`, `run_attempt`); dos intentos de la misma ejecución son dos filas |
| T15 | `AccesoRepositorio`: único por par usuario–repositorio |
| T16 | `Workflow`: único por (repositorio, path) |
| T17 | Un workflow validado exige evidencia |
| T18 | `ejecucion_real` válida: mismo workflow y commit, iniciada después |
| T19 | `ejecucion_real` rechaza otro workflow, otro commit o una ejecución anterior |

### API (`test_api.py`)

| ID | Prueba | Tipo |
|---|---|---|
| T20 | Crea la predicción con trazabilidad (commit, 3 ejecuciones previas, códigos de regla, autor sin datos personales) y guarda las métricas del cambio (2 archivos, +12 / −3) | Integración |
| T21 | Rechaza workflows no validados o no registrados (400, `workflow_no_validado`) | Funcional |
| T22 | Rechaza repositorios no registrados (404) | Funcional |
| T23 | Exige autenticación (401) | Seguridad |
| T24 | Exige un rol (403) | Seguridad |
| T25 | Valida repositorio, ruta y SHA (400) | Seguridad |
| T26 | Commit no encontrado en GitHub → 404 sin guardar | Integración |
| T27 | Sin acceso al repositorio no puede predecir (403, `sin_acceso`) | Seguridad |
| T28 | El administrador predice en cualquier repositorio | Seguridad |
| T29 | `/api/repositorios/` lista solo los repositorios asignados y sus workflows validados | Seguridad |
| T30 | Visibilidad: el desarrollador ve las propias, el líder todas las de sus repositorios, el admin todo | Seguridad |
| T31 | Detalle de una predicción sin acceso → 404 | Seguridad |
| T32 | Al quitar el acceso, el usuario deja de ver las predicciones | Seguridad |
| T33 | Verificar enlaza solo la ejecución del mismo workflow y commit iniciada después, y guarda etiqueta, subtipo y paso fallido | Integración |
| T34 | Sin ejecución posterior → `pendiente`, sin enlazar | Integración |
| T35 | Un caso ambiguo no se etiqueta como fallo (y = null) | Integración |
| T36 | No se puede verificar una predicción sin acceso (404) | Seguridad |
| T37 | Solo el administrador activa modelos | Seguridad |
| T38 | Supervisión: tras verificar, cuenta el caso evaluable en su nivel y calcula Brier; el desarrollador recibe 403 | Funcional |
| T39 | El líder técnico registra una decisión (201) y el desarrollador la ve en el detalle | Funcional |
| T40 | Decisión: desarrollador 403, líder sin acceso al repositorio 404, decisión no válida 400 | Seguridad |
| T41 | Integraciones: solo el administrador; la respuesta no contiene el token | Seguridad |
| T42 | Sincronizar: solo el administrador; guarda las ejecuciones de los workflows validados | Integración |
| T43 | Workflow cuyo archivo ya no existe en GitHub: responde 404, queda como no disponible, deja de ofrecerse y se rechaza con `workflow_no_disponible` | Integración |
| T44 | Comando `verificar_workflows_github`: marca disponibles y no disponibles según la respuesta de GitHub | Integración |
| T50 | El líder fija una fecha límite al decidir; solo el desarrollador dueño recibe la asignación (por vencer, no vista) | Funcional |
| T51 | Fecha límite pasada rechazada (400) al decidir y al cambiarla | Seguridad |
| T52 | Fecha límite: sin decisión previa 400; el desarrollador no puede fijarla (403); un líder de otro repositorio no ve la predicción (404); líder y administrador sí | Seguridad |
| T53 | Solo el desarrollador dueño marca vista y cumplida (líder y admin 403, otro desarrollador 404); el líder ve las marcas | Seguridad |
| T54 | Cambiar la fecha límite deja la asignación como no vista | Funcional |
| T55 | La asignación usa solo la última decisión de la predicción | Funcional |
| T56 | Estado de la asignación: pendiente, por vencer (0 o 1 días), vencida y cumplida | Unitaria |
| T57 | `/api/repositorios/?todos=1` por rol: incluye repositorios sin workflows; por defecto no cambia; sin rol 403 | Seguridad |
| T58 | `/api/resumen-admin/`: líder y desarrollador 403; usuarios por rol de mayor jerarquía (suman el total) y conteo de workflows | Seguridad |
| T59 | Comando `crear_usuario`: repetible sin duplicar, `--repos` fija los accesos, el administrador es superusuario, repositorio inexistente no crea nada | Funcional |
| T60 | Un nuevo análisis con `atiende_decision` enlaza la respuesta, marca la asignación cumplida y vista, conserva `decision` y `comentario`; el líder ve el nuevo análisis, su nivel y el comentario | Funcional |
| T61 | Una asignación no se atiende dos veces (`asignacion_ya_atendida`) | Seguridad |
| T62 | Respuesta: otro desarrollador o decisión inexistente (`asignacion_no_encontrada`), otro workflow (`asignacion_otro_workflow`); no se enlaza nada | Seguridad |
| T63 | Una autorización no se atiende con análisis (`asignacion_no_atendible`); "Entendido" solo para autorizaciones | Funcional |
| T64 | Una decisión que ya no es la última no se atiende (`asignacion_no_vigente`); una autorización sin fecha llega como asignación y se cierra con Entendido | Funcional |
| T65 | Verificar: ejecución exitosa enlazada (`despliegue_completado`, y = 0) | Integración |
| T66 | Verificar: ejecución en curso no se enlaza (pendiente) | Integración |
| T67 | Verificar: reintento (`run_attempt` = 2) etiquetado con los jobs de ese intento | Integración |
| T68 | Supervisión: 4 predicciones, 3 verificadas, 2 evaluables (la ambigua no cuenta), Brier = media de (p − y)², `predicciones_demostracion` al marcar el repositorio | Funcional |

### Frontend (`npm test`, `node --test`, sin dependencias)

| ID | Caso | Tipo |
|---|---|---|
| F01 | La interfaz de administrador se reinicia si el token pasa a ser de un desarrollador; no se reinicia si usuario y rol coinciden; sí si cambia el rol o caduca la sesión | Unitaria |
| F02 | El foco, la visibilidad y el evento `storage` de la clave del token disparan la comprobación de `/api/yo/` | Unitaria |
| F03 | Panel de administración: si un endpoint falla, las demás tarjetas siguen con sus datos | Unitaria |
| F04 | Un dato inexistente es un estado vacío, distinto de un error; el motivo del error es concreto (403, 401, 0, 404) | Unitaria |

## 2. Pruebas de punta a punta (manual)

| Fecha | Paso | Resultado |
|---|---|---|
| 2026-10-15 | Inicio de sesión a través del proxy de Vite | OK |
| 2026-10-15 | Predicción real sobre `novuhq/novu` `deploy.yml` (antes de exigir workflows validados) | OK: riesgo bajo (8,3 %) |
| 2026-10-15 | `validar_workflows_dataset` sobre la base de datos limpia (dataset v1) | OK: 414 repositorios; 662 workflows validados y 22 sin validar |
| 2026-10-15 | `registrar_modelo --modelo v1.1` + `validar_workflows_dataset` (dataset v1.1) | OK: v1.1 activo y v1 inactivo; 639 validados y 28 validaciones de v1 retiradas |
| 2026-10-15 | `train_models.py` modificado reproduce v1 | OK: métricas idénticas a las publicadas |
| 2026-10-15 | `npm run build` del frontend con selección de repositorio y workflow, códigos de regla y verificación | OK |
| 2026-10-16 | `npm run build` con decisión del líder, supervisión e integraciones; búsqueda de colores fuera de `tokens.css` | OK: sin colores fuera de la paleta |

Con la nueva regla, `novuhq/novu` `deploy.yml` ya no se admite: no está en el dataset. Un administrador tendría que validarlo con su evidencia.
| 2026-10-23 | `manage.py test riesgo` | OK: 59 pruebas |
| 2026-10-23 | `npm run build` del frontend por perfiles (no hay ESLint en el proyecto) | OK |
| 2026-10-23 | `crear_usuario` para `prueba_admin`, `prueba_lider` (2 repositorios) y `prueba_dev` (1); repetido sin duplicar | OK |
| 2026-10-23 | Tres perfiles a la vez por el proxy de Vite: el líder decide con fecha límite sobre un análisis de `prueba_dev`; el desarrollador recibe la asignación (por vencer), la marca vista y cumplida; el líder ve las marcas; fecha pasada 400; `resumen-admin` 403 para líder y desarrollador | OK |
| 2026-10-24 | Diagnóstico del panel de administración con un token real de administrador | Los 8 endpoints responden 200 directamente y por el proxy; los fallos vistos eran 403 pedidos con la sesión de `prueba_dev` (65 en el registro del backend) |
| 2026-10-24 | Proxy de `/admin` tras reiniciar Vite (el reinicio automático había fallado al cambiar `vite.config.js`) | OK: sirve el admin de Django |
| 2026-10-24 | Registro y sincronización de `mastodon/mastodon` (build-nightly) y `Azure-Samples/azure-search-openai-demo` (azure-dev) por la API; `todo-nodejs-mongo` descartado (1 ejecución en 7 semanas) | OK: 20 ejecuciones guardadas en cada uno |
| 2026-10-24 | Prueba de extremo a extremo con GitHub Actions real en el repositorio de demostración `ErickTerranova2004/demo-despliegue-riesgo` (16 ciclos: análisis de `prueba_dev` antes de la ejecución → `workflow_dispatch` o push a `main` desde una rama de preparación → `gh run watch` → Verificar resultado real; 6 fallos provocados) | OK: 16 de 16 verificados; 10 `despliegue_completado` y 6 `despliegue_no_completado`, coincidiendo con el fallo provocado en los 16 casos |
| 2026-10-24 | Respuesta a una asignación por la API con los tres perfiles: el líder pospone el análisis 130, el desarrollador lo atiende con el análisis 131, un segundo intento se rechaza, el líder ve Cumplida con el análisis #131 (Bajo → Bajo) | OK |

## 3. Pruebas funcionales pendientes para el usuario

- Abrir los tres perfiles a la vez (ventana normal, incógnito y otro navegador, con `scripts/iniciar_demo.ps1`) y comprobar en la interfaz: menú de cada rol, campana y aviso del desarrollador, tarjeta "Mis asignaciones", marcar cumplida y ver el cambio en Pendientes del líder.
- Aceptar las notificaciones del navegador en el perfil del desarrollador y comprobar el aviso de una asignación nueva (tarda hasta 60 s).
- Con los tres perfiles a la vez: el desarrollador recibe la ventana emergente al entrar, pulsa Atender ahora, hace el nuevo análisis y la asignación queda cumplida; el líder ve "Cumplida con el análisis #N" y la comparación de riesgo; el administrador ve las cuatro tarjetas con datos o con su estado vacío o error específico.
- Repetir `migrate`, `registrar_modelo` y `validar_workflows_dataset` sobre PostgreSQL.
