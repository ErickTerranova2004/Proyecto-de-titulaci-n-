from django.db import migrations, models

ANTERIOR = (
    r"(?i)\bdeploy|despliegue|despleg|\brollout\b|\bpromote\b|"
    r"helm (upgrade|install)|kubectl (apply|set image|rollout)|"
    r"terraform apply|wrangler-action"
)
NUEVO = (
    r"(?i)\bdeploy(?!ments?\b)|despliegue|despleg|\brollout\b|\bpromote\b|"
    r"helm (upgrade|install)|kubectl (apply|set image|rollout)|"
    r"terraform apply|wrangler-action"
)


def actualizar(apps, schema_editor):
    """Solo los workflows con el patrón por defecto anterior; los patrones
    ajustados por el administrador no se tocan."""
    Workflow = apps.get_model("riesgo", "Workflow")
    Workflow.objects.filter(patron_paso_despliegue=ANTERIOR).update(patron_paso_despliegue=NUEVO)


def revertir(apps, schema_editor):
    Workflow = apps.get_model("riesgo", "Workflow")
    Workflow.objects.filter(patron_paso_despliegue=NUEVO).update(patron_paso_despliegue=ANTERIOR)


class Migration(migrations.Migration):

    dependencies = [
        ("riesgo", "0010_patron_despliegue_por_acciones"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workflow",
            name="patron_paso_despliegue",
            field=models.CharField(default=NUEVO, max_length=500),
        ),
        migrations.RunPython(actualizar, revertir),
    ]
