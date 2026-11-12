"""Análisis explicado y recomendaciones generados con Gemini.

El nivel, la probabilidad y los factores siguen saliendo del modelo
entrenado (predictor.py); Gemini solo los interpreta junto con el contexto
del commit y redacta el análisis y las recomendaciones. Si no hay clave de
API o la llamada falla, se usan las reglas de recomendaciones.py.
"""

import json
import logging
import math

import httpx
from django.conf import settings
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from riesgo.services.recomendaciones import recomendar

logger = logging.getLogger(__name__)

MAX_MENSAJE = 2000
MAX_ARCHIVOS = 40

SISTEMA = """\
Eres un ingeniero DevOps que asiste a un equipo de desarrollo antes de un \
despliegue con GitHub Actions. Recibes el resultado de un modelo de \
aprendizaje automático (LightGBM calibrado) que estimó la probabilidad de \
que el despliegue no se complete, los factores que más influyeron según \
SHAP y el contexto del commit y de las ejecuciones previas del workflow.

Reglas:
- El nivel de riesgo y la probabilidad son del modelo validado: no los \
recalcules ni los contradigas. Explícalos.
- Apóyate solo en los datos recibidos. Si falta información (por ejemplo, \
no hay ejecuciones previas), dilo en lugar de suponer.
- "resumen": 2 a 4 frases en español, para un desarrollador, que expliquen \
por qué el modelo asignó ese nivel y qué pesa más.
- "recomendaciones": de 1 a 5 acciones concretas y verificables antes de \
desplegar, ordenadas por prioridad. En "variable" indica el nombre exacto \
de la variable del modelo en la que se basa cada una, o null si se basa \
en el contexto del commit.
"""


class Recomendacion(BaseModel):
    variable: str | None
    texto: str


class Analisis(BaseModel):
    resumen: str
    recomendaciones: list[Recomendacion]


def _limpio(valor):
    if isinstance(valor, float) and math.isnan(valor):
        return None
    return valor


def _contexto(variables, resultado, contexto, repositorio, workflow_path,
              rama, evento):
    commit = contexto["commit"]
    info = commit.get("commit") or {}
    archivos = commit.get("files") or []
    return {
        "despliegue": {"repositorio": repositorio, "workflow": workflow_path,
                       "rama": rama, "evento": evento},
        "modelo": {
            "version": resultado["version"].version,
            "probabilidad_no_completado": round(resultado["probabilidad"], 4),
            "nivel": resultado["nivel"],
            "limites_nivel": resultado["version"].metadatos.get(
                "limites_riesgo"),
            "factores_shap": resultado["factores"],
        },
        "variables": {k: _limpio(v) for k, v in variables.items()},
        # El autor no se envía: la plataforma solo guarda su hash.
        "commit": {
            "sha": commit.get("sha"),
            "mensaje": (info.get("message") or "")[:MAX_MENSAJE],
            "estadisticas": commit.get("stats"),
            "archivos": [{"nombre": a.get("filename"),
                          "estado": a.get("status"),
                          "cambios": a.get("changes")}
                         for a in archivos[:MAX_ARCHIVOS]],
            "archivos_omitidos": max(len(archivos) - MAX_ARCHIVOS, 0),
        },
        "ejecuciones_previas_workflow": [
            {"inicio": e.get("run_started_at"),
             "conclusion": e.get("conclusion"),
             "rama": e.get("head_branch"), "evento": e.get("event")}
            for e in contexto["previas"]],
    }


def _por_reglas(variables, factores, error=None):
    return {"origen": "reglas", "modelo": None, "resumen": "",
            "error": error}, recomendar(variables, factores)


def analizar(variables, resultado, contexto, repositorio, workflow_path,
             rama, evento):
    """Devuelve (analisis_ia, recomendaciones).

    analisis_ia: {"origen", "modelo", "resumen", "error"}.
    recomendaciones: lista de {"codigo", "variable", "texto"}.
    """
    if not settings.GEMINI_API_KEY:
        return _por_reglas(variables, resultado["factores"])

    datos = _contexto(variables, resultado, contexto, repositorio,
                      workflow_path, rama, evento)
    cliente = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(
            timeout=settings.IA_TIMEOUT * 1000,
            # 429/503 por alta demanda suelen durar pocos segundos.
            retry_options=types.HttpRetryOptions(
                attempts=2, initial_delay=2, max_delay=10,
                http_status_codes=[429, 500, 503, 504])))
    try:
        respuesta = cliente.models.generate_content(
            model=settings.GEMINI_MODELO,
            contents=json.dumps(datos, ensure_ascii=False, default=str),
            config=types.GenerateContentConfig(
                system_instruction=SISTEMA,
                response_mime_type="application/json",
                response_schema=Analisis),
        )
    # httpx.HTTPError: tiempo agotado o conexión cortada (no es OSError).
    except (errors.APIError, httpx.HTTPError, OSError) as exc:
        logger.warning("Gemini no disponible, se usan reglas: %s", exc)
        return _por_reglas(variables, resultado["factores"],
                           type(exc).__name__)

    analisis = respuesta.parsed
    if not isinstance(analisis, Analisis):
        motivo = (str(respuesta.candidates[0].finish_reason)
                  if respuesta.candidates else "sin_respuesta")
        logger.warning("Gemini no devolvió un análisis (%s), se usan reglas",
                       motivo)
        return _por_reglas(variables, resultado["factores"], motivo)

    recomendaciones = [
        {"codigo": f"IA{i:02d}", "variable": r.variable, "texto": r.texto}
        for i, r in enumerate(analisis.recomendaciones, start=1)]
    return ({"origen": "ia",
             "modelo": respuesta.model_version or settings.GEMINI_MODELO,
             "resumen": analisis.resumen, "error": None},
            recomendaciones or recomendar(variables, resultado["factores"]))
