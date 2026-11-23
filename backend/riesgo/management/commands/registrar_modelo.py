import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import CommandError

from riesgo.auditoria import ComandoAuditado
from riesgo.models import ROLES, VersionModelo
from riesgo.services.modelos import registrar_activacion


class Command(ComandoAuditado):
    help = ("Crea los grupos de roles y registra (y activa) un modelo "
            "entrenado a partir de su archivo JSON de metadatos. Con "
            "--sin-activar lo registra como alternativo (p. ej. v2-xgb).")

    def add_arguments(self, parser):
        parser.add_argument("--modelo", default="v2",
                            help="Versión del modelo, p. ej. v2, v2-xgb o v1.1")
        parser.add_argument("--sin-activar", action="store_true",
                            help="Registrar sin cambiar el modelo principal.")

    def handle(self, *args, **opciones):
        for rol in ROLES:
            Group.objects.get_or_create(name=rol)

        version = opciones["modelo"]
        archivo = version.replace(".", "_").replace("-", "_")
        meta_ruta = settings.MODELOS_DIR / f"modelo_riesgo_{archivo}.json"
        if not meta_ruta.exists():
            raise CommandError(f"No existe {meta_ruta}")
        meta = json.loads(meta_ruta.read_text(encoding="utf-8"))
        for nombre in (f"modelo_riesgo_{archivo}.joblib",
                       f"modelo_riesgo_{archivo}_shap.joblib"):
            if not (Path(settings.MODELOS_DIR) / nombre).exists():
                raise CommandError(f"Falta {nombre} en {settings.MODELOS_DIR}")

        activar = not opciones["sin_activar"]
        anterior = VersionModelo.objects.filter(activo=True).first()
        defaults = {
            "nombre_modelo": meta["modelo"],
            "archivo": f"modelo_riesgo_{archivo}.joblib",
            "archivo_explicacion": f"modelo_riesgo_{archivo}_shap.joblib",
            "metadatos": meta,
        }
        if activar:
            VersionModelo.objects.update(activo=False)
            defaults["activo"] = True
        modelo, creado = VersionModelo.objects.update_or_create(
            version=version, defaults=defaults)
        if activar:
            # Historial de activaciones (trx_activacion_modelo).
            registrar_activacion(modelo, anterior, origen="comando")
        accion = "registrado" if creado else "actualizado"
        estado = "y activado" if activar else "sin activar (alternativo)"
        self.stdout.write(self.style.SUCCESS(
            f"Modelo {modelo} {accion} {estado}. Roles: {', '.join(ROLES)}"))
