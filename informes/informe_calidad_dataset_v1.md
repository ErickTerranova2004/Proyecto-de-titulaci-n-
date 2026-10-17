# Informe de calidad del dataset de riesgo de despliegue

## Procedencia

- Fuente: GHALogs v1.0.1 (Zenodo 14796970, CC BY-SA 4.0), `runs.json.gz` (MD5 verificado en registro_datasets.csv).
- Selección: workflows con pasos reales de despliegue ejecutados (find_deploy_runs.py) en entornos de aplicación (label_deploy_runs.py).
- Script: build_dataset.py. Datos originales sin modificar.
- Licencia del dataset derivado: CC BY-SA 4.0 (compartir igual).

## Definición de fila y etiqueta

- Fila: un intento (run_id + run_attempt) de un workflow de despliegue.
- y = 1: el intento de despliegue no se completó con éxito; y = 0: despliegue ejecutado y workflow exitoso.

## Recuento

- Filas del entorno de aplicación antes de depurar: 3,278
- Duplicados por repositorios renombrados eliminados: 124
- Excluidas por no tener intento de despliegue o ser ambiguas: 329
- Sin metadatos en runs.json.gz: 0
- Filas finales: 2,825
- Positivos (y = 1): 553 (19.6 %)
- Repositorios: 414 | workflows: 684
- Filas de workflows que fallan siempre: 208

### Niveles de evidencia de origen (tras eliminar duplicados)

| Nivel | Filas |
|---|---:|
| despliegue exitoso | 2,272 |
| éxito sin despliegue ejecutado | 270 |
| fallo antes del despliegue | 229 |
| fallo tras ejecutar el despliegue (paso posterior) | 160 |
| fallo en despliegue - evidencia media (sin referencia) | 110 |
| fallo en despliegue - evidencia media | 48 |
| fallo en otro job; despliegue completado | 36 |
| excluida (cancelled) | 15 |
| excluida (skipped) | 8 |
| fallo en despliegue - evidencia alta | 6 |

## Partición temporal

- Corte: 2023-11-09 03:05:45+00:00

| Partición | Filas | Tasa de y = 1 |
|---|---:|---:|
| entrenamiento | 2,118 | 18.3 % |
| prueba | 707 | 23.5 % |

- Repositorios de prueba también presentes en entrenamiento: 100 de 150

## Valores faltantes (%)

Los faltantes de historial son estructurales: primera ejecución observada del workflow o repositorio. No se imputan aquí.

| Variable | % faltante |
|---|---:|
| wf_tasa_fallo_prev | 18.3 |
| wf_ultimo_fallo | 18.3 |
| wf_horas_desde_ultimo | 18.2 |
| wf_duracion_media_prev_min | 18.2 |
| repo_tasa_fallo_prev | 3.9 |

## Estadísticos descriptivos

| Variable | Media | Mediana | Mín | Máx |
|---|---:|---:|---:|---:|
| msg_len | 162.26 | 65.0 | 3.0 | 11260.0 |
| msg_lineas | 5.03 | 1.0 | 1.0 | 498.0 |
| msg_merge | 0.22 | 0.0 | 0.0 | 1.0 |
| msg_revert | 0.01 | 0.0 | 0.0 | 1.0 |
| msg_fix | 0.19 | 0.0 | 0.0 | 1.0 |
| msg_feat | 0.13 | 0.0 | 0.0 | 1.0 |
| msg_deps | 0.13 | 0.0 | 0.0 | 1.0 |
| msg_docs | 0.05 | 0.0 | 0.0 | 1.0 |
| msg_ci | 0.05 | 0.0 | 0.0 | 1.0 |
| autor_bot | 0.1 | 0.0 | 0.0 | 1.0 |
| reejecutado_por_otro | 0.0 | 0.0 | 0.0 | 1.0 |
| rama_principal | 0.59 | 1.0 | 0.0 | 1.0 |
| rama_bot | 0.0 | 0.0 | 0.0 | 1.0 |
| rama_tag | 0.12 | 0.0 | 0.0 | 1.0 |
| tiene_pr | 0.34 | 0.0 | 0.0 | 1.0 |
| es_reintento | 0.03 | 0.0 | 0.0 | 1.0 |
| hora_utc | 11.8 | 12.0 | 0.0 | 23.0 |
| dia_semana | 2.86 | 3.0 | 0.0 | 6.0 |
| fin_de_semana | 0.19 | 0.0 | 0.0 | 1.0 |
| retraso_commit_run_min | 6306.03 | 0.28 | 0.0 | 927590.3 |
| wf_n_prev | 2.45 | 2.0 | 0.0 | 14.0 |
| wf_tasa_fallo_prev | 0.19 | 0.0 | 0.0 | 1.0 |
| wf_ultimo_fallo | 0.19 | 0.0 | 0.0 | 1.0 |
| wf_horas_desde_ultimo | 110.38 | 17.66 | 0.0 | 2322.4 |
| wf_duracion_media_prev_min | 36.34 | 4.7 | 0.07 | 21605.68 |
| repo_n_prev | 39.46 | 17.0 | 0.0 | 491.0 |
| repo_tasa_fallo_prev | 0.18 | 0.1 | 0.0 | 1.0 |
| repo_n_workflows_prev | 10.08 | 5.0 | 0.0 | 109.0 |

## Control de fuga de información

- Excluidas como predictoras: conclusion, updated_at, duración y pasos de la ejecución actual, nivel de evidencia.
- El historial usa solo ejecuciones que empezaron antes (run_started_at) de la ejecución evaluada.
- Nombres y correos de autores no se guardan; solo un hash.

## Limitaciones

- GHALogs guarda como máximo 5 ejecuciones por workflow: el historial por workflow es corto.
- Las etiquetas se infieren de pasos ejecutados, no de logs completos; y = 1 incluye fallos de compilación o pruebas dentro del pipeline de despliegue.
- Sin métricas del cambio de código (archivos, líneas): requieren la API de GitHub con token (trabajo futuro).
