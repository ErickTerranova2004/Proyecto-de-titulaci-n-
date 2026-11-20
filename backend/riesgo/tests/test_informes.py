"""Informe de cumplimiento: envío por el desarrollador, permisos, contenido,
decisión final del líder, PDF con auditoría de descargas y correo."""

from datetime import timedelta
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from riesgo.models import (DecisionDespliegue, DescargaInforme,
                           InformeCumplimiento, Prediccion)
from riesgo.services import github
from riesgo.tests import test_api
from riesgo.tests.test_api import DATOS, ClienteFalso

COMENTARIO = "Corregí el YAML del workflow y añadí pruebas de humo."


@override_settings(GEMINI_API_KEY="", CORREO_CONFIGURADO=False, EMAIL_HOST="",
                   FRONTEND_URL="http://plataforma.test")
class InformeCumplimientoTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)
        cls.lider.email = "lider@ejemplo.test"
        cls.lider.save(update_fields=["email"])

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente

    def _analizar(self, usuario, **extra):
        with mock.patch.object(github, "GitHubClient", ClienteFalso):
            r = self.cliente(usuario).post("/api/predicciones/",
                                           dict(DATOS, **extra), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def setUp(self):
        # Análisis original, indicación del líder y respuesta del desarrollador.
        self.original = self._analizar(self.dev)
        r = self.cliente(self.lider).post(
            f"/api/predicciones/{self.original['id']}/decision/",
            {"decision": "solicitar_revision", "comentario": "Revise el YAML",
             "fecha_limite": (timezone.localdate() + timedelta(days=3)).isoformat()},
            format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.asignacion = DecisionDespliegue.objects.get(
            prediccion_id=self.original["id"])
        self.nuevo = self._analizar(self.dev, atiende_decision=self.asignacion.id,
                                    respuesta_desarrollador="Cambié el YAML")

    def _enviar(self, usuario=None, comentario=COMENTARIO, asignacion=None):
        return self.cliente(usuario or self.dev).post(
            f"/api/asignaciones/{(asignacion or self.asignacion).id}/informe/",
            {"comentario": comentario}, format="json")

    def test_el_desarrollador_envia_el_informe(self):
        r = self._enviar()
        self.assertEqual(r.status_code, 201, r.content)
        informe = InformeCumplimiento.objects.get()
        self.assertEqual((informe.asignacion_id, informe.prediccion_original_id,
                          informe.prediccion_nueva_id, informe.desarrollador,
                          informe.lider),
                         (self.asignacion.id, self.original["id"],
                          self.nuevo["id"], self.dev, self.lider))
        self.assertEqual(informe.comentario, COMENTARIO)
        self.assertEqual(informe.usu_creacion, "dev")
        self.assertEqual(informe.est_registro, "A")
        self.assertEqual(r.json()["numero"], f"IC-{informe.id:05d}")
        # La asignación lo indica (para no ofrecer el botón otra vez).
        asignaciones = self.cliente(self.dev).get("/api/asignaciones/").json()
        self.assertEqual(asignaciones[0]["informe"]["id"], informe.id)

    def test_comentario_obligatorio_y_un_solo_informe(self):
        for comentario in ("", "   ", "corto"):
            r = self._enviar(comentario=comentario)
            self.assertEqual(r.status_code, 400, comentario)
        self.assertEqual(self._enviar().status_code, 201)
        r = self._enviar()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "informe_ya_enviado")

    def test_sin_nuevo_analisis_no_hay_informe(self):
        otro = self._analizar(self.dev)
        self.cliente(self.lider).post(
            f"/api/predicciones/{otro['id']}/decision/",
            {"decision": "posponer", "fecha_limite": (
                timezone.localdate() + timedelta(days=2)).isoformat()},
            format="json")
        pendiente = DecisionDespliegue.objects.get(prediccion_id=otro["id"])
        r = self._enviar(asignacion=pendiente)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "sin_nuevo_analisis")

    def test_solo_el_autor_lo_envia(self):
        # dev2 no ve la asignación de dev.
        self.assertEqual(self._enviar(self.dev2).status_code, 404)
        # El líder la ve, pero no es el autor.
        r = self._enviar(self.lider)
        self.assertEqual(r.status_code, 403)
        self.assertFalse(InformeCumplimiento.objects.exists())

    def test_quien_puede_verlo(self):
        informe_id = self._enviar().json()["id"]
        for usuario, ve in ((self.dev, True), (self.lider, True), (self.admin, True),
                            (self.dev2, False), (self.lider_ajeno, False)):
            with self.subTest(usuario=usuario.username):
                lista = self.cliente(usuario).get("/api/informes/").json()
                self.assertEqual([i["id"] for i in lista], [informe_id] if ve else [])
                estado = self.cliente(usuario).get(
                    f"/api/informes/{informe_id}/").status_code
                self.assertEqual(estado, 200 if ve else 404)
                self.assertEqual(self.cliente(usuario).get(
                    f"/api/informes/{informe_id}/pdf/").status_code,
                    200 if ve else 404)

    def test_contenido_del_informe(self):
        informe_id = self._enviar().json()["id"]
        c = self.cliente(self.lider).get(f"/api/informes/{informe_id}/").json()
        self.assertEqual((c["repositorio"], c["workflow"], c["desarrollador"],
                          c["lider"]),
                         ("acme/tienda", DATOS["workflow_path"], "dev", "lider"))
        self.assertEqual(c["indicacion"]["decision"], "solicitar_revision")
        self.assertEqual(c["indicacion"]["comentario"], "Revise el YAML")
        self.assertIsNotNone(c["indicacion"]["fecha_limite"])
        self.assertEqual(c["original"]["id"], self.original["id"])
        self.assertEqual(c["nuevo"]["id"], self.nuevo["id"])
        for clave in ("probabilidad", "nivel", "recomendacion"):
            self.assertIn(clave, c["nuevo"])
        self.assertAlmostEqual(
            c["diferencia_puntos"],
            (c["nuevo"]["probabilidad"] - c["original"]["probabilidad"]) * 100,
            places=1)
        self.assertIsInstance(c["factores"], list)
        self.assertEqual(c["comentario"], COMENTARIO)
        self.assertIn("resumen", c["ia"])
        self.assertIsInstance(c["ia"]["recomendaciones"], list)
        self.assertIsNone(c["decision_final"])
        self.assertTrue(c["puede_decidir"])
        # Al abrirlo, el líder lo marca como leído; el desarrollador no.
        self.assertIsNotNone(InformeCumplimiento.objects.get().leido_en)
        dev = self.cliente(self.dev).get(f"/api/informes/{informe_id}/").json()
        self.assertFalse(dev["puede_decidir"])

    def test_factores_shap_que_cambian(self):
        informe_id = self._enviar().json()["id"]
        Prediccion.objects.filter(pk=self.nuevo["id"]).update(
            variables={**Prediccion.objects.get(pk=self.nuevo["id"]).variables,
                       "wf_tasa_fallo_prev": 0.0, "wf_ultimo_fallo": 0.0})
        c = self.cliente(self.lider).get(f"/api/informes/{informe_id}/").json()
        self.assertTrue(c["factores"])
        diferencias = [abs(f["diferencia"]) for f in c["factores"]]
        self.assertEqual(diferencias, sorted(diferencias, reverse=True))
        self.assertTrue(all(f["descripcion"] for f in c["factores"]))

    def test_decision_final_del_lider(self):
        informe_id = self._enviar().json()["id"]
        r = self.cliente(self.dev).post(f"/api/informes/{informe_id}/decision/",
                                        {"decision": "autorizar"}, format="json")
        self.assertEqual(r.status_code, 403)
        r = self.cliente(self.lider).post(
            f"/api/informes/{informe_id}/decision/",
            {"decision": "autorizar", "comentario": "Bien resuelto"},
            format="json")
        self.assertEqual(r.status_code, 201, r.content)
        final = r.json()["decision_final"]
        self.assertEqual((final["decision"], final["comentario"], final["usuario"]),
                         ("autorizar", "Bien resuelto", "lider"))
        # Es una decisión sobre el análisis nuevo (sale en historiales).
        decision = DecisionDespliegue.objects.get(pk=final["id"])
        self.assertEqual(decision.prediccion_id, self.nuevo["id"])
        self.assertEqual(InformeCumplimiento.objects.get().decision_final, decision)
        lista = self.cliente(self.lider).get("/api/informes/").json()
        self.assertEqual(lista[0]["decision_final"]["decision"], "autorizar")
        # El administrador también puede; uno ajeno no.
        r = self.cliente(self.admin).post(f"/api/informes/{informe_id}/decision/",
                                          {"decision": "posponer"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.cliente(self.lider_ajeno).post(
            f"/api/informes/{informe_id}/decision/", {"decision": "posponer"},
            format="json").status_code, 404)

    def test_pdf_y_auditoria_de_descargas(self):
        informe_id = self._enviar().json()["id"]
        self.cliente(self.lider).post(f"/api/informes/{informe_id}/decision/",
                                      {"decision": "autorizar"}, format="json")
        r = self.cliente(self.lider).get(f"/api/informes/{informe_id}/pdf/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertIn(f"IC-{informe_id:05d}", r["Content-Disposition"])
        self.assertTrue(r.content.startswith(b"%PDF"))
        self.cliente(self.admin).get(f"/api/informes/{informe_id}/pdf/")
        descargas = DescargaInforme.objects.order_by("descargado_en")
        self.assertEqual([(d.nombre_usuario, d.usu_creacion, d.formato)
                          for d in descargas],
                         [("lider", "lider", "pdf"), ("admin", "admin", "pdf")])
        detalle = self.cliente(self.admin).get(f"/api/informes/{informe_id}/").json()
        self.assertEqual(detalle["descargas"], 2)

    def test_correo_al_lider_solo_si_esta_configurado(self):
        self._enviar()
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(InformeCumplimiento.objects.get().correo_enviado)

    @override_settings(CORREO_CONFIGURADO=True)
    def test_correo_al_lider_con_el_enlace(self):
        informe_id = self._enviar().json()["id"]
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ["lider@ejemplo.test"])
        self.assertIn(f"IC-{informe_id:05d}", correo.subject)
        self.assertIn(f"http://plataforma.test/?informe={informe_id}", correo.body)
        self.assertTrue(InformeCumplimiento.objects.get().correo_enviado)

    def test_filtro_por_fechas_y_orden(self):
        primero = self._enviar().json()["id"]
        # Segundo informe, de otra asignación, enviado "ayer".
        otro = self._analizar(self.dev)
        self.cliente(self.lider).post(
            f"/api/predicciones/{otro['id']}/decision/",
            {"decision": "posponer", "fecha_limite": (
                timezone.localdate() + timedelta(days=2)).isoformat()},
            format="json")
        segunda = DecisionDespliegue.objects.get(prediccion_id=otro["id"])
        self._analizar(self.dev, atiende_decision=segunda.id)
        segundo = self._enviar(asignacion=segunda).json()["id"]
        ayer = timezone.now() - timedelta(days=1)
        InformeCumplimiento.objects.filter(pk=segundo).update(enviado_en=ayer)
        hoy = timezone.localdate().isoformat()
        cliente = self.cliente(self.lider)
        self.assertEqual([i["id"] for i in cliente.get("/api/informes/").json()],
                         [primero, segundo])
        self.assertEqual([i["id"] for i in cliente.get(
            "/api/informes/?orden=antiguo").json()], [segundo, primero])
        self.assertEqual([i["id"] for i in cliente.get(
            f"/api/informes/?desde={hoy}").json()], [primero])
        self.assertEqual([i["id"] for i in cliente.get(
            f"/api/informes/?hasta={timezone.localdate(ayer).isoformat()}").json()],
            [segundo])
        self.assertEqual(cliente.get("/api/informes/?desde=ayer").status_code, 400)

    def test_traspaso_al_eliminar_un_usuario(self):
        self._enviar()
        r = self.cliente(self.admin).delete(
            f"/api/gestion/usuarios/{self.lider.id}/?transferir_a={self.admin.id}")
        self.assertIn(r.status_code, (200, 204), r.content)
        self.assertEqual(InformeCumplimiento.objects.get().lider, self.admin)
