# Ejecuciones con pasos de despliegue reales (GHALogs)

> Clasificación basada en los pasos ejecutados registrados en log_insights, no en el nombre del workflow. Los patrones pueden omitir mecanismos de despliegue propios (scripts internos). 'Fallo probable en el paso de despliegue' es una heurística: el paso de despliegue fue el último registrado en su job.

- Registros leídos: 580,641
- Registros sin log_insights (no clasificables): 62,703
- Ejecuciones con publicación en GitHub Pages (excluidas): 28,440
- Workflows con al menos un paso de despliegue ejecutado: 1,290
- Repositorios: 686
- Ejecuciones de esos workflows: 6,183

## Ejecuciones por categoría de evidencia

| Categoría | Ejecuciones |
|---|---:|
| despliegue ejecutado; workflow exitoso | 4,299 |
| despliegue ejecutado; fallo en otro paso (antes o después) | 585 |
| fallo antes de llegar al despliegue | 467 |
| workflow exitoso sin paso de despliegue ejecutado | 451 |
| fallo probable en el paso de despliegue | 332 |
| otro resultado (cancelled) | 36 |
| otro resultado (skipped) | 10 |
| otro resultado (action_required) | 3 |

## Mecanismos de despliegue detectados

| Mecanismo | Ejecuciones |
|---|---:|
| shell: kubectl apply | 1,546 |
| shell: helm install | 612 |
| nwtgck/actions-netlify | 365 |
| appleboy/ssh-action | 341 |
| firebaseextended/action-hosting-deploy | 330 |
| cloudflare/wrangler-action | 263 |
| superfly/flyctl-actions | 238 |
| shell: vercel deploy | 235 |
| shell: helm upgrade | 221 |
| aws-actions/amazon-ecs-deploy-task-definition | 187 |
| shell: terraform apply | 173 |
| shell: flyctl deploy | 149 |
| shell: netlify deploy | 135 |
| shell: kubectl set image | 132 |
| amondnet/vercel-action | 120 |
| azure/webapps-deploy | 114 |
| easingthemes/ssh-deploy | 110 |
| akhileshns/heroku-deploy | 83 |
| shell: aws ecs update-service | 53 |
| shell: kubectl rollout restart | 46 |
| azure/functions-action | 39 |
| shell: gcloud run deploy | 31 |
| google-github-actions/deploy-appengine | 21 |
| google-github-actions/deploy-cloudrun | 20 |
| shell: serverless deploy | 19 |
| shell: vercel --prod | 19 |
| shell: Firebase deploy | 17 |
| azure/container-apps-deploy-action | 16 |
| einaregilsson/beanstalk-deploy | 16 |
| shell: Helm install | 16 |

## Workflows con fallos probables en el paso de despliegue

| Repositorio | Ruta | Categorías |
|---|---|---|
| rome/tools | .github/workflows/main.yml | fallo probable en el paso de despliegue: 5 |
| swishjam/swishjam | .github/workflows/heroku_deploy.yml | fallo probable en el paso de despliegue: 5 |
| crowddotdev/crowd.dev | .github/workflows/lf-staging-deploy-frontend.yaml | fallo probable en el paso de despliegue: 5 |
| supabase/realtime | .github/workflows/staging_supabench.yml | fallo probable en el paso de despliegue: 5 |
| supabase/realtime | .github/workflows/staging.yml | fallo probable en el paso de despliegue: 5 |
| alii/searchy | .github/workflows/cloudflare.yml | fallo probable en el paso de despliegue: 5 |
| leifermendez/bot-whatsapp | .github/workflows/netlify.yml | fallo probable en el paso de despliegue: 5 |
| novuhq/novu | .github/workflows/prod-deploy-api.yml | fallo probable en el paso de despliegue: 5 |
| biomejs/biome | .github/workflows/website_deploy.yml | fallo probable en el paso de despliegue: 5 |
| mu-editor/mu | .github/workflows/test.yml | fallo probable en el paso de despliegue: 5 |
| iqss/dataverse | .github/workflows/deploy_beta_testing.yml | fallo probable en el paso de despliegue: 5 |
| tensorflow/tfjs | .github/workflows/deploy-benchmark-preview.yml | fallo probable en el paso de despliegue: 5 |
| withastro/astro | .github/workflows/test-hosts.yml | fallo probable en el paso de despliegue: 5 |
| oshi/oshi | .github/workflows/solaris.yaml | fallo probable en el paso de despliegue: 5 |
| aws/aws-xray-sdk-go | .github/workflows/IntegrationTesting.yml | fallo probable en el paso de despliegue: 5 |
| gdg-x/hoverboard | .github/workflows/deploy-preview.yaml | fallo probable en el paso de despliegue: 5 |
| open-wc/open-wc | .github/workflows/preview.yml | fallo probable en el paso de despliegue: 5 |
| dekorateio/dekorate | .github/workflows/integration-tests.yml | fallo probable en el paso de despliegue: 5 |
| imjasonh/kontain.me | .github/workflows/deploy.yaml | fallo probable en el paso de despliegue: 5 |
| keikoproj/instance-manager | .github/workflows/functional-test.yaml | fallo probable en el paso de despliegue: 5 |
| arco-design/arco-design-vue | .github/workflows/deploy-site-preview.yml | fallo probable en el paso de despliegue: 5 |
| eporsche/daybreak | .github/workflows/heroku.yml | fallo probable en el paso de despliegue: 5 |
| google/devlibrary | .github/workflows/firebase-hosting-merge.yml | fallo probable en el paso de despliegue: 5 |
| telepresenceio/telepresence | .github/workflows/compatibility.yaml | fallo probable en el paso de despliegue: 5 |
| meshery/meshery | .github/workflows/cncf-playground-reset.yaml | fallo probable en el paso de despliegue: 5 |
| quay/quay | .github/workflows/CI-nightly.yaml | fallo probable en el paso de despliegue: 5 |
| azure/iotedge-lorawan-starterkit | .github/workflows/e2e-ci.yaml | fallo probable en el paso de despliegue: 4, fallo antes de llegar al despliegue: 1 |
| chainsafe/gossamer | .github/workflows/staging.yml | fallo probable en el paso de despliegue: 4, despliegue ejecutado; workflow exitoso: 1 |
| wolfi-dev/os | .github/workflows/dag-push-production.yaml | fallo probable en el paso de despliegue: 4, despliegue ejecutado; workflow exitoso: 1 |
| dynatrace-oss/barista | .github/workflows/barista-preview.yml | fallo probable en el paso de despliegue: 4, despliegue ejecutado; fallo en otro paso (antes o después): 1 |
| refinedev/refine | .github/workflows/next-push.yml | fallo probable en el paso de despliegue: 4, fallo antes de llegar al despliegue: 1 |
| rustwasm/gloo | .github/workflows/publish-website.yml | fallo probable en el paso de despliegue: 4, fallo antes de llegar al despliegue: 1 |
| balena-io/etcher | .github/workflows/flowzone.yml | fallo probable en el paso de despliegue: 4, workflow exitoso sin paso de despliegue ejecutado: 1 |
| enix/kube-image-keeper | .github/workflows/tests.yaml | fallo probable en el paso de despliegue: 4, despliegue ejecutado; fallo en otro paso (antes o después): 1 |
| temporalio/sdk-typescript | .github/workflows/ci.yml | fallo probable en el paso de despliegue: 4, despliegue ejecutado; workflow exitoso: 1 |
| webdevcody/code-racer | .github/workflows/deploy-wss.yml | fallo probable en el paso de despliegue: 3, despliegue ejecutado; workflow exitoso: 2 |
| signalk/signalk-server | .github/workflows/release.yml | fallo probable en el paso de despliegue: 3, fallo antes de llegar al despliegue: 2 |
| turingai-team/chatgpt-discord-bot | .github/workflows/auto-deploy.yml | fallo probable en el paso de despliegue: 3, fallo antes de llegar al despliegue: 2 |
| tensorflow/tfjs | .github/workflows/deploy-benchmark-prod.yml | fallo probable en el paso de despliegue: 3 |
| kiwicom/orbit | .github/workflows/cron-tracking.yml | fallo probable en el paso de despliegue: 3, fallo antes de llegar al despliegue: 1 |
