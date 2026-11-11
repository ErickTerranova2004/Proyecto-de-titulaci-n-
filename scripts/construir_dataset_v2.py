#!/usr/bin/env python3
"""Construye el dataset v2 del modelo a partir del dataset congelado.

Entrada (congelada el 2026-11-10, no se modifica):
- informes/orden_repos_curva.csv: los 202 repositorios del dataset de
  entrenamiento (203 válidos menos cultpodcasts/RedditPodcastPoster).
- informes/cache_filtrado/etiquetas.json: etiquetas de la regla 7; el dataset
  usa las 50 ejecuciones más recientes de cada repositorio (TOPE_DATASET) con
  y = 0 o y = 1.

Salida: datos_procesados/dataset_riesgo_despliegue_v2.csv, una fila por
ejecución etiquetada.

Las variables se calculan con la MISMA función que usa la plataforma,
`variables_desde_datos` (backend/riesgo/services/features.py), con el inicio
de cada ejecución como momento del despliegue. Esa función solo usa lo que ya
había terminado o existía antes de ese momento (ejecuciones previas, checks
del commit, pull requests). Las consultas a la API son las mismas que hace la
plataforma (mismos parámetros, PARAMS_PULLS y PARAMS_CHECKS).

Llamadas por repositorio: listados de ejecuciones del workflow y del
repositorio (paginados, con ventana de 7 a 180 días antes de la primera
ejecución etiquetada). Por commit distinto: el commit (tamaño del cambio),
sus pull requests y sus checks. Por reintento: los intentos anteriores.

Solo lectura de la API de GitHub. Caché por repositorio en
informes/cache_filtrado/variables_v2/ para poder reanudar.

Uso:
    backend/venv/Scripts/python.exe -X utf8 scripts/construir_dataset_v2.py
    backend/venv/Scripts/python.exe -X utf8 scripts/construir_dataset_v2.py --repos owner/repo
"""

import argparse
import csv
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
from riesgo.services.features import (  # noqa: E402
    PARAMS_CHECKS, PARAMS_PULLS, variables_desde_datos,
)

ORDEN = RAIZ / "informes" / "orden_repos_curva.csv"
SALIDA = RAIZ / "datos_procesados" / "dataset_riesgo_despliegue_v2.csv"
TOPE = 50  # filtrar_repos_reales.TOPE_DATASET, congelado
PREVIAS_REPO = 100  # features.MAX_PREVIAS_REPO
PREVIAS_WORKFLOW = 4  # features.MAX_PREVIAS_WORKFLOW
VENTANAS_DIAS = (7, 30, 90, 180)
MAX_RESULTADOS = 1000  # límite de la API con el filtro `created`

# Campos de cada ejecución que usan las variables.
CAMPOS_RUN = ("id", "run_attempt", "status", "conclusion", "event",
              "head_branch", "head_sha", "workflow_id", "check_suite_id",
              "run_started_at", "created_at", "updated_at")
NUMERICAS = [
    "msg_len", "msg_lineas", "msg_merge", "msg_revert", "msg_fix",
    "msg_feat", "msg_deps", "msg_docs", "msg_ci", "autor_bot",
    "rama_principal", "rama_tag", "tiene_pr", "es_reintento",
    "hora_utc", "dia_semana", "fin_de_semana", "retraso_commit_run_min",
    "archivos_modificados", "lineas_anadidas", "lineas_borradas",
    "checks_n_prev", "checks_fallidos_prev", "checks_tasa_fallo_prev",
    "wf_n_prev", "wf_tasa_fallo_prev", "wf_ultimo_fallo",
    "wf_horas_desde_ultimo", "wf_duracion_media_prev_min",
    "repo_n_prev", "repo_tasa_fallo_prev", "repo_n_workflows_prev",
]


def fecha(texto):
    return datetime.fromisoformat(texto.replace("Z", "+00:00")) if texto else None


def iso(momento):
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resumir(run):
    return {k: run.get(k) for k in CAMPOS_RUN}


def listar(gh, ruta, desde, hasta):
    """Ejecuciones creadas en [desde, hasta]. Divide el intervalo si supera
    el máximo de resultados que devuelve la API con el filtro `created`."""
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
        datos = gh.get(ruta, dict(params, page=pagina)) or {}
        nuevos = datos.get("workflow_runs", [])
        if not nuevos:
            break
        runs += nuevos
        pagina += 1
    return [resumir(r) for r in runs]


def historial(gh, ruta, primer_momento, ultimo_momento, minimo):
    """Ejecuciones desde antes del primer momento hasta el último. Amplía la
    ventana hasta tener `minimo` ejecuciones previas al primer momento."""
    for dias in VENTANAS_DIAS:
        runs = listar(gh, ruta, primer_momento - timedelta(days=dias),
                      ultimo_momento + timedelta(minutes=1))
        previas = sum(fecha(r["created_at"]) < primer_momento for r in runs)
        if previas >= minimo:
            break
    unicos = {r["id"]: r for r in runs}
    return sorted(unicos.values(), key=lambda r: r["run_started_at"] or "")


def intentos_anteriores(gh, repo, run):
    """Los intentos anteriores de un reintento (el listado solo devuelve el
    último). En la plataforma esos intentos ya existían antes del reintento."""
    return [resumir(gh.get(f"/repos/{repo}/actions/runs/{run['id']}/attempts/{n}") or {})
            for n in range(1, run.get("run_attempt") or 1)]


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
                (self.gh.get(f"{base}/check-runs", PARAMS_CHECKS) or {}).get("check_runs", []))
        return self.cache[sha]


def variables_ejecucion(gh, repo, run, runs_wf, runs_repo, datos_commit):
    """Variables de una ejecución histórica con el mismo código que la
    plataforma, tomando su inicio como momento del despliegue."""
    momento = fecha(run["run_started_at"])
    anteriores = intentos_anteriores(gh, repo, run)
    commit, pulls, checks = datos_commit(run["head_sha"])
    mismo_commit = [r for r in runs_wf if r["head_sha"] == run["head_sha"]] + anteriores
    return variables_desde_datos(
        commit, run.get("head_branch") or "", run.get("event") or "", momento,
        runs_wf + anteriores, runs_repo + anteriores, mismo_commit, pulls, checks,
        intento=run.get("run_attempt") or 1, run_id=run["id"])


def filas_repo(gh, repo, plataforma, ruta_workflow, etiquetas, historial_runs, cache_dir):
    cache = cache_dir / (repo.replace("/", "__") + ".json")
    # Caché por ejecución: las variables no dependen de la etiqueta, así que
    # al re-etiquetar solo se calculan las ejecuciones nuevas del top 50 y la
    # y y el subtipo salen siempre de las etiquetas vigentes.
    guardadas_cache = {}
    if cache.exists():
        for f in json.loads(cache.read_text(encoding="utf-8")):
            f.setdefault("ejecucion_reconstruida", 0)  # cachés anteriores a la columna
            guardadas_cache[f["run_id"]] = f
    etiquetadas = [f for f in etiquetas[:TOPE] if f.get("y") in (0, 1)]
    if not etiquetadas:
        return []
    faltan = [f for f in etiquetadas if f["run"] not in guardadas_cache]
    if not faltan:
        return [dict(guardadas_cache[f["run"]], y=f["y"], subtipo=f.get("subtipo") or "")
                for f in etiquetadas]
    inicio = {r["id"]: fecha(r["inicio"]) for r in historial_runs}
    momentos = [inicio[f["run"]] for f in etiquetadas]
    archivo = ruta_workflow.rsplit("/", 1)[-1]
    runs_wf = historial(gh, f"/repos/{repo}/actions/workflows/{archivo}/runs",
                        min(momentos), max(momentos), PREVIAS_WORKFLOW)
    runs_repo = historial(gh, f"/repos/{repo}/actions/runs",
                          min(momentos), max(momentos), PREVIAS_REPO)
    por_id = {r["id"]: r for r in runs_wf}
    datos_commit = DatosCommit(gh, repo)
    filas = []
    guardadas = {r["id"]: r for r in historial_runs}
    for f in etiquetadas:
        if f["run"] in guardadas_cache:
            filas.append(dict(guardadas_cache[f["run"]], y=f["y"], subtipo=f.get("subtipo") or ""))
            continue
        run = por_id.get(f["run"]) or resumir(
            gh.get(f"/repos/{repo}/actions/runs/{f['run']}") or {})
        reconstruida = not run.get("run_started_at")
        if reconstruida:
            # La ejecución se borró de GitHub después de etiquetarla: se
            # reconstruye con lo que se guardó al etiquetarla.
            h = guardadas[f["run"]]
            run = {"id": f["run"], "run_attempt": h["intento"], "status": "completed",
                   "conclusion": h["conclusion"], "event": h["evento"],
                   "head_branch": f.get("rama") or "", "head_sha": h["sha"],
                   "workflow_id": None, "check_suite_id": None,
                   "run_started_at": h["inicio"], "created_at": h["inicio"],
                   "updated_at": None}
        variables = variables_ejecucion(gh, repo, run, runs_wf, runs_repo, datos_commit)
        filas.append({
            "repositorio": repo, "plataforma": plataforma,
            "workflow_path": ruta_workflow, "run_id": run["id"],
            "run_attempt": run.get("run_attempt"),
            "run_started_at": run["run_started_at"], "y": f["y"],
            "subtipo": f.get("subtipo") or "",
            "ejecucion_reconstruida": int(reconstruida), **variables,
        })
    cache_dir.mkdir(parents=True, exist_ok=True)
    todas = {**guardadas_cache, **{f["run_id"]: f for f in filas}}
    cache.write_text(json.dumps(list(todas.values()), ensure_ascii=False, default=str),
                     encoding="utf-8")
    return filas


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repos", nargs="*", help="Solo estos repositorios")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "filtrar", RAIZ / "scripts" / "filtrar_repos_reales.py")
    filtrar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(filtrar)
    orden = list(csv.DictReader(ORDEN.open(encoding="utf-8")))
    etiquetas = filtrar.leer(filtrar.ETIQUETAS, {})
    historial_runs = filtrar.leer(filtrar.HISTORIAL, {})
    perfiles = filtrar.leer(filtrar.PERFILES, {})
    gh = filtrar.GitHub()
    todas = []
    for i, fila in enumerate(orden, 1):
        repo = fila["repositorio"]
        if args.repos and repo not in args.repos:
            continue
        filas = filas_repo(gh, repo, fila["plataforma"], perfiles[repo]["ruta"],
                           etiquetas[repo], historial_runs[repo],
                           filtrar.CACHE / "variables_v2")
        todas += filas
        print(f"{i}/{len(orden)} {repo}: {len(filas)} filas", flush=True)
    if args.repos:
        return
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    columnas = ["repositorio", "plataforma", "workflow_path", "run_id",
                "run_attempt", "run_started_at", "y", "subtipo",
                "ejecucion_reconstruida", "event"] + NUMERICAS
    with SALIDA.open("w", encoding="utf-8", newline="") as salida:
        escritor = csv.DictWriter(salida, fieldnames=columnas, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(todas)
    y1 = sum(f["y"] == 1 for f in todas)
    print(f"{SALIDA}: {len(todas)} filas · y=1 {y1} ({100 * y1 / max(len(todas), 1):.1f} %) · "
          f"{len({f['repositorio'] for f in todas})} repositorios")


if __name__ == "__main__":
    main()
