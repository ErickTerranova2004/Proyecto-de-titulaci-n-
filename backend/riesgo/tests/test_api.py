from datetime import timedelta
from io import StringIO
from pathlib import Path
import shutil
import tempfile
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from riesgo.models import (AccesoRepositorio, EjecucionWorkflow, Prediccion,
                           Repositorio, Workflow)
from riesgo.services import github

SHA = "a" * 40
COMMIT = {"sha": SHA, "commit": {
    "message": "fix: corrige configuración",
    "author": {"name": "dev"},
    "committer": {"date": "2026-10-15T09:00:00Z"}},
    "stats": {"additions": 12, "deletions": 3, "total": 15},
    "files": [{"filename": "a.py"}, {"filename": "b.py"}]}
RUNS = [{"id": 100 + i, "run_attempt": 1, "status": "completed",
         "conclusion": c, "workflow_id": 7, "head_sha": "c" * 40,
         "event": "push", "head_branch": "main",
         "run_started_at": f"2026-10-1{i}T08:00:00Z",
         "updated_at": f"2026-10-1{i}T08:05:00Z"}
        for i, c in enumerate(["success", "failure", "failure"])]
DATOS = {"repositorio": "acme/tienda",
         "workflow_path": ".github/workflows/deploy.yml",
         "head_sha": SHA, "rama": "main", "evento": "push"}


def iso(momento):
    return momento.strftime("%Y-%m-%dT%H:%M:%SZ")


class ClienteFalso:
    """Simula la API de GitHub. RUNS_REALES y JOBS se fijan por prueba."""

    RUNS_REALES = []
    JOBS = []

    def repositorio(self, repo):
        raise github.NoEncontrado(repo)

    def commit(self, repo, sha):
        return COMMIT

    def ultimo_commit(self, repo, rama):
        return COMMIT

    def ejecuciones_workflow(self, repo, path, n=20, head_sha=None):
        return self.RUNS_REALES if head_sha else RUNS

    def ejecuciones_repositorio(self, repo, n=100):
        return RUNS

    def jobs_intento(self, repo, run_id, intento):
        return self.JOBS

    def limite(self):
        return {"limit": 5000, "remaining": 4990, "reset": 1}


class ClienteNoEncontrado(ClienteFalso):
    def commit(self, repo, sha):
        raise github.NoEncontrado(repo)


class ApiTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("registrar_modelo", stdout=StringIO())
        cls.repo = Repositorio.objects.create(
            nombre_completo="acme/tienda", propietario="acme", nombre="tienda")
        cls.repo_ajeno = Repositorio.objects.create(
            nombre_completo="acme/ajeno", propietario="acme", nombre="ajeno")
        for repo in (cls.repo, cls.repo_ajeno):
            Workflow.objects.create(
                repositorio=repo, path=".github/workflows/deploy.yml",
                despliegue_validado=True, evidencia_validacion="prueba")
        Workflow.objects.create(repositorio=cls.repo,
                                path=".github/workflows/ci.yml")
        cls.dev = cls._usuario("dev", "desarrollador", [cls.repo])
        cls.dev2 = cls._usuario("dev2", "desarrollador", [cls.repo])
        cls.lider = cls._usuario("lider", "lider_tecnico", [cls.repo])
        cls.lider_ajeno = cls._usuario("lider_ajeno", "lider_tecnico",
                                       [cls.repo_ajeno])
        cls.admin = cls._usuario("admin", "administrador", [])
        cls.sin_rol = User.objects.create_user("visitante", password="x")

    @staticmethod
    def _usuario(nombre, rol, repos):
        usuario = User.objects.create_user(nombre, password="x")
        usuario.groups.add(Group.objects.get(name=rol))
        for repo in repos:
            AccesoRepositorio.objects.create(usuario=usuario, repositorio=repo)
        return usuario

    def cliente(self, usuario):
        api = APIClient()
        api.force_authenticate(usuario)
        return api

    def predecir(self, usuario, datos=DATOS, falso=ClienteFalso):
        with mock.patch.object(github, "GitHubClient", falso):
            return self.cliente(usuario).post("/api/predicciones/", datos,
                                              format="json")

    def verificar(self, usuario, prediccion_id, runs, jobs):
        falso = type("Falso", (ClienteFalso,),
                     {"RUNS_REALES": runs, "JOBS": jobs})
        with mock.patch.object(github, "GitHubClient", falso):
            return self.cliente(usuario).post(
                f"/api/predicciones/{prediccion_id}/verificar/")

    # --- Creación y trazabilidad -------------------------------------------

    def test_crea_prediccion_con_trazabilidad(self):
        r = self.predecir(self.dev)
        self.assertEqual(r.status_code, 201, r.content)
        cuerpo = r.json()
        self.assertIn(cuerpo["nivel"], ["bajo", "medio", "alto"])
        self.assertEqual(cuerpo["version_modelo"], "v1.1")
        self.assertEqual(cuerpo["repositorio"], "acme/tienda")
        self.assertEqual(cuerpo["head_sha"], SHA)
        self.assertEqual(len(cuerpo["ejecuciones_previas"]), 3)
        self.assertIsNone(cuerpo["ejecucion_real"])
        self.assertTrue(all(r["codigo"] for r in cuerpo["recomendaciones"]))
        prediccion = Prediccion.objects.get()
        self.assertEqual(prediccion.commit.repositorio, self.repo)
        self.assertEqual(prediccion.commit.mensaje_resumen,
                         "fix: corrige configuración")
        self.assertNotEqual(prediccion.commit.autor_hash, "dev")
        # Métricas del cambio de código recopiladas desde GitHub.
        self.assertEqual(cuerpo["cambio"], {"archivos_modificados": 2,
                                            "adiciones": 12,
                                            "eliminaciones": 3})

    def test_rechaza_workflow_no_validado(self):
        for ruta in (".github/workflows/ci.yml",
                     ".github/workflows/inexistente.yml"):
            r = self.predecir(self.dev, dict(DATOS, workflow_path=ruta))
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.json()["codigo"], "workflow_no_validado")
            self.assertIn("no está validado", r.json()["detail"])
        self.assertEqual(Prediccion.objects.count(), 0)

    def test_rechaza_repositorio_no_registrado(self):
        r = self.predecir(self.admin, dict(DATOS, repositorio="acme/nuevo"))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["codigo"], "repositorio_no_registrado")

    def test_requiere_autenticacion(self):
        r = APIClient().post("/api/predicciones/", DATOS, format="json")
        self.assertEqual(r.status_code, 401)

    def test_requiere_rol(self):
        self.assertEqual(self.predecir(self.sin_rol).status_code, 403)

    def test_valida_entradas(self):
        for campo, valor in [("repositorio", "../etc/passwd"),
                             ("workflow_path", "deploy.sh"),
                             ("head_sha", "zzz")]:
            r = self.predecir(self.dev, dict(DATOS, **{campo: valor}))
            self.assertEqual(r.status_code, 400, campo)

    def test_commit_no_encontrado_en_github(self):
        r = self.predecir(self.dev, falso=ClienteNoEncontrado)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Prediccion.objects.count(), 0)

    def test_rama_inexistente_indica_la_rama_principal(self):
        class SinRama(ClienteFalso):
            def ultimo_commit(self, repo, rama):
                raise github.RamaNoEncontrada(rama, "master")

        r = self.predecir(self.dev, dict(DATOS, head_sha="", rama="main"),
                          falso=SinRama)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "rama_no_encontrada")
        self.assertIn("master", r.json()["detail"])
        self.assertEqual(Prediccion.objects.count(), 0)

    def test_cliente_github_detecta_rama_inexistente(self):
        def respuesta(estado, datos=None):
            return mock.Mock(status_code=estado, headers={},
                             json=mock.Mock(return_value=datos or {}))

        sesion = mock.Mock()
        sesion.get.side_effect = [respuesta(422),
                                  respuesta(200, {"default_branch": "master"})]
        cliente = github.GitHubClient(token="", base_url="https://gh",
                                      sesion=sesion)
        with self.assertRaises(github.RamaNoEncontrada) as ctx:
            cliente.ultimo_commit("acme/inexistente-rama", "main")
        self.assertEqual(ctx.exception.principal, "master")

    # --- Acceso por repositorio ---------------------------------------------

    def test_sin_acceso_no_puede_predecir(self):
        r = self.predecir(self.dev, dict(DATOS, repositorio="acme/ajeno"))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["codigo"], "sin_acceso")

    def test_admin_predice_en_cualquier_repositorio(self):
        r = self.predecir(self.admin, dict(DATOS, repositorio="acme/ajeno"))
        self.assertEqual(r.status_code, 201)

    def test_repositorios_visibles_por_acceso(self):
        def nombres(usuario):
            return {r["nombre_completo"] for r in
                    self.cliente(usuario).get("/api/repositorios/").json()}
        self.assertEqual(nombres(self.dev), {"acme/tienda"})
        self.assertEqual(nombres(self.lider_ajeno), {"acme/ajeno"})
        self.assertEqual(nombres(self.admin), {"acme/tienda", "acme/ajeno"})
        workflows = self.cliente(self.dev).get("/api/repositorios/").json()[0][
            "workflows"]
        self.assertEqual([w["path"] for w in workflows],
                         [".github/workflows/deploy.yml"])

    def test_visibilidad_de_predicciones_por_acceso_y_rol(self):
        self.predecir(self.dev)
        self.predecir(self.dev2)
        self.predecir(self.admin, dict(DATOS, repositorio="acme/ajeno"))

        def total(usuario):
            return len(self.cliente(usuario).get("/api/predicciones/").json())
        self.assertEqual(total(self.dev), 1)          # propias en su repo
        self.assertEqual(total(self.lider), 2)        # todas de acme/tienda
        self.assertEqual(total(self.lider_ajeno), 1)  # solo acme/ajeno
        self.assertEqual(total(self.admin), 3)        # todo

    def test_detalle_sin_acceso_devuelve_404(self):
        id_ = self.predecir(self.dev).json()["id"]
        r = self.cliente(self.lider_ajeno).get(f"/api/predicciones/{id_}/")
        self.assertEqual(r.status_code, 404)

    def test_quitar_acceso_oculta_predicciones(self):
        self.predecir(self.dev)
        AccesoRepositorio.objects.filter(usuario=self.dev).delete()
        self.assertEqual(
            self.cliente(self.dev).get("/api/predicciones/").json(), [])

    # --- Verificación con la ejecución real ---------------------------------

    def run_real(self, prediccion, minutos, sha=SHA, conclusion="failure",
                 run_id=900, path=".github/workflows/deploy.yml"):
        inicio = Prediccion.objects.get(id=prediccion).creada_en + timedelta(
            minutes=minutos)
        return {"id": run_id, "run_attempt": 1, "status": "completed",
                "conclusion": conclusion, "head_sha": sha, "path": path,
                "event": "push", "head_branch": "main",
                "run_started_at": iso(inicio),
                "updated_at": iso(inicio + timedelta(minutes=3))}

    def test_verifica_con_ejecucion_posterior_del_mismo_workflow_y_commit(self):
        id_ = self.predecir(self.dev).json()["id"]
        runs = [
            self.run_real(id_, -10, run_id=1),                 # anterior
            self.run_real(id_, 5, sha="d" * 40, run_id=2),     # otro commit
            self.run_real(id_, 6, run_id=3,
                          path=".github/workflows/otro.yml"),  # otro workflow
            self.run_real(id_, 8, run_id=4),                   # válida
        ]
        jobs = [{"id": 1, "name": "deploy", "conclusion": "failure",
                 "started_at": "x", "steps": [
                     {"number": 1, "name": "Build", "conclusion": "success"},
                     {"number": 2, "name": "Deploy to ECS",
                      "conclusion": "failure"}]}]
        r = self.verificar(self.dev, id_, runs, jobs)
        self.assertEqual(r.status_code, 200, r.content)
        real = r.json()["ejecucion_real"]
        self.assertEqual(real["run_id"], 4)
        self.assertEqual(real["etiqueta"], "despliegue_no_completado")
        self.assertEqual(real["subtipo_etiqueta"], "en_paso_de_despliegue")
        self.assertEqual(real["paso_fallido"], "deploy / Deploy to ECS")
        self.assertEqual(real["y"], 1)

    def test_verificacion_pendiente_si_no_hay_ejecucion_posterior(self):
        id_ = self.predecir(self.dev).json()["id"]
        r = self.verificar(self.dev, id_, [self.run_real(id_, -10)], [])
        self.assertEqual(r.json()["estado"], "pendiente")
        self.assertIsNone(Prediccion.objects.get(id=id_).ejecucion_real)

    def test_verificacion_ambigua_no_se_etiqueta_como_fallo(self):
        id_ = self.predecir(self.dev).json()["id"]
        jobs = [{"id": 1, "name": "deploy", "conclusion": "success",
                 "started_at": "1", "steps": [{"number": 1,
                                               "name": "Deploy to ECS",
                                               "conclusion": "success"}]},
                {"id": 2, "name": "e2e", "conclusion": "failure",
                 "started_at": "2", "steps": [{"number": 1, "name": "Tests",
                                               "conclusion": "failure"}]}]
        r = self.verificar(self.dev, id_, [self.run_real(id_, 5)], jobs)
        real = r.json()["ejecucion_real"]
        self.assertEqual(real["etiqueta"], "excluida_ambigua")
        self.assertIsNone(real["y"])

    def test_no_puede_verificar_prediccion_sin_acceso(self):
        id_ = self.predecir(self.dev).json()["id"]
        r = self.verificar(self.lider_ajeno, id_, [], [])
        self.assertEqual(r.status_code, 404)

    # --- Modelos ------------------------------------------------------------

    def test_solo_admin_activa_modelos(self):
        modelo_id = self.cliente(self.dev).get("/api/modelos/").json()[0]["id"]
        url = f"/api/modelos/{modelo_id}/activar/"
        self.assertEqual(self.cliente(self.dev).post(url).status_code, 403)
        self.assertEqual(self.cliente(self.admin).post(url).status_code, 200)

    def test_supervision_compara_con_resultados_reales(self):
        id_ = self.predecir(self.dev).json()["id"]
        jobs = [{"id": 1, "name": "deploy", "conclusion": "failure",
                 "started_at": "x", "steps": [
                     {"number": 1, "name": "Deploy to ECS",
                      "conclusion": "failure"}]}]
        self.verificar(self.dev, id_, [self.run_real(id_, 5)], jobs)
        modelo = Prediccion.objects.get(id=id_).version_modelo_id
        url = f"/api/modelos/{modelo}/supervision/"
        self.assertEqual(self.cliente(self.dev).get(url).status_code, 403)
        datos = self.cliente(self.admin).get(url).json()
        self.assertEqual(datos["evaluables"], 1)
        nivel = Prediccion.objects.get(id=id_).nivel
        self.assertEqual(datos["por_nivel"][nivel]["no_completados"], 1)
        self.assertIsNotNone(datos["brier"])

    # --- Decisión del líder técnico ------------------------------------------

    def test_lider_registra_decision(self):
        id_ = self.predecir(self.dev).json()["id"]
        url = f"/api/predicciones/{id_}/decision/"
        r = self.cliente(self.lider).post(
            url, {"decision": "solicitar_revision", "comentario": "Revisar"},
            format="json")
        self.assertEqual(r.status_code, 201, r.content)
        decision = r.json()["decisiones"][0]
        self.assertEqual(decision["decision"], "solicitar_revision")
        self.assertEqual(decision["usuario"], "lider")
        # El desarrollador ve la decisión en el historial.
        detalle = self.cliente(self.dev).get(f"/api/predicciones/{id_}/")
        self.assertEqual(len(detalle.json()["decisiones"]), 1)

    def test_decision_permisos_y_validacion(self):
        id_ = self.predecir(self.dev).json()["id"]
        url = f"/api/predicciones/{id_}/decision/"
        cuerpo = {"decision": "autorizar"}
        self.assertEqual(self.cliente(self.dev).post(
            url, cuerpo, format="json").status_code, 403)
        self.assertEqual(self.cliente(self.lider_ajeno).post(
            url, cuerpo, format="json").status_code, 404)
        self.assertEqual(self.cliente(self.lider).post(
            url, {"decision": "desplegar_ya"}, format="json").status_code, 400)

    # --- Integración con GitHub (administrador) ------------------------------

    def test_integraciones_solo_admin_y_sin_revelar_token(self):
        with mock.patch.object(github, "GitHubClient", ClienteFalso), \
                self.settings(GITHUB_TOKEN="ghp_" + "x" * 36):
            self.assertEqual(self.cliente(self.lider).get(
                "/api/integraciones/").status_code, 403)
            r = self.cliente(self.admin).get("/api/integraciones/")
        self.assertEqual(r.status_code, 200)
        datos = r.json()["github"]
        self.assertTrue(datos["token_configurado"])
        self.assertEqual(datos["restantes"], 4990)
        self.assertNotIn("x" * 36, r.content.decode())

    def test_sincronizar_guarda_ejecuciones(self):
        url = f"/api/repositorios/{self.repo.id}/sincronizar/"
        with mock.patch.object(github, "GitHubClient", ClienteFalso):
            self.assertEqual(self.cliente(self.lider).post(url).status_code,
                             403)
            r = self.cliente(self.admin).post(url)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["ejecuciones_guardadas"], len(RUNS))
        self.assertEqual(
            EjecucionWorkflow.objects.filter(
                workflow__repositorio=self.repo).count(), len(RUNS))

    def test_workflow_eliminado_en_github_se_retira(self):
        class SinArchivo(ClienteFalso):
            def ejecuciones_workflow(self, repo, path, n=20, head_sha=None):
                raise github.NoEncontrado(
                    f"/repos/{repo}/actions/workflows/deploy.yml/runs")

        r = self.predecir(self.dev, falso=SinArchivo)
        self.assertEqual(r.status_code, 404)
        self.assertIn("ya no existe", r.json()["detail"])
        workflow = Workflow.objects.get(repositorio=self.repo,
                                        path=DATOS["workflow_path"])
        self.assertFalse(workflow.disponible_github)
        # Ya no se ofrece ni admite nuevos análisis; el registro se conserva.
        r = self.predecir(self.dev)
        self.assertEqual(r.json()["codigo"], "workflow_no_disponible")
        self.assertEqual(self.cliente(self.dev).get("/api/repositorios/")
                         .json(), [])

    def test_comando_verifica_workflows_en_github(self):
        respuestas = {"acme/tienda": 404, "acme/ajeno": 200}

        def head(sesion, url, **kwargs):
            repo = url.split("githubusercontent.com/")[1].rsplit("/HEAD/")[0]
            return mock.Mock(status_code=respuestas[repo])

        with mock.patch("requests.Session.head", head):
            call_command("verificar_workflows_github", salida=str(
                Path(self.directorio_temporal()) / "no_disponibles.csv"),
                stdout=StringIO())
        disponibles = dict(Workflow.objects.filter(
            despliegue_validado=True).values_list(
            "repositorio__nombre_completo", "disponible_github"))
        self.assertEqual(disponibles, {"acme/tienda": False,
                                       "acme/ajeno": True})

    # --- Alta manual de workflows (administrador) ---------------------------

    EVIDENCIA = "Despliega la API a Heroku en el paso 'Deploy to production'."

    def registrar(self, usuario, datos, falso=None):
        class RepoNuevo(ClienteFalso):
            def repositorio(self, repo):
                return {"id": 99, "full_name": "acme/nuevo"}

            def workflow(self, repo, path):
                return {"name": "Deploy"}

        with mock.patch.object(github, "GitHubClient", falso or RepoNuevo):
            return self.cliente(usuario).post("/api/repositorios/registrar/",
                                              datos, format="json")

    def test_admin_registra_workflow_validado(self):
        r = self.registrar(self.admin, {
            "repositorio": "acme/nuevo",
            "workflow_path": ".github/workflows/deploy.yml",
            "evidencia": self.EVIDENCIA})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["ejecuciones_recientes"], len(RUNS))
        workflow = Workflow.objects.get(repositorio__nombre_completo="acme/nuevo")
        self.assertTrue(workflow.despliegue_validado)
        self.assertEqual(workflow.evidencia_validacion, self.EVIDENCIA)
        self.assertEqual(workflow.validado_por, self.admin)
        self.assertEqual(workflow.repositorio.github_id, 99)
        repos = self.cliente(self.admin).get("/api/repositorios/").json()
        self.assertIn("acme/nuevo", [x["nombre_completo"] for x in repos])
        # Registrarlo otra vez no duplica ni sobrescribe la evidencia.
        r = self.registrar(self.admin, {
            "repositorio": "acme/nuevo",
            "workflow_path": ".github/workflows/deploy.yml",
            "evidencia": self.EVIDENCIA + " Segunda vez."})
        self.assertEqual(r.status_code, 409)

    def test_registro_solo_admin_y_con_evidencia(self):
        datos = {"repositorio": "acme/nuevo",
                 "workflow_path": ".github/workflows/deploy.yml",
                 "evidencia": self.EVIDENCIA}
        self.assertEqual(self.registrar(self.lider, datos).status_code, 403)
        r = self.registrar(self.admin, dict(datos, evidencia="despliega"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("evidencia", r.json())
        self.assertFalse(Repositorio.objects.filter(
            nombre_completo="acme/nuevo").exists())

    def test_registro_rechaza_workflow_inexistente(self):
        class SinWorkflow(ClienteFalso):
            def repositorio(self, repo):
                return {"id": 99, "full_name": "acme/nuevo"}

            def workflow(self, repo, path):
                raise github.NoEncontrado(path)

        r = self.registrar(self.admin, {
            "repositorio": "acme/nuevo",
            "workflow_path": ".github/workflows/deploy.yml",
            "evidencia": self.EVIDENCIA}, falso=SinWorkflow)
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Repositorio.objects.filter(
            nombre_completo="acme/nuevo").exists())

    def directorio_temporal(self):
        directorio = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directorio, ignore_errors=True)
        return directorio
