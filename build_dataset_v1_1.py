#!/usr/bin/env python3
"""Construye el dataset v1.1 corrigiendo las reglas que dependían del resultado.

v1 (build_dataset.py + label_deploy_runs.py) se conserva sin cambios. v1.1
cambia SOLO las reglas de inclusión y etiquetado; las variables predictoras
se calculan con las mismas funciones de build_dataset.py.

Correcciones (ver la auditoría generada en el informe de calidad):
1. Entorno por workflow: un workflow es efímero si CUALQUIERA de sus
   ejecuciones crea un clúster de prueba; es vista previa si su ruta lo
   indica. En v1 se decidía por ejecución y una ejecución que fallaba antes
   de crear el clúster parecía un despliegue a una aplicación.
2. Intención de despliegue sin mirar el propio resultado: una ejecución es
   un intento de despliegue si OTRA ejecución del mismo workflow y del mismo
   contexto (evento + rama, o "tag") ejecutó un paso de despliegue
   (leave-one-out). En v1 un fallo sin paso de despliegue era y = 1 y un
   éxito sin paso de despliegue se excluía: la inclusión dependía del
   resultado.
3. Ejecuciones sin log_insights: no se puede saber hasta dónde llegaron;
   se marcan como ambiguas. En v1 contaban como "sin paso de despliegue".
4. Los casos ambiguos se conservan (columna `ambiguo` y `motivo_ambiguo`)
   con y vacío y no se usan para entrenar.
"""

import argparse
import collections
import json
from pathlib import Path

import numpy as np
import pandas as pd

import build_dataset as v1
from find_deploy_runs import abrir_archivo
from label_deploy_runs import EVENTOS_PREVIEW, analizar


def contexto(evento, rama):
    rama = rama or ""
    return (evento, "tag" if v1.RAMA_TAG.match(rama) else rama)


def leer_ejecuciones_despliegue(ruta_runs, workflows):
    """Una fila por ejecución de los workflows candidatos, con sus pasos."""
    filas = []
    with abrir_archivo(ruta_runs) as archivo:
        for linea in archivo:
            if not linea.strip():
                continue
            try:
                r = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if (r.get("repository_name"), r.get("workflow_path")) \
                    not in workflows:
                continue
            m = r.get("metadata") or {}
            despliegues, efimero = analizar(r)
            insights = r.get("log_insights") or []
            filas.append({
                "run_id": m.get("id"),
                "run_attempt": r.get("run_attempt"),
                "repository_name": r.get("repository_name"),
                "workflow_path": r.get("workflow_path"),
                "repo_id": (m.get("repository") or {}).get("id"),
                "workflow_id": m.get("workflow_id"),
                "event": m.get("event"),
                "head_branch": m.get("head_branch") or "",
                "head_sha": m.get("head_sha"),
                "conclusion": str(m.get("conclusion")),
                "tiene_log": bool(insights),
                "n_pasos": sum(len(j.get("steps") or []) for j in insights),
                "efimero_ejecucion": efimero,
                "despliega": bool(despliegues),
                "pasos_despliegue": "; ".join(sorted(
                    {d["nombre"] for d in despliegues})),
                "candidato_fallo_despliegue": any(
                    d["ultimo_del_job"] and not d["actividad_posterior"]
                    for d in despliegues),
                "paso_posterior": any(not d["ultimo_del_job"]
                                      for d in despliegues),
            })
    df = pd.DataFrame(filas)
    # Repositorios renombrados: la misma ejecución aparece varias veces. Se
    # conserva el registro con más información de log (no depende del
    # resultado: es la misma ejecución).
    df = df.sort_values(["tiene_log", "n_pasos"], ascending=False)
    return df.drop_duplicates(["run_id", "run_attempt"]).reset_index(
        drop=True)


def etiquetar(df):
    """Aplica las reglas v1.1. Devuelve df con estado, y y motivos."""
    por_wf = df.groupby("workflow_id")
    efimero_wf = por_wf["efimero_ejecucion"].transform("any")
    preview_wf = df["workflow_path"].str.lower().str.contains("preview")
    df["entorno_workflow"] = np.where(
        efimero_wf, "efímero de pruebas",
        np.where(preview_wf, "vista previa", "aplicación"))

    # Intención de despliegue (leave-one-out por workflow y contexto).
    df["contexto"] = [contexto(e, b) for e, b in
                      zip(df["event"], df["head_branch"])]
    grupos = collections.defaultdict(list)
    for i, fila in df.iterrows():
        grupos[(fila["workflow_id"], fila["contexto"])].append(i)
    intencion = {}
    for indices in grupos.values():
        for i in indices:
            otros = [j for j in indices if j != i and df.at[j, "tiene_log"]]
            if not otros:
                intencion[i] = "indeterminada"
            elif any(df.at[j, "despliega"] for j in otros):
                intencion[i] = "sí"
            else:
                intencion[i] = "no"
    df["intencion_despliegue"] = pd.Series(intencion)

    estado, y, motivo = [], [], []
    for _, f in df.iterrows():
        if f["entorno_workflow"] != "aplicación":
            estado.append("excluida"), y.append(np.nan)
            motivo.append(f"workflow de {f['entorno_workflow']}")
        elif f["event"] in EVENTOS_PREVIEW:
            estado.append("excluida"), y.append(np.nan)
            motivo.append("evento de pull request (vista previa)")
        elif f["conclusion"] not in ("success", "failure"):
            estado.append("excluida"), y.append(np.nan)
            motivo.append(f"resultado {f['conclusion']}")
        elif not f["tiene_log"]:
            estado.append("ambiguo"), y.append(np.nan)
            motivo.append("sin log_insights: no se sabe hasta dónde llegó")
        elif f["intencion_despliegue"] == "indeterminada":
            estado.append("ambiguo"), y.append(np.nan)
            motivo.append("intención de despliegue indeterminada (ninguna "
                          "otra ejecución del mismo contexto)")
        elif f["intencion_despliegue"] == "no":
            estado.append("excluida"), y.append(np.nan)
            motivo.append("sin intento de despliegue en este contexto")
        elif f["conclusion"] == "success":
            if f["despliega"]:
                estado.append("etiquetada"), y.append(0)
                motivo.append("despliegue completado")
            else:
                estado.append("ambiguo"), y.append(np.nan)
                motivo.append("éxito sin paso de despliegue en un contexto "
                              "que despliega")
        elif not f["despliega"]:
            estado.append("etiquetada"), y.append(1)
            motivo.append("fallo antes del despliegue")
        elif f["candidato_fallo_despliegue"]:
            estado.append("etiquetada"), y.append(1)
            motivo.append("fallo en el paso de despliegue (inferido)")
        elif f["paso_posterior"]:
            estado.append("etiquetada"), y.append(1)
            motivo.append("fallo tras ejecutar el despliegue (paso "
                          "posterior)")
        else:
            estado.append("ambiguo"), y.append(np.nan)
            motivo.append("fallo en otro job con el despliegue completado")
    df["estado"], df["y"], df["motivo"] = estado, y, motivo
    return df


def auditoria(df, v1_dataset, v1_niveles):
    """Tabla de reglas v1: dependencia del resultado y filas afectadas."""
    v1d = pd.read_csv(v1_dataset)
    claves_v1 = v1d.set_index(["run_id", "run_attempt"])["y"]
    niveles = pd.read_csv(v1_niveles, encoding="utf-8")
    niveles = niveles.drop_duplicates(["run_id", "run_attempt"])
    df = df.set_index(["run_id", "run_attempt"])
    en_v1 = df.index.isin(claves_v1.index)
    y_v1 = claves_v1.reindex(df.index)

    def conteo(mascara, y_ref=y_v1):
        m = pd.Series(mascara, index=df.index)
        return (int(m.sum()), int(((y_ref == 1) & m).sum()),
                int(((y_ref == 0) & m).sum()))

    niv = niveles.set_index(["run_id", "run_attempt"]).reindex(df.index)
    reglas = []
    efimero_mal = (en_v1 & (df["entorno_workflow"] == "efímero de pruebas")
                   ).to_numpy()
    reglas.append(("Entorno efímero decidido por ejecución "
                   "(label_deploy_runs.py)", "Sí: el clúster solo aparece si "
                   "la ejecución llegó a crearlo", *conteo(efimero_mal),
                   "Corregida: entorno por workflow"))
    antes = (en_v1 & (niv["nivel_evidencia"] == "fallo antes del despliegue")
             ).to_numpy()
    exito_sin = (niv["nivel_evidencia"] == "éxito sin despliegue ejecutado"
                 ) & (niv["entorno"] == "aplicación")
    reglas.append(("Intención de despliegue inferida del propio resultado: "
                   "fallo sin paso de despliegue → y = 1; éxito sin paso → "
                   "excluido", "Sí: el paso de despliegue solo existe si la "
                   "ejecución avanzó", *conteo(antes),
                   f"Corregida: intención leave-one-out por contexto "
                   f"(además, {int(exito_sin.sum())} éxitos sin despliegue "
                   f"excluidos en v1 se reevalúan)"))
    sin_log = (en_v1 & ~df["tiene_log"]).to_numpy()
    reglas.append(("Ejecución sin log_insights tratada como 'sin paso de "
                   "despliegue'", "Sí: la falta de log puede deberse al "
                   "resultado (p. ej., fallo de arranque)", *conteo(sin_log),
                   "Corregida: ambiguo"))
    otro_job = ((niv["nivel_evidencia"]
                 == "fallo en otro job; despliegue completado")
                & (niv["entorno"] == "aplicación")).to_numpy()
    reglas.append(("Fallo en otro job con el despliegue completado → "
                   "excluido", "Sí (solo existe en fallos), inevitable: la "
                   "etiqueta es desconocida", int(otro_job.sum()), 0, 0,
                   "Se conserva como 'ambiguo' (antes se borraba)"))
    otros = niv["conclusion"].isin(["cancelled", "skipped",
                                    "action_required"]).to_numpy() & (
        niv["entorno"] == "aplicación").to_numpy()
    reglas.append(("Excluir cancelled / skipped / action_required",
                   "Sí (es un resultado), inevitable: no hay etiqueta",
                   int(otros.sum()), 0, 0, "Sin cambio"))
    reglas.append(("Vista previa por evento de pull request o ruta "
                   "'preview'", "No: el evento y la ruta se conocen antes "
                   "de ejecutar", 0, 0, 0, "Sin cambio (ruta evaluada por "
                   "workflow)"))
    reglas.append(("Deduplicar repositorios renombrados prefiriendo el "
                   "registro con más log", "No: es la misma ejecución; "
                   "depende de la disponibilidad del log", 124, 0, 0,
                   "Sin cambio"))
    reglas.append(("Selección de workflows: alguna ejecución ejecutó un "
                   "paso de despliegue (find_deploy_runs.py)", "Sí, a nivel "
                   "de workflow: un workflow cuyas ejecuciones observadas "
                   "fallaron todas antes de desplegar no entra", None, None,
                   None, "No corregible sin el YAML histórico (≈1.300 "
                   "consultas a la API con token); se declara como sesgo de "
                   "selección"))
    reglas.append(("Variables de historial (ejecuciones anteriores)",
                   "No: solo usan ejecuciones que empezaron antes", 0, 0, 0,
                   "Sin cambio"))
    reglas.append(("Indicador 'workflow que siempre falla'", "Sí (usa todas "
                   "las ejecuciones), pero solo para el análisis de "
                   "sensibilidad; no es variable ni filtro", 0, 0, 0,
                   "Sin cambio"))
    return reglas


def main():
    parser = argparse.ArgumentParser(description="Dataset v1.1.")
    parser.add_argument("--runs", required=True)
    parser.add_argument("--deploy-csv", required=True,
                        help="informes/deploy_runs.csv (find_deploy_runs.py)")
    parser.add_argument("--v1-dataset", required=True)
    parser.add_argument("--v1-niveles", required=True)
    parser.add_argument("--historial", required=True,
                        help="datos_procesados/historial_runs.pkl")
    parser.add_argument("--out", required=True)
    parser.add_argument("--runs-out", required=True,
                        help="CSV por ejecución con la clasificación v1.1")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    candidatos = pd.read_csv(args.deploy_csv)
    workflows = set(zip(candidatos["repository_name"],
                        candidatos["workflow_path"]))
    print(f"Workflows candidatos: {len(workflows):,}. Leyendo runs...")
    ejecuciones = etiquetar(leer_ejecuciones_despliegue(args.runs,
                                                        workflows))
    ejecuciones["workflow_siempre_falla"] = ejecuciones.groupby(
        "workflow_id")["conclusion"].transform(
        lambda c: bool((c == "failure").all()))
    # CSV por ejecución, compatible con validar_workflows_dataset.
    salida_runs = ejecuciones.assign(
        entorno=ejecuciones["entorno_workflow"])
    salida_runs.drop(columns=["contexto"]).to_csv(args.runs_out, index=False,
                                                  encoding="utf-8")

    reglas = auditoria(ejecuciones.copy(), args.v1_dataset, args.v1_niveles)

    # Dataset: etiquetadas + ambiguas (las ambiguas con y vacío).
    datos = ejecuciones[ejecuciones["estado"].isin(
        ["etiquetada", "ambiguo"])].copy()
    datos["ambiguo"] = (datos["estado"] == "ambiguo").astype(int)
    datos["motivo_ambiguo"] = np.where(datos["ambiguo"] == 1,
                                       datos["motivo"], "")

    runs = pd.read_pickle(args.historial)
    hist_wf = v1.historial(runs, "workflow_id", "wf")
    hist_repo = v1.historial(runs, "repo_id", "repo")
    runs = runs.set_index(["run_id", "run_attempt"]).join(hist_wf).join(
        hist_repo)
    datos = datos.set_index(["run_id", "run_attempt"]).join(
        runs, how="inner", rsuffix="_run").reset_index()
    datos = pd.concat([datos, v1.variables_commit(datos)], axis=1)
    variables = [
        "event", "msg_len", "msg_lineas", "msg_merge", "msg_revert",
        "msg_fix", "msg_feat", "msg_deps", "msg_docs", "msg_ci",
        "autor_bot", "reejecutado_por_otro", "rama_principal", "rama_bot",
        "rama_tag", "tiene_pr", "es_reintento", "hora_utc", "dia_semana",
        "fin_de_semana", "retraso_commit_run_min", "wf_n_prev",
        "wf_tasa_fallo_prev", "wf_ultimo_fallo", "wf_horas_desde_ultimo",
        "wf_duracion_media_prev_min", "repo_n_prev", "repo_tasa_fallo_prev",
        "repo_n_workflows_prev",
    ]
    final = datos[["run_id", "run_attempt", "repository_name",
                   "workflow_path", "repo_id", "workflow_id", "head_sha",
                   "run_started_at"] + variables + [
        "motivo", "pasos_despliegue", "workflow_siempre_falla", "ambiguo",
        "motivo_ambiguo", "y"]].copy()
    final = final.rename(columns={"motivo": "nivel_evidencia"})
    final["autor_hash"] = datos["commit_author"].map(v1.anonimizar)
    final = final.sort_values("run_started_at").reset_index(drop=True)

    # Misma regla de partición que v1: cuantil 0,75 de run_started_at de las
    # filas etiquetadas.
    etiquetadas = final[final["ambiguo"] == 0]
    corte = etiquetadas["run_started_at"].quantile(0.75)
    final["particion"] = np.where(final["run_started_at"] < corte,
                                  "entrenamiento", "prueba")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(args.out, index=False, encoding="utf-8")

    # Informe de calidad.
    app = ejecuciones[ejecuciones["entorno_workflow"] == "aplicación"]
    lineas = [
        "# Informe de calidad del dataset v1.1",
        "",
        "## Procedencia",
        "",
        "- Fuente: GHALogs v1.0.1 (Zenodo 14796970, CC BY-SA 4.0).",
        "- Script: `build_dataset_v1_1.py`. v1 se conserva en "
        "`datos_procesados/dataset_riesgo_despliegue_v1.csv`.",
        "- Variables predictoras: mismas funciones que v1 "
        "(`build_dataset.py`).",
        "",
        "## Auditoría de las reglas de inclusión y etiquetado de v1",
        "",
        "'Filas afectadas' son filas del dataset v1 cuya decisión tomó esa "
        "regla (una fila puede verse afectada por varias reglas).",
        "",
        "| Regla de v1 | ¿Depende del resultado? | Filas afectadas | y = 1 | "
        "y = 0 | Decisión v1.1 |",
        "|---|---|---:|---:|---:|---|",
    ]
    for regla, depende, n, n1, n0, decision in reglas:
        celdas = ["—" if v is None else f"{v:,}" for v in (n, n1, n0)]
        lineas.append(f"| {regla} | {depende} | {' | '.join(celdas)} | "
                      f"{decision} |")
    lineas += [
        "",
        "## Clasificación de las ejecuciones de workflows candidatos",
        "",
        f"- Ejecuciones (sin duplicados): {len(ejecuciones):,}; workflows: "
        f"{ejecuciones['workflow_id'].nunique():,}",
        "",
        "| Entorno del workflow | Workflows | Ejecuciones |",
        "|---|---:|---:|",
    ]
    for entorno, g in ejecuciones.groupby("entorno_workflow"):
        lineas.append(f"| {entorno} | {g['workflow_id'].nunique():,} | "
                      f"{len(g):,} |")
    lineas += [
        "",
        "### Ejecuciones de workflows de aplicación por estado y motivo",
        "",
        "| Estado | Motivo | Ejecuciones | y |",
        "|---|---|---:|---|",
    ]
    for (est, mot), g in app.groupby(["estado", "motivo"]):
        valor = ("—" if g["y"].isna().all() else str(int(g["y"].iloc[0])))
        lineas.append(f"| {est} | {mot} | {len(g):,} | {valor} |")
    etiq = final[final["ambiguo"] == 0]
    amb = final[final["ambiguo"] == 1]
    por_particion = etiq.groupby("particion")["y"].agg(["size", "mean"])
    lineas += [
        "",
        "## Dataset v1.1",
        "",
        f"- Filas totales: {len(final):,} (etiquetadas: {len(etiq):,}; "
        f"**ambiguas conservadas y excluidas del entrenamiento: "
        f"{len(amb):,}**)",
        f"- Positivos (y = 1) entre las etiquetadas: "
        f"{int(etiq['y'].sum()):,} ({etiq['y'].mean() * 100:.1f} %)",
        f"- Repositorios (etiquetadas): {etiq['repo_id'].nunique():,} | "
        f"workflows: {etiq['workflow_id'].nunique():,}",
        f"- Filas etiquetadas de workflows que fallan siempre: "
        f"{int(etiq['workflow_siempre_falla'].sum()):,}",
        "",
        "### Ambiguas por motivo",
        "",
        "| Motivo | Filas |",
        "|---|---:|",
    ]
    lineas += [f"| {k} | {v:,} |" for k, v in
               amb["motivo_ambiguo"].value_counts().items()]
    lineas += [
        "",
        "## Partición temporal (misma regla que v1)",
        "",
        f"- Corte: {corte}",
        "",
        "| Partición | Filas etiquetadas | Tasa de y = 1 |",
        "|---|---:|---:|",
    ]
    lineas += [f"| {p} | {int(r['size']):,} | {r['mean'] * 100:.1f} % |"
               for p, r in por_particion.iterrows()]
    faltantes = etiq[variables].isna().mean().mul(100).round(1)
    lineas += [
        "",
        "## Valores faltantes en filas etiquetadas (%)",
        "",
        "| Variable | % faltante |",
        "|---|---:|",
    ]
    lineas += [f"| {k} | {v} |" for k, v in faltantes.items() if v > 0]
    lineas += [
        "",
        "## Limitaciones que permanecen",
        "",
        "- Sesgo de selección de workflows (ver la auditoría): solo entran "
        "workflows con al menos una ejecución que llegó a desplegar.",
        "- La intención de despliegue se infiere de otras ejecuciones del "
        "mismo contexto; con un máximo de 5 ejecuciones por workflow, "
        "muchos contextos quedan indeterminados (ambiguos).",
        "- Dentro de un workflow, el resultado de las demás ejecuciones "
        "puede estar correlacionado con el de la ejecución evaluada.",
        "",
    ]
    Path(args.report).write_text("\n".join(lineas), encoding="utf-8")
    print(f"Dataset: {args.out} | Informe: {args.report}")


if __name__ == "__main__":
    main()
