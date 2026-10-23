from rest_framework import serializers

from riesgo.models import (DecisionDespliegue, EjecucionWorkflow, Prediccion,
                           Repositorio, VersionModelo)
from riesgo.services.github import REPO, SHA, WORKFLOW

EVENTOS = ["push", "workflow_dispatch", "release", "pull_request",
           "schedule", "workflow_run", "repository_dispatch"]


class SolicitudPrediccionSerializer(serializers.Serializer):
    repositorio = serializers.RegexField(
        REPO, error_messages={"invalid": "Use el formato propietario/nombre."})
    workflow_path = serializers.RegexField(
        WORKFLOW, error_messages={
            "invalid": "Use una ruta .github/workflows/<archivo>.yml"})
    rama = serializers.CharField(max_length=255, required=False,
                                 allow_blank=True, default="")
    head_sha = serializers.RegexField(SHA, required=False, allow_blank=True,
                                      default="")
    evento = serializers.ChoiceField(choices=EVENTOS, default="push")

    def validate(self, datos):
        if not datos["head_sha"] and not datos["rama"]:
            raise serializers.ValidationError(
                "Indique un commit (head_sha) o una rama.")
        return datos


class SolicitudRegistroSerializer(serializers.Serializer):
    """Alta manual de un workflow de despliegue por el administrador."""

    repositorio = serializers.RegexField(
        REPO, error_messages={"invalid": "Use el formato propietario/nombre."})
    workflow_path = serializers.RegexField(
        WORKFLOW, error_messages={
            "invalid": "Use una ruta .github/workflows/<archivo>.yml"})
    evidencia = serializers.CharField(
        min_length=30, max_length=2000, trim_whitespace=True,
        error_messages={"min_length": (
            "Describa la evidencia con al menos 30 caracteres: a qué entorno "
            "despliega y en qué paso del workflow.")})


class EjecucionSerializer(serializers.ModelSerializer):
    y = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = EjecucionWorkflow
        fields = ["run_id", "run_attempt", "evento", "rama", "conclusion",
                  "iniciada_en", "despliegue_ejecutado", "paso_fallido",
                  "etiqueta", "subtipo_etiqueta", "y", "etiquetada_en"]


class SolicitudDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=DecisionDespliegue.DECISIONES)
    comentario = serializers.CharField(max_length=1000, required=False,
                                       allow_blank=True, default="")


class DecisionSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username")

    class Meta:
        model = DecisionDespliegue
        fields = ["decision", "comentario", "usuario", "creada_en"]


class PrediccionSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username")
    repositorio = serializers.CharField(
        source="workflow.repositorio.nombre_completo")
    workflow_path = serializers.CharField(source="workflow.path")
    head_sha = serializers.CharField(source="commit.sha")
    version_modelo = serializers.CharField(source="version_modelo.version")
    cambio = serializers.SerializerMethodField()
    ejecuciones_previas = serializers.SerializerMethodField()
    ejecucion_real = EjecucionSerializer(read_only=True)
    decisiones = DecisionSerializer(many=True, read_only=True)

    class Meta:
        model = Prediccion
        fields = ["id", "usuario", "repositorio", "workflow_path", "head_sha",
                  "rama", "evento", "cambio", "variables", "probabilidad",
                  "nivel", "factores", "recomendaciones", "version_modelo",
                  "ejecuciones_previas", "ejecucion_real", "decisiones",
                  "verificada_en", "datos_github_extraidos_en", "creada_en"]

    def get_cambio(self, prediccion):
        commit = prediccion.commit
        return {"archivos_modificados": commit.archivos_modificados,
                "adiciones": commit.adiciones,
                "eliminaciones": commit.eliminaciones}

    def get_ejecuciones_previas(self, prediccion):
        return [{"run_id": e.run_id, "run_attempt": e.run_attempt,
                 "conclusion": e.conclusion, "iniciada_en": e.iniciada_en}
                for e in prediccion.ejecuciones_previas.all()]


class RepositorioSerializer(serializers.ModelSerializer):
    workflows = serializers.SerializerMethodField()

    class Meta:
        model = Repositorio
        fields = ["id", "nombre_completo", "workflows"]

    def get_workflows(self, repositorio):
        return [{"path": w.path, "nombre": w.nombre}
                for w in repositorio.workflows.all()
                if w.despliegue_validado and w.disponible_github]


class VersionModeloSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionModelo
        fields = ["id", "version", "nombre_modelo", "metadatos", "activo",
                  "registrado_en"]
