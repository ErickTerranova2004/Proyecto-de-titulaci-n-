"""Análisis en lote de ejecuciones posteriores a la fecha de corte.

Validación prospectiva del modelo activo: para cada ejecución terminada de un
workflow registrado que empezó después de la ejecución más reciente del
entrenamiento (metadatos.fecha_corte), se calculan las variables en el
momento en que empezó, solo con lo que existía antes (la misma función y las
mismas consultas que scripts/construir_dataset_v2.py), se predice con el
modelo activo y se etiqueta su resultado real con la API de jobs, igual que
el botón «Verificar resultado real».

Las ejecuciones que aún no han terminado se cuentan como pendientes y se
analizan al volver a ejecutar el lote. Solo lectura de la API de GitHub; no se
guardan las ejecuciones históricas usadas para calcular las variables (solo
la ejecución evaluada).

Listado incremental (SeguimientoLote): cada pasada lista las ejecuciones
creadas desde la pasada anterior menos 48 h (redondeado al inicio del día,
para que la URL no cambie y sirva el ETag) y consulta una a una las que
quedaron pendientes. Se salta las ejecuciones ya enlazadas a un análisis
interactivo del mismo modelo, para no contar dos veces el mismo despliegue en
la supervisión. Cada pasada también enlaza el resultado real de los análisis
interactivos pendientes (verificar_interactivos).
"""

import math
from datetime import datetime, timedelta, timezone

import requests
from django.db import transaction
from django.utils import timezone as dj_timezone

from riesgo.models import Prediccion, SeguimientoLote
from riesgo.services import github
from riesgo.services.analisis_ia import _por_reglas
from riesgo.services.features import (PARAMS_CHECKS, PARAMS_PULLS, fecha,
                                      variables_desde_datos)
from riesgo.services.github import GitHubClient
from riesgo.services.predictor import predecir
from riesgo.services.trazabilidad import guardar_commit, guardar_ejecucion
from riesgo.services.verificacion import enlazar_resultado, etiquetar_run

PREVIAS_WORKFLOW = 4  # features.MAX_PREVIAS_WORKFLOW
PREVIAS_REPO = 100  # features.MAX_PREVIAS_REPO
VENTANAS_DIAS = (7, 30, 90, 180)
MAX_RESULTADOS = 1000  # límite de la API con el filtro `created`
CONCLUSIONES_ANALIZADAS = ("success", "failure")
CAMPOS_RUN = ("id", "run_attempt", "status", "conclusion", "event",
              "head_branch", "head_sha", "workflow_id", "check_suite_id",
              "run_started_at", "created_at", "updated_at")
SOLAPE = timedelta(hours=48)
POR_PAGINA = 100
DIAS_INTERACTIVOS = 30


class SesionContada(requests.Session):
    """Cuenta las peticiones reales a GitHub (las de la caché no cuentan).

    `llamadas` son las que gastan cuota; las respuestas 304 de una petición
    condicional no la gastan y se cuentan aparte en `sin_cambios`.
    """

    llamadas = 0
    sin_cambios = 0

    def get(self, *args, **kwargs):
        respuesta = super().get(*args, **kwargs)
        if respuesta.status_code == 304:
            self.sin_cambios += 1
        else:
            self.llamadas += 1
        return respuesta


def cliente_contado():
    return GitHubClient(sesion=SesionContada())


def iso(momento):
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resumir(run):
    return {k: run.get(k) for k in CAMPOS_RUN}


def listar(gh, ruta, desde, hasta):
    """Ejecuciones creadas en [desde, hasta] (divide el intervalo si supera el
    máximo de resultados de la API)."""
    params = {"created": f"{iso(desde)}..{iso(hasta)}", "per_page": 100}
    primera = gh.get(ruta, dict(params, page=1)) or {}
    total = primera.get("total_count", 0)
    if total > MAX_RESULTADOS and hasta - desde > timedelta(minutes=10):
        mitad = desde + (hasta - desde) / 2
        return (listar(gh, ruta, desde, mitad)
                + listar(gh, ruta, mitad + timedelta(seconds=1), hasta))
    runs = list(primera.get("workflow_runs", []))
    pagina = 2
    while len(runs) < min(total, MAX_RESULTADOS):
        nuevos = (gh.get(ruta, dict(params, page=pagina)) or {}).get(
            "workflow_runs", [])
        if not nuevos:
            break
        runs += nuevos
        pagina += 1
    return [resumir(r) for r in runs]


def historial(gh, ruta, primer_momento, ultimo_momento, minimo):
    """Ejecuciones desde antes del primer momento hasta el último, ampliando
    la ventana hasta tener `minimo` previas al primer momento."""
    for dias in VENTANAS_DIAS:
        runs = listar(gh, ruta, primer_momento - timedelta(days=dias),
                      ultimo_momento + timedelta(minutes=1))
        if sum(fecha(r["created_at"]) < primer_momento for r in runs) >= minimo:
            break
    unicos = {r["id"]: r for r in runs}
    return sorted(unicos.values(), key=lambda r: r["run_started_at"] or "")


class DatosCommit:
    """Commit, pull requests y checks de cada commit (una consulta por sha)."""

    def __init__(self, gh, repo):
        self.gh, self.repo, self.cache = gh, repo, {}

    def __call__(self, sha):
        if sha not in self.cache:
            base = f"/repos/{self.repo}/commits/{sha}"
            self.cache[sha] = (
                self.gh.get(base) or {},
                self.gh.get(f"{base}/pulls", PARAMS_PULLS) or [],
                (self.gh.get(f"{base}/check-runs", PARAMS_CHECKS) or {}).get(
                    "check_runs", []))
        return self.cache[sha]


def variables_ejecucion(gh, repo, run, runs_wf, runs_repo, datos_commit):
    """Variables de una ejecución con su inicio como momento del despliegue."""
    momento = fecha(run["run_started_at"])
    anteriores = [resumir(gh.get(
        f"/repos/{repo}/actions/runs/{run['id']}/attempts/{n}") or {})
        for n in range(1, run.get("run_attempt") or 1)]
    commit, pulls, checks = datos_commit(run["head_sha"])
    mismo_commit = [r for r in runs_wf
                    if r["head_sha"] == run["head_sha"]] + anteriores
    variables = variables_desde_datos(
        commit, run.get("head_branch") or "", run.get("event") or "", momento,
        runs_wf + anteriores, runs_repo + anteriores, mismo_commit, pulls,
        checks, intento=run.get("run_attempt") or 1, run_id=run["id"])
    return variables, commit


# --- Listado incremental ----------------------------------------------------

def inicio_listado(corte, seguimiento):
    """Desde cuándo listar: la pasada anterior menos 48 h, al inicio del día
    (la misma URL todo el día, para el ETag), nunca antes del corte."""
    if seguimiento is None:
        return corte
    desde = (seguimiento.listado_hasta - SOLAPE).astimezone(timezone.utc)
    return max(corte, desde.replace(hour=0, minute=0, second=0,
                                    microsecond=0))


def posterior_al_corte(run, corte):
    # Sin run_started_at todavía (en cola): se sigue como pendiente.
    return (not run.get("run_started_at")
            or fecha(run["run_started_at"]) > corte)


def listar_nuevas(gh, workflow, desde, etag=""):
    """Ejecuciones del workflow creadas desde `desde`.

    Devuelve (runs, etag); runs es None si la primera página no ha cambiado
    (304). El ETag solo se conserva si el listado cabe en una página: un
    cambio en otra página no alteraría el de la primera.
    """
    repo = workflow.repositorio.nombre_completo
    archivo = workflow.path.rsplit("/", 1)[-1]
    ruta = f"/repos/{repo}/actions/workflows/{archivo}/runs"
    params = {"created": f">={iso(desde)}", "per_page": POR_PAGINA}
    primera, etag = gh.get_condicional(ruta, dict(params, page=1), etag)
    if primera is None:
        return None, etag
    total = primera.get("total_count", 0)
    if total > MAX_RESULTADOS:
        return listar(gh, ruta, desde, datetime.now(timezone.utc)
                      + timedelta(minutes=1)), ""
    runs = list(primera.get("workflow_runs", []))
    pagina = 2
    while len(runs) < total:
        nuevos = (gh.get(ruta, dict(params, page=pagina)) or {}).get(
            "workflow_runs", [])
        if not nuevos:
            break
        runs += nuevos
        pagina += 1
    return [resumir(r) for r in runs], (etag if total <= POR_PAGINA else "")


def consultar_runs(gh, repo, ids):
    """Estado actual de ejecuciones concretas (las que quedaron pendientes)."""
    runs = []
    for run_id in ids:
        try:
            runs.append(resumir(gh.get(f"/repos/{repo}/actions/runs/{run_id}")))
        except github.NoEncontrado:
            pass  # borrada en GitHub: ya no hay nada que seguir
    return runs


def clasificar(runs, analizadas):
    """Separa las ejecuciones en a analizar, pendientes y no analizables."""
    nuevas = [r for r in runs if r["id"] not in analizadas]
    terminadas = [r for r in nuevas if r.get("status") == "completed"]
    return {
        "analizar": [r for r in terminadas
                     if r.get("conclusion") in CONCLUSIONES_ANALIZADAS],
        "pendientes": [r for r in nuevas if r.get("status") != "completed"],
        "no_analizables": [r for r in terminadas
                           if r.get("conclusion") not in CONCLUSIONES_ANALIZADAS],
        "ya_analizadas": len(runs) - len(nuevas),
    }


def run_ids_analizados(workflow, version):
    """(ya analizadas en lote, enlazadas a un análisis interactivo del mismo
    modelo y no analizadas en lote).

    Las segundas no se analizan en lote: ese despliegue ya cuenta en la
    supervisión con la predicción hecha antes de que ocurriera.
    """
    enlazadas = Prediccion.objects.filter(workflow=workflow,
                                          ejecucion_real__isnull=False)
    lote_ids = set(enlazadas.filter(origen="lote").values_list(
        "ejecucion_real__run_id", flat=True))
    interactivas = set(enlazadas.filter(
        origen="interactivo", version_modelo=version).values_list(
        "ejecucion_real__run_id", flat=True))
    return lote_ids, interactivas - lote_ids


def revisar_workflow(gh, workflow, corte, version):
    """Ejecuciones que hay que mirar en esta pasada, clasificadas.

    Devuelve (grupos, estado); `estado` se guarda en SeguimientoLote solo si
    la pasada del workflow termina bien.
    """
    inicio = dj_timezone.now()
    seguimiento = SeguimientoLote.objects.filter(workflow=workflow).first()
    desde = inicio_listado(corte, seguimiento)
    clave = iso(desde)
    etag_previo = (seguimiento.etag if seguimiento
                   and seguimiento.etag_params == clave else "")
    runs, etag = listar_nuevas(gh, workflow, desde, etag_previo)
    previas = seguimiento.pendientes if seguimiento else []
    sin_cambios = runs is None
    if sin_cambios:
        # Nada cambió desde `desde`: solo las pendientes anteriores a la
        # ventana pueden haber terminado.
        runs = []
        consultar = [p for p in previas if fecha(p["creada"]) < desde]
        conservar = [p for p in previas if fecha(p["creada"]) >= desde]
    else:
        vistas = {r["id"] for r in runs}
        consultar = [p for p in previas if p["id"] not in vistas]
        conservar = []
    repo = workflow.repositorio.nombre_completo
    runs += consultar_runs(gh, repo, [p["id"] for p in consultar])
    runs = [r for r in runs if posterior_al_corte(r, corte)]
    lote_ids, interactivas = run_ids_analizados(workflow, version)
    grupos = clasificar(runs, lote_ids | interactivas)
    grupos["enlazadas_interactivo"] = sum(r["id"] in interactivas
                                          for r in runs)
    grupos["sin_cambios"] = int(sin_cambios)
    pendientes = conservar + [{"id": r["id"], "creada": r.get("created_at")}
                              for r in grupos["pendientes"]]
    estado = {"listado_hasta": inicio, "pendientes": pendientes,
              "etag": etag, "etag_params": clave if etag else ""}
    return grupos, estado


def guardar_estado(workflow, estado):
    SeguimientoLote.objects.update_or_create(workflow=workflow,
                                             defaults=estado)


def resumen_grupos(grupos, analizadas=None):
    resumen = {k: (len(v) if isinstance(v, list) else v)
               for k, v in grupos.items()}
    if analizadas is not None:
        del resumen["analizar"]
        resumen = {"analizadas": analizadas, **resumen}
    return resumen


def _json_seguro(variables):
    return {k: (None if isinstance(v, float) and math.isnan(v) else v)
            for k, v in variables.items()}


def analizar_workflow(gh, workflow, corte, version, usuario):
    """Analiza y verifica las ejecuciones terminadas posteriores al corte.

    Devuelve el resumen del workflow y la lista de predicciones creadas. El
    estado del listado incremental solo se guarda si todo terminó bien (si
    falla, la pasada siguiente vuelve a mirar la misma ventana).
    """
    repo = workflow.repositorio.nombre_completo
    grupos, estado = revisar_workflow(gh, workflow, corte, version)
    creadas = []
    if grupos["analizar"]:
        momentos = [fecha(r["run_started_at"]) for r in grupos["analizar"]]
        archivo = workflow.path.rsplit("/", 1)[-1]
        runs_wf = historial(gh, f"/repos/{repo}/actions/workflows/{archivo}/runs",
                            min(momentos), max(momentos), PREVIAS_WORKFLOW)
        runs_repo = historial(gh, f"/repos/{repo}/actions/runs",
                              min(momentos), max(momentos), PREVIAS_REPO)
        datos_commit = DatosCommit(gh, repo)
        for run in sorted(grupos["analizar"], key=lambda r: r["run_started_at"]):
            creadas.append(_analizar_run(gh, workflow, run, runs_wf, runs_repo,
                                         datos_commit, version, usuario))
    guardar_estado(workflow, estado)
    return resumen_grupos(grupos, analizadas=len(creadas)), creadas


def _analizar_run(gh, workflow, run, runs_wf, runs_repo, datos_commit,
                  version, usuario):
    repo = workflow.repositorio.nombre_completo
    variables, commit_api = variables_ejecucion(gh, repo, run, runs_wf,
                                                runs_repo, datos_commit)
    resultado = predecir(variables, version)
    analisis, recomendaciones = _por_reglas(variables, resultado["factores"])
    jobs = gh.jobs_intento(repo, run["id"], run.get("run_attempt") or 1)
    etiqueta = etiquetar_run(gh, workflow, run, jobs)
    ahora = dj_timezone.now()
    with transaction.atomic():
        commit = guardar_commit(workflow.repositorio, run["head_sha"],
                                commit_api)
        ejecucion = guardar_ejecucion(workflow, run, ahora)
        for campo, valor in etiqueta.items():
            setattr(ejecucion, campo, valor)
        ejecucion.etiquetada_en = ahora
        ejecucion.save()
        prediccion = Prediccion(
            usuario=usuario, workflow=workflow, commit=commit,
            version_modelo=version, rama=run.get("head_branch") or "",
            evento=run.get("event") or "", variables=_json_seguro(variables),
            probabilidad=resultado["probabilidad"], nivel=resultado["nivel"],
            recomendacion=resultado["recomendacion"],
            factores=resultado["factores"], recomendaciones=recomendaciones,
            analisis_ia=analisis, origen="lote",
            momento_variables=fecha(run["run_started_at"]),
            ejecucion_real=ejecucion, verificada_en=ahora,
            datos_github_extraidos_en=ahora)
        prediccion.clean()
        prediccion.save()
    return prediccion


# --- Análisis interactivos pendientes --------------------------------------

def interactivos_pendientes(dias=DIAS_INTERACTIVOS):
    """Análisis interactivos recientes sin resultado real, de repositorios
    activos que no son de prueba (los reales y el de demostración)."""
    return (Prediccion.objects.filter(
        origen="interactivo", ejecucion_real__isnull=True,
        creada_en__gte=dj_timezone.now() - timedelta(days=dias),
        workflow__repositorio__est_registro="A",
        workflow__repositorio__es_prueba=False)
        .select_related("workflow__repositorio", "commit")
        .order_by("creada_en"))


def verificar_interactivos(gh, dias=DIAS_INTERACTIVOS):
    """Enlaza el resultado real de los análisis interactivos pendientes, igual
    que el botón «Verificar resultado real».

    Devuelve (resumen, enlazadas, errores).
    """
    resumen, enlazadas, errores = {"enlazadas": 0, "pendientes": 0}, [], []
    for prediccion in interactivos_pendientes(dias):
        try:
            enlazada, _ = enlazar_resultado(gh, prediccion)
        except github.LimiteExcedido:
            raise
        except github.GitHubError as exc:
            errores.append(f"análisis {prediccion.id}: {exc}")
            continue
        resumen["enlazadas" if enlazada else "pendientes"] += 1
        if enlazada:
            enlazadas.append(prediccion)
    return resumen, enlazadas, errores
