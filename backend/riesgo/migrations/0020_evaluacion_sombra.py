"""Evaluación en sombra de las versiones no activas (v1, v1.1).

Nuevo origen «sombra» y la columna id_prediccion_base (la predicción del
modelo activo cuya ejecución se evalúa). La clave foránea y su índice se
renombran en la 0021: Django crea el índice al final de esta migración.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models



class Migration(migrations.Migration):

    dependencies = [
        ('riesgo', '0019_auditoria'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='prediccion',
            name='prediccion_base',
            field=models.ForeignKey(blank=True, db_column='id_prediccion_base', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='riesgo.prediccion'),
        ),
        migrations.AlterField(
            model_name='prediccion',
            name='origen',
            field=models.CharField(choices=[('interactivo', 'Análisis en la plataforma'), ('lote', 'Análisis en lote de una ejecución posterior'), ('sombra', 'Evaluación en sombra de una versión no activa')], db_column='tip_origen', default='interactivo', max_length=12),
        ),
        migrations.AddConstraint(
            model_name='prediccion',
            constraint=models.UniqueConstraint(fields=('version_modelo', 'prediccion_base'), name='uk_trx_prediccion_id_version_modelo_id_prediccion_base'),
        ),
    ]
