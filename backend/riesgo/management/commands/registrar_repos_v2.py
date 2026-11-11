"""Registra los 198 repositorios del dataset v2 con su workflow de despliegue.

Fuente: la «Lista final» de informes/informe_filtrado_repos_reales.md
(repositorio, workflow, plataforma y evidencia de la revisión manual). Cada
workflow queda validado con esa evidencia y cada repositorio, activo y
asignado a los usuarios indicados en --asignar (el grupo que revisa la
validación prospectiva).

No hace llamadas a GitHub ni carga ejecuciones históricas: las ejecuciones
posteriores a la fecha de corte las analiza `analizar_lote`.

    manage.py registrar_repos_v2 --validado-por revision_admin \
        --asignar revision_dev revision_lider revision_admin [--aplicar]
"""

import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from riesgo.models import AccesoRepositorio, Repositorio, Workflow

FILA = re.compile(
    r"^\| \d+ \| \[(?P<repo>[^\]]+)\]\(https://github\.com/[^/]+/[^/]+/blob/"
    r"HEAD/(?P<ruta>[^)]+)\)(?P<marca>[^|]*)\| [^|]+\| (?P<plataforma>[^|]+)"
    r"\|(?:[^|]*\|){3} (?P<evidencia>.*) \|$", re.M)


def leer_lista(ruta_informe):
    texto = ruta_informe.read_text(encoding="utf-8")
    if "## Lista final" not in texto:
        raise CommandError(f"{ruta_informe} no tiene la sección «Lista final».")
    lista = texto.split("## Lista final", 1)[1].split("\n## ", 1)[0]
    return [{k: v.strip() for k, v in m.groupdict().items()}
            for m in FILA.finditer(lista)]


def evidencia(fila):
    return (f"Repositorio del dataset v2 (informes/informe_filtrado_repos_"
            f"reales.md, «Lista final»): workflow de despliegue a producción "
            f"validado en la revisión manual. Plataforma: {fila['plataforma']}. "
            f"{fila['evidencia']}")[:2000]


class Command(BaseCommand):
    help = "Registra los repositorios del dataset v2 (sin ejecuciones)."

    def add_arguments(self, parser):
        parser.add_argument("--informe", default=str(
            settings.PROJECT_DIR / "informes" /
            "informe_filtrado_repos_reales.md"))
        parser.add_argument("--esperados", type=int, default=198)
        parser.add_argument("--validado-por", required=True)
        parser.add_argument("--asignar", nargs="*", default=[])
        parser.add_argument("--aplicar", action="store_true")

    def handle(self, *args, **opciones):
        from pathlib import Path
        filas = leer_lista(Path(opciones["informe"]))
        if len(filas) != opciones["esperados"]:
            raise CommandError(f"Se esperaban {opciones['esperados']} "
                               f"repositorios y la lista tiene {len(filas)}.")
        modelo = get_user_model()
        try:
            validador = modelo.objects.get(username=opciones["validado_por"])
        except modelo.DoesNotExist:
            raise CommandError(f"No existe el usuario {opciones['validado_por']}.")
        asignar = list(modelo.objects.filter(username__in=opciones["asignar"]))
        if len(asignar) != len(set(opciones["asignar"])):
            raise CommandError("Algún usuario de --asignar no existe.")

        existentes = {r.nombre_completo.lower(): r
                      for r in Repositorio.objects.all()}
        ya = [f["repo"] for f in filas if f["repo"].lower() in existentes]
        self.stdout.write(
            f"Lista: {len(filas)} repositorios ({len(ya)} ya registrados). "
            f"Asignados a: {', '.join(u.username for u in asignar) or '—'}.")
        if not opciones["aplicar"]:
            self.stdout.write("Sin --aplicar: no se guardó nada.")
            return

        ahora = timezone.now()
        creados = 0
        with transaction.atomic():
            for fila in filas:
                repo = existentes.get(fila["repo"].lower())
                if repo is None:
                    propietario, _, nombre = fila["repo"].partition("/")
                    repo = Repositorio.objects.create(
                        nombre_completo=fila["repo"], propietario=propietario,
                        nombre=nombre)
                    creados += 1
                repo.est_registro = "A"
                repo.es_prueba = False
                repo.save(update_fields=["est_registro", "es_prueba"])
                workflow, _ = Workflow.objects.get_or_create(
                    repositorio=repo, path=fila["ruta"])
                workflow.despliegue_validado = True
                workflow.evidencia_validacion = evidencia(fila)
                workflow.validado_por = validador
                workflow.validado_en = ahora
                workflow.disponible_github = True
                workflow.full_clean(exclude=["github_id"])
                workflow.save()
                for usuario in asignar:
                    AccesoRepositorio.objects.get_or_create(
                        usuario=usuario, repositorio=repo,
                        defaults={"asignado_por": validador})
        self.stdout.write(self.style.SUCCESS(
            f"{creados} repositorios nuevos; {len(filas)} workflows validados "
            "y asignados."))
