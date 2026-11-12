"""Commits pendientes de desplegar y aviso de commit ya desplegado."""

from unittest import mock

from django.test import TestCase, override_settings

from riesgo.models import PendienteDespliegue, Prediccion, Repositorio, Workflow
from riesgo.services import github
from riesgo.services.pendientes import (actualizar_pendientes,
                                        siguiente_version)
from riesgo.tests import test_api

DESPLEGADO = "d" * 40
CABEZA = "c" * 40


class GitHubPendientes:
    """API mínima: despliegues correctos del workflow, cabeza de la rama y
    comparación; responde 304 si el ETag coincide con el contenido."""

    def __init__(self):
        self.despliegues = [
            {"id": 9, "event": "pull_request", "head_sha": "e" * 40,
             "head_branch": "feature", "run_started_at": "2026-11-10T10:00:00Z"},
            {"id": 8, "event": "release", "head_sha": DESPLEGADO,
             "head_branch": "v1.5.3", "run_started_at": "2026-10-30T14:52:13Z"},
        ]
        self.cabeza = CABEZA
        self.llamadas = []

    def get(self, ruta, params=None):
        self.llamadas.append(ruta)
        if "/compare/" in ruta:
            return {"status": "ahead", "ahead_by": 4}
        return {"default_branch": "main"}

    def get_condicional(self, ruta, params=None, etag=""):
        self.llamadas.append(ruta)
        if ruta.endswith("/git/ref/heads/main"):
            datos = {"object": {"sha": self.cabeza}}
        else:
            datos = {"workflow_runs": self.despliegues}
        actual = str(hash(repr(datos)))
        return (None, etag) if etag == actual else (datos, actual)


class PendientesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        repo = Repositorio.objects.create(
            nombre_completo="suffolk/efile", propietario="suffolk", nombre="efile")
        cls.workflow = Workflow.objects.create(
            repositorio=repo, path=".github/workflows/fly-prod-release.yml",
            despliegue_validado=True, evidencia_validacion="prueba")

    def test_siguiente_version(self):
        self.assertEqual(siguiente_version("v1.5.3"), "v1.5.4")
        self.assertEqual(siguiente_version("2.0.9"), "2.0.10")
        self.assertIsNone(siguiente_version("main"))
        self.assertIsNone(siguiente_version("v2.0.24-rc.0"))

    def test_calcula_commits_pendientes_desde_el_ultimo_despliegue(self):
        gh = GitHubPendientes()
        self.assertEqual(actualizar_pendientes(gh, self.workflow), "actualizado")
        p = PendienteDespliegue.objects.get(workflow=self.workflow)
        self.assertEqual(p.commits_pendientes, 4)
        self.assertEqual(p.sha_cabeza, CABEZA)
        self.assertEqual(p.rama_principal, "main")
        # Ignora la ejecución de pull request: el último despliegue es la release.
        self.assertEqual(p.ultimo_despliegue_sha, DESPLEGADO)
        self.assertEqual(p.ultimo_despliegue_evento, "release")
        self.assertEqual(p.rama_sugerida, "v1.5.4")

    def test_sin_cambios_no_vuelve_a_comparar(self):
        gh = GitHubPendientes()
        actualizar_pendientes(gh, self.workflow)
        gh.llamadas.clear()
        self.assertEqual(actualizar_pendientes(gh, self.workflow), "sin_cambios")
        # Solo las dos consultas condicionales (304, no gastan cuota).
        self.assertEqual(len(gh.llamadas), 2)
        self.assertFalse(any("/compare/" in r for r in gh.llamadas))

    def test_al_desplegar_la_cabeza_no_quedan_pendientes(self):
        gh = GitHubPendientes()
        actualizar_pendientes(gh, self.workflow)
        gh.despliegues.insert(0, {"id": 10, "event": "release",
                                  "head_sha": CABEZA, "head_branch": "v1.5.4",
                                  "run_started_at": "2026-11-12T10:00:00Z"})
        actualizar_pendientes(gh, self.workflow)
        p = PendienteDespliegue.objects.get(workflow=self.workflow)
        self.assertEqual(p.commits_pendientes, 0)
        self.assertEqual(p.rama_sugerida, "v1.5.5")

    def test_commit_desplegado_que_ya_no_existe(self):
        # Caso Sophon/FightingNerd: compare responde 404.
        gh = GitHubPendientes()
        original = gh.get

        def get(ruta, params=None):
            if "/compare/" in ruta:
                raise github.NoEncontrado(ruta)
            return original(ruta, params)

        gh.get = get
        self.assertEqual(actualizar_pendientes(gh, self.workflow), "actualizado")
        self.assertIsNone(PendienteDespliegue.objects.get(
            workflow=self.workflow).commits_pendientes)

    def test_sin_despliegues_correctos_no_hay_con_que_comparar(self):
        gh = GitHubPendientes()
        gh.despliegues = []
        actualizar_pendientes(gh, self.workflow)
        self.assertIsNone(PendienteDespliegue.objects.get(
            workflow=self.workflow).commits_pendientes)


@override_settings(GEMINI_API_KEY="")
class NuevoAnalisisPendientesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente
    predecir = test_api.ApiTest.predecir

    def ejecucion(self, conclusion, status="completed", sha=test_api.SHA, path=None):
        return {"id": 77, "run_attempt": 1, "status": status,
                "conclusion": conclusion, "head_sha": sha,
                "path": path or ".github/workflows/deploy.yml",
                "event": "release", "head_branch": "v6.3.0",
                "run_started_at": "2026-11-06T21:21:00Z",
                "html_url": "https://github.com/acme/tienda/actions/runs/77"}

    def analizar(self, runs, **extra):
        falso = type("Falso", (test_api.ClienteFalso,), {"RUNS_REALES": runs})
        return self.predecir(self.dev, {**test_api.DATOS, **extra}, falso)

    def test_avisa_si_el_commit_ya_se_desplego(self):
        r = self.analizar([self.ejecucion("success")])
        self.assertEqual(r.status_code, 409, r.content)
        cuerpo = r.json()
        self.assertEqual(cuerpo["codigo"], "commit_ya_desplegado")
        self.assertFalse(cuerpo["en_curso"])
        self.assertEqual(cuerpo["ejecucion"]["run_id"], 77)
        self.assertEqual(cuerpo["ejecucion"]["iniciada_en"], "2026-11-06T21:21:00Z")
        self.assertIn("ya se desplegó", cuerpo["detail"])
        self.assertFalse(Prediccion.objects.exists())

    def test_continuar_de_todos_modos(self):
        r = self.analizar([self.ejecucion("success")], confirmar_desplegado=True)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Prediccion.objects.count(), 1)

    def test_avisa_si_se_esta_desplegando(self):
        r = self.analizar([self.ejecucion(None, status="in_progress")])
        self.assertEqual(r.status_code, 409)
        self.assertTrue(r.json()["en_curso"])

    def test_no_avisa_por_fallidas_omitidas_ni_de_otro_workflow(self):
        # Un reintento de un fallo sí es un despliegue futuro enlazable.
        runs = [self.ejecucion("failure"), self.ejecucion("skipped"), self.ejecucion("cancelled"),
                self.ejecucion("success", path=".github/workflows/ci.yml")]
        r = self.analizar(runs)
        self.assertEqual(r.status_code, 201, r.content)

    def test_selector_con_pendientes_sin_consultar_github(self):
        workflow = Workflow.objects.get(repositorio=self.repo,
                                        path=".github/workflows/deploy.yml")
        PendienteDespliegue.objects.create(
            workflow=workflow, rama_principal="main", sha_cabeza="c" * 40,
            commits_pendientes=3, ultimo_despliegue_evento="release",
            rama_sugerida="v1.5.4", calculado_en="2026-11-12T05:00:00Z")
        with mock.patch.object(github, "GitHubClient",
                               side_effect=AssertionError("sin GitHub")):
            r = self.cliente(self.dev).get("/api/repositorios/")
        self.assertEqual(r.status_code, 200, r.content)
        repo = next(x for x in r.json() if x["nombre_completo"] == "acme/tienda")
        pendientes = repo["workflows"][0]["pendientes"]
        self.assertEqual(pendientes["commits"], 3)
        self.assertEqual(pendientes["sha"], "c" * 40)
        self.assertEqual(pendientes["evento"], "release")
        self.assertEqual(pendientes["rama"], "v1.5.4")
