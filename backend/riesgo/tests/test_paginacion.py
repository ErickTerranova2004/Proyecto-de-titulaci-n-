"""Paginación en el backend de historiales, pendientes, asignaciones,
informes y usuarios: total, páginas, filtros y orden respetados, y la lista
completa intacta sin ?pagina."""

from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from riesgo.models import DecisionDespliegue, Prediccion
from riesgo.services import github
from riesgo.tests import test_api
from riesgo.tests.test_api import DATOS, ClienteFalso

N = 30


@override_settings(GEMINI_API_KEY="")
class PaginacionTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente

    def setUp(self):
        with mock.patch.object(github, "GitHubClient", ClienteFalso):
            r = self.cliente(self.dev).post("/api/predicciones/", DATOS, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        base = Prediccion.objects.get(pk=r.json()["id"])
        ahora = timezone.now()
        # N análisis con fechas distintas y niveles alternos.
        for i in range(1, N):
            copia = Prediccion.objects.get(pk=base.pk)
            copia.pk = None
            copia.save()
            Prediccion.objects.filter(pk=copia.pk).update(
                creada_en=ahora - timedelta(hours=i),
                nivel=("alto", "medio", "bajo")[i % 3])
        Prediccion.objects.filter(pk=base.pk).update(creada_en=ahora, nivel="bajo")
        self.ids = list(Prediccion.objects.order_by("-creada_en", "-id")
                        .values_list("id", flat=True))
        self.assertEqual(len(self.ids), N)

    def _get(self, usuario, ruta):
        r = self.cliente(usuario).get(ruta)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_sin_pagina_la_lista_completa_no_cambia(self):
        lista = self._get(self.dev, "/api/predicciones/")
        self.assertIsInstance(lista, list)
        self.assertEqual([p["id"] for p in lista], self.ids)

    def test_paginas_de_25_con_total(self):
        p1 = self._get(self.dev, "/api/predicciones/?pagina=1")
        self.assertEqual((p1["total"], p1["pagina"], p1["por_pagina"], p1["paginas"]),
                         (N, 1, 25, 2))
        self.assertEqual(len(p1["resultados"]), 25)
        p2 = self._get(self.dev, "/api/predicciones/?pagina=2")
        self.assertEqual(len(p2["resultados"]), N - 25)
        # Las páginas juntas son la lista completa, en el mismo orden.
        self.assertEqual([p["id"] for p in p1["resultados"] + p2["resultados"]], self.ids)

    def test_50_y_100_por_pagina(self):
        for por_pagina in (50, 100):
            datos = self._get(self.dev, f"/api/predicciones/?pagina=1&por_pagina={por_pagina}")
            self.assertEqual((datos["paginas"], len(datos["resultados"])), (1, N))

    def test_respeta_filtros_y_orden(self):
        altos = Prediccion.objects.filter(nivel="alto").count()
        datos = self._get(self.dev, "/api/predicciones/?pagina=1&nivel=alto")
        self.assertEqual(datos["total"], altos)
        self.assertTrue(all(p["nivel"] == "alto" for p in datos["resultados"]))
        antiguo = self._get(self.dev, "/api/predicciones/?pagina=1&orden=antiguo")
        self.assertEqual([p["id"] for p in antiguo["resultados"]], list(reversed(self.ids))[:25])
        # Pendientes del líder: sin decisión.
        Prediccion.objects.filter(pk=self.ids[0]).first().decisiones.create(
            usuario=self.lider, decision="autorizar")
        pendientes = self._get(self.lider, "/api/predicciones/?pagina=1&sin_decision=1")
        self.assertEqual(pendientes["total"], N - 1)
        self.assertNotIn(self.ids[0], [p["id"] for p in pendientes["resultados"]])

    def test_orden_por_decision_en_el_backend(self):
        # Decisiones en dos análisis antiguos: van primero, la más reciente antes.
        viejo, mas_viejo = self.ids[-2], self.ids[-1]
        for pk, hace in ((mas_viejo, 2), (viejo, 1)):
            d = DecisionDespliegue.objects.create(prediccion_id=pk, usuario=self.lider,
                                                  decision="autorizar")
            DecisionDespliegue.objects.filter(pk=d.pk).update(
                creada_en=timezone.now() - timedelta(minutes=hace))
        datos = self._get(self.lider, "/api/predicciones/?pagina=1&orden=decision")
        ids = [p["id"] for p in datos["resultados"]]
        self.assertEqual(ids[:2], [viejo, mas_viejo])
        self.assertEqual(ids[2:], [i for i in self.ids if i not in (viejo, mas_viejo)][:23])

    def test_pagina_inexistente_muestra_la_ultima_y_valores_no_validos(self):
        datos = self._get(self.dev, "/api/predicciones/?pagina=9")
        self.assertEqual((datos["pagina"], len(datos["resultados"])), (2, N - 25))
        for consulta in ("pagina=0", "pagina=x", "pagina=1&por_pagina=10", "pagina=1&por_pagina=abc"):
            self.assertEqual(self.cliente(self.dev).get(
                f"/api/predicciones/?{consulta}").status_code, 400, consulta)

    def test_asignaciones_paginadas(self):
        manana = timezone.localdate() + timedelta(days=1)
        for pk in self.ids[:27]:
            DecisionDespliegue.objects.create(prediccion_id=pk, usuario=self.lider,
                                              decision="posponer", fecha_limite=manana)
        completa = self._get(self.lider, "/api/asignaciones/")
        self.assertEqual(len(completa), 27)
        p2 = self._get(self.lider, "/api/asignaciones/?pagina=2")
        self.assertEqual((p2["total"], len(p2["resultados"])), (27, 2))
        p1 = self._get(self.lider, "/api/asignaciones/?pagina=1")
        self.assertEqual([a["id"] for a in p1["resultados"] + p2["resultados"]],
                         [a["id"] for a in completa])

    def test_informes_paginados(self):
        datos = self._get(self.lider, "/api/informes/?pagina=1&por_pagina=50")
        self.assertEqual((datos["total"], datos["paginas"], datos["resultados"]), (0, 1, []))
        self.assertIsInstance(self._get(self.lider, "/api/informes/"), list)

    def test_usuarios_tabla_filtrada_y_paginada(self):
        sin = self._get(self.admin, "/api/gestion/usuarios/")
        self.assertNotIn("tabla", sin)
        datos = self._get(self.admin, "/api/gestion/usuarios/?pagina=1")
        self.assertEqual(datos["tabla"]["total"], len(datos["usuarios"]))
        nombres = [u["usuario"] for u in datos["tabla"]["resultados"]]
        self.assertEqual(nombres, sorted(nombres))
        devs = self._get(self.admin, "/api/gestion/usuarios/?pagina=1&filtro=desarrollador")
        self.assertEqual({u["usuario"] for u in devs["tabla"]["resultados"]}, {"dev", "dev2"})
        buscar = self._get(self.admin, "/api/gestion/usuarios/?pagina=1&q=LIDER")
        self.assertEqual({u["usuario"] for u in buscar["tabla"]["resultados"]},
                         {"lider", "lider_ajeno"})
        # Los indicadores siguen recibiendo todas las cuentas.
        self.assertEqual(len(devs["usuarios"]), len(datos["usuarios"]))
        self.assertEqual(self.cliente(self.admin).get(
            "/api/gestion/usuarios/?pagina=1&filtro=otro").status_code, 400)
