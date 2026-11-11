from django.test import SimpleTestCase

from riesgo.models import PATRON_DESPLIEGUE, EjecucionWorkflow
from riesgo.services.etiquetado import etiquetar_ejecucion


def job(id_, nombre, pasos, conclusion="success", inicio="2026-10-15T10:00"):
    return {"id": id_, "name": nombre, "conclusion": conclusion,
            "started_at": inicio,
            "steps": [{"number": i + 1, "name": n, "conclusion": c}
                      for i, (n, c) in enumerate(pasos)]}


class ReglaEtiquetadoTest(SimpleTestCase):
    def etiquetar(self, conclusion, jobs):
        return etiquetar_ejecucion(conclusion, jobs, PATRON_DESPLIEGUE)

    def test_exito_con_despliegue(self):
        r = self.etiquetar("success", [job(1, "deploy", [
            ("Build", "success"), ("Deploy to ECS", "success")])])
        self.assertEqual(r["etiqueta"], "despliegue_completado")
        self.assertTrue(r["despliegue_ejecutado"])

    def test_exito_sin_despliegue_se_excluye(self):
        r = self.etiquetar("success", [job(1, "build", [
            ("Build", "success"), ("Deploy to ECS", "skipped")])])
        self.assertEqual(r["etiqueta"], "excluida_sin_intento")

    def test_fallo_antes_del_despliegue(self):
        r = self.etiquetar("failure", [job(1, "deploy", [
            ("Build", "failure"), ("Deploy to ECS", "skipped")], "failure")])
        self.assertEqual(r["etiqueta"], "despliegue_no_completado")
        self.assertEqual(r["subtipo_etiqueta"], "antes_del_despliegue")
        self.assertEqual(r["paso_fallido"], "deploy / Build")

    def test_fallo_en_el_paso_de_despliegue(self):
        r = self.etiquetar("failure", [job(1, "deploy", [
            ("Build", "success"), ("Deploy to ECS", "failure")], "failure")])
        self.assertEqual(r["subtipo_etiqueta"], "en_paso_de_despliegue")
        self.assertEqual(r["paso_fallido"], "deploy / Deploy to ECS")

    def test_fallo_posterior_en_el_mismo_job(self):
        r = self.etiquetar("failure", [job(1, "deploy", [
            ("Deploy to ECS", "success"), ("Smoke test", "failure")],
            "failure")])
        self.assertEqual(r["subtipo_etiqueta"], "posterior_mismo_job")

    def test_fallo_en_otro_job_con_despliegue_completado_es_ambiguo(self):
        # Caso novu: el despliegue terminó y falló un job de pruebas.
        r = self.etiquetar("failure", [
            job(1, "deploy", [("Deploy to ECS", "success")]),
            job(2, "e2e", [("Run tests", "failure")], "failure",
                "2026-10-15T10:05")])
        self.assertEqual(r["etiqueta"], "excluida_ambigua")
        self.assertEqual(r["paso_fallido"], "e2e / Run tests")

    def test_cancelada_se_excluye(self):
        r = self.etiquetar("cancelled", [])
        self.assertEqual(r["etiqueta"], "excluida_otro_resultado")

    def test_omitida_y_pendiente_de_aprobacion_se_excluyen(self):
        for conclusion in ("skipped", "action_required", "startup_failure"):
            with self.subTest(conclusion=conclusion):
                r = self.etiquetar(conclusion, [job(1, "deploy", [
                    ("Deploy to ECS", "skipped")], conclusion)])
                self.assertEqual(r["etiqueta"], "excluida_otro_resultado")

    def test_fallo_sin_ningun_job_se_excluye(self):
        # El workflow no llegó a arrancar (YAML inválido, startup_failure):
        # no es un intento de despliegue, no cuenta como y = 1.
        r = self.etiquetar("failure", [])
        self.assertEqual(r["etiqueta"], "excluida_sin_jobs")
        self.assertEqual(r["subtipo_etiqueta"], "")
        self.assertFalse(r["despliegue_ejecutado"])


class SoloProduccionTest(SimpleTestCase):
    """Solo cuentan los despliegues a producción (fase 2, «Excluidas»)."""

    def etiquetar(self, conclusion, jobs):
        return etiquetar_ejecucion(conclusion, jobs, PATRON_DESPLIEGUE)

    def test_despliegue_solo_a_entornos_no_productivos_se_excluye(self):
        for entorno in ("deploy-staging", "deploy-dev", "Deploy to test",
                        "preview", "deploy-demo", "deploy-beta", "nightly"):
            with self.subTest(entorno=entorno):
                r = self.etiquetar("success", [job(1, entorno, [
                    ("Build", "success"), ("Deploy to ECS", "success")])])
                self.assertEqual(r["etiqueta"], "excluida_no_produccion")
                self.assertFalse(r["despliegue_ejecutado"])

    def test_el_entorno_tambien_se_lee_del_nombre_del_paso(self):
        r = self.etiquetar("success", [job(1, "deploy", [
            ("Deploy to staging", "success")])])
        self.assertEqual(r["etiqueta"], "excluida_no_produccion")

    def test_staging_y_produccion_cuenta_la_de_produccion(self):
        r = self.etiquetar("success", [
            job(1, "deploy-staging", [("Deploy to ECS", "success")]),
            job(2, "deploy-production", [("Deploy to ECS", "success")],
                inicio="2026-10-15T10:05")])
        self.assertEqual(r["etiqueta"], "despliegue_completado")

    def test_fallo_en_el_despliegue_a_staging_se_excluye(self):
        r = self.etiquetar("failure", [job(1, "deploy-staging", [
            ("Build", "success"), ("Deploy to ECS", "failure")], "failure")])
        self.assertEqual(r["etiqueta"], "excluida_no_produccion")

    def test_fallo_tras_desplegar_solo_a_staging_se_excluye(self):
        # Staging terminó bien y fallaron las pruebas posteriores: no hubo
        # intento de despliegue a producción.
        r = self.etiquetar("failure", [
            job(1, "deploy-staging", [("Deploy to ECS", "success")]),
            job(2, "e2e", [("Run tests", "failure")], "failure",
                "2026-10-15T10:05")])
        self.assertEqual(r["etiqueta"], "excluida_no_produccion")

    def test_pasos_con_specs_no_son_despliegue(self):
        # «ecs» no debe encajar dentro de «specs» (caso elsa-hanke/elsa-backend).
        r = self.etiquetar("success", [job(1, "e2e", [
            ("Select Cypress specs and write summary", "success")])])
        self.assertEqual(r["etiqueta"], "excluida_sin_intento")

    def test_fallo_en_el_despliegue_a_produccion_es_y1(self):
        r = self.etiquetar("failure", [
            job(1, "deploy-staging", [("Deploy to ECS", "success")]),
            job(2, "deploy-production", [("Deploy to ECS", "failure")],
                "failure", "2026-10-15T10:05")])
        self.assertEqual(r["etiqueta"], "despliegue_no_completado")
        self.assertEqual(r["subtipo_etiqueta"], "en_paso_de_despliegue")


class VariableObjetivoTest(SimpleTestCase):
    """La `y` del modelo para cada etiqueta (fase2_variable_objetivo.md)."""

    def y(self, conclusion, jobs):
        etiqueta = etiquetar_ejecucion(conclusion, jobs,
                                       PATRON_DESPLIEGUE)["etiqueta"]
        return EjecucionWorkflow(etiqueta=etiqueta).y

    def test_despliegue_completado_es_y0(self):
        self.assertEqual(self.y("success", [job(1, "deploy", [
            ("Deploy to ECS", "success")])]), 0)

    def test_fallo_antes_del_despliegue_es_y1(self):
        self.assertEqual(self.y("failure", [job(1, "deploy", [
            ("Build", "failure"), ("Deploy to ECS", "skipped")],
            "failure")]), 1)

    def test_excluidas_no_tienen_y(self):
        casos = {"sin jobs": ("failure", []),
                 "cancelada": ("cancelled", []),
                 "omitida": ("skipped", []),
                 "pendiente de aprobación": ("action_required", []),
                 "solo staging": ("success", [job(1, "deploy-staging", [
                     ("Deploy to ECS", "success")])])}
        for nombre, (conclusion, jobs) in casos.items():
            with self.subTest(nombre):
                self.assertIsNone(self.y(conclusion, jobs))


def job_yaml(id_, nombre, pasos, conclusion="success", entorno=None,
             inicio="2026-10-15T10:00"):
    """Job de la API enriquecido con datos del YAML (environment, uses, run),
    como lo hace scripts/filtrar_repos_reales.py."""
    j = {"id": id_, "name": nombre, "conclusion": conclusion,
         "started_at": inicio,
         "steps": [dict({"number": i + 1, "name": n, "conclusion": c}, **extra)
                   for i, (n, c, extra) in enumerate(pasos)]}
    if entorno:
        j["environment"] = entorno
    return j


class FalsosPositivosTest(SimpleTestCase):
    """Falsos positivos encontrados en la auditoría de PATRON_DESPLIEGUE
    (muestra de 30 ejecuciones y=0, 2026-11-08)."""

    def etiquetar(self, conclusion, jobs):
        return etiquetar_ejecucion(conclusion, jobs, PATRON_DESPLIEGUE)

    def test_pasos_auxiliares_no_son_despliegue(self):
        auxiliares = [
            "Compute App Engine version tag",       # solana-playground
            "Install Vercel CLI",                   # auth0/openidconnect-playground
            "Show deployed URL",                    # oatmealfarmnetwork
            "Set DEPLOY_ENV from Branch Name",      # nulib/dc-api-v2
            "Confirm deploy environment",           # nulib/dc-api-v2
            "Set GitHub Deploy Key",                # nulib/dc-api-v2
            "Prepapre app.yaml file for production deployment",  # noplp-stats
            "Check deployment status",
            "Deployment summary",
            "Setup flyctl",
            "Get Cloud Run URL",
            "Build webapp",
            "npm run deploy:dry-run",
        ]
        for nombre in auxiliares:
            with self.subTest(nombre):
                r = self.etiquetar("success", [job(1, "build", [
                    (nombre, "success")])])
                self.assertEqual(r["etiqueta"], "excluida_sin_intento")

    def test_job_de_despliegue_omitido_no_cuenta(self):
        # solana-playground: «Deploy Playground Server» estaba skipped.
        r = self.etiquetar("success", [
            job(1, "Resolve deploy version", [
                ("Compute App Engine version tag", "success")]),
            job(2, "Deploy Server", [("Deploy to App Engine", "skipped")],
                "skipped")])
        self.assertEqual(r["etiqueta"], "excluida_sin_intento")

    def test_entornos_no_productivos_en_el_nombre_del_job(self):
        # pagopa/oneidentity: despliegues a uat y dev.
        r = self.etiquetar("success", [
            job(1, "Deploy on ECS io-uat-eu-south-1", [
                ("Deploy Amazon ECS task definition", "success")]),
            job(2, "Deploy on ECS dev-eu-south-1", [
                ("Deploy Amazon ECS task definition", "success")])])
        self.assertEqual(r["etiqueta"], "excluida_no_produccion")

    def test_hosting_estatico_no_es_despliegue_de_una_aplicacion(self):
        # dune-admin (Cloudflare Pages) y similares.
        estaticos = [
            ("Deploy Frontend to Cloudflare Pages", {}),
            ("Deploy static site to S3 bucket", {}),
            ("Deploy", {"uses": "actions/deploy-pages@v4"}),
            ("Deploy", {"run": "npx netlify deploy --prod"}),
            ("Deploy", {"run": "firebase deploy --only hosting"}),
            ("Deploy", {"uses": "Azure/static-web-apps-deploy@v1"}),
        ]
        for nombre, extra in estaticos:
            with self.subTest(nombre, **extra):
                r = self.etiquetar("success", [job_yaml(1, "deploy", [
                    (nombre, "success", extra)])])
                self.assertEqual(r["etiqueta"], "excluida_sin_intento")

    def test_backend_cuenta_aunque_el_frontend_sea_estatico(self):
        r = self.etiquetar("success", [
            job(1, "deploy-frontend", [
                ("Deploy static site to S3 bucket", "success")]),
            job(2, "deploy-backend", [
                ("Deploy Amazon ECS task definition", "success")],
                inicio="2026-10-15T10:05")])
        self.assertEqual(r["etiqueta"], "despliegue_completado")


class SenalesPrioritariasTest(SimpleTestCase):
    """Entorno del job y acción conocida pesan más que el nombre del paso."""

    def etiquetar(self, conclusion, jobs):
        return etiquetar_ejecucion(conclusion, jobs, PATRON_DESPLIEGUE)

    def test_accion_conocida_aunque_el_nombre_no_diga_deploy(self):
        for extra in ({"uses": "google-github-actions/deploy-cloudrun@v2"},
                      {"uses": "aws-actions/amazon-ecs-deploy-task-definition@v2"},
                      {"run": "aws ecs update-service --cluster c --service s"},
                      {"run": "gcloud run deploy api --image x"},
                      {"run": "helm upgrade --install api ./chart"}):
            with self.subTest(**extra):
                r = self.etiquetar("success", [job_yaml(1, "release", [
                    ("Publish", "success", extra)])])
                self.assertEqual(r["etiqueta"], "despliegue_completado")

    def test_accion_por_defecto_en_el_nombre(self):
        r = self.etiquetar("success", [job(1, "deploy", [
            ("Run cloudflare/wrangler-action@v3", "success")])])
        self.assertEqual(r["etiqueta"], "despliegue_completado")

    def test_dry_run_de_una_accion_conocida_no_cuenta(self):
        r = self.etiquetar("success", [job_yaml(1, "check", [
            ("Plan", "success", {"run": "helm upgrade --install api . --dry-run"})])])
        self.assertEqual(r["etiqueta"], "excluida_sin_intento")

    def test_el_environment_del_job_manda_sobre_el_nombre(self):
        # pongstylin/tactics: workflow «Deploy Staging» con environment production.
        r = self.etiquetar("success", [job_yaml(1, "deploy-staging", [
            ("Deploy Amazon ECS task definition", "success", {})],
            entorno="production")])
        self.assertEqual(r["etiqueta"], "despliegue_completado")
        # emeralddb: job «deploy-main» con environment beta.
        r = self.etiquetar("success", [job_yaml(1, "deploy-main", [
            ("Deploy to Heroku", "success", {})], entorno="beta")])
        self.assertEqual(r["etiqueta"], "excluida_no_produccion")

    def test_job_de_hosting_estatico_no_cuenta(self):
        # sbmagar13/recipe-jar: job «Deploy to Cloudflare Pages», paso «Deploy»
        # con cloudflare/wrangler-action (muestra con semilla 2026).
        r = self.etiquetar("success", [job_yaml(1, "Deploy to Cloudflare Pages", [
            ("Deploy", "success", {"uses": "cloudflare/wrangler-action@v3"})])])
        self.assertEqual(r["etiqueta"], "excluida_sin_intento")

    def test_matriz_de_despliegue_no_es_despliegue(self):
        # hms-dbmi-cellenics/iac: solo se generó la matriz; el despliegue se omitió.
        r = self.etiquetar("success", [
            job_yaml(1, "load-config / Generate deployment matrix", [
                ("Build deployment matrix", "success", {})]),
            job_yaml(2, "Deploy changed CloudFormation template", [], "skipped")])
        self.assertEqual(r["etiqueta"], "excluida_sin_intento")

    def test_comprobacion_de_sintaxis_de_ansible_no_es_despliegue(self):
        # Cour-de-cassation/judilibre-search y cbg-ethz/WisePulse (muestra con
        # semilla 7): «Syntax check» con ansible-playbook --syntax-check.
        r = self.etiquetar("success", [job_yaml(1, "Ansible checks", [
            ("Syntax check", "success",
             {"run": "ansible-playbook -i inventory site.yml --syntax-check"})])])
        self.assertEqual(r["etiqueta"], "excluida_sin_intento")

    def test_entornos_no_productivos_de_la_regla_7(self):
        # reserveRecAdminTest (camelCase), preprod y el entorno «at» de udot-atspm.
        for entorno in ("reserveRecAdminTest", "preprod", "pre-prod", "at", "pull_request"):
            with self.subTest(entorno=entorno):
                r = self.etiquetar("success", [job_yaml(1, "deploy", [
                    ("CDK Deploy", "success", {"run": "cdk deploy --all"})], entorno=entorno)])
                self.assertEqual(r["etiqueta"], "excluida_no_produccion")
        # «at» solo cuenta como entorno completo, no dentro de un nombre.
        r = self.etiquetar("success", [job_yaml(1, "Deploy - at - api", [
            ("CloudRun Service Deploy", "success",
             {"uses": "google-github-actions/deploy-cloudrun@v2"})], entorno="prod")])
        self.assertEqual(r["etiqueta"], "despliegue_completado")

    def test_fallo_en_job_con_entorno_no_productivo(self):
        # PA-NIHR-CRN/dte-study-api: falló «Deploy Dev» (environment DEV) y los
        # despliegues a TEST…PROD se omitieron.
        r = self.etiquetar("failure", [
            job_yaml(1, "Build", [("Build", "success", {})]),
            job_yaml(2, "Deploy Dev", [("Configure AWS credentials", "failure", {})],
                     "failure", entorno="DEV"),
            job_yaml(3, "Deploy Prod", [], "skipped", entorno="PROD")])
        self.assertEqual(r["etiqueta"], "excluida_no_produccion")

    def test_paso_build_de_accion_docker_con_despliegue_omitido_por_if(self):
        # ccrma/webchuck-ide: en un pull_request el paso rsync tiene
        # `if: github.event_name == 'push'` y se omite, pero GitHub construye
        # antes la imagen de la acción («Build burnett01/rsync-deployments@…»).
        r = self.etiquetar("success", [job_yaml(1, "build", [
            ("Build burnett01/rsync-deployments@6.0.0", "success", {}),
            ("Run npm run build", "success", {"run": "npm run build"}),
            ("Deploy to dev", "skipped",
             {"uses": "burnett01/rsync-deployments@6.0.0"})])])
        self.assertEqual(r["etiqueta"], "excluida_sin_intento")
        self.assertFalse(r["despliegue_ejecutado"])

    def test_paso_build_no_convierte_en_ambiguo_un_fallo_previo(self):
        # Fallan las pruebas y el despliegue se omite; el «Build» de la
        # acción terminó bien pero no desplegó nada: es antes_del_despliegue.
        r = self.etiquetar("failure", [
            job_yaml(1, "test", [("Run tests", "failure", {"run": "npm test"})],
                     "failure"),
            job_yaml(2, "deploy", [
                ("Build digitalocean/app_action/deploy@v2", "success", {}),
                ("Deploy to DigitalOcean", "skipped",
                 {"uses": "digitalocean/app_action/deploy@v2"})],
                     inicio="2026-10-15T10:05")])
        self.assertEqual((r["etiqueta"], r["subtipo_etiqueta"]),
                         ("despliegue_no_completado", "antes_del_despliegue"))

    def test_despliegue_real_con_accion_docker_sigue_contando(self):
        r = self.etiquetar("success", [job_yaml(1, "deploy", [
            ("Build burnett01/rsync-deployments@9.0.2", "success", {}),
            ("Sync repo to remote VM", "success",
             {"uses": "burnett01/rsync-deployments@9.0.2"})])])
        self.assertEqual(r["etiqueta"], "despliegue_completado")

    def test_paso_pre_de_una_accion_omitida_no_es_despliegue(self):
        # GitHub ejecuta «Pre …» al empezar el job aunque el paso real se
        # omita con `if:`.
        r = self.etiquetar("success", [job_yaml(1, "deploy", [
            ("Pre Run aws-actions/amazon-ecs-deploy-task-definition@v2", "success", {}),
            ("Run aws-actions/amazon-ecs-deploy-task-definition@v2", "skipped",
             {"uses": "aws-actions/amazon-ecs-deploy-task-definition@v2"})])])
        self.assertEqual(r["etiqueta"], "excluida_sin_intento")
