# Clasificación preliminar de workflows

- Archivos YAML encontrados: 9

> Clasificación automática basada en palabras clave. No confirma despliegues ni fallos reales.

| Archivo | Categorías detectadas | Evidencias encontradas |
|---|---|---|
| armosec_kubescape__.github__workflows__02-release.yaml.yml | Publicación de artefactos; Pruebas o compilación | L148: args: release --clean ${{ inputs.skip_publish == true && '--skip=publish' \|\| '' }}<br>L170: - name: Attest build provenance<br>L172: uses: actions/attest-build-provenance@4d101475d8b20a2381f78447822ac1eab6504dd8 # v4.2.2 |
| cylc_cylc-flow__.github__workflows__1_create_release_pr.yml.yml | Publicación de artefactos; Pruebas o compilación | L57: pypi-package-name: 'cylc-flow'<br>L59: - name: Test build<br>L60: uses: cylc/release-actions/build-python-package@v1<br>L65: towncrier build --yes<br>L70: test-workflows: test_fast.yml, test_functional.yml, bash.yml, test_conda-build.yml |
| cylc_cylc-flow__.github__workflows__2_auto_publish_release.yml.yml | Publicación de artefactos; Pruebas o compilación | L1: name: Release stage 2 - auto publish<br>L27: publish:<br>L48: - name: Build<br>L49: uses: cylc/release-actions/build-python-package@v1<br>L51: - name: Publish distribution to PyPI<br>L52: uses: pypa/gh-action-pypi-publish@release/v1<br>L54: user: __token__ # uses the API token feature of PyPI - least permissions possible<br>L57: # repository_url: https://test.pypi.org/legacy/ |
| green-software-foundation_carbon-aware-sdk__.github__workflows__2-pre-release.yaml.yml | Publicación de artefactos; Pruebas o compilación | L1: name: 2-Publish container image to GitHub Packages<br>L16: group: publish<br>L20: publish-container-image:<br>L42: - name: Build and push Docker image<br>L43: uses: docker/build-push-action@v4.0.0 |
| haproxytech_dataplaneapi__.github__workflows__.goreleaser.yml.yml | Revisión manual necesaria | Sin coincidencias |
| hootrhino_rulex__.github__workflows__1_auto_release.yml.yml | Pruebas o compilación | L8: build: |
| kubescape_kubescape__.github__workflows__02-release.yaml.yml | Publicación de artefactos; Pruebas o compilación | L148: args: release --clean ${{ inputs.skip_publish == true && '--skip=publish' \|\| '' }}<br>L170: - name: Attest build provenance<br>L172: uses: actions/attest-build-provenance@4d101475d8b20a2381f78447822ac1eab6504dd8 # v4.2.2 |
| playcover_playcover__.github__workflows__2.nightly_release.yml.yml | Publicación de artefactos; Pruebas o compilación | L1: name: Build nightly release<br>L9: build:<br>L26: - name: Set build number<br>L62: uses: actions/upload-artifact@v7 |
| stratospheric-dev_stratospheric__.github__workflows__04-publish-todo-app.yml.yml | Posible despliegue; Publicación de artefactos; Pruebas o compilación | L2: name: 04 - Publish Todo-App<br>L16: - '.github/workflows/04-publish-todo-app.yml'<br>L19: build-and-publish:<br>L21: name: Build and publish Todo App<br>L36: - name: Build application<br>L38: run: ./gradlew build --stacktrace<br>L40: - name: Zip build reports<br>L42: run: zip -r reports.zip **/build/reports |

## Resumen de categorías

| Categoría | Archivos que coinciden |
|---|---:|
| Pruebas o compilación | 8 |
| Publicación de artefactos | 7 |
| Revisión manual necesaria | 1 |
| Posible despliegue | 1 |

## Limitaciones

- Un archivo puede coincidir con varias categorías.
- Las palabras clave pueden producir falsos positivos.
- La configuración actual puede diferir de la histórica.
- Un workflow fallido no equivale necesariamente a un despliegue fallido.
- Las categorías no deben utilizarse directamente como etiquetas de entrenamiento.
