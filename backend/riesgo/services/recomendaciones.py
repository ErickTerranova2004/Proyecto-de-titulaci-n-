"""Recomendaciones basadas en reglas.

Solo se generan para factores que aumentan el riesgo según SHAP, y cada
regla se apoya en una observación del análisis de datos (informes/). Cada
recomendación guarda el código de la regla que la generó.
"""

import math


def _hay(valor):
    return valor is not None and not (isinstance(valor, float)
                                      and math.isnan(valor))


# variable → (código, condición, texto)
REGLAS = {
    "wf_tasa_fallo_prev": (
        "R01_HISTORIAL_FALLOS_WORKFLOW",
        lambda v: _hay(v.get("wf_tasa_fallo_prev"))
        and v["wf_tasa_fallo_prev"] > 0,
        "Las ejecuciones recientes de este workflow han fallado. Revise y "
        "corrija la causa antes de desplegar: el historial de fallos es el "
        "factor más asociado a despliegues no completados."),
    "wf_ultimo_fallo": (
        "R02_ULTIMA_EJECUCION_FALLIDA",
        lambda v: v.get("wf_ultimo_fallo") == 1,
        "La última ejecución del workflow falló. Confirme que el problema "
        "se resolvió (secretos, permisos, infraestructura) antes de "
        "relanzar."),
    "repo_tasa_fallo_prev": (
        "R03_FALLOS_REPOSITORIO",
        lambda v: _hay(v.get("repo_tasa_fallo_prev"))
        and v["repo_tasa_fallo_prev"] > 0.2,
        "El repositorio tiene una tasa de fallos reciente elevada en sus "
        "workflows. Verifique que la compilación y las pruebas pasan en "
        "la rama antes de desplegar."),
    "wf_n_prev": (
        "R04_SIN_HISTORIAL",
        lambda v: v.get("wf_n_prev", 0) == 0,
        "No hay ejecuciones previas de este workflow: la estimación tiene "
        "menos información. Considere desplegar primero en un entorno de "
        "staging."),
    "retraso_commit_run_min": (
        "R05_COMMIT_ANTIGUO",
        lambda v: _hay(v.get("retraso_commit_run_min"))
        and v["retraso_commit_run_min"] > 7 * 24 * 60,
        "El commit tiene más de una semana. Compruebe que las dependencias "
        "y la infraestructura no cambiaron desde entonces."),
    "msg_deps": (
        "R06_ACTUALIZACION_DEPENDENCIAS",
        lambda v: v.get("msg_deps") == 1,
        "El cambio actualiza dependencias: revise las notas de versión y "
        "ejecute las pruebas completas."),
}

GENERICA = {
    "codigo": "R00_SIN_FACTORES_DESTACADOS",
    "variable": None,
    "texto": "No se identificaron factores de riesgo destacados. Siga el "
             "procedimiento habitual de despliegue y verificación.",
}


def recomendar(variables, factores):
    recomendaciones = []
    for factor in factores:
        regla = REGLAS.get(factor["variable"])
        if factor["efecto"] != "aumenta" or regla is None:
            continue
        codigo, condicion, texto = regla
        if condicion(variables) and all(r["codigo"] != codigo
                                        for r in recomendaciones):
            recomendaciones.append({"codigo": codigo,
                                    "variable": factor["variable"],
                                    "texto": texto})
    return recomendaciones or [GENERICA]
