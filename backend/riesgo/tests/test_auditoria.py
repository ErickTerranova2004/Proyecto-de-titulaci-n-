"""Cada vía de escritura llena los campos de auditoría (riesgo/auditoria.py):
usu_creacion, fec_creacion, usu_modificacion y fec_modificacion, con el
usuario de la petición (API), del comando o del lote."""

import importlib
import pkgutil
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from riesgo import auditoria
from riesgo.models import (AccesoRepositorio, Commit, DecisionDespliegue,
                           EjecucionWorkflow, PendienteDespliegue, Prediccion,
                           PrediccionEjecucion, Repositorio, SeguimientoLote,
                           VersionModelo, Workflow)
from riesgo.services import lote
from riesgo.tests import test_api
from riesgo.tests.test_validacion_prospectiva import (CORTE, GitHubFalso,
                                                      momento)


def auditada(test, fila, creo, modifico=None):
    fila.refresh_from_db()
    test.assertEqual(fila.usu_creacion, creo, f"usu_creacion de {fila!r}")
    test.assertEqual(fila.usu_modificacion, modifico or creo,
                     f"usu_modificacion de {fila!r}")
    test.assertEqual(fila.est_registro, "A")
    for campo in fila._meta.concrete_fields:
        if campo.column in ("fec_creacion", "fec_modificacion"):
            test.assertIsNotNone(getattr(fila, campo.attname), campo.column)


class MecanismoTest(TestCase):
    """save, update_fields, update(), bulk_create y bulk_update."""

    def test_crear_y_modificar_con_save(self):
        with auditoria.como("ana"):
            repo = Repositorio.objects.create(nombre_completo="a/b",
                                              propietario="a", nombre="b")
        auditada(self, repo, "ana")
        creado, modificado = repo.creado_en, repo.fec_modificacion
        with auditoria.como("luis"):
            repo.nombre = "c"
            repo.save()
        auditada(self, repo, "ana", "luis")
        self.assertEqual(repo.creado_en, creado)  # la creación no cambia
        self.assertGreater(repo.fec_modificacion, modificado)

    def test_save_con_update_fields_tambien_audita(self):
        with auditoria.como("ana"):
            repo = Repositorio.objects.create(nombre_completo="a/b",
                                              propietario="a", nombre="b")
        with auditoria.como("luis"):
            repo.est_registro = "I"
            repo.save(update_fields=["est_registro"])
        repo.refresh_from_db()
        self.assertEqual((repo.est_registro, repo.usu_modificacion), ("I", "luis"))

    def test_queryset_update_y_bulk_update(self):
        with auditoria.como("ana"):
            repos = [Repositorio.objects.create(
                nombre_completo=f"a/{i}", propietario="a", nombre=str(i))
                for i in range(2)]
        with auditoria.como("luis"):
            Repositorio.objects.filter(nombre="0").update(es_prueba=True)
        auditada(self, repos[0], "ana", "luis")
        auditada(self, repos[1], "ana")
        with auditoria.como("eva"):
            repos[1].es_prueba = True
            Repositorio.objects.bulk_update(repos[1:], ["es_prueba"])
        auditada(self, repos[1], "ana", "eva")

    def test_bulk_create(self):
        u = User.objects.create_user("u")
        with auditoria.como("ana"):
            repo = Repositorio.objects.create(nombre_completo="a/b",
                                              propietario="a", nombre="b")
            AccesoRepositorio.objects.bulk_create(
                [AccesoRepositorio(usuario=u, repositorio=repo)])
        auditada(self, AccesoRepositorio.objects.get(), "ana")

    def test_sin_contexto_queda_como_sistema(self):
        repo = Repositorio.objects.create(nombre_completo="a/b",
                                          propietario="a", nombre="b")
        auditada(self, repo, auditoria.USUARIO_SISTEMA)

    def test_todas_las_tablas_propias_estan_auditadas(self):
        for modelo in (Repositorio, AccesoRepositorio, Workflow, Commit,
                       EjecucionWorkflow, VersionModelo, Prediccion,
                       PrediccionEjecucion, DecisionDespliegue,
                       SeguimientoLote, PendienteDespliegue):
            columnas = {f.column for f in modelo._meta.concrete_fields}
            self.assertTrue({"est_registro", "usu_creacion", "fec_creacion",
                             "usu_modificacion", "fec_modificacion"}
                            <= columnas, modelo.__name__)
            self.assertIsInstance(modelo.objects.all(),
                                  auditoria.AuditoriaQuerySet, modelo.__name__)

    def test_todos_los_comandos_fijan_su_usuario(self):
        from riesgo.management import commands
        for info in pkgutil.iter_modules(commands.__path__):
            modulo = importlib.import_module(f"{commands.__name__}.{info.name}")
            self.assertTrue(issubclass(modulo.Command, auditoria.ComandoAuditado),
                            info.name)


@override_settings(GEMINI_API_KEY="")
class ApiAuditadaTest(TestCase):
    """La API atribuye cada escritura al usuario del token (middleware)."""

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente
    predecir = test_api.ApiTest.predecir
    verificar = test_api.ApiTest.verificar
    run_real = test_api.ApiTest.run_real
    decidir = test_api.ApiTest.decidir

    def test_analisis_decision_asignacion_y_verificacion(self):
        id_ = self.predecir(self.dev).json()["id"]
        p = Prediccion.objects.get(id=id_)
        auditada(self, p, "dev")
        auditada(self, p.commit, "dev")
        for fila in PrediccionEjecucion.objects.filter(prediccion=p):
            auditada(self, fila, "dev")
        for ejecucion in p.ejecuciones_previas.all():
            auditada(self, ejecucion, "dev")

        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assertEqual(self.decidir(self.lider, id_, fecha_limite=manana)
                         .status_code, 201)
        decision = DecisionDespliegue.objects.get(prediccion=p)
        auditada(self, decision, "lider")
        asignacion = self.cliente(self.dev).get("/api/asignaciones/").json()[0]
        self.cliente(self.dev).post(f"/api/asignaciones/{asignacion['id']}/vista/")
        auditada(self, decision, "lider", "dev")

        r = self.verificar(self.lider, id_, [self.run_real(
            id_, 5, conclusion="success")], [])
        self.assertEqual(r.status_code, 200, r.content)
        auditada(self, p, "dev", "lider")
        auditada(self, p.ejecucion_real, "lider")

    def test_gestion_de_accesos_workflows_y_modelos(self):
        otro = Repositorio.objects.create(nombre_completo="acme/otro",
                                          propietario="acme", nombre="otro")
        r = self.cliente(self.admin).put(
            f"/api/gestion/usuarios/{self.dev.id}/repositorios/",
            {"repositorios": [self.repo.id, otro.id]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        auditada(self, AccesoRepositorio.objects.get(usuario=self.dev,
                                                     repositorio=otro), "admin")

        workflow = Workflow.objects.get(repositorio=self.repo,
                                        path=".github/workflows/ci.yml")
        r = self.cliente(self.admin).post(
            "/api/gestion/workflows/validar/",
            {"ids": [workflow.id], "validado": True, "evidencia": "Paso deploy"},
            format="json")
        self.assertEqual(r.json()["actualizados"], 1)
        auditada(self, workflow, auditoria.USUARIO_SISTEMA, "admin")

        modelo = VersionModelo.objects.order_by("id").first()
        self.assertEqual(self.cliente(self.admin).post(
            f"/api/modelos/{modelo.id}/activar/").status_code, 200)
        for version in VersionModelo.objects.all():
            auditada(self, version, "comando:registrar_modelo", "admin")


@override_settings(GEMINI_API_KEY="")
class LoteYComandosAuditadosTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("registrar_modelo", stdout=StringIO())
        cls.repo = Repositorio.objects.create(
            nombre_completo="acme/tienda", propietario="acme", nombre="tienda")
        cls.workflow = Workflow.objects.create(
            repositorio=cls.repo, path=".github/workflows/deploy.yml",
            despliegue_validado=True, evidencia_validacion="prueba")
        cls.usuario = User.objects.create_user("analisis_lote")
        cls.dev = User.objects.create_user("dev")

    def test_pasada_del_lote(self):
        gh = GitHubFalso()
        gh.sesion = type("S", (), {"llamadas": 0, "sin_cambios": 0})()
        gh.limite = lambda: {"remaining": 1, "limit": 1}
        commit = Commit.objects.create(repositorio=self.repo, sha=f"{3:040d}")
        interactivo = Prediccion.objects.create(
            usuario=self.dev, workflow=self.workflow, commit=commit,
            version_modelo=VersionModelo.objects.get(activo=True),
            evento="push", variables={}, probabilidad=0.1, nivel="bajo",
            factores=[], recomendaciones=[], datos_github_extraidos_en=CORTE)
        Prediccion.objects.filter(id=interactivo.id).update(
            creada_en=momento(10, 8))
        with mock.patch.object(lote, "cliente_contado", return_value=gh):
            call_command("analizar_lote", stdout=StringIO())
        # El análisis interactivo lo enlaza la pasada del lote.
        auditada(self, interactivo, auditoria.USUARIO_SISTEMA, "analisis_lote")
        creadas = Prediccion.objects.filter(origen="lote")
        self.assertTrue(creadas.exists())
        for p in creadas:
            auditada(self, p, "analisis_lote")
            auditada(self, p.ejecucion_real, "analisis_lote")
        auditada(self, SeguimientoLote.objects.get(), "analisis_lote")
        auditada(self, PendienteDespliegue.objects.get(), "analisis_lote")

    def test_comandos_de_registro(self):
        auditada(self, VersionModelo.objects.get(activo=True),
                 "comando:registrar_modelo")
        call_command("crear_usuario", "nuevo_dev", "--rol", "desarrollador",
                     "--password", "Clave-Prueba-2026", "--repos",
                     "acme/tienda", stdout=StringIO())
        auditada(self, AccesoRepositorio.objects.get(
            usuario__username="nuevo_dev"), "comando:crear_usuario")
