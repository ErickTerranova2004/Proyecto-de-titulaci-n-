"""Nombres del ER (pk_/fk_/ix_/sq_) para trx_activacion_modelo, con el mismo
SQL idempotente de la 0018 (en una migración aparte: Django crea las claves
foráneas al final de la 0027)."""

import importlib

from django.db import migrations

ER = importlib.import_module(
    "riesgo.migrations.0018_nombres_er_indices_y_vistas_seg")
RENOMBRAR = ER.RENOMBRAR.replace(
    "ARRAY['mae_repositorio'",
    "ARRAY['trx_activacion_modelo', 'mae_repositorio'")
assert RENOMBRAR != ER.RENOMBRAR


class Migration(migrations.Migration):

    dependencies = [("riesgo", "0027_activacion_modelo")]

    operations = [migrations.RunSQL(RENOMBRAR, migrations.RunSQL.noop)]
