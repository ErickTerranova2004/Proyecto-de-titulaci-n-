"""Desactiva (est_registro='I', sin borrar) los datos de los repositorios de
los casos de prueba (Repositorio.es_prueba) y todo lo que cuelga de ellos.

Así no aparecen en historiales, paneles, pendientes, asignaciones ni en el
Planificador (que solo muestran est_registro='A'); las métricas ya los
excluían con para_modelo(). Se conservan para la auditoría.

- Nunca toca el repositorio de demostración (Repositorio.es_demostracion).
- Solo cambia filas de esos repositorios: los análisis de las cuentas de
  prueba en repositorios reales no se tocan.
- Sin --aplicar solo informa. Es idempotente.
"""

from django.db import transaction

from riesgo.auditoria import ComandoAuditado
from riesgo.models import (AccesoRepositorio, Commit, DecisionDespliegue,
                           EjecucionWorkflow, PendienteDespliegue, Prediccion,
                           PrediccionEjecucion, Repositorio, SeguimientoLote,
                           Workflow)


def consultas(repos):
    """(nombre, queryset) de todo lo que cuelga de los repositorios dados."""
    return [
        ("Repositorios", Repositorio.objects.filter(id__in=repos)),
        ("Workflows", Workflow.objects.filter(repositorio__in=repos)),
        ("Commits", Commit.objects.filter(repositorio__in=repos)),
        ("Ejecuciones", EjecucionWorkflow.objects.filter(
            workflow__repositorio__in=repos)),
        ("Análisis", Prediccion.con_sombra.filter(
            workflow__repositorio__in=repos)),
        ("Análisis–ejecución", PrediccionEjecucion.objects.filter(
            prediccion__workflow__repositorio__in=repos)),
        ("Decisiones", DecisionDespliegue.objects.filter(
            prediccion__workflow__repositorio__in=repos)),
        ("Accesos", AccesoRepositorio.objects.filter(repositorio__in=repos)),
        ("Seguimiento del lote", SeguimientoLote.objects.filter(
            workflow__repositorio__in=repos)),
        ("Commits pendientes", PendienteDespliegue.objects.filter(
            workflow__repositorio__in=repos)),
    ]


class Command(ComandoAuditado):
    help = ("Desactiva (est_registro='I') los repositorios de los casos de "
            "prueba y lo que cuelga de ellos. Sin --aplicar solo informa.")

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true",
                            help="Guarda los cambios (por defecto solo informa).")

    def handle(self, *args, **opciones):
        repos = list(Repositorio.objects.filter(
            es_prueba=True, es_demostracion=False).values_list("id", flat=True))
        self.stdout.write(f"Repositorios de prueba: {len(repos)} "
                          "(el de demostración no se toca).")
        lista = consultas(repos)
        for nombre, consulta in lista:
            total = consulta.count()
            activos = consulta.filter(est_registro="A").count()
            self.stdout.write(f"  {nombre}: {total} (activos {activos})")
        if not opciones["aplicar"]:
            self.stdout.write("Sin --aplicar: no se guardó nada.")
            return
        with transaction.atomic():
            cambiados = {nombre: consulta.filter(est_registro="A").update(
                est_registro="I") for nombre, consulta in lista}
        self.stdout.write(self.style.SUCCESS(
            "Desactivados: " + ", ".join(f"{n} {c}" for n, c in cambiados.items())))
