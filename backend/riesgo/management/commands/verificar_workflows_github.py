"""Comprueba que el archivo de cada workflow validado siga existiendo en GitHub.

Los datos de GHALogs son de 2023; desde entonces algunos repositorios
renombraron o eliminaron sus workflows y GitHub responde 404 al pedir sus
ejecuciones. Este comando los marca como no disponibles para que no se
ofrezcan en nuevos análisis. No se borran: se conservan sus predicciones y su
evidencia de validación.

La consulta se hace a raw.githubusercontent.com (rama por defecto), que no
consume la cuota de la API REST de GitHub.
"""

import csv
from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from riesgo.models import Workflow

RAW = "https://raw.githubusercontent.com/{repo}/HEAD/{path}"


def estado_archivo(sesion, workflow):
    url = RAW.format(repo=workflow.repositorio.nombre_completo,
                     path=workflow.path)
    try:
        return sesion.head(url, allow_redirects=True, timeout=20).status_code
    except requests.RequestException:
        return None


class Command(BaseCommand):
    help = "Marca como no disponibles los workflows que ya no existen."

    def add_arguments(self, parser):
        parser.add_argument("--salida", default=str(
            settings.PROJECT_DIR / "informes" / "workflows_no_disponibles.csv"))
        parser.add_argument("--hilos", type=int, default=8)

    def handle(self, *args, **opciones):
        workflows = list(Workflow.objects.filter(despliegue_validado=True)
                         .select_related("repositorio"))
        sesion = requests.Session()
        with ThreadPoolExecutor(opciones["hilos"]) as grupo:
            estados = list(grupo.map(lambda w: estado_archivo(sesion, w),
                                     workflows))

        ahora = timezone.now()
        retirados, recuperados, sin_respuesta = [], 0, 0
        for workflow, codigo in zip(workflows, estados):
            if codigo is None or codigo >= 500 or codigo == 429:
                # Sin respuesta fiable: no se cambia nada.
                sin_respuesta += 1
                continue
            disponible = codigo == 200
            if not disponible:
                retirados.append((workflow, codigo))
            elif not workflow.disponible_github:
                recuperados += 1
            workflow.disponible_github = disponible
            workflow.verificado_github_en = ahora
            workflow.save(update_fields=["disponible_github",
                                         "verificado_github_en"])

        with open(opciones["salida"], "w", newline="",
                  encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["repositorio", "workflow_path", "http",
                               "verificado_en"])
            for workflow, codigo in sorted(retirados, key=lambda x: (
                    x[0].repositorio.nombre_completo, x[0].path)):
                escritor.writerow([workflow.repositorio.nombre_completo,
                                   workflow.path, codigo, ahora.isoformat()])

        self.stdout.write(self.style.SUCCESS(
            f"{len(workflows)} workflows validados revisados: "
            f"{len(workflows) - len(retirados) - sin_respuesta} disponibles, "
            f"{len(retirados)} no disponibles, {recuperados} recuperados, "
            f"{sin_respuesta} sin respuesta (sin cambios). "
            f"Lista: {opciones['salida']}"))
