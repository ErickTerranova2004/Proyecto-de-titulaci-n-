"""Planificador de despliegue: estima el riesgo de escenarios alternativos.

Parte de un análisis guardado y cambia solo las condiciones que decide el
desarrollador (día, hora, reintento y pull request). El resto de variables
(commit e historial) quedan como en el análisis base. Nada se guarda.

El modelo usa la hora y el día en UTC; la pantalla trabaja en hora local
(settings.TIME_ZONE, America/Guayaquil = UTC−5).
"""

from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from django.conf import settings

from riesgo.services.predictor import (DESCRIPCIONES, contribuciones,
                                       nivel_de, predecir, probabilidades)

CONDICIONES = ("dia", "hora", "es_reintento", "tiene_pr")
# Franjas que se evalúan para las mejores ventanas (hora local).
HORAS_VENTANA = range(7, 21)
DIAS_VENTANA = 7
MAX_EXPLICACION = 8


def zona():
    return ZoneInfo(settings.TIME_ZONE)


def momento_base(prediccion):
    """Momento (UTC) al que corresponden hora_utc y dia_semana del análisis.

    Normalmente es creada_en; si el análisis se guardó justo después de un
    cambio de hora, se retrocede hasta la hora en que se calcularon.
    """
    creada = prediccion.creada_en.astimezone(timezone.utc)
    variables = prediccion.variables
    momento = creada
    for _ in range(24 * 7):
        if (momento.hour == variables.get("hora_utc", momento.hour)
                and momento.weekday() == variables.get("dia_semana",
                                                       momento.weekday())):
            return momento
        momento -= timedelta(hours=1)
    return creada


def condiciones_base(prediccion):
    local = momento_base(prediccion).astimezone(zona())
    return {"dia": local.weekday(), "hora": local.hour,
            "es_reintento": bool(prediccion.variables.get("es_reintento")),
            "tiene_pr": bool(prediccion.variables.get("tiene_pr"))}


def momento_escenario(base, dia, hora):
    """Próxima ocurrencia local de (día, hora) desde el momento base."""
    local = base.astimezone(zona())
    candidato = local.replace(hour=hora) + timedelta(
        days=(dia - local.weekday()) % 7)
    if candidato < local:
        candidato += timedelta(days=7)
    return candidato


def variables_escenario(variables, base, momento, es_reintento, tiene_pr):
    """Variables del análisis base con las condiciones del escenario."""
    utc = momento.astimezone(timezone.utc)
    desfase_min = (momento - base).total_seconds() / 60
    nuevas = dict(variables)
    nuevas.update({
        "hora_utc": utc.hour,
        "dia_semana": utc.weekday(),
        "fin_de_semana": int(utc.weekday() >= 5),
        "es_reintento": int(es_reintento),
        "tiene_pr": int(tiene_pr),
    })
    # Desplegar más tarde hace el commit y la última ejecución más antiguos.
    if nuevas.get("retraso_commit_run_min") is not None:
        nuevas["retraso_commit_run_min"] += desfase_min
    if nuevas.get("wf_horas_desde_ultimo") is not None:
        nuevas["wf_horas_desde_ultimo"] += desfase_min / 60
    return nuevas


def _resumen(probabilidad, version):
    return {"probabilidad": probabilidad,
            "nivel": nivel_de(probabilidad,
                              version.metadatos["limites_riesgo"])}


def estimar_escenario(prediccion, condiciones):
    version = prediccion.version_modelo
    base = momento_base(prediccion)
    momento = momento_escenario(base, condiciones["dia"], condiciones["hora"])
    variables = variables_escenario(
        prediccion.variables, base, momento, condiciones["es_reintento"],
        condiciones["tiene_pr"])
    resultado = predecir(variables, version)
    prob_base = probabilidades([prediccion.variables], version)[0]

    shap_base = contribuciones(prediccion.variables, version)
    shap_escenario = contribuciones(variables, version)
    diferencias = {v: shap_escenario.get(v, 0.0) - shap_base.get(v, 0.0)
                   for v in set(shap_base) | set(shap_escenario)}
    explicacion = [
        {"variable": v, "descripcion": DESCRIPCIONES.get(v, v),
         "diferencia": round(d, 4)}
        for v, d in sorted(diferencias.items(), key=lambda x: -abs(x[1]))
        if abs(d) > 1e-6][:MAX_EXPLICACION]

    return {
        "condiciones_base": condiciones_base(prediccion),
        "condiciones": condiciones,
        "base": _resumen(prob_base, version),
        "escenario": {**_resumen(resultado["probabilidad"], version),
                      "factores": resultado["factores"],
                      "momento_local": momento.isoformat()},
        "diferencia_puntos": round(
            (resultado["probabilidad"] - prob_base) * 100, 2),
        "explicacion": explicacion,
    }


def mejores_ventanas(prediccion, n=3):
    """Las n franjas de menor riesgo de los 7 días siguientes al análisis.

    Mantiene reintento y pull request del análisis base y devuelve como
    máximo una franja por día.
    """
    version = prediccion.version_modelo
    base = momento_base(prediccion)
    inicio = base.astimezone(zona())
    limite = inicio + timedelta(days=DIAS_VENTANA)
    reintento = bool(prediccion.variables.get("es_reintento"))
    pr = bool(prediccion.variables.get("tiene_pr"))

    momentos = [
        candidato
        for dias in range(DIAS_VENTANA + 1)
        for hora in HORAS_VENTANA
        if inicio < (candidato := (inicio + timedelta(days=dias)).replace(
            hour=hora)) <= limite]
    probs = probabilidades(
        [variables_escenario(prediccion.variables, base, m, reintento, pr)
         for m in momentos], version)

    ventanas, dias_usados = [], set()
    for prob, momento in sorted(zip(probs, momentos),
                                key=lambda x: (x[0], x[1])):
        if momento.date() in dias_usados:
            continue
        dias_usados.add(momento.date())
        ventanas.append({"momento_local": momento.isoformat(),
                         "dia": momento.weekday(), "hora": momento.hour,
                         "es_reintento": reintento, "tiene_pr": pr,
                         **_resumen(prob, version)})
        if len(ventanas) == n:
            break
    return {"condiciones_base": condiciones_base(prediccion),
            "ventanas": ventanas}
