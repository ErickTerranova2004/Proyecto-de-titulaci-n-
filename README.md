# Plataforma predictiva de riesgo de despliegue

Tesis: *Plataforma predictiva basada en IA para el riesgo de despliegue de aplicaciones empresariales*.

La plataforma estima la **probabilidad de que un intento de despliegue no se complete con éxito** en su pipeline de GitHub Actions. Explica la estimación con SHAP y propone recomendaciones basadas en reglas. **No predice incidentes en producción**; la justificación del alcance está en [informes/fase2_variable_objetivo.md](informes/fase2_variable_objetivo.md).

## Estructura

| Ruta | Contenido |
|---|---|
| `Datos/` | Datasets originales (solo lectura, no versionados) |
| `inspect_*.py`, `register_file.py` | Exploración inicial y registro de datasets |
| `find_deploy_runs.py` | Detecta ejecuciones con pasos reales de despliegue (`log_insights`) |
| `inspect_workflow_runs.py` | Muestra los pasos ejecutados de un workflow concreto |
| `label_deploy_runs.py` | Asigna niveles de evidencia de fallo de despliegue |
| `build_dataset.py` | Construye el dataset v1 (conservado para trazabilidad) |
| `build_dataset_v1_1.py` | Dataset v1.1 vigente: corrige las reglas que dependían del resultado e incluye la auditoría |
| `train_models.py` | Entrena, evalúa, calibra y explica los modelos (`--version`) |
| `compare_versions.py` | Compara dos versiones con los artefactos guardados |
| `datos_procesados/` | Datasets `dataset_riesgo_despliegue_v1.csv` y `_v1_1.csv` (vigente) |
| `modelos/` | Modelos y metadatos: `modelo_riesgo_v1.*` y `modelo_riesgo_v1_1.*` (activo) |
| `informes/` | Informes de cada fase y figuras |
| `backend/` | API en Django + DRF (PostgreSQL) |
| `frontend/` | Interfaz en React (Vite) |
| `docs/` | Manual, arquitectura, plan de pruebas, validez y [cumplimiento de la propuesta](docs/cumplimiento_propuesta.md) |

## Reproducir los resultados

Ver [docs/manual_instalacion.md](docs/manual_instalacion.md), sección "Reproducir el pipeline de datos y el modelo".
