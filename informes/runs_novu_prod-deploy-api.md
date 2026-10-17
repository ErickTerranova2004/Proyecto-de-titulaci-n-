# Ejecuciones históricas: novuhq/novu / .github/workflows/prod-deploy-api.yml

- Ejecuciones encontradas en GHALogs: 5

> Los jobs y pasos provienen de log_insights (ejecución real de 2023). Un job ausente normalmente no se ejecutó o no generó log. El campo 'errors' de un paso son errores de análisis del script, no el resultado del paso.

## Ejecución #182 (intento 2)

- id: 6458599105
- created_at: 2023-10-09T15:18:52Z
- event: workflow_dispatch | rama: v0.20.x
- conclusion: **failure**
- head_sha: 7062b3730dd90054f2e900cd3a913f6c0412953a
- mensaje del commit: fix: feature flag service
- html_url: https://github.com/novuhq/novu/actions/runs/6458599105

### Job (archivo de log): 1_deploy_prod_api_eu  deploy_service.txt - 9 pasos, 299 s
- shell: echo "Deploying api to novu-prod-eu And Docker Tag ghcr.io/novuhq/novu/api-ee:7062b3730dd90054f2e900cd3a913f6c (0.1 s)
- acción actions/checkout@master (2.0 s)
- acción hashicorp/setup-terraform@v1 (1.5 s)
- shell: terraform init (15.4 s)
- shell: echo "ecs_container_name=$(terraform output -json api_ecs_container_name | jq -r .)" >> $GITHUB_ENV (16.7 s)
- acción aws-actions/configure-aws-credentials@v1 (1.3 s)
- shell: aws ecs describe-task-definition --task-definition prod-eu-api-task \ (2.2 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (259.9 s)

### Job (archivo de log): 1_Test E2E EE.txt - 14 pasos, 95 s
- shell: echo (0.1 s)
- acción actions/checkout@v3 (5.9 s)
- shell: (sin código) (6.4 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.7 s)
- acción actions/setup-node@v3 (19.1 s)
- acción supercharge/redis-github-action@1.5.0 (8.6 s)
- acción supercharge/mongodb-github-action@v1.9.0 (9.0 s)
- acción actions/cache@v3 (5.4 s)
- shell: pnpm install --frozen-lockfile (30.5 s)
- shell: pnpm i -g wait-on (2.8 s)
- shell: (sin código) (0.9 s)
- acción vishnudxb/redis-cluster@1.0.5 (4.2 s)
- acción mansagroup/nrwl-nx-action@v3 (0.5 s)

### Job (archivo de log): 1_New Relic Deploy.txt - 2 pasos, 2 s
- shell: echo "RELEASE_VERSION=v0.20.x" >> $GITHUB_ENV (0.1 s)
- acción newrelic/deployment-marker-action@v2.3.0 (2.0 s)

### Job (archivo de log): 1_test_api (novuapi)  e2e_api.txt - 24 pasos, 635 s
- shell: if ! [[ -z "***" ]]; then (0.1 s)
- acción actions/checkout@v3 (5.0 s)
- shell: (sin código) (7.6 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.8 s)
- acción actions/setup-node@v3 (22.6 s)
- acción supercharge/redis-github-action@1.5.0 (8.9 s)
- acción supercharge/mongodb-github-action@v1.9.0 (10.9 s)
- acción actions/cache@v3 (10.9 s)
- shell: pnpm install --frozen-lockfile (40.5 s)
- shell: pnpm i -g wait-on (2.7 s)
- shell: (sin código) (1.6 s)
- acción vishnudxb/redis-cluster@1.0.5 (5.2 s)
- acción mansagroup/nrwl-nx-action@v3 (28.6 s)
- shell: (sin código) (0.0 s)
- shell: docker-compose -f docker-compose.localstack.yml up -d (55.8 s)
- shell: (sin código) (0.0 s)
- shell: CI='' pnpm build:worker (9.9 s)
- shell: cd apps/worker && pnpm start:test & (5.0 s)
- shell: wait-on --timeout=180000 http://localhost:1342/v1/health-check (21.6 s)
- shell: CI='' pnpm build:api (6.1 s)
- shell: cd apps/api && pnpm test:e2e (318.0 s)
- shell: sudo kill -9 $(sudo lsof -t -i:1342) (0.2 s)
- shell: cd apps/api && pnpm test (71.8 s)

### Job (archivo de log): 6_deploy_prod_api_us.txt - 1 pasos, 261 s
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (260.9 s)

### Job (archivo de log): 1_deploy_docs.txt - 1 pasos, 1 s
- acción fjogeleit/http-request-action@v1 (0.9 s)

### Job (archivo de log): 1_deploy_prod_api_us  deploy_service.txt - 12 pasos, 277 s
- shell: echo "Deploying api to novu-prod And Docker Tag ghcr.io/novuhq/novu/api-ee:7062b3730dd90054f2e900cd3a913f6c041 (0.1 s)
- acción actions/checkout@master (1.7 s)
- acción hashicorp/setup-terraform@v1 (1.5 s)
- shell: terraform init (15.1 s)
- shell: echo "ecs_container_name=$(terraform output -json api_ecs_container_name | jq -r .)" >> $GITHUB_ENV (16.0 s)
- acción aws-actions/configure-aws-credentials@v1 (0.9 s)
- shell: aws ecs describe-task-definition --task-definition prod-api-task \ (1.8 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (234.8 s)
- acción actions/checkout@v3 (1.6 s)
- acción martinbeentjes/npm-get-version-action@main (0.8 s)
- acción getsentry/action-release@v1 (3.0 s)

### Job (archivo de log): 1_build_prod_image (novuapi-ee).txt - 14 pasos, 397 s
- acción actions/checkout@v3 (5.2 s)
- shell: (sin código) (6.5 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.6 s)
- acción actions/setup-node@v3 (19.6 s)
- acción supercharge/redis-github-action@1.5.0 (8.5 s)
- acción supercharge/mongodb-github-action@v1.9.0 (8.9 s)
- acción actions/cache@v3 (5.7 s)
- shell: pnpm install --frozen-lockfile (31.4 s)
- shell: pnpm i -g wait-on (1.6 s)
- shell: pnpm build:api (29.1 s)
- acción depot/setup-action@v1 (2.1 s)
- shell: echo "BULL_MQ_PRO_NPM_TOKEN=***" >> $GITHUB_ENV (0.0 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (276.7 s)

### Job (archivo de log): 2_build_prod_image (novuapi).txt - 13 pasos, 306 s
- acción actions/checkout@v3 (3.7 s)
- shell: (sin código) (6.0 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.7 s)
- acción actions/setup-node@v3 (13.8 s)
- acción supercharge/redis-github-action@1.5.0 (8.0 s)
- acción supercharge/mongodb-github-action@v1.9.0 (7.9 s)
- acción actions/cache@v3 (2.8 s)
- shell: pnpm install --frozen-lockfile (32.3 s)
- shell: pnpm i -g wait-on (1.7 s)
- shell: pnpm build:api (26.6 s)
- acción depot/setup-action@v1 (1.2 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (200.8 s)

## Ejecución #183 (intento 1)

- id: 6533311970
- created_at: 2023-10-16T12:07:14Z
- event: workflow_dispatch | rama: v0.20.x
- conclusion: **failure**
- head_sha: 066e218bd0cf56bfed476db177011977051dd2b7
- mensaje del commit: chore: pnpm lock file update
- html_url: https://github.com/novuhq/novu/actions/runs/6533311970

### Job (archivo de log): 1_deploy_prod_api_eu  deploy_service.txt - 9 pasos, 231 s
- shell: echo "Deploying api to novu-prod-eu And Docker Tag ghcr.io/novuhq/novu/api-ee:066e218bd0cf56bfed476db177011977 (0.1 s)
- acción actions/checkout@master (1.0 s)
- acción hashicorp/setup-terraform@v1 (1.2 s)
- shell: terraform init (10.1 s)
- shell: echo "ecs_container_name=$(terraform output -json api_ecs_container_name | jq -r .)" >> $GITHUB_ENV (10.5 s)
- acción aws-actions/configure-aws-credentials@v1 (0.8 s)
- shell: aws ecs describe-task-definition --task-definition prod-eu-api-task \ (1.4 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (205.4 s)

### Job (archivo de log): 1_Test E2E EE.txt - 14 pasos, 90 s
- shell: echo (0.1 s)
- acción actions/checkout@v3 (3.6 s)
- shell: (sin código) (6.1 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.8 s)
- acción actions/setup-node@v3 (15.9 s)
- acción supercharge/redis-github-action@1.5.0 (7.2 s)
- acción supercharge/mongodb-github-action@v1.9.0 (8.9 s)
- acción actions/cache@v3 (4.2 s)
- shell: pnpm install --frozen-lockfile (34.9 s)
- shell: pnpm i -g wait-on (2.3 s)
- shell: (sin código) (0.8 s)
- acción vishnudxb/redis-cluster@1.0.5 (3.9 s)
- acción mansagroup/nrwl-nx-action@v3 (0.6 s)

### Job (archivo de log): 1_New Relic Deploy.txt - 2 pasos, 2 s
- shell: echo "RELEASE_VERSION=v0.20.x" >> $GITHUB_ENV (0.1 s)
- acción newrelic/deployment-marker-action@v2.3.0 (2.1 s)

### Job (archivo de log): 1_test_api (novuapi)  e2e_api.txt - 24 pasos, 584 s
- shell: if ! [[ -z "***" ]]; then (0.1 s)
- acción actions/checkout@v3 (4.9 s)
- shell: (sin código) (6.5 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.9 s)
- acción actions/setup-node@v3 (21.4 s)
- acción supercharge/redis-github-action@1.5.0 (9.4 s)
- acción supercharge/mongodb-github-action@v1.9.0 (9.7 s)
- acción actions/cache@v3 (6.4 s)
- shell: pnpm install --frozen-lockfile (35.2 s)
- shell: pnpm i -g wait-on (2.7 s)
- shell: (sin código) (1.3 s)
- acción vishnudxb/redis-cluster@1.0.5 (4.6 s)
- acción mansagroup/nrwl-nx-action@v3 (25.8 s)
- shell: (sin código) (0.0 s)
- shell: docker-compose -f docker-compose.localstack.yml up -d (49.1 s)
- shell: (sin código) (0.0 s)
- shell: CI='' pnpm build:worker (8.9 s)
- shell: cd apps/worker && pnpm start:test & (5.0 s)
- shell: wait-on --timeout=180000 http://localhost:1342/v1/health-check (18.9 s)
- shell: CI='' pnpm build:api (5.1 s)
- shell: cd apps/api && pnpm test:e2e (305.8 s)
- shell: sudo kill -9 $(sudo lsof -t -i:1342) (0.2 s)
- shell: cd apps/api && pnpm test (61.3 s)

### Job (archivo de log): 1_deploy_docs.txt - 1 pasos, 1 s
- acción fjogeleit/http-request-action@v1 (0.6 s)

### Job (archivo de log): 1_deploy_prod_api_us  deploy_service.txt - 12 pasos, 284 s
- shell: echo "Deploying api to novu-prod And Docker Tag ghcr.io/novuhq/novu/api-ee:066e218bd0cf56bfed476db177011977051 (0.1 s)
- acción actions/checkout@master (1.3 s)
- acción hashicorp/setup-terraform@v1 (1.4 s)
- shell: terraform init (13.9 s)
- shell: echo "ecs_container_name=$(terraform output -json api_ecs_container_name | jq -r .)" >> $GITHUB_ENV (14.7 s)
- acción aws-actions/configure-aws-credentials@v1 (0.6 s)
- shell: aws ecs describe-task-definition --task-definition prod-api-task \ (1.3 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (245.9 s)
- acción actions/checkout@v3 (1.5 s)
- acción martinbeentjes/npm-get-version-action@main (0.6 s)
- acción getsentry/action-release@v1 (2.8 s)

### Job (archivo de log): 1_test_api (novuapi-ee)  e2e_api.txt - 24 pasos, 602 s
- shell: if ! [[ -z "***" ]]; then (0.1 s)
- acción actions/checkout@v3 (5.0 s)
- shell: (sin código) (7.3 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.8 s)
- acción actions/setup-node@v3 (19.2 s)
- acción supercharge/redis-github-action@1.5.0 (9.0 s)
- acción supercharge/mongodb-github-action@v1.9.0 (10.1 s)
- acción actions/cache@v3 (6.2 s)
- shell: pnpm install --frozen-lockfile (36.3 s)
- shell: pnpm i -g wait-on (2.6 s)
- shell: (sin código) (1.8 s)
- acción vishnudxb/redis-cluster@1.0.5 (4.7 s)
- acción mansagroup/nrwl-nx-action@v3 (27.7 s)
- shell: (sin código) (0.0 s)
- shell: docker-compose -f docker-compose.localstack.yml up -d (50.1 s)
- shell: (sin código) (0.0 s)
- shell: CI='' pnpm build:worker (8.1 s)
- shell: cd apps/worker && pnpm start:test & (5.0 s)
- shell: wait-on --timeout=180000 http://localhost:1342/v1/health-check (20.3 s)
- shell: CI='' pnpm build:api (5.6 s)
- shell: cd apps/api && pnpm test:e2e (316.0 s)
- shell: sudo kill -9 $(sudo lsof -t -i:1342) (0.2 s)
- shell: cd apps/api && pnpm test (64.5 s)

### Job (archivo de log): 1_build_prod_image (novuapi-ee).txt - 14 pasos, 545 s
- acción actions/checkout@v3 (5.0 s)
- shell: (sin código) (7.7 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.1 s)
- acción pnpm/action-setup@v2 (1.8 s)
- acción actions/setup-node@v3 (21.8 s)
- acción supercharge/redis-github-action@1.5.0 (9.0 s)
- acción supercharge/mongodb-github-action@v1.9.0 (10.9 s)
- acción actions/cache@v3 (6.5 s)
- shell: pnpm install --frozen-lockfile (41.5 s)
- shell: pnpm i -g wait-on (1.8 s)
- shell: pnpm build:api (37.3 s)
- acción depot/setup-action@v1 (2.2 s)
- shell: echo "BULL_MQ_PRO_NPM_TOKEN=***" >> $GITHUB_ENV (0.0 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (399.3 s)

### Job (archivo de log): 2_build_prod_image (novuapi).txt - 13 pasos, 483 s
- acción actions/checkout@v3 (3.6 s)
- shell: (sin código) (5.8 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.1 s)
- acción pnpm/action-setup@v2 (1.8 s)
- acción actions/setup-node@v3 (16.1 s)
- acción supercharge/redis-github-action@1.5.0 (7.4 s)
- acción supercharge/mongodb-github-action@v1.9.0 (8.7 s)
- acción actions/cache@v3 (3.8 s)
- shell: pnpm install --frozen-lockfile (35.4 s)
- shell: pnpm i -g wait-on (1.8 s)
- shell: pnpm build:api (31.6 s)
- acción depot/setup-action@v1 (1.1 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (366.0 s)

## Ejecución #184 (intento 3)

- id: 6617202105
- created_at: 2023-10-23T18:04:50Z
- event: workflow_dispatch | rama: v0.20.x
- conclusion: **failure**
- head_sha: cc476dd3f1487735fe90011fd00150901c5002bf
- mensaje del commit: fix(api): add organization collection context (#4629)
- html_url: https://github.com/novuhq/novu/actions/runs/6617202105

### Job (archivo de log): 0_deploy_prod_api_eu  deploy_service.txt - 9 pasos, 285 s
- shell: echo "Deploying api to novu-prod-eu And Docker Tag ghcr.io/novuhq/novu/api-ee:cc476dd3f1487735fe90011fd0015090 (0.1 s)
- acción actions/checkout@master (1.4 s)
- acción hashicorp/setup-terraform@v1 (1.6 s)
- shell: terraform init (12.5 s)
- shell: echo "ecs_container_name=$(terraform output -json api_ecs_container_name | jq -r .)" >> $GITHUB_ENV (12.7 s)
- acción aws-actions/configure-aws-credentials@v1 (1.0 s)
- shell: aws ecs describe-task-definition --task-definition prod-eu-api-task \ (5.4 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (249.7 s)

### Job (archivo de log): 0_Test E2E EE.txt - 14 pasos, 89 s
- shell: echo (0.1 s)
- acción actions/checkout@v3 (3.8 s)
- shell: (sin código) (6.9 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.7 s)
- acción actions/setup-node@v3 (15.8 s)
- acción supercharge/redis-github-action@1.5.0 (9.0 s)
- acción supercharge/mongodb-github-action@v1.9.0 (8.4 s)
- acción actions/cache@v3 (4.1 s)
- shell: pnpm install --frozen-lockfile (31.5 s)
- shell: pnpm i -g wait-on (2.4 s)
- shell: (sin código) (1.1 s)
- acción vishnudxb/redis-cluster@1.0.5 (3.9 s)
- acción mansagroup/nrwl-nx-action@v3 (0.5 s)

### Job (archivo de log): 0_New Relic Deploy.txt - 2 pasos, 4 s
- shell: echo "RELEASE_VERSION=v0.20.x" >> $GITHUB_ENV (0.1 s)
- acción newrelic/deployment-marker-action@v2.3.0 (3.5 s)

### Job (archivo de log): -2113929216_deploy_prod_api_us.txt - 1 pasos, 486 s
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (486.3 s)

### Job (archivo de log): 0_deploy_docs.txt - 1 pasos, 2 s
- acción fjogeleit/http-request-action@v1 (1.8 s)

### Job (archivo de log): 0_deploy_prod_api_us  deploy_service.txt - 12 pasos, 291 s
- shell: echo "Deploying api to novu-prod And Docker Tag ghcr.io/novuhq/novu/api-ee:cc476dd3f1487735fe90011fd00150901c5 (0.1 s)
- acción actions/checkout@master (3.7 s)
- acción hashicorp/setup-terraform@v1 (1.5 s)
- shell: terraform init (11.8 s)
- shell: echo "ecs_container_name=$(terraform output -json api_ecs_container_name | jq -r .)" >> $GITHUB_ENV (12.3 s)
- acción aws-actions/configure-aws-credentials@v1 (0.6 s)
- shell: aws ecs describe-task-definition --task-definition prod-api-task \ (10.7 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (242.7 s)
- acción actions/checkout@v3 (1.6 s)
- acción martinbeentjes/npm-get-version-action@main (0.7 s)
- acción getsentry/action-release@v1 (5.7 s)

### Job (archivo de log): 0_test_api (novuapi-ee)  e2e_api.txt - 24 pasos, 1046 s
- shell: if ! [[ -z "***" ]]; then (0.1 s)
- acción actions/checkout@v3 (4.7 s)
- shell: (sin código) (7.2 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.9 s)
- acción actions/setup-node@v3 (19.4 s)
- acción supercharge/redis-github-action@1.5.0 (9.1 s)
- acción supercharge/mongodb-github-action@v1.9.0 (10.4 s)
- acción actions/cache@v3 (4.4 s)
- shell: pnpm install --frozen-lockfile (42.3 s)
- shell: pnpm i -g wait-on (2.6 s)
- shell: (sin código) (1.8 s)
- acción vishnudxb/redis-cluster@1.0.5 (4.7 s)
- acción mansagroup/nrwl-nx-action@v3 (63.6 s)
- shell: (sin código) (0.0 s)
- shell: docker-compose -f docker-compose.localstack.yml up -d (54.9 s)
- shell: (sin código) (0.0 s)
- shell: CI='' pnpm build:worker (297.7 s)
- shell: cd apps/worker && pnpm start:test & (5.0 s)
- shell: wait-on --timeout=180000 http://localhost:1342/v1/health-check (21.2 s)
- shell: CI='' pnpm build:api (67.5 s)
- shell: cd apps/api && pnpm test:e2e (355.0 s)
- shell: sudo kill -9 $(sudo lsof -t -i:1342) (0.2 s)
- shell: cd apps/api && pnpm test (72.5 s)

### Job (archivo de log): 0_build_prod_image (novuapi-ee).txt - 14 pasos, 651 s
- acción actions/checkout@v3 (4.4 s)
- shell: (sin código) (10.4 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.1 s)
- acción pnpm/action-setup@v2 (1.9 s)
- acción actions/setup-node@v3 (18.9 s)
- acción supercharge/redis-github-action@1.5.0 (8.3 s)
- acción supercharge/mongodb-github-action@v1.9.0 (9.7 s)
- acción actions/cache@v3 (4.7 s)
- shell: pnpm install --frozen-lockfile (41.6 s)
- shell: pnpm i -g wait-on (1.8 s)
- shell: pnpm build:api (35.6 s)
- acción depot/setup-action@v1 (2.0 s)
- shell: echo "BULL_MQ_PRO_NPM_TOKEN=***" >> $GITHUB_ENV (0.0 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (511.9 s)

### Job (archivo de log): 1_build_prod_image (novuapi).txt - 13 pasos, 551 s
- acción actions/checkout@v3 (5.1 s)
- shell: (sin código) (9.6 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.8 s)
- acción actions/setup-node@v3 (14.0 s)
- acción supercharge/redis-github-action@1.5.0 (8.7 s)
- acción supercharge/mongodb-github-action@v1.9.0 (7.9 s)
- acción actions/cache@v3 (8.0 s)
- shell: pnpm install --frozen-lockfile (32.1 s)
- shell: pnpm i -g wait-on (1.7 s)
- shell: pnpm build:api (27.2 s)
- acción depot/setup-action@v1 (1.0 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (434.2 s)

## Ejecución #185 (intento 2)

- id: 6618063327
- created_at: 2023-10-23T19:28:30Z
- event: workflow_dispatch | rama: v0.20.x
- conclusion: **failure**
- head_sha: 3a98372ed76bab05e6115650970d1cd689cb19c9
- mensaje del commit: fix(api):  integration find one refactor
- html_url: https://github.com/novuhq/novu/actions/runs/6618063327

### Job (archivo de log): 0_deploy_prod_api_eu  deploy_service.txt - 9 pasos, 269 s
- shell: echo "Deploying api to novu-prod-eu And Docker Tag ghcr.io/novuhq/novu/api-ee:3a98372ed76bab05e6115650970d1cd6 (0.1 s)
- acción actions/checkout@master (1.6 s)
- acción hashicorp/setup-terraform@v1 (1.5 s)
- shell: terraform init (12.7 s)
- shell: echo "ecs_container_name=$(terraform output -json api_ecs_container_name | jq -r .)" >> $GITHUB_ENV (12.9 s)
- acción aws-actions/configure-aws-credentials@v1 (1.0 s)
- shell: aws ecs describe-task-definition --task-definition prod-eu-api-task \ (1.9 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (236.9 s)

### Job (archivo de log): 0_Test E2E EE.txt - 14 pasos, 112 s
- shell: echo (0.1 s)
- acción actions/checkout@v3 (5.9 s)
- shell: (sin código) (7.7 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.9 s)
- acción actions/setup-node@v3 (20.2 s)
- acción supercharge/redis-github-action@1.5.0 (8.6 s)
- acción supercharge/mongodb-github-action@v1.9.0 (10.2 s)
- acción actions/cache@v3 (5.9 s)
- shell: pnpm install --frozen-lockfile (41.4 s)
- shell: pnpm i -g wait-on (2.5 s)
- shell: (sin código) (2.1 s)
- acción vishnudxb/redis-cluster@1.0.5 (4.8 s)
- acción mansagroup/nrwl-nx-action@v3 (0.6 s)

### Job (archivo de log): 0_New Relic Deploy.txt - 2 pasos, 3 s
- shell: echo "RELEASE_VERSION=v0.20.x" >> $GITHUB_ENV (0.1 s)
- acción newrelic/deployment-marker-action@v2.3.0 (2.5 s)

### Job (archivo de log): 0_test_api (novuapi)  e2e_api.txt - 24 pasos, 501 s
- shell: if ! [[ -z "***" ]]; then (0.1 s)
- acción actions/checkout@v3 (2.9 s)
- shell: (sin código) (7.0 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.6 s)
- acción actions/setup-node@v3 (13.5 s)
- acción supercharge/redis-github-action@1.5.0 (7.7 s)
- acción supercharge/mongodb-github-action@v1.9.0 (7.8 s)
- acción actions/cache@v3 (3.0 s)
- shell: pnpm install --frozen-lockfile (33.9 s)
- shell: pnpm i -g wait-on (2.0 s)
- shell: (sin código) (1.3 s)
- acción vishnudxb/redis-cluster@1.0.5 (3.2 s)
- acción mansagroup/nrwl-nx-action@v3 (22.2 s)
- shell: (sin código) (0.0 s)
- shell: docker-compose -f docker-compose.localstack.yml up -d (48.0 s)
- shell: (sin código) (0.0 s)
- shell: CI='' pnpm build:worker (6.0 s)
- shell: cd apps/worker && pnpm start:test & (5.1 s)
- shell: wait-on --timeout=180000 http://localhost:1342/v1/health-check (14.8 s)
- shell: CI='' pnpm build:api (4.3 s)
- shell: cd apps/api && pnpm test:e2e (264.1 s)
- shell: sudo kill -9 $(sudo lsof -t -i:1342) (0.1 s)
- shell: cd apps/api && pnpm test (52.2 s)

### Job (archivo de log): -2113929216_deploy_prod_api_us.txt - 13 pasos, 481 s
- acción actions/checkout@v3 (5.1 s)
- shell: (sin código) (7.1 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.8 s)
- acción actions/setup-node@v3 (22.6 s)
- acción supercharge/redis-github-action@1.5.0 (8.4 s)
- acción supercharge/mongodb-github-action@v1.9.0 (8.9 s)
- acción actions/cache@v3 (4.5 s)
- shell: pnpm install --frozen-lockfile (31.6 s)
- shell: pnpm i -g wait-on (1.7 s)
- shell: pnpm build:api (27.7 s)
- acción depot/setup-action@v1 (1.7 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (359.8 s)

### Job (archivo de log): 0_deploy_docs.txt - 1 pasos, 1 s
- acción fjogeleit/http-request-action@v1 (0.6 s)

### Job (archivo de log): 0_deploy_prod_api_us  deploy_service.txt - 12 pasos, 278 s
- shell: echo "Deploying api to novu-prod And Docker Tag ghcr.io/novuhq/novu/api-ee:3a98372ed76bab05e6115650970d1cd689c (0.1 s)
- acción actions/checkout@master (1.0 s)
- acción hashicorp/setup-terraform@v1 (1.2 s)
- shell: terraform init (10.2 s)
- shell: echo "ecs_container_name=$(terraform output -json api_ecs_container_name | jq -r .)" >> $GITHUB_ENV (11.7 s)
- acción aws-actions/configure-aws-credentials@v1 (0.5 s)
- shell: aws ecs describe-task-definition --task-definition prod-api-task \ (7.0 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (242.1 s)
- acción actions/checkout@v3 (1.2 s)
- acción martinbeentjes/npm-get-version-action@main (0.6 s)
- acción getsentry/action-release@v1 (2.5 s)

### Job (archivo de log): 0_test_api (novuapi-ee)  e2e_api.txt - 24 pasos, 602 s
- shell: if ! [[ -z "***" ]]; then (0.1 s)
- acción actions/checkout@v3 (3.0 s)
- shell: (sin código) (17.3 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.8 s)
- acción actions/setup-node@v3 (14.9 s)
- acción supercharge/redis-github-action@1.5.0 (9.8 s)
- acción supercharge/mongodb-github-action@v1.9.0 (8.9 s)
- acción actions/cache@v3 (3.4 s)
- shell: pnpm install --frozen-lockfile (36.8 s)
- shell: pnpm i -g wait-on (2.2 s)
- shell: (sin código) (1.2 s)
- acción vishnudxb/redis-cluster@1.0.5 (3.6 s)
- acción mansagroup/nrwl-nx-action@v3 (26.4 s)
- shell: (sin código) (0.0 s)
- shell: docker-compose -f docker-compose.localstack.yml up -d (59.1 s)
- shell: (sin código) (0.0 s)
- shell: CI='' pnpm build:worker (6.2 s)
- shell: cd apps/worker && pnpm start:test & (5.0 s)
- shell: wait-on --timeout=180000 http://localhost:1342/v1/health-check (19.3 s)
- shell: CI='' pnpm build:api (5.1 s)
- shell: cd apps/api && pnpm test:e2e (313.6 s)
- shell: sudo kill -9 $(sudo lsof -t -i:1342) (0.2 s)
- shell: cd apps/api && pnpm test (64.0 s)

### Job (archivo de log): 0_build_prod_image (novuapi-ee).txt - 14 pasos, 573 s
- acción actions/checkout@v3 (4.6 s)
- shell: (sin código) (7.5 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.1 s)
- acción pnpm/action-setup@v2 (2.9 s)
- acción actions/setup-node@v3 (21.5 s)
- acción supercharge/redis-github-action@1.5.0 (8.7 s)
- acción supercharge/mongodb-github-action@v1.9.0 (10.6 s)
- acción actions/cache@v3 (4.6 s)
- shell: pnpm install --frozen-lockfile (42.3 s)
- shell: pnpm i -g wait-on (2.0 s)
- shell: pnpm build:api (35.7 s)
- acción depot/setup-action@v1 (2.1 s)
- shell: echo "BULL_MQ_PRO_NPM_TOKEN=***" >> $GITHUB_ENV (0.0 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (430.9 s)

### Job (archivo de log): 1_build_prod_image (novuapi).txt - 13 pasos, 481 s
- acción actions/checkout@v3 (5.1 s)
- shell: (sin código) (7.1 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (1.8 s)
- acción actions/setup-node@v3 (22.6 s)
- acción supercharge/redis-github-action@1.5.0 (8.4 s)
- acción supercharge/mongodb-github-action@v1.9.0 (8.9 s)
- acción actions/cache@v3 (4.5 s)
- shell: pnpm install --frozen-lockfile (31.6 s)
- shell: pnpm i -g wait-on (1.7 s)
- shell: pnpm build:api (27.7 s)
- acción depot/setup-action@v1 (1.7 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (359.8 s)

## Ejecución #186 (intento 1)

- id: 6654827774
- created_at: 2023-10-26T13:28:31Z
- event: workflow_dispatch | rama: v0.21.x
- conclusion: **failure**
- head_sha: ab02ec67f8e3b760ad92935f814946b40be2cfd4
- mensaje del commit: Merge pull request #4651 from Arcturus22/Branch0
- html_url: https://github.com/novuhq/novu/actions/runs/6654827774

### Job (archivo de log): 0_deploy_prod_api_eu  deploy_service.txt - 9 pasos, 243 s
- shell: echo "Deploying api to novu-prod-eu And Docker Tag ghcr.io/novuhq/novu/api-ee:ab02ec67f8e3b760ad92935f814946b4 (0.1 s)
- acción actions/checkout@master (1.5 s)
- acción hashicorp/setup-terraform@v1 (1.6 s)
- shell: terraform init (14.7 s)
- shell: echo "ecs_container_name=$(terraform output -json api_ecs_container_name | jq -r .)" >> $GITHUB_ENV (15.8 s)
- acción aws-actions/configure-aws-credentials@v1 (1.1 s)
- shell: aws ecs describe-task-definition --task-definition prod-eu-api-task \ (1.9 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (206.6 s)

### Job (archivo de log): 0_Test E2E EE.txt - 14 pasos, 117 s
- shell: echo (0.1 s)
- acción actions/checkout@v3 (4.4 s)
- shell: (sin código) (6.5 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (3.0 s)
- acción actions/setup-node@v3 (23.6 s)
- acción supercharge/redis-github-action@1.5.0 (7.8 s)
- acción supercharge/mongodb-github-action@v1.9.0 (10.7 s)
- acción actions/cache@v3 (9.6 s)
- shell: pnpm install --frozen-lockfile (41.2 s)
- shell: pnpm i -g wait-on (2.4 s)
- shell: (sin código) (1.7 s)
- acción vishnudxb/redis-cluster@1.0.5 (4.8 s)
- acción mansagroup/nrwl-nx-action@v3 (0.7 s)

### Job (archivo de log): 0_New Relic Deploy.txt - 2 pasos, 3 s
- shell: echo "RELEASE_VERSION=v0.21.x" >> $GITHUB_ENV (0.1 s)
- acción newrelic/deployment-marker-action@v2.3.0 (2.4 s)

### Job (archivo de log): 0_test_api (novuapi)  e2e_api.txt - 24 pasos, 606 s
- shell: if ! [[ -z "***" ]]; then (0.1 s)
- acción actions/checkout@v3 (4.2 s)
- shell: (sin código) (6.4 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (2.7 s)
- acción actions/setup-node@v3 (20.2 s)
- acción supercharge/redis-github-action@1.5.0 (9.1 s)
- acción supercharge/mongodb-github-action@v1.9.0 (10.0 s)
- acción actions/cache@v3 (10.1 s)
- shell: pnpm install --frozen-lockfile (38.0 s)
- shell: pnpm i -g wait-on (2.2 s)
- shell: (sin código) (1.7 s)
- acción vishnudxb/redis-cluster@1.0.5 (4.8 s)
- acción mansagroup/nrwl-nx-action@v3 (32.0 s)
- shell: (sin código) (0.0 s)
- shell: docker-compose -f docker-compose.localstack.yml up -d (49.9 s)
- shell: (sin código) (0.0 s)
- shell: CI='' pnpm build:worker (6.7 s)
- shell: cd apps/worker && pnpm start:test & (5.0 s)
- shell: wait-on --timeout=180000 http://localhost:1342/v1/health-check (20.2 s)
- shell: CI='' pnpm build:api (4.4 s)
- shell: cd apps/api && pnpm test:e2e (315.9 s)
- shell: sudo kill -9 $(sudo lsof -t -i:1342) (0.2 s)
- shell: cd apps/api && pnpm test (62.1 s)

### Job (archivo de log): 0_deploy_docs.txt - 1 pasos, 1 s
- acción fjogeleit/http-request-action@v1 (0.6 s)

### Job (archivo de log): 0_deploy_prod_api_us  deploy_service.txt - 12 pasos, 277 s
- shell: echo "Deploying api to novu-prod And Docker Tag ghcr.io/novuhq/novu/api-ee:ab02ec67f8e3b760ad92935f814946b40be (0.1 s)
- acción actions/checkout@master (1.3 s)
- acción hashicorp/setup-terraform@v1 (1.6 s)
- shell: terraform init (11.7 s)
- shell: echo "ecs_container_name=$(terraform output -json api_ecs_container_name | jq -r .)" >> $GITHUB_ENV (11.8 s)
- acción aws-actions/configure-aws-credentials@v1 (0.6 s)
- shell: aws ecs describe-task-definition --task-definition prod-api-task \ (1.6 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (242.5 s)
- acción actions/checkout@v3 (1.5 s)
- acción martinbeentjes/npm-get-version-action@main (0.8 s)
- acción getsentry/action-release@v1 (3.2 s)

### Job (archivo de log): 0_test_api (novuapi-ee)  e2e_api.txt - 24 pasos, 600 s
- shell: if ! [[ -z "***" ]]; then (0.1 s)
- acción actions/checkout@v3 (3.1 s)
- shell: (sin código) (6.3 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.0 s)
- acción pnpm/action-setup@v2 (2.9 s)
- acción actions/setup-node@v3 (16.1 s)
- acción supercharge/redis-github-action@1.5.0 (7.6 s)
- acción supercharge/mongodb-github-action@v1.9.0 (9.1 s)
- acción actions/cache@v3 (7.1 s)
- shell: pnpm install --frozen-lockfile (39.1 s)
- shell: pnpm i -g wait-on (2.0 s)
- shell: (sin código) (1.2 s)
- acción vishnudxb/redis-cluster@1.0.5 (3.9 s)
- acción mansagroup/nrwl-nx-action@v3 (31.3 s)
- shell: (sin código) (0.0 s)
- shell: docker-compose -f docker-compose.localstack.yml up -d (51.5 s)
- shell: (sin código) (0.0 s)
- shell: CI='' pnpm build:worker (5.4 s)
- shell: cd apps/worker && pnpm start:test & (5.0 s)
- shell: wait-on --timeout=180000 http://localhost:1342/v1/health-check (19.9 s)
- shell: CI='' pnpm build:api (3.6 s)
- shell: cd apps/api && pnpm test:e2e (319.2 s)
- shell: sudo kill -9 $(sudo lsof -t -i:1342) (0.2 s)
- shell: cd apps/api && pnpm test (66.0 s)

### Job (archivo de log): 0_build_prod_image (novuapi-ee).txt - 14 pasos, 507 s
- acción actions/checkout@v3 (3.6 s)
- shell: (sin código) (6.5 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.1 s)
- acción pnpm/action-setup@v2 (2.8 s)
- acción actions/setup-node@v3 (15.7 s)
- acción supercharge/redis-github-action@1.5.0 (8.3 s)
- acción supercharge/mongodb-github-action@v1.9.0 (8.9 s)
- acción actions/cache@v3 (6.9 s)
- shell: pnpm install --frozen-lockfile (39.5 s)
- shell: pnpm i -g wait-on (1.6 s)
- shell: pnpm build:api (35.4 s)
- acción depot/setup-action@v1 (1.3 s)
- shell: echo "BULL_MQ_PRO_NPM_TOKEN=***" >> $GITHUB_ENV (0.0 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (376.9 s)

### Job (archivo de log): 1_build_prod_image (novuapi).txt - 13 pasos, 371 s
- acción actions/checkout@v3 (4.5 s)
- shell: (sin código) (6.5 s)
- shell: echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p (0.1 s)
- acción pnpm/action-setup@v2 (2.9 s)
- acción actions/setup-node@v3 (22.1 s)
- acción supercharge/redis-github-action@1.5.0 (8.3 s)
- acción supercharge/mongodb-github-action@v1.9.0 (9.9 s)
- acción actions/cache@v3 (8.8 s)
- shell: pnpm install --frozen-lockfile (38.1 s)
- shell: pnpm i -g wait-on (1.8 s)
- shell: pnpm build:api (37.8 s)
- acción depot/setup-action@v1 (1.7 s)
- shell: echo $GH_PASSWORD | docker login ghcr.io -u $GH_ACTOR --password-stdin (228.9 s)
