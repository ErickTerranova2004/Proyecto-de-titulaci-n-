from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token

from riesgo.models import AccesoRepositorio, Prediccion
from riesgo.services import github
from riesgo.tests import test_api
from riesgo.tests.test_api import DATOS, ClienteFalso


@override_settings(GEMINI_API_KEY="")
class EliminarUsuarioTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente

    def eliminar(self, usuario):
        return self.cliente(self.admin).delete(
            f"/api/gestion/usuarios/{usuario.id}/")

    def test_elimina_cuenta_sin_historial(self):
        Token.objects.create(user=self.dev2)
        r = self.eliminar(self.dev2)
        self.assertEqual(r.status_code, 204, r.content)
        self.assertFalse(User.objects.filter(id=self.dev2.id).exists())
        self.assertFalse(AccesoRepositorio.objects.filter(
            usuario_id=self.dev2.id).exists())
        self.assertFalse(Token.objects.filter(user_id=self.dev2.id).exists())

    def test_no_elimina_cuenta_con_analisis(self):
        with mock.patch.object(github, "GitHubClient", ClienteFalso):
            self.cliente(self.dev).post("/api/predicciones/", DATOS,
                                        format="json")
        r = self.eliminar(self.dev)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["codigo"], "con_historial")
        self.assertTrue(User.objects.filter(id=self.dev.id).exists())
        self.assertEqual(Prediccion.objects.filter(usuario=self.dev).count(),
                         1)

    def test_no_elimina_su_propia_cuenta(self):
        r = self.eliminar(self.admin)
        self.assertEqual(r.status_code, 400)
        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_no_elimina_al_superusuario(self):
        raiz = User.objects.create_superuser("raiz", password="x")
        self.assertEqual(self.eliminar(raiz).status_code, 400)
        self.assertTrue(User.objects.filter(id=raiz.id).exists())

    def test_solo_el_administrador_elimina(self):
        r = self.cliente(self.lider).delete(
            f"/api/gestion/usuarios/{self.dev2.id}/")
        self.assertEqual(r.status_code, 403)
        self.assertTrue(User.objects.filter(id=self.dev2.id).exists())

    def test_listado_informa_el_historial(self):
        with mock.patch.object(github, "GitHubClient", ClienteFalso):
            self.cliente(self.dev).post("/api/predicciones/", DATOS,
                                        format="json")
        usuarios = {u["usuario"]: u for u in self.cliente(self.admin).get(
            "/api/gestion/usuarios/").json()["usuarios"]}
        self.assertEqual(usuarios["dev"]["analisis"], 1)
        self.assertEqual(usuarios["dev2"]["analisis"], 0)
        self.assertEqual(usuarios["dev2"]["decisiones"], 0)
