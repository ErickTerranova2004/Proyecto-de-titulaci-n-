"""Recomendación automática (funcionalidad 6), estado de los repositorios y
modelo v2 a través de la API."""

import csv
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from riesgo.models import Prediccion, Repositorio, VersionModelo
from riesgo.services import github
from riesgo.services.predictor import recomendacion_de
from riesgo.tests import test_api
from riesgo.tests.test_api import DATOS, ClienteFalso


class RecomendacionDeTest(SimpleTestCase):
    def test_alto_pide_revision_y_bajo_o_medio_permiten(self):
        self.assertEqual(recomendacion_de("alto"), "solicitar_revision")
        self.assertEqual(recomendacion_de("medio"), "permitir")
        self.assertEqual(recomendacion_de("bajo"), "permitir")


@override_settings(GEMINI_API_KEY="")
class RecomendacionApiTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente
    predecir = test_api.ApiTest.predecir

    def analizar(self):
        r = self.predecir(self.dev)
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def decidir(self, id_, decision):
        r = self.cliente(self.lider).post(
            f"/api/predicciones/{id_}/decision/",
            {"decision": decision, "comentario": "ok"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["decisiones"][0]

    def test_se_guarda_con_la_prediccion_segun_el_nivel(self):
        analisis = self.analizar()
        self.assertEqual(analisis["recomendacion"],
                         recomendacion_de(analisis["nivel"]))
        guardada = Prediccion.objects.get(id=analisis["id"])
        self.assertEqual(guardada.recomendacion, analisis["recomendacion"])

    def _con_nivel(self, nivel):
        """Fuerza el nivel para probar las dos recomendaciones."""
        with mock.patch("riesgo.services.predictor.nivel_de",
                        return_value=nivel):
            return self.analizar()

    def test_nivel_alto_recomienda_solicitar_revision(self):
        self.assertEqual(self._con_nivel("alto")["recomendacion"],
                         "solicitar_revision")
        for nivel in ("bajo", "medio"):
            self.assertEqual(self._con_nivel(nivel)["recomendacion"],
                             "permitir")

    def test_el_lider_acepta_la_recomendacion(self):
        analisis = self._con_nivel("alto")
        decision = self.decidir(analisis["id"], "solicitar_revision")
        self.assertEqual(decision["recomendacion"], "solicitar_revision")
        self.assertIs(decision["acepta_recomendacion"], True)
        analisis = self._con_nivel("bajo")
        self.assertIs(self.decidir(analisis["id"], "autorizar")
                      ["acepta_recomendacion"], True)

    def test_el_lider_cambia_la_recomendacion(self):
        analisis = self._con_nivel("alto")
        decision = self.decidir(analisis["id"], "autorizar")
        self.assertEqual(decision["recomendacion"], "solicitar_revision")
        self.assertIs(decision["acepta_recomendacion"], False)
        # Posponer no coincide con ninguna recomendación.
        analisis = self._con_nivel("medio")
        self.assertIs(self.decidir(analisis["id"], "posponer")
                      ["acepta_recomendacion"], False)

    def test_predicciones_anteriores_sin_recomendacion(self):
        analisis = self.analizar()
        Prediccion.objects.filter(id=analisis["id"]).update(recomendacion="")
        decision = self.decidir(analisis["id"], "autorizar")
        self.assertEqual(decision["recomendacion"], "")
        self.assertIsNone(decision["acepta_recomendacion"])

    def test_el_desarrollador_no_registra_decisiones(self):
        analisis = self.analizar()
        r = self.cliente(self.dev).post(
            f"/api/predicciones/{analisis['id']}/decision/",
            {"decision": "autorizar"}, format="json")
        self.assertEqual(r.status_code, 403)


@override_settings(GEMINI_API_KEY="")
class EstadoRepositorioTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente
    predecir = test_api.ApiTest.predecir

    def test_inactivo_conserva_historial_pero_no_admite_analisis(self):
        anterior = self.predecir(self.dev).json()
        Repositorio.objects.filter(id=self.repo.id).update(est_registro="I")
        r = self.predecir(self.dev)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "repositorio_inactivo")
        # No aparece en los selectores (ni con ?todos=1).
        for url in ("/api/repositorios/", "/api/repositorios/?todos=1"):
            nombres = [x["nombre_completo"] for x in
                       self.cliente(self.dev).get(url).json()]
            self.assertNotIn("acme/tienda", nombres)
        # Su historial sigue visible.
        historial = self.cliente(self.dev).get("/api/predicciones/").json()
        self.assertEqual([p["id"] for p in historial], [anterior["id"]])

    def test_prueba_fuera_de_metricas_y_dashboards(self):
        analisis = self.predecir(self.dev).json()
        self.assertFalse(analisis["prueba"])
        Repositorio.objects.filter(id=self.repo.id).update(es_prueba=True)
        self.assertFalse(Prediccion.objects.para_modelo()
                         .filter(id=analisis["id"]).exists())
        # El serializador lo marca para que el panel no lo cuente.
        self.assertTrue(self.cliente(self.dev).get(
            f"/api/predicciones/{analisis['id']}/").json()["prueba"])
        modelo = Prediccion.objects.get(id=analisis["id"]).version_modelo_id
        datos = self.cliente(self.admin).get(
            f"/api/modelos/{modelo}/supervision/").json()
        self.assertEqual(datos["predicciones"], 0)
        self.assertEqual(datos["predicciones_prueba"], 1)
        self.assertEqual(datos["predicciones_demostracion"], 0)


class AplicarDecisionesReposTest(TestCase):
    def setUp(self):
        crear = Repositorio.objects.create
        self.ghalogs = crear(nombre_completo="org/ghalogs", propietario="org",
                             nombre="ghalogs")
        self.caso = crear(nombre_completo="org/caso", propietario="org",
                          nombre="caso")
        self.azure = crear(nombre_completo="Azure-Samples/azure-search-openai-demo",
                           propietario="Azure-Samples",
                           nombre="azure-search-openai-demo")
        self.demo = crear(nombre_completo="yo/demo", propietario="yo",
                          nombre="demo", es_demostracion=True)
        self.otro = crear(nombre_completo="org/otro", propietario="org",
                          nombre="otro")
        carpeta = Path(tempfile.mkdtemp())
        self.dataset = carpeta / "dataset.csv"
        with open(self.dataset, "w", newline="", encoding="utf-8") as f:
            escritor = csv.writer(f)
            escritor.writerow(["run_id", "repository_name"])
            escritor.writerow([1, "org/ghalogs"])
            escritor.writerow([2, "yo/demo"])
        self.casos = carpeta / "casos.json"
        self.casos.write_text(json.dumps([{"repositorio": "org/caso"}]),
                              encoding="utf-8")

    def ejecutar(self, *extra):
        salida = StringIO()
        call_command("aplicar_decisiones_repos", "--dataset-ghalogs",
                     str(self.dataset), "--casos-prueba", str(self.casos),
                     *extra, stdout=salida)
        return salida.getvalue()

    def estado(self, repo):
        repo.refresh_from_db()
        return repo.est_registro, repo.es_prueba

    def test_sin_aplicar_no_cambia_nada(self):
        texto = self.ejecutar()
        self.assertIn("no se guardó nada", texto)
        for repo in (self.ghalogs, self.caso, self.azure):
            self.assertEqual(self.estado(repo), ("A", False))

    def test_aplica_las_decisiones_y_deja_la_demo_igual(self):
        self.ejecutar("--aplicar")
        self.assertEqual(self.estado(self.ghalogs), ("I", False))
        self.assertEqual(self.estado(self.azure), ("I", False))
        self.assertEqual(self.estado(self.caso), ("A", True))
        self.assertEqual(self.estado(self.otro), ("A", False))
        self.assertEqual(self.estado(self.demo), ("A", False))
        # Idempotente.
        self.assertIn("cambian 0", self.ejecutar("--aplicar"))


@override_settings(GEMINI_API_KEY="")
class ModeloV2ApiTest(TestCase):
    """El modelo v2 registrado calcula todas sus variables, SHAP y la
    recomendación a través de la API."""

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)
        # v1.1 registrada y después v2 (la versión por defecto).
        call_command("registrar_modelo", "--modelo", "v1.1", stdout=StringIO())
        call_command("registrar_modelo", stdout=StringIO())

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente
    predecir = test_api.ApiTest.predecir

    def test_v2_vigente_y_v1_1_no(self):
        self.assertEqual(list(VersionModelo.objects.filter(activo=True)
                              .values_list("version", flat=True)), ["v2"])
        self.assertFalse(VersionModelo.objects.get(version="v1.1").activo)

    def test_prediccion_con_v2(self):
        r = self.predecir(self.dev)
        self.assertEqual(r.status_code, 201, r.content)
        cuerpo = r.json()
        meta = VersionModelo.objects.get(version="v2").metadatos
        self.assertEqual(cuerpo["version_modelo"], "v2")
        esperadas = meta["variables_categoricas"] + meta["variables_numericas"]
        self.assertTrue(set(esperadas) <= set(cuerpo["variables"]))
        self.assertTrue(cuerpo["factores"])
        self.assertEqual(cuerpo["recomendacion"],
                         recomendacion_de(cuerpo["nivel"]))
        # La v1.1 usaba reejecutado_por_otro (información futura): v2 no.
        self.assertNotIn("reejecutado_por_otro", esperadas)
        self.assertNotIn("reejecutado_por_otro",
                         [f["variable"] for f in cuerpo["factores"]])
