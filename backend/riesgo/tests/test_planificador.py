from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from zoneinfo import ZoneInfo

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings

from riesgo.models import Prediccion
from riesgo.services import github, planificador
from riesgo.services.planificador import (condiciones_base, momento_base,
                                          momento_local, validar_momento,
                                          variables_escenario)
from riesgo.tests import test_api
from riesgo.tests.test_api import DATOS, ClienteFalso

GYE = ZoneInfo("America/Guayaquil")
# Lunes 2 de noviembre de 2026, 10:00 en Guayaquil (15:00 UTC).
BASE = datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc)
VARIABLES = {"hora_utc": 15, "dia_semana": 0, "fin_de_semana": 0,
             "es_reintento": 0, "tiene_pr": 0, "retraso_commit_run_min": 60.0,
             "wf_horas_desde_ultimo": 5.0, "wf_tasa_fallo_prev": 0.5,
             "msg_fix": 1}
# Fechas guardadas coherentes con VARIABLES (commit 60 min y última
# ejecución previa 5 h antes del análisis base).
COMMIT = BASE - timedelta(minutes=60)
PREVIA = BASE - timedelta(hours=5)


def _escenario(fecha, hora, reintento=False, pr=False, refs=True):
    extra = {"fecha_commit": COMMIT, "ultima_previa": PREVIA} if refs else {}
    return variables_escenario(VARIABLES, BASE, momento_local(fecha, hora),
                               reintento, pr, **extra)


def _ahora(local):
    """Fija la hora actual (dada en hora de Guayaquil)."""
    return mock.patch.object(planificador, "ahora",
                             return_value=local.replace(tzinfo=GYE))


class ConversionHorariaTest(SimpleTestCase):

    def test_zona_de_la_pantalla(self):
        self.assertEqual(settings.TIME_ZONE, "America/Guayaquil")

    def test_noche_local_es_el_dia_siguiente_en_utc(self):
        v = _escenario(date(2026, 11, 2), 21)  # lunes 21:00 local
        self.assertEqual((v["dia_semana"], v["hora_utc"]), (1, 2))
        self.assertEqual(v["fin_de_semana"], 0)

    def test_sabado_noche_local_es_domingo_utc(self):
        v = _escenario(date(2026, 11, 7), 20)
        self.assertEqual((v["dia_semana"], v["hora_utc"]), (6, 1))
        self.assertEqual(v["fin_de_semana"], 1)

    def test_viernes_noche_local_ya_es_fin_de_semana_utc(self):
        v = _escenario(date(2026, 11, 6), 22)
        self.assertEqual((v["dia_semana"], v["hora_utc"]), (5, 3))
        self.assertEqual(v["fin_de_semana"], 1)

    def test_manana_local(self):
        v = _escenario(date(2026, 11, 4), 8)  # miércoles 08:00 = 13:00 UTC
        self.assertEqual((v["dia_semana"], v["hora_utc"]), (2, 13))

    def test_condiciones_base_en_hora_local(self):
        prediccion = SimpleNamespace(
            creada_en=datetime(2026, 11, 3, 2, 10, 30, tzinfo=timezone.utc),
            momento_variables=None,
            variables={"hora_utc": 2, "dia_semana": 1, "es_reintento": 0,
                       "tiene_pr": 1})
        self.assertEqual(condiciones_base(prediccion),
                         {"fecha": "2026-11-02", "dia": 0, "hora": 21,
                          "es_reintento": False, "tiene_pr": True})

    def test_momento_base_vuelve_a_la_hora_calculada(self):
        # Guardado a las 16:00:01 UTC con variables calculadas a las 15:59.
        prediccion = SimpleNamespace(
            creada_en=datetime(2026, 11, 2, 16, 0, 1, tzinfo=timezone.utc),
            momento_variables=None,
            variables={"hora_utc": 15, "dia_semana": 0})
        self.assertEqual(momento_base(prediccion).hour, 15)

    def test_momento_base_de_un_analisis_en_lote(self):
        fijado = datetime(2026, 11, 1, 3, 30, tzinfo=timezone.utc)
        prediccion = SimpleNamespace(creada_en=BASE, momento_variables=fijado,
                                     variables={})
        self.assertEqual(momento_base(prediccion), fijado)


class VariablesDeTiempoTest(SimpleTestCase):
    """Las variables que dependen del momento se recalculan para el
    escenario; el resto queda como en el análisis base."""

    def test_solo_cambian_condiciones_y_variables_de_tiempo(self):
        v = _escenario(date(2026, 11, 2), 21, reintento=True, pr=True)
        cambiadas = {k for k in VARIABLES if v[k] != VARIABLES[k]}
        self.assertEqual(cambiadas, {"hora_utc", "dia_semana", "es_reintento",
                                     "tiene_pr", "retraso_commit_run_min",
                                     "wf_horas_desde_ultimo"})
        self.assertEqual(set(v), set(VARIABLES))
        self.assertEqual(v["wf_tasa_fallo_prev"], 0.5)

    def test_se_recalculan_desde_commit_y_ultima_ejecucion(self):
        # Jueves 19/11 09:00 local: 17 días y 23 h después del análisis base.
        v = _escenario(date(2026, 11, 19), 9)
        momento = datetime(2026, 11, 19, 14, 0, tzinfo=timezone.utc)
        self.assertEqual(v["retraso_commit_run_min"],
                         (momento - COMMIT).total_seconds() / 60)
        self.assertEqual(v["wf_horas_desde_ultimo"],
                         (momento - PREVIA).total_seconds() / 3600)
        self.assertEqual((v["hora_utc"], v["dia_semana"]), (14, 3))

    def test_sin_fechas_guardadas_se_desplaza_el_valor_base(self):
        v = _escenario(date(2026, 11, 2), 21, refs=False)  # 11 h después
        self.assertEqual(v["retraso_commit_run_min"], 60 + 11 * 60)
        self.assertEqual(v["wf_horas_desde_ultimo"], 5 + 11)

    def test_el_retraso_nunca_es_negativo(self):
        v = variables_escenario(VARIABLES, BASE,
                                momento_local(date(2026, 11, 2), 8), False,
                                False, fecha_commit=BASE)
        self.assertEqual(v["retraso_commit_run_min"], 0)

    def test_sin_historial_sigue_sin_historial(self):
        variables = dict(VARIABLES, wf_horas_desde_ultimo=None,
                         retraso_commit_run_min=None)
        v = variables_escenario(variables, BASE,
                                momento_local(date(2026, 11, 5), 9), False,
                                False, fecha_commit=COMMIT,
                                ultima_previa=PREVIA)
        self.assertIsNone(v["wf_horas_desde_ultimo"])
        self.assertIsNone(v["retraso_commit_run_min"])

    def test_no_modifica_las_variables_del_analisis_base(self):
        copia = dict(VARIABLES)
        _escenario(date(2026, 11, 20), 15, reintento=True, pr=True)
        self.assertEqual(VARIABLES, copia)


class MomentoValidoTest(SimpleTestCase):

    def test_desde_la_hora_en_curso(self):
        with _ahora(datetime(2026, 11, 18, 19, 52)):
            self.assertEqual(validar_momento(date(2026, 11, 18), 19), "")
            self.assertEqual(validar_momento(date(2026, 11, 18), 20), "")
            self.assertIn("hora actual",
                          validar_momento(date(2026, 11, 18), 18))
            self.assertIn("hora actual",
                          validar_momento(date(2026, 11, 17), 23))

    def test_hasta_el_limite_de_dias(self):
        with _ahora(datetime(2026, 11, 18, 10, 0)):
            self.assertEqual(validar_momento(date(2026, 12, 2), 9), "")
            self.assertIn("14 días", validar_momento(date(2026, 12, 3), 9))


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
        self.manana = (planificador.hoy_local() + timedelta(days=1))

    def _conteos(self):
        return {m.__name__: m.objects.count()
                for m in apps.get_app_config("riesgo").get_models()}

    def _datos(self, fecha=None, hora=9, **extra):
        return {"fecha": (fecha or self.manana).isoformat(), "hora": hora,
                "es_reintento": False, "tiene_pr": False, **extra}

    def test_escenario_devuelve_comparacion(self):
        r = self.cliente(self.dev).post(
            f"{self.url}/escenario/",
            self._datos(hora=22, es_reintento=True, tiene_pr=True),
            format="json")
        self.assertEqual(r.status_code, 200, r.content)
        cuerpo = r.json()
        self.assertIn(cuerpo["escenario"]["nivel"], ["bajo", "medio", "alto"])
        self.assertTrue(cuerpo["escenario"]["factores"])
        self.assertAlmostEqual(cuerpo["base"]["probabilidad"],
                               self.prediccion["probabilidad"], places=12)
        self.assertAlmostEqual(
            cuerpo["diferencia_puntos"],
            (cuerpo["escenario"]["probabilidad"]
             - cuerpo["base"]["probabilidad"]) * 100, places=1)
        self.assertTrue(all(e["diferencia"] for e in cuerpo["explicacion"]))
        self.assertEqual(cuerpo["condiciones"]["fecha"],
                         self.manana.isoformat())
        self.assertEqual(cuerpo["condiciones"]["dia"], self.manana.weekday())
        momento = datetime.fromisoformat(cuerpo["escenario"]["momento_local"])
        self.assertEqual((momento.date(), momento.hour, momento.minute),
                         (self.manana, 22, 0))

    def test_variables_de_tiempo_respecto_al_escenario(self):
        r = self.cliente(self.dev).post(f"{self.url}/escenario/",
                                        self._datos(hora=9), format="json")
        self.assertEqual(r.status_code, 200, r.content)
        tiempo = r.json()["variables_tiempo"]["escenario"]
        momento = momento_local(self.manana, 9).astimezone(timezone.utc)
        commit = datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc)
        previa = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)
        self.assertEqual(tiempo["hora_utc"], 14)
        self.assertEqual(tiempo["dia_semana"], momento.weekday())
        self.assertEqual(tiempo["fin_de_semana"], int(momento.weekday() >= 5))
        self.assertAlmostEqual(tiempo["retraso_commit_run_min"],
                               (momento - commit).total_seconds() / 60)
        self.assertAlmostEqual(tiempo["wf_horas_desde_ultimo"],
                               (momento - previa).total_seconds() / 3600)
        base = r.json()["variables_tiempo"]["base"]
        guardadas = Prediccion.objects.get(pk=self.prediccion["id"]).variables
        self.assertEqual(base["retraso_commit_run_min"],
                         guardadas["retraso_commit_run_min"])

    def test_rechaza_variables_no_permitidas_y_momentos_pasados(self):
        r = self.cliente(self.dev).post(
            f"{self.url}/escenario/", self._datos(wf_tasa_fallo_prev=0),
            format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("wf_tasa_fallo_prev", r.json())
        ayer = planificador.hoy_local() - timedelta(days=1)
        for datos in (self._datos(hora=24), self._datos(fecha=ayer),
                      {"dia": 1, "hora": 9, "es_reintento": False,
                       "tiene_pr": False}):
            self.assertEqual(self.cliente(self.dev).post(
                f"{self.url}/escenario/", datos,
                format="json").status_code, 400, datos)

    def test_no_guarda_nada_ni_cambia_el_analisis_base(self):
        antes = self._conteos()
        guardada = Prediccion.objects.get(pk=self.prediccion["id"])
        variables, prob = dict(guardada.variables), guardada.probabilidad
        self.cliente(self.dev).post(
            f"{self.url}/escenario/",
            self._datos(hora=8, es_reintento=True, tiene_pr=True),
            format="json")
        self.cliente(self.dev).get(f"{self.url}/ventanas/")
        self.assertEqual(self._conteos(), antes)
        guardada.refresh_from_db()
        self.assertEqual(guardada.variables, variables)
        self.assertEqual(guardada.probabilidad, prob)

    def _ventanas(self, hoy_local, consulta=""):
        with _ahora(hoy_local):
            r = self.cliente(self.dev).get(f"{self.url}/ventanas/{consulta}")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_ventanas_desde_manana_en_orden_cronologico(self):
        for hoy, esperadas in (
                (datetime(2026, 11, 18, 10, 0), ["2026-11-19", "2026-11-20",
                                                 "2026-11-21"]),
                (datetime(2026, 11, 22, 23, 30), ["2026-11-23", "2026-11-24",
                                                  "2026-11-25"])):
            with self.subTest(hoy=hoy):
                cuerpo = self._ventanas(hoy)
                ventanas = cuerpo["ventanas"]
                self.assertEqual([v["fecha"] for v in ventanas], esperadas)
                self.assertEqual(cuerpo["desde"], esperadas[0])
                for v in ventanas:
                    momento = datetime.fromisoformat(v["momento_local"])
                    self.assertTrue(7 <= v["hora"] <= 20)
                    self.assertEqual((momento.hour, momento.minute),
                                     (v["hora"], 0))
                    self.assertEqual(momento.date().isoformat(), v["fecha"])
                    self.assertEqual(v["dia"], momento.weekday())
                    self.assertIn(v["nivel"], ["bajo", "medio", "alto"])

    def test_mejor_opcion_es_la_de_menor_riesgo(self):
        ventanas = self._ventanas(datetime(2026, 11, 18, 10, 0))["ventanas"]
        mejores = [v for v in ventanas if v["mejor"]]
        self.assertEqual(len(mejores), 1)
        self.assertEqual(mejores[0]["probabilidad"],
                         min(v["probabilidad"] for v in ventanas))

    def test_diferencia_con_el_analisis_base_y_factores_principales(self):
        cuerpo = self._ventanas(datetime(2026, 11, 18, 10, 0))
        base = cuerpo["base"]
        self.assertAlmostEqual(base["probabilidad"],
                               self.prediccion["probabilidad"], places=12)
        self.assertEqual(base["nivel"], self.prediccion["nivel"])
        for v in cuerpo["ventanas"]:
            self.assertAlmostEqual(
                v["diferencia_puntos"],
                (v["probabilidad"] - base["probabilidad"]) * 100, places=1)
        factores = cuerpo["factores_base"]
        self.assertEqual(len(factores), 3)
        self.assertEqual(len({f["variable"] for f in factores}), 3)
        self.assertTrue(all(f["descripcion"] for f in factores))
        # Primero las que suben el riesgo, de mayor a menor peso.
        positivas = [f["contribucion"] for f in factores
                     if f["contribucion"] > 0]
        self.assertEqual(positivas, sorted(positivas, reverse=True))
        self.assertEqual(factores[:len(positivas)],
                         [f for f in factores if f["contribucion"] > 0])

    def test_cada_ventana_es_la_hora_de_menor_riesgo_del_dia(self):
        ventanas = self._ventanas(datetime(2026, 11, 18, 10, 0))["ventanas"]
        primera = ventanas[0]
        fecha = date.fromisoformat(primera["fecha"])
        with _ahora(datetime(2026, 11, 18, 10, 0)):
            probs = [self.cliente(self.dev).post(
                f"{self.url}/escenario/", self._datos(fecha=fecha, hora=h),
                format="json").json()["escenario"]["probabilidad"]
                for h in range(7, 21)]
        self.assertAlmostEqual(primera["probabilidad"], min(probs), places=12)

    def test_numero_de_dias_configurable(self):
        hoy = datetime(2026, 11, 18, 10, 0)
        self.assertEqual(len(self._ventanas(hoy)["ventanas"]), 3)
        self.assertEqual(len(self._ventanas(hoy, "?dias=5")["ventanas"]), 5)
        with override_settings(PLANIFICADOR_DIAS_VENTANAS=2):
            self.assertEqual(len(self._ventanas(hoy)["ventanas"]), 2)
        for malo in ("0", "15", "x"):
            self.assertEqual(self.cliente(self.dev).get(
                f"{self.url}/ventanas/?dias={malo}").status_code, 400)

    def test_otro_desarrollador_no_ve_el_analisis(self):
        self.assertEqual(self.cliente(self.dev2).post(
            f"{self.url}/escenario/", self._datos(),
            format="json").status_code, 404)
        self.assertEqual(self.cliente(self.dev2).get(
            f"{self.url}/ventanas/").status_code, 404)


class VocabularioTest(SimpleTestCase):
    """El planificador estima escenarios; no usa la palabra prohibida."""

    def test_sin_palabra_prohibida(self):
        raiz = Path(settings.BASE_DIR).parent
        archivos = [
            raiz / "backend/riesgo/services/planificador.py",
            raiz / "frontend/src/components/Planificador.jsx",
            raiz / "frontend/src/planificador.js",
            raiz / "frontend/src/roles.js",
            raiz / "frontend/src/api.js",
        ]
        prohibida = "simul" + "a"
        for archivo in archivos:
            with self.subTest(archivo=archivo.name):
                self.assertNotIn(prohibida,
                                 archivo.read_text(encoding="utf-8").lower())
