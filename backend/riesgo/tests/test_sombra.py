"""Evaluación en sombra de v1 y v1.1 sobre las ejecuciones evaluables de la
supervisión de v2 (riesgo/services/sombra.py y supervision.comparacion)."""

from datetime import datetime, timezone
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from riesgo.models import (Commit, EjecucionWorkflow, Prediccion, Repositorio,
                           VersionModelo, Workflow)
from riesgo.services import predictor, sombra, supervision
from riesgo.tests import test_api


def momento(dia, hora=12):
    return datetime(2026, 11, dia, hora, tzinfo=timezone.utc)


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        # v1 y v1.1 registradas pero no activas; v2 activa (la última).
        for modelo in ("v1", "v1.1", "v2"):
            call_command("registrar_modelo", "--modelo", modelo,
                         stdout=StringIO())
        cls.v2 = VersionModelo.objects.get(activo=True)
        cls.v1 = VersionModelo.objects.get(version="v1")
        cls.v11 = VersionModelo.objects.get(version="v1.1")
        cls.lote = User.objects.create_user("analisis_lote")
        cls.repo = Repositorio.objects.create(
            nombre_completo="acme/tienda", propietario="acme", nombre="tienda")
        cls.workflow = Workflow.objects.create(
            repositorio=cls.repo, path=".github/workflows/deploy.yml",
            despliegue_validado=True, evidencia_validacion="prueba")
        meta = cls.v2.metadatos
        # Variables como las guarda v2: con rama_bot (la calcula aunque v2 no
        # la use) y sin reejecutado_por_otro.
        cls.variables = {c: 0 for c in meta["variables_numericas"]}
        cls.variables.update(event="push", wf_n_prev=12, repo_n_prev=40,
                             wf_tasa_fallo_prev=0.25, hora_utc=15,
                             dia_semana=2, msg_len=40, msg_lineas=1,
                             wf_horas_desde_ultimo=None, rama_bot=0)
        cls.variables.pop("reejecutado_por_otro", None)

    def prediccion(self, etiqueta="despliegue_no_completado", inicio=None,
                   repo=None, origen="lote", variables=None):
        repo = repo or self.repo
        workflow = self.workflow if repo == self.repo else Workflow.objects.create(
            repositorio=repo, path=".github/workflows/deploy.yml",
            despliegue_validado=True, evidencia_validacion="prueba")
        inicio = inicio or momento(12)
        n = Commit.objects.count()
        commit = Commit.objects.create(repositorio=repo, sha=f"{n:040d}")
        ejecucion = EjecucionWorkflow.objects.create(
            workflow=workflow, commit=commit, run_id=5000 + n,
            iniciada_en=inicio, extraida_en=inicio, etiqueta=etiqueta)
        return Prediccion.objects.create(
            usuario=self.lote, workflow=workflow, commit=commit,
            version_modelo=self.v2, evento="push",
            variables=variables or dict(self.variables), probabilidad=0.3,
            nivel="alto", factores=[], recomendaciones=[], origen=origen,
            ejecucion_real=ejecucion, momento_variables=inicio,
            verificada_en=inicio, datos_github_extraidos_en=inicio)


class VariablesTest(Base):
    def test_rellena_con_la_mediana_solo_las_que_no_existen(self):
        medianas = sombra.medianas(self.v1)
        self.assertIn("reejecutado_por_otro", medianas)
        completas, rellenadas = sombra.variables_para(self.v1, self.variables)
        self.assertEqual(rellenadas, ["reejecutado_por_otro"])
        self.assertEqual(completas["reejecutado_por_otro"],
                         medianas["reejecutado_por_otro"])
        # Un nulo guardado (sin historial) se respeta: lo imputa el modelo.
        self.assertIsNone(completas["wf_horas_desde_ultimo"])
        self.assertEqual(completas["wf_tasa_fallo_prev"], 0.25)
        # Las medianas son las del imputador de cada modelo.
        self.assertEqual(set(medianas), set(
            self.v1.metadatos["variables_numericas"]))


class GenerarTest(Base):
    def test_predice_las_mismas_ejecuciones_evaluables_de_v2(self):
        evaluable = self.prediccion()
        completado = self.prediccion("despliegue_completado", momento(13))
        self.prediccion("excluida_sin_intento", momento(14))       # no evaluable
        self.prediccion(inicio=momento(1))                          # antes del corte
        demo = Repositorio.objects.create(
            nombre_completo="demo/app", propietario="demo", nombre="app",
            es_demostracion=True)
        self.prediccion(repo=demo)                                  # demostración

        resumen = sombra.generar(self.lote)
        self.assertEqual(resumen["v1"]["creadas"], 2)
        self.assertEqual(resumen["v1.1"]["creadas"], 2)
        self.assertEqual(resumen["v1"]["rellenadas"], ["reejecutado_por_otro"])
        sombras = Prediccion.con_sombra.filter(origen="sombra")
        self.assertEqual(sombras.count(), 4)
        self.assertEqual(
            set(sombras.values_list("prediccion_base_id", flat=True)),
            {evaluable.id, completado.id})
        for s in sombras.select_related("prediccion_base", "version_modelo"):
            base = s.prediccion_base
            self.assertEqual(s.ejecucion_real_id, base.ejecucion_real_id)
            self.assertEqual(s.commit_id, base.commit_id)
            esperada = predictor.probabilidades(
                [sombra.variables_para(s.version_modelo, base.variables)[0]],
                s.version_modelo)[0]
            self.assertAlmostEqual(s.probabilidad, esperada)
            self.assertEqual(s.nivel, predictor.nivel_de(
                esperada, s.version_modelo.metadatos["limites_riesgo"]))
            s.clean()
        # Repetir no duplica.
        self.assertEqual(sombra.generar(self.lote)["v1"]["creadas"], 0)
        self.assertEqual(sombras.count(), 4)

    def test_comando_contar_no_guarda(self):
        self.prediccion()
        salida = StringIO()
        call_command("evaluar_sombra", "--contar", stdout=salida)
        self.assertIn("Sombra v1: 1 por crear", salida.getvalue())
        self.assertFalse(Prediccion.con_sombra.filter(origen="sombra").exists())
        call_command("evaluar_sombra", stdout=StringIO())
        self.assertEqual(
            Prediccion.con_sombra.filter(origen="sombra").count(), 2)


class FueraDeLaPlataformaTest(Base):
    """Las predicciones en sombra no son análisis de usuarios."""

    def test_no_aparecen_en_historiales_dashboards_ni_supervision(self):
        base = self.prediccion()
        sombra.generar(self.lote)
        self.assertEqual(Prediccion.con_sombra.count(), 3)
        self.assertEqual(list(Prediccion.objects.values_list("id", flat=True)),
                         [base.id])
        admin = test_api.ApiTest._usuario("admin", "administrador", [])
        api = test_api.ApiTest.cliente(self, admin)
        self.assertEqual([p["id"] for p in api.get("/api/predicciones/").json()],
                         [base.id])
        # La supervisión de v2 (activo) no las cuenta; la de una versión no
        # activa las suma (no hace análisis nuevos) y lo indica aparte.
        datos = api.get(f"/api/modelos/{self.v2.id}/supervision/").json()
        self.assertEqual((datos["predicciones"], datos["predicciones_sombra"]),
                         (1, 0))
        for version in (self.v1, self.v11):
            datos = api.get(f"/api/modelos/{version.id}/supervision/").json()
            self.assertEqual(datos["predicciones"], 1)
            self.assertEqual(datos["predicciones_sombra"], 1)
            self.assertEqual(datos["verificadas"], 1)
            self.assertEqual(datos["evaluables"], 1)
            self.assertEqual(datos["por_nivel"][Prediccion.con_sombra.get(
                origen="sombra", version_modelo=version).nivel]
                ["no_completados"], 1)
            self.assertIsNotNone(datos["brier"])
        workflows = api.get("/api/gestion/workflows/").json()["workflows"]
        self.assertEqual(workflows[0]["predicciones"], 1)
        usuarios = {u["usuario"]: u for u in api.get(
            "/api/gestion/usuarios/").json()["usuarios"]}
        self.assertEqual(usuarios["analisis_lote"]["analisis"], 1)


class ComparacionTest(Base):
    def test_mismas_ejecuciones_para_los_tres_modelos(self):
        for i in range(6):
            self.prediccion("despliegue_no_completado" if i % 2 else
                            "despliegue_completado", momento(12, i))
        sombra.generar(self.lote)
        # Una evaluable nueva sin sombra todavía: no entra en la comparación.
        self.prediccion(inicio=momento(13))
        admin = test_api.ApiTest._usuario("admin", "administrador", [])
        r = test_api.ApiTest.cliente(self, admin).get(
            "/api/modelos/comparacion-sombra/")
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertEqual(datos["referencia"], "v2")
        self.assertEqual(datos["ejecuciones"], 6)
        self.assertEqual(datos["no_completados"], 3)
        self.assertEqual(datos["sin_sombra"], 1)
        self.assertEqual([m["version"] for m in datos["modelos"]],
                         ["v2", "v1.1", "v1"])
        self.assertEqual([m["en_sombra"] for m in datos["modelos"]],
                         [False, True, True])
        for m in datos["modelos"]:
            self.assertEqual(sum(n["evaluables"] for n in m["por_nivel"].values()), 6)
            self.assertEqual(
                sum(n["no_completados"] for n in m["por_nivel"].values()), 3)
            self.assertIsNotNone(m["brier"]["valor"])
            self.assertEqual(len(m["brier"]["ic95"]), 2)
            self.assertIsNotNone(m["pr_auc"]["valor"])
        self.assertIn("diferencia_con_referencia", datos["modelos"][1])
        self.assertNotIn("diferencia_con_referencia", datos["modelos"][0])

    def test_solo_administrador(self):
        dev = test_api.ApiTest._usuario("dev", "desarrollador", [self.repo])
        r = test_api.ApiTest.cliente(self, dev).get(
            "/api/modelos/comparacion-sombra/")
        self.assertEqual(r.status_code, 403)


class MetricasTest(SimpleTestCase):
    def test_wilson(self):
        bajo, alto = supervision.wilson(5, 10)
        self.assertAlmostEqual(bajo, 0.2366, places=3)
        self.assertAlmostEqual(alto, 0.7634, places=3)
        self.assertIsNone(supervision.wilson(0, 0))

    def test_diferencia_pareada_con_la_referencia(self):
        y = [0, 1, 0, 1, 1, 0, 0, 1]
        p = [0.1, 0.8, 0.2, 0.7, 0.9, 0.3, 0.2, 0.6]
        r = supervision.metricas_pareadas(y, {"v2": p, "v1": p}, "v2")
        self.assertEqual(r["v1"]["diferencia_con_referencia"]["brier"],
                         {"valor": 0.0, "ic95": [0.0, 0.0]})
        self.assertAlmostEqual(r["v2"]["pr_auc"]["valor"], 1.0)
        bajo, alto = r["v2"]["brier"]["ic95"]
        self.assertLessEqual(bajo, r["v2"]["brier"]["valor"])
        self.assertGreaterEqual(alto, r["v2"]["brier"]["valor"])


class VersionOcultaTest(Base):
    """v1.1 oculta (est_registro = 'I', migración 0022): no sale en ninguna
    pantalla, pero sus filas y predicciones se conservan."""

    def setUp(self):
        VersionModelo.objects.filter(id=self.v11.id).update(est_registro="I")
        admin = test_api.ApiTest._usuario("admin", "administrador", [])
        self.api = test_api.ApiTest.cliente(self, admin)

    def test_no_sale_en_la_lista_ni_se_puede_activar_ni_supervisar(self):
        versiones = [m["version"] for m in self.api.get("/api/modelos/").json()]
        self.assertEqual(sorted(versiones), ["v1", "v2"])
        self.assertEqual(self.api.post(
            f"/api/modelos/{self.v11.id}/activar/").status_code, 404)
        self.assertEqual(self.api.get(
            f"/api/modelos/{self.v11.id}/supervision/").status_code, 404)
        self.assertTrue(VersionModelo.objects.get(id=self.v11.id).activo is False)

    def test_comparacion_y_sombra_sin_la_version_oculta(self):
        self.prediccion()
        resumen = sombra.generar(self.lote)
        self.assertEqual(list(resumen), ["v1"])
        datos = self.api.get("/api/modelos/comparacion-sombra/").json()
        self.assertEqual([m["version"] for m in datos["modelos"]], ["v2", "v1"])
        self.assertEqual(datos["ejecuciones"], 1)

    def test_la_migracion_solo_oculta_v1_1(self):
        from importlib import import_module
        from django.apps import apps
        VersionModelo.objects.update(est_registro="A")
        migracion = import_module("riesgo.migrations.0022_ocultar_v1_1")
        migracion.estado("I")(apps, None)
        self.assertEqual(
            dict(VersionModelo.objects.values_list("version", "est_registro")),
            {"v1": "A", "v1.1": "I", "v2": "A"})
        migracion.estado("A")(apps, None)
        self.assertFalse(VersionModelo.objects.filter(est_registro="I").exists())


class V1OcultaTest(Base):
    """v1 oculta (migración 0029): fuera de Modelos, supervisión,
    comparación y selectores, y el lote ya no la evalúa en sombra."""

    def setUp(self):
        VersionModelo.objects.filter(id__in=[self.v1.id, self.v11.id]).update(
            est_registro="I")
        admin = test_api.ApiTest._usuario("admin", "administrador", [])
        self.api = test_api.ApiTest.cliente(self, admin)

    def test_no_sale_ni_se_evalua_en_sombra(self):
        self.assertEqual([m["version"] for m in self.api.get("/api/modelos/").json()],
                         ["v2"])
        self.assertEqual(self.api.get(
            f"/api/modelos/{self.v1.id}/supervision/").status_code, 404)
        self.prediccion()
        self.assertEqual(sombra.generar(self.lote), {})
        self.assertFalse(Prediccion.con_sombra.filter(
            origen="sombra", version_modelo=self.v1).exists())
        datos = self.api.get("/api/modelos/comparacion-sombra/").json()
        self.assertEqual([m["version"] for m in datos["modelos"]], ["v2"])
        # Las filas se conservan.
        self.assertTrue(VersionModelo.objects.filter(id=self.v1.id).exists())

    def test_la_migracion_solo_oculta_v1(self):
        from importlib import import_module
        from django.apps import apps
        VersionModelo.objects.update(est_registro="A")
        migracion = import_module("riesgo.migrations.0029_ocultar_v1")
        migracion.estado("I")(apps, None)
        self.assertEqual(
            dict(VersionModelo.objects.values_list("version", "est_registro")),
            {"v1": "I", "v1.1": "A", "v2": "A"})
        migracion.estado("A")(apps, None)
        self.assertFalse(VersionModelo.objects.filter(est_registro="I").exists())


class XGBoostEnSombraTest(Base):
    """Configuración actual: v1 y v1.1 ocultas, Random Forest (v2) principal
    y XGBoost (v2-xgb) alternativo en sombra sobre las mismas ejecuciones."""

    def setUp(self):
        VersionModelo.objects.filter(id__in=[self.v1.id, self.v11.id]).update(
            est_registro="I")
        call_command("registrar_modelo", "--modelo", "v2-xgb", "--sin-activar",
                     stdout=StringIO())
        self.xgb = VersionModelo.objects.get(version="v2-xgb")
        admin = test_api.ApiTest._usuario("admin", "administrador", [])
        self.api = test_api.ApiTest.cliente(self, admin)

    def test_sombra_con_las_variables_guardadas_y_comparacion(self):
        predicciones = [self.prediccion("despliegue_no_completado" if i % 2 else
                                        "despliegue_completado", momento(12, i))
                        for i in range(6)]
        resumen = sombra.generar(self.lote)
        self.assertEqual(list(resumen), ["v2-xgb"])
        self.assertEqual(resumen["v2-xgb"]["creadas"], 6)
        # Mismas variables que v2: no hace falta rellenar ninguna.
        self.assertEqual(resumen["v2-xgb"]["rellenadas"], [])
        filas = Prediccion.con_sombra.filter(origen="sombra",
                                             version_modelo=self.xgb)
        for p in predicciones:
            s = filas.get(prediccion_base=p)
            self.assertEqual(s.variables, p.variables)
            self.assertAlmostEqual(
                s.probabilidad, predictor.probabilidades([p.variables], self.xgb)[0])
            self.assertEqual(s.ejecucion_real_id, p.ejecucion_real_id)
        # Una segunda pasada no duplica.
        self.assertEqual(sombra.generar(self.lote)["v2-xgb"]["creadas"], 0)
        datos = self.api.get("/api/modelos/comparacion-sombra/").json()
        self.assertEqual([(m["version"], m["nombre_modelo"], m["en_sombra"])
                          for m in datos["modelos"]],
                         [("v2", "Random Forest", False),
                          ("v2-xgb", "XGBoost", True)])
        self.assertEqual(datos["ejecuciones"], 6)
        self.assertIn("diferencia_con_referencia", datos["modelos"][1])

    def test_supervision_de_los_dos(self):
        self.prediccion()
        sombra.generar(self.lote)
        modelos = self.api.get("/api/modelos/").json()
        self.assertEqual([m["version"] for m in modelos], ["v2-xgb", "v2"])
        for m in modelos:
            datos = self.api.get(f"/api/modelos/{m['id']}/supervision/").json()
            self.assertEqual(datos["evaluables"], 1, m["version"])
        datos = self.api.get(f"/api/modelos/{self.xgb.id}/supervision/").json()
        self.assertEqual(datos["predicciones_sombra"], 1)
