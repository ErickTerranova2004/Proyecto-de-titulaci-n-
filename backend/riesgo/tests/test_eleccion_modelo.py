"""Elección del modelo en cada análisis (Random Forest o XGBoost, ambos del
dataset v2): todo el análisis sale del modelo elegido; «Comparar ambos» crea
los dos sin que ninguno sea oficial hasta que el autor elige uno."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from riesgo.models import DecisionDespliegue, Prediccion, VersionModelo
from riesgo.services import informes, predictor, supervision
from riesgo.tests import test_api
from riesgo.tests.test_api import DATOS


@override_settings(GEMINI_API_KEY="")
class EleccionModeloTest(TestCase):
    cliente = test_api.ApiTest.cliente
    predecir = test_api.ApiTest.predecir
    _usuario = test_api.ApiTest._usuario

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)
        call_command("registrar_modelo", "--modelo", "v2-xgb", "--sin-activar",
                     stdout=StringIO())
        cls.rf = VersionModelo.objects.get(version="v2")
        cls.xgb = VersionModelo.objects.get(version="v2-xgb")

    def analizar(self, modelo=None, usuario=None, **extra):
        datos = dict(DATOS, **extra)
        if modelo is not None:
            datos["modelo"] = modelo
        return self.predecir(usuario or self.dev, datos)

    # --- Un modelo -----------------------------------------------------------

    def test_por_defecto_el_principal(self):
        r = self.analizar()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual((r.json()["version_modelo"], r.json()["modelo_nombre"]),
                         ("v2", "Random Forest"))

    def test_todo_el_analisis_sale_del_modelo_elegido(self):
        r = self.analizar("v2-xgb")
        self.assertEqual(r.status_code, 201, r.content)
        datos = r.json()
        self.assertEqual((datos["version_modelo"], datos["modelo_nombre"]),
                         ("v2-xgb", "XGBoost"))
        p = Prediccion.objects.get(id=datos["id"])
        esperado = predictor.predecir(p.variables, self.xgb)
        self.assertAlmostEqual(p.probabilidad, esperado["probabilidad"])
        self.assertEqual(p.nivel, predictor.nivel_de(
            p.probabilidad, self.xgb.metadatos["limites_riesgo"]))
        self.assertEqual(p.recomendacion, predictor.recomendacion_de(p.nivel))
        self.assertEqual(p.factores, esperado["factores"])
        self.assertNotAlmostEqual(
            p.probabilidad, predictor.predecir(p.variables, self.rf)["probabilidad"])
        # El texto (IA o reglas) también se redactó con este resultado.
        self.assertTrue(p.recomendaciones)
        # Es un análisis normal: lo ve el líder y puede decidir.
        self.assertEqual(p.est_registro, "A")
        r = self.cliente(self.lider).post(
            f"/api/predicciones/{p.id}/decision/",
            {"decision": "autorizar"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)

    def test_modelo_no_disponible(self):
        VersionModelo.objects.filter(version="v2-xgb").update(est_registro="I")
        for modelo in ("v2-xgb", "v1", "otro"):
            with self.subTest(modelo=modelo):
                r = self.analizar(modelo)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.json()["codigo"], "modelo_no_disponible")
        self.assertEqual(self.analizar("comparar").json()["codigo"],
                         "modelo_no_disponible")

    # --- Comparar ambos ----------------------------------------------------------

    def comparar(self, **extra):
        r = self.analizar("comparar", **extra)
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["comparacion"]

    def test_comparar_crea_los_dos_sin_oficial(self):
        rf, xgb = self.comparar()
        self.assertEqual([rf["version_modelo"], xgb["version_modelo"]],
                         ["v2", "v2-xgb"])
        self.assertEqual(rf["variables"], xgb["variables"])
        filas = Prediccion.objects.filter(id__in=[rf["id"], xgb["id"]])
        self.assertEqual(set(filas.values_list("est_registro", flat=True)), {"I"})
        self.assertEqual(Prediccion.objects.get(id=xgb["id"]).prediccion_base_id,
                         rf["id"])
        # Ninguno sale en historiales ni lo puede decidir el líder.
        for usuario in (self.dev, self.lider):
            ids = [p["id"] for p in self.cliente(usuario).get(
                "/api/predicciones/").json()]
            self.assertNotIn(rf["id"], ids)
            self.assertNotIn(xgb["id"], ids)
        self.assertEqual(self.cliente(self.lider).post(
            f"/api/predicciones/{rf['id']}/decision/",
            {"decision": "autorizar"}, format="json").status_code, 404)

    def test_elegir_el_oficial(self):
        rf, xgb = self.comparar()
        url = f"/api/predicciones/{xgb['id']}/oficial/"
        # Solo el autor.
        self.assertEqual(self.cliente(self.dev2).post(url).status_code, 404)
        r = self.cliente(self.dev).post(url)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["version_modelo"], "v2-xgb")
        self.assertEqual(Prediccion.objects.get(id=xgb["id"]).est_registro, "A")
        self.assertEqual(Prediccion.objects.get(id=rf["id"]).est_registro, "I")
        ids = [p["id"] for p in self.cliente(self.lider).get(
            "/api/predicciones/").json()]
        self.assertIn(xgb["id"], ids)
        self.assertNotIn(rf["id"], ids)
        # Solo se elige una vez.
        r = self.cliente(self.dev).post(f"/api/predicciones/{rf['id']}/oficial/")
        self.assertEqual(r.status_code, 409)

    def test_oficial_solo_para_comparaciones(self):
        p = self.analizar("v2").json()
        r = self.cliente(self.dev).post(f"/api/predicciones/{p['id']}/oficial/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["codigo"], "sin_comparacion")
        self.assertEqual(self.cliente(self.dev).post(
            "/api/predicciones/999999/oficial/").status_code, 404)

    def test_comparar_y_atender_una_asignacion(self):
        original = self.analizar("v2").json()
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        r = self.cliente(self.lider).post(
            f"/api/predicciones/{original['id']}/decision/",
            {"decision": "solicitar_revision", "fecha_limite": manana},
            format="json")
        self.assertEqual(r.status_code, 201, r.content)
        asignacion = DecisionDespliegue.objects.get(prediccion_id=original["id"])
        extra = {"atiende_decision": asignacion.id,
                 "respuesta_desarrollador": "Se corrigió el despliegue."}
        rf, xgb = self.comparar(**extra)
        # La respuesta se registra al elegir el oficial, no antes.
        asignacion.refresh_from_db()
        self.assertIsNone(asignacion.prediccion_respuesta_id)
        r = self.cliente(self.dev).post(
            f"/api/predicciones/{rf['id']}/oficial/", extra, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        asignacion.refresh_from_db()
        self.assertEqual(asignacion.prediccion_respuesta_id, rf["id"])

    def test_los_no_elegidos_no_cuentan_en_la_supervision(self):
        rf, xgb = self.comparar()
        self.cliente(self.dev).post(f"/api/predicciones/{rf['id']}/oficial/")
        todas, _, _, _ = supervision.posteriores_al_corte(self.xgb)
        self.assertFalse(todas.filter(id=xgb["id"]).exists())
        todas, _, _, _ = supervision.posteriores_al_corte(self.rf)
        self.assertTrue(todas.filter(id=rf["id"]).exists())

    # --- Historiales, planificador e informes --------------------------------

    def test_filtro_modelo_en_los_historiales(self):
        a = self.analizar("v2").json()["id"]
        b = self.analizar("v2-xgb").json()["id"]
        for modelo, esperado in (("v2", a), ("v2-xgb", b)):
            ids = [p["id"] for p in self.cliente(self.lider).get(
                f"/api/predicciones/?modelo={modelo}").json()]
            self.assertIn(esperado, ids)
            self.assertNotIn(b if esperado == a else a, ids)

    def test_planificador_con_otro_modelo(self):
        p = self.analizar("v2").json()
        url = f"/api/predicciones/{p['id']}/ventanas/"
        datos = self.cliente(self.dev).get(url).json()
        self.assertEqual(datos["modelo"], {"version": "v2",
                                           "nombre": "Random Forest"})
        self.assertAlmostEqual(datos["base"]["probabilidad"], p["probabilidad"])
        datos = self.cliente(self.dev).get(f"{url}?modelo=v2-xgb").json()
        self.assertEqual(datos["modelo"]["version"], "v2-xgb")
        variables = Prediccion.objects.get(id=p["id"]).variables
        self.assertAlmostEqual(datos["base"]["probabilidad"],
                               predictor.probabilidades([variables], self.xgb)[0])
        r = self.cliente(self.dev).get(f"{url}?modelo=v1")
        self.assertEqual(r.status_code, 400)

    def test_informe_con_modelos_distintos(self):
        original = Prediccion.objects.get(id=self.analizar("v2").json()["id"])
        nueva = Prediccion.objects.get(id=self.analizar("v2-xgb").json()["id"])
        factores = informes.factores_cambio(original, nueva)
        # Mismas variables y mismo modelo para los dos (el del nuevo): nada
        # cambia, en lugar de restar SHAP de escalas distintas.
        self.assertEqual(factores, [])
        datos = informes._analisis(nueva)
        self.assertEqual((datos["version_modelo"], datos["modelo_nombre"]),
                         ("v2-xgb", "XGBoost"))


class FactoresEnProbabilidadTest(TestCase):
    """Los factores SHAP de XGBoost se presentan en puntos de probabilidad,
    como los de Random Forest (no en log-odds)."""

    @classmethod
    def setUpTestData(cls):
        call_command("registrar_modelo", stdout=StringIO())
        call_command("registrar_modelo", "--modelo", "v2-xgb", "--sin-activar",
                     stdout=StringIO())
        cls.xgb = VersionModelo.objects.get(version="v2-xgb")
        cls.rf = VersionModelo.objects.get(version="v2")
        meta = cls.rf.metadatos
        cls.variables = {c: 0 for c in meta["variables_numericas"]}
        cls.variables.update(event="push", wf_n_prev=12, repo_n_prev=40,
                             wf_tasa_fallo_prev=0.25, wf_ultimo_fallo=1,
                             hora_utc=15, dia_semana=2, msg_len=40,
                             msg_lineas=1, wf_horas_desde_ultimo=3.0)

    def base_y_media(self, version):
        _, base, explicador = predictor._modelos(version)
        fila = predictor._filas([self.variables], version.metadatos)
        import numpy as np
        return (float(base.predict_proba(fila)[0, 1]),
                float(np.ravel(explicador.expected_value)[0]), explicador)

    def test_xgboost_en_probabilidad(self):
        contribuciones = predictor.contribuciones(self.variables, self.xgb)
        p, media, explicador = self.base_y_media(self.xgb)
        self.assertEqual(explicador.model_output, "probability")
        # Suman el cambio de probabilidad (como Random Forest), no log-odds.
        self.assertAlmostEqual(sum(contribuciones.values()), p - media, places=4)
        self.assertTrue(all(abs(c) <= 1 for c in contribuciones.values()))
        resultado = predictor.predecir(self.variables, self.xgb)
        self.assertTrue(resultado["factores"])
        for f in resultado["factores"]:
            self.assertEqual(f["efecto"], "aumenta" if f["contribucion"] > 0 else "reduce")

    def test_random_forest_igual_que_antes(self):
        contribuciones = predictor.contribuciones(self.variables, self.rf)
        p, media, explicador = self.base_y_media(self.rf)
        # TreeExplainer exacto de sklearn (float32): suma con error < 0,001.
        self.assertAlmostEqual(sum(contribuciones.values()), p - media, places=3)

    def test_sin_dataset_reparte_el_cambio_de_probabilidad(self):
        import numpy as np
        fila = np.array([0.8, -0.3, 0.1])
        convertida = predictor._log_odds_a_probabilidad(fila, np.array([-2.0]))
        sigmoide = lambda x: 1 / (1 + np.exp(-x))  # noqa: E731
        self.assertAlmostEqual(convertida.sum(), sigmoide(-1.4) - sigmoide(-2.0))
        self.assertEqual(list(np.sign(convertida)), [1, -1, 1])
        self.assertEqual(list(predictor._log_odds_a_probabilidad(
            np.zeros(2), np.array([0.0]))), [0, 0])

    def test_la_ia_recibe_la_escala(self):
        from riesgo.services.analisis_ia import SISTEMA
        self.assertIn("puntos de probabilidad", SISTEMA)
        self.assertIn("No hables de log-odds", SISTEMA)

    def test_tasa_real_por_nivel_en_la_api_de_modelos(self):
        admin = test_api.ApiTest._usuario("admin", "administrador", [])
        modelos = test_api.ApiTest.cliente(self, admin).get("/api/modelos/").json()
        for m in modelos:
            self.assertEqual(set(m["tasa_real_por_nivel"]), {"bajo", "medio", "alto"})
            # Sin despliegues verificados no hay tasa.
            self.assertIsNone(m["tasa_real_por_nivel"]["alto"]["tasa"])


@override_settings(GEMINI_API_KEY="")
class PermisosYDisponibilidadTest(TestCase):
    """Solo el administrador cambia el principal y la disponibilidad; un
    modelo no disponible no se puede usar en análisis ni en el
    Planificador; Random Forest (modelo del lote) siempre está disponible."""

    cliente = test_api.ApiTest.cliente
    predecir = test_api.ApiTest.predecir
    _usuario = test_api.ApiTest._usuario

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)
        call_command("registrar_modelo", "--modelo", "v2-xgb", "--sin-activar",
                     stdout=StringIO())
        cls.rf = VersionModelo.objects.get(version="v2")
        cls.xgb = VersionModelo.objects.get(version="v2-xgb")

    def disponibilidad(self, version, disponible, usuario=None):
        return self.cliente(usuario or self.admin).post(
            f"/api/modelos/{version.id}/disponibilidad/",
            {"disponible": disponible}, format="json")

    def test_solo_el_administrador_cambia_el_principal(self):
        url = f"/api/modelos/{self.xgb.id}/activar/"
        for usuario in (self.dev, self.lider):
            with self.subTest(usuario=usuario.username):
                r = self.cliente(usuario).post(url, {"confirmacion": "v2-xgb"},
                                               format="json")
                self.assertEqual(r.status_code, 403)
        self.assertEqual(VersionModelo.objects.get(activo=True).version, "v2")
        self.assertEqual(self.cliente(self.admin).post(
            url, {"confirmacion": "v2-xgb"}, format="json").status_code, 200)

    def test_solo_el_administrador_cambia_la_disponibilidad(self):
        for usuario in (self.dev, self.lider):
            with self.subTest(usuario=usuario.username):
                self.assertEqual(self.disponibilidad(self.xgb, False, usuario)
                                 .status_code, 403)
        self.assertTrue(VersionModelo.objects.get(id=self.xgb.id).disponible)

    def test_random_forest_y_el_principal_siempre_disponibles(self):
        r = self.disponibilidad(self.rf, False)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "disponibilidad_no_permitida")
        modelos = {m["version"]: m for m in self.cliente(self.admin).get(
            "/api/modelos/").json()}
        self.assertIn("análisis en lote", modelos["v2"]["motivo_siempre_disponible"])
        self.assertIsNone(modelos["v2-xgb"]["motivo_siempre_disponible"])
        # XGBoost principal: tampoco se puede quitar mientras lo sea.
        self.cliente(self.admin).post(f"/api/modelos/{self.xgb.id}/activar/",
                                      {"confirmacion": "v2-xgb"}, format="json")
        self.assertEqual(self.disponibilidad(self.xgb, False).status_code, 400)
        self.assertEqual(self.disponibilidad(self.xgb, "no").status_code, 400)

    def test_no_disponible_se_rechaza_y_queda_registrado(self):
        from riesgo.models import DisponibilidadModelo
        r = self.disponibilidad(self.xgb, False)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(r.json()["disponible"])
        fila = DisponibilidadModelo.objects.get(version_modelo=self.xgb)
        self.assertEqual((fila.disponible, fila.usuario, fila.nombre_usuario,
                          fila.usu_creacion), (False, self.admin, "admin", "admin"))
        self.assertEqual(r.json()["ultimo_cambio_disponibilidad"]["usuario"], "admin")
        # Nuevo análisis: ni XGBoost ni «Comparar ambos».
        for modelo in ("v2-xgb", "comparar"):
            r = self.predecir(self.dev, dict(DATOS, modelo=modelo))
            self.assertEqual(r.status_code, 400, modelo)
            self.assertEqual(r.json()["codigo"], "modelo_no_disponible")
        # Random Forest y el principal por defecto siguen funcionando.
        p = self.predecir(self.dev, DATOS)
        self.assertEqual(p.status_code, 201)
        # Planificador.
        r = self.cliente(self.dev).get(
            f"/api/predicciones/{p.json()['id']}/ventanas/?modelo=v2-xgb")
        self.assertEqual(r.status_code, 400)
        # No se puede hacer principal un modelo no disponible.
        r = self.cliente(self.admin).post(f"/api/modelos/{self.xgb.id}/activar/",
                                          {"confirmacion": "v2-xgb"}, format="json")
        self.assertEqual(r.status_code, 400)
        # Volver a ofrecerlo también queda registrado.
        self.assertEqual(self.disponibilidad(self.xgb, True).status_code, 200)
        self.assertEqual(DisponibilidadModelo.objects.filter(
            version_modelo=self.xgb).count(), 2)
        self.assertEqual(self.predecir(self.dev, dict(DATOS, modelo="v2-xgb"))
                         .status_code, 201)
