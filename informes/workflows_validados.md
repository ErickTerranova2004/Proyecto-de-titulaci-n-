# Workflows validados como despliegue a aplicaciones

Generado con `manage.py validar_workflows_dataset` a partir del **dataset v1.1** (2026-10-15). Detalle por workflow en `informes/workflows_validados.csv`. La evidencia de cada workflow está en el campo `Workflow.evidencia_validacion`.

## Criterio

Un workflow se marca `despliegue_validado = True` solo si cumple las dos condiciones:
1. Pertenece al dataset final vigente (`datos_procesados/dataset_riesgo_despliegue_v1_1.csv`), con filas etiquetadas o ambiguas.
2. En GHALogs ejecutó **al menos un paso real de despliegue en un entorno de aplicación**. Desde v1.1, el entorno se decide **por workflow**: no cuentan los workflows con alguna ejecución en un clúster efímero de prueba, ni los de vista previa, ni GitHub Pages.

`validado_por` queda vacío porque la validación es automática y reproducible. Las validaciones manuales desde el admin de Django registran al usuario y la fecha, y este comando no las modifica.

## Resultado (dataset v1.1)

| Concepto | Total |
|---|---:|
| Workflows del dataset v1.1 | 639 |
| Validados | **639** |
| Validaciones automáticas de v1 retiradas (ya no están en el dataset vigente) | 28 |
| Workflows registrados sin validar en la base de datos (incluye los 22 detectados en v1) | 49 |

## Historia de este control

Con el dataset v1 se detectaron 22 workflows que solo desplegaban en clústeres efímeros de prueba, pero tenían 28 filas con y = 1. La clasificación del entorno por ejecución no los reconocía cuando la ejecución fallaba antes de crear el clúster. Este hallazgo dio lugar a la auditoría de todas las reglas y al dataset v1.1 (ver `docs/evaluacion_y_validez.md`, sección 2).
