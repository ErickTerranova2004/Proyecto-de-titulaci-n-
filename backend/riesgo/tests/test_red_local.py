"""Modo red local (IP_RED_LOCAL): ALLOWED_HOSTS, CORS, CSRF y FRONTEND_URL.

settings.py se evalúa al arrancar, así que cada caso lo carga en un proceso
aparte con las variables de entorno del caso (tienen prioridad sobre .env).
"""

import json
import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase

LEER = ("import json, config.settings as s; print(json.dumps({"
        "'hosts': s.ALLOWED_HOSTS, 'cors': s.CORS_ALLOWED_ORIGINS, "
        "'csrf': s.CSRF_TRUSTED_ORIGINS, 'frontend': s.FRONTEND_URL}))")


def _settings(**entorno):
    env = {k: v for k, v in os.environ.items()
           if k not in ("IP_RED_LOCAL", "FRONTEND_URL", "PUERTO_FRONTEND")}
    env.update(entorno)
    salida = subprocess.run([sys.executable, "-c", LEER], cwd=settings.BASE_DIR,
                            env=env, capture_output=True, text=True,
                            check=True, timeout=60)
    return json.loads(salida.stdout.strip().splitlines()[-1])


class RedLocalTest(SimpleTestCase):

    def test_con_ip_se_admite_la_red_local(self):
        s = _settings(IP_RED_LOCAL="192.168.1.6",
                      FRONTEND_URL="")  # vacío: se deduce de la IP
        self.assertIn("192.168.1.6", s["hosts"])
        self.assertIn("http://192.168.1.6:5174", s["cors"])
        self.assertIn("http://192.168.1.6:5174", s["csrf"])
        self.assertEqual(s["frontend"], "http://192.168.1.6:5174")

    def test_frontend_url_explicita_tiene_prioridad(self):
        s = _settings(IP_RED_LOCAL="10.0.0.8", PUERTO_FRONTEND="5180",
                      FRONTEND_URL="http://10.0.0.8:5180/")
        self.assertEqual(s["frontend"], "http://10.0.0.8:5180")
        self.assertIn("http://10.0.0.8:5180", s["cors"])

    def test_sin_ip_no_se_abre_a_la_red(self):
        s = _settings(IP_RED_LOCAL="", FRONTEND_URL="")
        self.assertFalse([h for h in s["hosts"] if h.startswith(("192.", "10."))])
        self.assertEqual(s["csrf"], [])
        self.assertEqual(s["frontend"], "http://localhost:5174")
