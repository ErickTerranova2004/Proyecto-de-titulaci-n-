"""Resultado real de una predicción: etiquetado y enlace de la ejecución.

Igual que el dataset: los jobs de la API se completan con el YAML del
workflow en el commit de la ejecución (uses, run y environment de cada paso,
etiquetado.enriquecer) antes de aplicar la regla de etiquetado. Sin el YAML,
un paso como «Sync repo to remote VM» (burnett01/rsync-deployments) no se
reconoce como despliegue.

`enlazar_resultado` lo usan el botón «Verificar resultado real» y cada pasada
del análisis en lote (análisis interactivos pendientes), así que el enlace no
depende de que alguien tenga la pestaña abierta.
"""

import logging

from django.db import transaction
from django.utils import timezone

from riesgo.services import github
from riesgo.services.etiquetado import (enriquecer, etiquetar_ejecucion,
                                        info_workflow)
from riesgo.services.features import fecha
from riesgo.services.trazabilidad import guardar_ejecucion

logger = logging.getLogger(__name__)


def etiquetar_run(cliente, workflow, run, jobs):
    repo = workflow.repositorio.nombre_completo
    info = {}
    sha = run.get("head_sha")
    if sha:
        try:
            info = info_workflow(cliente.contenido_workflow(
                repo, workflow.path, sha))
        except github.NoEncontrado:
            # El archivo no existe en ese commit: solo los nombres de pasos.
            logger.info("Sin YAML de %s en %s", workflow.path, sha[:7])
    return etiquetar_ejecucion(run.get("conclusion"), enriquecer(jobs, info),
                               workflow.patron_paso_despliegue)


def del_workflow(run, workflow):
    return (run.get("path") or workflow.path).split("@")[0] == workflow.path


def candidata(runs, workflow, sha, creada_en):
    """Primera ejecución terminada del mismo workflow y commit que empezó
    después del análisis (la que se enlaza como resultado real).

    Se ignoran las omitidas (conclusion «skipped»): no son un intento de
    despliegue. Ej.: lumos-web publica antes un prerelease -rc.0 del mismo
    commit cuya ejecución se omite, y la release real llega minutos después.
    """
    posteriores = sorted(
        (r for r in runs
         if r.get("head_sha") == sha and r.get("status") == "completed"
         and r.get("conclusion") != "skipped"
         and del_workflow(r, workflow)
         and fecha(r.get("run_started_at"))
         and fecha(r["run_started_at"]) > creada_en),
        key=lambda r: r["run_started_at"])
    return posteriores[0] if posteriores else None


def enlazar_resultado(cliente, prediccion):
    """Busca en GitHub la ejecución real y la enlaza si ya existe.

    Devuelve (enlazada, runs): runs son las ejecuciones del commit consultadas,
    para explicar el motivo cuando aún no hay nada que enlazar.
    """
    workflow = prediccion.workflow
    repo = workflow.repositorio.nombre_completo
    sha = prediccion.commit.sha
    runs = cliente.ejecuciones_workflow(repo, workflow.path, head_sha=sha)
    run = candidata(runs, workflow, sha, prediccion.creada_en)
    if run is None:
        return False, runs
    jobs = cliente.jobs_intento(repo, run["id"], run.get("run_attempt") or 1)
    etiqueta = etiquetar_run(cliente, workflow, run, jobs)
    with transaction.atomic():
        ejecucion = guardar_ejecucion(workflow, run)
        for campo, valor in etiqueta.items():
            setattr(ejecucion, campo, valor)
        ejecucion.etiquetada_en = timezone.now()
        ejecucion.save()
        prediccion.ejecucion_real = ejecucion
        prediccion.verificada_en = timezone.now()
        prediccion.clean()
        prediccion.save(update_fields=["ejecucion_real", "verificada_en"])
    return True, runs
