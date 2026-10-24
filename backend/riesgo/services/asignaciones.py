"""Asignaciones al desarrollador: la última decisión de una predicción con
fecha límite, o una autorización (que solo requiere "Entendido"). El mensaje
es el comentario del líder técnico.

Las fechas son solo días (sin hora) en la zona de settings.TIME_ZONE
(America/Guayaquil), con timezone.localdate().
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone

from riesgo.models import DecisionDespliegue

logger = logging.getLogger(__name__)

# Días restantes a partir de los que la asignación pasa a "por vencer".
DIAS_POR_VENCER = 1
# Decisiones que el desarrollador atiende con un nuevo análisis.
ATENDIBLES = ("posponer", "solicitar_revision")
# Filtro de las decisiones que son asignaciones para el desarrollador.
ES_ASIGNACION = Q(fecha_limite__isnull=False) | Q(decision="autorizar")


def ultimas_decisiones(predicciones):
    """Última decisión de cada predicción del queryset dado."""
    ultima = (DecisionDespliegue.objects
              .filter(prediccion=OuterRef("prediccion"))
              .order_by("-creada_en", "-id").values("id")[:1])
    return DecisionDespliegue.objects.filter(
        prediccion__in=predicciones, id=Subquery(ultima))


def es_ultima(decision):
    return not decision.prediccion.decisiones.filter(
        creada_en__gt=decision.creada_en).exists()


def dias_restantes(decision, hoy=None):
    if decision.fecha_limite is None:
        return None
    return (decision.fecha_limite - (hoy or timezone.localdate())).days


def estado(decision, hoy=None):
    """pendiente, por_vencer (faltan 0 o 1 días), vencida o cumplida.

    Una autorización sin fecha queda pendiente hasta el "Entendido"."""
    if decision.fecha_limite is None and decision.decision != "autorizar":
        return None
    if decision.cumplida_en:
        return "cumplida"
    if decision.fecha_limite is None:
        return "pendiente"
    dias = dias_restantes(decision, hoy)
    if dias < 0:
        return "vencida"
    if dias <= DIAS_POR_VENCER:
        return "por_vencer"
    return "pendiente"


class RespuestaNoValida(Exception):
    """La decisión no se puede atender con este nuevo análisis."""

    def __init__(self, mensaje, codigo):
        super().__init__(mensaje)
        self.codigo = codigo


def validar_respuesta(decision_id, usuario, repositorio, workflow_path):
    """Comprueba que el usuario pueda atender esa decisión con un nuevo
    análisis del mismo workflow. Devuelve la decisión."""
    decision = (DecisionDespliegue.objects
                .select_related("prediccion__workflow__repositorio")
                .filter(id=decision_id).first())
    if decision is None or decision.prediccion.usuario_id != usuario.id:
        raise RespuestaNoValida(
            "La asignación no existe o no es de uno de sus análisis.",
            "asignacion_no_encontrada")
    if not es_ultima(decision):
        raise RespuestaNoValida(
            "Esa decisión ya no es la vigente para el análisis.",
            "asignacion_no_vigente")
    if decision.decision not in ATENDIBLES:
        raise RespuestaNoValida(
            "Una autorización no requiere un nuevo análisis.",
            "asignacion_no_atendible")
    if decision.prediccion_respuesta_id is not None:
        raise RespuestaNoValida(
            "Esta asignación ya se atendió con otro análisis.",
            "asignacion_ya_atendida")
    workflow = decision.prediccion.workflow
    if (workflow.repositorio.nombre_completo.lower() != repositorio.lower()
            or workflow.path != workflow_path):
        raise RespuestaNoValida(
            "El nuevo análisis debe ser del mismo repositorio y workflow que "
            "el análisis original.", "asignacion_otro_workflow")
    return decision


def registrar_respuesta(decision, prediccion, respuesta):
    """Enlaza el nuevo análisis y marca la asignación como cumplida."""
    ahora = timezone.now()
    decision.prediccion_respuesta = prediccion
    decision.respuesta_desarrollador = respuesta
    decision.vista_por_desarrollador_en = (
        decision.vista_por_desarrollador_en or ahora)
    decision.cumplida_en = decision.cumplida_en or ahora
    decision.save(update_fields=[
        "prediccion_respuesta", "respuesta_desarrollador",
        "vista_por_desarrollador_en", "cumplida_en"])


def notificar_por_correo(decision):
    """Correo opcional al desarrollador (CORREO_ASIGNACIONES=1)."""
    desarrollador = decision.prediccion.usuario
    if not settings.CORREO_ASIGNACIONES or not desarrollador.email:
        return False
    repositorio = decision.prediccion.workflow.repositorio.nombre_completo
    cuerpo = (f"{decision.usuario.username} le asignó una tarea sobre el "
              f"análisis {decision.prediccion_id} de {repositorio}.\n\n"
              f"Decisión: {decision.get_decision_display()}\n"
              f"Fecha límite: {decision.fecha_limite:%d/%m/%Y}\n")
    if decision.comentario:
        cuerpo += f"Mensaje: {decision.comentario}\n"
    try:
        send_mail(f"Asignación con fecha límite: {repositorio}", cuerpo,
                  settings.DEFAULT_FROM_EMAIL, [desarrollador.email])
    except Exception:  # noqa: BLE001 - el correo no debe impedir la decisión
        logger.warning("No se pudo enviar el correo de la asignación %s",
                       decision.id)
        return False
    return True
