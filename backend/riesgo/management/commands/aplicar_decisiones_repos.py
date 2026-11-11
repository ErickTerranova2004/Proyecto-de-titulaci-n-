"""Aplica las decisiones del autor sobre los repositorios al activar v2.

Ver informes/informe_filtrado_repos_reales.md («Decisiones del autor sobre
la plataforma»):
1. Repositorios del dataset GHALogs v1.1: est_registro='I' (sin borrarlos).
2. Repositorios de los 30 casos de prueba (datos_prueba/casos_prueba_30.json):
   es_prueba=True (fuera de métricas y dashboards).
3. Azure-Samples/azure-search-openai-demo y openfoodfacts/openfoodfacts-server:
   est_registro='I'.
4. Repositorio de demostración: sin cambios.

Sin --aplicar solo informa de lo que cambiaría. Es idempotente.
"""

import csv
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from riesgo.models import Repositorio

SIN_FUENTE = ("Azure-Samples/azure-search-openai-demo",
              "openfoodfacts/openfoodfacts-server")


class Command(BaseCommand):
    help = "Marca inactivos y de prueba los repositorios según lo acordado."

    def add_arguments(self, parser):
        raiz = settings.PROJECT_DIR
        parser.add_argument("--dataset-ghalogs", default=str(
            raiz / "datos_procesados" / "dataset_riesgo_despliegue_v1_1.csv"))
        parser.add_argument("--casos-prueba", default=str(
            raiz / "datos_prueba" / "casos_prueba_30.json"))
        parser.add_argument("--aplicar", action="store_true",
                            help="Guarda los cambios (por defecto solo informa).")

    def handle(self, *args, **opciones):
        try:
            with open(opciones["dataset_ghalogs"], encoding="utf-8") as archivo:
                ghalogs = {f["repository_name"].lower()
                           for f in csv.DictReader(archivo)}
            with open(opciones["casos_prueba"], encoding="utf-8") as archivo:
                casos = {c["repositorio"].lower() for c in json.load(archivo)}
        except FileNotFoundError as exc:
            raise CommandError(str(exc))
        sin_fuente = {n.lower() for n in SIN_FUENTE}

        inactivar, prueba, solapados = [], [], []
        for repo in Repositorio.objects.all():
            nombre = repo.nombre_completo.lower()
            if repo.es_demostracion:
                continue
            en_ghalogs = nombre in ghalogs or nombre in sin_fuente
            if en_ghalogs and nombre in casos:
                solapados.append(repo.nombre_completo)
            if en_ghalogs:
                inactivar.append(repo)
            if nombre in casos:
                prueba.append(repo)
        if solapados:
            raise CommandError("Repositorios en GHALogs y en los casos de "
                               f"prueba a la vez: {solapados}")

        cambian_estado = [r for r in inactivar if r.est_registro != "I"]
        cambian_prueba = [r for r in prueba if not r.es_prueba]
        self.stdout.write(
            f"Inactivos: {len(inactivar)} (GHALogs "
            f"{sum(r.nombre_completo.lower() in ghalogs for r in inactivar)}, "
            f"sin fuente {sum(r.nombre_completo.lower() in sin_fuente for r in inactivar)}); "
            f"cambian {len(cambian_estado)}.\n"
            f"De prueba: {len(prueba)} de {len(casos)} casos; cambian "
            f"{len(cambian_prueba)}.\n"
            f"Demostración sin cambios: "
            f"{Repositorio.objects.filter(es_demostracion=True).count()}.\n"
            f"Siguen activos y fuera de los dos grupos: "
            f"{Repositorio.objects.count() - len(inactivar) - len(prueba)}.")
        if not opciones["aplicar"]:
            self.stdout.write("Sin --aplicar: no se guardó nada.")
            return
        with transaction.atomic():
            Repositorio.objects.filter(
                id__in=[r.id for r in cambian_estado]).update(est_registro="I")
            Repositorio.objects.filter(
                id__in=[r.id for r in cambian_prueba]).update(es_prueba=True)
        self.stdout.write(self.style.SUCCESS("Cambios guardados."))
