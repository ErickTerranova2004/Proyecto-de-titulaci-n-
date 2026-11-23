"""Nombres del ER (pk_/fk_/ix_/sq_) para trx_restablecimiento_clave, con el
mismo SQL idempotente de la 0018."""

import importlib

from django.db import migrations

ER = importlib.import_module(
    "riesgo.migrations.0018_nombres_er_indices_y_vistas_seg")
RENOMBRAR = ER.RENOMBRAR.replace(
    "ARRAY['mae_repositorio'",
    "ARRAY['trx_restablecimiento_clave', 'mae_repositorio'")
assert RENOMBRAR != ER.RENOMBRAR


class Migration(migrations.Migration):

    dependencies = [("riesgo", "0023_restablecimiento_clave")]

    operations = [migrations.RunSQL(RENOMBRAR, migrations.RunSQL.noop)]
