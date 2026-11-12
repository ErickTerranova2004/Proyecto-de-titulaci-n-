"""Commits pendientes de desplegar por workflow y despliegues previos.

- actualizar_pendientes: lo llama cada pasada del análisis en lote. Compara
  el último despliegue correcto del workflow con la cabeza de la rama
  principal. Las dos primeras consultas son condicionales (ETag): si nada
  cambió, GitHub responde 304 y no se gasta cuota ni se vuelve a comparar.
- despliegue_previo: lo usa «Nuevo análisis» para avisar si el commit elegido
  ya se desplegó (o se está desplegando): ese análisis nunca podría enlazarse
  con un resultado real, porque solo se enlaza un despliegue que empiece
  después del análisis.
"""

import re

from django.utils import timezone

from riesgo.models import PendienteDespliegue
from riesgo.services import github
from riesgo.services.features import fecha
from riesgo.services.verificacion import del_workflow

VERSION = re.compile(r"^(v?)(\d+)\.(\d+)\.(\d+)$", re.IGNORECASE)
EVENTOS_IGNORADOS = ("pull_request", "pull_request_target")


def siguiente_version(rama):
    """v1.5.3 → v1.5.4 (el tag probable de la próxima release); None si la
    rama no es un número de versión."""
    m = VERSION.match(rama or "")
    if not m:
        return None
    return f"{m[1]}{m[2]}.{m[3]}.{int(m[4]) + 1}"


def _ultimo_despliegue(datos):
    for run in (datos or {}).get("workflow_runs", []):
        if run.get("event") not in EVENTOS_IGNORADOS:
            return run
    return None


def actualizar_pendientes(gh, workflow):
    """Actualiza (o crea) el PendienteDespliegue del workflow.

    Devuelve "sin_cambios" si GitHub respondió 304 a ambas consultas, o
    "actualizado".
    """
    repo = workflow.repositorio.nombre_completo
    archivo = workflow.path.rsplit("/", 1)[-1]
    estado = (PendienteDespliegue.objects.filter(workflow=workflow).first()
              or PendienteDespliegue(workflow=workflow))
    if not estado.rama_principal:
        estado.rama_principal = gh.get(f"/repos/{repo}").get(
            "default_branch") or "main"
        estado.etag_cabeza = ""
    despliegues, estado.etag_despliegues = gh.get_condicional(
        f"/repos/{repo}/actions/workflows/{archivo}/runs",
        {"status": "success", "per_page": 10}, estado.etag_despliegues)
    try:
        cabeza, estado.etag_cabeza = gh.get_condicional(
            f"/repos/{repo}/git/ref/heads/{estado.rama_principal}", None,
            estado.etag_cabeza)
    except github.NoEncontrado:
        # La rama principal cambió de nombre: se vuelve a consultar la próxima vez.
        estado.rama_principal, estado.etag_cabeza = "", ""
        cabeza = None
    estado.calculado_en = timezone.now()
    if despliegues is None and cabeza is None and estado.pk:
        estado.save(update_fields=["calculado_en", "rama_principal",
                                   "etag_cabeza"])
        return "sin_cambios"

    if despliegues is not None:
        ultimo = _ultimo_despliegue(despliegues)
        estado.ultimo_despliegue_sha = (ultimo or {}).get("head_sha") or ""
        estado.ultimo_despliegue_en = fecha((ultimo or {}).get("run_started_at"))
        estado.ultimo_despliegue_evento = (ultimo or {}).get("event") or ""
        estado.ultimo_despliegue_rama = (ultimo or {}).get("head_branch") or ""
    if cabeza is not None:
        estado.sha_cabeza = (cabeza.get("object") or {}).get("sha") or ""

    if not estado.ultimo_despliegue_sha or not estado.sha_cabeza:
        estado.commits_pendientes = None
    elif estado.ultimo_despliegue_sha == estado.sha_cabeza:
        estado.commits_pendientes = 0
    else:
        # Commits inmutables: la comparación se cachea.
        try:
            comparacion = gh.get(
                f"/repos/{repo}/compare/"
                f"{estado.ultimo_despliegue_sha}...{estado.sha_cabeza}",
                {"per_page": 1})
            estado.commits_pendientes = (
                comparacion.get("ahead_by") or 0
                if comparacion.get("status") in ("ahead", "diverged") else 0)
        except github.NoEncontrado:
            # El commit desplegado ya no está en el repositorio (force push
            # o despliegue desde un fork): no hay con qué comparar.
            estado.commits_pendientes = None
    estado.rama_sugerida = (siguiente_version(estado.ultimo_despliegue_rama)
                            or estado.rama_principal)
    estado.save()
    return "actualizado"


def despliegue_previo(cliente, repo, workflow, sha):
    """Ejecución del workflow para este commit que ya terminó bien o sigue en
    curso (la más reciente), o None.

    Los intentos fallidos o cancelados no cuentan: un reintento sí es un
    despliegue posterior que se enlazará. Las omitidas (skipped) tampoco.
    """
    runs = [r for r in cliente.ejecuciones_workflow(repo, workflow.path,
                                                    head_sha=sha)
            if r.get("head_sha") == sha and del_workflow(r, workflow)
            and r.get("conclusion") != "skipped"
            and (r.get("status") != "completed"
                 or r.get("conclusion") == "success")]
    if not runs:
        return None
    run = max(runs, key=lambda r: r.get("run_started_at") or r.get("created_at")
              or "")
    return {"run_id": run.get("id"), "estado": run.get("status") or "",
            "conclusion": run.get("conclusion") or "",
            "evento": run.get("event") or "",
            "rama": run.get("head_branch") or "",
            "iniciada_en": run.get("run_started_at") or run.get("created_at"),
            "url": run.get("html_url")}
