"""Las decisiones del líder solo se toman sobre análisis de un desarrollador:
los del lote (cuenta analisis_lote) no se ven ni admiten decisión."""

from riesgo.models import AccesoRepositorio, DecisionDespliegue, Prediccion
from riesgo.tests import test_api, test_sombra


class DecisionLoteTest(test_sombra.Base):
    def setUp(self):
        self.lider = test_api.ApiTest._usuario("lider", "lider_tecnico", [self.repo])
        self.dev = test_api.ApiTest._usuario("dev", "desarrollador", [self.repo])
        self.api_lider = test_api.ApiTest.cliente(self, self.lider)
        self.lote_p = self.prediccion()                        # del lote
        self.dev_p = self.prediccion(origen="interactivo")
        Prediccion.objects.filter(id=self.dev_p.id).update(usuario=self.dev)

    def test_el_lider_solo_ve_analisis_de_desarrolladores(self):
        ids = [p["id"] for p in self.api_lider.get("/api/predicciones/").json()]
        self.assertEqual(ids, [self.dev_p.id])
        self.assertEqual(self.api_lider.get(
            f"/api/predicciones/{self.lote_p.id}/").status_code, 404)

    def test_no_se_decide_sobre_un_analisis_del_lote(self):
        admin = test_api.ApiTest._usuario("admin", "administrador", [])
        r = test_api.ApiTest.cliente(self, admin).post(
            f"/api/predicciones/{self.lote_p.id}/decision/",
            {"decision": "posponer", "fecha_limite": "2099-01-01"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "no_es_interactivo")
        self.assertFalse(DecisionDespliegue.objects.exists())

    def test_la_asignacion_llega_al_desarrollador(self):
        r = self.api_lider.post(
            f"/api/predicciones/{self.dev_p.id}/decision/",
            {"decision": "solicitar_revision", "comentario": "Revise el YAML",
             "fecha_limite": "2099-01-01"}, format="json")
        self.assertEqual(r.status_code, 201)
        asignaciones = test_api.ApiTest.cliente(self, self.dev).get(
            "/api/asignaciones/").json()
        self.assertEqual([a["prediccion"] for a in asignaciones], [self.dev_p.id])
        self.assertEqual(asignaciones[0]["mensaje"], "Revise el YAML")
