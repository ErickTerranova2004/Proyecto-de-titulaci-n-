"""Informes de cumplimiento (services/informes.py).

- POST /api/asignaciones/<id>/informe/ (en views.AsignacionViewSet): el
  desarrollador lo envía con su comentario.
- GET /api/informes/?desde&hasta&orden: los visibles para el usuario.
- GET /api/informes/<id>/: el informe completo.
- POST /api/informes/<id>/decision/: decisión final del líder.
- GET /api/informes/<id>/pdf/: PDF (cada descarga queda registrada).
"""

from datetime import date

from django.db.models import Case, F, IntegerField, Value, When
from django.http import HttpResponse
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from riesgo import paginacion
from riesgo.models import DecisionDespliegue
from riesgo.permissions import PuedePredecir
from riesgo.services import informes


class SolicitudInformeSerializer(serializers.Serializer):
    comentario = serializers.CharField(max_length=2000, trim_whitespace=True)


class SolicitudDecisionFinalSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=DecisionDespliegue.DECISIONES)
    comentario = serializers.CharField(max_length=1000, required=False,
                                       allow_blank=True, default="")


def _error(mensaje, codigo, estado):
    return Response({"detail": mensaje, "codigo": codigo}, status=estado)


def _fecha(parametros, nombre):
    valor = (parametros.get(nombre) or "").strip()
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise serializers.ValidationError(
            {nombre: "Use una fecha con el formato AAAA-MM-DD."})


RESULTADOS = ("bajo", "mantuvo", "subio")


def _rango(campo):
    return Case(*(When(**{campo: nivel}, then=Value(n))
                  for n, nivel in enumerate(("bajo", "medio", "alto"))),
                output_field=IntegerField())


def filtrar_informes(consulta, parametros):
    """Filtros de «Informes recibidos» e «Informes de cumplimiento»:
    - nivel: bajo, medio o alto (nivel actual: el del análisis nuevo);
    - resultado: bajo (bajó el nivel), mantuvo o subio, comparando el nivel
      del análisis original con el del nuevo;
    - decision: pendiente (sin decisión final) o autorizar, posponer,
      solicitar_revision;
    - repo: parte del nombre del repositorio.
    """
    nivel = (parametros.get("nivel") or "").strip()
    if nivel:
        if nivel not in ("bajo", "medio", "alto"):
            raise serializers.ValidationError({"nivel": "Use bajo, medio o alto."})
        consulta = consulta.filter(prediccion_nueva__nivel=nivel)
    resultado = (parametros.get("resultado") or "").strip()
    if resultado:
        if resultado not in RESULTADOS:
            raise serializers.ValidationError({"resultado": "Use bajo, mantuvo o subio."})
        consulta = consulta.annotate(
            rango_original=_rango("prediccion_original__nivel"),
            rango_nuevo=_rango("prediccion_nueva__nivel"))
        comparacion = {"bajo": "rango_nuevo__lt", "mantuvo": "rango_nuevo", "subio": "rango_nuevo__gt"}
        consulta = consulta.filter(**{comparacion[resultado]: F("rango_original")})
    decision = (parametros.get("decision") or "").strip()
    if decision:
        tipos = {d for d, _ in DecisionDespliegue.DECISIONES}
        if decision == "pendiente":
            consulta = consulta.filter(decision_final__isnull=True)
        elif decision in tipos:
            consulta = consulta.filter(decision_final__decision=decision)
        else:
            raise serializers.ValidationError(
                {"decision": "Use pendiente, autorizar, posponer o solicitar_revision."})
    repo = (parametros.get("repo") or "").strip()
    if repo:
        consulta = consulta.filter(
            prediccion_original__workflow__repositorio__nombre_completo__icontains=repo)
    return consulta


def enviar_informe(request, asignacion):
    """Lo usa AsignacionViewSet.informe."""
    solicitud = SolicitudInformeSerializer(data=request.data)
    solicitud.is_valid(raise_exception=True)
    try:
        informe = informes.crear(asignacion, request.user,
                                 solicitud.validated_data["comentario"])
    except informes.InformeNoValido as exc:
        estado = (status.HTTP_403_FORBIDDEN if exc.codigo == "no_es_dueno"
                  else status.HTTP_400_BAD_REQUEST)
        return _error(str(exc), exc.codigo, estado)
    return Response(informes.contenido(informe, request.user),
                    status=status.HTTP_201_CREATED)


class InformeViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     GenericViewSet):
    permission_classes = [PuedePredecir]

    def get_queryset(self):
        consulta = informes.informes_visibles(self.request.user)
        if self.action != "list":
            return consulta
        parametros = self.request.query_params
        desde, hasta = _fecha(parametros, "desde"), _fecha(parametros, "hasta")
        if desde and hasta and desde > hasta:
            raise serializers.ValidationError(
                {"desde": "La fecha «desde» no puede ser posterior a «hasta»."})
        # Día local (settings.TIME_ZONE), ambos extremos incluidos.
        if desde:
            consulta = consulta.filter(enviado_en__date__gte=desde)
        if hasta:
            consulta = consulta.filter(enviado_en__date__lte=hasta)
        consulta = filtrar_informes(consulta, parametros)
        if parametros.get("orden") == "antiguo":
            return consulta.order_by("enviado_en", "id")
        return consulta.order_by("-enviado_en", "-id")

    def list(self, request):
        consulta = self.get_queryset()
        if paginacion.pedida(request.query_params):
            return Response(paginacion.paginar(
                consulta, request.query_params,
                lambda filas: [informes.resumen(i) for i in filas]))
        return Response([informes.resumen(i) for i in consulta])

    def retrieve(self, request, pk=None):
        informe = self.get_object()
        informes.marcar_leido(informe, request.user)
        return Response(informes.contenido(informe, request.user))

    @action(detail=True, methods=["post"])
    def decision(self, request, pk=None):
        informe = self.get_object()
        solicitud = SolicitudDecisionFinalSerializer(data=request.data)
        solicitud.is_valid(raise_exception=True)
        try:
            informes.decidir(informe, request.user, **solicitud.validated_data)
        except informes.InformeNoValido as exc:
            return _error(str(exc), exc.codigo, status.HTTP_403_FORBIDDEN)
        return Response(informes.contenido(informe, request.user),
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        informe = self.get_object()
        contenido = informes.pdf(informe, request.user)
        informes.registrar_descarga(informe, request.user, "pdf")
        respuesta = HttpResponse(contenido, content_type="application/pdf")
        respuesta["Content-Disposition"] = (
            f'attachment; filename="informe_{informe.numero}.pdf"')
        return respuesta
