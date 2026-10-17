#!/usr/bin/env python3
"""Construye el dataset de investigación de riesgo de despliegue.

Fila = un intento de ejecución (run_id + run_attempt) de un workflow que
ejecuta pasos reales de despliegue en un entorno de aplicación (según
label_deploy_runs.py). Los datos originales no se modifican.

Variable objetivo (y = despliegue_no_completado):
  0 = el paso de despliegue se ejecutó y el workflow terminó con éxito.
  1 = el intento de despliegue no se completó con éxito: falló antes de
      llegar al despliegue, durante el despliegue o en un paso posterior
      del mismo job (por ejemplo, una verificación).
  Excluidas: ejecuciones sin intento de despliegue (éxito sin paso de
  despliegue), fallos en otro job con el despliegue completado (ambiguas),
  canceladas, omitidas y pendientes de aprobación.

Todas las variables predictoras se calculan con información disponible
antes de que empiece la ejecución: metadatos del commit y del disparo, y
el historial de ejecuciones estrictamente anteriores.
"""

import argparse
import collections
import gzip
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

NIVEL_A_ETIQUETA = {
    "despliegue exitoso": 0,
    "fallo antes del despliegue": 1,
    "fallo en despliegue - evidencia alta": 1,
    "fallo en despliegue - evidencia media": 1,
    "fallo en despliegue - evidencia media (sin referencia)": 1,
    "fallo tras ejecutar el despliegue (paso posterior)": 1,
}

RAMA_PRINCIPAL = re.compile(r"^(main|master|prod|production|release|live)$",
                            re.IGNORECASE)
RAMA_BOT = re.compile(r"dependabot|renovate", re.IGNORECASE)
RAMA_TAG = re.compile(r"^v?\d+\.\d+", re.IGNORECASE)
AUTOR_BOT = re.compile(r"\[bot\]|dependabot|renovate|github-actions",
                       re.IGNORECASE)


def fecha(texto):
    if not texto:
        return None
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return None


def cargar_etiquetas(ruta):
    """Lee las etiquetas, elimina ejecuciones duplicadas por renombrado."""
    df = pd.read_csv(ruta, encoding="utf-8")
    df = df[df["entorno"] == "aplicación"].copy()
    inicial = len(df)
    # Si la misma ejecución aparece con varios nombres de repositorio, se
    # conserva el registro con pasos de despliegue detectados (más
    # informativo); en caso de empate, el primero.
    df["_tiene_pasos"] = df["pasos_despliegue"].notna()
    df = df.sort_values("_tiene_pasos", ascending=False)
    df = df.drop_duplicates(["run_id", "run_attempt"], keep="first")
    df = df.drop(columns="_tiene_pasos")
    return df, inicial - len(df)


def leer_ejecuciones(ruta_runs, repos):
    """Lee los metadatos de todas las ejecuciones de los repositorios dados."""
    filas = []
    with gzip.open(ruta_runs, "rt", encoding="utf-8",
                   errors="replace") as archivo:
        for linea in archivo:
            if not linea.strip():
                continue
            try:
                r = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if r.get("repository_name") not in repos:
                continue
            m = r.get("metadata") or {}
            commit = m.get("head_commit") or {}
            autor = commit.get("author") or {}
            filas.append({
                "run_id": m.get("id"),
                "run_attempt": r.get("run_attempt"),
                "repo_id": (m.get("repository") or {}).get("id"),
                "workflow_id": m.get("workflow_id"),
                "event": m.get("event"),
                "head_branch": m.get("head_branch") or "",
                "created_at": fecha(m.get("created_at")),
                "run_started_at": fecha(m.get("run_started_at")),
                "updated_at": fecha(m.get("updated_at")),
                "conclusion": m.get("conclusion"),
                "commit_timestamp": fecha(commit.get("timestamp")),
                "commit_message": str(commit.get("message") or ""),
                "commit_author": str(autor.get("name") or ""),
                "actor": (m.get("actor") or {}).get("login"),
                "triggering_actor": (m.get("triggering_actor") or {})
                .get("login"),
                "n_pull_requests": len(m.get("pull_requests") or []),
            })
    df = pd.DataFrame(filas)
    # Las mismas ejecuciones aparecen bajo nombres de repositorio antiguos.
    return df.drop_duplicates(["run_id", "run_attempt"])


def historial(df, clave, prefijo):
    """Variables de ejecuciones estrictamente anteriores con la misma clave."""
    df = df.sort_values("run_started_at")
    salida = {}
    for _, grupo in df.groupby(clave, sort=False):
        tiempos = grupo["run_started_at"].tolist()
        fallos = (grupo["conclusion"] == "failure").tolist()
        exitos = (grupo["conclusion"] == "success").tolist()
        duraciones = ((grupo["updated_at"] - grupo["run_started_at"])
                      .dt.total_seconds() / 60).tolist()
        workflows = grupo["workflow_id"].tolist()
        for i, run in enumerate(zip(grupo["run_id"], grupo["run_attempt"])):
            # Solo ejecuciones que empezaron antes que esta.
            previas = [j for j in range(i) if tiempos[j] < tiempos[i]]
            binarias = [j for j in previas if fallos[j] or exitos[j]]
            registro = {f"{prefijo}_n_prev": len(previas)}
            registro[f"{prefijo}_tasa_fallo_prev"] = (
                np.mean([fallos[j] for j in binarias]) if binarias else np.nan)
            if prefijo == "wf":
                ultimo = binarias[-1] if binarias else None
                registro["wf_ultimo_fallo"] = (
                    np.nan if ultimo is None else float(fallos[ultimo]))
                registro["wf_horas_desde_ultimo"] = (
                    (tiempos[i] - tiempos[previas[-1]]).total_seconds() / 3600
                    if previas else np.nan)
                registro["wf_duracion_media_prev_min"] = (
                    np.nanmean([duraciones[j] for j in previas])
                    if previas else np.nan)
            else:
                registro["repo_n_workflows_prev"] = len(
                    {workflows[j] for j in previas})
            salida[run] = registro
    resultado = pd.DataFrame.from_dict(salida, orient="index")
    resultado.index.names = ["run_id", "run_attempt"]
    return resultado


def variables_commit(df):
    msg = df["commit_message"]
    primera = msg.str.split("\n").str[0].str.lower()
    out = pd.DataFrame(index=df.index)
    out["msg_len"] = msg.str.len()
    out["msg_lineas"] = msg.str.count("\n") + 1
    out["msg_merge"] = primera.str.startswith("merge").astype(int)
    out["msg_revert"] = primera.str.contains("revert").astype(int)
    out["msg_fix"] = primera.str.contains(r"\bfix|hotfix|bug").astype(int)
    out["msg_feat"] = primera.str.contains(r"\bfeat|\badd\b").astype(int)
    out["msg_deps"] = primera.str.contains(
        r"bump|deps|dependenc|upgrade|update .* to").astype(int)
    out["msg_docs"] = primera.str.contains(r"\bdocs?\b|readme").astype(int)
    out["msg_ci"] = primera.str.contains(r"\bci\b|workflow|pipeline").astype(
        int)
    out["autor_bot"] = df["commit_author"].str.contains(AUTOR_BOT).astype(int)
    out["reejecutado_por_otro"] = (
        df["actor"].fillna("") != df["triggering_actor"].fillna("")
    ).astype(int)
    rama = df["head_branch"]
    out["rama_principal"] = rama.str.match(RAMA_PRINCIPAL).astype(int)
    out["rama_bot"] = rama.str.contains(RAMA_BOT).astype(int)
    out["rama_tag"] = rama.str.match(RAMA_TAG).astype(int)
    out["tiene_pr"] = (df["n_pull_requests"] > 0).astype(int)
    out["es_reintento"] = (df["run_attempt"] > 1).astype(int)
    inicio = df["run_started_at"]
    out["hora_utc"] = inicio.dt.hour
    out["dia_semana"] = inicio.dt.dayofweek
    out["fin_de_semana"] = (inicio.dt.dayofweek >= 5).astype(int)
    retraso = (inicio - df["commit_timestamp"]).dt.total_seconds() / 60
    out["retraso_commit_run_min"] = retraso.clip(lower=0)
    return out


def anonimizar(valor):
    return hashlib.sha256(str(valor).encode()).hexdigest()[:12]


def main():
    parser = argparse.ArgumentParser(description="Construye el dataset.")
    parser.add_argument("--runs", required=True)
    parser.add_argument("--labels", required=True,
                        help="informes/deploy_runs_niveles.csv")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    etiquetas, duplicados = cargar_etiquetas(args.labels)
    conteo_niveles = etiquetas["nivel_evidencia"].value_counts()
    etiquetas["y"] = etiquetas["nivel_evidencia"].map(NIVEL_A_ETIQUETA)
    excluidas = etiquetas["y"].isna().sum()
    etiquetas = etiquetas.dropna(subset=["y"])
    etiquetas["y"] = etiquetas["y"].astype(int)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache = out / "historial_runs.pkl"
    if cache.exists():
        print(f"Usando historial en caché: {cache}")
        runs = pd.read_pickle(cache)
    else:
        print("Leyendo historial de ejecuciones de los repositorios...")
        repos = set(pd.read_csv(args.labels, encoding="utf-8")
                    ["repository_name"])
        runs = leer_ejecuciones(args.runs, repos)
        runs.to_pickle(cache)
    print(f"Ejecuciones de historial: {len(runs):,}")

    hist_wf = historial(runs, "workflow_id", "wf")
    hist_repo = historial(runs, "repo_id", "repo")
    runs = runs.set_index(["run_id", "run_attempt"])
    runs = runs.join(hist_wf).join(hist_repo)

    datos = etiquetas.set_index(["run_id", "run_attempt"]).join(
        runs, how="inner", rsuffix="_run")
    sin_metadatos = len(etiquetas) - len(datos)
    datos = datos.reset_index()
    datos = pd.concat([datos, variables_commit(datos)], axis=1)

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
    identificacion = ["run_id", "run_attempt", "repository_name",
                      "workflow_path", "repo_id", "workflow_id", "head_sha",
                      "run_started_at"]
    trazabilidad = ["nivel_evidencia", "pasos_despliegue",
                    "workflow_siempre_falla"]
    final = datos[identificacion + variables + trazabilidad + ["y"]].copy()
    final["autor_hash"] = datos["commit_author"].map(anonimizar)
    final = final.sort_values("run_started_at").reset_index(drop=True)

    # División temporal: el 25 % más reciente se reserva para evaluación.
    corte = final["run_started_at"].quantile(0.75)
    final["particion"] = np.where(final["run_started_at"] < corte,
                                  "entrenamiento", "prueba")

    final.to_csv(out / "dataset_riesgo_despliegue.csv", index=False,
                 encoding="utf-8")

    # Informe de calidad.
    faltantes = final[variables].isna().mean().mul(100).round(1)
    descripcion = final[variables].describe().T[
        ["mean", "50%", "min", "max"]].round(2)
    por_particion = final.groupby("particion")["y"].agg(["size", "mean"])
    lineas = [
        "# Informe de calidad del dataset de riesgo de despliegue",
        "",
        "## Procedencia",
        "",
        "- Fuente: GHALogs v1.0.1 (Zenodo 14796970, CC BY-SA 4.0), "
        "`runs.json.gz` (MD5 verificado en registro_datasets.csv).",
        "- Selección: workflows con pasos reales de despliegue ejecutados "
        "(find_deploy_runs.py) en entornos de aplicación "
        "(label_deploy_runs.py).",
        "- Script: build_dataset.py. Datos originales sin modificar.",
        "- Licencia del dataset derivado: CC BY-SA 4.0 (compartir igual).",
        "",
        "## Definición de fila y etiqueta",
        "",
        "- Fila: un intento (run_id + run_attempt) de un workflow de "
        "despliegue.",
        "- y = 1: el intento de despliegue no se completó con éxito; "
        "y = 0: despliegue ejecutado y workflow exitoso.",
        "",
        "## Recuento",
        "",
        f"- Filas del entorno de aplicación antes de depurar: "
        f"{len(etiquetas) + excluidas + duplicados:,}",
        f"- Duplicados por repositorios renombrados eliminados: "
        f"{duplicados:,}",
        f"- Excluidas por no tener intento de despliegue o ser ambiguas: "
        f"{excluidas:,}",
        f"- Sin metadatos en runs.json.gz: {sin_metadatos:,}",
        f"- Filas finales: {len(final):,}",
        f"- Positivos (y = 1): {int(final['y'].sum()):,} "
        f"({final['y'].mean() * 100:.1f} %)",
        f"- Repositorios: {final['repo_id'].nunique():,} | workflows: "
        f"{final['workflow_id'].nunique():,}",
        f"- Filas de workflows que fallan siempre: "
        f"{int(final['workflow_siempre_falla'].sum()):,}",
        "",
        "### Niveles de evidencia de origen (tras eliminar duplicados)",
        "",
        "| Nivel | Filas |",
        "|---|---:|",
    ]
    lineas += [f"| {k} | {v:,} |" for k, v in conteo_niveles.items()]
    lineas += [
        "",
        "## Partición temporal",
        "",
        f"- Corte: {corte}",
        "",
        "| Partición | Filas | Tasa de y = 1 |",
        "|---|---:|---:|",
    ]
    lineas += [f"| {p} | {int(r['size']):,} | {r['mean'] * 100:.1f} % |"
               for p, r in por_particion.iterrows()]
    repos_train = set(final.loc[final.particion == "entrenamiento",
                                "repo_id"])
    repos_test = set(final.loc[final.particion == "prueba", "repo_id"])
    lineas += [
        "",
        f"- Repositorios de prueba también presentes en entrenamiento: "
        f"{len(repos_test & repos_train):,} de {len(repos_test):,}",
        "",
        "## Valores faltantes (%)",
        "",
        "Los faltantes de historial son estructurales: primera ejecución "
        "observada del workflow o repositorio. No se imputan aquí.",
        "",
        "| Variable | % faltante |",
        "|---|---:|",
    ]
    lineas += [f"| {k} | {v} |" for k, v in faltantes.items() if v > 0]
    lineas += [
        "",
        "## Estadísticos descriptivos",
        "",
        "| Variable | Media | Mediana | Mín | Máx |",
        "|---|---:|---:|---:|---:|",
    ]
    lineas += [f"| {k} | {r['mean']} | {r['50%']} | {r['min']} | {r['max']} |"
               for k, r in descripcion.iterrows()]
    lineas += [
        "",
        "## Control de fuga de información",
        "",
        "- Excluidas como predictoras: conclusion, updated_at, duración y "
        "pasos de la ejecución actual, nivel de evidencia.",
        "- El historial usa solo ejecuciones que empezaron antes "
        "(run_started_at) de la ejecución evaluada.",
        "- Nombres y correos de autores no se guardan; solo un hash.",
        "",
        "## Limitaciones",
        "",
        "- GHALogs guarda como máximo 5 ejecuciones por workflow: el "
        "historial por workflow es corto.",
        "- Las etiquetas se infieren de pasos ejecutados, no de logs "
        "completos; y = 1 incluye fallos de compilación o pruebas dentro "
        "del pipeline de despliegue.",
        "- Sin métricas del cambio de código (archivos, líneas): requieren "
        "la API de GitHub con token (trabajo futuro).",
        "",
    ]
    Path(args.report).write_text("\n".join(lineas), encoding="utf-8")
    print(f"Dataset: {out / 'dataset_riesgo_despliegue.csv'}")
    print(f"Informe: {args.report}")


if __name__ == "__main__":
    main()
