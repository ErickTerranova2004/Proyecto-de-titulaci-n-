"""Etiquetado del resultado real de una ejecución en la plataforma.

Igual que el dataset: los jobs de la API se completan con el YAML del
workflow en el commit de la ejecución (uses, run y environment de cada paso,
etiquetado.enriquecer) antes de aplicar la regla de etiquetado. Sin el YAML,
un paso como «Sync repo to remote VM» (burnett01/rsync-deployments) no se
reconoce como despliegue.
"""

import logging

from riesgo.services import github
from riesgo.services.etiquetado import (enriquecer, etiquetar_ejecucion,
                                        info_workflow)

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
