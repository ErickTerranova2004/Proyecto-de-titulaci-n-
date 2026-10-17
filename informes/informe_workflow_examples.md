# Validación de workflows candidatos de GitHub

- Registros locales leídos: 580,641
- Errores JSON: 0
- Workflows únicos candidatos: 32,438
- Máximo seleccionado para consulta: 25
- Autenticación mediante token: no

> Las categorías son indicios automáticos. No demuestran que se haya realizado un despliegue ni que haya fallado.

## Resultados

| Repositorio | Ruta | Resultado de consulta | Indicios del contenido | Archivo guardado |
|---|---|---|---|---|
| dropbox/store | .github/workflows/.ci_test_and_publish.yml | No encontrado (404) | No se pudo clasificar |  |
| mobilenativefoundation/store | .github/workflows/.ci_test_and_publish.yml | No encontrado (404) | No se pudo clasificar |  |
| haproxytech/dataplaneapi | .github/workflows/.goreleaser.yml | OK | Indicios insuficientes; revisar manualmente | informes\workflow_definitions\haproxytech_dataplaneapi__.github__workflows__.goreleaser.yml.yml |
| haproxytech/kubernetes-ingress | .github/workflows/.goreleaser.yml | No encontrado (404) | No se pudo clasificar |  |
| webrpc/webrpc | .github/workflows/.goreleaser.yml | No encontrado (404) | No se pudo clasificar |  |
| armosec/kubescape | .github/workflows/02-release.yaml | OK | entorno o acción de despliegue; publicación de artefactos | informes\workflow_definitions\armosec_kubescape__.github__workflows__02-release.yaml.yml |
| kubescape/kubescape | .github/workflows/02-release.yaml | OK | entorno o acción de despliegue; publicación de artefactos | informes\workflow_definitions\kubescape_kubescape__.github__workflows__02-release.yaml.yml |
| armosec/kubescape | .github/workflows/03-post-release.yaml | No encontrado (404) | No se pudo clasificar |  |
| kubescape/kubescape | .github/workflows/03-post-release.yaml | No encontrado (404) | No se pudo clasificar |  |
| armosec/kubescape | .github/workflows/04-publish-krew-plugin.yaml | No encontrado (404) | No se pudo clasificar |  |
| kubescape/kubescape | .github/workflows/04-publish-krew-plugin.yaml | No encontrado (404) | No se pudo clasificar |  |
| stratospheric-dev/stratospheric | .github/workflows/04-publish-todo-app.yml | OK | entorno o acción de despliegue; publicación de artefactos | informes\workflow_definitions\stratospheric-dev_stratospheric__.github__workflows__04-publish-todo-app.yml.yml |
| shopware/platform | .github/workflows/05-release.yml | No encontrado (404) | No se pudo clasificar |  |
| shopware/shopware | .github/workflows/05-release.yml | No encontrado (404) | No se pudo clasificar |  |
| hootrhino/rulex | .github/workflows/1_auto_release.yml | OK | Indicios insuficientes; revisar manualmente | informes\workflow_definitions\hootrhino_rulex__.github__workflows__1_auto_release.yml.yml |
| cylc/cylc-flow | .github/workflows/1_create_release_pr.yml | OK | publicación de artefactos | informes\workflow_definitions\cylc_cylc-flow__.github__workflows__1_create_release_pr.yml.yml |
| uniswap/interface | .github/workflows/2-deploy-to-staging.yml | No encontrado (404) | No se pudo clasificar |  |
| uniswap/uniswap-interface | .github/workflows/2-deploy-to-staging.yml | No encontrado (404) | No se pudo clasificar |  |
| green-software-foundation/carbon-aware-sdk | .github/workflows/2-pre-release.yaml | OK | publicación de artefactos | informes\workflow_definitions\green-software-foundation_carbon-aware-sdk__.github__workflows__2-pre-release.yaml.yml |
| green-software-foundation/carbon-aware-sdk | .github/workflows/2.a-deploy.yaml | No encontrado (404) | No se pudo clasificar |  |
| playcover/playcover | .github/workflows/2.nightly_release.yml | OK | publicación de artefactos | informes\workflow_definitions\playcover_playcover__.github__workflows__2.nightly_release.yml.yml |
| aurae-runtime/aurae | .github/workflows/291-deploy-website-documentation-aurae-builder-make-docs.yml | No encontrado (404) | No se pudo clasificar |  |
| aurae-runtime/auraescript | .github/workflows/291-deploy-website-documentation-aurae-builder-make-docs.yml | No encontrado (404) | No se pudo clasificar |  |
| cylc/cylc-flow | .github/workflows/2_auto_publish_release.yml | OK | publicación de artefactos | informes\workflow_definitions\cylc_cylc-flow__.github__workflows__2_auto_publish_release.yml.yml |
| prisma/language-tools | .github/workflows/3_LS_tests_publish.yml | No encontrado (404) | No se pudo clasificar |  |

## Conteos de ejecuciones en GHALogs

Los conteos siguientes corresponden a ejecuciones históricas asociadas a cada ruta, no a nuevas consultas de GitHub.

| Repositorio | Ruta | Conclusiones | Eventos |
|---|---|---|---|
| dropbox/store | .github/workflows/.ci_test_and_publish.yml | success: 5 | push: 5 |
| mobilenativefoundation/store | .github/workflows/.ci_test_and_publish.yml | success: 5 | push: 5 |
| haproxytech/dataplaneapi | .github/workflows/.goreleaser.yml | success: 4, failure: 1 | push: 5 |
| haproxytech/kubernetes-ingress | .github/workflows/.goreleaser.yml | success: 5 | push: 5 |
| webrpc/webrpc | .github/workflows/.goreleaser.yml | failure: 5 | push: 5 |
| armosec/kubescape | .github/workflows/02-release.yaml | success: 2, startup_failure: 1, cancelled: 1, failure: 1 | push: 5 |
| kubescape/kubescape | .github/workflows/02-release.yaml | failure: 5 | push: 5 |
| armosec/kubescape | .github/workflows/03-post-release.yaml | success: 3 | release: 3 |
| kubescape/kubescape | .github/workflows/03-post-release.yaml | success: 5 | release: 5 |
| armosec/kubescape | .github/workflows/04-publish-krew-plugin.yaml | success: 3 | push: 3 |
| kubescape/kubescape | .github/workflows/04-publish-krew-plugin.yaml | success: 5 | push: 5 |
| stratospheric-dev/stratospheric | .github/workflows/04-publish-todo-app.yml | failure: 5 | push: 5 |
| shopware/platform | .github/workflows/05-release.yml | success: 5 | release: 5 |
| shopware/shopware | .github/workflows/05-release.yml | success: 5 | release: 5 |
| hootrhino/rulex | .github/workflows/1_auto_release.yml | failure: 2, success: 1 | push: 3 |
| cylc/cylc-flow | .github/workflows/1_create_release_pr.yml | success: 4 | workflow_dispatch: 4 |
| uniswap/interface | .github/workflows/2-deploy-to-staging.yml | success: 5 | push: 5 |
| uniswap/uniswap-interface | .github/workflows/2-deploy-to-staging.yml | success: 5 | push: 5 |
| green-software-foundation/carbon-aware-sdk | .github/workflows/2-pre-release.yaml | success: 5 | push: 5 |
| green-software-foundation/carbon-aware-sdk | .github/workflows/2.a-deploy.yaml | failure: 5 | pull_request: 3, push: 2 |
| playcover/playcover | .github/workflows/2.nightly_release.yml | success: 5 | schedule: 5 |
| aurae-runtime/aurae | .github/workflows/291-deploy-website-documentation-aurae-builder-make-docs.yml | success: 2 | push: 2 |
| aurae-runtime/auraescript | .github/workflows/291-deploy-website-documentation-aurae-builder-make-docs.yml | success: 1 | push: 1 |
| cylc/cylc-flow | .github/workflows/2_auto_publish_release.yml | success: 3, skipped: 2 | pull_request: 5 |
| prisma/language-tools | .github/workflows/3_LS_tests_publish.yml | success: 5 | workflow_dispatch: 5 |

## Limitaciones

- Solo se consultó una muestra de workflows únicos.
- El contenido actual del repositorio puede diferir de la versión existente cuando ocurrió una ejecución histórica.
- Los patrones automáticos pueden producir falsos positivos y falsos negativos.
- Un archivo no encontrado no demuestra que el workflow no existiera en la fecha de la ejecución.
- No se asignan etiquetas de fallo real de despliegue.
