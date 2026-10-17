# Fase 3. Evaluación de los datasets

Fecha: 2026-10-15. Las estadísticas se recalcularon directamente sobre los archivos.

| Criterio | GADFPD (`final_research_dataset_MASTER.csv`) | GHALogs (`runs.json.gz`) |
|---|---|---|
| Relevancia para el despliegue | Baja. Los 384 workflows del subconjunto binario (`success`/`failure`) son CI de 32 proyectos grandes (react, numpy, elasticsearch…). Lo más parecido a un despliegue es `docs-deploy` (documentación) y publicaciones de librerías. **No hay despliegues de aplicaciones a entornos** | Media. 1.290 workflows en 686 repositorios ejecutan pasos reales de despliegue (ECS, Kubernetes, Heroku, Fly.io, Netlify, Vercel, Azure, Firebase…) |
| Resultado observable | `conclusion` del workflow. Mezcla etiquetas de Travis (`passed`, `failed`, `errored`) y de GitHub Actions | `conclusion` del workflow, más los pasos ejecutados (`log_insights`), que permiten inferir hasta dónde llegó el pipeline |
| Variables previas a la predicción | Commit: `total_churn`, `files_modified`, `additions`, `deletions`, `msg_len`, `is_merge`, `time_since_last_commit`. `duration`, `updated_at` y `status` son posteriores (fuga) | Commit (mensaje, autor, hora), evento, rama, intento e historial previo. **Sin métricas de churn**: hay que obtenerlas de la API por `head_sha` |
| Calidad | 30 % de `conclusion` nulo; hasta 37,5 % de nulos en metadatos | 0 errores de lectura; 62.703 ejecuciones sin `log_insights` |
| Duplicados | 50.529 `run_id` repetidos en el total; **0 en el subconjunto binario** (145.839 ejecuciones únicas). Hasta 2.190 filas por commit | `_id` único, pero **la misma ejecución aparece con varios nombres de repositorio** (renombrados). En el subconjunto de despliegue, 124 duplicados se resolvieron con `repository.id` |
| Intentos | `run_attempt` hasta 11 | Solo se guarda el último intento de cada ejecución (`run_attempt` de 1 a 7) |
| Cobertura temporal | Subconjunto binario: 2025-02-24 → 2026-04-18. Hay fechas de 2016 en las filas de Travis | 2023-06-30 → 2023-11-14 (4,5 meses); como máximo 5 ejecuciones por workflow |
| Información adicional de GitHub | **Sí**: la API de jobs funciona para estas ejecuciones (resultado exacto de cada paso), aunque las más antiguas pueden caducar | Las ejecuciones de 2023 **ya no existen** en la API (404). El YAML histórico se recupera con `?ref=head_sha`. Los logs completos ocupan 142 GB en Zenodo |
| Licencia | CC BY 4.0 | CC BY-SA 4.0 (los datos derivados deben compartirse con la misma licencia) |
| Datos personales | Nombres y correos de autores | Nombres y correos en `head_commit` → no se guardan; solo un hash |

## Estadísticas revisadas

- GADFPD: el binario `success`/`failure` tiene 145.839 filas con 5,95 % de fallos (confirmado). Pero esas filas pertenecen a **32 repositorios**, no a 654: los otros 622 solo aparecen en filas de Travis o con `conclusion` nulo.
- GADFPD: 17.522 `passed` y 3.702 `failed` son etiquetas de Travis CI y no se pueden mezclar sin normalizar.
- GHALogs: 15,88 % de fallos en el binario (confirmado).

## Recomendación

- **Dataset de entrenamiento: GHALogs**, filtrado a workflows con pasos de despliegue reales (ver `fase2_variable_objetivo.md`). Es el único con despliegues de aplicaciones observables.
- **GADFPD no se usa para entrenar el modelo de despliegue**, porque no contiene despliegues de aplicaciones. Sirve como referencia de variables de churn y para justificar que las métricas del commit son obtenibles en tiempo real.
- **Ninguno de los dos es suficiente para predecir el fallo real dentro del paso de despliegue ni los incidentes en producción.** Esta limitación se declara en la tesis.
