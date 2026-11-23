"""Planificador de despliegue: estima el riesgo de escenarios alternativos.

Parte de un análisis guardado y cambia solo las condiciones que decide el
desarrollador (fecha, hora, reintento y pull request). Nada se guarda: ni el
análisis base ni el modelo cambian.

El escenario es un momento concreto (fecha y hora en punto, hora local) a
partir de la hora actual. Las variables que dependen del momento del
despliegue se recalculan para ese momento:

- hora_utc, dia_semana y fin_de_semana: del momento en UTC (lo que usa el
  modelo; la pantalla trabaja en settings.TIME_ZONE, America/Guayaquil).
- retraso_commit_run_min: minutos entre la fecha del commit (Commit.fecha) y
  el momento, como en features.variables_commit (nunca negativo).
- wf_horas_desde_ultimo: horas entre el inicio de la última ejecución previa
  usada por el análisis y el momento, como en features.variables_workflow.

Si falta la fecha del commit o de la ejecución previa, se desplaza el valor
guardado con la diferencia entre el momento del escenario y el del análisis
base (mismo resultado salvo el recorte a cero). El resto del historial
(ejecuciones, fallos, checks y pull requests que ocurran hasta ese momento)
no se conoce de antemano y queda como en el análisis base.
"""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone as dj_timezone

from riesgo.services.predictor import (DESCRIPCIONES, contribuciones,
                                       nivel_de, predecir, probabilidades)

# Franja que se evalúa en las mejores ventanas (hora local, ambas incluidas).
HORAS_VENTANA = range(7, 21)
# Días hacia adelante que admite un escenario o la lista de ventanas.
MAX_DIAS = 14
MAX_EXPLICACION = 8
VARIABLES_TIEMPO = ("hora_utc", "dia_semana", "fin_de_semana",
                    "retraso_commit_run_min", "wf_horas_desde_ultimo")


def zona():
    return ZoneInfo(settings.TIME_ZONE)


def ahora():
    """Momento actual (separado para poder fijarlo en las pruebas)."""
    return dj_timezone.now()


def hoy_local():
    return ahora().astimezone(zona()).date()


def momento_local(fecha, hora):
    """Fecha y hora en punto locales como datetime con zona."""
    return datetime.combine(fecha, time(hora), tzinfo=zona())


def momento_base(prediccion):
    """Momento (UTC) al que corresponden hora_utc y dia_semana del análisis.

    En los análisis en lote es momento_variables. En los interactivos es
    creada_en; si el análisis se guardó justo después de un cambio de hora,
    se retrocede hasta la hora en que se calcularon.
    """
    fijado = getattr(prediccion, "momento_variables", None)
    if fijado:
        return fijado.astimezone(timezone.utc)
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
    """Día, hora y condiciones del análisis base (hora local), para mostrar."""
    local = momento_base(prediccion).astimezone(zona())
    return {"fecha": local.date().isoformat(), "dia": local.weekday(),
            "hora": local.hour,
            "es_reintento": bool(prediccion.variables.get("es_reintento")),
            "tiene_pr": bool(prediccion.variables.get("tiene_pr"))}


def referencias(prediccion):
    """Fechas guardadas que permiten recalcular las variables de tiempo."""
    commit = getattr(prediccion, "commit", None)
    fecha_commit = getattr(commit, "fecha", None)
    ultima_previa = None
    previas = getattr(prediccion, "ejecuciones_previas", None)
    if previas is not None and hasattr(previas, "all"):
        inicios = [e.iniciada_en for e in previas.all() if e.iniciada_en]
        ultima_previa = max(inicios) if inicios else None
    return {"fecha_commit": fecha_commit, "ultima_previa": ultima_previa}


def variables_escenario(variables, base, momento, es_reintento, tiene_pr,
                        fecha_commit=None, ultima_previa=None):
    """Variables del análisis base con las condiciones del escenario.

    Las de tiempo se recalculan para `momento`; las demás no cambian.
    """
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
    if nuevas.get("retraso_commit_run_min") is not None:
        if fecha_commit is not None:
            minutos = (momento - fecha_commit).total_seconds() / 60
        else:
            minutos = nuevas["retraso_commit_run_min"] + desfase_min
        nuevas["retraso_commit_run_min"] = max(minutos, 0)
    if nuevas.get("wf_horas_desde_ultimo") is not None:
        if ultima_previa is not None:
            nuevas["wf_horas_desde_ultimo"] = (
                (momento - ultima_previa).total_seconds() / 3600)
        else:
            nuevas["wf_horas_desde_ultimo"] += desfase_min / 60
    return nuevas


def _variables_en(prediccion, momento, es_reintento, tiene_pr, refs=None):
    refs = refs if refs is not None else referencias(prediccion)
    return variables_escenario(prediccion.variables, momento_base(prediccion),
                               momento, es_reintento, tiene_pr, **refs)


def _resumen(probabilidad, version):
    return {"probabilidad": probabilidad,
            "nivel": nivel_de(probabilidad,
                              version.metadatos["limites_riesgo"])}


def _modelo(version):
    return {"version": version.version, "nombre": version.nombre_modelo}


def _tiempo(variables):
    return {v: variables.get(v) for v in VARIABLES_TIEMPO}


def estimar_escenario(prediccion, condiciones, version=None):
    """`condiciones`: fecha (date), hora local, es_reintento y tiene_pr.
    `version`: modelo con el que se estima (por defecto, el del análisis
    base); la base se recalcula con ese mismo modelo."""
    version = version or prediccion.version_modelo
    momento = momento_local(condiciones["fecha"], condiciones["hora"])
    variables = _variables_en(prediccion, momento, condiciones["es_reintento"],
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
        "modelo": _modelo(version),
        "condiciones_base": condiciones_base(prediccion),
        "condiciones": {**condiciones,
                        "fecha": condiciones["fecha"].isoformat(),
                        "dia": condiciones["fecha"].weekday()},
        "base": _resumen(prob_base, version),
        "escenario": {**_resumen(resultado["probabilidad"], version),
                      "factores": resultado["factores"],
                      "momento_local": momento.isoformat()},
        "diferencia_puntos": round(
            (resultado["probabilidad"] - prob_base) * 100, 2),
        "variables_tiempo": {"base": _tiempo(prediccion.variables),
                             "escenario": _tiempo(variables)},
        "explicacion": explicacion,
    }


def mejores_ventanas(prediccion, dias=None, version=None):
    """La hora de menor riesgo de cada uno de los próximos `dias` días.

    Empieza mañana (hora local), evalúa de 07:00 a 20:00 y mantiene
    reintento y pull request del análisis base. Las ventanas van en orden
    cronológico; `mejor` marca la de menor riesgo (la primera si empatan).
    """
    dias = dias or settings.PLANIFICADOR_DIAS_VENTANAS
    version = version or prediccion.version_modelo
    prob_base = probabilidades([prediccion.variables], version)[0]
    reintento = bool(prediccion.variables.get("es_reintento"))
    pr = bool(prediccion.variables.get("tiene_pr"))
    refs = referencias(prediccion)
    desde = hoy_local() + timedelta(days=1)

    ventanas = []
    for n in range(dias):
        fecha = desde + timedelta(days=n)
        momentos = [momento_local(fecha, h) for h in HORAS_VENTANA]
        probs = probabilidades(
            [_variables_en(prediccion, m, reintento, pr, refs)
             for m in momentos], version)
        prob, momento = min(zip(probs, momentos), key=lambda x: (x[0], x[1]))
        ventanas.append({"momento_local": momento.isoformat(),
                         "fecha": fecha.isoformat(),
                         "dia": fecha.weekday(), "hora": momento.hour,
                         "es_reintento": reintento, "tiene_pr": pr,
                         "mejor": False,
                         "diferencia_puntos": round((prob - prob_base) * 100,
                                                    2),
                         **_resumen(prob, version)})
    if ventanas:
        min(ventanas, key=lambda v: v["probabilidad"])["mejor"] = True
    return {"modelo": _modelo(version),
            "condiciones_base": condiciones_base(prediccion),
            "base": _resumen(prob_base, version),
            "desde": desde.isoformat(), "dias": dias,
            "ventanas": ventanas}


def validar_momento(fecha, hora):
    """Mensaje si el momento no se puede estimar; "" si es válido.

    Se admite desde la hora en curso hasta MAX_DIAS días después de hoy.
    """
    actual = ahora().astimezone(zona()).replace(minute=0, second=0,
                                                microsecond=0)
    momento = momento_local(fecha, hora)
    if momento < actual:
        return "El escenario debe ser a partir de la hora actual."
    if fecha > actual.date() + timedelta(days=MAX_DIAS):
        return f"El escenario no puede estar a más de {MAX_DIAS} días."
    return ""
