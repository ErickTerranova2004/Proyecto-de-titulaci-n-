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
    "tiene_pr": "Ejecución asociada a un pull request",
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


def predecir(variables, version=None):
    version = version or modelo_activo()
    meta = version.metadatos
    modelo, base, explicador = _cargar(_ruta(version.archivo),
                                       _ruta(version.archivo_explicacion))
    columnas = meta["variables_categoricas"] + meta["variables_numericas"]
    fila = pd.DataFrame([{c: variables.get(c, np.nan) for c in columnas}])
    probabilidad = float(modelo.predict_proba(fila)[0, 1])

    limites = meta["limites_riesgo"]
    if probabilidad >= limites["alto"]:
        nivel = "alto"
    elif probabilidad >= limites["medio"]:
        nivel = "medio"
    else:
        nivel = "bajo"

    # SHAP sobre el modelo sin calibrar (misma ordenación de riesgo).
    prep = base.named_steps["prep"]
    transformada = pd.DataFrame(prep.transform(fila),
                                columns=prep.get_feature_names_out())
    valores = explicador(transformada).values
    if valores.ndim == 3:
        valores = valores[:, :, 1]
    contribuciones = {}
    for nombre, valor in zip(transformada.columns, valores[0]):
        original, _ = _nombre_original(nombre)
        contribuciones[original] = contribuciones.get(original, 0.0) + float(
            valor)
    factores = [
        {
            "variable": nombre,
            "descripcion": DESCRIPCIONES.get(nombre, nombre),
            "valor": _valor_legible(variables.get(nombre)),
            "contribucion": round(c, 4),
            "efecto": "aumenta" if c > 0 else "reduce",
        }
        for nombre, c in sorted(contribuciones.items(),
                                key=lambda x: -abs(x[1]))
        if abs(c) > 1e-6
    ][:8]
    return {"probabilidad": probabilidad, "nivel": nivel,
            "factores": factores, "version": version}
