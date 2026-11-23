"""Restablecimiento de contraseña por correo (services/restablecimiento.py,
views_clave.py y la gestión de usuarios del administrador)."""

import re
from datetime import datetime, timedelta
from unittest import mock

from django.contrib.auth.models import Group, User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from riesgo.models import RestablecimientoClave

URL_FRONTEND = "https://riesgo.ejemplo.test"
CLAVE_NUEVA = "Despliegue-Seguro-2026"


# Sin correo configurado aunque backend/.env tenga EMAIL_HOST: las pruebas no
# dependen del .env (Django guarda los mensajes en mail.outbox, nunca envía).
@override_settings(FRONTEND_URL=URL_FRONTEND, CORREO_CONFIGURADO=False,
                   EMAIL_HOST="")
class RestablecimientoTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("jefa", password="x",
                                             email="jefa@ejemplo.test")
        cls.admin.groups.add(Group.objects.get_or_create(
            name="administrador")[0])
        cls.dev = User.objects.create_user("ana", password="Clave-Vieja-2026",
                                           email="ana@ejemplo.test")
        cls.dev.groups.add(Group.objects.get_or_create(
            name="desarrollador")[0])
        cls.sin_correo = User.objects.create_user("beto", password="x")

    def setUp(self):
        cache.clear()  # límite de peticiones públicas por IP

    def cliente(self, usuario=None):
        api = APIClient()
        if usuario:
            api.force_authenticate(usuario)
        return api

    def enviar_admin(self, usuario):
        return self.cliente(self.admin).post(
            f"/api/gestion/usuarios/{usuario.id}/restablecer/")

    def enlace_del_correo(self, indice=-1):
        cuerpo = mail.outbox[indice].body
        encontrado = re.search(
            re.escape(URL_FRONTEND) + r"/restablecer/([^/\s]+)/([^/\s]+)",
            cuerpo)
        self.assertIsNotNone(encontrado, cuerpo)
        return encontrado.group(1), encontrado.group(2)

    def confirmar(self, uid, token, clave=CLAVE_NUEVA, confirmacion=None):
        return self.cliente().post("/api/auth/restablecer/confirmar/", {
            "uid": uid, "token": token, "contrasena": clave,
            "confirmacion": clave if confirmacion is None else confirmacion},
            format="json")

    # --- Administrador ------------------------------------------------------
    def test_admin_envia_el_enlace_y_queda_auditado(self):
        r = self.enviar_admin(self.dev)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["correo"], "ana@ejemplo.test")
        self.assertEqual(r.json()["medio"], "consola")  # sin EMAIL_HOST
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana@ejemplo.test"])
        self.assertIn("una vez", mail.outbox[0].body)
        uid, token = self.enlace_del_correo()
        self.assertTrue(default_token_generator.check_token(self.dev, token))

        registro = RestablecimientoClave.objects.get()
        self.assertEqual(registro.usuario, self.dev)
        self.assertEqual(registro.solicitado_por, self.admin)
        self.assertEqual(registro.usu_creacion, "jefa")
        self.assertEqual(registro.origen, "administrador")
        self.assertTrue(registro.enviado)
        self.assertIsNone(registro.cambiada_en)
        # La contraseña no cambia hasta que el usuario usa el enlace.
        self.dev.refresh_from_db()
        self.assertTrue(self.dev.check_password("Clave-Vieja-2026"))

    def test_sin_correo_no_se_envia(self):
        r = self.enviar_admin(self.sin_correo)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "sin_correo")
        self.assertEqual(mail.outbox, [])
        self.assertFalse(RestablecimientoClave.objects.exists())

    def test_solo_el_administrador_envia(self):
        r = self.cliente(self.dev).post(
            f"/api/gestion/usuarios/{self.dev.id}/restablecer/")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(mail.outbox, [])

    def test_fallo_del_servidor_de_correo(self):
        with mock.patch("riesgo.services.restablecimiento.send_mail",
                        side_effect=OSError("sin red")):
            r = self.enviar_admin(self.dev)
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json()["codigo"], "envio_fallido")
        self.assertFalse(RestablecimientoClave.objects.get().enviado)

    def test_admin_ya_no_escribe_contrasenas(self):
        r = self.cliente(self.admin).patch(
            f"/api/gestion/usuarios/{self.dev.id}/",
            {"contrasena": "Otra-Clave-2026"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "contrasena_no_permitida")
        self.dev.refresh_from_db()
        self.assertTrue(self.dev.check_password("Clave-Vieja-2026"))

    def test_alta_sin_contrasena_envia_el_enlace(self):
        r = self.cliente(self.admin).post("/api/gestion/usuarios/", {
            "usuario": "carla", "correo": "carla@ejemplo.test",
            "rol": "desarrollador"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertFalse(r.json()["clave_definida"])
        self.assertTrue(r.json()["envio"]["enviado"])
        carla = User.objects.get(username="carla")
        self.assertFalse(carla.has_usable_password())
        uid, token = self.enlace_del_correo()
        self.assertEqual(self.confirmar(uid, token).status_code, 200)
        carla.refresh_from_db()
        self.assertTrue(carla.check_password(CLAVE_NUEVA))

    def test_alta_exige_correo_y_rechaza_contrasena(self):
        api = self.cliente(self.admin)
        r = api.post("/api/gestion/usuarios/", {"usuario": "dani"},
                     format="json")
        self.assertEqual(r.json()["codigo"], "correo_vacio")
        r = api.post("/api/gestion/usuarios/", {
            "usuario": "dani", "correo": "dani@ejemplo.test",
            "contrasena": "Clave-Prueba-2026"}, format="json")
        self.assertEqual(r.json()["codigo"], "contrasena_no_permitida")
        self.assertFalse(User.objects.filter(username="dani").exists())

    def test_listado_informa_correo_y_ultimo_envio(self):
        self.enviar_admin(self.dev)
        datos = self.cliente(self.admin).get("/api/gestion/usuarios/").json()
        self.assertEqual(datos["correo"], {"configurado": False,
                                           "medio": "consola"})
        usuarios = {u["usuario"]: u for u in datos["usuarios"]}
        ultimo = usuarios["ana"]["ultimo_restablecimiento"]
        self.assertEqual(ultimo["solicitado_por"], "jefa")
        self.assertIsNone(ultimo["cambiada_en"])
        self.assertIsNone(usuarios["beto"]["ultimo_restablecimiento"])

    # --- Pantalla pública ---------------------------------------------------
    def test_cambio_con_el_enlace_cierra_sesiones_y_registra_la_fecha(self):
        Token.objects.create(user=self.dev)
        self.enviar_admin(self.dev)
        uid, token = self.enlace_del_correo()
        r = self.cliente().post("/api/auth/restablecer/validar/",
                                {"uid": uid, "token": token}, format="json")
        self.assertEqual(r.json(), {"valido": True, "usuario": "ana"})

        r = self.confirmar(uid, token)
        self.assertEqual(r.status_code, 200, r.content)
        self.dev.refresh_from_db()
        self.assertTrue(self.dev.check_password(CLAVE_NUEVA))
        self.assertFalse(Token.objects.filter(user=self.dev).exists())
        registro = RestablecimientoClave.objects.get()
        self.assertIsNotNone(registro.cambiada_en)
        self.assertEqual(registro.usu_modificacion, "ana")
        # Con la nueva contraseña se inicia sesión.
        r = self.cliente().post("/api/auth/token/", {
            "username": "ana", "password": CLAVE_NUEVA})
        self.assertEqual(r.status_code, 200)

    def test_el_enlace_es_de_un_solo_uso(self):
        self.enviar_admin(self.dev)
        uid, token = self.enlace_del_correo()
        self.assertEqual(self.confirmar(uid, token).status_code, 200)
        r = self.confirmar(uid, token, clave="Segunda-Clave-2026")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "enlace_no_valido")
        self.dev.refresh_from_db()
        self.assertTrue(self.dev.check_password(CLAVE_NUEVA))

    def test_el_enlace_caduca_en_una_hora(self):
        self.enviar_admin(self.dev)
        uid, token = self.enlace_del_correo()
        # El generador de Django usa la hora local sin zona (datetime.now()).
        despues = datetime.now() + timedelta(hours=1, minutes=1)
        with mock.patch.object(default_token_generator, "_now",
                               return_value=despues):
            r = self.confirmar(uid, token)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["codigo"], "enlace_no_valido")

    def test_reglas_de_validacion_de_django(self):
        self.enviar_admin(self.dev)
        uid, token = self.enlace_del_correo()
        for clave, confirmacion, codigo in (
                ("12345678901", None, "contrasena_no_valida"),  # numérica
                ("corta", None, "contrasena_no_valida"),
                ("password123", None, "contrasena_no_valida"),  # común
                (CLAVE_NUEVA, "Otra-Distinta-2026", "no_coinciden"),
                ("", None, "contrasena_vacia")):
            with self.subTest(clave=clave):
                r = self.confirmar(uid, token, clave, confirmacion)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.json()["codigo"], codigo)
        self.dev.refresh_from_db()
        self.assertTrue(self.dev.check_password("Clave-Vieja-2026"))

    def test_enlace_manipulado(self):
        self.enviar_admin(self.dev)
        uid, token = self.enlace_del_correo()
        for datos in ({"uid": uid, "token": token + "x"},
                      {"uid": "no-es-base64", "token": token},
                      {"uid": "", "token": ""}):
            with self.subTest(datos=datos):
                r = self.cliente().post("/api/auth/restablecer/validar/",
                                        datos, format="json")
                self.assertEqual(r.status_code, 400)

    def test_un_token_caducado_en_el_navegador_no_impide_usar_el_enlace(self):
        self.enviar_admin(self.dev)
        uid, token = self.enlace_del_correo()
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION="Token no-existe")
        r = api.post("/api/auth/restablecer/validar/",
                     {"uid": uid, "token": token}, format="json")
        self.assertEqual(r.status_code, 200)

    # --- «¿Olvidó su contraseña?» -------------------------------------------
    def test_olvido_responde_igual_exista_o_no_el_correo(self):
        api = self.cliente()
        existe = api.post("/api/auth/restablecer/solicitar/",
                          {"correo": "ANA@ejemplo.test"}, format="json")
        no_existe = api.post("/api/auth/restablecer/solicitar/",
                             {"correo": "nadie@ejemplo.test"}, format="json")
        vacio = api.post("/api/auth/restablecer/solicitar/", {},
                         format="json")
        self.assertEqual(existe.status_code, 200)
        self.assertEqual(existe.json(), no_existe.json())
        self.assertEqual(existe.json(), vacio.json())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ana@ejemplo.test"])
        registro = RestablecimientoClave.objects.get()
        self.assertEqual(registro.origen, "usuario")
        self.assertIsNone(registro.solicitado_por)
        self.assertEqual(registro.usu_creacion, "anonimo")

    def test_olvido_no_envia_a_cuentas_desactivadas(self):
        self.dev.is_active = False
        self.dev.save()
        r = self.cliente().post("/api/auth/restablecer/solicitar/",
                                {"correo": "ana@ejemplo.test"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(mail.outbox, [])

    def test_limite_de_peticiones_publicas(self):
        api = self.cliente()
        codigos = [api.post("/api/auth/restablecer/solicitar/",
                            {"correo": "nadie@ejemplo.test"},
                            format="json").status_code for _ in range(21)]
        self.assertEqual(codigos[:20], [200] * 20)
        self.assertEqual(codigos[20], 429)
