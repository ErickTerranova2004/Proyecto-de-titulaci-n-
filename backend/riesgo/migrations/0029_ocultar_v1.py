"""Oculta la versión v1 del modelo (est_registro = 'I'), como la 0022 con
v1.1.

No se borra: hay predicciones (interactivas, de lote y en sombra) que la
referencian y sus archivos siguen en modelos/. Deja de salir en Modelos, la
supervisión, la comparación y los selectores, y el lote ya no la evalúa en
sombra (solo usa versiones con est_registro = 'A'). La comparación en sombra
con v1 quedó guardada en informes/comparacion_sombra_v1.md.
"""

from django.db import migrations
from django.utils import timezone

USUARIO = "migracion_0029"


def estado(valor):
    def aplicar(apps, schema_editor):
        VersionModelo = apps.get_model("riesgo", "VersionModelo")
        VersionModelo.objects.filter(version="v1", activo=False).update(
            est_registro=valor, usu_modificacion=USUARIO,
            fec_modificacion=timezone.now())
    return aplicar


class Migration(migrations.Migration):

    dependencies = [("riesgo", "0028_nombres_er_activacion")]

    operations = [migrations.RunPython(estado("I"), estado("A"))]
