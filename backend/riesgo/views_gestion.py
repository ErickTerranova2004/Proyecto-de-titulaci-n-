"""Gestión de usuarios, accesos y workflows desde la interfaz (solo administrador).

Reemplaza el uso del administrador de Django para estas tareas. Cada listado
devuelve todo en una sola petición para no gastar el límite de 120/hora.
"""
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from riesgo.models import (PATRON_DESPLIEGUE, ROLES, AccesoRepositorio,
                           Repositorio, Workflow)
from riesgo.permissions import EsAdministrador, rol_principal
from riesgo.services import github
from riesgo.views import _error, _error_github

Usuario = get_user_model()
MAL = status.HTTP_400_BAD_REQUEST
NO_ENCONTRADO = status.HTTP_404_NOT_FOUND


# ------------------------------------------------------------------ Usuarios
def _consulta_usuarios():
    return Usuario.objects.prefetch_related(
        "groups", "accesos__repositorio").order_by("username")


def _serializar_usuario(u, actual):
    return {
        "id": u.id,
        "usuario": u.username,
        "correo": u.email,
        "nombre": u.get_full_name(),
        "rol": rol_principal(u),
        "superusuario": u.is_superuser,
        "activo": u.is_active,
        "ultimo_acceso": u.last_login,
        "alta": u.date_joined,
        "repositorios": sorted(
            ({"id": a.repositorio_id, "nombre": a.repositorio.nombre_completo}
             for a in u.accesos.all()),
            key=lambda r: r["nombre"].lower()),
        "es_actual": u.id == actual.id,
    }


def _validar_contrasena(contrasena, usuario):
    try:
        validate_password(contrasena, usuario)
    except ValidationError as exc:
        return " ".join(exc.messages)
    return None


def _asignar_rol(usuario, rol):
    """Deja al usuario con un solo rol (o ninguno)."""
    usuario.groups.remove(*Group.objects.filter(name__in=ROLES))
    if rol:
        usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
    # El administrador puede entrar también al admin de Django.
    usuario.is_staff = rol == "administrador" or usuario.is_superuser
    usuario.save(update_fields=["is_staff"])


@api_view(["GET", "POST"])
@permission_classes([EsAdministrador])
def usuarios(request):
    if request.method == "GET":
        return Response({
            "usuarios": [_serializar_usuario(u, request.user)
                         for u in _consulta_usuarios()],
            "repositorios": list(Repositorio.objects.values(
                "id", "nombre_completo", "es_demostracion")),
        })

    datos = request.data
    nombre = str(datos.get("usuario", "")).strip()
    correo = str(datos.get("correo", "")).strip()
    contrasena = str(datos.get("contrasena", ""))
    rol = datos.get("rol") or None
    if not nombre:
        return _error("Escriba el nombre de usuario.", "usuario_vacio", MAL)
    if Usuario.objects.filter(username__iexact=nombre).exists():
        return _error("Ese nombre de usuario ya existe.", "usuario_existente",
                      MAL)
    if rol is not None and rol not in ROLES:
        return _error("Rol no válido.", "rol_no_valido", MAL)
    problema = _validar_contrasena(contrasena,
                                   Usuario(username=nombre, email=correo))
    if problema:
        return _error(problema, "contrasena_no_valida", MAL)

    with transaction.atomic():
        nuevo = Usuario.objects.create_user(username=nombre, email=correo,
                                            password=contrasena)
        _asignar_rol(nuevo, rol)
    return Response(
        _serializar_usuario(_consulta_usuarios().get(pk=nuevo.pk),
                            request.user),
        status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([EsAdministrador])
def usuario_detalle(request, pk):
    usuario = Usuario.objects.filter(pk=pk).first()
    if usuario is None:
        return _error("Usuario no encontrado.", "no_encontrado", NO_ENCONTRADO)
    datos = request.data
    es_yo = usuario.pk == request.user.pk

    # 1. Validar todo antes de cambiar nada.
    if "rol" in datos:
        rol = datos["rol"] or None
        if rol is not None and rol not in ROLES:
            return _error("Rol no válido.", "rol_no_valido", MAL)
        if usuario.is_superuser:
            return _error("El superusuario siempre es administrador.",
                          "es_superusuario", MAL)
        if es_yo and rol != "administrador":
            return _error("No puede quitarse su propio rol de administrador.",
                          "propio_rol", MAL)
    if "activo" in datos and es_yo and not datos["activo"]:
        return _error("No puede desactivar su propia cuenta.",
                      "propia_cuenta", MAL)
    contrasena = str(datos.get("contrasena") or "")
    if contrasena:
        problema = _validar_contrasena(contrasena, usuario)
        if problema:
            return _error(problema, "contrasena_no_valida", MAL)

    # 2. Aplicar los cambios.
    with transaction.atomic():
        if "rol" in datos:
            _asignar_rol(usuario, datos["rol"] or None)
        if "activo" in datos:
            usuario.is_active = bool(datos["activo"])
        if "correo" in datos:
            usuario.email = str(datos["correo"]).strip()
        if contrasena:
            usuario.set_password(contrasena)
        usuario.save()
        # Cuenta desactivada o contraseña cambiada: se cierran sus sesiones.
        if not usuario.is_active or (contrasena and not es_yo):
            Token.objects.filter(user=usuario).delete()

    return Response(_serializar_usuario(_consulta_usuarios().get(pk=pk),
                                        request.user))


@api_view(["PUT"])
@permission_classes([EsAdministrador])
def usuario_repositorios(request, pk):
    """Reemplaza la lista de repositorios asignados al usuario."""
    usuario = Usuario.objects.filter(pk=pk).first()
    if usuario is None:
        return _error("Usuario no encontrado.", "no_encontrado", NO_ENCONTRADO)
    lista = request.data.get("repositorios")
    try:
        ids = {int(i) for i in lista}
    except (TypeError, ValueError):
        return _error("Lista de repositorios no válida.", "lista_no_valida",
                      MAL)
    existentes = set(Repositorio.objects.filter(id__in=ids)
                     .values_list("id", flat=True))
    if existentes != ids:
        return _error("Alguno de los repositorios no existe.",
                      "repositorio_no_existe", MAL)

    with transaction.atomic():
        usuario.accesos.exclude(repositorio_id__in=ids).delete()
        actuales = set(usuario.accesos.values_list("repositorio_id",
                                                   flat=True))
        AccesoRepositorio.objects.bulk_create([
            AccesoRepositorio(usuario=usuario, repositorio_id=i,
                              asignado_por=request.user)
            for i in ids - actuales])
    return Response(_serializar_usuario(_consulta_usuarios().get(pk=pk),
                                        request.user))


# ----------------------------------------------------------------- Workflows
def _consulta_workflows():
    return Workflow.objects.select_related(
        "repositorio", "validado_por").annotate(
        n_ejecuciones=Count("ejecuciones", distinct=True),
        n_predicciones=Count("predicciones", distinct=True))


def _serializar_workflow(w):
    repo = w.repositorio.nombre_completo
    return {
        "id": w.id,
        "repositorio": repo,
        "demostracion": w.repositorio.es_demostracion,
        "path": w.path,
        "nombre": w.nombre or w.path.rsplit("/", 1)[-1],
        "validado": w.despliegue_validado,
        "evidencia": w.evidencia_validacion,
        "validado_por": w.validado_por.username if w.validado_por else None,
        "validado_en": w.validado_en,
        "disponible": w.disponible_github,
        "verificado_en": w.verificado_github_en,
        "patron": w.patron_paso_despliegue,
        "patron_por_defecto": w.patron_paso_despliegue == PATRON_DESPLIEGUE,
        "ejecuciones": w.n_ejecuciones,
        "predicciones": w.n_predicciones,
        "url": f"https://github.com/{repo}/blob/HEAD/{w.path}",
    }


@api_view(["GET"])
@permission_classes([EsAdministrador])
def workflows(request):
    return Response({
        "workflows": [_serializar_workflow(w) for w in _consulta_workflows()],
        "patron_por_defecto": PATRON_DESPLIEGUE,
    })


@api_view(["PATCH"])
@permission_classes([EsAdministrador])
def workflow_detalle(request, pk):
    w = Workflow.objects.filter(pk=pk).first()
    if w is None:
        return _error("Workflow no encontrado.", "no_encontrado",
                      NO_ENCONTRADO)
    datos = request.data
    validado = bool(datos.get("validado", w.despliegue_validado))
    evidencia = str(datos.get("evidencia", w.evidencia_validacion)).strip()
    patron = (str(datos.get("patron", w.patron_paso_despliegue)).strip()
              or PATRON_DESPLIEGUE)

    if validado and not evidencia:
        return _error("Un workflow validado debe documentar la evidencia.",
                      "sin_evidencia", MAL)
    if len(patron) > 500:
        return _error("El patrón no puede superar 500 caracteres.",
                      "patron_largo", MAL)
    try:
        re.compile(patron)
    except re.error as exc:
        return _error(f"El patrón no es una expresión regular válida: {exc}",
                      "patron_no_valido", MAL)

    if validado and not w.despliegue_validado:
        w.validado_por, w.validado_en = request.user, timezone.now()
    elif not validado:
        w.validado_por, w.validado_en = None, None
    w.despliegue_validado = validado
    w.evidencia_validacion = evidencia
    w.patron_paso_despliegue = patron
    w.clean()
    w.save()
    return Response(_serializar_workflow(_consulta_workflows().get(pk=pk)))


@api_view(["POST"])
@permission_classes([EsAdministrador])
def workflows_validar(request):
    """Valida o quita la validación de varios workflows a la vez."""
    ids = request.data.get("ids")
    validado = bool(request.data.get("validado", True))
    evidencia = str(request.data.get("evidencia", "")).strip()
    if not isinstance(ids, list) or not ids:
        return _error("No se seleccionaron workflows.", "sin_seleccion", MAL)
    if validado and not evidencia:
        return _error("Documente la evidencia de la validación.",
                      "sin_evidencia", MAL)

    consulta = Workflow.objects.filter(id__in=ids)
    if validado:
        n = consulta.filter(despliegue_validado=False).update(
            despliegue_validado=True, evidencia_validacion=evidencia,
            validado_por=request.user, validado_en=timezone.now())
    else:
        n = consulta.filter(despliegue_validado=True).update(
            despliegue_validado=False, validado_por=None, validado_en=None)
    return Response({"actualizados": n})


@api_view(["POST"])
@permission_classes([EsAdministrador])
def workflow_comprobar(request, pk):
    """Comprueba en GitHub si el archivo del workflow sigue existiendo."""
    w = Workflow.objects.select_related("repositorio").filter(pk=pk).first()
    if w is None:
        return _error("Workflow no encontrado.", "no_encontrado",
                      NO_ENCONTRADO)
    try:
        github.GitHubClient().workflow(w.repositorio.nombre_completo, w.path)
        disponible = True
    except github.NoEncontrado:
        disponible = False
    except github.GitHubError as exc:
        return _error_github(exc)
    w.disponible_github = disponible
    w.verificado_github_en = timezone.now()
    w.save(update_fields=["disponible_github", "verificado_github_en"])
    return Response(_serializar_workflow(_consulta_workflows().get(pk=pk)))