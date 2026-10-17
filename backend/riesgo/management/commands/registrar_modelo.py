import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from riesgo.models import ROLES, VersionModelo


class Command(BaseCommand):
    help = ("Crea los grupos de roles y registra (y activa) un modelo "
            "entrenado a partir de su archivo JSON de metadatos.")

    def add_arguments(self, parser):
        parser.add_argument("--modelo", default="v1.1",
                            help="Versión del modelo, p. ej. v1 o v1.1")

    def handle(self, *args, **opciones):
        for rol in ROLES:
            Group.objects.get_or_create(name=rol)

        version = opciones["modelo"]
        archivo = version.replace(".", "_")
        meta_ruta = settings.MODELOS_DIR / f"modelo_riesgo_{archivo}.json"
        if not meta_ruta.exists():
            raise CommandError(f"No existe {meta_ruta}")
        meta = json.loads(meta_ruta.read_text(encoding="utf-8"))
        for nombre in (f"modelo_riesgo_{archivo}.joblib",
                       f"modelo_riesgo_{archivo}_shap.joblib"):
            if not (Path(settings.MODELOS_DIR) / nombre).exists():
                raise CommandError(f"Falta {nombre} en {settings.MODELOS_DIR}")

        VersionModelo.objects.update(activo=False)
        modelo, creado = VersionModelo.objects.update_or_create(
            version=version,
            defaults={
                "nombre_modelo": meta["modelo"],
                "archivo": f"modelo_riesgo_{archivo}.joblib",
                "archivo_explicacion": f"modelo_riesgo_{archivo}_shap.joblib",
                "metadatos": meta,
                "activo": True,
            },
        )
        accion = "registrado" if creado else "actualizado"
        self.stdout.write(self.style.SUCCESS(
            f"Modelo {modelo} {accion} y activado. Roles: {', '.join(ROLES)}"))
