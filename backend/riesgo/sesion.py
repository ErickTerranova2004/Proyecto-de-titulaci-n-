"""Inicio de sesión de la API con token (POST /api/auth/token/).

Igual que rest_framework.authtoken.views.obtain_auth_token, pero emite la
señal user_logged_in de Django, que actualiza auth_user.last_login: es el
«Último acceso» de Usuarios y accesos (el token de DRF no lo registra).
"""

from django.contrib.auth.signals import user_logged_in
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response


class IniciarSesion(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=usuario)
        user_logged_in.send(sender=usuario.__class__, request=request,
                            user=usuario)
        return Response({"token": token.key})


iniciar_sesion = IniciarSesion.as_view()
