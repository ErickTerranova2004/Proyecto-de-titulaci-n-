"""Análisis en lote de ejecuciones posteriores a la fecha de corte.

Validación prospectiva del modelo activo: para cada ejecución terminada de un
workflow registrado que empezó después de la ejecución más reciente del
entrenamiento (metadatos.fecha_corte), se calculan las variables en el
momento en que empezó, solo con lo que existía antes (la misma función y las
mismas consultas que scripts/construir_dataset_v2.py), se predice con el
modelo activo y se etiqueta su resultado real con la API de jobs, igual que
el botón «Verificar resultado real».

Las ejecuciones que aún no han terminado se cuentan como pendientes y se
analizan al volver a ejecutar el lote. Solo lectura de la API de GitHub; no se
guardan las ejecuciones históricas usadas para calcular las variables (solo
la ejecución evaluada).
"""

import math
from datetime import datetime, timedelta, timezone

import requests
from django.db import transaction
from django.utils import timezone as dj_timezone

from riesgo.models import Prediccion
from riesgo.services.analisis_ia import _por_reglas
from riesgo.services.etiquetado import etiquetar_ejecucion
from riesgo.services.features import (PARAMS_CHECKS, PARAMS_PULLS, fecha,
                                      variables_desde_datos)
from riesgo.services.github import GitHubClient
from riesgo.services.predictor import predecir
from riesgo.services.trazabilidad import guardar_commit, guardar_ejecucion

PREVIAS_WORKFLOW = 4  # features.MAX_PREVIAS_WORKFLOW
PREVIAS_REPO = 100  # features.MAX_PREVIAS_REPO
VENTANAS_DIAS = (7, 30, 90, 180)
MAX_RESULTADOS = 1000  # límite de la API con el filtro `created`
CONCLUSIONES_ANALIZADAS = ("success", "failure")
CAMPOS_RUN = ("id", "run_attempt", "status", "conclusion", "event",
              "head_branch", "head_sha", "workflow_id", "check_suite_id",
              "run_started_at", "created_at", "updated_at")


class SesionContada(requests.Session):
    """Cuenta las peticiones reales a GitHub (las de la caché no cuentan)."""

    llamadas = 0

    def get(self, *args, **kwargs):
        self.llamadas += 1
        return super().get(*args, **kwargs)


def cliente_contado():
    return GitHubClient(sesion=SesionContada())


def iso(momento):
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resumir(run):
    return {k: run.get(k) for k in CAMPOS_RUN}


def listar(gh, ruta, desde, hasta):
    """Ejecuciones creadas en [desde, hasta] (divide el intervalo si supera el
    máximo de resultados de la API)."""
    params = {"created": f"{iso(desde)}..{iso(hasta)}", "per_page": 100}
    primera = gh.get(ruta, dict(params, page=1)) or {}
    total = primera.get("total_count", 0)
    if total > MAX_RESULTADOS and hasta - desde > timedelta(minutes=10):
        mitad = desde + (hasta - desde) / 2
        return (listar(gh, ruta, desde, mitad)
                + listar(gh, ruta, mitad + timedelta(seconds=1), hasta))
    runs = list(primera.get("workflow_runs", []))
    pagina = 2
    while len(runs) < min(total, MAX_RESULTADOS):
        nuevos = (gh.get(ruta, dict(params, page=pagina)) or {}).get(
            "workflow_runs", [])
        if not nuevos:
            break
        runs += nuevos
        pagina += 1
    return [resumir(r) for r in runs]


def historial(gh, ruta, primer_momento, ultimo_momento, minimo):
    """Ejecuciones desde antes del primer momento hasta el último, ampliando
    la ventana hasta tener `minimo` previas al primer momento."""
    for dias in VENTANAS_DIAS:
        runs = listar(gh, ruta, primer_momento - timedelta(days=dias),
                      ultimo_momento + timedelta(minutes=1))
        if sum(fecha(r["created_at"]) < primer_momento for r in runs) >= minimo:
            break
    unicos = {r["id"]: r for r in runs}
    return sorted(unicos.values(), key=lambda r: r["run_started_at"] or "")


class DatosCommit:
    """Commit, pull requests y checks de cada commit (una consulta por sha)."""

    def __init__(self, gh, repo):
        self.gh, self.repo, self.cache = gh, repo, {}

    def __call__(self, sha):
        if sha not in self.cache:
            base = f"/repos/{self.repo}/commits/{sha}"
            self.cache[sha] = (
                self.gh.get(base) or {},
                self.gh.get(f"{base}/pulls", PARAMS_PULLS) or [],
                (self.gh.get(f"{base}/check-runs", PARAMS_CHECKS) or {}).get(
                    "check_runs", []))
        return self.cache[sha]


def variables_ejecucion(gh, repo, run, runs_wf, runs_repo, datos_commit):
    """Variables de una ejecución con su inicio como momento del despliegue."""
    momento = fecha(run["run_started_at"])
    anteriores = [resumir(gh.get(
        f"/repos/{repo}/actions/runs/{run['id']}/attempts/{n}") or {})
        for n in range(1, run.get("run_attempt") or 1)]
    commit, pulls, checks = datos_commit(run["head_sha"])
    mismo_commit = [r for r in runs_wf
                    if r["head_sha"] == run["head_sha"]] + anteriores
    variables = variables_desde_datos(
        commit, run.get("head_branch") or "", run.get("event") or "", momento,
        runs_wf + anteriores, runs_repo + anteriores, mismo_commit, pulls,
        checks, intento=run.get("run_attempt") or 1, run_id=run["id"])
    return variables, commit


def ejecuciones_posteriores(gh, workflow, corte):
    """Ejecuciones del workflow que empezaron después de la fecha de corte."""
    repo = workflow.repositorio.nombre_completo
    archivo = workflow.path.rsplit("/", 1)[-1]
    runs = listar(gh, f"/repos/{repo}/actions/workflows/{archivo}/runs",
                  corte, datetime.now(timezone.utc) + timedelta(minutes=1))
    return [r for r in runs
            if r.get("run_started_at") and fecha(r["run_started_at"]) > corte]


def _json_seguro(variables):
    return {k: (None if isinstance(v, float) and math.isnan(v) else v)
            for k, v in variables.items()}


def clasificar(runs, analizadas):
    """Separa las ejecuciones en a analizar, pendientes y no analizables."""
    nuevas = [r for r in runs if r["id"] not in analizadas]
    terminadas = [r for r in nuevas if r.get("status") == "completed"]
    return {
        "analizar": [r for r in terminadas
                     if r.get("conclusion") in CONCLUSIONES_ANALIZADAS],
        "pendientes": [r for r in nuevas if r.get("status") != "completed"],
        "no_analizables": [r for r in terminadas
                           if r.get("conclusion") not in CONCLUSIONES_ANALIZADAS],
        "ya_analizadas": len(runs) - len(nuevas),
    }


def run_ids_analizados(workflow):
    return set(Prediccion.objects.filter(
        workflow=workflow, origen="lote").values_list(
        "ejecucion_real__run_id", flat=True))


def analizar_workflow(gh, workflow, corte, version, usuario):
    """Analiza y verifica las ejecuciones terminadas posteriores al corte.

    Devuelve el resumen del workflow y la lista de predicciones creadas.
    """
    repo = workflow.repositorio.nombre_completo
    grupos = clasificar(ejecuciones_posteriores(gh, workflow, corte),
                        run_ids_analizados(workflow))
    creadas = []
    if grupos["analizar"]:
        momentos = [fecha(r["run_started_at"]) for r in grupos["analizar"]]
        archivo = workflow.path.rsplit("/", 1)[-1]
        runs_wf = historial(gh, f"/repos/{repo}/actions/workflows/{archivo}/runs",
                            min(momentos), max(momentos), PREVIAS_WORKFLOW)
        runs_repo = historial(gh, f"/repos/{repo}/actions/runs",
                              min(momentos), max(momentos), PREVIAS_REPO)
        datos_commit = DatosCommit(gh, repo)
        for run in sorted(grupos["analizar"], key=lambda r: r["run_started_at"]):
            creadas.append(_analizar_run(gh, workflow, run, runs_wf, runs_repo,
                                         datos_commit, version, usuario))
    return {"analizadas": len(creadas),
            "pendientes": len(grupos["pendientes"]),
            "no_analizables": len(grupos["no_analizables"]),
            "ya_analizadas": grupos["ya_analizadas"]}, creadas


def _analizar_run(gh, workflow, run, runs_wf, runs_repo, datos_commit,
                  version, usuario):
    repo = workflow.repositorio.nombre_completo
    variables, commit_api = variables_ejecucion(gh, repo, run, runs_wf,
                                                runs_repo, datos_commit)
    resultado = predecir(variables, version)
    analisis, recomendaciones = _por_reglas(variables, resultado["factores"])
    jobs = gh.jobs_intento(repo, run["id"], run.get("run_attempt") or 1)
    etiqueta = etiquetar_ejecucion(run.get("conclusion"), jobs,
                                   workflow.patron_paso_despliegue)
    ahora = dj_timezone.now()
    with transaction.atomic():
        commit = guardar_commit(workflow.repositorio, run["head_sha"],
                                commit_api)
        ejecucion = guardar_ejecucion(workflow, run, ahora)
        for campo, valor in etiqueta.items():
            setattr(ejecucion, campo, valor)
        ejecucion.etiquetada_en = ahora
        ejecucion.save()
        prediccion = Prediccion(
            usuario=usuario, workflow=workflow, commit=commit,
            version_modelo=version, rama=run.get("head_branch") or "",
            evento=run.get("event") or "", variables=_json_seguro(variables),
            probabilidad=resultado["probabilidad"], nivel=resultado["nivel"],
            recomendacion=resultado["recomendacion"],
            factores=resultado["factores"], recomendaciones=recomendaciones,
            analisis_ia=analisis, origen="lote",
            momento_variables=fecha(run["run_started_at"]),
            ejecucion_real=ejecucion, verificada_en=ahora,
            datos_github_extraidos_en=ahora)
        prediccion.clean()
        prediccion.save()
    return prediccion
