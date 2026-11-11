"""Analiza en lote las ejecuciones posteriores a la fecha de corte.

Para los workflows validados de repositorios activos que no son de prueba ni
de demostración: predice con el modelo activo cada ejecución terminada que
empezó después de metadatos.fecha_corte (variables en su inicio) y etiqueta
su resultado real. Se puede repetir: solo analiza las ejecuciones nuevas o que
hayan terminado desde la vez anterior.

    manage.py analizar_lote --contar            # solo cuenta (1 llamada por workflow)
    manage.py analizar_lote --usuario analisis_lote
"""

import time
from collections import Counter

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from riesgo.models import Workflow
from riesgo.services import github, lote
from riesgo.services.features import fecha
from riesgo.services.predictor import SinModeloActivo, modelo_activo


class Command(BaseCommand):
    help = "Validación prospectiva: analiza ejecuciones posteriores al corte."

    def add_arguments(self, parser):
        parser.add_argument("--contar", action="store_true",
                            help="Solo cuenta las ejecuciones (no analiza).")
        parser.add_argument("--usuario", default="analisis_lote",
                            help="Usuario al que se atribuyen las predicciones.")
        parser.add_argument("--repos", nargs="*", help="Solo estos repositorios.")
        parser.add_argument("--max-llamadas", type=int, default=3000,
                            help="Se detiene al superar este número de llamadas.")

    def handle(self, *args, **opciones):
        try:
            version = modelo_activo()
        except SinModeloActivo:
            raise CommandError("No hay un modelo activo.")
        corte = fecha(version.metadatos.get("fecha_corte"))
        if corte is None:
            raise CommandError(f"El modelo {version} no tiene fecha_corte.")
        usuario = None
        if not opciones["contar"]:
            usuario = get_user_model().objects.filter(
                username=opciones["usuario"]).first()
            if usuario is None:
                raise CommandError(f"No existe el usuario {opciones['usuario']}.")

        workflows = (Workflow.objects.filter(
            despliegue_validado=True, disponible_github=True,
            repositorio__est_registro="A", repositorio__es_prueba=False,
            repositorio__es_demostracion=False)
            .select_related("repositorio").order_by("repositorio__nombre_completo"))
        if opciones["repos"]:
            workflows = workflows.filter(
                repositorio__nombre_completo__in=opciones["repos"])
        gh = lote.cliente_contado()
        self.stdout.write(f"Modelo {version.version}; corte {corte:%Y-%m-%d %H:%M:%S} "
                          f"UTC; {workflows.count()} workflows.")
        total, etiquetas, errores = Counter(), Counter(), []
        inicio = time.time()
        for i, workflow in enumerate(workflows, 1):
            if gh.sesion.llamadas > opciones["max_llamadas"]:
                self.stdout.write(self.style.WARNING(
                    f"Límite de {opciones['max_llamadas']} llamadas alcanzado en "
                    f"{i - 1}/{workflows.count()} workflows; vuelva a ejecutar."))
                break
            try:
                if opciones["contar"]:
                    grupos = lote.clasificar(
                        lote.ejecuciones_posteriores(gh, workflow, corte),
                        lote.run_ids_analizados(workflow))
                    resumen = {k: (len(v) if isinstance(v, list) else v)
                               for k, v in grupos.items()}
                else:
                    resumen, creadas = lote.analizar_workflow(
                        gh, workflow, corte, version, usuario)
                    etiquetas.update(p.ejecucion_real.etiqueta for p in creadas)
            except github.LimiteExcedido:
                raise CommandError("Límite de la API de GitHub agotado; "
                                   "vuelva a ejecutar más tarde.")
            except github.GitHubError as exc:
                errores.append(f"{workflow}: {exc}")
                continue
            total.update(resumen)
            if any(resumen.get(k) for k in ("analizar", "analizadas", "pendientes")):
                self.stdout.write(f"{i}. {workflow.repositorio}: {resumen}")
        self.stdout.write(
            f"\nTotal: {dict(total)}\nEtiquetas: {dict(etiquetas)}\n"
            f"Llamadas a la API: {gh.sesion.llamadas} · {time.time() - inicio:.0f} s")
        for error in errores:
            self.stdout.write(self.style.ERROR(error))
