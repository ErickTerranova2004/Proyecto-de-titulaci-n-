from django.core.management.base import BaseCommand, CommandError

from riesgo.models import Repositorio
from riesgo.services import github
from riesgo.services.sincronizacion import sincronizar_repositorio


class Command(BaseCommand):
    help = ("Recopila desde GitHub las ejecuciones recientes de los workflows "
            "de despliegue validados y las guarda en la base de datos. "
            "Puede programarse (Programador de tareas de Windows o cron) para "
            "que la recopilación sea automática.")

    def add_arguments(self, parser):
        parser.add_argument("repositorios", nargs="+",
                            help="Uno o más repositorios propietario/nombre")
        parser.add_argument("--por-workflow", type=int, default=20)

    def handle(self, *args, **opciones):
        cliente = github.GitHubClient()
        for nombre in opciones["repositorios"]:
            repo = Repositorio.objects.filter(
                nombre_completo__iexact=nombre).first()
            if repo is None:
                raise CommandError(f"{nombre} no está registrado")
            try:
                r = sincronizar_repositorio(repo, cliente,
                                            opciones["por_workflow"])
            except github.LimiteExcedido:
                raise CommandError("Límite de la API de GitHub agotado")
            self.stdout.write(self.style.SUCCESS(
                f"{r['repositorio']}: {r['ejecuciones_guardadas']} ejecuciones "
                f"de {r['workflows']} workflows"))
            for error in r["errores"]:
                self.stdout.write(self.style.WARNING(f"  {error}"))
