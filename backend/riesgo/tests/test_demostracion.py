from unittest import mock

from django.test import TestCase, override_settings

from riesgo.models import EjecucionWorkflow, Prediccion, Repositorio
from riesgo.services import github
from riesgo.tests import test_api
from riesgo.tests.test_api import DATOS, ClienteFalso


@override_settings(GEMINI_API_KEY="")
class RepositorioDemostracionTest(TestCase):
    """Un repositorio de demostración (p. ej. ErickTerranova2004/
    demo-despliegue-riesgo) sirve para demostraciones en vivo, pero sus
    ejecuciones quedan fuera del entrenamiento, las métricas y los dashboards."""

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente
    run_real = test_api.ApiTest.run_real
    verificar = test_api.ApiTest.verificar

    def setUp(self):
        Repositorio.objects.filter(id=self.repo.id).update(es_demostracion=True)

    def analizar(self):
        with mock.patch.object(github, "GitHubClient", ClienteFalso):
            r = self.cliente(self.dev).post("/api/predicciones/", DATOS, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def test_sigue_disponible_para_demostraciones(self):
        analisis = self.analizar()
        self.assertTrue(analisis["demostracion"])
        # Resultado, historial y planificador funcionan igual.
        url = f"/api/predicciones/{analisis['id']}"
        self.assertEqual(self.cliente(self.dev).get(f"{url}/").status_code, 200)
        historial = self.cliente(self.dev).get("/api/predicciones/").json()
        self.assertEqual([p["id"] for p in historial], [analisis["id"]])
        self.assertEqual(self.cliente(self.dev).get(f"{url}/ventanas/").status_code, 200)
        jobs = [{"id": 1, "name": "deploy", "conclusion": "success", "started_at": "x",
                 "steps": [{"number": 1, "name": "Deploy to ECS", "conclusion": "success"}]}]
        r = self.verificar(self.dev, analisis["id"],
                           [self.run_real(analisis["id"], 5, conclusion="success")], jobs)
        self.assertEqual(r.json()["ejecucion_real"]["etiqueta"], "despliegue_completado")

    def test_fuera_de_los_datos_del_modelo(self):
        analisis = self.analizar()
        jobs = [{"id": 1, "name": "deploy", "conclusion": "success", "started_at": "x",
                 "steps": [{"number": 1, "name": "Deploy to ECS", "conclusion": "success"}]}]
        self.verificar(self.dev, analisis["id"],
                       [self.run_real(analisis["id"], 5, conclusion="success")], jobs)
        # Entrenamiento y métricas parten de para_modelo(): la demo no aparece.
        self.assertTrue(Prediccion.objects.filter(id=analisis["id"]).exists())
        self.assertFalse(Prediccion.objects.para_modelo().filter(id=analisis["id"]).exists())
        self.assertTrue(EjecucionWorkflow.objects.filter(workflow__repositorio=self.repo).exists())
        self.assertFalse(EjecucionWorkflow.objects.para_modelo()
                         .filter(workflow__repositorio=self.repo).exists())
        # Al quitar la marca vuelve a contar como dato del modelo.
        Repositorio.objects.filter(id=self.repo.id).update(es_demostracion=False)
        self.assertTrue(Prediccion.objects.para_modelo().filter(id=analisis["id"]).exists())

    def test_fuera_de_las_metricas_de_supervision(self):
        analisis = self.analizar()
        modelo = Prediccion.objects.get(id=analisis["id"]).version_modelo_id
        datos = self.cliente(self.admin).get(f"/api/modelos/{modelo}/supervision/").json()
        self.assertEqual(datos["predicciones"], 0)
        self.assertEqual(datos["evaluables"], 0)
        self.assertEqual(datos["predicciones_demostracion"], 1)
