"""Datos desactivados (est_registro='I'): los de los casos de prueba no salen
en historiales, paneles, pendientes, asignaciones ni en el Planificador, y
se conservan. Comando desactivar_datos_prueba."""

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from riesgo.models import (AccesoRepositorio, DecisionDespliegue, Prediccion,
                           Repositorio, Workflow)
from riesgo.services import github
from riesgo.tests import test_api
from riesgo.tests.test_api import DATOS, ClienteFalso


@override_settings(GEMINI_API_KEY="")
class DatosInactivosTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente

    def _analizar(self, usuario, repositorio):
        with mock.patch.object(github, "GitHubClient", ClienteFalso):
            r = self.cliente(usuario).post(
                "/api/predicciones/", dict(DATOS, repositorio=repositorio),
                format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["id"]

    def setUp(self):
        # acme/tienda hace de repositorio de casos de prueba; acme/ajeno es
        # un repositorio real con un análisis que debe seguir visible.
        self.de_prueba = self._analizar(self.dev, "acme/tienda")
        self.real = self._analizar(self.admin, "acme/ajeno")
        r = self.cliente(self.lider).post(
            f"/api/predicciones/{self.de_prueba}/decision/",
            {"decision": "solicitar_revision", "comentario": "Revise",
             "fecha_limite": "2099-01-01"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.demo = Repositorio.objects.create(
            nombre_completo="acme/demo", propietario="acme", nombre="demo",
            es_demostracion=True, es_prueba=True)
        Repositorio.objects.filter(pk=self.repo.pk).update(es_prueba=True)

    def _desactivar(self, aplicar=True):
        salida = StringIO()
        call_command("desactivar_datos_prueba",
                     *(["--aplicar"] if aplicar else []), stdout=salida)
        return salida.getvalue()

    def _ids(self, usuario, consulta=""):
        r = self.cliente(usuario).get(f"/api/predicciones/{consulta}")
        self.assertEqual(r.status_code, 200)
        return {p["id"] for p in r.json()}

    def test_sin_aplicar_no_cambia_nada(self):
        salida = self._desactivar(aplicar=False)
        self.assertIn("no se guardó nada", salida)
        self.assertEqual(Prediccion.objects.get(pk=self.de_prueba).est_registro, "A")
        self.assertIn(self.de_prueba, self._ids(self.dev))

    def test_desactiva_sin_borrar_y_sin_tocar_demostracion_ni_reales(self):
        antes = Prediccion.con_sombra.count()
        self._desactivar()
        self.assertEqual(Prediccion.con_sombra.count(), antes)
        p = Prediccion.con_sombra.get(pk=self.de_prueba)
        self.assertEqual(p.est_registro, "I")
        self.assertEqual(Repositorio.objects.get(pk=self.repo.pk).est_registro, "I")
        self.assertFalse(Workflow.objects.filter(
            repositorio=self.repo, est_registro="A").exists())
        self.assertFalse(AccesoRepositorio.objects.filter(
            repositorio=self.repo, est_registro="A").exists())
        self.assertEqual(DecisionDespliegue.objects.get(
            prediccion_id=self.de_prueba).est_registro, "I")
        self.assertEqual(Repositorio.objects.get(pk=self.demo.pk).est_registro, "A")
        self.assertEqual(Prediccion.objects.get(pk=self.real).est_registro, "A")
        # Idempotente.
        self.assertIn("Repositorios 0", self._desactivar())

    def test_historiales_pendientes_y_planificador_los_ocultan(self):
        self._desactivar()
        self.assertEqual(self._ids(self.admin), {self.real})
        self.assertEqual(self._ids(self.admin, "?origen=interactivo"), {self.real})
        self.assertEqual(self._ids(self.lider), set())
        self.assertEqual(self._ids(self.lider, "?sin_decision=1"), set())
        self.assertEqual(self._ids(self.dev), set())
        for usuario in (self.admin, self.dev):
            for ruta in ("", "ventanas/"):
                self.assertEqual(self.cliente(usuario).get(
                    f"/api/predicciones/{self.de_prueba}/{ruta}").status_code, 404)

    def test_asignaciones_las_ocultan(self):
        antes = self.cliente(self.dev).get("/api/asignaciones/").json()
        self.assertEqual([a["prediccion"] for a in antes], [self.de_prueba])
        self._desactivar()
        self.assertEqual(self.cliente(self.dev).get("/api/asignaciones/").json(), [])

    def test_un_acceso_desactivado_no_da_visibilidad(self):
        Prediccion.objects.filter(pk=self.de_prueba).update(est_registro="A")
        AccesoRepositorio.objects.filter(usuario=self.lider).update(est_registro="I")
        self.assertEqual(self._ids(self.lider), set())
        repos = self.cliente(self.lider).get("/api/repositorios/?todos=1").json()
        self.assertEqual(repos, [])

    def test_gestion_no_borra_accesos_desactivados_y_puede_reactivarlos(self):
        self._desactivar()
        acceso = AccesoRepositorio.objects.get(usuario=self.dev, repositorio=self.repo)
        r = self.cliente(self.admin).put(
            f"/api/gestion/usuarios/{self.dev.id}/repositorios/",
            {"repositorios": []}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["repositorios"], [])
        acceso.refresh_from_db()
        self.assertEqual(acceso.est_registro, "I")
        r = self.cliente(self.admin).put(
            f"/api/gestion/usuarios/{self.dev.id}/repositorios/",
            {"repositorios": [self.repo.id]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        acceso.refresh_from_db()
        self.assertEqual(acceso.est_registro, "A")
        self.assertEqual(AccesoRepositorio.objects.filter(
            usuario=self.dev, repositorio=self.repo).count(), 1)

    def test_resumen_admin_cuenta_solo_workflows_activos(self):
        antes = self.cliente(self.admin).get("/api/resumen-admin/").json()
        de_prueba = Workflow.objects.filter(repositorio=self.repo).count()
        self.assertGreater(de_prueba, 0)
        self._desactivar()
        despues = self.cliente(self.admin).get("/api/resumen-admin/").json()
        self.assertEqual(despues["workflows"]["total"],
                         antes["workflows"]["total"] - de_prueba)
