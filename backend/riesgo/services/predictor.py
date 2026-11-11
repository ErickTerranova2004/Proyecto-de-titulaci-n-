"""Carga el modelo activo, calcula la probabilidad, el nivel y los factores."""

import math
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from django.conf import settings

from riesgo.models import VersionModelo

DESCRIPCIONES = {
    "wf_tasa_fallo_prev": "Tasa de fallos de las ejecuciones previas del "
                          "workflow",
    "wf_ultimo_fallo": "La última ejecución del workflow falló",
    "wf_n_prev": "Número de ejecuciones previas del workflow",
    "wf_horas_desde_ultimo": "Horas desde la ejecución previa del workflow",
    "wf_duracion_media_prev_min": "Duración media de las ejecuciones previas "
                                  "(min)",
    "repo_tasa_fallo_prev": "Tasa de fallos reciente del repositorio",
    "repo_n_prev": "Ejecuciones previas observadas en el repositorio",
    "repo_n_workflows_prev": "Workflows activos en el repositorio",
    "retraso_commit_run_min": "Minutos entre el commit y el despliegue",
    "rama_principal": "Despliegue desde la rama principal",
    "rama_tag": "Despliegue desde una etiqueta de versión",
    "rama_bot": "Rama creada por un bot de dependencias",
    "msg_len": "Longitud del mensaje del commit",
    "msg_lineas": "Líneas del mensaje del commit",
    "msg_merge": "El commit es un merge",
    "msg_revert": "El commit revierte cambios",
    "msg_fix": "El commit corrige un error",
    "msg_feat": "El commit añade funcionalidad",
    "msg_deps": "El commit actualiza dependencias",
    "msg_docs": "El commit modifica documentación",
    "msg_ci": "El commit modifica la configuración de CI",
    "autor_bot": "El autor es un bot",
    "tiene_pr": "El commit pertenece a un pull request",
    "archivos_modificados": "Archivos modificados en el commit",
    "lineas_anadidas": "Líneas añadidas en el commit",
    "lineas_borradas": "Líneas borradas en el commit",
    "checks_n_prev": "Checks del commit terminados antes del despliegue",
    "checks_fallidos_prev": "Checks fallidos del commit antes del despliegue",
    "checks_tasa_fallo_prev": "Proporción de checks fallidos del commit",
    "hora_utc": "Hora del despliegue (UTC)",
    "dia_semana": "Día de la semana",
    "fin_de_semana": "Despliegue en fin de semana",
    "es_reintento": "Es un reintento",
    "reejecutado_por_otro": "Reejecutado por otra persona",
}


class SinModeloActivo(Exception):
    pass


@lru_cache(maxsize=4)
def _cargar(archivo, archivo_explicacion):
    modelo = joblib.load(archivo)
    base = joblib.load(archivo_explicacion)
    explicador = shap.TreeExplainer(base.named_steps["modelo"])
    return modelo, base, explicador


def modelo_activo():
    version = VersionModelo.objects.filter(activo=True).first()
    if version is None:
        raise SinModeloActivo()
    return version


def _ruta(nombre):
    ruta = Path(nombre)
    return str(ruta if ruta.is_absolute() else settings.MODELOS_DIR / ruta)


def _nombre_original(transformada):
    """'num__missingindicator_x' -> ('x', True); 'cat__event_push' -> event."""
    nombre = transformada.split("__", 1)[1]
    if nombre.startswith("missingindicator_"):
        return nombre[len("missingindicator_"):], True
    if transformada.startswith("cat__"):
        return "event", False
    return nombre, False


def _valor_legible(valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "sin historial"
    if isinstance(valor, float):
        return round(valor, 3)
    return valor


def _modelos(version):
    return _cargar(_ruta(version.archivo), _ruta(version.archivo_explicacion))


def _filas(lista_variables, meta):
    columnas = meta["variables_categoricas"] + meta["variables_numericas"]
    return pd.DataFrame([{c: _a_numero(v.get(c)) for c in columnas}
                         for v in lista_variables], columns=columnas)


def _a_numero(valor):
    # Las variables guardadas en JSON tienen None donde hubo NaN.
    return np.nan if valor is None else valor


def nivel_de(probabilidad, limites):
    if probabilidad >= limites["alto"]:
        return "alto"
    if probabilidad >= limites["medio"]:
        return "medio"
    return "bajo"


def recomendacion_de(nivel):
    """Recomendación automática: con riesgo alto, revisar antes de desplegar.

    El líder técnico puede aceptarla o cambiarla al registrar su decisión.
    """
    return "solicitar_revision" if nivel == "alto" else "permitir"


def probabilidades(lista_variables, version):
    """Probabilidad de varias filas en una sola llamada (sin SHAP)."""
    modelo, _, _ = _modelos(version)
    filas = _filas(lista_variables, version.metadatos)
    return [float(p) for p in modelo.predict_proba(filas)[:, 1]]


def contribuciones(variables, version):
    """Contribución SHAP de cada variable original (todas, sin recortar)."""
    _, base, explicador = _modelos(version)
    # SHAP sobre el modelo sin calibrar (misma ordenación de riesgo).
    prep = base.named_steps["prep"]
    transformada = pd.DataFrame(
        prep.transform(_filas([variables], version.metadatos)),
        columns=prep.get_feature_names_out())
    valores = explicador(transformada).values
    if valores.ndim == 3:
        valores = valores[:, :, 1]
    resultado = {}
    for nombre, valor in zip(transformada.columns, valores[0]):
        original, _ = _nombre_original(nombre)
        resultado[original] = resultado.get(original, 0.0) + float(valor)
    return resultado


def predecir(variables, version=None):
    version = version or modelo_activo()
    probabilidad = probabilidades([variables], version)[0]
    nivel = nivel_de(probabilidad, version.metadatos["limites_riesgo"])
    factores = [
        {
            "variable": nombre,
            "descripcion": DESCRIPCIONES.get(nombre, nombre),
            "valor": _valor_legible(variables.get(nombre)),
            "contribucion": round(c, 4),
            "efecto": "aumenta" if c > 0 else "reduce",
        }
        for nombre, c in sorted(contribuciones(variables, version).items(),
                                key=lambda x: -abs(x[1]))
        if abs(c) > 1e-6
    ][:8]
    return {"probabilidad": probabilidad, "nivel": nivel,
            "recomendacion": recomendacion_de(nivel),
            "factores": factores, "version": version}
