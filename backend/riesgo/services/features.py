"""Calcula las variables del modelo a partir de la API de GitHub.

Replica las definiciones de build_dataset.py. Para reducir la diferencia
entre entrenamiento y uso (GHALogs guarda como máximo 5 ejecuciones por
workflow), el historial usa como máximo las 4 ejecuciones previas más
recientes del workflow y 5 por workflow en el historial del repositorio.
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

MAX_PREVIAS_WORKFLOW = 4
MAX_POR_WORKFLOW_REPO = 5


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
        "reejecutado_por_otro": 0,
        "rama_principal": int(bool(RAMA_PRINCIPAL.match(rama or ""))),
        "rama_bot": int(bool(RAMA_BOT.search(rama or ""))),
        "rama_tag": int(bool(RAMA_TAG.match(rama or ""))),
        "tiene_pr": int(evento in EVENTOS_PR),
        "es_reintento": 0,
        "hora_utc": momento.hour,
        "dia_semana": momento.weekday(),
        "fin_de_semana": int(momento.weekday() >= 5),
        "retraso_commit_run_min": max(retraso, 0) if retraso == retraso
        else np.nan,
    }


def _previas(ejecuciones, momento):
    """Ejecuciones completadas que empezaron antes del momento dado."""
    previas = []
    for e in ejecuciones:
        inicio = fecha(e.get("run_started_at"))
        if e.get("status") == "completed" and inicio and inicio < momento:
            previas.append(e)
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
    for e in _previas(ejecuciones, momento):
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


def calcular_variables(cliente, repo, workflow_path, sha, rama, evento,
                       momento=None):
    """Devuelve (variables, fecha de extracción, contexto).

    El contexto contiene el commit y las ejecuciones previas del workflow
    usadas, para guardarlos como trazabilidad de la predicción.
    """
    momento = momento or datetime.now(timezone.utc)
    commit = cliente.commit(repo, sha)
    datos_commit = commit.get("commit") or {}
    autor = (datos_commit.get("author") or {}).get("name", "")
    fecha_commit = fecha((datos_commit.get("committer") or {}).get("date"))
    variables = variables_commit(datos_commit.get("message") or "", autor,
                                 rama, evento, momento, fecha_commit)
    ejecuciones = cliente.ejecuciones_workflow(repo, workflow_path)
    variables.update(variables_workflow(ejecuciones, momento))
    variables.update(variables_repositorio(
        cliente.ejecuciones_repositorio(repo), momento))
    contexto = {"commit": commit,
                "previas": previas_workflow(ejecuciones, momento)}
    return variables, datetime.now(timezone.utc), contexto
