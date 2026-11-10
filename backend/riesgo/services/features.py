"""Calcula las variables del modelo a partir de la API de GitHub.

Un único código para el entrenamiento y la plataforma: `variables_desde_datos`
recibe los datos de GitHub ya descargados y el momento del despliegue. La
plataforma lo llama con el momento actual (`calcular_variables`) y
scripts/construir_dataset_v2.py, con el inicio de cada ejecución histórica.

Regla contra la fuga de información: solo cuenta lo que ya existía o había
terminado antes del momento del despliegue (ejecuciones previas terminadas,
checks terminados, pull requests creados). En la plataforma, lo que aún está
en curso no tiene estado `completed` ni fecha de fin, así que el resultado es
el mismo.

El historial usa como máximo las 4 ejecuciones previas más recientes del
workflow y, en el repositorio, las 100 más recientes con 5 por workflow
(límites heredados de GHALogs, que guarda como máximo 5 por workflow).
"""

import re
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

RAMA_PRINCIPAL = re.compile(r"^(main|master|prod|production|release|live)$",
                            re.IGNORECASE)
RAMA_BOT = re.compile(r"dependabot|renovate", re.IGNORECASE)
RAMA_TAG = re.compile(r"^v?\d+\.\d+", re.IGNORECASE)
AUTOR_BOT = re.compile(r"\[bot\]|dependabot|renovate|github-actions",
                       re.IGNORECASE)
EVENTOS_PR = {"pull_request", "pull_request_target"}
# Conclusiones de un check que cuentan como fallido.
CHECK_FALLIDO = {"failure", "timed_out", "startup_failure"}

# Mismas consultas en la plataforma (github.py) y en el dataset.
PARAMS_PULLS = {"per_page": 100}
PARAMS_CHECKS = {"per_page": 100, "filter": "all"}

MAX_PREVIAS_WORKFLOW = 4
MAX_POR_WORKFLOW_REPO = 5
MAX_PREVIAS_REPO = 100


def fecha(texto):
    if not texto:
        return None
    return datetime.fromisoformat(str(texto).replace("Z", "+00:00"))


def variables_commit(mensaje, autor, rama, evento, momento, fecha_commit):
    primera = mensaje.split("\n")[0].lower()
    retraso = ((momento - fecha_commit).total_seconds() / 60
               if fecha_commit else np.nan)
    return {
        "event": evento,
        "msg_len": len(mensaje),
        "msg_lineas": mensaje.count("\n") + 1,
        "msg_merge": int(primera.startswith("merge")),
        "msg_revert": int("revert" in primera),
        "msg_fix": int(bool(re.search(r"\bfix|hotfix|bug", primera))),
        "msg_feat": int(bool(re.search(r"\bfeat|\badd\b", primera))),
        "msg_deps": int(bool(re.search(
            r"bump|deps|dependenc|upgrade|update .* to", primera))),
        "msg_docs": int(bool(re.search(r"\bdocs?\b|readme", primera))),
        "msg_ci": int(bool(re.search(r"\bci\b|workflow|pipeline", primera))),
        "autor_bot": int(bool(AUTOR_BOT.search(autor or ""))),
        "rama_principal": int(bool(RAMA_PRINCIPAL.match(rama or ""))),
        "rama_bot": int(bool(RAMA_BOT.search(rama or ""))),
        "rama_tag": int(bool(RAMA_TAG.match(rama or ""))),
        "hora_utc": momento.hour,
        "dia_semana": momento.weekday(),
        "fin_de_semana": int(momento.weekday() >= 5),
        "retraso_commit_run_min": max(retraso, 0) if retraso == retraso
        else np.nan,
    }


def variables_cambio(commit):
    """Tamaño del cambio: archivos modificados y líneas añadidas y borradas.

    La API devuelve como máximo 300 archivos por commit; `stats` cuenta
    todas las líneas.
    """
    stats = commit.get("stats") or {}
    archivos = commit.get("files")
    return {
        "archivos_modificados": len(archivos) if archivos is not None else np.nan,
        "lineas_anadidas": stats.get("additions", np.nan),
        "lineas_borradas": stats.get("deletions", np.nan),
    }


def terminada_antes(ejecucion, momento):
    """La ejecución empezó y terminó antes del momento del despliegue."""
    inicio = fecha(ejecucion.get("run_started_at"))
    fin = fecha(ejecucion.get("updated_at"))
    return (ejecucion.get("status") == "completed" and inicio is not None
            and inicio < momento and (fin is None or fin <= momento))


def _previas(ejecuciones, momento):
    """Ejecuciones terminadas antes del momento, de la más antigua a la más
    reciente."""
    previas = [e for e in ejecuciones if terminada_antes(e, momento)]
    return sorted(previas, key=lambda e: e["run_started_at"])


def previas_workflow(ejecuciones, momento):
    """Ejecuciones del workflow que alimentan las variables de historial."""
    return _previas(ejecuciones, momento)[-MAX_PREVIAS_WORKFLOW:]


def variables_workflow(ejecuciones, momento):
    previas = previas_workflow(ejecuciones, momento)
    binarias = [e for e in previas
                if e.get("conclusion") in ("success", "failure")]
    fallos = [e.get("conclusion") == "failure" for e in binarias]
    duraciones = [
        (fecha(e["updated_at"]) - fecha(e["run_started_at"])).total_seconds()
        / 60 for e in previas if e.get("updated_at")]
    return {
        "wf_n_prev": len(previas),
        "wf_tasa_fallo_prev": float(np.mean(fallos)) if fallos else np.nan,
        "wf_ultimo_fallo": float(fallos[-1]) if fallos else np.nan,
        "wf_horas_desde_ultimo": (
            (momento - fecha(previas[-1]["run_started_at"])).total_seconds()
            / 3600 if previas else np.nan),
        "wf_duracion_media_prev_min": (float(np.mean(duraciones))
                                       if duraciones else np.nan),
    }


def variables_repositorio(ejecuciones, momento):
    por_workflow = defaultdict(list)
    for e in _previas(ejecuciones, momento)[-MAX_PREVIAS_REPO:]:
        por_workflow[e.get("workflow_id")].append(e)
    previas = [e for lista in por_workflow.values()
               for e in lista[-MAX_POR_WORKFLOW_REPO:]]
    binarias = [e.get("conclusion") == "failure" for e in previas
                if e.get("conclusion") in ("success", "failure")]
    return {
        "repo_n_prev": len(previas),
        "repo_tasa_fallo_prev": (float(np.mean(binarias)) if binarias
                                 else np.nan),
        "repo_n_workflows_prev": len(por_workflow),
    }


def variables_checks(checks, ejecuciones_mismo_commit, momento):
    """Pruebas y comprobaciones del mismo commit (check runs) que terminaron
    antes del despliegue.

    Se excluyen los checks del propio workflow de despliegue en ese commit
    (su check suite: la propia ejecución, sus otros intentos y otras
    ejecuciones del mismo workflow) para no medir el despliegue con su propio
    resultado.
    """
    propias = {e.get("check_suite_id") for e in ejecuciones_mismo_commit
               if e.get("check_suite_id")}
    previos = [c for c in checks
               if (c.get("check_suite") or {}).get("id") not in propias
               and c.get("status") == "completed"
               and fecha(c.get("completed_at")) is not None
               and fecha(c.get("completed_at")) <= momento]
    fallidos = sum(c.get("conclusion") in CHECK_FALLIDO for c in previos)
    return {"checks_n_prev": len(previos),
            "checks_fallidos_prev": fallidos,
            "checks_tasa_fallo_prev": (fallidos / len(previos) if previos
                                       else np.nan)}


def variable_tiene_pr(pull_requests, evento, momento):
    """El commit pertenece a un pull request creado antes del despliegue (o la
    ejecución la dispara un pull request)."""
    if evento in EVENTOS_PR:
        return 1
    return int(any(fecha(p.get("created_at")) is not None
                   and fecha(p["created_at"]) <= momento
                   for p in pull_requests))


def variable_es_reintento(intento, ejecuciones_mismo_commit, momento,
                          run_id=None):
    """Es un reintento si es un intento posterior al primero o si el mismo
    workflow ya terminó una ejecución con este commit antes del despliegue."""
    if (intento or 1) > 1:
        return 1
    return int(any(not es_propia(e, run_id, intento)
                   and terminada_antes(e, momento)
                   for e in ejecuciones_mismo_commit))


def es_propia(ejecucion, run_id, intento):
    """La fila es el propio intento evaluado (no sus intentos anteriores)."""
    return (run_id is not None and ejecucion.get("id") == run_id
            and (ejecucion.get("run_attempt") or 1) == (intento or 1))


def variables_desde_datos(commit, rama, evento, momento, ejecuciones_workflow,
                          ejecuciones_repositorio, ejecuciones_mismo_commit,
                          pull_requests, checks, intento=1, run_id=None):
    """Todas las variables del modelo con los datos de GitHub ya descargados.

    - commit: respuesta de /repos/{repo}/commits/{sha}.
    - ejecuciones_*: listados de /actions/runs (workflow, repositorio y
      workflow filtrado por el commit).
    - pull_requests: /repos/{repo}/commits/{sha}/pulls.
    - checks: check_runs de /repos/{repo}/commits/{sha}/check-runs.
    - intento y run_id: los de la ejecución evaluada (en la plataforma, antes
      de lanzarla, intento = 1 y run_id = None).
    """
    datos = commit.get("commit") or {}
    variables = variables_commit(
        datos.get("message") or "", (datos.get("author") or {}).get("name", ""),
        rama, evento, momento, fecha((datos.get("committer") or {}).get("date")))
    variables.update(variables_cambio(commit))
    variables["tiene_pr"] = variable_tiene_pr(pull_requests, evento, momento)
    variables["es_reintento"] = variable_es_reintento(
        intento, ejecuciones_mismo_commit, momento, run_id)
    variables.update(variables_workflow(
        [e for e in ejecuciones_workflow if not es_propia(e, run_id, intento)],
        momento))
    variables.update(variables_repositorio(
        [e for e in ejecuciones_repositorio if not es_propia(e, run_id, intento)],
        momento))
    variables.update(variables_checks(checks, ejecuciones_mismo_commit, momento))
    return variables


def calcular_variables(cliente, repo, workflow_path, sha, rama, evento,
                       momento=None, intento=1):
    """Devuelve (variables, fecha de extracción, contexto).

    El contexto contiene el commit y las ejecuciones previas del workflow
    usadas, para guardarlos como trazabilidad de la predicción.
    """
    momento = momento or datetime.now(timezone.utc)
    commit = cliente.commit(repo, sha)
    sha_completo = commit.get("sha") or sha
    ejecuciones = cliente.ejecuciones_workflow(repo, workflow_path)
    mismo_commit = cliente.ejecuciones_workflow(repo, workflow_path,
                                                head_sha=sha_completo)
    variables = variables_desde_datos(
        commit, rama, evento, momento, ejecuciones,
        cliente.ejecuciones_repositorio(repo), mismo_commit,
        cliente.pulls_commit(repo, sha_completo),
        cliente.checks_commit(repo, sha_completo), intento=intento)
    contexto = {"commit": commit,
                "previas": previas_workflow(ejecuciones, momento)}
    return variables, datetime.now(timezone.utc), contexto
