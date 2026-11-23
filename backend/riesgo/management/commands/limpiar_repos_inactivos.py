"""Limpieza de los repositorios inactivos y de los workflows no productivos.

Ver docs/estado_proyecto.md («Limpieza de repositorios inactivos»).

1. Repositorios inactivos (est_registro='I', casi todos del dataset GHALogs
   v1.1): pone est_registro='I' en sus workflows, sus análisis interactivos,
   las decisiones y asignaciones de esos análisis, sus enlaces con las
   ejecuciones previas, sus informes de cumplimiento y los accesos al
   repositorio. Los análisis en lote y en sombra NO se tocan: son la historia
   del modelo v1 (supervisión y comparación en sombra). Ningún análisis de un
   repositorio inactivo sale en los historiales de los roles
   (permissions.predicciones_visibles).
2. Workflows que por su nombre no son de producción (staging, pages, dev,
   preview, qa, uat, sandbox, demo, solo pruebas): despliegue_validado=False.
   Se excluyen el repositorio de demostración y los de repositorios activos
   que se comprobaron como producción (EXCEPCIONES).

No borra nada. Sin --aplicar solo informa. Es idempotente.
"""

import re

from django.db import transaction
from django.db.models import Q

from riesgo.auditoria import ComandoAuditado
from riesgo.models import (AccesoRepositorio, DecisionDespliegue,
                           InformeCumplimiento, Prediccion,
                           PrediccionEjecucion, Repositorio, Workflow)

# Palabras del nombre del archivo que indican un entorno no productivo.
NO_PRODUCCION = {"staging", "stage", "stg", "pages", "dev", "develop",
                 "development", "preview", "previews", "qa", "uat",
                 "sandbox", "demo"}
PRUEBAS = {"test", "tests", "testing"}
# Con estas palabras el workflow también despliega a producción.
PRODUCCION = {"prod", "production", "produccion", "live"}
DESPLIEGUE = {"deploy", "deployment", "release", "publish", "cd"}
# Workflows de repositorios activos comprobados como producción.
EXCEPCIONES = {
    ("mozilla/probe-scraper", ".github/workflows/build-test-deploy.yml"),
    ("dailybruin/flamingo", ".github/workflows/test_and_deploy.yml"),
    # Se dispara con «develop», pero despliega al slot Production.
    ("explorer-consulting/schoolfeedbackwebapi",
     ".github/workflows/gimi_develop_feedback-api.yml"),
}


def palabras(ruta):
    nombre = ruta.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
    return set(re.split(r"[^a-z0-9]+", nombre)) - {""}


def no_es_produccion(ruta):
    """Por el nombre del archivo: entorno no productivo (sin palabra de
    producción) o solo pruebas (sin palabra de despliegue)."""
    p = palabras(ruta)
    if p & PRODUCCION:
        return False
    if p & NO_PRODUCCION:
        return True
    return bool(p & PRUEBAS) and not p & DESPLIEGUE


def a_desvalidar():
    return [w for w in Workflow.objects.filter(despliegue_validado=True)
            .select_related("repositorio")
            if not w.repositorio.es_demostracion
            and (w.repositorio.nombre_completo.lower(), w.path) not in EXCEPCIONES
            and no_es_produccion(w.path)]


def consultas_inactivos():
    inactivos = Repositorio.objects.filter(est_registro="I")
    interactivos = Prediccion.objects.filter(
        workflow__repositorio__in=inactivos, origen="interactivo")
    return [
        ("Workflows", Workflow.objects.filter(repositorio__in=inactivos)),
        ("Análisis interactivos", interactivos),
        ("Decisiones y asignaciones",
         DecisionDespliegue.objects.filter(prediccion__in=interactivos)),
        ("Enlaces análisis–ejecución",
         PrediccionEjecucion.objects.filter(prediccion__in=interactivos)),
        ("Informes de cumplimiento", InformeCumplimiento.objects.filter(
            Q(prediccion_original__in=interactivos)
            | Q(prediccion_nueva__in=interactivos))),
        ("Accesos", AccesoRepositorio.objects.filter(repositorio__in=inactivos)),
    ]


class Command(ComandoAuditado):
    help = ("Desactiva lo que cuelga de los repositorios inactivos y quita la "
            "validación de los workflows no productivos. Sin --aplicar solo "
            "informa.")

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true",
                            help="Guarda los cambios (por defecto solo informa).")
        parser.add_argument("--detalle", action="store_true",
                            help="Lista los workflows a los que se quita la validación.")

    def handle(self, *args, **opciones):
        inactivos = Repositorio.objects.filter(est_registro="I")
        conservados = Prediccion.con_sombra.filter(
            workflow__repositorio__in=inactivos, origen__in=("lote", "sombra"))
        self.stdout.write(f"Repositorios inactivos: {inactivos.count()} "
                          f"(de prueba {inactivos.filter(es_prueba=True).count()}).")
        self.stdout.write("1. Se desactivan (est_registro='I'):")
        lista = consultas_inactivos()
        for nombre, consulta in lista:
            self.stdout.write(f"   {nombre}: {consulta.filter(est_registro='A').count()} "
                              f"activos de {consulta.count()}")
        self.stdout.write(f"   Se conservan sin cambios (historia del modelo v1): "
                          f"{conservados.filter(origen='lote').count()} en lote y "
                          f"{conservados.filter(origen='sombra').count()} en sombra.")

        desvalidar = a_desvalidar()
        en_activos = [w for w in desvalidar if w.repositorio.est_registro == "A"]
        self.stdout.write(f"2. Workflows no productivos a los que se quita la validación: "
                          f"{len(desvalidar)} (en repositorios activos: {len(en_activos)}).")
        if opciones["detalle"] or en_activos:
            for w in sorted(desvalidar if opciones["detalle"] else en_activos,
                            key=lambda w: (w.repositorio.nombre_completo.lower(), w.path)):
                self.stdout.write(f"   - {w.repositorio.nombre_completo} :: {w.path} "
                                  f"[repo {w.repositorio.est_registro}]")

        if not opciones["aplicar"]:
            self.stdout.write("Sin --aplicar: no se guardó nada.")
            return
        with transaction.atomic():
            # Primero las relaciones (sus filtros dependen de análisis aún activos).
            cambios = {nombre: consulta.filter(est_registro="A").update(est_registro="I")
                       for nombre, consulta in reversed(lista)}
            cambios["Workflows desvalidados"] = Workflow.objects.filter(
                id__in=[w.id for w in desvalidar]).update(despliegue_validado=False)
        self.stdout.write(self.style.SUCCESS(
            "Guardado: " + ", ".join(f"{n} {c}" for n, c in cambios.items())))
