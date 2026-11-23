"""Activación de versiones del modelo.

Solo se puede activar una versión visible (est_registro = 'A') con fecha de
corte (metadatos.fecha_corte): sin ella el análisis en lote no sabe desde
cuándo evaluar y la supervisión no se puede calcular. v1 y v1.1 no la tienen;
solo se evalúan en sombra (services/sombra.py).

Activar exige escribir el nombre de la versión como confirmación y deja una
fila en trx_activacion_modelo (quién, cuándo, desde dónde y cuál estaba
activa antes).
"""

from django.db import transaction

from .. import auditoria
from ..models import ActivacionModelo, VersionModelo
from .features import fecha


class NoActivable(Exception):
    def __init__(self, mensaje, codigo):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def fecha_corte(version):
    try:
        return fecha((version.metadatos or {}).get("fecha_corte"))
    except (TypeError, ValueError):
        return None


def motivo_no_activable(version):
    """Por qué no se puede activar la versión (None si se puede)."""
    if version.est_registro != "A":
        return "Esta versión está oculta y no se puede activar."
    if fecha_corte(version) is None:
        return ("Esta versión no tiene fecha de corte: solo se evalúa en "
                "sombra y no se puede activar.")
    return None


def recomendada():
    """La versión visible más reciente con fecha de corte (la de fecha de
    corte más tardía; a igualdad, la última registrada)."""
    candidatas = [v for v in VersionModelo.objects.filter(est_registro="A")
                  if fecha_corte(v) is not None]
    return max(candidatas, default=None,
               key=lambda v: (fecha_corte(v), v.registrado_en, v.id))


def estado():
    """Modelo activo frente al recomendado (aviso del panel del
    administrador)."""
    activo = VersionModelo.objects.filter(activo=True).first()
    referencia = recomendada()
    return {
        "activo": activo.version if activo else None,
        "recomendado": referencia.version if referencia else None,
        "aviso": referencia is not None and (
            activo is None or activo.id != referencia.id),
        # Sin fecha de corte el análisis en lote se niega a correr.
        "activo_sin_corte": activo is not None and fecha_corte(activo) is None,
    }


def registrar_activacion(version, anterior, usuario=None, origen="plataforma"):
    return ActivacionModelo.objects.create(
        version_modelo=version,
        version_anterior=anterior if anterior and anterior.id != version.id
        else None,
        usuario=usuario,
        nombre_usuario=(usuario.get_username() if usuario
                        else auditoria.usuario_actual())[:150],
        origen=origen)


def activar(version, usuario, confirmacion):
    """Activa `version` desde la pantalla Modelos (NoActivable si no se
    puede)."""
    motivo = motivo_no_activable(version)
    if motivo:
        raise NoActivable(motivo, "version_no_activable")
    if version.activo:
        raise NoActivable("Esta versión ya es la activa.", "ya_activa")
    if (confirmacion or "").strip() != version.version:
        raise NoActivable(
            f"Para confirmar, escriba el nombre de la versión "
            f"({version.version}).", "confirmacion_incorrecta")
    with transaction.atomic():
        anterior = (VersionModelo.objects.select_for_update()
                    .filter(activo=True).first())
        VersionModelo.objects.update(activo=False)
        version.activo = True
        version.save(update_fields=["activo"])
        return registrar_activacion(version, anterior, usuario)
