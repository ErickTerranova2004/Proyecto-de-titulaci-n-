"""Asignaciones al desarrollador: la última decisión de una predicción con
fecha límite. El mensaje es el comentario del líder técnico.

Las fechas son solo días (sin hora) en la zona de settings.TIME_ZONE
(America/Guayaquil), con timezone.localdate().
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from riesgo.models import DecisionDespliegue

logger = logging.getLogger(__name__)

# Días restantes a partir de los que la asignación pasa a "por vencer".
DIAS_POR_VENCER = 1


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
    """pendiente, por_vencer (faltan 0 o 1 días), vencida o cumplida."""
    if decision.fecha_limite is None:
        return None
    if decision.cumplida_en:
        return "cumplida"
    dias = dias_restantes(decision, hoy)
    if dias < 0:
        return "vencida"
    if dias <= DIAS_POR_VENCER:
        return "por_vencer"
    return "pendiente"


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
