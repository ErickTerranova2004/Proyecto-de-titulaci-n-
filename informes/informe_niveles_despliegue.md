# Niveles de evidencia de fallo de despliegue (GHALogs)

> Etiquetas inferidas a partir de pasos ejecutados (log_insights). No son resultados confirmados por logs completos. 'Evidencia alta' = el despliegue fue el último paso de su job, nada empezó después y duró al menos 3 veces la mediana de los despliegues exitosos del mismo workflow.

- Workflows analizados: 1,290
- Ejecuciones: 6,183

## Ejecuciones por nivel de evidencia y tipo de entorno

| Nivel | aplicación | vista previa | efímero de pruebas |
|---|---:|---:|---:|
| despliegue exitoso | 2,353 | 764 | 1,182 |
| excluida (action_required) | 0 | 3 | 0 |
| excluida (cancelled) | 17 | 7 | 12 |
| excluida (skipped) | 8 | 2 | 0 |
| fallo antes del despliegue | 242 | 165 | 60 |
| fallo en despliegue - evidencia alta | 6 | 3 | 1 |
| fallo en despliegue - evidencia media | 52 | 21 | 17 |
| fallo en despliegue - evidencia media (sin referencia) | 111 | 36 | 11 |
| fallo en otro job; despliegue completado | 39 | 13 | 2 |
| fallo tras ejecutar el despliegue (paso posterior) | 164 | 32 | 409 |
| éxito sin despliegue ejecutado | 286 | 162 | 3 |

## Resumen para la variable objetivo (entorno de aplicación)

- Despliegues exitosos: 2,353
- Fallos en despliegue (alta + media): 169
- Fallos en despliegue con evidencia alta: 6
- Fallos en despliegue de workflows que fallan siempre: 105
- Repositorios con fallos en despliegue: 70
- Workflows con fallos y éxitos de despliegue: 38

## Fallos con evidencia alta (entorno de aplicación)

| Repositorio | Ruta | Fecha | Despliegue (s) | Mediana éxito (s) |
|---|---|---|---:|---:|
| argentlabs/dappland | .github/workflows/deploy.yml | 2023-11-12T14:15:34Z | 105 | 31 |
| chainsafe/gossamer | .github/workflows/staging.yml | 2023-09-23T21:16:07Z | 1867 | 236 |
| chainsafe/gossamer | .github/workflows/staging.yml | 2023-09-25T15:22:10Z | 1870 | 236 |
| chainsafe/gossamer | .github/workflows/staging.yml | 2023-10-03T14:41:00Z | 1871 | 236 |
| chainsafe/gossamer | .github/workflows/staging.yml | 2023-10-03T19:13:16Z | 1882 | 236 |
| ever-co/ever-gauzy | .github/workflows/deploy-fly-demo.yml | 2023-11-11T08:11:53Z | 63 | 3 |
