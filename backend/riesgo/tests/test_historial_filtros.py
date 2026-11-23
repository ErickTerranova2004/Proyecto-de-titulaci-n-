"""Filtros y orden de los historiales y de «Pendientes de decisión»
(views.filtrar_historial): se aplican en el backend."""

from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from riesgo.models import (Commit, DecisionDespliegue, Prediccion,
                           VersionModelo, Workflow)
from riesgo.tests import test_api


def local(dia, hora):
    """Fecha y hora de America/Guayaquil (la zona de la plataforma)."""
    return timezone.make_aware(datetime(2026, 11, dia, hora, 0))


class FiltrosHistorialTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)
        workflow = Workflow.objects.get(repositorio=cls.repo,
                                        path=".github/workflows/deploy.yml")
        commit = Commit.objects.create(repositorio=cls.repo, sha="a" * 40)
        version = VersionModelo.objects.filter(est_registro="A").first()

        def crear(usuario, nivel, creada_en, origen="interactivo"):
            p = Prediccion.objects.create(
                usuario=usuario, workflow=workflow, commit=commit,
                version_modelo=version, evento="push", variables={},
                probabilidad={"bajo": 0.1, "medio": 0.4, "alto": 0.8}[nivel],
                nivel=nivel, factores=[], recomendaciones=[], origen=origen,
                datos_github_extraidos_en=timezone.now())
            # auto_now_add: la fecha se fija después de crear.
            Prediccion.objects.filter(pk=p.pk).update(creada_en=creada_en)
            return p.pk

        # 23:30 del 10 en Guayaquil es el 11 en UTC: cuenta como día 10.
        cls.p10 = crear(cls.dev, "alto", local(10, 23) + timedelta(minutes=30))
        cls.p12 = crear(cls.dev, "bajo", local(12, 9))
        cls.p14 = crear(cls.dev2, "medio", local(14, 9))
        cls.p16 = crear(cls.dev, "alto", local(16, 9))
        cls.lote = crear(cls.admin, "alto", local(13, 9), origen="lote")
        DecisionDespliegue.objects.create(
            prediccion_id=cls.p16, usuario=cls.lider, decision="autorizar")

    def ids(self, usuario, consulta=""):
        r = self.cliente(usuario).get(f"/api/predicciones/{consulta}")
        self.assertEqual(r.status_code, 200, r.content)
        return [p["id"] for p in r.json()]

    cliente = test_api.ApiTest.cliente
    _usuario = test_api.ApiTest._usuario

    def test_por_defecto_del_mas_reciente_al_mas_antiguo(self):
        self.assertEqual(self.ids(self.lider),
                         [self.p16, self.p14, self.p12, self.p10])
        self.assertEqual(self.ids(self.dev),
                         [self.p16, self.p12, self.p10])
        self.assertEqual(self.ids(self.lider, "?orden=antiguo"),
                         [self.p10, self.p12, self.p14, self.p16])

    def test_rango_de_fechas_incluye_ambos_extremos(self):
        self.assertEqual(self.ids(self.lider, "?desde=2026-11-12&hasta=2026-11-14"),
                         [self.p14, self.p12])
        self.assertEqual(self.ids(self.lider, "?desde=2026-11-14"),
                         [self.p16, self.p14])
        self.assertEqual(self.ids(self.lider, "?hasta=2026-11-12"),
                         [self.p12, self.p10])

    def test_el_dia_es_el_de_la_zona_horaria_de_la_plataforma(self):
        self.assertEqual(self.ids(self.lider, "?desde=2026-11-10&hasta=2026-11-10"),
                         [self.p10])
        self.assertEqual(self.ids(self.lider, "?desde=2026-11-11&hasta=2026-11-11"),
                         [])

    def test_el_filtro_respeta_la_visibilidad_del_rol(self):
        # El desarrollador no ve el análisis de dev2 aunque esté en el rango.
        self.assertEqual(self.ids(self.dev, "?desde=2026-11-14&hasta=2026-11-14"),
                         [])
        # El administrador ve también el lote, y puede filtrarlo por origen.
        self.assertEqual(self.ids(self.admin, "?desde=2026-11-13&hasta=2026-11-13"),
                         [self.lote])
        self.assertEqual(self.ids(self.admin, "?origen=interactivo"),
                         [self.p16, self.p14, self.p12, self.p10])
        self.assertEqual(self.ids(self.lider, "?origen=lote"), [])

    def test_nivel_y_sin_decision_para_pendientes(self):
        self.assertEqual(self.ids(self.lider, "?nivel=alto"),
                         [self.p16, self.p10])
        self.assertEqual(self.ids(self.lider, "?nivel=alto&sin_decision=1"),
                         [self.p10])
        self.assertEqual(self.ids(self.lider, "?nivel=medio,bajo"),
                         [self.p14, self.p12])
        self.assertEqual(
            self.ids(self.lider, "?sin_decision=1&desde=2026-11-12"),
            [self.p14, self.p12])

    def test_decision_por_la_ultima_decision(self):
        # p12: posponer y después autorizar (cuenta la última); p14: posponer.
        for pk, tipo, minutos in ((self.p12, "posponer", 2), (self.p12, "autorizar", 1),
                                  (self.p14, "posponer", 1)):
            d = DecisionDespliegue.objects.create(prediccion_id=pk, usuario=self.lider,
                                                  decision=tipo)
            DecisionDespliegue.objects.filter(pk=d.pk).update(
                creada_en=timezone.now() - timedelta(minutes=minutos))
        self.assertEqual(self.ids(self.lider, "?decision=autorizar"), [self.p16, self.p12])
        self.assertEqual(self.ids(self.lider, "?decision=posponer"), [self.p14])
        self.assertEqual(self.ids(self.lider, "?decision=solicitar_revision"), [])
        self.assertEqual(self.ids(self.lider, "?decision=sin_decision"), [self.p10])
        # Con nivel y paginación.
        r = self.cliente(self.lider).get("/api/predicciones/?decision=autorizar&nivel=alto&pagina=1")
        self.assertEqual([p["id"] for p in r.json()["resultados"]], [self.p16])

    def test_busqueda_por_repositorio(self):
        self.assertEqual(self.ids(self.lider, "?repo=TIENDA"),
                         [self.p16, self.p14, self.p12, self.p10])
        self.assertEqual(self.ids(self.lider, "?repo=acme/tie"), [self.p16, self.p14, self.p12, self.p10])
        self.assertEqual(self.ids(self.lider, "?repo=otro"), [])
        self.assertEqual(self.ids(self.lider, "?repo=%20%20"), [self.p16, self.p14, self.p12, self.p10])

    def test_parametros_no_validos(self):
        api = self.cliente(self.lider)
        for consulta, campo in (("?decision=aprobar", "decision"),
                                ("?desde=12/11/2026", "desde"),
                                ("?hasta=2026-02-30", "hasta"),
                                ("?desde=2026-11-15&hasta=2026-11-10", "desde"),
                                ("?nivel=critico", "nivel"),
                                ("?orden=azar", "orden"),
                                ("?origen=sombra", "origen")):
            with self.subTest(consulta=consulta):
                r = api.get(f"/api/predicciones/{consulta}")
                self.assertEqual(r.status_code, 400)
                self.assertIn(campo, r.json())

    def test_los_filtros_no_afectan_al_detalle(self):
        r = self.cliente(self.lider).get(
            f"/api/predicciones/{self.p10}/?desde=2026-11-15")
        self.assertEqual(r.status_code, 200)
