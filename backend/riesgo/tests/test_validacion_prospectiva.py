"""Validación prospectiva de v2: fecha de corte, análisis en lote y registro
de los repositorios del dataset."""

import tempfile
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from riesgo.models import (AccesoRepositorio, Commit, EjecucionWorkflow,
                           Prediccion, Repositorio, VersionModelo, Workflow)
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

    def get(self, ruta, params=None):
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
                                   "no_analizables": 1, "ya_analizadas": 0})
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
