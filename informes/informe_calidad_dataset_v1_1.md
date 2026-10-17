# Informe de calidad del dataset v1.1

## Procedencia

- Fuente: GHALogs v1.0.1 (Zenodo 14796970, CC BY-SA 4.0).
- Script: `build_dataset_v1_1.py`. v1 se conserva en `datos_procesados/dataset_riesgo_despliegue_v1.csv`.
- Variables predictoras: mismas funciones que v1 (`build_dataset.py`).

## Auditoría de las reglas de inclusión y etiquetado de v1

'Filas afectadas' son filas del dataset v1 cuya decisión tomó esa regla (una fila puede verse afectada por varias reglas).

| Regla de v1 | ¿Depende del resultado? | Filas afectadas | y = 1 | y = 0 | Decisión v1.1 |
|---|---|---:|---:|---:|---|
| Entorno efímero decidido por ejecución (label_deploy_runs.py) | Sí: el clúster solo aparece si la ejecución llegó a crearlo | 63 | 60 | 3 | Corregida: entorno por workflow |
| Intención de despliegue inferida del propio resultado: fallo sin paso de despliegue → y = 1; éxito sin paso → excluido | Sí: el paso de despliegue solo existe si la ejecución avanzó | 229 | 229 | 0 | Corregida: intención leave-one-out por contexto (además, 271 éxitos sin despliegue excluidos en v1 se reevalúan) |
| Ejecución sin log_insights tratada como 'sin paso de despliegue' | Sí: la falta de log puede deberse al resultado (p. ej., fallo de arranque) | 52 | 52 | 0 | Corregida: ambiguo |
| Fallo en otro job con el despliegue completado → excluido | Sí (solo existe en fallos), inevitable: la etiqueta es desconocida | 36 | 0 | 0 | Se conserva como 'ambiguo' (antes se borraba) |
| Excluir cancelled / skipped / action_required | Sí (es un resultado), inevitable: no hay etiqueta | 23 | 0 | 0 | Sin cambio |
| Vista previa por evento de pull request o ruta 'preview' | No: el evento y la ruta se conocen antes de ejecutar | 0 | 0 | 0 | Sin cambio (ruta evaluada por workflow) |
| Deduplicar repositorios renombrados prefiriendo el registro con más log | No: es la misma ejecución; depende de la disponibilidad del log | 124 | 0 | 0 | Sin cambio |
| Selección de workflows: alguna ejecución ejecutó un paso de despliegue (find_deploy_runs.py) | Sí, a nivel de workflow: un workflow cuyas ejecuciones observadas fallaron todas antes de desplegar no entra | — | — | — | No corregible sin el YAML histórico (≈1.300 consultas a la API con token); se declara como sesgo de selección |
| Variables de historial (ejecuciones anteriores) | No: solo usan ejecuciones que empezaron antes | 0 | 0 | 0 | Sin cambio |
| Indicador 'workflow que siempre falla' | Sí (usa todas las ejecuciones), pero solo para el análisis de sensibilidad; no es variable ni filtro | 0 | 0 | 0 | Sin cambio |

## Clasificación de las ejecuciones de workflows candidatos

- Ejecuciones (sin duplicados): 6,001; workflows: 1,149

| Entorno del workflow | Workflows | Ejecuciones |
|---|---:|---:|
| aplicación | 728 | 3,808 |
| efímero de pruebas | 364 | 1,879 |
| vista previa | 57 | 314 |

### Ejecuciones de workflows de aplicación por estado y motivo

| Estado | Motivo | Ejecuciones | y |
|---|---|---:|---|
| ambiguo | fallo en otro job con el despliegue completado | 32 | — |
| ambiguo | intención de despliegue indeterminada (ninguna otra ejecución del mismo contexto) | 300 | — |
| ambiguo | sin log_insights: no se sabe hasta dónde llegó | 224 | — |
| ambiguo | éxito sin paso de despliegue en un contexto que despliega | 35 | — |
| etiquetada | despliegue completado | 2,014 | 0 |
| etiquetada | fallo antes del despliegue | 111 | 1 |
| etiquetada | fallo en el paso de despliegue (inferido) | 151 | 1 |
| etiquetada | fallo tras ejecutar el despliegue (paso posterior) | 116 | 1 |
| excluida | evento de pull request (vista previa) | 742 | — |
| excluida | resultado cancelled | 13 | — |
| excluida | resultado skipped | 5 | — |
| excluida | sin intento de despliegue en este contexto | 65 | — |

## Dataset v1.1

- Filas totales: 2,983 (etiquetadas: 2,392; **ambiguas conservadas y excluidas del entrenamiento: 591**)
- Positivos (y = 1) entre las etiquetadas: 378 (15.8 %)
- Repositorios (etiquetadas): 348 | workflows: 525
- Filas etiquetadas de workflows que fallan siempre: 148

### Ambiguas por motivo

| Motivo | Filas |
|---|---:|
| intención de despliegue indeterminada (ninguna otra ejecución del mismo contexto) | 300 |
| sin log_insights: no se sabe hasta dónde llegó | 224 |
| éxito sin paso de despliegue en un contexto que despliega | 35 |
| fallo en otro job con el despliegue completado | 32 |

## Partición temporal (misma regla que v1)

- Corte: 2023-11-08 20:30:14.750000+00:00

| Partición | Filas etiquetadas | Tasa de y = 1 |
|---|---:|---:|
| entrenamiento | 1,794 | 14.5 % |
| prueba | 598 | 19.6 % |

## Valores faltantes en filas etiquetadas (%)

| Variable | % faltante |
|---|---:|
| wf_tasa_fallo_prev | 17.6 |
| wf_ultimo_fallo | 17.6 |
| wf_horas_desde_ultimo | 17.5 |
| wf_duracion_media_prev_min | 17.5 |
| repo_tasa_fallo_prev | 3.8 |

## Limitaciones que permanecen

- Sesgo de selección de workflows (ver la auditoría): solo entran workflows con al menos una ejecución que llegó a desplegar.
- La intención de despliegue se infiere de otras ejecuciones del mismo contexto; con un máximo de 5 ejecuciones por workflow, muchos contextos quedan indeterminados (ambiguos).
- Dentro de un workflow, el resultado de las demás ejecuciones puede estar correlacionado con el de la ejecución evaluada.
