import logging
import math

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from riesgo.models import (EjecucionWorkflow, Prediccion, Repositorio,
                           VersionModelo, Workflow)
from riesgo.permissions import (EsAdministrador, EsLiderOAdministrador,
                                PuedePredecir, predicciones_visibles,
                                repositorios_visibles, rol_principal, roles,
                                tiene_acceso)
from riesgo.serializers import (AsignacionSerializer, PrediccionSerializer,
                                RepositorioSerializer,
                                SolicitudDecisionSerializer,
                                SolicitudFechaLimiteSerializer,
                                SolicitudPrediccionSerializer,
                                SolicitudRegistroSerializer,
                                VersionModeloSerializer)
from riesgo.services import asignaciones, github
from riesgo.services.sincronizacion import sincronizar_repositorio
from riesgo.services.etiquetado import etiquetar_ejecucion
from riesgo.services.features import calcular_variables, fecha
from riesgo.services.predictor import SinModeloActivo, predecir
from riesgo.services.recomendaciones import recomendar
from riesgo.services.trazabilidad import (RepositorioNoRegistrado,
                                          guardar_commit, guardar_ejecucion,
                                          resolver_repositorio)

logger = logging.getLogger(__name__)


def _json_seguro(variables):
    """Convierte NaN en None para guardar JSON válido."""
    return {k: (None if isinstance(v, float) and math.isnan(v) else v)
            for k, v in variables.items()}


def _error(mensaje, codigo, estado):
    return Response({"detail": mensaje, "codigo": codigo}, status=estado)


def _error_github(exc):
    if isinstance(exc, github.RamaNoEncontrada):
        return _error(f"La rama {exc.rama} no existe en el repositorio. Su "
                      f"rama principal es {exc.principal}.",
                      "rama_no_encontrada", status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, github.NoEncontrado):
        if "/actions/workflows/" in str(exc):
            return _error("El archivo del workflow ya no existe en GitHub "
                          "(fue renombrado o eliminado después de los "
                          "datos de GHALogs). Elija otro workflow.",
                          "github_no_encontrado", status.HTTP_404_NOT_FOUND)
        return _error("Repositorio, workflow o commit no encontrado en "
                      "GitHub, o sin permisos de lectura.",
                      "github_no_encontrado", status.HTTP_404_NOT_FOUND)
    if isinstance(exc, github.LimiteExcedido):
        return Response({"detail": "Límite de la API de GitHub agotado. "
                                   "Intente más tarde o configure "
                                   "GITHUB_TOKEN en backend/.env.",
                         "codigo": "github_limite", "reinicio": exc.reinicio},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return _error("Error al consultar GitHub.", "github_error",
                  status.HTTP_502_BAD_GATEWAY)


@api_view(["GET"])
def yo(request):
    return Response({"usuario": request.user.username,
                     "roles": sorted(roles(request.user))})


class RepositorioViewSet(mixins.ListModelMixin, GenericViewSet):
    """Repositorios visibles con sus workflows de despliegue validados."""

    serializer_class = RepositorioSerializer
    permission_classes = [PuedePredecir]

    def get_queryset(self):
        visibles = repositorios_visibles(self.request.user)
        # ?todos=1: todos los repositorios visibles (asignados), aunque no
        # tengan workflows utilizables. Lo usan los paneles por rol.
        if self.request.query_params.get("todos") == "1":
            return visibles.prefetch_related("workflows")
        # Por defecto, solo los que tienen algún workflow utilizable (selector
        # de Nuevo análisis e Integraciones).
        return visibles.filter(
            workflows__despliegue_validado=True,
            workflows__disponible_github=True).distinct().prefetch_related(
            "workflows")

    @action(detail=True, methods=["post"],
            permission_classes=[EsAdministrador])
    def sincronizar(self, request, pk=None):
        """Recopila desde GitHub las ejecuciones de sus workflows validados."""
        repositorio = self.get_object()
        try:
            resultado = sincronizar_repositorio(repositorio,
                                                github.GitHubClient())
        except github.GitHubError as exc:
            return _error_github(exc)
        logger.info("Sincronización de %s por %s: %s ejecuciones",
                    repositorio, request.user.username,
                    resultado["ejecuciones_guardadas"])
        return Response(resultado)

    @action(detail=False, methods=["post"],
            permission_classes=[EsAdministrador])
    def registrar(self, request):
        """Registra y valida un workflow de despliegue fuera del dataset.

        Comprueba en GitHub que el repositorio y el archivo del workflow
        existen y guarda la evidencia documentada por el administrador.
        """
        solicitud = SolicitudRegistroSerializer(data=request.data)
        solicitud.is_valid(raise_exception=True)
        datos = solicitud.validated_data
        cliente = github.GitHubClient()
        try:
            info_repo = cliente.repositorio(datos["repositorio"])
        except github.NoEncontrado:
            return _error("El repositorio no existe en GitHub o es privado "
                          "y el token no tiene permiso de lectura.",
                          "github_no_encontrado", status.HTTP_404_NOT_FOUND)
        except github.GitHubError as exc:
            return _error_github(exc)
        nombre = info_repo["full_name"]
        try:
            info_wf = cliente.workflow(nombre, datos["workflow_path"])
            recientes = cliente.ejecuciones_workflow(
                nombre, datos["workflow_path"])
        except github.NoEncontrado:
            return _error(f"El workflow {datos['workflow_path']} no existe "
                          f"en {nombre}.", "github_no_encontrado",
                          status.HTTP_404_NOT_FOUND)
        except github.GitHubError as exc:
            return _error_github(exc)

        with transaction.atomic():
            repositorio = (
                Repositorio.objects.filter(github_id=info_repo["id"]).first()
                or Repositorio.objects.filter(
                    nombre_completo__iexact=nombre).first()
                or Repositorio(github_id=info_repo["id"]))
            repositorio.github_id = info_repo["id"]
            repositorio.nombre_completo = nombre
            repositorio.propietario, _, repositorio.nombre = \
                nombre.partition("/")
            repositorio.save()
            workflow, creado = Workflow.objects.get_or_create(
                repositorio=repositorio, path=datos["workflow_path"])
            if (not creado and workflow.despliegue_validado
                    and workflow.disponible_github):
                return _error("Este workflow ya está registrado y validado.",
                              "ya_registrado", status.HTTP_409_CONFLICT)
            workflow.nombre = info_wf.get("name", "")[:200]
            workflow.despliegue_validado = True
            workflow.evidencia_validacion = datos["evidencia"]
            workflow.validado_por = request.user
            workflow.validado_en = timezone.now()
            workflow.disponible_github = True
            workflow.verificado_github_en = timezone.now()
            workflow.save()

        logger.info("Workflow %s registrado por %s", workflow,
                    request.user.username)
        return Response({
            "repositorio": nombre,
            "workflow_path": workflow.path,
            "ejecuciones_recientes": len(recientes),
        }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([EsAdministrador])
def integraciones(request):
    """Estado de la integración con GitHub (sin revelar el token)."""
    try:
        limite = github.GitHubClient().limite()
        error = ""
    except Exception:  # noqa: BLE001 - se informa sin detalles internos
        limite, error = {}, "No se pudo consultar el estado de la API de GitHub."
    ultima = EjecucionWorkflow.objects.aggregate(Max("extraida_en"))[
        "extraida_en__max"]
    return Response({"github": {
        "api_url": settings.GITHUB_API_URL,
        "token_configurado": bool(settings.GITHUB_TOKEN),
        "limite": limite.get("limit"),
        "restantes": limite.get("remaining"),
        "reinicio": limite.get("reset"),
        "error": error,
        "repositorios_registrados": Repositorio.objects.count(),
        "workflows_validados": Workflow.objects.filter(
            despliegue_validado=True).count(),
        "ejecuciones_almacenadas": EjecucionWorkflow.objects.count(),
        "ultima_extraccion": ultima,
    }})


class PrediccionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        GenericViewSet):
    serializer_class = PrediccionSerializer
    permission_classes = [PuedePredecir]

    def get_queryset(self):
        consulta = predicciones_visibles(self.request.user).prefetch_related(
            "ejecuciones_previas", "decisiones__usuario")
        repositorio = self.request.query_params.get("repositorio")
        if repositorio:
            consulta = consulta.filter(
                workflow__repositorio__nombre_completo=repositorio)
        return consulta

    def create(self, request):
        solicitud = SolicitudPrediccionSerializer(data=request.data)
        solicitud.is_valid(raise_exception=True)
        datos = solicitud.validated_data
        cliente = github.GitHubClient()

        try:
            repositorio = resolver_repositorio(datos["repositorio"], cliente)
        except RepositorioNoRegistrado:
            return _error("El repositorio no está registrado en la "
                          "plataforma.", "repositorio_no_registrado",
                          status.HTTP_404_NOT_FOUND)
        except github.GitHubError as exc:
            return _error_github(exc)
        if not tiene_acceso(request.user, repositorio):
            return _error("No tiene acceso asignado a este repositorio.",
                          "sin_acceso", status.HTTP_403_FORBIDDEN)
        workflow = Workflow.objects.filter(
            repositorio=repositorio, path=datos["workflow_path"]).first()
        if workflow is not None and not workflow.disponible_github:
            return _error(
                f"El workflow {workflow.path} ya no existe en GitHub (fue "
                "renombrado o eliminado). Elija otro workflow.",
                "workflow_no_disponible", status.HTTP_400_BAD_REQUEST)
        if workflow is None or not workflow.despliegue_validado:
            return _error(
                f"El workflow {datos['workflow_path']} no está validado como "
                "workflow de despliegue a una aplicación. Un administrador "
                "debe validarlo y documentar la evidencia antes de usarlo.",
                "workflow_no_validado", status.HTTP_400_BAD_REQUEST)
        atendida = None
        if datos["atiende_decision"] is not None:
            try:
                atendida = asignaciones.validar_respuesta(
                    datos["atiende_decision"], request.user,
                    repositorio.nombre_completo, workflow.path)
            except asignaciones.RespuestaNoValida as exc:
                return _error(str(exc), exc.codigo,
                              status.HTTP_400_BAD_REQUEST)

        nombre = repositorio.nombre_completo
        try:
            sha = datos["head_sha"]
            if not sha:
                sha = cliente.ultimo_commit(nombre, datos["rama"])["sha"]
            variables, extraido, contexto = calcular_variables(
                cliente, nombre, workflow.path, sha, datos["rama"],
                datos["evento"])
            resultado = predecir(variables)
        except github.GitHubError as exc:
            if (isinstance(exc, github.NoEncontrado)
                    and "/actions/workflows/" in str(exc)):
                # El archivo ya no existe: se retira de los nuevos análisis.
                workflow.disponible_github = False
                workflow.verificado_github_en = timezone.now()
                workflow.save(update_fields=["disponible_github",
                                             "verificado_github_en"])
            return _error_github(exc)
        except SinModeloActivo:
            return _error("No hay un modelo activo.", "sin_modelo",
                          status.HTTP_503_SERVICE_UNAVAILABLE)

        with transaction.atomic():
            commit = guardar_commit(repositorio, contexto["commit"].get("sha")
                                    or sha, contexto["commit"])
            previas = [guardar_ejecucion(workflow, run, extraido)
                       for run in contexto["previas"]]
            prediccion = workflow.predicciones.create(
                usuario=request.user,
                commit=commit,
                rama=datos["rama"],
                evento=datos["evento"],
                variables=_json_seguro(variables),
                probabilidad=resultado["probabilidad"],
                nivel=resultado["nivel"],
                factores=resultado["factores"],
                recomendaciones=recomendar(variables, resultado["factores"]),
                version_modelo=resultado["version"],
                datos_github_extraidos_en=extraido,
            )
            prediccion.ejecuciones_previas.set(previas)
            if atendida is not None:
                asignaciones.registrar_respuesta(
                    atendida, prediccion, datos["respuesta_desarrollador"])
        logger.info("Predicción %s creada por %s para %s", prediccion.id,
                    request.user.username, nombre)
        return Response(PrediccionSerializer(prediccion).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def verificar(self, request, pk=None):
        """Enlaza la ejecución real posterior del mismo workflow y commit."""
        prediccion = self.get_object()
        if prediccion.ejecucion_real_id:
            return Response(PrediccionSerializer(prediccion).data)
        workflow = prediccion.workflow
        repo = workflow.repositorio.nombre_completo
        sha = prediccion.commit.sha
        cliente = github.GitHubClient()
        try:
            runs = cliente.ejecuciones_workflow(repo, workflow.path,
                                                head_sha=sha)
            candidatas = sorted(
                (r for r in runs
                 if r.get("head_sha") == sha
                 and r.get("status") == "completed"
                 and (r.get("path") or workflow.path).split("@")[0]
                 == workflow.path
                 and fecha(r.get("run_started_at"))
                 and fecha(r["run_started_at"]) > prediccion.creada_en),
                key=lambda r: r["run_started_at"])
            if not candidatas:
                return Response({"estado": "pendiente",
                                 "detail": "Todavía no hay una ejecución "
                                           "completada del mismo workflow "
                                           "y commit posterior a la "
                                           "predicción."})
            run = candidatas[0]
            jobs = cliente.jobs_intento(repo, run["id"],
                                        run.get("run_attempt") or 1)
        except github.GitHubError as exc:
            return _error_github(exc)

        etiqueta = etiquetar_ejecucion(run.get("conclusion"), jobs,
                                       workflow.patron_paso_despliegue)
        with transaction.atomic():
            ejecucion = guardar_ejecucion(workflow, run)
            for campo, valor in etiqueta.items():
                setattr(ejecucion, campo, valor)
            ejecucion.etiquetada_en = timezone.now()
            ejecucion.save()
            prediccion.ejecucion_real = ejecucion
            prediccion.verificada_en = timezone.now()
            prediccion.clean()
            prediccion.save(update_fields=["ejecucion_real",
                                           "verificada_en"])
        return Response(PrediccionSerializer(prediccion).data)

    @action(detail=True, methods=["post"],
            permission_classes=[EsLiderOAdministrador])
    def decision(self, request, pk=None):
        """El líder técnico autoriza, pospone o pide revisión del cambio."""
        prediccion = self.get_object()
        solicitud = SolicitudDecisionSerializer(data=request.data)
        solicitud.is_valid(raise_exception=True)
        decision = prediccion.decisiones.create(usuario=request.user,
                                                **solicitud.validated_data)
        logger.info("Decisión %s sobre la predicción %s por %s",
                    decision.decision, prediccion.id, request.user.username)
        if decision.fecha_limite:
            asignaciones.notificar_por_correo(decision)
        return Response(PrediccionSerializer(prediccion).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="fecha-limite",
            permission_classes=[EsLiderOAdministrador])
    def fecha_limite(self, request, pk=None):
        """Añade o cambia la fecha límite de la última decisión."""
        prediccion = self.get_object()
        decision = prediccion.decisiones.order_by("-creada_en", "-id").first()
        if decision is None:
            return _error("Registre primero una decisión sobre este análisis.",
                          "sin_decision", status.HTTP_400_BAD_REQUEST)
        solicitud = SolicitudFechaLimiteSerializer(data=request.data)
        solicitud.is_valid(raise_exception=True)
        decision.fecha_limite = solicitud.validated_data["fecha_limite"]
        # El desarrollador debe volver a ver la asignación con la nueva fecha.
        decision.vista_por_desarrollador_en = None
        decision.save(update_fields=["fecha_limite",
                                     "vista_por_desarrollador_en"])
        logger.info("Fecha límite de la predicción %s fijada por %s",
                    prediccion.id, request.user.username)
        asignaciones.notificar_por_correo(decision)
        return Response(PrediccionSerializer(prediccion).data)


class VersionModeloViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = VersionModelo.objects.all()
    serializer_class = VersionModeloSerializer
    permission_classes = [PuedePredecir]

    @action(detail=True, permission_classes=[EsAdministrador])
    def supervision(self, request, pk=None):
        """Comparación de las predicciones con los resultados reales."""
        version = self.get_object()
        predicciones = Prediccion.objects.filter(version_modelo=version)
        evaluables = [
            (p.nivel, p.probabilidad, p.ejecucion_real.y)
            for p in predicciones.filter(
                ejecucion_real__etiqueta__in=["despliegue_completado",
                                              "despliegue_no_completado"])
            .select_related("ejecucion_real")]
        por_nivel = {}
        for nivel in ("bajo", "medio", "alto"):
            casos = [y for n, _, y in evaluables if n == nivel]
            por_nivel[nivel] = {
                "evaluables": len(casos),
                "no_completados": sum(casos),
                "tasa": (sum(casos) / len(casos)) if casos else None,
            }
        brier = (sum((p - y) ** 2 for _, p, y in evaluables) / len(evaluables)
                 if evaluables else None)
        return Response({
            "version": version.version,
            "predicciones": predicciones.count(),
            "verificadas": predicciones.filter(
                ejecucion_real__isnull=False).count(),
            "evaluables": len(evaluables),
            "por_nivel": por_nivel,
            "brier": brier,
        })

    @action(detail=True, methods=["post"],
            permission_classes=[EsAdministrador])
    def activar(self, request, pk=None):
        version = self.get_object()
        with transaction.atomic():
            VersionModelo.objects.update(activo=False)
            version.activo = True
            version.save(update_fields=["activo"])
        return Response(VersionModeloSerializer(version).data)


class AsignacionViewSet(mixins.ListModelMixin, GenericViewSet):
    """Asignaciones (última decisión con fecha límite) de las predicciones
    visibles: el desarrollador recibe solo las de sus análisis."""

    serializer_class = AsignacionSerializer
    permission_classes = [PuedePredecir]

    def get_queryset(self):
        return (asignaciones.ultimas_decisiones(
                    predicciones_visibles(self.request.user))
                .filter(asignaciones.ES_ASIGNACION)
                .select_related("usuario", "prediccion__usuario",
                                "prediccion__workflow__repositorio",
                                "prediccion_respuesta")
                .order_by(F("fecha_limite").asc(nulls_last=True), "id"))

    def _marcar(self, request, campo):
        decision = self.get_object()
        if decision.prediccion.usuario_id != request.user.id:
            return _error("Solo el desarrollador que hizo el análisis puede "
                          "marcar esta asignación.", "no_es_dueno",
                          status.HTTP_403_FORBIDDEN)
        ahora = timezone.now()
        cambios = set()
        for nombre in ("vista_por_desarrollador_en", campo):
            if getattr(decision, nombre) is None:
                setattr(decision, nombre, ahora)
                cambios.add(nombre)
        if cambios:
            decision.save(update_fields=sorted(cambios))
        return Response(AsignacionSerializer(decision).data)

    @action(detail=True, methods=["post"])
    def vista(self, request, pk=None):
        return self._marcar(request, "vista_por_desarrollador_en")

    @action(detail=True, methods=["post"])
    def cumplida(self, request, pk=None):
        return self._marcar(request, "cumplida_en")

    @action(detail=True, methods=["post"])
    def entendida(self, request, pk=None):
        """"Entendido" de una autorización: no requiere nuevo análisis."""
        if self.get_object().decision != "autorizar":
            return _error("Solo una autorización se marca como entendida; "
                          "las demás se atienden con un nuevo análisis.",
                          "no_es_autorizacion", status.HTTP_400_BAD_REQUEST)
        return self._marcar(request, "cumplida_en")


@api_view(["GET"])
@permission_classes([EsAdministrador])
def resumen_admin(request):
    """Conteos para el panel del administrador (sin datos personales).

    Cada usuario cuenta una vez, en su rol de mayor jerarquía (como el menú);
    el superusuario cuenta como administrador.
    """
    usuarios = {"administrador": 0, "lider_tecnico": 0, "desarrollador": 0,
                "sin_rol": 0}
    for usuario in get_user_model().objects.prefetch_related("groups"):
        usuarios[rol_principal(usuario) or "sin_rol"] += 1
    usuarios["total"] = sum(usuarios.values())
    workflows = Workflow.objects.all()
    validados = workflows.filter(despliegue_validado=True)
    return Response({
        "usuarios": usuarios,
        "workflows": {
            "total": workflows.count(),
            "validados": validados.count(),
            "sin_validar": workflows.filter(despliegue_validado=False).count(),
            "validados_disponibles_github": validados.filter(
                disponible_github=True).count(),
        },
    })
