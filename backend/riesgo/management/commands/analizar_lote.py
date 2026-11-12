"""Analiza en lote las ejecuciones posteriores a la fecha de corte.

Cada pasada:
1. Enlaza el resultado real de los análisis interactivos pendientes (de los
   últimos --dias-interactivos días, repositorios reales y de demostración),
   igual que el botón «Verificar resultado real», aunque nadie tenga la
   pestaña abierta.
2. Para los workflows validados de repositorios activos que no son de prueba
   ni de demostración: predice con el modelo activo cada ejecución terminada
   que empezó después de metadatos.fecha_corte (variables en su inicio) y
   etiqueta su resultado real. Solo lista lo creado desde la pasada anterior
   menos 48 h (SeguimientoLote) y se salta las ejecuciones ya enlazadas a un
   análisis interactivo.

    manage.py analizar_lote --contar            # solo cuenta (no guarda nada)
    manage.py analizar_lote --usuario analisis_lote

Lo programa scripts/analizar_lote.cmd (Programador de tareas, cada 4 h).
"""

import time
from collections import Counter

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from riesgo.models import Workflow
from riesgo.services import github, lote
from riesgo.services.features import fecha
from riesgo.services.predictor import SinModeloActivo, modelo_activo


class Command(BaseCommand):
    help = "Validación prospectiva: analiza ejecuciones posteriores al corte."

    def add_arguments(self, parser):
        parser.add_argument("--contar", action="store_true",
                            help="Solo cuenta las ejecuciones (no guarda nada).")
        parser.add_argument("--usuario", default="analisis_lote",
                            help="Usuario al que se atribuyen las predicciones.")
        parser.add_argument("--repos", nargs="*", help="Solo estos repositorios.")
        parser.add_argument("--max-llamadas", type=int, default=3000,
                            help="Se detiene al superar este número de llamadas.")
        parser.add_argument("--dias-interactivos", type=int,
                            default=lote.DIAS_INTERACTIVOS,
                            help="Antigüedad máxima de los análisis "
                                 "interactivos que se verifican.")

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
        inicio = time.time()
        self.stdout.write(f"=== Pasada del lote {timezone.localtime():%Y-%m-%d %H:%M:%S} "
                          f"· modelo {version.version}; corte "
                          f"{corte:%Y-%m-%d %H:%M:%S} UTC; {workflows.count()} workflows.")
        errores = []
        try:
            self._interactivos(gh, opciones, errores)
            total, etiquetas = self._workflows(gh, workflows, corte, version,
                                               usuario, opciones, errores)
        except github.LimiteExcedido:
            raise CommandError("Límite de la API de GitHub agotado; "
                               "vuelva a ejecutar más tarde.")
        self.stdout.write(
            f"\nTotal: {dict(total)}\nEtiquetas: {dict(etiquetas)}\n"
            f"Llamadas a la API: {gh.sesion.llamadas} · sin cambios (304, no "
            f"gastan cuota): {gh.sesion.sin_cambios} · {time.time() - inicio:.0f} s")
        try:
            cuota = gh.limite()
            self.stdout.write(f"Cuota restante: {cuota.get('remaining')} de "
                              f"{cuota.get('limit')}")
        except github.GitHubError:
            pass
        for error in errores:
            self.stdout.write(self.style.ERROR(error))
        self.stdout.write("=== Fin de la pasada")

    def _interactivos(self, gh, opciones, errores):
        pendientes = lote.interactivos_pendientes(opciones["dias_interactivos"])
        if opciones["contar"]:
            self.stdout.write(f"Análisis interactivos pendientes: {pendientes.count()}")
            return
        resumen, enlazadas, fallos = lote.verificar_interactivos(
            gh, opciones["dias_interactivos"])
        errores.extend(fallos)
        self.stdout.write(f"Análisis interactivos: {resumen}")
        for p in enlazadas:
            self.stdout.write(f"  análisis {p.id} ({p.workflow.repositorio}) → run "
                              f"{p.ejecucion_real.run_id}: {p.ejecucion_real.etiqueta}")

    def _workflows(self, gh, workflows, corte, version, usuario, opciones,
                   errores):
        total, etiquetas = Counter(), Counter()
        for i, workflow in enumerate(workflows, 1):
            if gh.sesion.llamadas > opciones["max_llamadas"]:
                self.stdout.write(self.style.WARNING(
                    f"Límite de {opciones['max_llamadas']} llamadas alcanzado en "
                    f"{i - 1}/{workflows.count()} workflows; vuelva a ejecutar."))
                break
            try:
                if opciones["contar"]:
                    grupos, _ = lote.revisar_workflow(gh, workflow, corte, version)
                    resumen = lote.resumen_grupos(grupos)
                else:
                    resumen, creadas = lote.analizar_workflow(
                        gh, workflow, corte, version, usuario)
                    etiquetas.update(p.ejecucion_real.etiqueta for p in creadas)
            except github.LimiteExcedido:
                raise
            except github.GitHubError as exc:
                errores.append(f"{workflow}: {exc}")
                continue
            total.update(resumen)
            if any(resumen.get(k) for k in ("analizar", "analizadas", "pendientes",
                                            "enlazadas_interactivo")):
                self.stdout.write(f"{i}. {workflow.repositorio}: {resumen}")
        return total, etiquetas
