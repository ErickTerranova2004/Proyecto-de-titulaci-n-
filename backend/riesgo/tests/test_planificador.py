from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings

from riesgo.services import github
from riesgo.services.planificador import (condiciones_base, momento_base,
                                          momento_escenario,
                                          variables_escenario)
from riesgo.tests import test_api
from riesgo.tests.test_api import DATOS, ClienteFalso

# Lunes 2 de noviembre de 2026, 10:00 en Guayaquil (15:00 UTC).
BASE = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)
VARIABLES = {"hora_utc": 15, "dia_semana": 0, "fin_de_semana": 0,
             "es_reintento": 0, "tiene_pr": 0, "retraso_commit_run_min": 60.0,
             "wf_horas_desde_ultimo": 5.0, "wf_tasa_fallo_prev": 0.5,
             "msg_fix": 1}


def _escenario(dia, hora, reintento=False, pr=False):
    momento = momento_escenario(BASE, dia, hora)
    return variables_escenario(VARIABLES, BASE, momento, reintento, pr)


class ConversionHorariaTest(SimpleTestCase):

    def test_zona_de_la_pantalla(self):
        self.assertEqual(settings.TIME_ZONE, "America/Guayaquil")

    def test_noche_local_es_el_dia_siguiente_en_utc(self):
        v = _escenario(0, 21)  # lunes 21:00 local
        self.assertEqual((v["dia_semana"], v["hora_utc"]), (1, 2))
        self.assertEqual(v["fin_de_semana"], 0)

    def test_sabado_noche_local_es_domingo_utc(self):
        v = _escenario(5, 20)
        self.assertEqual((v["dia_semana"], v["hora_utc"]), (6, 1))
        self.assertEqual(v["fin_de_semana"], 1)

    def test_viernes_noche_local_ya_es_fin_de_semana_utc(self):
        v = _escenario(4, 22)
        self.assertEqual((v["dia_semana"], v["hora_utc"]), (5, 3))
        self.assertEqual(v["fin_de_semana"], 1)

    def test_manana_local(self):
        v = _escenario(2, 8)  # miércoles 08:00 local = 13:00 UTC
        self.assertEqual((v["dia_semana"], v["hora_utc"]), (2, 13))

    def test_condiciones_base_en_hora_local(self):
        prediccion = SimpleNamespace(
            creada_en=datetime(2026, 11, 3, 2, 10, 30, tzinfo=timezone.utc),
            variables={"hora_utc": 2, "dia_semana": 1, "es_reintento": 0,
                       "tiene_pr": 1})
        self.assertEqual(condiciones_base(prediccion),
                         {"dia": 0, "hora": 21, "es_reintento": False,
                          "tiene_pr": True})

    def test_momento_base_vuelve_a_la_hora_calculada(self):
        # Guardado a las 16:00:01 UTC con variables calculadas a las 15:59.
        prediccion = SimpleNamespace(
            creada_en=datetime(2026, 11, 2, 16, 0, 1, tzinfo=timezone.utc),
            variables={"hora_utc": 15, "dia_semana": 0})
        self.assertEqual(momento_base(prediccion).hour, 15)


class VariablesPermitidasTest(SimpleTestCase):

    def test_solo_cambian_condiciones_y_derivadas(self):
        v = _escenario(0, 21, reintento=True, pr=True)
        cambiadas = {k for k in VARIABLES if v[k] != VARIABLES[k]}
        self.assertEqual(cambiadas, {"hora_utc", "dia_semana", "es_reintento",
                                     "tiene_pr", "retraso_commit_run_min",
                                     "wf_horas_desde_ultimo"})
        self.assertEqual(set(v), set(VARIABLES))

    def test_desplegar_mas_tarde_envejece_commit_e_historial(self):
        v = _escenario(0, 21)  # 11 h después del análisis base
        self.assertEqual(v["retraso_commit_run_min"], 60 + 11 * 60)
        self.assertEqual(v["wf_horas_desde_ultimo"], 5 + 11)

    def test_sin_historial_sigue_sin_historial(self):
        variables = dict(VARIABLES, wf_horas_desde_ultimo=None)
        v = variables_escenario(variables, BASE,
                                momento_escenario(BASE, 3, 9), False, False)
        self.assertIsNone(v["wf_horas_desde_ultimo"])

    def test_misma_hora_anterior_es_la_semana_siguiente(self):
        momento = momento_escenario(BASE, 0, 9)  # lunes 09:00 < 10:00
        self.assertEqual(momento - BASE, timedelta(days=7) - timedelta(
            hours=1))


@override_settings(GEMINI_API_KEY="")
class PlanificadorApiTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente

    def setUp(self):
        with mock.patch.object(github, "GitHubClient", ClienteFalso):
            r = self.cliente(self.dev).post("/api/predicciones/", DATOS,
                                            format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.prediccion = r.json()
        self.url = f"/api/predicciones/{self.prediccion['id']}"

    def _conteos(self):
        return {m.__name__: m.objects.count()
                for m in apps.get_app_config("riesgo").get_models()}

    def test_escenario_sin_cambios_reproduce_el_analisis_base(self):
        base = self.cliente(self.dev).get(f"{self.url}/ventanas/").json()[
            "condiciones_base"]
        r = self.cliente(self.dev).post(f"{self.url}/escenario/", base,
                                        format="json")
        self.assertEqual(r.status_code, 200, r.content)
        cuerpo = r.json()
        self.assertAlmostEqual(cuerpo["escenario"]["probabilidad"],
                               self.prediccion["probabilidad"], places=12)
        self.assertAlmostEqual(cuerpo["base"]["probabilidad"],
                               self.prediccion["probabilidad"], places=12)
        self.assertEqual(cuerpo["escenario"]["nivel"],
                         self.prediccion["nivel"])
        self.assertEqual(cuerpo["diferencia_puntos"], 0)
        self.assertEqual(cuerpo["explicacion"], [])

    def test_escenario_alternativo_devuelve_comparacion(self):
        r = self.cliente(self.dev).post(
            f"{self.url}/escenario/",
            {"dia": 5, "hora": 22, "es_reintento": True, "tiene_pr": True},
            format="json")
        self.assertEqual(r.status_code, 200, r.content)
        cuerpo = r.json()
        self.assertIn(cuerpo["escenario"]["nivel"], ["bajo", "medio", "alto"])
        self.assertTrue(cuerpo["escenario"]["factores"])
        self.assertAlmostEqual(
            cuerpo["diferencia_puntos"],
            (cuerpo["escenario"]["probabilidad"]
             - cuerpo["base"]["probabilidad"]) * 100, places=1)
        self.assertTrue(all(e["diferencia"] for e in cuerpo["explicacion"]))

    def test_rechaza_variables_no_permitidas(self):
        r = self.cliente(self.dev).post(
            f"{self.url}/escenario/",
            {"dia": 1, "hora": 9, "es_reintento": False, "tiene_pr": False,
             "wf_tasa_fallo_prev": 0},
            format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("wf_tasa_fallo_prev", r.json())
        for valor in ({"dia": 7}, {"hora": 24}):
            datos = {"dia": 1, "hora": 9, "es_reintento": False,
                     "tiene_pr": False, **valor}
            self.assertEqual(self.cliente(self.dev).post(
                f"{self.url}/escenario/", datos,
                format="json").status_code, 400)

    def test_no_guarda_nada(self):
        antes = self._conteos()
        self.cliente(self.dev).post(
            f"{self.url}/escenario/",
            {"dia": 2, "hora": 8, "es_reintento": False, "tiene_pr": False},
            format="json")
        self.cliente(self.dev).get(f"{self.url}/ventanas/")
        self.assertEqual(self._conteos(), antes)

    def test_mejores_ventanas(self):
        r = self.cliente(self.dev).get(f"{self.url}/ventanas/")
        self.assertEqual(r.status_code, 200, r.content)
        ventanas = r.json()["ventanas"]
        self.assertEqual(len(ventanas), 3)
        probs = [v["probabilidad"] for v in ventanas]
        self.assertEqual(probs, sorted(probs))
        creada = datetime.fromisoformat(
            self.prediccion["creada_en"].replace("Z", "+00:00"))
        fechas = set()
        for v in ventanas:
            momento = datetime.fromisoformat(v["momento_local"])
            self.assertTrue(7 <= v["hora"] <= 20)
            self.assertEqual(momento.hour, v["hora"])
            self.assertTrue(timedelta(0) < momento - creada
                            <= timedelta(days=7, hours=1))
            fechas.add(momento.date())
        self.assertEqual(len(fechas), 3)

    def test_otro_desarrollador_no_ve_el_analisis(self):
        datos = {"dia": 1, "hora": 9, "es_reintento": False,
                 "tiene_pr": False}
        self.assertEqual(self.cliente(self.dev2).post(
            f"{self.url}/escenario/", datos, format="json").status_code, 404)
        self.assertEqual(self.cliente(self.dev2).get(
            f"{self.url}/ventanas/").status_code, 404)


class VocabularioTest(SimpleTestCase):
    """El planificador estima escenarios; no usa la palabra prohibida."""

    def test_sin_palabra_prohibida(self):
        raiz = Path(settings.BASE_DIR).parent
        archivos = [
            raiz / "backend/riesgo/services/planificador.py",
            raiz / "frontend/src/components/Planificador.jsx",
            raiz / "frontend/src/roles.js",
            raiz / "frontend/src/api.js",
        ]
        prohibida = "simul" + "a"
        for archivo in archivos:
            with self.subTest(archivo=archivo.name):
                self.assertNotIn(prohibida,
                                 archivo.read_text(encoding="utf-8").lower())
