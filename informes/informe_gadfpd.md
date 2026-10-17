# Informe GADFPD: `.\Datos\final_research_dataset_MASTER.csv`

Filas: **303,079** | Columnas: **38** (el artículo declara 303.079 filas)

## 1. Columnas esperadas vs. reales

- Presentes: `run_id`, `workflow_id`, `status`, `conclusion`, `duration`, `event`, `run_attempt`, `created_at`, `updated_at`, `commit_sha`, `total_churn`, `files_modified`, `msg_len`, `is_merge`, `time_since_last_commit`
- **Ausentes**: ninguna
- **No documentadas en el artículo**: `repo`, `repo_name`, `run_started_at`, `head_branch`, `run_number`, `author_name`, `author_email`, `committer_name`, `committer_email`, `authored_date`, `committed_date`, `message`, `num_parents`, `additions`, `deletions`, `timestamp_raw`, `commit_date`, `author`, `node_id`, `head_sha`, `actor_login`, `triggering_actor_login`, `timestamp`
- Columna de repositorio detectada: ['repo', 'repo_name']
- Columna de plataforma/origen detectada: **NINGUNA** (separar Travis/Actions solo sería posible por fecha)

## 2. Diccionario de datos (ejemplos reales del CSV)

               Columna    Tipo  Nulos  % nulos  Únicos                             Ejemplo real ¿Posterior a la ejecución?
                run_id   int64      0     0.00  252550                              24607299342                    revisar
                  repo     str      0     0.00     654                      home-assistant/core                    revisar
             repo_name     str 280493    92.55     621                  google/closure-compiler                    revisar
            commit_sha     str      0     0.00   54841 476a04dcb2bb56f0f8c81b1cd5a8ce08b5d0bf99                    revisar
            conclusion     str  91047    30.04      10                                  success                  SÍ (fuga)
                status     str  22613     7.46       9                                completed                  SÍ (fuga)
              duration float64      5     0.00   15425                                     39.0                  SÍ (fuga)
            created_at     str  91030    30.04  146294                2026-04-18 14:58:34+00:00                    revisar
        run_started_at     str  91030    30.04  147201                2026-04-18 14:58:34+00:00                    revisar
            updated_at     str 113616    37.49  175156                2026-04-18 14:59:13+00:00                  SÍ (fuga)
                 event     str 113616    37.49      18                                     push                    revisar
           head_branch     str  91031    30.04   14196                                      dev                    revisar
            run_number float64  91030    30.04   90194                                   7006.0                    revisar
           author_name     str 113616    37.49    3190                           Denis Shulyaka                    revisar
          author_email     str 113616    37.49    3233                       Shulyaka@gmail.com                    revisar
        committer_name     str 113616    37.49    1265                                   GitHub                    revisar
       committer_email     str 113616    37.49    1278                       noreply@github.com                    revisar
         authored_date     str 113616    37.49   28853                2026-04-18 14:58:31+00:00                    revisar
        committed_date     str 113616    37.49   28869                2026-04-18 14:58:31+00:00                    revisar
               message     str 113616    37.49   28498    Add Claude Opus 4.7 support (#168496)                    revisar
               msg_len   int64      0     0.00    2649                                       37                    revisar
              is_merge  object 113616    37.49       2                                    False                    revisar
           num_parents float64 113616    37.49       2                                      1.0                    revisar
             additions   int64      0     0.00    2097                                       73                    revisar
             deletions   int64      0     0.00    1545                                       14                    revisar
           total_churn float64 113616    37.49    2355                                     87.0                    revisar
        files_modified   int64      0     0.00     390                                        9                    revisar
         timestamp_raw     str      0     0.00  109835                2026-04-18 14:58:31+00:00                    revisar
           commit_date     str 212049    69.96   14991                2026-03-08 19:19:35+00:00                    revisar
                author     str 189463    62.51    2118                  malfait.robin@gmail.com                    revisar
           workflow_id float64 113616    37.49     396                               47565721.0                    revisar
               node_id     str 113616    37.49  189463               WFR_kwLOAMSroc8AAAAFurWXDg                    revisar
              head_sha     str 113616    37.49   28942 476a04dcb2bb56f0f8c81b1cd5a8ce08b5d0bf99                    revisar
           run_attempt float64 113616    37.49      11                                      1.0                    revisar
           actor_login     str 113616    37.49    6359                                   zweckj                    revisar
triggering_actor_login     str 113616    37.49    6125                                   zweckj                    revisar
time_since_last_commit float64 113616    37.49   11103                                   7880.0                    revisar
             timestamp     str 212049    69.96   59000                2026-03-08 19:19:38+00:00                    revisar

## 3. Duplicados

- Filas completas duplicadas: **0**
- `run_id` repetido: **50,529** (sobre 303,079)
- Commits distintos: 54,841; commits con >1 fila: 28,794; máx. filas por commit: 2190 (mismas métricas de código repetidas)

## 4. Cobertura temporal y separación Travis / GitHub Actions (HIPÓTESIS)

- `created_at` parseable: 69.96% | rango: 2016-08-08 17:58:18+00:00 → 2026-04-18 17:48:19+00:00

                    Periodo  filas
   ≥ 2024-05 (GHA probable) 189463
< 2024-05 (Travis probable)  22586

Si hay filas entre ene-2017 y abr-2024, o fechas inválidas, la separación por fecha NO es limpia.

## 5. Etiqueta `conclusion`

     conclusion      n     %
        success 137168 45.26
            NaN  91047 30.04
        skipped  38041 12.55
         passed  17522  5.78
        failure   8671  2.86
      cancelled   5260  1.74
         failed   3702  1.22
        errored   1253  0.41
startup_failure    271  0.09
       canceled    109  0.04
action_required     35  0.01

Fallo entre success+failure: **5.95%** (145,839 filas utilizables binarias)

     periodo  filas  tasa_fallo
GHA probable 145839      0.0595

**Cruce `status` × `conclusion`** (en GitHub, `status` no debería contener 'failure'):

   status  action_required  cancelled  failure  skipped  startup_failure  success
completed               35       5260     8671    38041              271   137168

**Tasa de fallo por `event` (success+failure)**:

                 event  filas  tasa_fallo
                  push  41700      0.0907
          pull_request  29425      0.0802
              schedule  22073      0.0356
                status  13038      0.0023
               dynamic  12959      0.0588
         issue_comment   8720      0.0003
          workflow_run   8059      0.0341
                issues   6654      0.0249
     workflow_dispatch   1779      0.2400
   pull_request_target    884      0.0769
   repository_dispatch    228      0.0132
               release    180      0.0556
           merge_group    126      0.0000
                create      7      0.0000
branch_protection_rule      5      0.0000

## 6. Registros inválidos o inconsistentes

- `updated_at` < `created_at`: 0
- `duration` negativa: 0; > 1 día: 2,599; > 1 año: 1,760
- `total_churn`: negativos 0; no numéricos 0
- `files_modified`: negativos 0; no numéricos 0
- `msg_len`: negativos 0; no numéricos 0
- `time_since_last_commit`: negativos 0; no numéricos 0

## 7. Resumen numérico

               columna    count         mean          std         min          25%          50%          75%          max
                run_id 303079.0 1.998528e+10 6.183131e+09 150710124.0 1.924637e+10 2.223679e+10 2.344047e+10 2.461037e+10
              duration 303074.0 2.031472e+05 2.630732e+06         0.0 9.000000e+00 6.000000e+01 4.630000e+02 3.652238e+07
            run_number 212049.0 9.305536e+04 1.711651e+05         1.0 4.320000e+03 1.471500e+04 7.131400e+04 6.282970e+05
               msg_len 303079.0 3.681840e+02 1.323320e+03         0.0 5.700000e+01 1.130000e+02 2.900000e+02 1.221040e+05
           num_parents 189463.0 1.164000e+00 3.710000e-01         1.0 1.000000e+00 1.000000e+00 1.000000e+00 2.000000e+00
             additions 303079.0 6.249750e+02 1.208062e+04         0.0 2.000000e+00 1.500000e+01 9.000000e+01 1.386702e+06
             deletions 303079.0 4.265420e+02 6.905489e+03         0.0 1.000000e+00 4.000000e+00 2.800000e+01 3.466390e+05
           total_churn 189463.0 1.107237e+03 1.779462e+04         0.0 6.000000e+00 3.200000e+01 1.620000e+02 1.394827e+06
        files_modified 303079.0 1.122000e+01 8.171200e+01         0.0 1.000000e+00 2.000000e+00 5.000000e+00 1.101700e+04
           workflow_id 189463.0 6.991057e+07 7.428068e+07      2970.0 1.374564e+07 4.300180e+07 1.039564e+08 2.608992e+08
           run_attempt 189463.0 1.019000e+00 1.590000e-01         1.0 1.000000e+00 1.000000e+00 1.000000e+00 1.200000e+01
time_since_last_commit 189463.0 3.795138e+04 2.456461e+05         0.0 4.460000e+02 2.254000e+03 1.327200e+04 1.213698e+07

## 8. Correlación entre numéricas (posible redundancia)

                 index  total_churn  files_modified  msg_len  time_since_last_commit  duration
           total_churn        1.000           0.786    0.144                   0.065     0.006
        files_modified        0.786           1.000    0.113                   0.085    -0.003
               msg_len        0.144           0.113    1.000                   0.047    -0.164
time_since_last_commit        0.065           0.085    0.047                   1.000    -0.093
              duration        0.006          -0.003   -0.164                  -0.093     1.000

## 9. Recordatorio de interpretación

`conclusion` describe el resultado de un workflow run. NO es evidencia de fallo de un despliegue en producción.
