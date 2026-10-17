"""Guarda repositorios, commits y ejecuciones obtenidos de GitHub."""

import hashlib

from django.utils import timezone

from riesgo.models import Commit, EjecucionWorkflow, Repositorio
from riesgo.services import github
from riesgo.services.features import fecha


class RepositorioNoRegistrado(Exception):
    pass


def resolver_repositorio(nombre, cliente):
    """Busca el repositorio por nombre o, si fue renombrado, por github_id."""
    repo = Repositorio.objects.filter(nombre_completo__iexact=nombre).first()
    if repo:
        return repo
    try:
        datos = cliente.repositorio(nombre)
    except github.NoEncontrado:
        raise RepositorioNoRegistrado(nombre)
    repo = Repositorio.objects.filter(github_id=datos.get("id")).first()
    if repo is None:
        raise RepositorioNoRegistrado(nombre)
    # Se actualiza al nombre actual para futuras búsquedas.
    if datos.get("full_name") and datos["full_name"] != repo.nombre_completo:
        propietario, _, corto = datos["full_name"].partition("/")
        repo.nombre_completo = datos["full_name"]
        repo.propietario, repo.nombre = propietario, corto
        repo.save(update_fields=["nombre_completo", "propietario", "nombre"])
    return repo


def guardar_commit(repositorio, sha, datos=None):
    commit, _ = Commit.objects.get_or_create(repositorio=repositorio, sha=sha)
    if datos:
        info = datos.get("commit") or {}
        autor = (info.get("author") or {}).get("name") or ""
        commit.fecha = fecha((info.get("committer") or {}).get("date"))
        commit.autor_hash = (hashlib.sha256(autor.encode()).hexdigest()[:12]
                             if autor else "")
        commit.mensaje_resumen = (info.get("message") or "").split("\n")[0][
            :200]
        commit.save()
    return commit


def guardar_ejecucion(workflow, run, extraida_en=None):
    """Crea o actualiza un intento de ejecución a partir del JSON de GitHub."""
    commit = (guardar_commit(workflow.repositorio, run["head_sha"])
              if run.get("head_sha") else None)
    ejecucion, _ = EjecucionWorkflow.objects.update_or_create(
        run_id=run["id"], run_attempt=run.get("run_attempt") or 1,
        defaults={
            "workflow": workflow,
            "commit": commit,
            "evento": run.get("event") or "",
            "rama": run.get("head_branch") or "",
            "estado": run.get("status") or "",
            "conclusion": run.get("conclusion") or "",
            "iniciada_en": fecha(run.get("run_started_at")),
            "actualizada_en": fecha(run.get("updated_at")),
            "extraida_en": extraida_en or timezone.now(),
        })
    return ejecucion
