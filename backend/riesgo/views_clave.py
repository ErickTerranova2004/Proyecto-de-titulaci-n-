"""Restablecimiento de contraseña sin sesión (pantallas públicas).

- POST /api/auth/restablecer/solicitar/ {correo}: «¿Olvidó su contraseña?».
  Responde siempre lo mismo, exista o no una cuenta con ese correo.
- POST /api/auth/restablecer/validar/ {uid, token}: si el enlace sigue
  valiendo (la pantalla lo comprueba antes de pedir la contraseña).
- POST /api/auth/restablecer/confirmar/ {uid, token, contrasena,
  confirmacion}: guarda la nueva contraseña con las reglas de
  AUTH_PASSWORD_VALIDATORS y cierra las sesiones abiertas de la cuenta.

Sin autenticación (un token caducado en el navegador no debe impedir usar
el enlace) y con un límite propio por IP (DEFAULT_THROTTLE_RATES
«restablecer»). El token va en el cuerpo, nunca en la URL de la API, para que
no quede en los registros del servidor.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import (api_view, authentication_classes,
                                       permission_classes, throttle_classes)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from riesgo.auditoria import como
from riesgo.services import restablecimiento
from riesgo.views import _error

MAL = status.HTTP_400_BAD_REQUEST
MENSAJE_SOLICITUD = (
    "Si el correo corresponde a una cuenta activa, recibirá un enlace para "
    "restablecer la contraseña. El enlace vale durante una hora.")
ENLACE_NO_VALIDO = (
    "El enlace no es válido o ya caducó (vale una hora y solo se puede usar "
    "una vez). Pida uno nuevo desde «¿Olvidó su contraseña?» o al "
    "administrador.")


class LimiteRestablecer(AnonRateThrottle):
    scope = "restablecer"


def _publica(vista):
    for decorador in (throttle_classes([LimiteRestablecer]),
                      permission_classes([AllowAny]),
                      authentication_classes([]),
                      api_view(["POST"])):
        vista = decorador(vista)
    return vista


@_publica
def solicitar(request):
    restablecimiento.solicitar_por_correo(str(request.data.get("correo", "")))
    # Mismo mensaje exista o no la cuenta. Que el correo no esté configurado
    # es un dato del servidor, no de las cuentas: se puede avisar.
    return Response({
        "mensaje": MENSAJE_SOLICITUD,
        "correo_configurado": restablecimiento.medio_correo() == "smtp",
    })


@_publica
def validar(request):
    usuario = restablecimiento.usuario_del_enlace(
        str(request.data.get("uid", "")), str(request.data.get("token", "")))
    if usuario is None:
        return _error(ENLACE_NO_VALIDO, "enlace_no_valido", MAL)
    return Response({"valido": True, "usuario": usuario.username})


@_publica
def confirmar(request):
    datos = request.data
    usuario = restablecimiento.usuario_del_enlace(
        str(datos.get("uid", "")), str(datos.get("token", "")))
    if usuario is None:
        return _error(ENLACE_NO_VALIDO, "enlace_no_valido", MAL)
    contrasena = str(datos.get("contrasena") or "")
    if not contrasena:
        return _error("Escriba la nueva contraseña.", "contrasena_vacia", MAL)
    if contrasena != str(datos.get("confirmacion") or ""):
        return _error("Las dos contraseñas no coinciden.", "no_coinciden",
                      MAL)
    try:
        validate_password(contrasena, usuario)
    except ValidationError as exc:
        return _error(" ".join(exc.messages), "contrasena_no_valida", MAL)

    with como(usuario), transaction.atomic():
        usuario.set_password(contrasena)  # invalida el enlace (un solo uso)
        usuario.save(update_fields=["password"])
        # Las sesiones abiertas con la contraseña anterior se cierran.
        Token.objects.filter(user=usuario).delete()
        restablecimiento.registrar_cambio(usuario)
    return Response({"usuario": usuario.username,
                     "mensaje": "Contraseña actualizada. Ya puede iniciar "
                                "sesión con la nueva contraseña."})
