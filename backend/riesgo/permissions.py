"""Roles (grupos de Django) y visibilidad por repositorio asignado.

- Administrador: ve todo.
- Líder técnico: todas las predicciones de sus repositorios asignados.
- Desarrollador: sus propias predicciones en sus repositorios asignados.
"""

from rest_framework.permissions import BasePermission

from riesgo.models import AccesoRepositorio, Prediccion, Repositorio


def roles(usuario):
    if usuario.is_superuser:
        return {"administrador"}
    return set(usuario.groups.values_list("name", flat=True))


# De mayor a menor jerarquía (igual que el menú de la interfaz).
JERARQUIA = ("administrador", "lider_tecnico", "desarrollador")


def rol_principal(usuario):
    """Rol de mayor jerarquía del usuario, o None si no tiene ninguno."""
    suyos = roles(usuario)
    return next((rol for rol in JERARQUIA if rol in suyos), None)


def es_admin(usuario):
    return "administrador" in roles(usuario)


def es_lider(usuario):
    return "lider_tecnico" in roles(usuario)


def tiene_acceso(usuario, repositorio):
    return es_admin(usuario) or AccesoRepositorio.objects.filter(
        usuario=usuario, repositorio=repositorio).exists()


def repositorios_visibles(usuario):
    consulta = Repositorio.objects.all()
    if es_admin(usuario):
        return consulta
    return consulta.filter(accesos__usuario=usuario)


def predicciones_visibles(usuario):
    consulta = Prediccion.objects.select_related(
        "usuario", "version_modelo", "workflow__repositorio", "commit",
        "ejecucion_real")
    if es_admin(usuario):
        return consulta
    consulta = consulta.filter(workflow__repositorio__accesos__usuario=usuario)
    if not es_lider(usuario):
        consulta = consulta.filter(usuario=usuario)
    return consulta


class PuedePredecir(BasePermission):
    message = "Se requiere un rol de la plataforma."

    def has_permission(self, request, view):
        return bool(roles(request.user))


class EsLiderOAdministrador(BasePermission):
    message = "Solo el líder técnico o el administrador registran decisiones."

    def has_permission(self, request, view):
        return es_lider(request.user) or es_admin(request.user)


class EsAdministrador(BasePermission):
    message = "Solo el administrador puede realizar esta acción."

    def has_permission(self, request, view):
        return es_admin(request.user)
