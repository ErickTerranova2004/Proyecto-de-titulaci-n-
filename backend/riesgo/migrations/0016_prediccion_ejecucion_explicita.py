"""La tabla intermedia de ejecuciones previas pasa a ser un modelo explícito
(PrediccionEjecucion) sobre la misma tabla: solo cambia el estado de Django,
no la base de datos. Permite renombrarla al ER (int_prediccion_ejecucion)."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("riesgo", "0015_pendiente_despliegue")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="PrediccionEjecucion",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True,
                                                   primary_key=True,
                                                   serialize=False,
                                                   verbose_name="ID")),
                        ("prediccion", models.ForeignKey(
                            on_delete=django.db.models.deletion.CASCADE,
                            to="riesgo.prediccion")),
                        ("ejecucion_workflow", models.ForeignKey(
                            db_column="ejecucionworkflow_id",
                            on_delete=django.db.models.deletion.CASCADE,
                            to="riesgo.ejecucionworkflow")),
                    ],
                    options={
                        "db_table": "riesgo_prediccion_ejecuciones_previas",
                        "unique_together": {("prediccion", "ejecucion_workflow")},
                    },
                ),
                migrations.AlterField(
                    model_name="prediccion",
                    name="ejecuciones_previas",
                    field=models.ManyToManyField(
                        blank=True, related_name="predicciones_que_la_usan",
                        through="riesgo.PrediccionEjecucion",
                        to="riesgo.ejecucionworkflow"),
                ),
            ],
        ),
    ]
