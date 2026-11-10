#!/usr/bin/env python3
"""Construye el dataset v2 del modelo a partir del dataset congelado.

Entrada (congelada el 2026-11-10, no se modifica):
- informes/orden_repos_curva.csv: los 202 repositorios del dataset de
  entrenamiento (203 válidos menos cultpodcasts/RedditPodcastPoster).
- informes/cache_filtrado/etiquetas.json: etiquetas de la regla 7; el dataset
  usa las 50 ejecuciones más recientes de cada repositorio (TOPE_DATASET) con
  y = 0 o y = 1.

Salida: datos_procesados/dataset_riesgo_despliegue_v2.csv, una fila por
ejecución etiquetada, con las 28 variables del modelo.

Las variables se calculan con las mismas funciones que usa la plataforma
(backend/riesgo/services/features.py) para que el entrenamiento y el uso
calculen igual cada variable. Dos detalles para que no haya fuga de
información del futuro:
- El momento de cada fila es el inicio de la ejecución (run_started_at).
- Una ejecución previa solo cuenta si ya había terminado en ese momento
  (updated_at <= momento). En la plataforma, una ejecución en curso no cuenta
  porque su estado aún no es `completed`.
El historial del workflow usa las 4 ejecuciones previas más recientes y el
del repositorio, las 100 ejecuciones más recientes con 5 por workflow, igual
que la plataforma (github.py: ejecuciones_repositorio n=100).

Como en v1 y v1.1 (build_dataset.py), en el entrenamiento se calculan con
datos reales tres variables que la plataforma fija antes del despliegue:
es_reintento (run_attempt > 1), reejecutado_por_otro (actor distinto de
triggering_actor) y tiene_pr (la ejecución tiene un pull request asociado).

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
    variables_commit, variables_repositorio, variables_workflow,
)

_spec = importlib.util.spec_from_file_location(
    "filtrar", RAIZ / "scripts" / "filtrar_repos_reales.py")
filtrar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(filtrar)

ORDEN = RAIZ / "informes" / "orden_repos_curva.csv"
CACHE_V2 = filtrar.CACHE / "variables_v2"
SALIDA = RAIZ / "datos_procesados" / "dataset_riesgo_despliegue_v2.csv"
TOPE = filtrar.TOPE_DATASET  # 50, congelado
PREVIAS_REPO = 100  # github.py: ejecuciones_repositorio(n=100)
PREVIAS_WORKFLOW = 4  # features.py: MAX_PREVIAS_WORKFLOW
VENTANAS_DIAS = (7, 30, 90, 180)
MAX_RESULTADOS = 1000  # límite de la API con el filtro `created`

CAMPOS_RUN = ("id", "run_attempt", "status", "conclusion", "event",
              "head_branch", "workflow_id", "path", "run_started_at",
              "created_at", "updated_at")
NUMERICAS = [
    "msg_len", "msg_lineas", "msg_merge", "msg_revert", "msg_fix",
    "msg_feat", "msg_deps", "msg_docs", "msg_ci", "autor_bot",
    "reejecutado_por_otro", "rama_principal", "rama_bot", "rama_tag",
    "tiene_pr", "es_reintento", "hora_utc", "dia_semana", "fin_de_semana",
    "retraso_commit_run_min", "wf_n_prev", "wf_tasa_fallo_prev",
    "wf_ultimo_fallo", "wf_horas_desde_ultimo", "wf_duracion_media_prev_min",
    "repo_n_prev", "repo_tasa_fallo_prev", "repo_n_workflows_prev",
]


def fecha(texto):
    return datetime.fromisoformat(texto.replace("Z", "+00:00")) if texto else None


def iso(momento):
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resumir(run):
    """Campos que usan las variables (sin el resto del objeto de la API)."""
    datos = {k: run.get(k) for k in CAMPOS_RUN}
    commit = run.get("head_commit") or {}
    datos.update({
        "actor": (run.get("actor") or {}).get("login"),
        "triggering_actor": (run.get("triggering_actor") or {}).get("login"),
        "n_pull_requests": len(run.get("pull_requests") or []),
        "commit_message": commit.get("message") or "",
        "commit_author": (commit.get("author") or {}).get("name") or "",
        # head_commit.timestamp es la fecha del commit (equivale a
        # commit.committer.date, que usa la plataforma).
        "commit_timestamp": commit.get("timestamp"),
    })
    return datos


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


def terminadas_antes(runs, momento, excluir):
    """Ejecuciones que ya habían terminado en el momento (sin la propia)."""
    return [r for r in runs if r["id"] != excluir and r["status"] == "completed"
            and r["updated_at"] and fecha(r["updated_at"]) <= momento]


def filas_repo(gh, repo, plataforma, ruta_workflow, etiquetas, historial_runs):
    cache = CACHE_V2 / (repo.replace("/", "__") + ".json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    inicio = {r["id"]: fecha(r["inicio"]) for r in historial_runs}
    etiquetadas = [f for f in etiquetas[:TOPE] if f.get("y") in (0, 1)]
    if not etiquetadas:
        return []
    momentos = [inicio[f["run"]] for f in etiquetadas]
    archivo = ruta_workflow.rsplit("/", 1)[-1]
    runs_wf = historial(gh, f"/repos/{repo}/actions/workflows/{archivo}/runs",
                        min(momentos), max(momentos), PREVIAS_WORKFLOW)
    runs_repo = historial(gh, f"/repos/{repo}/actions/runs",
                          min(momentos), max(momentos), PREVIAS_REPO)
    por_id = {r["id"]: r for r in runs_wf}
    filas = []
    for f in etiquetadas:
        run = por_id.get(f["run"])
        if run is None:  # fuera de la ventana listada: se pide directamente
            run = resumir(gh.get(f"/repos/{repo}/actions/runs/{f['run']}") or {})
        momento = fecha(run["run_started_at"]) or inicio[f["run"]]
        rama, evento = run.get("head_branch") or "", run.get("event") or ""
        variables = variables_commit(
            run["commit_message"], run["commit_author"], rama, evento, momento,
            fecha(run["commit_timestamp"]))
        variables.update({
            "es_reintento": int((run.get("run_attempt") or 1) > 1),
            "reejecutado_por_otro": int((run.get("actor") or "")
                                        != (run.get("triggering_actor") or "")),
            "tiene_pr": int(run["n_pull_requests"] > 0),
        })
        previas_wf = terminadas_antes(runs_wf, momento, run["id"])
        variables.update(variables_workflow(previas_wf, momento))
        previas_repo = terminadas_antes(runs_repo, momento, run["id"])
        previas_repo = sorted(previas_repo, key=lambda r: r["created_at"])[-PREVIAS_REPO:]
        variables.update(variables_repositorio(previas_repo, momento))
        filas.append({
            "repositorio": repo, "plataforma": plataforma,
            "workflow_path": ruta_workflow, "run_id": run["id"],
            "run_attempt": run.get("run_attempt"),
            "run_started_at": iso(momento), "y": f["y"],
            "subtipo": f.get("subtipo") or "", **variables,
        })
    CACHE_V2.mkdir(parents=True, exist_ok=True)
    filtrar.guardar(cache, filas)
    return filas


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repos", nargs="*", help="Solo estos repositorios")
    args = parser.parse_args()
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
                           etiquetas[repo], historial_runs[repo])
        todas += filas
        print(f"{i}/{len(orden)} {repo}: {len(filas)} filas", flush=True)
    if args.repos:
        return
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    columnas = ["repositorio", "plataforma", "workflow_path", "run_id",
                "run_attempt", "run_started_at", "y", "subtipo", "event"] + NUMERICAS
    with SALIDA.open("w", encoding="utf-8", newline="") as salida:
        escritor = csv.DictWriter(salida, fieldnames=columnas, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(todas)
    y1 = sum(f["y"] == 1 for f in todas)
    print(f"{SALIDA}: {len(todas)} filas · y=1 {y1} ({100 * y1 / max(len(todas), 1):.1f} %) · "
          f"{len({f['repositorio'] for f in todas})} repositorios")


if __name__ == "__main__":
    main()
