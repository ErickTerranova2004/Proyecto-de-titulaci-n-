# Plan de pruebas

## 1. Pruebas automatizadas del backend (`manage.py test riesgo`)

Resultado del 2026-10-15, tras la migración inicial limpia y con el **modelo v1.1 (Random Forest) activo**: **37 pruebas, todas correctas** (`Ran 37 tests ... OK`).

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
| T20 | Crea la predicción con trazabilidad (commit, 3 ejecuciones previas, códigos de regla, autor sin datos personales) | Integración |
| T21 | Rechaza workflows no validados o no registrados (400, `workflow_no_validado`) | Funcional |
| T22 | Rechaza repositorios no registrados (404) | Funcional |
| T23 | Exige autenticación (401) | Seguridad |
| T24 | Exige un rol (403) | Seguridad |
| T25 | Valida repositorio, ruta y SHA (400) | Seguridad |
| T26 | Commit no encontrado en GitHub → 404 sin guardar | Integración |
| T27 | Sin acceso al repositorio no puede predecir (403, `sin_acceso`) | Seguridad |
| T28 | El administrador predice en cualquier repositorio | Seguridad |
| T29 | `/api/repositorios/` lista solo los repositorios asignados y sus workflows validados | Seguridad |
| T30 | Visibilidad: el desarrollador ve las propias, el líder todas las de sus repositorios, el admin todo; el resumen se filtra igual | Seguridad |
| T31 | Detalle de una predicción sin acceso → 404 | Seguridad |
| T32 | Al quitar el acceso, el usuario deja de ver las predicciones | Seguridad |
| T33 | Verificar enlaza solo la ejecución del mismo workflow y commit iniciada después, y guarda etiqueta, subtipo y paso fallido | Integración |
| T34 | Sin ejecución posterior → `pendiente`, sin enlazar | Integración |
| T35 | Un caso ambiguo no se etiqueta como fallo (y = null) | Integración |
| T36 | No se puede verificar una predicción sin acceso (404) | Seguridad |
| T37 | Solo el administrador activa modelos | Seguridad |

## 2. Pruebas de punta a punta (manual)

| Fecha | Paso | Resultado |
|---|---|---|
| 2026-10-15 | Inicio de sesión a través del proxy de Vite | OK |
| 2026-10-15 | Predicción real sobre `novuhq/novu` `deploy.yml` (antes de exigir workflows validados) | OK: riesgo bajo (8,3 %) |
| 2026-10-15 | `validar_workflows_dataset` sobre la base de datos limpia (dataset v1) | OK: 414 repositorios; 662 workflows validados y 22 sin validar |
| 2026-10-15 | `registrar_modelo --modelo v1.1` + `validar_workflows_dataset` (dataset v1.1) | OK: v1.1 activo y v1 inactivo; 639 validados y 28 validaciones de v1 retiradas |
| 2026-10-15 | `train_models.py` modificado reproduce v1 | OK: métricas idénticas a las publicadas |
| 2026-10-15 | `npm run build` del frontend con selección de repositorio y workflow, códigos de regla y verificación | OK |

Con la nueva regla, `novuhq/novu` `deploy.yml` ya no se admite: no está en el dataset. Un administrador tendría que validarlo con su evidencia.

## 3. Pruebas funcionales pendientes para el usuario

- Crear usuarios de los tres roles, asignarles repositorios en *Accesos a repositorios* y comprobar qué ve cada uno en la interfaz.
- Hacer un análisis sobre un repositorio validado con `GITHUB_TOKEN` configurado y, tras su siguiente ejecución, usar "Verificar resultado real".
- Repetir `migrate`, `registrar_modelo` y `validar_workflows_dataset` sobre PostgreSQL.
