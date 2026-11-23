"""Oculta la versión v1.1 del modelo (est_registro = 'I').

No se borra: hay predicciones interactivas y en sombra que la referencian y
sus archivos siguen en modelos/. La API de modelos, la supervisión, la
comparación en sombra y evaluar_sombra solo usan versiones con
est_registro = 'A'. La comparación en sombra con v1.1 quedó guardada en
informes/comparacion_sombra_v2.md.
"""

from django.db import migrations
from django.utils import timezone

USUARIO = "migracion_0022"


def estado(valor):
    def aplicar(apps, schema_editor):
        VersionModelo = apps.get_model("riesgo", "VersionModelo")
        VersionModelo.objects.filter(version="v1.1", activo=False).update(
            est_registro=valor, usu_modificacion=USUARIO,
            fec_modificacion=timezone.now())
    return aplicar


class Migration(migrations.Migration):

    dependencies = [("riesgo", "0021_nombres_er_sombra")]

    operations = [migrations.RunPython(estado("I"), estado("A"))]
