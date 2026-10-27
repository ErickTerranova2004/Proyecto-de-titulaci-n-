# Resultado de la carga de casos (2026-10-27 00:35)

Casos: 30 · coinciden con lo esperado: 30 · discrepancias: 0

| # | Tipo | Repositorio | HTTP real | HTTP esperado | Mensaje | Asignación | Sincronización |
|---|---|---|---|---|---|---|---|
| 1 | VÁLIDO | Shankar-105/Social-Media-Api | 201 | 201 |  | prueba_lider: asignado, prueba_dev: asignado | 20 ejecuciones en 0.1 s |
| 2 | VÁLIDO | plausible/website | 201 | 201 |  | prueba_lider: asignado | 20 ejecuciones en 0.1 s |
| 3 | VÁLIDO | zotero-chinese/website | 201 | 201 |  | prueba_dev: asignado | 20 ejecuciones en 0.1 s |
| 4 | VÁLIDO | martignoni/moodle-tool-guide | 201 | 201 |  | — | 20 ejecuciones en 0.1 s |
| 5 | VÁLIDO | thematters/matters-web | 201 | 201 |  | prueba_lider: asignado, prueba_dev: asignado | 20 ejecuciones en 0.1 s |
| 6 | VÁLIDO | vapor/website | 201 | 201 |  | prueba_lider: asignado | 20 ejecuciones en 0.1 s |
| 7 | VÁLIDO | b-partners/bpartners-api | 201 | 201 |  | prueba_dev: asignado | 20 ejecuciones en 0.2 s |
| 8 | VÁLIDO | yormengh/yormenops | 201 | 201 |  | — | 20 ejecuciones en 0.1 s |
| 9 | VÁLIDO | slomg/anarchychess | 201 | 201 |  | prueba_lider: asignado, prueba_dev: asignado | 20 ejecuciones en 0.1 s |
| 10 | VÁLIDO | spidermila/MedCover | 201 | 201 |  | prueba_lider: asignado | 18 ejecuciones en 0.1 s |
| 11 | VÁLIDO | niobium-nz/Niobium.Notification | 201 | 201 |  | prueba_dev: asignado | 20 ejecuciones en 0.2 s |
| 12 | VÁLIDO | JasonPuglisi/descent | 201 | 201 |  | prueba_lider: asignado, prueba_dev: asignado | 20 ejecuciones en 0.1 s |
| 13 | VÁLIDO | Mattilsynet/matvaretabellen-deux | 201 | 201 |  | prueba_lider: asignado | 20 ejecuciones en 0.1 s |
| 14 | VÁLIDO | vidhanio/site | 201 | 201 |  | — | 20 ejecuciones en 0.1 s |
| 15 | VÁLIDO | DFE-Digital/teacher-services-tech-docs | 201 | 201 |  | prueba_lider: asignado, prueba_dev: asignado | 20 ejecuciones en 0.1 s |
| 16 | VÁLIDO | Elao/elao_ | 201 | 201 |  | prueba_lider: asignado | 20 ejecuciones en 0.1 s |
| 17 | VÁLIDO | lubbaragaki/homelab | 201 | 201 |  | prueba_dev: asignado | 20 ejecuciones en 0.1 s |
| 18 | VÁLIDO | PADAS/das-web-react | 201 | 201 |  | — | 19 ejecuciones en 0.1 s |
| 19 | VÁLIDO | swuecho/chat | 201 | 201 |  | prueba_lider: asignado, prueba_dev: asignado | 20 ejecuciones en 0.1 s |
| 20 | VÁLIDO | bgalek/hackmerlin.io | 201 | 201 |  | prueba_lider: asignado | 20 ejecuciones en 0.1 s |
| 21 | VÁLIDO | MorzeTeam/Morze | 201 | 201 |  | prueba_dev: asignado | 20 ejecuciones en 0.1 s |
| 22 | VÁLIDO | vivid-planet/dextinity | 201 | 201 |  | — | 20 ejecuciones en 0.1 s |
| 23 | INVÁLIDO | Verilean/xeus-lean | 201 | 201 |  | — | 20 ejecuciones en 0.1 s |
| 24 | INVÁLIDO | binary-touch/meilibridge | 201 | 201 |  | — | 20 ejecuciones en 0.1 s |
| 25 | INVÁLIDO | godotengine/issue-stats | 201 | 201 |  | — | 20 ejecuciones en 0.1 s |
| 26 | INVÁLIDO | AdamArcane/obsidian-recipebox | 201 | 201 |  | — | 20 ejecuciones en 0.1 s |
| 27 | INVÁLIDO | sgkit-dev/bio2zarr | 201 | 201 |  | — | 20 ejecuciones en 0.1 s |
| 28 | LÍMITE | fastapi/full-stack-fastapi-template | 201 | 201 |  | — | 20 ejecuciones en 0.1 s |
| 29 | LÍMITE | clearlydefined/operations | 201 | 201 |  | — | 0 ejecuciones en 0.2 s |
| 30 | LÍMITE | mastodon/mastodon | 409 | 409 | Este workflow ya está registrado y validado. | — | — |

## Hallazgos sobre la plataforma

Las respuestas coinciden con el resultado esperado porque este se fijó con el comportamiento real del código. Aun así, la carga
confirma estos problemas:

1. **Los 5 INVÁLIDOS se aceptaron (201)**: el registro no analiza el YAML. Publicar una imagen (Verilean/xeus-lean,
   binary-touch/meilibridge), GitHub Pages (godotengine/issue-stats), solo CI (AdamArcane/obsidian-recipebox) y PyPI
   (sgkit-dev/bio2zarr) quedan como "workflows de despliegue validados", aunque el formulario dice que no se aceptan.
   Además aparecen en Nuevo análisis del administrador.
2. **No se comprueba el dataset base**: un repositorio del dataset con otra ruta se aceptaría, y un workflow del dataset marcado
   como no disponible se vuelve a validar sobrescribiendo su evidencia (revisado en el código; no se probó para no alterar el
   dataset).
3. **C1 (despliegue omitido)**: se acepta y la sincronización guarda 20 ejecuciones `skipped` sin etiqueta. El repositorio queda
   disponible para analizar aunque nunca despliega en el original.
4. **C2 (reutilizable)**: se acepta con 0 ejecuciones; sus ejecuciones se atribuyen al workflow que lo llama, así que nunca
   tendrá historial propio ni podrá verificarse un resultado real.
5. **Tiempo de sincronización (0,1–0,2 s)**: no mide GitHub. El registro ya pidió las 20 ejecuciones y el backend las sirve desde
   su caché (5 minutos); una sincronización sin caché tarda lo que tarde la API de GitHub.
6. **Límite de peticiones**: la plataforma permite 120 peticiones por hora por usuario; una carga de 30 casos (~4 peticiones cada
   uno) queda en el límite. El script espera lo que indica `Retry-After` si recibe 429.
