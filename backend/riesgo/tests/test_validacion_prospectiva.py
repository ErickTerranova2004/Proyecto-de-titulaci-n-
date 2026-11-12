"""Validación prospectiva de v2: fecha de corte, análisis en lote y registro
de los repositorios del dataset."""

import re
import tempfile
from unittest import mock
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from riesgo.models import (AccesoRepositorio, Commit, EjecucionWorkflow,
                           Prediccion, Repositorio, SeguimientoLote,
                           VersionModelo, Workflow)
from riesgo.services import lote
from riesgo.tests import test_api

CORTE = datetime(2026, 11, 9, 16, 9, 30, tzinfo=timezone.utc)


def momento(dia, hora=12):
    return datetime(2026, 11, dia, hora, tzinfo=timezone.utc)


def iso(m):
    return m.strftime("%Y-%m-%dT%H:%M:%SZ")


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("registrar_modelo", stdout=StringIO())
        cls.version = VersionModelo.objects.get(activo=True)
        cls.repo = Repositorio.objects.create(
            nombre_completo="acme/tienda", propietario="acme", nombre="tienda")
        cls.workflow = Workflow.objects.create(
            repositorio=cls.repo, path=".github/workflows/deploy.yml",
            despliegue_validado=True, evidencia_validacion="prueba")
        cls.usuario = User.objects.create_user("analisis_lote")


class FechaCorteTest(Base):
    def _prediccion(self, origen, inicio_real, creada_en=None):
        commit = Commit.objects.create(repositorio=self.repo,
                                       sha=f"{Commit.objects.count():040d}")
        ejecucion = EjecucionWorkflow.objects.create(
            workflow=self.workflow, commit=commit,
            run_id=1000 + Commit.objects.count(), iniciada_en=inicio_real,
            extraida_en=inicio_real, etiqueta="despliegue_no_completado")
        p = Prediccion.objects.create(
            usuario=self.usuario, workflow=self.workflow, commit=commit,
            version_modelo=self.version, evento="push", variables={},
            probabilidad=0.5, nivel="alto", factores=[], recomendaciones=[],
            origen=origen, ejecucion_real=ejecucion,
            momento_variables=inicio_real if origen == "lote" else None,
            datos_github_extraidos_en=inicio_real)
        if creada_en:
            Prediccion.objects.filter(id=p.id).update(creada_en=creada_en)
        return p

    def test_fecha_corte_en_los_metadatos_de_v2(self):
        self.assertEqual(self.version.version, "v2")
        self.assertEqual(self.version.metadatos["fecha_corte"],
                         "2026-11-09T16:09:30Z")

    def test_supervision_solo_cuenta_ejecuciones_posteriores_al_corte(self):
        self._prediccion("lote", momento(10))            # cuenta
        self._prediccion("lote", momento(1))             # vista en el entrenamiento
        self._prediccion("lote", CORTE)                  # justo en el corte: no
        reciente = self._prediccion("interactivo", datetime.now(timezone.utc))
        self._prediccion("interactivo", momento(5), creada_en=momento(4))
        Prediccion.objects.filter(id=reciente.id).update(
            creada_en=momento(10, 8))
        admin = test_api.ApiTest._usuario("admin", "administrador", [])
        datos = test_api.ApiTest.cliente(self, admin).get(
            f"/api/modelos/{self.version.id}/supervision/").json()
        self.assertEqual(datos["fecha_corte"], "2026-11-09T16:09:30Z")
        self.assertEqual(datos["predicciones"], 2)
        self.assertEqual(datos["evaluables"], 2)
        self.assertEqual(datos["predicciones_anteriores_al_corte"], 3)
        self.assertEqual(datos["predicciones_lote"], 1)

    def test_lote_exige_la_ejecucion_del_momento_de_las_variables(self):
        p = self._prediccion("lote", momento(10))
        p.momento_variables = momento(11)
        with self.assertRaises(Exception):
            p.clean()


class GitHubFalso:
    """Ejecuciones del workflow: 2 antes del corte y 4 después."""

    def __init__(self):
        self.runs = [
            self._run(1, momento(5), "success"),
            self._run(2, momento(8), "failure"),
            self._run(3, momento(10), "success"),
            self._run(4, momento(10, 15), "failure"),
            self._run(5, momento(11), "cancelled"),
            self._run(6, momento(11, 13), None, status="in_progress"),
        ]

    @staticmethod
    def _run(i, inicio, conclusion, status="completed"):
        return {"id": i, "run_attempt": 1, "status": status,
                "conclusion": conclusion, "event": "push",
                "head_branch": "main", "head_sha": f"{i:040d}",
                "workflow_id": 7, "check_suite_id": None,
                "run_started_at": iso(inicio), "created_at": iso(inicio),
                "updated_at": iso(inicio)}

    listados = None
    consultadas = None

    def get_condicional(self, ruta, params=None, etag=""):
        """Listado con `created=>=desde`; 304 si nada cambió desde el ETag."""
        if ruta.endswith("/git/ref/heads/main"):
            return {"object": {"sha": self.runs[-1]["head_sha"]}}, ""
        if "created" not in (params or {}):  # último despliegue correcto
            return {"workflow_runs": [r for r in self.runs[::-1]
                                      if r["conclusion"] == "success"]}, ""
        self.listados = (self.listados or []) + [params["created"]]
        desde = params["created"][2:]
        runs = [r for r in self.runs if r["created_at"] >= desde]
        actual = str(hash(repr(runs)))
        if etag and etag == actual:
            return None, etag
        return {"total_count": len(runs), "workflow_runs": runs}, actual

    def ejecuciones_workflow(self, repo, path, n=20, head_sha=None):
        return [r for r in self.runs if r["head_sha"] == head_sha]

    def get(self, ruta, params=None):
        una = re.search(r"/actions/runs/(\d+)$", ruta)
        if una:
            self.consultadas = (self.consultadas or []) + [int(una.group(1))]
            return next(r for r in self.runs if r["id"] == int(una.group(1)))
        if ruta.endswith("/runs"):
            return {"total_count": len(self.runs), "workflow_runs": self.runs}
        if ruta.endswith("/pulls"):
            return []
        if ruta.endswith("/check-runs"):
            return {"check_runs": []}
        return {"sha": ruta.rsplit("/", 1)[-1], "commit": {
            "message": "fix: algo", "author": {"name": "dev"},
            "committer": {"date": "2026-11-01T00:00:00Z"}},
            "stats": {"additions": 1, "deletions": 1}, "files": [{}]}

    def contenido_workflow(self, repo, workflow_path, ref):
        return ""

    def jobs_intento(self, repo, run_id, intento):
        ok = "success" if run_id == 3 else "failure"
        return [{"id": 1, "name": "deploy", "conclusion": ok, "started_at": "x",
                 "steps": [{"number": 1, "name": "Deploy to ECS",
                            "conclusion": ok}]}]


@override_settings(GEMINI_API_KEY="")
class AnalisisLoteTest(Base):
    def test_analiza_solo_las_terminadas_posteriores_al_corte(self):
        gh = GitHubFalso()
        resumen, creadas = lote.analizar_workflow(
            gh, self.workflow, CORTE, self.version, self.usuario)
        self.assertEqual(resumen, {"analizadas": 2, "pendientes": 1,
                                   "no_analizables": 1, "ya_analizadas": 0,
                                   "enlazadas_interactivo": 0,
                                   "sin_cambios": 0})
        por_run = {p.ejecucion_real.run_id: p for p in creadas}
        self.assertEqual(set(por_run), {3, 4})
        p3 = por_run[3]
        self.assertEqual(p3.origen, "lote")
        self.assertEqual(p3.momento_variables, momento(10))
        self.assertEqual(p3.ejecucion_real.etiqueta, "despliegue_completado")
        self.assertEqual(por_run[4].ejecucion_real.etiqueta,
                         "despliegue_no_completado")
        self.assertEqual(p3.version_modelo.version, "v2")
        self.assertTrue(p3.recomendacion)
        # Variables con lo anterior al inicio: 2 previas, la última falló.
        self.assertEqual(p3.variables["wf_n_prev"], 2)
        self.assertEqual(p3.variables["wf_ultimo_fallo"], 1)
        # No se guardan las ejecuciones históricas, solo las evaluadas.
        self.assertEqual(set(EjecucionWorkflow.objects.values_list(
            "run_id", flat=True)), {3, 4})

    def test_repetir_solo_analiza_lo_nuevo(self):
        gh = GitHubFalso()
        lote.analizar_workflow(gh, self.workflow, CORTE, self.version,
                               self.usuario)
        gh.runs[-1].update(status="completed", conclusion="success")
        resumen, creadas = lote.analizar_workflow(
            gh, self.workflow, CORTE, self.version, self.usuario)
        self.assertEqual(resumen["ya_analizadas"], 2)
        self.assertEqual([p.ejecucion_real.run_id for p in creadas], [6])
        self.assertEqual(Prediccion.objects.filter(origen="lote").count(), 3)


@override_settings(GEMINI_API_KEY="")
class ListadoIncrementalTest(Base):
    def analizar(self, gh):
        return lote.analizar_workflow(gh, self.workflow, CORTE, self.version,
                                      self.usuario)

    def test_primera_pasada_desde_el_corte_y_luego_ultima_pasada_menos_48h(self):
        gh = GitHubFalso()
        self.analizar(gh)
        self.assertEqual(gh.listados, [">=2026-11-09T16:09:30Z"])
        seguimiento = SeguimientoLote.objects.get(workflow=self.workflow)
        self.assertEqual([p["id"] for p in seguimiento.pendientes], [6])
        # Pasada anterior el 20 a las 15:00 → lista desde el 18 a las 00:00.
        SeguimientoLote.objects.filter(id=seguimiento.id).update(
            listado_hasta=momento(20, 15), etag="")
        gh.runs[-1].update(status="completed", conclusion="success")
        resumen, creadas = self.analizar(gh)
        self.assertEqual(gh.listados[-1], ">=2026-11-18T00:00:00Z")
        # La pendiente (creada el 11) queda fuera de la ventana: se consulta
        # sola, y como ya terminó, se analiza.
        self.assertEqual(gh.consultadas, [6])
        self.assertEqual([p.ejecucion_real.run_id for p in creadas], [6])
        self.assertEqual(SeguimientoLote.objects.get(
            workflow=self.workflow).pendientes, [])

    def test_nunca_lista_antes_del_corte(self):
        seguimiento = SeguimientoLote(listado_hasta=momento(10))
        self.assertEqual(lote.inicio_listado(CORTE, seguimiento), CORTE)

    def fijar_pasada(self, momento_pasada):
        """La pasada anterior a una hora conocida (la real es «ahora»)."""
        SeguimientoLote.objects.filter(workflow=self.workflow).update(
            listado_hasta=momento_pasada)

    def test_etag_sin_cambios_no_vuelve_a_analizar(self):
        gh = GitHubFalso()
        self.analizar(gh)
        # Pasada anterior el 11 → ventana desde el corte: la misma URL.
        self.fijar_pasada(momento(11, 6))
        resumen, creadas = self.analizar(gh)
        self.assertEqual(resumen["sin_cambios"], 1)
        self.assertEqual(creadas, [])
        self.assertIsNone(gh.consultadas)  # la pendiente está en la ventana
        # Se conserva la pendiente para la pasada siguiente.
        self.assertEqual([p["id"] for p in SeguimientoLote.objects.get(
            workflow=self.workflow).pendientes], [6])
        # Cuando cambia algo, el ETag ya no coincide y se analiza.
        gh.runs[-1].update(status="completed", conclusion="failure")
        self.fijar_pasada(momento(11, 6))
        resumen, creadas = self.analizar(gh)
        self.assertEqual(resumen["sin_cambios"], 0)
        self.assertEqual([p.ejecucion_real.run_id for p in creadas], [6])

    def test_cliente_envia_el_etag_y_el_304_no_cuenta_como_llamada(self):
        import requests
        respuestas = []

        def responder(sesion, metodo, url, **kwargs):
            respuesta = requests.Response()
            etag = kwargs["headers"].get("If-None-Match")
            respuesta.status_code = 304 if etag == '"v1"' else 200
            respuesta._content = b'{"total_count": 0, "workflow_runs": []}'
            respuesta.headers["ETag"] = '"v1"'
            respuestas.append(etag)
            return respuesta

        gh = lote.cliente_contado()
        with mock.patch.object(requests.Session, "request", responder):
            datos, etag = gh.get_condicional("/x", {"page": 1})
            self.assertEqual((datos["total_count"], etag), (0, '"v1"'))
            self.assertEqual(gh.get_condicional("/x", {"page": 1}, etag),
                             (None, '"v1"'))
        self.assertEqual(respuestas, [None, '"v1"'])
        self.assertEqual((gh.sesion.llamadas, gh.sesion.sin_cambios), (1, 1))

    def test_contar_no_guarda_estado(self):
        lote.revisar_workflow(GitHubFalso(), self.workflow, CORTE, self.version)
        self.assertFalse(SeguimientoLote.objects.exists())


@override_settings(GEMINI_API_KEY="")
class InteractivosEnLoteTest(Base):
    """Opción A: el lote se salta lo enlazado a un análisis interactivo, y
    cada pasada enlaza los interactivos pendientes."""

    def interactivo(self, sha, creada_en, repo=None, version=None):
        workflow = self.workflow
        if repo is not None:
            workflow = Workflow.objects.create(
                repositorio=repo, path=".github/workflows/deploy.yml",
                despliegue_validado=True, evidencia_validacion="prueba")
        commit, _ = Commit.objects.get_or_create(repositorio=workflow.repositorio,
                                                 sha=sha)
        p = Prediccion.objects.create(
            usuario=self.usuario, workflow=workflow, commit=commit,
            version_modelo=version or self.version, evento="push",
            variables={}, probabilidad=0.2, nivel="bajo", factores=[],
            recomendaciones=[], datos_github_extraidos_en=creada_en)
        Prediccion.objects.filter(id=p.id).update(creada_en=creada_en)
        p.refresh_from_db()
        return p

    def test_salta_ejecuciones_enlazadas_a_un_analisis_interactivo(self):
        gh = GitHubFalso()
        p = self.interactivo(f"{3:040d}", momento(10, 8))
        enlazada, _ = lote.enlazar_resultado(gh, p)
        self.assertTrue(enlazada)
        resumen, creadas = lote.analizar_workflow(
            gh, self.workflow, CORTE, self.version, self.usuario)
        self.assertEqual([c.ejecucion_real.run_id for c in creadas], [4])
        self.assertEqual(resumen["enlazadas_interactivo"], 1)
        # Una sola predicción por despliegue real.
        self.assertEqual(Prediccion.objects.filter(
            ejecucion_real__run_id=3).count(), 1)

    def test_interactivo_de_otro_modelo_no_impide_el_lote(self):
        gh = GitHubFalso()
        v1 = VersionModelo.objects.create(
            version="v1-prueba", nombre_modelo="x", archivo="x",
            archivo_explicacion="x", metadatos={})
        lote.enlazar_resultado(gh, self.interactivo(f"{3:040d}", momento(10, 8),
                                                    version=v1))
        _, creadas = lote.analizar_workflow(gh, self.workflow, CORTE,
                                            self.version, self.usuario)
        self.assertEqual(sorted(c.ejecucion_real.run_id for c in creadas), [3, 4])

    def test_la_pasada_enlaza_los_interactivos_pendientes(self):
        demo = Repositorio.objects.create(
            nombre_completo="yo/demo", propietario="yo", nombre="demo",
            es_demostracion=True)
        prueba = Repositorio.objects.create(
            nombre_completo="yo/prueba", propietario="yo", nombre="prueba",
            es_prueba=True)
        inactivo = Repositorio.objects.create(
            nombre_completo="yo/viejo", propietario="yo", nombre="viejo",
            est_registro="I")
        real = self.interactivo(f"{3:040d}", momento(10, 8))
        de_demo = self.interactivo(f"{4:040d}", momento(10, 8), repo=demo)
        antes = self.interactivo(f"{4:040d}", momento(10, 16))  # run 4 empezó antes
        self.interactivo(f"{4:040d}", momento(10, 8), repo=prueba)
        self.interactivo(f"{4:040d}", momento(10, 8), repo=inactivo)
        gh = GitHubFalso()
        resumen, enlazadas, errores = lote.verificar_interactivos(gh)
        self.assertEqual(errores, [])
        self.assertEqual(resumen, {"enlazadas": 2, "pendientes": 1})
        self.assertEqual({p.id for p in enlazadas}, {real.id, de_demo.id})
        real.refresh_from_db()
        self.assertEqual(real.ejecucion_real.run_id, 3)
        self.assertEqual(real.ejecucion_real.etiqueta, "despliegue_completado")
        antes.refresh_from_db()
        self.assertIsNone(antes.ejecucion_real)

    def test_ignora_la_ejecucion_omitida_del_prerelease(self):
        # Caso lumos-web: v2.0.25-rc.0 (skipped) y minutos después v2.0.25.
        gh = GitHubFalso()
        sha = f"{3:040d}"
        gh.runs = [GitHubFalso._run(3, momento(12, 10), "skipped"),
                   GitHubFalso._run(3, momento(12, 11), "success")]
        gh.runs[0]["id"] = 30
        for r in gh.runs:
            r["head_sha"] = sha
        p = self.interactivo(sha, momento(12, 8))
        enlazada, _ = lote.enlazar_resultado(gh, p)
        self.assertTrue(enlazada)
        self.assertEqual(p.ejecucion_real.run_id, 3)
        self.assertEqual(p.ejecucion_real.conclusion, "success")

    def test_no_verifica_analisis_de_hace_mas_de_30_dias(self):
        viejo = self.interactivo(f"{3:040d}", momento(10, 8))
        Prediccion.objects.filter(id=viejo.id).update(
            creada_en=datetime.now(timezone.utc) - timedelta(days=31))
        self.assertFalse(lote.interactivos_pendientes().exists())

    def test_comando_enlaza_primero_el_interactivo_y_el_lote_no_lo_duplica(self):
        gh = GitHubFalso()
        gh.sesion = type("S", (), {"llamadas": 0, "sin_cambios": 0})()
        gh.limite = lambda: {"remaining": 4999, "limit": 5000}
        p = self.interactivo(f"{3:040d}", momento(10, 8))
        salida = StringIO()
        with mock.patch.object(lote, "cliente_contado", return_value=gh):
            call_command("analizar_lote", stdout=salida)
        p.refresh_from_db()
        self.assertEqual(p.ejecucion_real.run_id, 3)
        self.assertEqual(Prediccion.objects.filter(
            ejecucion_real__run_id=3).count(), 1)
        self.assertEqual(set(Prediccion.objects.filter(origen="lote")
                             .values_list("ejecucion_real__run_id", flat=True)),
                         {4})
        self.assertIn("Análisis interactivos: {'enlazadas': 1", salida.getvalue())


class RegistrarReposV2Test(TestCase):
    INFORME = """# Informe

## Lista final

| # | Repositorio | Organización | Plataforma | Ejec. 6 meses | y=0 / y=1 | % fallos | Evidencia |
|---|---|---|---|---:|---|---:|---|
| 1 | [org/uno](https://github.com/org/uno/blob/HEAD/.github/workflows/deploy.yml) ⚠ atípico | org | AWS · ECS | 12 | 10 / 0 (10 / 0) | 0 | Despliega la API a ECS en producción. |
| 2 | [org/dos](https://github.com/org/dos/blob/HEAD/.github/workflows/cd.yaml) | org | Fly.io · Machines | 9 | 5 / 1 (5 / 1) | 17 | Despliega la web con flyctl deploy. |

## Excluidos
"""

    _usuario = test_api.ApiTest._usuario

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    def setUp(self):
        self.archivo = Path(tempfile.mkdtemp()) / "informe.md"
        self.archivo.write_text(self.INFORME, encoding="utf-8")
        Repositorio.objects.create(nombre_completo="org/dos", propietario="org",
                                   nombre="dos", est_registro="I")

    def ejecutar(self, *extra):
        call_command("registrar_repos_v2", "--informe", str(self.archivo),
                     "--esperados", "2", "--validado-por", "admin",
                     "--asignar", "dev", "lider", *extra, stdout=StringIO())

    def test_registra_activos_validados_y_asignados_sin_ejecuciones(self):
        self.ejecutar("--aplicar")
        for nombre, ruta in (("org/uno", ".github/workflows/deploy.yml"),
                             ("org/dos", ".github/workflows/cd.yaml")):
            repo = Repositorio.objects.get(nombre_completo=nombre)
            self.assertEqual(repo.est_registro, "A")
            wf = repo.workflows.get()
            self.assertEqual(wf.path, ruta)
            self.assertTrue(wf.despliegue_validado)
            self.assertIn("Lista final", wf.evidencia_validacion)
            self.assertEqual(set(AccesoRepositorio.objects.filter(
                repositorio=repo).values_list("usuario__username", flat=True)),
                {"dev", "lider"})
        self.assertFalse(EjecucionWorkflow.objects.exists())
        self.ejecutar("--aplicar")  # idempotente
        self.assertEqual(Workflow.objects.filter(
            repositorio__nombre_completo__startswith="org/").count(), 2)

    def test_sin_aplicar_no_guarda_y_comprueba_el_numero(self):
        self.ejecutar()
        self.assertFalse(Repositorio.objects.filter(nombre_completo="org/uno").exists())
        with self.assertRaises(CommandError):
            call_command("registrar_repos_v2", "--informe", str(self.archivo),
                         "--validado-por", "admin", stdout=StringIO())


@override_settings(GEMINI_API_KEY="")
class VerificarConYamlTest(TestCase):
    """«Verificar resultado real» lee el YAML del workflow en el commit."""

    @classmethod
    def setUpTestData(cls):
        test_api.ApiTest.setUpTestData.__func__(cls)

    _usuario = test_api.ApiTest._usuario
    cliente = test_api.ApiTest.cliente
    predecir = test_api.ApiTest.predecir
    run_real = test_api.ApiTest.run_real

    def verificar(self, yaml_texto):
        from unittest import mock
        from riesgo.services import github
        from riesgo.tests.test_etiquetado import jobs_kanvas
        id_ = self.predecir(self.dev).json()["id"]
        falso = type("Falso", (test_api.ClienteFalso,), {
            "RUNS_REALES": [self.run_real(id_, 5, conclusion="success")],
            "JOBS": jobs_kanvas(), "YAML": yaml_texto})
        with mock.patch.object(github, "GitHubClient", falso):
            r = self.cliente(self.dev).post(f"/api/predicciones/{id_}/verificar/")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["ejecucion_real"]["etiqueta"]

    def test_caso_kanvas_rsync_deployments(self):
        from riesgo.tests.test_etiquetado import YAML_KANVAS
        self.assertEqual(self.verificar(YAML_KANVAS), "despliegue_completado")

    def test_sin_yaml_solo_cuentan_los_nombres(self):
        self.assertEqual(self.verificar(""), "excluida_sin_intento")
