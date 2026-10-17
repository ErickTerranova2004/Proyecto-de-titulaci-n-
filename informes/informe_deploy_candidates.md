# Informe de posibles workflows de despliegue

> Las coincidencias son candidatas para revisión, no pruebas de que se haya realizado un despliegue.

- Registros JSON válidos procesados: 580,641
- Errores de parseo: 0
- Registros con coincidencias: 117,528

## Coincidencias por campo

| Campo | Registros coincidentes |
|---|---:|
| metadata.name | 96,934 |
| workflow_path | 88,438 |
| metadata.path | 88,438 |
| metadata.display_title | 65,010 |

## Resultados de las ejecuciones candidatas

| Conclusion | Cantidad |
|---|---:|
| success | 102,020 |
| failure | 14,308 |
| skipped | 737 |
| cancelled | 412 |
| startup_failure | 38 |
| action_required | 13 |

## Eventos de las ejecuciones candidatas

| Evento | Cantidad |
|---|---:|
| push | 52,571 |
| dynamic | 22,357 |
| pull_request | 13,280 |
| workflow_dispatch | 10,196 |
| release | 9,330 |
| schedule | 4,965 |
| workflow_run | 1,858 |
| pull_request_target | 1,335 |
| issue_comment | 420 |
| repository_dispatch | 364 |
| create | 321 |
| issues | 307 |
| milestone | 107 |
| pull_request_review | 38 |
| deployment | 35 |
| deployment_status | 18 |
| merge_group | 9 |
| delete | 6 |
| check_run | 5 |
| gollum | 3 |
| watch | 3 |

## Rutas y nombres más frecuentes

| Ruta | Nombre | Registros |
|---|---|---:|
| dynamic/pages/pages-build-deployment | pages build and deployment | 22,306 |
| .github/workflows/release.yml | Release | 7,038 |
| .github/workflows/release.yml | release | 2,124 |
| .github/workflows/release-drafter.yml | Release Drafter | 1,393 |
| .github/workflows/publish.yml | Publish | 1,368 |
| .github/workflows/release.yaml | Release | 997 |
| .github/workflows/deploy.yml | Deploy | 771 |
| .github/workflows/ci.yml | CI | 594 |
| .github/workflows/release.yaml | release | 494 |
| .github/workflows/python-publish.yml | Upload Python Package | 477 |
| .github/workflows/publish.yml | publish | 340 |
| .github/workflows/release-please.yml | release-please | 317 |
| .github/workflows/docker-publish.yml | Docker | 295 |
| .github/workflows/codeql-analysis.yml | CodeQL | 278 |
| .github/workflows/publish.yaml | Publish | 261 |
| .github/workflows/deploy.yml | deploy | 245 |
| .github/workflows/release.yml | .github/workflows/release.yml | 214 |
| .github/workflows/release.yml | goreleaser | 209 |
| .github/workflows/release.yml | Create Release | 203 |
| .github/workflows/goreleaser.yml | goreleaser | 194 |
| .github/workflows/test.yml | Test | 175 |
| .github/workflows/ci.yml | ci | 156 |
| .github/workflows/codeql.yml | CodeQL | 154 |
| .github/workflows/deploy-docs.yml | Deploy Docs | 153 |
| .github/workflows/build.yml | Build | 148 |
| .github/workflows/build.yml | build | 142 |
| .github/workflows/lint.yml | Lint | 126 |
| .github/workflows/release-drafter.yaml | Release Drafter | 122 |
| .github/workflows/static.yml | Deploy static content to Pages | 120 |
| .github/workflows/publish.yml | Publish to PyPI | 111 |
| .github/workflows/docker.yml | Publish Docker image | 105 |
| .github/workflows/main.yml | CI | 101 |
| .github/workflows/deploy.yaml | Deploy | 99 |
| .github/workflows/Release.yml | Release | 97 |
| .github/workflows/publish.yml | Release | 95 |
| .github/workflows/prep-release.yml | Step 1: Prep Release | 94 |
| .github/workflows/test.yml | test | 93 |
| .github/workflows/check-release.yml | Check Release | 92 |
| .github/workflows/tests.yml | Tests | 91 |
| .github/workflows/npm-publish.yml | Node.js Package | 90 |
| .github/workflows/publish.yml | Upload Python Package | 89 |
| .github/workflows/publish-snapshot.yml | Publish Snapshot | 87 |
| .github/workflows/publish-release.yml | Step 2: Publish Release | 87 |
| .github/workflows/publish.yml | Publish to NPM | 78 |
| .github/workflows/pythonpublish.yml | Upload Python Package | 76 |
| .github/workflows/publish-release.yml | Publish Release | 75 |
| .github/workflows/create-release.yml | Create Release | 74 |
| .github/workflows/docs.yml | Deploy Docs | 73 |
| .github/workflows/publish-docs.yml | Publish Docs | 73 |
| .github/workflows/winget.yml | Publish to WinGet | 72 |

## Ejemplos para revisión manual

| Repositorio | Ruta | Nombre | Título | Resultado | Evento | head_sha | Logs referenciados | Coincidencias |
|---|---|---|---|---|---|---|---|---|
| pytables/pytables | .github/workflows/wheels.yml | Wheels | Fix typo in release notes | success | push | bbe0ee53fd089d06e9979943734e37aa28a5731f | True | metadata.display_title |
| pytables/pytables | .github/workflows/ci.yml | CI | Fix typo in release notes | success | push | bbe0ee53fd089d06e9979943734e37aa28a5731f | True | metadata.display_title |
| pytables/pytables | .github/workflows/ubuntu.yml | ubuntu | Fix typo in release notes | success | push | bbe0ee53fd089d06e9979943734e37aa28a5731f | True | metadata.display_title |
| google/verible | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | 690f8e614b60725f6563ef2d8fb5a1d8bc94ff12 | True | workflow_path, metadata.name, metadata.path, metadata.display_title |
| google/verible | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | 9492fb169f17f4c47b19392192a5277f9b46ced4 | True | workflow_path, metadata.name, metadata.path, metadata.display_title |
| google/verible | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | 9e47c3642d1ffba6f2fe15f2d1cc6ec864b59164 | True | workflow_path, metadata.name, metadata.path, metadata.display_title |
| google/verible | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | b8a040cb63e72687980c1ed37bd543fcd1043fa9 | True | workflow_path, metadata.name, metadata.path, metadata.display_title |
| google/verible | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | 0c0e50d4e5cae09cfc51e7b9cd88617294f6e372 | True | workflow_path, metadata.name, metadata.path, metadata.display_title |
| j535d165/recordlinkage | .github/workflows/ci-workflow.yml | tests | Update CI pipeline for publishing package | success | push | b93d97641952f8c85106be5794ca93b1f1298fbc | True | metadata.display_title |
| j535d165/recordlinkage | .github/workflows/ci-workflow.yml | tests | Update CI pipeline for publishing package | success | push | b93d97641952f8c85106be5794ca93b1f1298fbc | True | metadata.display_title |
| j535d165/recordlinkage | .github/workflows/python-package.yml | Upload Python Package | Release v0.16 | success | release | b93d97641952f8c85106be5794ca93b1f1298fbc | True | metadata.display_title |
| j535d165/recordlinkage | .github/workflows/render-docs.yml | Build HTML with Sphinx | Update CI pipeline for publishing package | success | push | b93d97641952f8c85106be5794ca93b1f1298fbc | True | metadata.display_title |
| j535d165/recordlinkage | .github/workflows/render-docs.yml | Build HTML with Sphinx | Update CI pipeline for publishing package | success | push | b93d97641952f8c85106be5794ca93b1f1298fbc | True | metadata.display_title |
| bytecodealliance/wasmtime-go | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | 751c6ed002aa4400c8e49616d1e644d022151fe8 | True | workflow_path, metadata.name, metadata.path, metadata.display_title |
| bytecodealliance/wasmtime-go | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | 6b6e3cbc263e83c16d8c237e90a7d2ff9ece1d24 | True | workflow_path, metadata.name, metadata.path, metadata.display_title |
| ms-jpq/gay | .github/workflows/release.yml | Release | Merge branch '<3' of https://github.com/CyberTailor/gay into CyberTai… | failure | push | 975d3511c735fea046d7230ca9fb43b790d15e23 | True | workflow_path, metadata.name, metadata.path |
| ms-jpq/gay | .github/workflows/release.yml | Release | fmt | failure | push | f5dc1c0abe50740ac0e620c14c9593422925fe33 | True | workflow_path, metadata.name, metadata.path |
| ms-jpq/gay | .github/workflows/release.yml | Release | dist | failure | push | ad3d236103682d8ac622d70e6370f7bfa95176e8 | True | workflow_path, metadata.name, metadata.path |
| ms-jpq/gay | .github/workflows/release.yml | Release | Merge pull request #18 from ms-jpq/CyberTailor-<3 | success | push | ec6b620e1b2070152bdfd3d8bda4043985aed611 | True | workflow_path, metadata.name, metadata.path |
| ms-jpq/gay | .github/workflows/release.yml | Release | cfg | success | push | 0c225e215bf10491dee8b451e5dd7aef2f21f625 | True | workflow_path, metadata.name, metadata.path |
| devfile/api | .github/workflows/publish-devfile-schema.yaml | Publish Devfile Schema | Add area alizer label to all issue templates (#1149) | success | push | adde8ec27e812c21323beb6226846e4ce88dfb49 | True | workflow_path, metadata.name, metadata.path |
| devfile/api | .github/workflows/publish-devfile-schema.yaml | Publish Devfile Schema | Update deprecated github actions to latest version (#1231) | success | push | f331a0bc91308854dfbbd34d43ead489ae756e26 | True | workflow_path, metadata.name, metadata.path |
| devfile/api | .github/workflows/publish-devfile-schema.yaml | Publish Devfile Schema | Add license header file and script (#1256) | success | push | e05a23590d0f820bb7f070d7e782a5f9caf301c5 | True | workflow_path, metadata.name, metadata.path |
| devfile/api | .github/workflows/release-typescript-models.yaml | Release Typescript Models | Add area alizer label to all issue templates (#1149) | failure | push | adde8ec27e812c21323beb6226846e4ce88dfb49 | True | workflow_path, metadata.name, metadata.path |
| devfile/api | .github/workflows/release-typescript-models.yaml | Release Typescript Models | Update deprecated github actions to latest version (#1231) | failure | push | f331a0bc91308854dfbbd34d43ead489ae756e26 | True | workflow_path, metadata.name, metadata.path |
| devfile/api | .github/workflows/release-typescript-models.yaml | Release Typescript Models | Add license header file and script (#1256) | failure | push | e05a23590d0f820bb7f070d7e782a5f9caf301c5 | True | workflow_path, metadata.name, metadata.path |
| getstream/stream-video-android | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | 043c2301490fbdafb2afbbb4d6842e8135d62bbe | True | workflow_path, metadata.name, metadata.path, metadata.display_title |
| getstream/stream-video-android | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | 8847305de2d8dc9e3af9bb5ab462b15ead40ceb6 | True | workflow_path, metadata.name, metadata.path, metadata.display_title |
| getstream/stream-video-android | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | b01fedeea6c8e13ad2109dc326b1d5981979a543 | True | workflow_path, metadata.name, metadata.path, metadata.display_title |
| getstream/stream-video-android | dynamic/pages/pages-build-deployment | pages build and deployment | pages build and deployment | success | dynamic | 16cd2c33e21aa180e5f2a34457e0c3fa14f9c371 | True | workflow_path, metadata.name, metadata.path, metadata.display_title |

## Limitaciones

- Las palabras clave pueden producir falsos positivos y negativos.
- Una conclusion failure no demuestra un fallo de despliegue.
- La presencia de logs_archive no garantiza que los logs estén descargados o completos.
- Es necesario verificar el contenido y la finalidad del workflow antes de definir etiquetas para el modelo.
