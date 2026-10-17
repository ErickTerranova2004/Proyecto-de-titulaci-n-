"""Registra y valida los workflows de despliegue del dataset final (v1.1).

Solo se marcan como validados los workflows presentes en
datos_procesados/dataset_riesgo_despliegue_v1_1.csv que ejecutaron al menos un
paso de despliegue en entorno de aplicación. La evidencia de cada uno se
toma de informes/deploy_runs_v1_1.csv (pasos de despliegue ejecutados en
2023 según log_insights de GHALogs) y se documenta en
informes/workflows_validados.csv.
"""

import csv
from collections import Counter, defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from riesgo.models import Repositorio, Workflow

CRITERIO = (
    "Validado automáticamente a partir del dataset final de la tesis "
    "(GHALogs v1.0.1, Zenodo 14796970). Criterio: el workflow ejecutó pasos "
    "reales de despliegue a un entorno de aplicación según log_insights "
    "(find_deploy_runs.py + label_deploy_runs.py), excluyendo GitHub Pages, "
    "clústeres efímeros de prueba y vistas previas de pull requests. "
)


class Command(BaseCommand):
    help = "Valida como workflows de despliegue los del dataset final."

    def add_arguments(self, parser):
        raiz = settings.PROJECT_DIR
        parser.add_argument("--dataset", default=str(
            raiz / "datos_procesados" / "dataset_riesgo_despliegue_v1_1.csv"))
        parser.add_argument("--niveles", default=str(
            raiz / "informes" / "deploy_runs_v1_1.csv"))
        parser.add_argument("--salida", default=str(
            raiz / "informes" / "workflows_validados.csv"))

    def handle(self, *args, **opciones):
        try:
            with open(opciones["dataset"], encoding="utf-8") as archivo:
                filas = list(csv.DictReader(archivo))
            with open(opciones["niveles"], encoding="utf-8") as archivo:
                niveles = list(csv.DictReader(archivo))
        except FileNotFoundError as exc:
            raise CommandError(str(exc))

        # Mecanismos y ejecuciones con despliegue por (nombre, ruta).
        mecanismos = defaultdict(set)
        con_despliegue = Counter()
        for fila in niveles:
            if fila["entorno"] != "aplicación" or not fila["pasos_despliegue"]:
                continue
            clave = (fila["repository_name"], fila["workflow_path"])
            mecanismos[clave].update(fila["pasos_despliegue"].split("; "))
            con_despliegue[clave] += 1

        # Agrupa por identificadores estables de GitHub.
        repos = defaultdict(Counter)
        workflows = defaultdict(lambda: {"nombres": set(), "filas": 0,
                                         "positivos": 0, "ambiguas": 0})
        for fila in filas:
            repo_id = int(float(fila["repo_id"]))
            repos[repo_id][fila["repository_name"]] += 1
            w = workflows[(repo_id, fila["workflow_path"])]
            w["id"] = int(float(fila["workflow_id"]))
            w["nombres"].add(fila["repository_name"])
            w["filas"] += 1
            if fila.get("ambiguo") == "1" or fila["y"] == "":
                w["ambiguas"] += 1
            else:
                w["positivos"] += int(float(fila["y"]))

        ahora = timezone.now()
        documentados = []
        with transaction.atomic():
            objetos_repo = {}
            for repo_id, nombres in repos.items():
                nombre = nombres.most_common(1)[0][0]
                propietario, _, corto = nombre.partition("/")
                objetos_repo[repo_id], _ = Repositorio.objects.update_or_create(
                    github_id=repo_id,
                    defaults={"nombre_completo": nombre,
                              "propietario": propietario, "nombre": corto})
            for (repo_id, ruta), w in workflows.items():
                claves = [(n, ruta) for n in w["nombres"]]
                mec = sorted(set().union(*(mecanismos[c] for c in claves)))
                n_desp = sum(con_despliegue[c] for c in claves)
                datos = (f"Ejecuciones con paso de despliegue ejecutado en "
                         f"entorno de aplicación: {n_desp}. Mecanismos: "
                         f"{', '.join(mec) or 'ninguno'}. Filas en el "
                         f"dataset final: {w['filas']} ({w['positivos']} con "
                         f"despliegue no completado, {w['ambiguas']} "
                         f"ambiguas).")
                # Sin ningún despliegue observado en entorno de aplicación
                # (solo en vistas previas o clústeres efímeros) no hay
                # evidencia suficiente: se registra sin validar.
                validado = n_desp > 0
                evidencia = CRITERIO + datos if validado else (
                    "NO VALIDADO. El workflow está en el dataset final, pero "
                    "sus pasos de despliegue solo se ejecutaron en vistas "
                    "previas o clústeres efímeros de prueba; sus filas en "
                    "el dataset son fallos antes del despliegue que la "
                    "clasificación por ejecución no pudo reconocer como "
                    "efímeros (limitación documentada en "
                    "informes/workflows_validados.md). " + datos)
                Workflow.objects.update_or_create(
                    repositorio=objetos_repo[repo_id], path=ruta,
                    defaults={"github_id": w["id"],
                              "despliegue_validado": validado,
                              "evidencia_validacion": evidencia,
                              "validado_por": None,
                              "validado_en": ahora if validado else None})
                documentados.append({
                    "repositorio": objetos_repo[repo_id].nombre_completo,
                    "repo_github_id": repo_id,
                    "workflow_path": ruta,
                    "workflow_github_id": w["id"],
                    "despliegue_validado": validado,
                    "ejecuciones_con_despliegue": n_desp,
                    "mecanismos": "; ".join(mec),
                    "filas_dataset": w["filas"],
                    "positivos_dataset": w["positivos"],
                    "ambiguas_dataset": w["ambiguas"],
                })

            # Los workflows validados automáticamente con un dataset anterior
            # que ya no están en el actual dejan de estar validados. Las
            # validaciones manuales (validado_por no vacío) no se tocan.
            vigentes = {(objetos_repo[r].id, ruta) for r, ruta in workflows}
            retirados = 0
            for wf in Workflow.objects.filter(despliegue_validado=True,
                                              validado_por__isnull=True):
                if (wf.repositorio_id, wf.path) not in vigentes:
                    wf.despliegue_validado = False
                    wf.validado_en = None
                    wf.evidencia_validacion = (
                        "NO VALIDADO. Validado con un dataset anterior y "
                        "retirado porque no está en el dataset final "
                        "vigente. Evidencia anterior: "
                        + wf.evidencia_validacion)
                    wf.save()
                    retirados += 1

        with open(opciones["salida"], "w", newline="",
                  encoding="utf-8") as archivo:
            escritor = csv.DictWriter(archivo,
                                      fieldnames=list(documentados[0]))
            escritor.writeheader()
            escritor.writerows(sorted(documentados, key=lambda d: (
                d["repositorio"], d["workflow_path"])))
        validados = sum(d["despliegue_validado"] for d in documentados)
        self.stdout.write(self.style.SUCCESS(
            f"{len(objetos_repo)} repositorios y {len(documentados)} "
            f"workflows registrados: {validados} validados y "
            f"{len(documentados) - validados} sin validar; {retirados} "
            f"retirados de un dataset anterior. Evidencia: "
            f"{opciones['salida']}"))
