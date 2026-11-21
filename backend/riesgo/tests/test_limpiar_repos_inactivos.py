"""Limpieza de repositorios inactivos y workflows no productivos
(manage.py limpiar_repos_inactivos)."""

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from riesgo.management.commands.limpiar_repos_inactivos import no_es_produccion
from riesgo.models import (AccesoRepositorio, DecisionDespliegue, Prediccion,
                           PrediccionEjecucion, Repositorio, Workflow)
from riesgo.services import github
from riesgo.tests import test_api
from riesgo.tests.test_api import DATOS, ClienteFalso


class ReglaProduccionTest(SimpleTestCase):

    def test_no_productivos_por_el_nombre(self):
        for ruta in ("deploy-staging.yml", "deploy-pages.yml", "dev-deploy-inbound-mail.yml",
                     "qa-deployment.yml", "deploy-dev-app.yml", "preview.yml", "uat.yml",
                     "deploy-demo.yml", "sandbox_deploy.yml", "test.yml", "tests.yml",
                     "deploy-stg.yaml"):
            with self.subTest(ruta=ruta):
                self.assertTrue(no_es_produccion(f".github/workflows/{ruta}"))

    def test_productivos_o_mixtos(self):
        for ruta in ("deploy.yml", "prod-deploy-inbound-mail.yml", "deploy-production.yml",
                     "staging-and-production.yml", "test_and_deploy.yml", "build-test-deploy.yml",
                     "release.yml", "cd.yml", "main.yml", "developer-portal-deploy.yml"):
            with self.subTest(ruta=ruta):
                self.assertFalse(no_es_produccion(f".github/workflows/{ruta}"))


@override_settings(GEMINI_API_KEY="")
class LimpiarReposInactivosTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente

    def setUp(self):
        with mock.patch.object(github, "GitHubClient", ClienteFalso):
            r = self.cliente(self.dev).post("/api/predicciones/", DATOS, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.interactivo = Prediccion.objects.get(pk=r.json()["id"])
        self.decision = self.interactivo.decisiones.create(usuario=self.lider,
                                                           decision="posponer")
        # Análisis en lote del mismo repositorio (historia del modelo v1).
        lote = Prediccion.objects.get(pk=self.interactivo.pk)
        lote.pk = None
        lote.origen = "lote"
        lote.save()
        self.lote = lote
        Repositorio.objects.filter(pk=self.repo.pk).update(est_registro="I")
        # Workflows de repositorios activos: no productivo, demostración y excepción.
        self.staging = Workflow.objects.create(
            repositorio=self.repo_ajeno, path=".github/workflows/deploy-staging.yml",
            despliegue_validado=True, evidencia_validacion="x")
        demo = Repositorio.objects.create(nombre_completo="acme/demo", propietario="acme",
                                          nombre="demo", es_demostracion=True)
        self.demo = Workflow.objects.create(
            repositorio=demo, path=".github/workflows/deploy-demo.yml",
            despliegue_validado=True, evidencia_validacion="x")
        mozilla = Repositorio.objects.create(nombre_completo="mozilla/probe-scraper",
                                             propietario="mozilla", nombre="probe-scraper")
        self.excepcion = Workflow.objects.create(
            repositorio=mozilla, path=".github/workflows/build-test-deploy.yml",
            despliegue_validado=True, evidencia_validacion="x")

    def _comando(self, *args):
        salida = StringIO()
        call_command("limpiar_repos_inactivos", *args, stdout=salida)
        return salida.getvalue()

    def test_sin_aplicar_solo_informa(self):
        salida = self._comando()
        self.assertIn("Análisis interactivos: 1 activos de 1", salida)
        self.assertIn("1 en lote", salida)
        self.assertIn("no se guardó nada", salida)
        self.interactivo.refresh_from_db()
        self.staging.refresh_from_db()
        self.assertEqual(self.interactivo.est_registro, "A")
        self.assertTrue(self.staging.despliegue_validado)

    def test_aplica_sin_borrar(self):
        antes = Prediccion.con_sombra.count()
        self._comando("--aplicar")
        self.assertEqual(Prediccion.con_sombra.count(), antes)
        estado = lambda modelo, **f: set(modelo.objects.filter(**f).values_list("est_registro", flat=True))
        self.assertEqual(estado(Workflow, repositorio=self.repo), {"I"})
        self.assertEqual(Prediccion.objects.get(pk=self.interactivo.pk).est_registro, "I")
        self.assertEqual(DecisionDespliegue.objects.get(pk=self.decision.pk).est_registro, "I")
        self.assertEqual(estado(PrediccionEjecucion, prediccion=self.interactivo), {"I"})
        self.assertEqual(estado(AccesoRepositorio, repositorio=self.repo), {"I"})
        # El lote se conserva tal cual (historia del modelo v1).
        self.assertEqual(Prediccion.objects.get(pk=self.lote.pk).est_registro, "A")
        # Workflows: el no productivo pierde la validación; demostración y
        # excepción no; los de repositorios activos siguen activos.
        for w, validado in ((self.staging, False), (self.demo, True), (self.excepcion, True)):
            w.refresh_from_db()
            self.assertEqual((w.despliegue_validado, w.est_registro), (validado, "A"), w.path)
        self.assertEqual(estado(Workflow, repositorio=self.repo_ajeno), {"A"})
        # Idempotente.
        self.assertIn("Análisis interactivos: 0 activos", self._comando())

    def test_no_salen_en_los_historiales_de_los_roles(self):
        self._comando("--aplicar")
        for usuario, consulta in ((self.dev, ""), (self.lider, ""), (self.admin, "?origen=lote"),
                                  (self.admin, "?origen=interactivo")):
            with self.subTest(usuario=usuario.username, consulta=consulta):
                ids = [p["id"] for p in self.cliente(usuario).get(f"/api/predicciones/{consulta}").json()]
                self.assertNotIn(self.interactivo.id, ids)
                self.assertNotIn(self.lote.id, ids)
        self.assertEqual(self.cliente(self.dev).get("/api/asignaciones/").json(), [])
        self.assertEqual(self.cliente(self.dev).get(
            f"/api/predicciones/{self.interactivo.id}/ventanas/").status_code, 404)
