from datetime import timedelta
from io import StringIO
from pathlib import Path
import shutil
import tempfile
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from riesgo.models import (AccesoRepositorio, DecisionDespliegue,
                           EjecucionWorkflow, Prediccion,
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
        self.assertEqual(r.json()["motivo"], "solo_anteriores")
        self.assertIsNone(Prediccion.objects.get(id=id_).ejecucion_real)

    def test_verificacion_pendiente_sin_ejecuciones_del_commit(self):
        id_ = self.predecir(self.dev).json()["id"]
        otro_commit = self.run_real(id_, 5, sha="d" * 40)
        cuerpo = self.verificar(self.dev, id_, [otro_commit], []).json()
        self.assertEqual(cuerpo["motivo"], "sin_ejecuciones")
        self.assertEqual(cuerpo["repositorio"], "acme/tienda")
        self.assertEqual(cuerpo["workflow_path"], ".github/workflows/deploy.yml")
        self.assertEqual(cuerpo["sha_corto"], SHA[:7])
        self.assertEqual(cuerpo["url_actions"],
                         "https://github.com/acme/tienda/actions/workflows/deploy.yml")

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
        # Otro desarrollador del mismo repositorio tampoco ve la predicción.
        self.assertEqual(self.verificar(self.dev2, id_, [], []).status_code, 404)
        self.assertIsNone(Prediccion.objects.get(id=id_).ejecucion_real)

    JOBS_EXITO = [{"id": 1, "name": "deploy", "conclusion": "success", "started_at": "x",
                   "steps": [{"number": 1, "name": "Deploy to ECS", "conclusion": "success"}]}]
    JOBS_FALLO = [{"id": 1, "name": "deploy", "conclusion": "failure", "started_at": "x",
                   "steps": [{"number": 1, "name": "Deploy to ECS", "conclusion": "failure"}]}]

    def test_verifica_ejecucion_exitosa(self):
        id_ = self.predecir(self.dev).json()["id"]
        r = self.verificar(self.dev, id_, [self.run_real(id_, 5, conclusion="success")], self.JOBS_EXITO)
        real = r.json()["ejecucion_real"]
        self.assertEqual((real["etiqueta"], real["y"]), ("despliegue_completado", 0))

    def test_ejecucion_en_curso_no_se_enlaza(self):
        id_ = self.predecir(self.dev).json()["id"]
        run = dict(self.run_real(id_, 5), status="in_progress", conclusion=None)
        r = self.verificar(self.dev, id_, [run], self.JOBS_FALLO)
        self.assertEqual(r.json()["estado"], "pendiente")
        self.assertEqual(r.json()["motivo"], "en_curso")
        self.assertIsNone(Prediccion.objects.get(id=id_).ejecucion_real)

    def test_verifica_el_reintento_de_la_ejecucion(self):
        id_ = self.predecir(self.dev).json()["id"]
        intentos = []

        class Reintento(ClienteFalso):
            RUNS_REALES = [dict(self.run_real(id_, 9, conclusion="success"), run_attempt=2)]

            def jobs_intento(self, repo, run_id, intento):
                intentos.append(intento)
                return ApiTest.JOBS_EXITO

        with mock.patch.object(github, "GitHubClient", Reintento):
            r = self.cliente(self.dev).post(f"/api/predicciones/{id_}/verificar/")
        real = r.json()["ejecucion_real"]
        self.assertEqual((real["run_attempt"], real["etiqueta"]), (2, "despliegue_completado"))
        # Se etiqueta con los jobs del intento enlazado, no del primero.
        self.assertEqual(intentos, [2])

    def test_supervision_cuenta_verificadas_evaluables_y_brier(self):
        exito, fallo, ambigua, pendiente = (self.predecir(self.dev).json()["id"] for _ in range(4))
        self.verificar(self.dev, exito, [self.run_real(exito, 5, conclusion="success", run_id=11)], self.JOBS_EXITO)
        self.verificar(self.dev, fallo, [self.run_real(fallo, 5, run_id=12)], self.JOBS_FALLO)
        jobs_ambigua = self.JOBS_EXITO + [{"id": 2, "name": "e2e", "conclusion": "failure", "started_at": "y",
                                           "steps": [{"number": 1, "name": "Tests", "conclusion": "failure"}]}]
        self.verificar(self.dev, ambigua, [self.run_real(ambigua, 5, conclusion="failure", run_id=13)], jobs_ambigua)
        modelo = Prediccion.objects.get(id=exito).version_modelo_id
        datos = self.cliente(self.admin).get(f"/api/modelos/{modelo}/supervision/").json()
        self.assertEqual((datos["predicciones"], datos["verificadas"], datos["evaluables"]), (4, 3, 2))
        p_exito = Prediccion.objects.get(id=exito)
        p_fallo = Prediccion.objects.get(id=fallo)
        esperado = ((p_exito.probabilidad - 0) ** 2 + (p_fallo.probabilidad - 1) ** 2) / 2
        self.assertAlmostEqual(datos["brier"], esperado)
        por_nivel = datos["por_nivel"]
        self.assertEqual(sum(n["evaluables"] for n in por_nivel.values()), 2)
        self.assertEqual(sum(n["no_completados"] for n in por_nivel.values()), 1)
        self.assertEqual(datos["predicciones_demostracion"], 0)
        # Al marcar el repositorio como demostración se informa por separado.
        Repositorio.objects.filter(id=self.repo.id).update(es_demostracion=True)
        datos = self.cliente(self.admin).get(f"/api/modelos/{modelo}/supervision/").json()
        self.assertEqual(datos["predicciones_demostracion"], 4)

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

    # --- Fecha límite y asignaciones -------------------------------------------

    def decidir(self, usuario, id_, **extra):
        datos = {"decision": "solicitar_revision", "comentario": "Revise el cambio"}
        datos.update(extra)
        return self.cliente(usuario).post(
            f"/api/predicciones/{id_}/decision/", datos, format="json")

    def test_lider_fija_fecha_limite_y_dev_la_recibe(self):
        id_ = self.predecir(self.dev).json()["id"]
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        r = self.decidir(self.lider, id_, fecha_limite=manana)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["decisiones"][0]["fecha_limite"], manana)
        lista = self.cliente(self.dev).get("/api/asignaciones/").json()
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["mensaje"], "Revise el cambio")
        self.assertEqual(lista[0]["estado"], "por_vencer")
        self.assertFalse(lista[0]["vista"])
        # Otro desarrollador del mismo repositorio no la recibe.
        self.assertEqual(self.cliente(self.dev2).get("/api/asignaciones/").json(), [])

    def test_fecha_limite_pasada_rechazada(self):
        id_ = self.predecir(self.dev).json()["id"]
        ayer = (timezone.localdate() - timedelta(days=1)).isoformat()
        self.assertEqual(self.decidir(self.lider, id_, fecha_limite=ayer).status_code, 400)
        self.decidir(self.lider, id_)
        r = self.cliente(self.lider).post(
            f"/api/predicciones/{id_}/fecha-limite/", {"fecha_limite": ayer}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_permisos_de_la_fecha_limite(self):
        id_ = self.predecir(self.dev).json()["id"]
        hoy = timezone.localdate().isoformat()
        url = f"/api/predicciones/{id_}/fecha-limite/"
        # Sin decisión previa no se puede fijar la fecha.
        r = self.cliente(self.lider).post(url, {"fecha_limite": hoy}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "sin_decision")
        self.decidir(self.lider, id_)
        # El desarrollador no puede fijarla, ni al decidir ni después.
        self.assertEqual(self.decidir(self.dev, id_, fecha_limite=hoy).status_code, 403)
        self.assertEqual(self.cliente(self.dev).post(url, {"fecha_limite": hoy}, format="json").status_code, 403)
        # Un líder de otro repositorio no ve la predicción.
        self.assertEqual(self.cliente(self.lider_ajeno).post(url, {"fecha_limite": hoy}, format="json").status_code, 404)
        self.assertEqual(self.decidir(self.lider_ajeno, id_, fecha_limite=hoy).status_code, 404)
        # El líder del repositorio y el administrador sí.
        self.assertEqual(self.cliente(self.lider).post(url, {"fecha_limite": hoy}, format="json").status_code, 200)
        self.assertEqual(self.cliente(self.admin).post(url, {"fecha_limite": hoy}, format="json").status_code, 200)

    def test_solo_el_dueno_marca_vista_y_cumplida(self):
        id_ = self.predecir(self.dev).json()["id"]
        hoy = timezone.localdate().isoformat()
        self.decidir(self.lider, id_, fecha_limite=hoy)
        asignacion = self.cliente(self.dev).get("/api/asignaciones/").json()[0]
        base = f"/api/asignaciones/{asignacion['id']}"
        for usuario in (self.lider, self.admin):
            self.assertEqual(self.cliente(usuario).post(f"{base}/cumplida/").status_code, 403)
        self.assertEqual(self.cliente(self.dev2).post(f"{base}/vista/").status_code, 404)
        r = self.cliente(self.dev).post(f"{base}/vista/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["vista"])
        r = self.cliente(self.dev).post(f"{base}/cumplida/")
        self.assertEqual(r.json()["estado"], "cumplida")
        # El líder ve el cambio en el historial del equipo.
        decision = self.cliente(self.lider).get(f"/api/predicciones/{id_}/").json()["decisiones"][0]
        self.assertIsNotNone(decision["vista_por_desarrollador_en"])
        self.assertIsNotNone(decision["cumplida_en"])

    def test_cambiar_fecha_limite_reinicia_vista(self):
        id_ = self.predecir(self.dev).json()["id"]
        hoy = timezone.localdate()
        self.decidir(self.lider, id_, fecha_limite=hoy.isoformat())
        asignacion = self.cliente(self.dev).get("/api/asignaciones/").json()[0]
        self.cliente(self.dev).post(f"/api/asignaciones/{asignacion['id']}/vista/")
        nueva = (hoy + timedelta(days=5)).isoformat()
        self.cliente(self.lider).post(
            f"/api/predicciones/{id_}/fecha-limite/", {"fecha_limite": nueva}, format="json")
        asignacion = self.cliente(self.dev).get("/api/asignaciones/").json()[0]
        self.assertEqual(asignacion["fecha_limite"], nueva)
        self.assertEqual(asignacion["estado"], "pendiente")
        self.assertFalse(asignacion["vista"])

    def test_asignacion_usa_la_ultima_decision(self):
        id_ = self.predecir(self.dev).json()["id"]
        self.decidir(self.lider, id_, fecha_limite=timezone.localdate().isoformat())
        self.decidir(self.lider, id_, decision="solicitar_revision")
        # La última decisión no tiene fecha límite: ya no hay asignación.
        self.assertEqual(self.cliente(self.dev).get("/api/asignaciones/").json(), [])
        # Una autorización sí llega, sin fecha, y se cierra con "Entendido".
        self.decidir(self.lider, id_, decision="autorizar")
        lista = self.cliente(self.dev).get("/api/asignaciones/").json()
        self.assertEqual([(a["decision"], a["estado"], a["fecha_limite"]) for a in lista],
                         [("autorizar", "pendiente", None)])
        r = self.cliente(self.dev).post(f"/api/asignaciones/{lista[0]['id']}/entendida/")
        self.assertEqual(r.json()["estado"], "cumplida")

    def test_estado_de_la_asignacion(self):
        from riesgo.services.asignaciones import estado

        hoy = timezone.localdate()
        decision = DecisionDespliegue(fecha_limite=hoy + timedelta(days=3))
        self.assertEqual(estado(decision, hoy), "pendiente")
        decision.fecha_limite = hoy + timedelta(days=1)
        self.assertEqual(estado(decision, hoy), "por_vencer")
        decision.fecha_limite = hoy
        self.assertEqual(estado(decision, hoy), "por_vencer")
        decision.fecha_limite = hoy - timedelta(days=1)
        self.assertEqual(estado(decision, hoy), "vencida")
        decision.cumplida_en = timezone.now()
        self.assertEqual(estado(decision, hoy), "cumplida")

    # --- Repositorios ?todos=1 y resumen del administrador ---------------------

    def test_repositorios_todos_por_rol(self):
        sin_workflows = Repositorio.objects.create(
            nombre_completo="acme/vacio", propietario="acme", nombre="vacio")
        AccesoRepositorio.objects.create(usuario=self.dev, repositorio=sin_workflows)
        nombres = lambda r: sorted(x["nombre_completo"] for x in r.json())
        # Por defecto se ocultan los repositorios sin workflows utilizables.
        self.assertEqual(nombres(self.cliente(self.dev).get("/api/repositorios/")), ["acme/tienda"])
        r = self.cliente(self.dev).get("/api/repositorios/?todos=1")
        self.assertEqual(nombres(r), ["acme/tienda", "acme/vacio"])
        validados = {x["nombre_completo"]: x["workflows_validados"] for x in r.json()}
        self.assertEqual(validados, {"acme/tienda": 1, "acme/vacio": 0})
        self.assertEqual(nombres(self.cliente(self.lider).get("/api/repositorios/?todos=1")), ["acme/tienda"])
        self.assertEqual(nombres(self.cliente(self.admin).get("/api/repositorios/?todos=1")),
                         ["acme/ajeno", "acme/tienda", "acme/vacio"])
        self.assertEqual(self.cliente(self.sin_rol).get("/api/repositorios/?todos=1").status_code, 403)

    def test_resumen_admin(self):
        for usuario in (self.dev, self.lider):
            self.assertEqual(self.cliente(usuario).get("/api/resumen-admin/").status_code, 403)
        # Un usuario con dos roles cuenta una vez, en el de mayor jerarquía.
        self.dev2.groups.add(Group.objects.get(name="lider_tecnico"))
        User.objects.create_superuser("raiz", password="x")
        r = self.cliente(self.admin).get("/api/resumen-admin/")
        self.assertEqual(r.status_code, 200)
        usuarios = r.json()["usuarios"]
        self.assertEqual(usuarios, {"administrador": 2, "lider_tecnico": 3, "desarrollador": 1,
                                    "sin_rol": 1, "total": User.objects.count()})
        self.assertEqual(r.json()["workflows"], {"total": 3, "validados": 2, "sin_validar": 1,
                                                 "validados_disponibles_github": 2})

    # --- Comando crear_usuario -------------------------------------------------

    def test_comando_crear_usuario_repetible(self):
        call_command("crear_usuario", "nuevo_dev", rol="desarrollador", password="clave-1",
                     repos=["acme/tienda", "acme/ajeno"], stdout=StringIO())
        call_command("crear_usuario", "nuevo_dev", rol="desarrollador",
                     repos=["acme/tienda"], stdout=StringIO())
        usuario = User.objects.get(username="nuevo_dev")
        self.assertEqual(User.objects.filter(username="nuevo_dev").count(), 1)
        self.assertTrue(usuario.check_password("clave-1"))
        self.assertEqual(list(usuario.groups.values_list("name", flat=True)), ["desarrollador"])
        self.assertEqual(list(usuario.accesos.values_list("repositorio__nombre_completo", flat=True)),
                         ["acme/tienda"])
        self.assertFalse(usuario.is_superuser)
        call_command("crear_usuario", "nuevo_admin", rol="administrador", password="clave-2",
                     stdout=StringIO())
        admin = User.objects.get(username="nuevo_admin")
        self.assertTrue(admin.is_superuser and admin.is_staff)
        with self.assertRaises(CommandError):
            call_command("crear_usuario", "otro", rol="desarrollador", password="x",
                         repos=["acme/no-existe"], stdout=StringIO())
        self.assertFalse(User.objects.filter(username="otro").exists())

    # --- Respuesta del desarrollador con un nuevo análisis --------------------

    def asignar(self, id_, decision="posponer"):
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.decidir(self.lider, id_, decision=decision, fecha_limite=manana)
        return DecisionDespliegue.objects.filter(prediccion_id=id_).latest("creada_en")

    def test_nuevo_analisis_atiende_la_asignacion(self):
        original = self.predecir(self.dev).json()
        decision = self.asignar(original["id"])
        r = self.predecir(self.dev, dict(DATOS, atiende_decision=decision.id,
                                         respuesta_desarrollador="Actualicé las dependencias"))
        self.assertEqual(r.status_code, 201, r.content)
        decision.refresh_from_db()
        self.assertEqual(decision.prediccion_respuesta_id, r.json()["id"])
        self.assertEqual(decision.respuesta_desarrollador, "Actualicé las dependencias")
        self.assertIsNotNone(decision.cumplida_en)
        self.assertIsNotNone(decision.vista_por_desarrollador_en)
        # decision y comentario no cambian.
        self.assertEqual((decision.decision, decision.comentario), ("posponer", "Revise el cambio"))
        # El líder ve la respuesta: nuevo análisis, su nivel y el comentario.
        vista = self.cliente(self.lider).get(f"/api/predicciones/{original['id']}/").json()["decisiones"][0]
        self.assertEqual(vista["prediccion_respuesta"]["id"], r.json()["id"])
        self.assertEqual(vista["prediccion_respuesta"]["nivel"], r.json()["nivel"])
        self.assertEqual(vista["respuesta_desarrollador"], "Actualicé las dependencias")
        asignacion = self.cliente(self.lider).get("/api/asignaciones/").json()[0]
        self.assertEqual(asignacion["estado"], "cumplida")
        self.assertEqual(asignacion["nivel_original"], original["nivel"])

    def test_respuesta_no_se_atiende_dos_veces(self):
        decision = self.asignar(self.predecir(self.dev).json()["id"])
        self.assertEqual(self.predecir(self.dev, dict(DATOS, atiende_decision=decision.id)).status_code, 201)
        r = self.predecir(self.dev, dict(DATOS, atiende_decision=decision.id))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "asignacion_ya_atendida")

    def test_respuesta_permisos_y_validaciones(self):
        decision = self.asignar(self.predecir(self.dev).json()["id"])
        # Otro desarrollador del mismo repositorio no puede atenderla.
        r = self.predecir(self.dev2, dict(DATOS, atiende_decision=decision.id))
        self.assertEqual((r.status_code, r.json()["codigo"]), (400, "asignacion_no_encontrada"))
        # Una decisión inexistente.
        r = self.predecir(self.dev, dict(DATOS, atiende_decision=999999))
        self.assertEqual(r.json()["codigo"], "asignacion_no_encontrada")
        # Otro workflow del mismo repositorio.
        Workflow.objects.create(repositorio=self.repo, path=".github/workflows/deploy2.yml",
                                despliegue_validado=True, evidencia_validacion="prueba")
        r = self.predecir(self.dev, dict(DATOS, workflow_path=".github/workflows/deploy2.yml",
                                         atiende_decision=decision.id))
        self.assertEqual(r.json()["codigo"], "asignacion_otro_workflow")
        # Sin crear predicciones con una respuesta rechazada.
        decision.refresh_from_db()
        self.assertIsNone(decision.prediccion_respuesta_id)

    def test_autorizacion_no_se_atiende_con_analisis(self):
        decision = self.asignar(self.predecir(self.dev).json()["id"], decision="autorizar")
        r = self.predecir(self.dev, dict(DATOS, atiende_decision=decision.id))
        self.assertEqual(r.json()["codigo"], "asignacion_no_atendible")
        # "Entendido" solo para autorizaciones.
        otra = self.asignar(self.predecir(self.dev).json()["id"], decision="posponer")
        r = self.cliente(self.dev).post(f"/api/asignaciones/{otra.id}/entendida/")
        self.assertEqual(r.json()["codigo"], "no_es_autorizacion")

    def test_decision_no_vigente_no_se_atiende(self):
        id_ = self.predecir(self.dev).json()["id"]
        anterior = self.asignar(id_)
        self.asignar(id_, decision="solicitar_revision")
        r = self.predecir(self.dev, dict(DATOS, atiende_decision=anterior.id))
        self.assertEqual(r.json()["codigo"], "asignacion_no_vigente")
