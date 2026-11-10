"""Variables del modelo v2: mismo cálculo en la plataforma y en el dataset, y
sin información posterior al inicio del despliegue."""

import copy
import importlib.util
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.test import SimpleTestCase

from riesgo.services.features import (PARAMS_CHECKS, PARAMS_PULLS,
                                      calcular_variables, variables_desde_datos)

RAIZ = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "construir_dataset_v2", RAIZ / "scripts" / "construir_dataset_v2.py")
dataset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dataset)

REPO = "acme/tienda"
WORKFLOW = ".github/workflows/deploy.yml"
SHA, OTRO = "a" * 40, "b" * 40
M = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)  # inicio del despliegue


def t(**delta):
    return (M + timedelta(**delta)).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(id_, sha, inicio, fin, conclusion, suite, workflow_id=1, intento=1):
    return {"id": id_, "run_attempt": intento, "status": "completed",
            "conclusion": conclusion, "event": "push", "head_branch": "main",
            "head_sha": sha, "workflow_id": workflow_id, "check_suite_id": suite,
            "run_started_at": inicio, "created_at": inicio, "updated_at": fin}


def check(suite, conclusion, fin, estado="completed"):
    return {"check_suite": {"id": suite}, "status": estado,
            "conclusion": conclusion if estado == "completed" else None,
            "completed_at": fin if estado == "completed" else None}


def escenario():
    """Datos de GitHub tal como se descargan HOY (incluyen el futuro de M)."""
    despliegue = run(500, SHA, t(), t(minutes=10), "failure", 9500)
    runs_wf = [
        run(401, OTRO, t(days=-3), t(days=-3, minutes=10), "success", 9001),
        run(402, SHA, t(hours=-2), t(hours=-1, minutes=-50), "failure", 9002),
        # Empezó antes de M pero terminó después: en M aún estaba en curso.
        run(403, OTRO, t(minutes=-30), t(minutes=20), "failure", 9003),
        despliegue,
    ]
    runs_repo = runs_wf + [
        run(601, OTRO, t(days=-1), t(days=-1, minutes=5), "success", 9601, 2),
        run(602, OTRO, t(hours=1), t(hours=1, minutes=5), "failure", 9602, 2),
    ]
    commit = {"sha": SHA,
              "commit": {"message": "fix: corrige el pago\n\ndetalle",
                         "author": {"name": "dev"},
                         "committer": {"date": t(hours=-3)}},
              "stats": {"additions": 40, "deletions": 5, "total": 45},
              "files": [{"filename": f"f{i}.py"} for i in range(3)]}
    pulls = [{"number": 1, "created_at": t(days=-1)},
             {"number": 2, "created_at": t(days=1)}]  # posterior: no cuenta
    checks = [
        check(7001, "failure", t(hours=-1)),  # cuenta y falla
        check(7001, "success", t(hours=-1)),  # cuenta
        check(9002, "failure", t(hours=-1, minutes=-50)),  # mismo workflow
        check(9500, "failure", t(minutes=5)),  # la propia ejecución
        check(7002, "failure", t(minutes=30)),  # terminó después de M
        check(7003, None, None, estado="in_progress"),  # en curso
    ]
    return {"despliegue": despliegue, "runs_wf": runs_wf, "runs_repo": runs_repo,
            "commit": commit, "pulls": pulls, "checks": checks}


class GitHubFalso:
    """Imita la API para el script del dataset y registra las consultas."""

    def __init__(self, datos, intentos=None):
        self.datos, self.intentos, self.consultas = datos, intentos or {}, []

    def get(self, ruta, params=None):
        self.consultas.append((ruta, params))
        base = f"/repos/{REPO}/commits/{SHA}"
        if ruta == base:
            return self.datos["commit"]
        if ruta == f"{base}/pulls":
            return self.datos["pulls"]
        if ruta == f"{base}/check-runs":
            return {"check_runs": self.datos["checks"]}
        if "/attempts/" in ruta:
            return self.intentos[int(ruta.rsplit("/", 1)[-1])]
        raise AssertionError(f"consulta inesperada: {ruta}")


class ClientePlataformaFalso:
    """Imita GitHubClient de la plataforma con los mismos datos."""

    def __init__(self, datos):
        self.datos = datos

    def commit(self, repo, sha):
        return self.datos["commit"]

    def ejecuciones_workflow(self, repo, path, n=20, head_sha=None):
        runs = self.datos["runs_wf"]
        return [r for r in runs if r["head_sha"] == head_sha] if head_sha else runs

    def ejecuciones_repositorio(self, repo, n=100):
        return self.datos["runs_repo"]

    def pulls_commit(self, repo, sha):
        return self.datos["pulls"]

    def checks_commit(self, repo, sha):
        return self.datos["checks"]


def del_dataset(datos, intentos=None, despliegue=None):
    gh = GitHubFalso(datos, intentos)
    variables = dataset.variables_ejecucion(
        gh, REPO, despliegue or datos["despliegue"], datos["runs_wf"],
        datos["runs_repo"], dataset.DatosCommit(gh, REPO))
    return variables, gh


def iguales(a, b):
    def normal(v):
        return "nan" if isinstance(v, float) and math.isnan(v) else v
    return {k: normal(v) for k, v in a.items()} == {k: normal(v) for k, v in b.items()}


class MismoCalculoTest(SimpleTestCase):
    def test_plataforma_y_dataset_coinciden_en_la_misma_ejecucion(self):
        datos = escenario()
        desde_dataset, gh = del_dataset(datos)
        desde_plataforma, _, _ = calcular_variables(
            ClientePlataformaFalso(datos), REPO, WORKFLOW, SHA, "main", "push",
            momento=M)
        self.assertTrue(iguales(desde_dataset, desde_plataforma),
                        f"{desde_dataset}\n!=\n{desde_plataforma}")
        # Mismas consultas que la plataforma (mismos parámetros).
        self.assertIn((f"/repos/{REPO}/commits/{SHA}/pulls", PARAMS_PULLS), gh.consultas)
        self.assertIn((f"/repos/{REPO}/commits/{SHA}/check-runs", PARAMS_CHECKS),
                      gh.consultas)

    def test_valores_esperados(self):
        v, _ = del_dataset(escenario())
        self.assertEqual((v["archivos_modificados"], v["lineas_anadidas"],
                          v["lineas_borradas"]), (3, 40, 5))
        # Checks: solo 7001 (dos); se excluyen el propio workflow, los
        # posteriores a M y los que están en curso.
        self.assertEqual((v["checks_n_prev"], v["checks_fallidos_prev"]), (2, 1))
        self.assertEqual(v["checks_tasa_fallo_prev"], 0.5)
        self.assertEqual(v["tiene_pr"], 1)
        # El mismo workflow ya terminó una ejecución con este commit (402).
        self.assertEqual(v["es_reintento"], 1)
        # Historial: 401 y 402; 403 terminó después de M.
        self.assertEqual(v["wf_n_prev"], 2)
        self.assertEqual(v["wf_ultimo_fallo"], 1.0)
        self.assertNotIn("reejecutado_por_otro", v)


class SinInformacionPosteriorTest(SimpleTestCase):
    def test_lo_posterior_al_inicio_del_despliegue_no_cambia_las_variables(self):
        datos = escenario()
        base, _ = del_dataset(datos)
        cambiado = copy.deepcopy(datos)
        # Todo lo que ocurrió después de M cambia de resultado o desaparece.
        for r in cambiado["runs_repo"]:
            if r["id"] in (403, 500, 602):
                r["conclusion"] = "success" if r["conclusion"] == "failure" else "failure"
        cambiado["runs_wf"] = [r for r in cambiado["runs_repo"]
                               if r["workflow_id"] == 1]
        cambiado["pulls"] = cambiado["pulls"][:1]
        cambiado["checks"] = [c for c in cambiado["checks"]
                              if c["completed_at"] and c["completed_at"] <= t()
                              and c["check_suite"]["id"] != 9500]
        cambiado["checks"].append(check(7004, "failure", t(seconds=1)))
        cambiado["despliegue"] = next(r for r in cambiado["runs_wf"] if r["id"] == 500)
        despues, _ = del_dataset(cambiado)
        self.assertTrue(iguales(base, despues), f"{base}\n!=\n{despues}")

    def test_check_terminado_un_segundo_despues_no_cuenta(self):
        datos = escenario()
        datos["checks"] = [check(7001, "failure", t(seconds=1))]
        v = variables_desde_datos(
            datos["commit"], "main", "push", M, [], [], [], [], datos["checks"])
        self.assertEqual(v["checks_n_prev"], 0)


class ReintentoTest(SimpleTestCase):
    def test_plataforma_sin_ejecuciones_previas_del_commit_no_es_reintento(self):
        datos = escenario()
        datos["runs_wf"] = [r for r in datos["runs_wf"] if r["id"] != 402]
        datos["runs_repo"] = [r for r in datos["runs_repo"] if r["id"] != 402]
        v, _, _ = calcular_variables(ClientePlataformaFalso(datos), REPO, WORKFLOW,
                                     SHA, "main", "push", momento=M)
        self.assertEqual(v["es_reintento"], 0)

    def test_intento_posterior_usa_sus_intentos_anteriores(self):
        datos = escenario()
        datos["runs_wf"] = [r for r in datos["runs_wf"] if r["id"] != 402]
        datos["runs_repo"] = [r for r in datos["runs_repo"] if r["id"] != 402]
        segundo = dict(datos["despliegue"], run_attempt=2)
        datos["runs_wf"] = [segundo if r["id"] == 500 else r for r in datos["runs_wf"]]
        primero = run(500, SHA, t(hours=-1), t(minutes=-40), "failure", 9500)
        v, gh = del_dataset(datos, intentos={1: primero}, despliegue=segundo)
        self.assertEqual(v["es_reintento"], 1)
        # El primer intento (fallido) ya existía: entra en el historial.
        self.assertEqual(v["wf_ultimo_fallo"], 1.0)
        self.assertIn((f"/repos/{REPO}/actions/runs/500/attempts/1", None), gh.consultas)
