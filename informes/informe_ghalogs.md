# Informe GHALogs

## 1. Runs

- Líneas válidas: **580,641** | líneas con error de parseo: **0** | `_id` duplicados: **0**
- Repositorios distintos: 28,658 | workflows distintos: 123,784
- Runs por workflow: media 4.69, mediana 5.0, máx 5 (pocos runs por workflow limitan series temporales por workflow)
- Rango `metadata.created_at`: 2023-06-30T03:01:17Z → 2023-11-14T05:04:46Z
- Runs asociados a pull request (`pull_requests` no vacío): 191,909 | sin `head_sha`: 0

## 2. Claves presentes (nivel superior y `metadata`)

Nivel superior: `_id` (580,641), `repository_name` (580,641), `workflow_path` (580,641), `run_number` (580,641), `run_attempt` (580,641), `metadata` (580,641), `logs_archive` (580,640), `total_logs_size` (526,851), `log_insights` (525,832), `time_to_import` (317,528), `import_date` (235)

`metadata`: `id` (580,641), `name` (580,641), `node_id` (580,641), `head_branch` (580,641), `head_sha` (580,641), `path` (580,641), `display_title` (580,641), `run_number` (580,641), `event` (580,641), `status` (580,641), `conclusion` (580,641), `workflow_id` (580,641), `check_suite_id` (580,641), `check_suite_node_id` (580,641), `url` (580,641), `html_url` (580,641), `pull_requests` (580,641), `created_at` (580,641), `updated_at` (580,641), `actor` (580,641), `run_attempt` (580,641), `referenced_workflows` (580,641), `run_started_at` (580,641), `triggering_actor` (580,641), `jobs_url` (580,641), `logs_url` (580,641), `check_suite_url` (580,641), `artifacts_url` (580,641), `cancel_url` (580,641), `rerun_url` (580,641), `previous_attempt_url` (580,641), `workflow_url` (580,641), `head_commit` (580,641), `repository` (580,641), `head_repository` (580,641)

**Claves relacionadas con despliegues/entornos:** NINGUNA detectada

## 3. Etiqueta `metadata.conclusion`

| conclusion | n | % |
|---|---|---|
| success | 482,830 | 83.15% |
| failure | 91,163 | 15.70% |
| skipped | 4,113 | 0.71% |
| cancelled | 1,713 | 0.30% |
| action_required | 447 | 0.08% |
| startup_failure | 375 | 0.06% |

Fallo entre success+failure: **15.88%** (573,993 runs)

## 4. `status`

| status | n |
|---|---|
| completed | 580,641 |

## 5. Fallo por `event` (success+failure)

| event | runs | success+failure | % fallo |
|---|---|---|---|
| push | 196,669 | 195,593 | 14.16% |
| pull_request | 190,734 | 188,156 | 20.40% |
| schedule | 86,325 | 85,953 | 16.22% |
| dynamic | 29,658 | 29,585 | 2.46% |
| workflow_dispatch | 20,076 | 19,851 | 20.86% |
| pull_request_target | 19,122 | 18,580 | 7.53% |
| release | 11,721 | 11,586 | 15.92% |
| issues | 9,089 | 8,778 | 7.79% |
| workflow_run | 6,852 | 6,644 | 16.80% |
| issue_comment | 5,301 | 4,386 | 9.48% |
| repository_dispatch | 1,278 | 1,275 | 22.90% |
| merge_group | 860 | 858 | 4.55% |
| pull_request_review | 709 | 650 | 20.92% |
| create | 640 | 598 | 26.09% |
| status | 215 | 206 | 2.43% |

## 6. `run_attempt`

| run_attempt | n |
|---|---|
| 1 | 565,256 |
| 2 | 13,496 |
| 3 | 1,224 |
| 4 | 318 |
| 5 | 157 |
| 6 | 73 |

## 7. Repositorios

- Registros: **240,781** | `selected`: 28,322 | `processed`: 28,268
- Claves: `_id` (240,781), `total_runs_90d` (240,781), `repo` (240,781), `selected` (240,781), `processed` (28,683), `etag` (28,682), `nb_runs` (28,677), `nb_workflows` (28,677), `scraping_error` (1,675), `download_complete` (62)
- `total_runs_90d`: mediana 0, máx 38667
- `nb_runs` (runs recogidos por repo): mediana 15, máx 2135

## Recordatorio
`conclusion` es el resultado de un workflow run, no de un despliegue. Este dataset no aporta por sí mismo métricas de código (churn, archivos); habría que obtenerlas de la API por `head_sha`.
