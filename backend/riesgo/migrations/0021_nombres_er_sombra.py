"""Nombres del ER (fk_/ix_) para la clave foránea id_prediccion_base de la
0020, con el mismo SQL idempotente de la 0018."""

import importlib

from django.db import migrations

ER = importlib.import_module(
    "riesgo.migrations.0018_nombres_er_indices_y_vistas_seg")


class Migration(migrations.Migration):

    dependencies = [("riesgo", "0020_evaluacion_sombra")]

    operations = [migrations.RunSQL(ER.RENOMBRAR, migrations.RunSQL.noop)]
