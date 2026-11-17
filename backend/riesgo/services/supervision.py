"""Supervisión de un modelo con los resultados reales y comparación en sombra.

- posteriores_al_corte(version): predicciones que cuentan en la supervisión
  de una versión (sin demostración ni casos de prueba, y solo ejecuciones
  posteriores a metadatos.fecha_corte).
- EVALUABLES: etiquetas con resultado (completado / no completado).
- comparacion(): el modelo activo frente a sus predicciones en sombra (v1,
  v1.1) sobre exactamente las mismas ejecuciones evaluables, con tasa de
  fallo por nivel, Brier y PR-AUC con IC 95 %.
"""

import math

import numpy as np
from django.db.models import Q
from sklearn.metrics import average_precision_score

from riesgo.models import Prediccion, VersionModelo
from riesgo.services.features import fecha

EVALUABLES = ["despliegue_completado", "despliegue_no_completado"]
NIVELES = ("bajo", "medio", "alto")
# Remuestreos bootstrap pareados (mismas ejecuciones en todos los modelos) y
# semilla fija: el resultado no cambia al recargar la página.
REMUESTREOS = 1000
SEMILLA = 20261117
Z_95 = 1.959963984540054


def posteriores_al_corte(version):
    """(todas, predicciones que cuentan, fecha de corte, excluidas por el
    corte). Solo predicciones de la plataforma (el gestor por defecto ya
    excluye las de la evaluación en sombra)."""
    todas = Prediccion.objects.filter(version_modelo=version)
    # Ni las de demostración ni las de los casos de prueba: no son
    # validación del modelo.
    predicciones = todas.para_modelo()
    # Fecha de corte (metadatos.fecha_corte): solo cuentan ejecuciones que
    # empezaron después de la más reciente del entrenamiento.
    corte = fecha(version.metadatos.get("fecha_corte"))
    excluidas = 0
    if corte is not None:
        posteriores = predicciones.filter(
            Q(origen="lote", momento_variables__gt=corte)
            | Q(origen="interactivo", creada_en__gt=corte)).exclude(
            ejecucion_real__iniciada_en__lte=corte)
        excluidas = predicciones.count() - posteriores.count()
        predicciones = posteriores
    return todas, predicciones, corte, excluidas


def evaluables(predicciones):
    return predicciones.filter(ejecucion_real__etiqueta__in=EVALUABLES)


def tasas_por_nivel(niveles, y):
    resultado = {}
    for nivel in NIVELES:
        casos = [yi for n, yi in zip(niveles, y) if n == nivel]
        resultado[nivel] = {
            "evaluables": len(casos),
            "no_completados": sum(casos),
            "tasa": (sum(casos) / len(casos)) if casos else None,
        }
    return resultado


def brier(probabilidades, y):
    if not len(y):
        return None
    p, y = np.asarray(probabilidades, float), np.asarray(y, float)
    return float(np.mean((p - y) ** 2))


def wilson(exitos, n, z=Z_95):
    """IC 95 % de Wilson para una proporción (None si no hay casos)."""
    if not n:
        return None
    p = exitos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margen = (z / (1 + z * z / n)) * math.sqrt(p * (1 - p) / n
                                                + z * z / (4 * n * n))
    return [max(0.0, centro - margen), min(1.0, centro + margen)]


def _pr_auc(y, p):
    # Sin positivos (o sin negativos) la PR-AUC no está definida.
    if y.min() == y.max():
        return np.nan
    return average_precision_score(y, p)


def _ic(valores):
    valores = np.asarray(valores, float)
    valores = valores[~np.isnan(valores)]
    if not len(valores):
        return None
    return [float(np.percentile(valores, 2.5)),
            float(np.percentile(valores, 97.5))]


def _indicador(valor, muestras):
    return {"valor": None if valor is None or np.isnan(valor) else float(valor),
            "ic95": _ic(muestras)}


def metricas_pareadas(y, probabilidades, referencia):
    """Brier y PR-AUC de cada modelo, con IC 95 % bootstrap, y la diferencia
    con la referencia (otro modelo − referencia) sobre los mismos
    remuestreos: Brier menor y PR-AUC mayor son mejores.

    probabilidades: {version: lista alineada con y}."""
    y = np.asarray(y, int)
    p = {v: np.asarray(ps, float) for v, ps in probabilidades.items()}
    generador = np.random.default_rng(SEMILLA)
    n = len(y)
    muestras = {v: {"brier": [], "pr_auc": []} for v in p}
    for _ in range(REMUESTREOS if n else 0):
        i = generador.integers(0, n, n)
        for v, pv in p.items():
            muestras[v]["brier"].append(float(np.mean((pv[i] - y[i]) ** 2)))
            muestras[v]["pr_auc"].append(_pr_auc(y[i], pv[i]))

    def indicadores(v):
        return {"brier": _indicador(brier(p[v], y) if n else None,
                                    muestras[v]["brier"]),
                "pr_auc": _indicador(_pr_auc(y, p[v]) if n else None,
                                     muestras[v]["pr_auc"])}

    ref = indicadores(referencia)
    resultado = {referencia: ref}
    for v in p:
        if v == referencia:
            continue
        datos = indicadores(v)
        datos["diferencia_con_referencia"] = {
            m: _indicador(
                None if datos[m]["valor"] is None or ref[m]["valor"] is None
                else datos[m]["valor"] - ref[m]["valor"],
                np.asarray(muestras[v][m]) - np.asarray(muestras[referencia][m]))
            for m in ("brier", "pr_auc")}
        resultado[v] = datos
    return resultado


def comparacion():
    """El modelo activo y sus versiones en sombra sobre exactamente las
    mismas ejecuciones evaluables (las que tienen predicción en sombra de
    todas las demás versiones)."""
    referencia = VersionModelo.objects.filter(activo=True).first()
    if referencia is None:
        return None
    sombras = list(VersionModelo.objects.exclude(id=referencia.id)
                   .order_by("-registrado_en", "-id"))
    _, predicciones, corte, _ = posteriores_al_corte(referencia)
    base = list(evaluables(predicciones).select_related("ejecucion_real")
                .order_by("id"))
    base_ids = [p.id for p in base]
    filas = {v.id: {s.prediccion_base_id: s for s in Prediccion.con_sombra
                    .filter(origen="sombra", version_modelo=v,
                            prediccion_base_id__in=base_ids)}
             for v in sombras}
    comunes = [p for p in base if all(p.id in filas[v.id] for v in sombras)]
    y = [p.ejecucion_real.y for p in comunes]

    modelos = [(referencia, comunes)] + [
        (v, [filas[v.id][p.id] for p in comunes]) for v in sombras]
    metricas = metricas_pareadas(
        y, {v.version: [x.probabilidad for x in lista] for v, lista in modelos},
        referencia.version)
    resultado = []
    for version, lista in modelos:
        por_nivel = tasas_por_nivel([x.nivel for x in lista], y)
        for datos in por_nivel.values():
            datos["ic95"] = wilson(datos["no_completados"], datos["evaluables"])
        resultado.append({
            "version": version.version,
            "nombre_modelo": version.nombre_modelo,
            "en_sombra": version.id != referencia.id,
            "limites_riesgo": version.metadatos.get("limites_riesgo"),
            "por_nivel": por_nivel,
            **metricas[version.version],
        })
    return {
        "referencia": referencia.version,
        "fecha_corte": corte,
        "ejecuciones": len(comunes),
        "no_completados": sum(y),
        "evaluables_referencia": len(base),
        "sin_sombra": len(base) - len(comunes),
        "remuestreos": REMUESTREOS,
        "modelos": resultado,
    }
