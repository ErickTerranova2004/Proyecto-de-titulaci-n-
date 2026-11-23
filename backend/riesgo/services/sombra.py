"""Evaluación en sombra de las versiones visibles no activas.

Hoy: XGBoost (v2-xgb, alternativo) frente a Random Forest (v2, principal),
los dos del dataset v2. v1 y v1.1 están ocultas (est_registro = 'I') y ya
no se evalúan; su comparación quedó en informes/comparacion_sombra_v1.md y
comparacion_sombra_v2.md.

Cada versión no activa predice las mismas ejecuciones evaluables que cuentan
en la supervisión del modelo activo (posteriores a su fecha de corte), con
las variables ya guardadas en la predicción del modelo activo: no se activa
ningún modelo ni se consulta GitHub. Las variables que esa predicción no
tiene (p. ej. reejecutado_por_otro, que v2 no usa) se rellenan con la
mediana de entrenamiento de cada modelo (la del imputador de su pipeline).

Las predicciones en sombra se guardan con origen «sombra» y
prediccion_base = la del modelo activo. El gestor por defecto de Prediccion
las excluye: no son análisis de usuarios ni salen en historiales,
dashboards ni «Nuevo análisis».
"""

from functools import lru_cache

from django.db import transaction

from riesgo.models import Prediccion, VersionModelo
from riesgo.services import predictor, supervision


@lru_cache(maxsize=8)
def _medianas(archivo, archivo_explicacion):
    _, base, _ = predictor._cargar(archivo, archivo_explicacion)
    for nombre, transformador, columnas in base.named_steps["prep"].transformers_:
        if nombre != "num":
            continue
        pasos = getattr(transformador, "named_steps", None)
        imputador = pasos["imputar"] if pasos else transformador
        return {c: float(m) for c, m in zip(columnas, imputador.statistics_)}
    return {}


def medianas(version):
    """Mediana de entrenamiento de cada variable numérica del modelo."""
    return _medianas(predictor._ruta(version.archivo),
                     predictor._ruta(version.archivo_explicacion))


def variables_para(version, variables):
    """(variables completas para `version`, variables rellenadas con la
    mediana). Solo se rellenan las que no existen; un valor nulo guardado
    (sin historial) se respeta y lo trata el imputador del modelo."""
    completas = dict(variables)
    rellenadas = []
    for columna, mediana in medianas(version).items():
        if columna not in completas:
            completas[columna] = mediana
            rellenadas.append(columna)
    return completas, rellenadas


def pendientes(referencia, version):
    """Predicciones evaluables del modelo activo sin sombra de `version`."""
    _, predicciones, _, _ = supervision.posteriores_al_corte(referencia)
    hechas = Prediccion.con_sombra.filter(
        origen="sombra", version_modelo=version).values(
        "prediccion_base_id")
    return (supervision.evaluables(predicciones)
            .exclude(id__in=hechas).select_related("ejecucion_real")
            .order_by("id"))


def generar(usuario, contar=False):
    """Crea las predicciones en sombra que falten. Devuelve
    {version: {"creadas": n, "rellenadas": [variables]}}."""
    # La referencia es el modelo del lote (Random Forest), no el principal.
    from riesgo.services.modelos import modelo_lote
    referencia = modelo_lote()
    resumen = {}
    # Las versiones ocultas (est_registro = 'I') ya no se evalúan.
    visibles = VersionModelo.objects.filter(est_registro="A")
    for version in visibles.exclude(id=referencia.id).order_by("id"):
        lista = list(pendientes(referencia, version))
        filas, rellenadas = [], set()
        for p in lista:
            completas, faltan = variables_para(version, p.variables)
            filas.append(completas)
            rellenadas.update(faltan)
        resumen[version.version] = {"creadas": len(lista),
                                    "rellenadas": sorted(rellenadas)}
        if contar or not lista:
            continue
        limites = version.metadatos["limites_riesgo"]
        probabilidades = predictor.probabilidades(filas, version)
        nuevas = []
        for p, variables, probabilidad in zip(lista, filas, probabilidades):
            nivel = predictor.nivel_de(probabilidad, limites)
            nuevas.append(Prediccion(
                usuario=usuario, workflow_id=p.workflow_id,
                commit_id=p.commit_id, version_modelo=version, rama=p.rama,
                evento=p.evento, variables=variables,
                probabilidad=probabilidad, nivel=nivel,
                recomendacion=predictor.recomendacion_de(nivel),
                factores=[], recomendaciones=[], analisis_ia=None,
                origen="sombra", prediccion_base=p,
                momento_variables=p.momento_variables,
                ejecucion_real_id=p.ejecucion_real_id,
                verificada_en=p.verificada_en,
                datos_github_extraidos_en=p.datos_github_extraidos_en))
        with transaction.atomic():
            Prediccion.con_sombra.bulk_create(nuevas, batch_size=500)
    return resumen
