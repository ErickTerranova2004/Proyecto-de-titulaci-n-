"""Nombres del ER (pk_/fk_/ix_/sq_) para trx_informe_cumplimiento y
trx_descarga_informe, con el mismo SQL idempotente de la 0018 (en una
migración aparte: Django crea las claves foráneas al final de la 0025)."""

import importlib

from django.db import migrations

ER = importlib.import_module(
    "riesgo.migrations.0018_nombres_er_indices_y_vistas_seg")
RENOMBRAR = ER.RENOMBRAR.replace(
    "ARRAY['mae_repositorio'",
    "ARRAY['trx_informe_cumplimiento', 'trx_descarga_informe', "
    "'mae_repositorio'")
assert RENOMBRAR != ER.RENOMBRAR


class Migration(migrations.Migration):

    dependencies = [("riesgo", "0025_informe_cumplimiento")]

    operations = [migrations.RunSQL(RENOMBRAR, migrations.RunSQL.noop)]
