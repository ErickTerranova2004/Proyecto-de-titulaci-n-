"""Activación de versiones del modelo (services/modelos.py): solo con fecha
de corte, con confirmación escribiendo el nombre y con historial en
trx_activacion_modelo; aviso en el panel del administrador."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from riesgo.models import ActivacionModelo, VersionModelo
from riesgo.tests import test_api


@override_settings(GEMINI_API_KEY="")
class ActivacionModeloTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # v1 (sin fecha de corte) registrada antes; v2 activa.
        for modelo in ("v1", "v2"):
            call_command("registrar_modelo", "--modelo", modelo,
                         stdout=StringIO())
        cls.v1 = VersionModelo.objects.get(version="v1")
        cls.v2 = VersionModelo.objects.get(version="v2")
        cls.admin = test_api.ApiTest._usuario("admin", "administrador", [])
        cls.dev = test_api.ApiTest._usuario("dev", "desarrollador", [])

    def setUp(self):
        self.api = test_api.ApiTest.cliente(self, self.admin)

    def copia(self, version, corte):
        return VersionModelo.objects.create(
            version=version, nombre_modelo="Copia", archivo=self.v2.archivo,
            archivo_explicacion=self.v2.archivo_explicacion,
            metadatos={**self.v2.metadatos, "fecha_corte": corte})

    def activar(self, version, confirmacion=None):
        datos = {} if confirmacion is None else {"confirmacion": confirmacion}
        return self.api.post(f"/api/modelos/{version.id}/activar/", datos,
                             format="json")

    def activo(self):
        return VersionModelo.objects.get(activo=True).version

    def test_lista_indica_que_versiones_se_pueden_activar(self):
        modelos = {m["version"]: m for m in self.api.get("/api/modelos/").json()}
        self.assertTrue(modelos["v2"]["activable"])
        self.assertIsNone(modelos["v2"]["motivo_no_activable"])
        self.assertFalse(modelos["v1"]["activable"])
        self.assertIn("fecha de corte", modelos["v1"]["motivo_no_activable"])

    def test_no_se_activa_una_version_sin_fecha_de_corte(self):
        r = self.activar(self.v1, "v1")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "version_no_activable")
        self.assertEqual(self.activo(), "v2")
        self.assertFalse(ActivacionModelo.objects.filter(
            origen="plataforma").exists())

    def test_exige_escribir_el_nombre_de_la_version(self):
        nueva = self.copia("v3", "2026-11-20T00:00:00Z")
        for confirmacion in (None, "", "v2", "V3 "):
            with self.subTest(confirmacion=confirmacion):
                r = self.activar(nueva, confirmacion)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.json()["codigo"], "confirmacion_incorrecta")
                self.assertEqual(self.activo(), "v2")
        self.assertEqual(self.activar(nueva, " v3 ").status_code, 200)
        self.assertEqual(self.activo(), "v3")

    def test_registra_quien_y_cuando_en_el_historial(self):
        nueva = self.copia("v3", "2026-11-20T00:00:00Z")
        r = self.activar(nueva, "v3")
        self.assertEqual(r.status_code, 200)
        fila = ActivacionModelo.objects.get(origen="plataforma")
        self.assertEqual((fila.version_modelo, fila.version_anterior,
                          fila.usuario, fila.nombre_usuario),
                         (nueva, self.v2, self.admin, "admin"))
        self.assertIsNotNone(fila.activado_en)
        self.assertEqual(fila.usu_creacion, "admin")
        ultima = r.json()["ultima_activacion"]
        self.assertEqual((ultima["usuario"], ultima["origen"]),
                         ("admin", "plataforma"))

    def test_la_version_activa_no_se_vuelve_a_activar(self):
        r = self.activar(self.v2, "v2")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "ya_activa")

    def test_solo_el_administrador(self):
        nueva = self.copia("v3", "2026-11-20T00:00:00Z")
        r = test_api.ApiTest.cliente(self, self.dev).post(
            f"/api/modelos/{nueva.id}/activar/", {"confirmacion": "v3"},
            format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.activo(), "v2")

    def test_registrar_modelo_deja_constancia(self):
        filas = ActivacionModelo.objects.filter(origen="comando").order_by("id")
        self.assertEqual([(f.version_modelo.version,
                           f.version_anterior and f.version_anterior.version)
                          for f in filas], [("v1", None), ("v2", "v1")])

    def test_aviso_del_panel_si_el_activo_no_es_el_mas_reciente(self):
        estado = self.api.get("/api/resumen-admin/").json()["modelo"]
        self.assertEqual(estado, {"activo": "v2", "recomendado": "v2",
                                  "aviso": False, "activo_sin_corte": False})
        antigua = self.copia("v0", "2026-10-01T00:00:00Z")
        self.assertEqual(self.activar(antigua, "v0").status_code, 200)
        estado = self.api.get("/api/resumen-admin/").json()["modelo"]
        self.assertEqual(estado, {"activo": "v0", "recomendado": "v2",
                                  "aviso": True, "activo_sin_corte": False})
        # v1 activo (p. ej. por un comando): también avisa.
        VersionModelo.objects.update(activo=False)
        VersionModelo.objects.filter(id=self.v1.id).update(activo=True)
        estado = self.api.get("/api/resumen-admin/").json()["modelo"]
        self.assertEqual((estado["activo"], estado["aviso"],
                          estado["activo_sin_corte"]), ("v1", True, True))


@override_settings(GEMINI_API_KEY="")
class XGBoostAlternativoTest(TestCase):
    """Random Forest (v2, principal) y XGBoost (v2-xgb, alternativo),
    entrenados con el mismo dataset v2 y la misma fecha de corte."""

    @classmethod
    def setUpTestData(cls):
        call_command("registrar_modelo", stdout=StringIO())
        call_command("registrar_modelo", "--modelo", "v2-xgb", "--sin-activar",
                     stdout=StringIO())
        cls.rf = VersionModelo.objects.get(version="v2")
        cls.xgb = VersionModelo.objects.get(version="v2-xgb")
        cls.admin = test_api.ApiTest._usuario("admin", "administrador", [])

    def setUp(self):
        self.api = test_api.ApiTest.cliente(self, self.admin)

    def test_registro_sin_activar_con_sus_archivos_y_metadatos(self):
        self.assertTrue(self.rf.activo)
        self.assertFalse(self.xgb.activo)
        self.assertEqual(self.xgb.nombre_modelo, "XGBoost")
        self.assertEqual((self.xgb.archivo, self.xgb.archivo_explicacion),
                         ("modelo_riesgo_v2_xgb.joblib",
                          "modelo_riesgo_v2_xgb_shap.joblib"))
        meta, rf = self.xgb.metadatos, self.rf.metadatos
        for clave in ("fecha_corte", "variables_numericas",
                      "variables_categoricas", "dataset_sha256",
                      "limites_riesgo"):
            self.assertEqual(meta[clave], rf[clave], clave)
        self.assertEqual(meta["escala_shap"], "log-odds")
        self.assertIn("XGBoost", meta["metricas_validacion"])
        # Registrarlo no cuenta como activación.
        self.assertFalse(ActivacionModelo.objects.filter(
            version_modelo=self.xgb).exists())

    def test_modelos_principal_y_alternativo(self):
        modelos = {m["version"]: m for m in self.api.get("/api/modelos/").json()}
        self.assertEqual({v: m["rol"] for v, m in modelos.items()},
                         {"v2": "principal", "v2-xgb": "alternativo"})
        self.assertTrue(modelos["v2-xgb"]["activable"])

    def test_cambiar_el_principal_pide_el_nombre_y_no_dispara_el_aviso(self):
        url = f"/api/modelos/{self.xgb.id}/activar/"
        self.assertEqual(self.api.post(url, {"confirmacion": "XGBoost"},
                                       format="json").status_code, 400)
        self.assertEqual(self.api.post(url, {"confirmacion": "v2-xgb"},
                                       format="json").status_code, 200)
        fila = ActivacionModelo.objects.get(version_modelo=self.xgb)
        self.assertEqual((fila.version_anterior, fila.nombre_usuario),
                         (self.rf, "admin"))
        estado = self.api.get("/api/resumen-admin/").json()["modelo"]
        self.assertEqual((estado["activo"], estado["aviso"]), ("v2-xgb", False))

    def test_aviso_sin_falsos_positivos_con_el_alternativo(self):
        estado = self.api.get("/api/resumen-admin/").json()["modelo"]
        self.assertEqual(estado, {"activo": "v2", "recomendado": "v2",
                                  "aviso": False, "activo_sin_corte": False})


class ProteccionTest(TestCase):
    """Ninguno de los dos modelos se desactiva por error: no hay acción de
    desactivar y el admin de Django es de solo lectura para las versiones."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import User
        call_command("registrar_modelo", stdout=StringIO())
        call_command("registrar_modelo", "--modelo", "v2-xgb", "--sin-activar",
                     stdout=StringIO())
        cls.rf = VersionModelo.objects.get(version="v2")
        cls.super = User.objects.create_superuser("raiz", password="x")

    def test_admin_de_django_de_solo_lectura(self):
        self.client.force_login(self.super)
        url = f"/admin/riesgo/versionmodelo/{self.rf.id}/change/"
        r = self.client.post(url, {"version": "v2", "activo": "", "est_registro": "I"})
        self.assertIn(r.status_code, (403, 200))
        self.rf.refresh_from_db()
        self.assertEqual((self.rf.activo, self.rf.est_registro), (True, "A"))
        self.assertEqual(self.client.post(
            f"/admin/riesgo/versionmodelo/{self.rf.id}/delete/",
            {"post": "yes"}).status_code, 403)
        self.assertTrue(VersionModelo.objects.filter(id=self.rf.id).exists())
        self.assertEqual(self.client.get(
            "/admin/riesgo/versionmodelo/add/").status_code, 403)
        # El historial de activaciones se consulta, no se edita.
        self.assertEqual(self.client.get(
            "/admin/riesgo/activacionmodelo/").status_code, 200)

    def test_la_api_no_tiene_accion_de_desactivar(self):
        admin = test_api.ApiTest._usuario("admin", "administrador", [])
        api = test_api.ApiTest.cliente(self, admin)
        for accion in ("desactivar", ""):
            r = api.post(f"/api/modelos/{self.rf.id}/{accion}", {}, format="json")
            self.assertIn(r.status_code, (404, 405))
        self.assertEqual(VersionModelo.objects.get(activo=True).version, "v2")
