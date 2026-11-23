"""Análisis explicado y recomendaciones redactados con IA.

El nivel, la probabilidad, los factores SHAP y la recomendación siguen
saliendo del modelo entrenado (predictor.py); la IA solo los interpreta
junto con el contexto del commit y redacta el resumen y las recomendaciones
(IA01, IA02…). Proveedor: settings.IA_PROVEEDOR = claude (por defecto) |
gemini | reglas. Sin la clave del proveedor, o si la llamada falla, tarda más
de IA_TIMEOUT segundos o no devuelve un análisis válido, se usan las reglas
de recomendaciones.py: nunca un error 500.
"""

import json
import logging
import math
import time

import anthropic
import httpx
from django.conf import settings
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from riesgo.services.recomendaciones import recomendar

logger = logging.getLogger(__name__)

MAX_MENSAJE = 2000
MAX_ARCHIVOS = 40
# Cota de la respuesta (razonamiento incluido); el JSON ocupa unos cientos.
MAX_TOKENS_CLAUDE = 8000

SISTEMA = """\
Eres un ingeniero DevOps que asiste a un equipo de desarrollo antes de un \
despliegue con GitHub Actions. Recibes el resultado de un modelo de \
aprendizaje automático entrenado con despliegues reales, que estimó la \
probabilidad de que el despliegue no se complete, los factores que más \
influyeron según SHAP y el contexto del commit y de las ejecuciones previas \
del workflow.

Reglas:
- El nivel de riesgo y la probabilidad son del modelo validado: no los \
recalcules ni los contradigas. Explícalos.
- "contribucion" de cada factor SHAP está en puntos de probabilidad del modelo (0.05 = 5 puntos): positivo sube el riesgo y negativo lo baja. No hables de log-odds; si no citas el valor, di solo si el factor sube o baja el riesgo.
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


def _con_analisis(analisis, modelo, variables, factores):
    recomendaciones = [
        {"codigo": f"IA{i:02d}", "variable": r.variable, "texto": r.texto}
        for i, r in enumerate(analisis.recomendaciones, start=1)]
    return ({"origen": "ia", "modelo": modelo, "resumen": analisis.resumen,
             "error": None},
            recomendaciones or recomendar(variables, factores))


def analizar(variables, resultado, contexto, repositorio, workflow_path,
             rama, evento):
    """Devuelve (analisis_ia, recomendaciones).

    analisis_ia: {"origen", "modelo", "resumen", "error"} y, con Claude,
    "uso": {"tokens_entrada", "tokens_salida", "duracion_s"}.
    recomendaciones: lista de {"codigo", "variable", "texto"}.
    """
    proveedor = settings.IA_PROVEEDOR
    if proveedor == "claude" and settings.CLAUDE_API_KEY:
        redactar = _con_claude
    elif proveedor == "gemini" and settings.GEMINI_API_KEY:
        redactar = _con_gemini
    else:
        return _por_reglas(variables, resultado["factores"])
    datos = _contexto(variables, resultado, contexto, repositorio,
                      workflow_path, rama, evento)
    return redactar(datos, variables, resultado["factores"])


def _con_claude(datos, variables, factores):
    # Clave explícita (no se lee ANTHROPIC_API_KEY). Sin reintentos: así la
    # espera nunca supera IA_TIMEOUT y, si falla, el análisis sale por reglas.
    cliente = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY,
                                  timeout=float(settings.IA_TIMEOUT),
                                  max_retries=0)
    inicio = time.monotonic()
    try:
        respuesta = cliente.messages.parse(
            model=settings.CLAUDE_MODELO,
            max_tokens=MAX_TOKENS_CLAUDE,
            system=SISTEMA,
            # Redactar un resumen corto no necesita razonar a fondo.
            output_config={"effort": "low"},
            output_format=Analisis,
            messages=[{"role": "user", "content": json.dumps(
                datos, ensure_ascii=False, default=str)}],
        )
    except anthropic.APIError as exc:
        # Incluye tiempo agotado, conexión, 4xx y 5xx.
        logger.warning("Claude no disponible, se usan reglas: %s",
                       type(exc).__name__)
        return _por_reglas(variables, factores, type(exc).__name__)
    except ValueError as exc:
        # JSON incompleto o que no cumple el esquema (p. ej. max_tokens).
        logger.warning("Claude devolvió un análisis no válido: %s", exc)
        return _por_reglas(variables, factores, "respuesta_no_valida")

    analisis = respuesta.parsed_output
    if respuesta.stop_reason == "refusal" or not isinstance(analisis, Analisis):
        logger.warning("Claude no devolvió un análisis (%s), se usan reglas",
                       respuesta.stop_reason)
        return _por_reglas(variables, factores,
                           respuesta.stop_reason or "sin_respuesta")
    uso = respuesta.usage
    logger.info("Análisis con %s: %s tokens de entrada, %s de salida",
                respuesta.model, uso.input_tokens, uso.output_tokens)
    resultado, recomendaciones = _con_analisis(
        analisis, respuesta.model or settings.CLAUDE_MODELO, variables, factores)
    # Consumo de la llamada, guardado con el análisis (jsn_analisis_ia).
    resultado["uso"] = {"tokens_entrada": uso.input_tokens,
                        "tokens_salida": uso.output_tokens,
                        "duracion_s": round(time.monotonic() - inicio, 2)}
    return resultado, recomendaciones


def _con_gemini(datos, variables, factores):
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
        return _por_reglas(variables, factores, type(exc).__name__)

    analisis = respuesta.parsed
    if not isinstance(analisis, Analisis):
        motivo = (str(respuesta.candidates[0].finish_reason)
                  if respuesta.candidates else "sin_respuesta")
        logger.warning("Gemini no devolvió un análisis (%s), se usan reglas",
                       motivo)
        return _por_reglas(variables, factores, motivo)
    return _con_analisis(analisis,
                         respuesta.model_version or settings.GEMINI_MODELO,
                         variables, factores)
