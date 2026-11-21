"""Gestión de usuarios, accesos y workflows desde la interfaz (solo administrador).

Reemplaza el uso del administrador de Django para estas tareas. Cada listado
devuelve todo en una sola petición para no gastar el límite de peticiones por hora.

El administrador no escribe ni cambia contraseñas ajenas: envía al correo del
usuario un enlace para que la elija él (services/restablecimiento.py). Al
crear una cuenta se envía ese mismo enlace; hasta usarlo, la cuenta no tiene
contraseña utilizable.
"""
import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError as ErrorValidacion
from rest_framework.response import Response

from riesgo import paginacion

from riesgo.models import (PATRON_DESPLIEGUE, ROLES, AccesoRepositorio,
                           DecisionDespliegue, Prediccion, Repositorio,
                           InformeCumplimiento, RestablecimientoClave,
                           Workflow)
from riesgo.permissions import EsAdministrador, rol_principal
from riesgo.services import github, restablecimiento
from riesgo.views import _error, _error_github

Usuario = get_user_model()
MAL = status.HTTP_400_BAD_REQUEST
NO_ENCONTRADO = status.HTTP_404_NOT_FOUND


# ------------------------------------------------------------------ Usuarios
def _consulta_usuarios():
    return Usuario.objects.prefetch_related(
        "groups", "accesos__repositorio").annotate(
        n_analisis=Count("predicciones", distinct=True,
                         filter=~Q(predicciones__origen="sombra")),
        n_decisiones=Count("decisiones", distinct=True)).order_by("username")


def _serializar_restablecimiento(r):
    if r is None:
        return None
    return {
        "solicitado_en": r.solicitado_en,
        "origen": r.origen,
        "solicitado_por": r.usu_creacion,
        "correo": r.correo,
        "enviado": r.enviado,
        "medio": r.medio,
        "cambiada_en": r.cambiada_en,
    }


def _ultimos_restablecimientos(ids=None):
    """Último enlace de restablecimiento de cada cuenta, {id_usuario: fila}."""
    consulta = RestablecimientoClave.objects.filter(usuario__isnull=False)
    if ids is not None:
        consulta = consulta.filter(usuario_id__in=ids)
    ultimos = {}
    for r in consulta.order_by("-solicitado_en", "-id"):
        ultimos.setdefault(r.usuario_id, r)
    return ultimos


def _estado_correo():
    medio = restablecimiento.medio_correo()
    return {"configurado": medio == "smtp", "medio": medio}


def _serializar_usuario(u, actual, ultimos=None):
    if ultimos is None:
        ultimos = _ultimos_restablecimientos([u.id])
    return {
        "id": u.id,
        "usuario": u.username,
        "correo": u.email,
        "nombre": u.get_full_name(),
        "rol": rol_principal(u),
        "superusuario": u.is_superuser,
        "activo": u.is_active,
        # False: cuenta nueva que aún no eligió su contraseña con el enlace.
        "clave_definida": u.has_usable_password(),
        "ultimo_restablecimiento": _serializar_restablecimiento(
            ultimos.get(u.id)),
        "ultimo_acceso": u.last_login,
        "alta": u.date_joined,
        "repositorios": sorted(
            ({"id": a.repositorio_id, "nombre": a.repositorio.nombre_completo}
             for a in u.accesos.all() if a.est_registro == "A"),
            key=lambda r: r["nombre"].lower()),
        "es_actual": u.id == actual.id,
        # Con historial solo se elimina traspasándolo a otra cuenta.
        "analisis": u.n_analisis,
        "decisiones": u.n_decisiones,
    }


def _correo_valido(correo):
    try:
        validate_email(correo)
    except ValidationError:
        return False
    return True


def _resultado_envio(registro):
    """Respuesta del envío del enlace (para el aviso de la interfaz)."""
    return {"enviado": registro.enviado, "medio": registro.medio,
            "correo": registro.correo}


def _asignar_rol(usuario, rol):
    """Deja al usuario con un solo rol (o ninguno)."""
    usuario.groups.remove(*Group.objects.filter(name__in=ROLES))
    if rol:
        usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
    # El administrador puede entrar también al admin de Django.
    usuario.is_staff = rol == "administrador" or usuario.is_superuser
    usuario.save(update_fields=["is_staff"])


FILTROS_USUARIOS = ("todos", "administrador", "lider_tecnico", "desarrollador",
                    "sin_rol", "sin_correo", "inactivos")


def filtrar_usuarios(usuarios, filtro="todos", texto=""):
    """Filtro por rol o estado y búsqueda por usuario, nombre o correo, sobre
    los usuarios ya serializados (mismas reglas que la interfaz)."""
    if filtro not in FILTROS_USUARIOS:
        raise ErrorValidacion({"filtro": "Filtro no válido."})
    texto = (texto or "").strip().lower()

    def cumple(u):
        if filtro == "sin_rol" and u["rol"]:
            return False
        if filtro == "sin_correo" and u["correo"]:
            return False
        if filtro == "inactivos" and u["activo"]:
            return False
        if filtro in ROLES and u["rol"] != filtro:
            return False
        return not texto or any(texto in (u[c] or "").lower()
                                for c in ("usuario", "nombre", "correo"))
    return [u for u in usuarios if cumple(u)]


@api_view(["GET", "POST"])
@permission_classes([EsAdministrador])
def usuarios(request):
    if request.method == "GET":
        ultimos = _ultimos_restablecimientos()
        todos = [_serializar_usuario(u, request.user, ultimos)
                 for u in _consulta_usuarios()]
        respuesta = {
            # Todas las cuentas: indicadores, avisos y diálogos.
            "usuarios": todos,
            "correo": _estado_correo(),
            "repositorios": list(Repositorio.objects.values(
                "id", "nombre_completo", "es_demostracion", "es_prueba",
                "est_registro")),
        }
        parametros = request.query_params
        if paginacion.pedida(parametros):
            # Tabla: filtrada, ordenada por usuario y paginada.
            respuesta["tabla"] = paginacion.paginar(
                filtrar_usuarios(todos, parametros.get("filtro") or "todos",
                                 parametros.get("q")),
                parametros, lambda filas: filas)
        return Response(respuesta)

    datos = request.data
    nombre = str(datos.get("usuario", "")).strip()
    correo = str(datos.get("correo", "")).strip()
    rol = datos.get("rol") or None
    if not nombre:
        return _error("Escriba el nombre de usuario.", "usuario_vacio", MAL)
    if Usuario.objects.filter(username__iexact=nombre).exists():
        return _error("Ese nombre de usuario ya existe.", "usuario_existente",
                      MAL)
    if rol is not None and rol not in ROLES:
        return _error("Rol no válido.", "rol_no_valido", MAL)
    if "contrasena" in datos:
        return _error("El administrador no asigna contraseñas: el usuario "
                      "la elige con el enlace que recibe por correo.",
                      "contrasena_no_permitida", MAL)
    # El usuario elige su contraseña con el enlace: sin correo no hay enlace.
    if not correo:
        return _error("Escriba el correo electrónico: el usuario recibirá en "
                      "él el enlace para crear su contraseña.",
                      "correo_vacio", MAL)
    if not _correo_valido(correo):
        return _error("El correo electrónico no es válido.", "correo_no_valido",
                      MAL)

    with transaction.atomic():
        # Sin contraseña utilizable hasta que use el enlace.
        nuevo = Usuario.objects.create_user(username=nombre, email=correo,
                                            password=None)
        _asignar_rol(nuevo, rol)
    registro = restablecimiento.enviar_enlace(nuevo, "administrador",
                                              request.user)
    return Response(
        {**_serializar_usuario(_consulta_usuarios().get(pk=nuevo.pk),
                               request.user),
         "envio": _resultado_envio(registro)},
        status=status.HTTP_201_CREATED)


def destino_traspaso_valido(usuario, destino):
    """Motivo por el que `destino` no puede recibir el historial, o None.

    Debe ser otra cuenta activa con el mismo rol o administradora (así las
    decisiones siguen siendo de un líder o de un administrador)."""
    if destino.pk == usuario.pk:
        return "No puede traspasar el historial a la misma cuenta."
    if not destino.is_active:
        return f"{destino.username} está desactivado."
    rol, rol_destino = rol_principal(usuario), rol_principal(destino)
    if rol_destino != "administrador" and rol_destino != rol:
        return (f"{destino.username} no tiene el mismo rol que "
                f"{usuario.username} ni es administrador.")
    return None


def traspasar_historial(usuario, destino):
    """Análisis, decisiones, validaciones, asignaciones y accesos de
    `usuario` pasan a `destino` (los registros de auditoría conservan quién
    los creó)."""
    resumen = {
        # Con las de la evaluación en sombra (si la cuenta es la del lote).
        "analisis": Prediccion.con_sombra.filter(usuario=usuario).update(
            usuario=destino),
        "decisiones": DecisionDespliegue.objects.filter(
            usuario=usuario).update(usuario=destino),
        "workflows_validados": Workflow.objects.filter(
            validado_por=usuario).update(validado_por=destino),
        "accesos_asignados": AccesoRepositorio.objects.filter(
            asignado_por=usuario).update(asignado_por=destino),
        # Informes de cumplimiento enviados y recibidos (PROTECT).
        "informes": InformeCumplimiento.objects.filter(
            desarrollador=usuario).update(desarrollador=destino)
        + InformeCumplimiento.objects.filter(lider=usuario).update(lider=destino),
        "repositorios": 0,
    }
    # El administrador ve todos los repositorios: no necesita accesos.
    if rol_principal(destino) != "administrador":
        actuales = set(destino.accesos.values_list("repositorio_id", flat=True))
        # Solo los accesos activos: los desactivados no se vuelven a dar.
        nuevos = [AccesoRepositorio(usuario=destino, repositorio_id=r,
                                    asignado_por=destino)
                  for r in usuario.accesos.filter(est_registro="A")
                  .values_list("repositorio_id", flat=True)
                  if r not in actuales]
        AccesoRepositorio.objects.bulk_create(nuevos)
        resumen["repositorios"] = len(nuevos)
    return resumen


def _eliminar_usuario(usuario, es_yo, destino_id=None):
    """Elimina una cuenta. Si tiene historial (análisis o decisiones), antes
    lo traspasa a `destino_id`; sin destino, responde 409."""
    if es_yo:
        return _error("No puede eliminar su propia cuenta.", "propia_cuenta",
                      MAL)
    if usuario.is_superuser:
        return _error("El superusuario no se puede eliminar.",
                      "es_superusuario", MAL)
    analisis = Prediccion.con_sombra.filter(usuario=usuario).count()
    decisiones = usuario.decisiones.count()
    destino = None
    destino_id = (destino_id or "").strip()
    if destino_id and not destino_id.isdigit():
        return _error("transferir_a debe ser el id numérico de la cuenta que "
                      "recibe el historial.", "destino_no_valido", MAL)
    if destino_id:
        destino = Usuario.objects.filter(pk=int(destino_id)).first()
        if destino is None:
            return _error("La cuenta que recibiría el historial no existe.",
                          "destino_no_encontrado", MAL)
        problema = destino_traspaso_valido(usuario, destino)
        if problema:
            return _error(problema, "destino_no_valido", MAL)
    elif analisis or decisiones:
        return _error(
            f"{usuario.username} tiene {analisis} análisis y {decisiones} "
            "decisiones registradas. Para conservar la trazabilidad, elija "
            "a qué cuenta se traspasan antes de eliminarla.", "con_historial",
            status.HTTP_409_CONFLICT)
    with transaction.atomic():
        resumen = traspasar_historial(usuario, destino) if destino else None
        # Accesos y token se borran en cascada; quien validó workflows o
        # asignó accesos sin traspaso queda como "sin usuario" (SET_NULL).
        usuario.delete()
    if resumen is None:
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response({"eliminado": usuario.username,
                     "traspasado_a": destino.username, **resumen})


@api_view(["PATCH", "DELETE"])
@permission_classes([EsAdministrador])
def usuario_detalle(request, pk):
    usuario = Usuario.objects.filter(pk=pk).first()
    if usuario is None:
        return _error("Usuario no encontrado.", "no_encontrado", NO_ENCONTRADO)
    datos = request.data
    es_yo = usuario.pk == request.user.pk
    if request.method == "DELETE":
        return _eliminar_usuario(usuario, es_yo,
                                 request.query_params.get("transferir_a"))

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
    if "contrasena" in datos:
        return _error("El administrador no cambia contraseñas: envíe al "
                      "usuario el enlace para restablecerla.",
                      "contrasena_no_permitida", MAL)
    if "correo" in datos:
        correo = str(datos["correo"] or "").strip()
        if correo and not _correo_valido(correo):
            return _error("El correo electrónico no es válido.",
                          "correo_no_valido", MAL)

    # 2. Aplicar los cambios.
    with transaction.atomic():
        if "rol" in datos:
            _asignar_rol(usuario, datos["rol"] or None)
        if "activo" in datos:
            usuario.is_active = bool(datos["activo"])
        if "correo" in datos:
            usuario.email = str(datos["correo"] or "").strip()
        usuario.save()
        # Cuenta desactivada: se cierran sus sesiones.
        if not usuario.is_active:
            Token.objects.filter(user=usuario).delete()

    return Response(_serializar_usuario(_consulta_usuarios().get(pk=pk),
                                        request.user))


@api_view(["POST"])
@permission_classes([EsAdministrador])
def usuario_restablecer(request, pk):
    """Envía al correo del usuario el enlace para restablecer su contraseña
    (vale una hora y un solo uso). Queda registrado quién lo pidió."""
    usuario = Usuario.objects.filter(pk=pk).first()
    if usuario is None:
        return _error("Usuario no encontrado.", "no_encontrado", NO_ENCONTRADO)
    if not usuario.email:
        return _error(f"{usuario.username} no tiene correo registrado. "
                      "Regístrelo y guarde los cambios antes de enviar el "
                      "enlace.", "sin_correo", MAL)
    if not usuario.is_active:
        return _error(f"La cuenta {usuario.username} está desactivada: "
                      "actívela antes de enviar el enlace.", "inactivo", MAL)
    registro = restablecimiento.enviar_enlace(usuario, "administrador",
                                              request.user)
    if not registro.enviado:
        return _error("No se pudo enviar el correo. Revise la configuración "
                      "de EMAIL_* en backend/.env y el registro del servidor.",
                      "envio_fallido", status.HTTP_502_BAD_GATEWAY)
    return Response({
        **_resultado_envio(registro),
        "usuario": _serializar_usuario(_consulta_usuarios().get(pk=pk),
                                       request.user),
    })


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
        # Solo se quitan los accesos activos: los desactivados (casos de
        # prueba) no se muestran en la interfaz y se conservan por auditoría.
        usuario.accesos.filter(est_registro="A").exclude(
            repositorio_id__in=ids).delete()
        actuales = set(usuario.accesos.filter(est_registro="A").values_list(
            "repositorio_id", flat=True))
        # Volver a asignar un repositorio con el acceso desactivado lo
        # reactiva (hay una fila por usuario y repositorio).
        usuario.accesos.filter(est_registro="I", repositorio_id__in=ids).update(
            est_registro="A", asignado_por=request.user)
        inactivos = set(usuario.accesos.values_list("repositorio_id", flat=True))
        AccesoRepositorio.objects.bulk_create([
            AccesoRepositorio(usuario=usuario, repositorio_id=i,
                              asignado_por=request.user)
            for i in ids - actuales - inactivos])
    return Response(_serializar_usuario(_consulta_usuarios().get(pk=pk),
                                        request.user))


# ----------------------------------------------------------------- Workflows
def _consulta_workflows():
    return Workflow.objects.select_related(
        "repositorio", "validado_por").annotate(
        n_ejecuciones=Count("ejecuciones", distinct=True),
        n_predicciones=Count("predicciones", distinct=True,
                             filter=~Q(predicciones__origen="sombra")))


def _serializar_workflow(w):
    repo = w.repositorio.nombre_completo
    return {
        "id": w.id,
        "repositorio": repo,
        "demostracion": w.repositorio.es_demostracion,
        "prueba": w.repositorio.es_prueba,
        "repositorio_activo": w.repositorio.est_registro == "A",
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