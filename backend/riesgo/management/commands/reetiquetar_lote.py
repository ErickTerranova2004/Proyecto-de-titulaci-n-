"""Re-etiqueta el resultado real de las predicciones del análisis en lote.

Vuelve a consultar los jobs de cada ejecución evaluada y el YAML del workflow
en su commit (verificacion.etiquetar_run) y actualiza la etiqueta. Sin
--aplicar solo informa. --salida guarda la etiqueta antes y después de cada
predicción (JSON) para la trazabilidad del cambio.
"""

import json
from collections import Counter

from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from riesgo.auditoria import ComandoAuditado
from riesgo.models import Prediccion
from riesgo.services import github, lote
from riesgo.services.verificacion import etiquetar_run

CAMPOS = ("etiqueta", "subtipo_etiqueta", "despliegue_ejecutado",
          "paso_fallido")


class Command(ComandoAuditado):
    help = "Re-etiqueta las ejecuciones de las predicciones en lote."

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true")
        parser.add_argument("--salida", help="JSON con el antes y el después.")

    def handle(self, *args, **opciones):
        predicciones = (Prediccion.objects.filter(origen="lote")
                        .select_related("ejecucion_real", "commit",
                                        "workflow__repositorio")
                        .order_by("id"))
        gh = lote.cliente_contado()
        cambios, detalle = Counter(), []
        antes, despues = Counter(), Counter()
        for p in predicciones:
            ejecucion = p.ejecucion_real
            repo = p.workflow.repositorio.nombre_completo
            run = {"id": ejecucion.run_id, "conclusion": ejecucion.conclusion,
                   "head_sha": p.commit.sha}
            try:
                jobs = gh.jobs_intento(repo, ejecucion.run_id,
                                       ejecucion.run_attempt)
                nueva = etiquetar_run(gh, p.workflow, run, jobs)
            except github.LimiteExcedido:
                raise CommandError("Límite de la API agotado; repita más tarde.")
            previa = {c: getattr(ejecucion, c) for c in CAMPOS}
            antes[previa["etiqueta"]] += 1
            despues[nueva["etiqueta"]] += 1
            cambios[(previa["etiqueta"], nueva["etiqueta"])] += 1
            detalle.append({"prediccion": p.id, "repositorio": repo,
                            "run_id": ejecucion.run_id, "antes": previa,
                            "despues": nueva})
            if opciones["aplicar"] and previa != {c: nueva[c] for c in CAMPOS}:
                with transaction.atomic():
                    for campo in CAMPOS:
                        setattr(ejecucion, campo, nueva[campo])
                    ejecucion.etiquetada_en = timezone.now()
                    ejecucion.save()
        self.stdout.write(f"Predicciones: {len(detalle)} · llamadas a la API: "
                          f"{gh.sesion.llamadas}")
        self.stdout.write(f"Antes: {dict(antes)}\nDespués: {dict(despues)}")
        for (a, d), n in sorted(cambios.items(), key=lambda x: -x[1]):
            if a != d:
                self.stdout.write(f"  {a} → {d}: {n}")
        if opciones["salida"]:
            with open(opciones["salida"], "w", encoding="utf-8") as archivo:
                json.dump(detalle, archivo, ensure_ascii=False, indent=1,
                          default=str)
        self.stdout.write("Cambios guardados." if opciones["aplicar"]
                          else "Sin --aplicar: no se guardó nada.")
