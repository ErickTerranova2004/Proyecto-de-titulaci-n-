import logging
import math

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins

from riesgo.models import (AccesoRepositorio, DecisionDespliegue,
                           EjecucionWorkflow, Prediccion, Repositorio,
                           VersionModelo, Workflow)
from riesgo.permissions import (EsAdministrador, EsLiderOAdministrador,
                                PuedePredecir, predicciones_visibles,
                                repositorios_visibles, rol_principal, roles,
                                tiene_acceso)
from riesgo.serializers import (AsignacionSerializer, PrediccionSerializer,
                                RepositorioSerializer,
                                SolicitudDecisionSerializer,
                                SolicitudEscenarioSerializer,
                                SolicitudFechaLimiteSerializer,
                                SolicitudPrediccionSerializer,
                                SolicitudRegistroSerializer,
                                VersionModeloSerializer)
from riesgo.services import (analisis_ia, asignaciones, github, planificador,
                             supervision)
from riesgo.services.sincronizacion import sincronizar_repositorio
from riesgo.services.pendientes import despliegue_previo
from riesgo.services.verificacion import enlazar_resultado, etiquetar_run
from riesgo.services.features import calcular_variables
from riesgo.services.predictor import SinModeloActivo, predecir
from riesgo.services.trazabilidad import (RepositorioNoRegistrado,
                                          guardar_commit, guardar_ejecucion,
                                          resolver_repositorio)

logger = logging.getLogger(__name__)


def _json_seguro(variables):
    """Convierte NaN en None para guardar JSON válido."""
    return {k: (None if isinstance(v, float) and math.isnan(v) else v)
            for k, v in variables.items()}


def _error_no_interactivo():
    # Una decisión se asigna al desarrollador que hizo el análisis: la de un
    # análisis del lote no le llegaría a nadie.
    return _error("Solo se decide sobre análisis hechos por un desarrollador "
                  "antes de desplegar; los del lote evalúan despliegues que "
                  "ya ocurrieron.", "no_es_interactivo",
                  status.HTTP_400_BAD_REQUEST)


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


MOTIVOS_PENDIENTE = {
    "sin_ejecuciones": "No hay ejecuciones de este workflow para este commit.",
    "en_curso": "Hay una ejecución de este commit en curso; todavía no ha "
                "terminado.",
    "solo_anteriores": "Solo hay ejecuciones de este commit anteriores a la "
                       "predicción.",
}


def _verificacion_pendiente(runs, workflow, repo, sha, creada_en):
    """Motivo exacto por el que aún no hay ejecución real que enlazar."""
    # Las omitidas (skipped) no son intentos de despliegue: no cuentan.
    del_commit = [r for r in runs
                  if r.get("head_sha") == sha
                  and r.get("conclusion") != "skipped"
                  and (r.get("path") or workflow.path).split("@")[0]
                  == workflow.path]
    if not del_commit:
        motivo = "sin_ejecuciones"
    elif any(r.get("status") != "completed" for r in del_commit):
        motivo = "en_curso"
    else:
        motivo = "solo_anteriores"
    archivo = workflow.path.rsplit("/", 1)[-1]
    return {"estado": "pendiente", "motivo": motivo,
            "detail": MOTIVOS_PENDIENTE[motivo],
            "repositorio": repo, "workflow_path": workflow.path,
            "sha_corto": sha[:7],
            "url_actions": f"https://github.com/{repo}/actions/workflows/"
                           f"{archivo}"}


def _aviso_desplegado(previo, sha):
    """409 de «Nuevo análisis»: el commit ya se desplegó o se está
    desplegando; el desarrollador puede continuar de todos modos."""
    en_curso = previo["estado"] != "completed"
    detalle = (
        f"Este commit ({sha[:7]}) se está desplegando ahora."
        if en_curso else f"Este commit ({sha[:7]}) ya se desplegó.")
    return {"detail": detalle + " El análisis no podrá compararse con un "
                      "resultado real: solo se enlaza un despliegue que "
                      "empiece después del análisis.",
            "codigo": "commit_ya_desplegado", "en_curso": en_curso,
            "sha": sha, "ejecucion": previo}


def _ultima_ejecucion_commit(cliente, runs, workflow, repo, sha):
    """Resultado en GitHub de la última ejecución terminada del commit.

    Se muestra aunque haya empezado antes del análisis, pero no se enlaza a
    la predicción: no cuenta en la supervisión del modelo.
    """
    terminadas = sorted(
        (r for r in runs
         if r.get("head_sha") == sha and r.get("status") == "completed"
         and (r.get("path") or workflow.path).split("@")[0] == workflow.path
         and r.get("run_started_at")),
        key=lambda r: r["run_started_at"])
    if not terminadas:
        return None
    run = terminadas[-1]
    intento = run.get("run_attempt") or 1
    jobs = cliente.jobs_intento(repo, run["id"], intento)
    etiqueta = etiquetar_run(cliente, workflow, run, jobs)
    return {"run_id": run["id"], "run_attempt": intento,
            "evento": run.get("event", ""), "rama": run.get("head_branch", ""),
            "conclusion": run.get("conclusion", ""),
            "iniciada_en": run["run_started_at"], "url": run.get("html_url"),
            **etiqueta}


@api_view(["GET"])
def yo(request):
    return Response({"usuario": request.user.username,
                     "roles": sorted(roles(request.user))})


class RepositorioViewSet(mixins.ListModelMixin, GenericViewSet):
    """Repositorios visibles con sus workflows de despliegue validados."""

    serializer_class = RepositorioSerializer
    permission_classes = [PuedePredecir]

    def get_queryset(self):
        # Los inactivos conservan su historial, pero no se ofrecen.
        visibles = repositorios_visibles(self.request.user).filter(
            est_registro="A")
        # ?todos=1: todos los repositorios visibles (asignados), aunque no
        # tengan workflows utilizables. Lo usan los paneles por rol.
        if self.request.query_params.get("todos") == "1":
            return visibles.prefetch_related("workflows")
        # Por defecto, solo los que tienen algún workflow utilizable (selector
        # de Nuevo análisis e Integraciones).
        return visibles.filter(
            workflows__despliegue_validado=True,
            workflows__disponible_github=True).distinct().prefetch_related(
            "workflows", "workflows__pendiente_despliegue")

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
        # Usuarios a los que se asigna el repositorio: solo líderes técnicos
        # y desarrolladores activos (el administrador ya ve todos).
        asignar = list(get_user_model().objects.filter(
            id__in=set(datos["usuarios"]), is_active=True))
        if (len(asignar) != len(set(datos["usuarios"])) or any(
                rol_principal(u) not in ("lider_tecnico", "desarrollador")
                for u in asignar)):
            return _error("Solo se puede asignar el repositorio a líderes "
                          "técnicos y desarrolladores activos.",
                          "usuario_no_valido", status.HTTP_400_BAD_REQUEST)
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
            # Registrarlo de nuevo a mano lo vuelve a activar.
            repositorio.est_registro = "A"
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
            for usuario in asignar:
                AccesoRepositorio.objects.get_or_create(
                    usuario=usuario, repositorio=repositorio,
                    defaults={"asignado_por": request.user})

        logger.info("Workflow %s registrado por %s", workflow,
                    request.user.username)
        return Response({
            "repositorio": nombre,
            "workflow_path": workflow.path,
            "ejecuciones_recientes": len(recientes),
            "asignado_a": sorted(u.username for u in asignar),
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
        # Solo lo activo (est_registro='A'): sin los repositorios inactivos
        # ni los datos desactivados de los casos de prueba.
        "repositorios_registrados": Repositorio.objects.filter(
            est_registro="A").count(),
        "workflows_validados": Workflow.objects.filter(
            despliegue_validado=True, est_registro="A").count(),
        "ejecuciones_almacenadas": EjecucionWorkflow.objects.filter(
            est_registro="A").count(),
        "ultima_extraccion": ultima,
    }})


def _fecha_parametro(parametros, nombre):
    valor = (parametros.get(nombre) or "").strip()
    if not valor:
        return None
    try:
        fecha = parse_date(valor)
    except ValueError:
        fecha = None
    if fecha is None:
        raise ValidationError({nombre: "Use una fecha con el formato "
                                       "AAAA-MM-DD."})
    return fecha


def filtrar_historial(consulta, parametros):
    """Filtros y orden de los historiales y de «Pendientes de decisión».

    - desde / hasta (AAAA-MM-DD, ambos incluidos): día de creación del
      análisis en la zona horaria de la plataforma (America/Guayaquil).
    - nivel: bajo, medio o alto (varios separados por comas).
    - sin_decision=1: solo los análisis que esperan la decisión del líder.
    - origen: interactivo o lote (solo cambia algo para el administrador;
      el resto ya ve solo los interactivos).
    - orden: «reciente» (por defecto, del más reciente al más antiguo) o
      «antiguo».
    """
    desde = _fecha_parametro(parametros, "desde")
    hasta = _fecha_parametro(parametros, "hasta")
    if desde and hasta and desde > hasta:
        raise ValidationError({"desde": "La fecha «desde» no puede ser "
                                        "posterior a «hasta»."})
    if desde:
        consulta = consulta.filter(creada_en__date__gte=desde)
    if hasta:
        consulta = consulta.filter(creada_en__date__lte=hasta)

    niveles = {n.strip() for n in (parametros.get("nivel") or "").split(",")
               if n.strip()}
    validos = {n for n, _ in Prediccion.NIVELES}
    if niveles - validos:
        raise ValidationError({"nivel": "Use bajo, medio o alto."})
    if niveles:
        consulta = consulta.filter(nivel__in=niveles)

    if parametros.get("sin_decision") in ("1", "true"):
        consulta = consulta.filter(decisiones__isnull=True)

    origen = parametros.get("origen")
    if origen:
        if origen not in ("interactivo", "lote"):
            raise ValidationError({"origen": "Use interactivo o lote."})
        consulta = consulta.filter(origen=origen)

    orden = parametros.get("orden") or "reciente"
    if orden not in ("reciente", "antiguo"):
        raise ValidationError({"orden": "Use reciente o antiguo."})
    if orden == "antiguo":
        return consulta.order_by("creada_en", "id")
    return consulta.order_by("-creada_en", "-id")


class PrediccionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        GenericViewSet):
    serializer_class = PrediccionSerializer
    permission_classes = [PuedePredecir]

    def get_queryset(self):
        consulta = predicciones_visibles(self.request.user).prefetch_related(
            "ejecuciones_previas", "decisiones__usuario", "decisiones__informe")
        repositorio = self.request.query_params.get("repositorio")
        if repositorio:
            consulta = consulta.filter(
                workflow__repositorio__nombre_completo=repositorio)
        if self.action == "list":
            consulta = filtrar_historial(consulta, self.request.query_params)
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
        if repositorio.est_registro != "A":
            return _error("El repositorio está inactivo en la plataforma: se "
                          "conserva su historial, pero no admite nuevos "
                          "análisis.", "repositorio_inactivo",
                          status.HTTP_400_BAD_REQUEST)
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
            if not datos["confirmar_desplegado"]:
                # Misma consulta que calcular_variables (queda en caché).
                completo = cliente.commit(nombre, sha).get("sha") or sha
                previo = despliegue_previo(cliente, nombre, workflow, completo)
                if previo:
                    return Response(_aviso_desplegado(previo, completo),
                                    status=status.HTTP_409_CONFLICT)
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
        analisis, recomendaciones = analisis_ia.analizar(
            variables, resultado, contexto, nombre, workflow.path,
            datos["rama"], datos["evento"])

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
                recomendacion=resultado["recomendacion"],
                factores=resultado["factores"],
                recomendaciones=recomendaciones,
                analisis_ia=analisis,
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
            enlazada, runs = enlazar_resultado(cliente, prediccion)
            if not enlazada:
                pendiente = _verificacion_pendiente(
                    runs, workflow, repo, sha, prediccion.creada_en)
                pendiente["ejecucion_github"] = _ultima_ejecucion_commit(
                    cliente, runs, workflow, repo, sha)
                return Response(pendiente)
        except github.GitHubError as exc:
            return _error_github(exc)
        return Response(PrediccionSerializer(prediccion).data)

    @action(detail=True, methods=["post"])
    def escenario(self, request, pk=None):
        """Estima un escenario alternativo del análisis. No guarda nada."""
        prediccion = self.get_object()
        solicitud = SolicitudEscenarioSerializer(data=request.data)
        solicitud.is_valid(raise_exception=True)
        return Response(planificador.estimar_escenario(
            prediccion, solicitud.validated_data))

    @action(detail=True, methods=["get"])
    def ventanas(self, request, pk=None):
        """Hora de menor riesgo de cada uno de los próximos días, desde
        mañana. ?dias=N (1–14; por defecto PLANIFICADOR_DIAS_VENTANAS)."""
        dias = None
        if request.query_params.get("dias"):
            try:
                dias = int(request.query_params["dias"])
            except ValueError:
                dias = 0
            if not 1 <= dias <= planificador.MAX_DIAS:
                return Response(
                    {"dias": f"Debe ser un número entre 1 y "
                             f"{planificador.MAX_DIAS}."}, status=400)
        return Response(planificador.mejores_ventanas(self.get_object(),
                                                      dias))

    @action(detail=True, methods=["post"],
            permission_classes=[EsLiderOAdministrador])
    def decision(self, request, pk=None):
        """El líder técnico autoriza, pospone o pide revisión del cambio."""
        prediccion = self.get_object()
        if prediccion.origen != "interactivo":
            return _error_no_interactivo()
        solicitud = SolicitudDecisionSerializer(data=request.data)
        solicitud.is_valid(raise_exception=True)
        datos = solicitud.validated_data
        decision = asignaciones.registrar_decision(prediccion, request.user,
                                                   **datos)
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
        if self.get_object().origen != "interactivo":
            return _error_no_interactivo()
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
    # Las versiones ocultas (est_registro = 'I', p. ej. v1.1) no salen en
    # ninguna pantalla ni se pueden activar; sus filas y predicciones se
    # conservan.
    queryset = VersionModelo.objects.filter(est_registro="A")
    serializer_class = VersionModeloSerializer
    permission_classes = [PuedePredecir]

    @action(detail=True, permission_classes=[EsAdministrador])
    def supervision(self, request, pk=None):
        """Comparación de las predicciones con los resultados reales."""
        version = self.get_object()
        todas, predicciones, corte, excluidas_corte = (
            supervision.posteriores_al_corte(version))
        # Una versión no activa no hace análisis nuevos: su supervisión suma
        # sus predicciones en sombra (las mismas ejecuciones evaluables que
        # la del modelo activo, ver services/sombra.py).
        sombra = (Prediccion.con_sombra.filter(origen="sombra",
                                               version_modelo=version)
                  if not version.activo else Prediccion.con_sombra.none())
        evaluables = [
            (p.nivel, p.probabilidad, p.ejecucion_real.y)
            for consulta in (predicciones, sombra)
            for p in supervision.evaluables(consulta)
            .select_related("ejecucion_real")]
        y = [y for _, _, y in evaluables]
        por_nivel = supervision.tasas_por_nivel(
            [n for n, _, _ in evaluables], y)
        brier = supervision.brier([p for _, p, _ in evaluables], y)
        n_sombra = sombra.count()
        return Response({
            "version": version.version,
            "predicciones": predicciones.count() + n_sombra,
            "predicciones_sombra": n_sombra,
            # Excluidas de todas las métricas anteriores.
            "predicciones_demostracion": todas.de_demostracion().count(),
            "predicciones_prueba": todas.de_prueba().count(),
            "fecha_corte": corte,
            "predicciones_anteriores_al_corte": excluidas_corte,
            "predicciones_lote": predicciones.filter(origen="lote").count(),
            "verificadas": predicciones.filter(
                ejecucion_real__isnull=False).count()
            + sombra.filter(ejecucion_real__isnull=False).count(),
            "evaluables": len(evaluables),
            "por_nivel": por_nivel,
            "brier": brier,
        })

    @action(detail=False, url_path="comparacion-sombra",
            permission_classes=[EsAdministrador])
    def comparacion_sombra(self, request):
        """El modelo activo y las versiones no activas (evaluadas en sombra)
        sobre exactamente las mismas ejecuciones evaluables."""
        datos = supervision.comparacion()
        if datos is None:
            return _error("No hay un modelo activo.", "sin_modelo_activo",
                          status.HTTP_409_CONFLICT)
        return Response(datos)

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
                .filter(asignaciones.ES_ASIGNACION, est_registro="A")
                .select_related("usuario", "prediccion__usuario",
                                "prediccion__workflow__repositorio",
                                "prediccion_respuesta", "informe")
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
    def informe(self, request, pk=None):
        """El desarrollador envía al líder el informe de cumplimiento."""
        from riesgo.views_informes import enviar_informe
        return enviar_informe(request, self.get_object())

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
    # Sin los workflows desactivados (p. ej. los de los casos de prueba).
    workflows = Workflow.objects.filter(est_registro="A")
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
