from django.utils import timezone
from rest_framework import serializers

from riesgo.models import (DecisionDespliegue, EjecucionWorkflow, Prediccion,
                           Repositorio, VersionModelo)
from riesgo.services import asignaciones
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
    # Opcional: decisión del líder que este nuevo análisis atiende.
    atiende_decision = serializers.IntegerField(required=False,
                                                allow_null=True, default=None)
    respuesta_desarrollador = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default="")

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


def validar_fecha_limite(fecha):
    """No se admiten fechas pasadas (día local de America/Guayaquil)."""
    if fecha is not None and fecha < timezone.localdate():
        raise serializers.ValidationError(
            "La fecha límite no puede ser anterior a hoy.")
    return fecha


class SolicitudDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=DecisionDespliegue.DECISIONES)
    comentario = serializers.CharField(max_length=1000, required=False,
                                       allow_blank=True, default="")
    fecha_limite = serializers.DateField(required=False, allow_null=True,
                                         default=None,
                                         validators=[validar_fecha_limite])


class SolicitudFechaLimiteSerializer(serializers.Serializer):
    fecha_limite = serializers.DateField(validators=[validar_fecha_limite])


def respuesta(decision):
    """Nuevo análisis con el que el desarrollador atendió la decisión."""
    nueva = decision.prediccion_respuesta
    if nueva is None:
        return None
    return {"id": nueva.id, "nivel": nueva.nivel,
            "probabilidad": nueva.probabilidad, "creada_en": nueva.creada_en}


class DecisionSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.username")
    estado = serializers.SerializerMethodField()
    prediccion_respuesta = serializers.SerializerMethodField()

    class Meta:
        model = DecisionDespliegue
        fields = ["id", "decision", "comentario", "usuario", "creada_en",
                  "fecha_limite", "vista_por_desarrollador_en", "cumplida_en",
                  "estado", "prediccion_respuesta", "respuesta_desarrollador"]

    def get_estado(self, decision):
        return asignaciones.estado(decision)

    def get_prediccion_respuesta(self, decision):
        return respuesta(decision)


class AsignacionSerializer(serializers.ModelSerializer):
    """Última decisión de una predicción con fecha límite."""

    prediccion = serializers.IntegerField(source="prediccion_id")
    repositorio = serializers.CharField(
        source="prediccion.workflow.repositorio.nombre_completo")
    workflow_path = serializers.CharField(source="prediccion.workflow.path")
    nivel = serializers.CharField(source="prediccion.nivel")
    desarrollador = serializers.CharField(
        source="prediccion.usuario.username")
    lider = serializers.CharField(source="usuario.username")
    mensaje = serializers.CharField(source="comentario")
    nivel_original = serializers.CharField(source="prediccion.nivel")
    prediccion_respuesta = serializers.SerializerMethodField()
    dias_restantes = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    vista = serializers.SerializerMethodField()

    class Meta:
        model = DecisionDespliegue
        fields = ["id", "prediccion", "repositorio", "workflow_path", "nivel",
                  "desarrollador", "lider", "decision", "mensaje",
                  "fecha_limite", "dias_restantes", "estado", "vista",
                  "vista_por_desarrollador_en", "cumplida_en", "creada_en",
                  "nivel_original", "prediccion_respuesta",
                  "respuesta_desarrollador"]

    def get_prediccion_respuesta(self, decision):
        return respuesta(decision)

    def get_dias_restantes(self, decision):
        return asignaciones.dias_restantes(decision)

    def get_estado(self, decision):
        return asignaciones.estado(decision)

    def get_vista(self, decision):
        return decision.vista_por_desarrollador_en is not None


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
    workflows_validados = serializers.SerializerMethodField()

    class Meta:
        model = Repositorio
        fields = ["id", "nombre_completo", "workflows", "workflows_validados"]

    def get_workflows_validados(self, repositorio):
        return sum(1 for w in repositorio.workflows.all()
                   if w.despliegue_validado)

    def get_workflows(self, repositorio):
        return [{"path": w.path, "nombre": w.nombre}
                for w in repositorio.workflows.all()
                if w.despliegue_validado and w.disponible_github]


class VersionModeloSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersionModelo
        fields = ["id", "version", "nombre_modelo", "metadatos", "activo",
                  "registrado_en"]
