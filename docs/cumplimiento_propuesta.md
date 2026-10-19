# Cumplimiento de la propuesta aprobada (ECP)

Contraste entre lo comprometido en la propuesta *"Plataforma predictiva basada en IA para estimar el riesgo de despliegue de aplicaciones empresariales"* y lo implementado. Revisión del 2026-10-16.

Estado: **Cumple** = implementado y probado; **Parcial** = implementado con una limitación declarada; **Pendiente** = no implementado.

## Funciones y componentes

| Requisito de la propuesta | Implementación | Evidencia | Estado |
|---|---|---|---|
| Integración con GitHub (repositorios, commits, ejecuciones de pipelines) | `services/github.py` (cliente REST de solo lectura, con filtro de secretos en los registros) | Pruebas T20, T26, T33 | Cumple |
| Recopilación automática de datos, independiente de los análisis | `services/sincronizacion.py`, comando `sincronizar_github` y `POST /api/repositorios/{id}/sincronizar/` | Prueba T42; [manual §5](manual_instalacion.md) | Cumple (la programación periódica se hace con el programador de tareas del sistema) |
| Workflows vigentes en GitHub | Campo `Workflow.disponible_github` y comando `verificar_workflows_github` (consulta raw.githubusercontent.com, sin gastar cuota de la API) | Pruebas T43, T44; `informes/workflows_no_disponibles.csv` | Cumple: 268 de los 639 workflows validados ya no existen en GitHub (renombrados o eliminados después de 2023); se conservan para trazabilidad pero no se ofrecen en nuevos análisis. Quedan 371 workflows en 279 repositorios |
| Métricas de cambios de código | `Commit.archivos_modificados`, `adiciones`, `eliminaciones` | Prueba T20 | Parcial: se guardan y se muestran, pero **no son variables del modelo v1.1** porque GHALogs no las contiene; incorporarlas exige un nuevo dataset |
| Preparación de datos y dataset histórico | `find_deploy_runs.py`, `build_dataset_v1_1.py` | `informes/informe_calidad_dataset_v1_1.md` | Cumple |
| Entrenamiento, comparación y selección del modelo | `train_models.py`, `compare_versions.py` | `informes/fase5_modelos_v1_1.md`: Random Forest calibrado, PR-AUC 0,677 en la partición temporal de prueba | Cumple |
| Estimación del riesgo antes del despliegue | `POST /api/predicciones/`; solo usa ejecuciones completadas antes del análisis | Pruebas T02, T20 | Cumple |
| Explicabilidad (IA explicable) | SHAP por predicción (`prediccion.factores`) | Pantalla Resultado; prueba T20 | Cumple |
| Recomendaciones | Reglas con código asociadas a los factores que suben el riesgo | Prueba T06 | Cumple |
| Panel de control | Pantalla Panel (indicadores, gráficos por nivel, día y tendencia, repositorios con mayor riesgo) | [arquitectura: pantalla → dato](arquitectura.md) | Cumple |
| Historial de análisis | Pantalla Historial y `GET /api/predicciones/` | Pruebas T30–T32 | Cumple |
| Decisión del líder técnico (autorizar, posponer o pedir revisión) | `DecisionDespliegue` y `POST /api/predicciones/{id}/decision/`; formulario en Resultado | Pruebas T39, T40 | Cumple |
| Administración de integraciones | Pantalla Integraciones y `GET /api/integraciones/` (cuota de la API y token configurado sí/no; el token nunca se envía) | Prueba T41 | Cumple |
| Supervisión del modelo | `GET /api/modelos/{id}/supervision/`: tasa observada por nivel y Brier sobre predicciones verificadas; activación de versiones | Pruebas T37, T38 | Cumple |
| Roles: desarrollador, líder técnico y administrador | Grupos de Django, permisos de DRF y `AccesoRepositorio` | Pruebas T24, T27–T32, T40–T42 | Cumple |
| Seguridad | Autenticación por token, límite de solicitudes, secretos en `backend/.env`, autor del commit solo como hash | Prueba T05; [arquitectura §Seguridad](arquitectura.md) | Cumple |
| Stack: Django + DRF, React | `backend/`, `frontend/` | `npm run build`; `manage.py test riesgo` (44 pruebas) | Cumple |
| Base de datos PostgreSQL | `settings.py` usa PostgreSQL cuando `POSTGRES_DB` está definido | — | **Pendiente**: el entorno de desarrollo usa SQLite porque PostgreSQL no está instalado (requiere permisos de administrador del equipo). No hay cambios de código pendientes: basta configurar las variables `POSTGRES_*` y ejecutar `migrate` |
| Plan de pruebas | [plan_pruebas.md](plan_pruebas.md) | 44 pruebas automatizadas y pruebas manuales de punta a punta | Cumple |

## Alcance que se debe declarar en la tesis

- **Variable objetivo.** La plataforma estima la probabilidad de que un intento de despliegue **no se complete** en GitHub Actions. No es una "falla real de despliegue" ni un incidente en producción. Justificación: [informes/fase2_variable_objetivo.md](../informes/fase2_variable_objetivo.md).
- **Casos no evaluables.** Las ejecuciones ambiguas, sin intento de despliegue o canceladas se conservan, pero no cuentan como acierto ni como fallo, ni en el entrenamiento ni en la supervisión.
- **Validez.** Las amenazas a la validez y la generalización se tratan en [evaluacion_y_validez.md](evaluacion_y_validez.md).
- **Supervisión.** Con pocas predicciones verificadas, la tasa observada por nivel no es concluyente; la pantalla lo advierte.
