"""Recolección de datos desde GitHub sin necesidad de una predicción.

Descarga las ejecuciones recientes de los workflows de despliegue validados
de un repositorio y las guarda (con su commit) en la base de datos
histórica. Se usa desde la API (administrador) y desde el comando
`manage.py sincronizar_github`, que puede programarse para que la
recopilación sea automática.
"""

from django.utils import timezone

from riesgo.services import github
from riesgo.services.trazabilidad import guardar_ejecucion


def sincronizar_repositorio(repositorio, cliente, por_workflow=20):
    extraido = timezone.now()
    resultado = {"repositorio": repositorio.nombre_completo,
                 "workflows": 0, "ejecuciones_guardadas": 0, "errores": []}
    for workflow in repositorio.workflows.filter(despliegue_validado=True,
                                                   disponible_github=True):
        resultado["workflows"] += 1
        try:
            runs = cliente.ejecuciones_workflow(
                repositorio.nombre_completo, workflow.path, n=por_workflow)
        except github.NoEncontrado:
            resultado["errores"].append(
                f"{workflow.path}: no existe en GitHub o sin permisos")
            continue
        for run in runs:
            if run.get("status") == "completed":
                guardar_ejecucion(workflow, run, extraido)
                resultado["ejecuciones_guardadas"] += 1
    return resultado
