#!/usr/bin/env python3
"""Compara dos versiones del dataset y del modelo con los artefactos guardados.

Las métricas se recalculan con cada modelo sobre la partición de prueba de
su propio dataset; no se copian de los informes.
"""

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from train_models import CATEGORICAS, NUMERICAS


def evaluar(ruta_datos, dir_modelos, version):
    archivo = version.replace(".", "_")
    meta = json.loads((Path(dir_modelos) / f"modelo_riesgo_{archivo}.json")
                      .read_text(encoding="utf-8"))
    modelo = joblib.load(Path(dir_modelos) / f"modelo_riesgo_{archivo}.joblib")
    df = pd.read_csv(ruta_datos)
    ambiguas = int((df["ambiguo"] == 1).sum()) if "ambiguo" in df else 0
    if "ambiguo" in df:
        df = df[df["ambiguo"] == 0]
    df = df.dropna(subset=["y"])
    prueba = df[df["particion"] == "prueba"]
    p = modelo.predict_proba(prueba[CATEGORICAS + NUMERICAS])[:, 1]
    y = prueba["y"].astype(int).to_numpy()
    sin_siempre = ~prueba["workflow_siempre_falla"].astype(bool).to_numpy()
    limites = meta["limites_riesgo"]
    nivel = pd.cut(p, [-1, limites["medio"], limites["alto"], 2],
                   right=False, labels=["bajo", "medio", "alto"])
    tasas = (pd.DataFrame({"nivel": nivel, "y": y}).groupby(
        "nivel", observed=False)["y"].agg(["size", "mean"]))
    return {
        "modelo": meta["modelo"],
        "filas": len(df),
        "ambiguas": ambiguas,
        "repositorios": df["repo_id"].nunique(),
        "workflows": df["workflow_id"].nunique(),
        "fallos": df["y"].mean(),
        "prueba": len(prueba),
        "fallos_prueba": y.mean(),
        "pr_auc": average_precision_score(y, p),
        "roc_auc": roc_auc_score(y, p),
        "pr_auc_sin": average_precision_score(y[sin_siempre], p[sin_siempre]),
        "base_sin": y[sin_siempre].mean(),
        "tasas": tasas,
    }


def main():
    parser = argparse.ArgumentParser(description="Compara dos versiones.")
    parser.add_argument("--a", nargs=2, metavar=("VERSION", "DATASET"),
                        required=True)
    parser.add_argument("--b", nargs=2, metavar=("VERSION", "DATASET"),
                        required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--report", required=True,
                        help="Informe donde se inserta la comparación")
    args = parser.parse_args()

    (va, da), (vb, db) = args.a, args.b
    a = evaluar(da, args.model_dir, va)
    b = evaluar(db, args.model_dir, vb)

    def fila(nombre, fa, fb):
        return f"| {nombre} | {fa(a)} | {fb(b) if fb else fa(b)} |"

    pct = lambda clave: (lambda r: f"{r[clave] * 100:.1f} %")  # noqa: E731
    num = lambda clave: (lambda r: f"{r[clave]:,}")  # noqa: E731
    dec = lambda clave: (lambda r: f"{r[clave]:.3f}")  # noqa: E731
    lineas = [
        f"## Comparación {va} vs {vb}",
        "",
        "Métricas recalculadas con cada modelo guardado sobre la partición "
        "temporal de prueba de su propio dataset. Los datasets no son "
        "iguales, así que las diferencias reflejan sobre todo la corrección "
        "de las etiquetas, no una mejora del modelo.",
        "",
        f"| Indicador | {va} | {vb} |",
        "|---|---:|---:|",
        fila("Modelo seleccionado (misma regla de selección)",
             lambda r: r["modelo"], None),
        fila("Filas etiquetadas", num("filas"), None),
        fila("Filas ambiguas conservadas (excluidas del entrenamiento)",
             num("ambiguas"), None),
        fila("Repositorios", num("repositorios"), None),
        fila("Workflows", num("workflows"), None),
        fila("% de fallos (y = 1)", pct("fallos"), None),
        fila("Filas de prueba", num("prueba"), None),
        fila("% de fallos en prueba", pct("fallos_prueba"), None),
        fila("PR-AUC (prueba)", dec("pr_auc"), None),
        fila("ROC-AUC (prueba)", dec("roc_auc"), None),
        fila("PR-AUC sin workflows que siempre fallan", dec("pr_auc_sin"),
             None),
        fila("Tasa base sin workflows que siempre fallan", pct("base_sin"),
             None),
    ]
    for nivel in ["bajo", "medio", "alto"]:
        lineas.append(fila(
            f"Tasa de fallos observada en nivel {nivel} (ejecuciones)",
            lambda r, n=nivel: (f"{r['tasas'].loc[n, 'mean'] * 100:.1f} % "
                                f"({int(r['tasas'].loc[n, 'size'])})"),
            None))
    lineas += [""]

    ruta = Path(args.report)
    texto = ruta.read_text(encoding="utf-8")
    marcador = "## 1. Selección del modelo"
    inicio = texto.find(f"## Comparación {va} vs {vb}")
    if inicio != -1:
        texto = texto[:inicio] + texto[texto.find(marcador):]
    texto = texto.replace(marcador, "\n".join(lineas) + "\n" + marcador, 1)
    ruta.write_text(texto, encoding="utf-8")
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
