"""Restablecimiento de contraseña por correo.

El administrador ya no escribe contraseñas ajenas: envía un enlace al correo
del usuario (o el usuario lo pide desde «¿Olvidó su contraseña?») y es el
propio usuario quien elige la nueva en FRONTEND_URL/restablecer/<uid>/<token>.

El token es el de Django (PasswordResetTokenGenerator): caduca a los
PASSWORD_RESET_TIMEOUT segundos (1 hora) y es de un solo uso, porque depende
del hash de la contraseña y del último acceso, que cambian al usarlo. Cada
envío y cada cambio quedan en trx_restablecimiento_clave.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from riesgo.models import RestablecimientoClave

logger = logging.getLogger(__name__)
Usuario = get_user_model()

ASUNTO = "Restablecer su contraseña · Riesgo de despliegue"


def medio_correo():
    """«smtp» si EMAIL_HOST está configurado; «consola» si no (el mensaje se
    escribe en la terminal del servidor y no llega a ningún buzón)."""
    return "smtp" if settings.CORREO_CONFIGURADO else "consola"


def enlace(usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    return f"{settings.FRONTEND_URL}/restablecer/{uid}/{token}"


def _cuerpo(usuario, url):
    minutos = settings.PASSWORD_RESET_TIMEOUT // 60
    return (
        f"Hola {usuario.get_full_name() or usuario.username}:\n\n"
        "Se solicitó restablecer la contraseña de su cuenta "
        f"«{usuario.username}» en la plataforma Riesgo de despliegue.\n\n"
        "Para elegir una contraseña nueva, abra este enlace:\n\n"
        f"{url}\n\n"
        f"El enlace vale durante {minutos} minutos y solo se puede usar una "
        "vez. Si usted no lo pidió, ignore este correo: su contraseña actual "
        "no cambia.\n"
    )


def enviar_enlace(usuario, origen, solicitado_por=None):
    """Envía el enlace al correo del usuario y lo registra. Devuelve el
    registro (con `enviado` en False si el servidor de correo falló)."""
    registro = RestablecimientoClave(
        usuario=usuario, nombre_usuario=usuario.username,
        solicitado_por=solicitado_por, origen=origen, correo=usuario.email,
        medio=medio_correo())
    try:
        send_mail(ASUNTO, _cuerpo(usuario, enlace(usuario)),
                  settings.DEFAULT_FROM_EMAIL, [usuario.email])
        registro.enviado = True
    except Exception as exc:  # SMTP, red, credenciales…
        # Sin el mensaje de la excepción: algunos servidores repiten en él el
        # usuario SMTP.
        logger.error("No se pudo enviar el correo de restablecimiento a %s "
                     "(%s).", usuario.username, type(exc).__name__)
    registro.save()
    return registro


def solicitar_por_correo(correo):
    """«¿Olvidó su contraseña?»: envía el enlace a las cuentas activas con ese
    correo. No dice si existe alguna (la respuesta al usuario es siempre la
    misma)."""
    correo = (correo or "").strip()
    if not correo:
        return 0
    cuentas = Usuario.objects.filter(email__iexact=correo, is_active=True)
    for usuario in cuentas:
        enviar_enlace(usuario, "usuario")
    return len(cuentas)


def usuario_del_enlace(uid, token):
    """La cuenta del enlace si el token sigue siendo válido (no caducado ni
    usado), o None."""
    try:
        pk = force_str(urlsafe_base64_decode(uid or ""))
        usuario = Usuario.objects.get(pk=pk)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        return None
    if not usuario.is_active:
        return None
    if not default_token_generator.check_token(usuario, token or ""):
        return None
    return usuario


def registrar_cambio(usuario):
    """Marca como usado el último enlace pendiente de la cuenta."""
    pendiente = (RestablecimientoClave.objects
                 .filter(usuario=usuario, cambiada_en__isnull=True,
                         enviado=True)
                 .order_by("-solicitado_en", "-id").first())
    if pendiente is not None:
        pendiente.cambiada_en = timezone.now()
        pendiente.save(update_fields=["cambiada_en"])
    return pendiente
