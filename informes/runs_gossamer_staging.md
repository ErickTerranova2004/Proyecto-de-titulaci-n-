# Ejecuciones históricas: chainsafe/gossamer / .github/workflows/staging.yml

- Ejecuciones encontradas en GHALogs: 5

> Los jobs y pasos provienen de log_insights (ejecución real de 2023). Un job ausente normalmente no se ejecutó o no generó log. El campo 'errors' de un paso son errores de análisis del script, no el resultado del paso.

## Ejecución #154 (intento 1)

- id: 6286049703
- created_at: 2023-09-23T21:16:07Z
- event: push | rama: staging
- conclusion: **failure**
- head_sha: 7f97fb922872ce9b1cf28fbeb9a5f2fd7d38ba19
- mensaje del commit: Store state entries
- html_url: https://github.com/ChainSafe/gossamer/actions/runs/6286049703

### Job (archivo de log): 1_update (polkadot).txt - 6 pasos, 2037 s
- acción actions/checkout@v4 (3.5 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.7 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (164.2 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.0 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (1867.3 s)

### Job (archivo de log): 2_update (kusama).txt - 6 pasos, 311 s
- acción actions/checkout@v4 (3.6 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.8 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (178.1 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.0 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (127.2 s)

### Job (archivo de log): 3_update (westend).txt - 6 pasos, 384 s
- acción actions/checkout@v4 (4.9 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.9 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (219.1 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (157.6 s)

## Ejecución #155 (intento 1)

- id: 6301448294
- created_at: 2023-09-25T15:22:10Z
- event: push | rama: staging
- conclusion: **failure**
- head_sha: e79ba7fe163351370faadbf53c0da6d1fc2edfe6
- mensaje del commit: Merge branch 'eclesio/pebble-checkpoints' into staging
- html_url: https://github.com/ChainSafe/gossamer/actions/runs/6301448294

### Job (archivo de log): 3_update (westend).txt - 6 pasos, 466 s
- acción actions/checkout@v4 (6.4 s)
- acción aws-actions/configure-aws-credentials@v4 (0.7 s)
- acción aws-actions/amazon-ecr-login@v1 (1.9 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (267.4 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (189.9 s)

### Job (archivo de log): 1_update (polkadot).txt - 6 pasos, 2091 s
- acción actions/checkout@v4 (4.0 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.8 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (215.1 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (1869.9 s)

### Job (archivo de log): 2_update (kusama).txt - 6 pasos, 354 s
- acción actions/checkout@v4 (7.5 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.9 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (201.0 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.0 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (142.8 s)

## Ejecución #156 (intento 1)

- id: 6322074043
- created_at: 2023-09-27T06:07:54Z
- event: push | rama: staging
- conclusion: **success**
- head_sha: 6617a76a27cfcc0d7dc3867c39769380dec85232
- mensaje del commit: Merge branch 'eclesio/pebble-checkpoints' into eclesio/bad-signature-with-checkpoint
- html_url: https://github.com/ChainSafe/gossamer/actions/runs/6322074043

### Job (archivo de log): 3_update (westend).txt - 6 pasos, 320 s
- acción actions/checkout@v4 (3.6 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.8 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (171.8 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.0 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (142.5 s)

### Job (archivo de log): 1_update (polkadot).txt - 6 pasos, 384 s
- acción actions/checkout@v4 (3.6 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.8 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (204.4 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (173.9 s)

### Job (archivo de log): 2_update (kusama).txt - 6 pasos, 415 s
- acción actions/checkout@v4 (4.7 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.7 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (172.7 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.0 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (235.6 s)

## Ejecución #157 (intento 1)

- id: 6394567736
- created_at: 2023-10-03T14:41:00Z
- event: push | rama: staging
- conclusion: **failure**
- head_sha: d49f3b27b05a67a418b9034db8e30139102818dc
- mensaje del commit: retry at block 9m
- html_url: https://github.com/ChainSafe/gossamer/actions/runs/6394567736

### Job (archivo de log): 3_update (westend).txt - 6 pasos, 305 s
- acción actions/checkout@v4 (3.7 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.6 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (157.0 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.0 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (142.5 s)

### Job (archivo de log): 1_update (polkadot).txt - 6 pasos, 2041 s
- acción actions/checkout@v4 (5.4 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.6 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (162.6 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.0 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (1871.0 s)

### Job (archivo de log): 2_update (kusama).txt - 6 pasos, 373 s
- acción actions/checkout@v4 (5.5 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.9 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (222.2 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (142.3 s)

## Ejecución #158 (intento 1)

- id: 6397410913
- created_at: 2023-10-03T19:13:16Z
- event: push | rama: staging
- conclusion: **failure**
- head_sha: 37e2ad9addb6b131388b58c4e8d2cfeb3e1afacc
- mensaje del commit: Merge branch 'diego/trieV1/versioning' into staging
- html_url: https://github.com/ChainSafe/gossamer/actions/runs/6397410913

### Job (archivo de log): 1_update (polkadot).txt - 6 pasos, 2063 s
- acción actions/checkout@v4 (4.4 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.6 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (174.5 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (1881.8 s)

### Job (archivo de log): 2_update (kusama).txt - 6 pasos, 349 s
- acción actions/checkout@v4 (3.8 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (1.9 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (200.3 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (142.3 s)

### Job (archivo de log): 3_update (westend).txt - 6 pasos, 433 s
- acción actions/checkout@v4 (4.8 s)
- acción aws-actions/configure-aws-credentials@v4 (0.6 s)
- acción aws-actions/amazon-ecr-login@v1 (2.0 s)
- shell: docker build -f=Dockerfile.staging . --progress=plain -t=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG --build-arg  (205.2 s)
- acción aws-actions/amazon-ecs-render-task-definition@v1 (0.1 s)
- acción aws-actions/amazon-ecs-deploy-task-definition@v1 (220.6 s)
