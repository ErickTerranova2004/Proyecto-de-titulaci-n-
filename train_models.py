#!/usr/bin/env python3
"""Entrena y evalúa modelos de riesgo de despliegue.

- Selección del modelo con validación cruzada agrupada por repositorio
  dentro del conjunto de entrenamiento (nunca con el conjunto de prueba).
- Evaluación final en la partición temporal de prueba (25 % más reciente)
  y, como análisis secundario, en repositorios no vistos (GroupKFold).
- Probabilidades calibradas (sigmoide) y niveles de riesgo definidos por
  riesgo relativo frente a la tasa base de entrenamiento.
- Explicaciones con SHAP para el modelo seleccionado.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import shap  # noqa: E402
from lightgbm import LGBMClassifier  # noqa: E402
from sklearn.base import clone  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV, calibration_curve  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.dummy import DummyClassifier  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score, average_precision_score, balanced_accuracy_score,
    brier_score_loss, confusion_matrix, f1_score, log_loss,
    matthews_corrcoef, precision_recall_curve, precision_score,
    recall_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import GroupKFold  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, StandardScaler  # noqa: E402
from sklearn.tree import DecisionTreeClassifier  # noqa: E402

SEMILLA = 42
CATEGORICAS = ["event"]
NUMERICAS = [
    "msg_len", "msg_lineas", "msg_merge", "msg_revert", "msg_fix",
    "msg_feat", "msg_deps", "msg_docs", "msg_ci", "autor_bot",
    "reejecutado_por_otro", "rama_principal", "rama_bot", "rama_tag",
    "tiene_pr", "es_reintento", "hora_utc", "dia_semana", "fin_de_semana",
    "retraso_commit_run_min", "wf_n_prev", "wf_tasa_fallo_prev",
    "wf_ultimo_fallo", "wf_horas_desde_ultimo", "wf_duracion_media_prev_min",
    "repo_n_prev", "repo_tasa_fallo_prev", "repo_n_workflows_prev",
]
HISTORIAL = [c for c in NUMERICAS if c.startswith(("wf_", "repo_"))]


def preprocesador(numericas, escalar):
    pasos = [("imputar", SimpleImputer(strategy="median",
                                        add_indicator=True))]
    if escalar:
        pasos.append(("escalar", StandardScaler()))
    return ColumnTransformer([
        ("num", Pipeline(pasos), numericas),
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist",
                              min_frequency=20), CATEGORICAS),
    ])


def modelos(numericas):
    return {
        "Base: tasa de fallos (Dummy)": Pipeline([
            ("prep", preprocesador(numericas, False)),
            ("modelo", DummyClassifier(strategy="prior"))]),
        "Regresión logística": Pipeline([
            ("prep", preprocesador(numericas, True)),
            ("modelo", LogisticRegression(max_iter=2000, C=0.5))]),
        "Árbol de decisión": Pipeline([
            ("prep", preprocesador(numericas, False)),
            ("modelo", DecisionTreeClassifier(max_depth=4,
                                              min_samples_leaf=30,
                                              random_state=SEMILLA))]),
        "Random Forest": Pipeline([
            ("prep", preprocesador(numericas, False)),
            ("modelo", RandomForestClassifier(
                n_estimators=400, min_samples_leaf=10, n_jobs=-1,
                random_state=SEMILLA))]),
        "LightGBM": Pipeline([
            ("prep", preprocesador(numericas, False)),
            ("modelo", LGBMClassifier(
                n_estimators=300, learning_rate=0.03, num_leaves=15,
                min_child_samples=30, subsample=0.8, subsample_freq=1,
                colsample_bytree=0.8, random_state=SEMILLA, verbose=-1))]),
    }


def regla_historial(df, tasa_base):
    """Regla sencilla: la tasa de fallos previa del workflow."""
    return df["wf_tasa_fallo_prev"].fillna(tasa_base).to_numpy()


def calibrado(modelo, grupos_cv):
    return CalibratedClassifierCV(modelo, method="sigmoid", cv=grupos_cv)


def oof(modelo, X, y, grupos, n=5):
    """Probabilidades fuera de pliegue con GroupKFold por repositorio."""
    pred = np.zeros(len(y))
    for tr, va in GroupKFold(n_splits=n).split(X, y, grupos):
        m = clone(modelo).fit(X.iloc[tr], y.iloc[tr])
        pred[va] = m.predict_proba(X.iloc[va])[:, 1]
    return pred


def metricas(y, p, umbral):
    pred = (p >= umbral).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "PR-AUC": average_precision_score(y, p),
        "ROC-AUC": roc_auc_score(y, p),
        "Brier": brier_score_loss(y, p),
        "LogLoss": log_loss(y, np.clip(p, 1e-6, 1 - 1e-6)),
        "Precision": precision_score(y, pred, zero_division=0),
        "Recall": recall_score(y, pred, zero_division=0),
        "F1": f1_score(y, pred, zero_division=0),
        "MCC": matthews_corrcoef(y, pred),
        "Balanced acc.": balanced_accuracy_score(y, pred),
        "Accuracy": accuracy_score(y, pred),
        "TN": tn, "FP": fp, "FN": fn, "TP": tp,
    }


def umbral_f1(y, p):
    prec, rec, umbrales = precision_recall_curve(y, p)
    f1 = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    return float(umbrales[np.argmax(f1[:-1])])


def ic_bootstrap(y, p, funcion, n=1000):
    rng = np.random.default_rng(SEMILLA)
    y = np.asarray(y)
    valores = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].min() == y[idx].max():
            continue
        valores.append(funcion(y[idx], p[idx]))
    return np.percentile(valores, [2.5, 97.5])


def nivel_riesgo(p, limite_medio, limite_alto):
    return np.where(p >= limite_alto, "alto",
                    np.where(p >= limite_medio, "medio", "bajo"))


def tabla_md(df, decimales=3):
    cols = list(df.columns)
    lineas = ["| " + " | ".join([df.index.name or ""] + cols) + " |",
              "|---|" + "---:|" * len(cols)]
    for idx, fila in df.iterrows():
        valores = [f"{v:.{decimales}f}" if isinstance(v, float) else str(v)
                   for v in fila]
        lineas.append("| " + " | ".join([str(idx)] + valores) + " |")
    return lineas


def main():
    parser = argparse.ArgumentParser(description="Entrena modelos.")
    parser.add_argument("--data", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--fig-dir", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--version", default="v1",
                        help="Versión del modelo, p. ej. v1 o v1.1")
    args = parser.parse_args()

    df = pd.read_csv(args.data, parse_dates=["run_started_at"])
    # Desde v1.1 el dataset conserva filas ambiguas (y vacío) que no se
    # usan para entrenar ni evaluar. En v1 no existen.
    if "ambiguo" in df.columns:
        df = df[df["ambiguo"] == 0].copy()
    df = df.dropna(subset=["y"]).reset_index(drop=True)
    df["y"] = df["y"].astype(int)
    version = args.version
    archivo_version = version.replace(".", "_")
    sufijo = "" if version == "v1" else f"_{archivo_version}"
    figuras = Path(args.fig_dir)
    figuras.mkdir(parents=True, exist_ok=True)
    columnas = CATEGORICAS + NUMERICAS
    train = df[df.particion == "entrenamiento"].reset_index(drop=True)
    test = df[df.particion == "prueba"].reset_index(drop=True)
    Xtr, ytr, gtr = train[columnas], train["y"], train["repo_id"]
    Xte, yte = test[columnas], test["y"]
    tasa_base = float(ytr.mean())
    cv = list(GroupKFold(n_splits=5).split(Xtr, ytr, gtr))

    # 1) Selección en entrenamiento (OOF agrupado por repositorio).
    print("Validación cruzada en entrenamiento...")
    seleccion = {}
    oof_preds = {}
    for nombre, modelo in modelos(NUMERICAS).items():
        p = oof(calibrado(modelo, 5), Xtr, ytr, gtr)
        oof_preds[nombre] = p
        seleccion[nombre] = {
            "PR-AUC": average_precision_score(ytr, p),
            "ROC-AUC": roc_auc_score(ytr, p),
            "Brier": brier_score_loss(ytr, p),
        }
    p_regla = regla_historial(train, tasa_base)
    seleccion["Regla: tasa de fallos previa del workflow"] = {
        "PR-AUC": average_precision_score(ytr, p_regla),
        "ROC-AUC": roc_auc_score(ytr, p_regla),
        "Brier": brier_score_loss(ytr, p_regla),
    }
    tabla_sel = pd.DataFrame(seleccion).T
    tabla_sel.index.name = "Modelo"
    candidatos = tabla_sel.drop(
        index=["Base: tasa de fallos (Dummy)",
               "Regla: tasa de fallos previa del workflow"])
    mejor = candidatos["PR-AUC"].idxmax()
    print(f"Modelo seleccionado: {mejor}")

    # 2) Entrenamiento final y evaluación en prueba temporal.
    resultados = {}
    probs_test = {}
    umbrales = {}
    finales = {}
    for nombre, modelo in modelos(NUMERICAS).items():
        final = calibrado(modelo, cv).fit(Xtr, ytr)
        finales[nombre] = final
        p = final.predict_proba(Xte)[:, 1]
        probs_test[nombre] = p
        umbrales[nombre] = (umbral_f1(ytr, oof_preds[nombre])
                            if nombre != "Base: tasa de fallos (Dummy)"
                            else 0.5)
        resultados[nombre] = metricas(yte, p, umbrales[nombre])
    nombre_regla = "Regla: tasa de fallos previa del workflow"
    p_regla_te = regla_historial(test, tasa_base)
    probs_test[nombre_regla] = p_regla_te
    umbrales[nombre_regla] = umbral_f1(ytr, p_regla)
    resultados[nombre_regla] = metricas(yte, p_regla_te,
                                        umbrales[nombre_regla])
    tabla_test = pd.DataFrame(resultados).T
    tabla_test.index.name = "Modelo"

    p_mejor = probs_test[mejor]
    ic_pr = ic_bootstrap(yte, p_mejor, average_precision_score)
    ic_roc = ic_bootstrap(yte, p_mejor, roc_auc_score)
    ic_pr_regla = ic_bootstrap(yte, p_regla_te, average_precision_score)

    # 3) Generalización a repositorios no vistos (todo el dataset).
    print("GroupKFold por repositorio en todo el dataset...")
    Xall, yall, gall = df[columnas], df["y"], df["repo_id"]
    p_grupo = oof(calibrado(modelos(NUMERICAS)[mejor], 5), Xall, yall, gall)
    p_grupo_regla = regla_historial(df, float(yall.mean()))

    # 4) Ablación: sin variables de historial.
    sin_hist = [c for c in NUMERICAS if c not in HISTORIAL]
    abl = calibrado(modelos(sin_hist)[mejor], cv).fit(
        train[CATEGORICAS + sin_hist], ytr)
    p_abl = abl.predict_proba(test[CATEGORICAS + sin_hist])[:, 1]

    # 5) Niveles de riesgo por riesgo relativo (definidos en entrenamiento).
    limite_medio, limite_alto = tasa_base, 2 * tasa_base
    niveles_te = nivel_riesgo(p_mejor, limite_medio, limite_alto)
    tabla_niveles = (pd.DataFrame({"nivel": niveles_te, "y": yte})
                     .groupby("nivel")["y"].agg(["size", "mean"])
                     .reindex(["bajo", "medio", "alto"]))

    # 6) Figuras.
    fig, ejes = plt.subplots(1, 3, figsize=(16, 4.8))
    for nombre in [mejor, "Regresión logística", nombre_regla,
                   "Base: tasa de fallos (Dummy)"]:
        p = probs_test[nombre]
        prec, rec, _ = precision_recall_curve(yte, p)
        ejes[0].plot(rec, prec, label=nombre)
        fpr, tpr, _ = roc_curve(yte, p)
        ejes[1].plot(fpr, tpr, label=nombre)
    ejes[0].axhline(yte.mean(), ls=":", c="grey")
    ejes[0].set(xlabel="Recall", ylabel="Precision",
                title="Curva precision-recall (prueba)")
    ejes[1].plot([0, 1], [0, 1], ls=":", c="grey")
    ejes[1].set(xlabel="Tasa de falsos positivos",
                ylabel="Tasa de verdaderos positivos", title="Curva ROC (prueba)")
    frac, media = calibration_curve(yte, p_mejor, n_bins=8,
                                    strategy="quantile")
    ejes[2].plot(media, frac, "o-", label=mejor)
    ejes[2].plot([0, 1], [0, 1], ls=":", c="grey")
    ejes[2].set(xlabel="Probabilidad predicha", ylabel="Frecuencia observada",
                title="Calibración (prueba)")
    for eje in ejes:
        eje.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figuras / f"curvas_evaluacion{sufijo}.png", dpi=150)
    plt.close(fig)

    # 7) SHAP del modelo seleccionado (sin calibración: misma ordenación).
    base = clone(modelos(NUMERICAS)[mejor]).fit(Xtr, ytr)
    prep = base.named_steps["prep"]
    nombres = list(prep.get_feature_names_out())
    Xte_t = pd.DataFrame(prep.transform(Xte), columns=nombres)
    estimador = base.named_steps["modelo"]
    if isinstance(estimador, LogisticRegression):
        Xtr_t = pd.DataFrame(prep.transform(Xtr), columns=nombres)
        explicador = shap.LinearExplainer(estimador, Xtr_t)
    else:
        explicador = shap.TreeExplainer(estimador)
    valores = explicador(Xte_t)
    if valores.values.ndim == 3:
        valores = valores[:, :, 1]
    importancia = (pd.Series(np.abs(valores.values).mean(0), index=nombres)
                   .sort_values(ascending=False))
    plt.figure()
    shap.plots.beeswarm(valores, max_display=15, show=False)
    plt.tight_layout()
    plt.savefig(figuras / f"shap_resumen{sufijo}.png", dpi=150,
                bbox_inches="tight")
    plt.close("all")

    # 8) Guardar el modelo seleccionado con sus metadatos.
    modelos_dir = Path(args.model_dir)
    modelos_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(finales[mejor],
                modelos_dir / f"modelo_riesgo_{archivo_version}.joblib")
    joblib.dump(base,
                modelos_dir / f"modelo_riesgo_{archivo_version}_shap.joblib")
    meta = {
        "version": version,
        "modelo": mejor,
        "fecha_entrenamiento": datetime.now(timezone.utc).isoformat(),
        "variables_categoricas": CATEGORICAS,
        "variables_numericas": NUMERICAS,
        "tasa_base_entrenamiento": tasa_base,
        "limites_riesgo": {"medio": limite_medio, "alto": limite_alto},
        "umbral_f1": umbrales[mejor],
        "metricas_prueba": {k: float(v) for k, v in
                            resultados[mejor].items()},
        "filas_entrenamiento": int(len(train)),
        "filas_prueba": int(len(test)),
        "etiqueta": "despliegue_no_completado (ver fase2_variable_objetivo.md)",
    }
    (modelos_dir / f"modelo_riesgo_{archivo_version}.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # 9) Informe.
    cols_test = ["PR-AUC", "ROC-AUC", "Brier", "Precision", "Recall", "F1",
                 "MCC", "Balanced acc.", "Accuracy", "TN", "FP", "FN", "TP"]
    r = resultados[mejor]
    lineas = [
        f"# Fase 5. Modelos de riesgo de despliegue ({version})",
        "",
        f"- Datos: `{args.data}` | entrenamiento: {len(train):,} filas "
        f"({ytr.mean() * 100:.1f} % positivos) | prueba temporal: "
        f"{len(test):,} filas ({yte.mean() * 100:.1f} % positivos).",
        "- Etiqueta: despliegue no completado (ver "
        "`fase2_variable_objetivo.md`).",
        "- Todas las probabilidades están calibradas (sigmoide, validación "
        "agrupada por repositorio).",
        "",
        "## 1. Selección del modelo (solo entrenamiento, validación "
        "cruzada agrupada por repositorio)",
        "",
    ]
    lineas += tabla_md(tabla_sel)
    lineas += [
        "",
        f"**Seleccionado por PR-AUC: {mejor}.** La selección se hizo sin "
        "usar el conjunto de prueba. Las diferencias de PR-AUC entre "
        "regresión logística, árbol, Random Forest y LightGBM en esta "
        "validación son pequeñas frente a la variabilidad esperable con "
        "este tamaño de muestra; el modelo seleccionado no se cambia tras "
        "ver los resultados de prueba para evitar sesgo de selección. "
        "(El ROC-AUC del Dummy difiere de 0,5 porque cada pliegue predice "
        "una constante distinta.)",
        "",
        "## 2. Evaluación en la partición temporal de prueba",
        "",
        "El umbral de clasificación se eligió maximizando F1 en las "
        "predicciones fuera de pliegue del entrenamiento.",
        "",
    ]
    lineas += tabla_md(tabla_test[cols_test])
    lineas += [
        "",
        f"- {mejor}: PR-AUC {r['PR-AUC']:.3f} (IC 95 % bootstrap "
        f"{ic_pr[0]:.3f}–{ic_pr[1]:.3f}); ROC-AUC {r['ROC-AUC']:.3f} "
        f"(IC 95 % {ic_roc[0]:.3f}–{ic_roc[1]:.3f}).",
        f"- Regla de historial: PR-AUC "
        f"{resultados[nombre_regla]['PR-AUC']:.3f} (IC 95 % "
        f"{ic_pr_regla[0]:.3f}–{ic_pr_regla[1]:.3f}).",
        f"- Matriz de confusión ({mejor}, umbral {umbrales[mejor]:.3f}): "
        f"TN={r['TN']}, FP={r['FP']}, FN={r['FN']}, TP={r['TP']}.",
        f"- Por qué la exactitud no basta: un modelo que siempre predice "
        f"'completado' obtiene una exactitud de {1 - yte.mean():.3f} y no "
        "detecta ningún fallo.",
        "",
        "## 3. Generalización a repositorios no vistos (GroupKFold, todo "
        "el dataset)",
        "",
        f"- {mejor}: PR-AUC {average_precision_score(yall, p_grupo):.3f}, "
        f"ROC-AUC {roc_auc_score(yall, p_grupo):.3f} (tasa base "
        f"{yall.mean():.3f}).",
        f"- Regla de historial: PR-AUC "
        f"{average_precision_score(yall, p_grupo_regla):.3f}, ROC-AUC "
        f"{roc_auc_score(yall, p_grupo_regla):.3f}.",
        "",
        "## 4. Ablación: sin variables de historial",
        "",
        f"- {mejor} sin historial: PR-AUC "
        f"{average_precision_score(yte, p_abl):.3f}, ROC-AUC "
        f"{roc_auc_score(yte, p_abl):.3f} (prueba temporal).",
        "",
        "## 4b. Sensibilidad: sin workflows que fallan siempre",
        "",
        "Se excluyen de la evaluación las ejecuciones de workflows cuyas "
        "ejecuciones observadas fallaron todas (configuración rota "
        "persistente). La exclusión solo se aplica a la evaluación; el "
        "indicador usa información futura y no es una variable del modelo.",
        "",
        "| Modelo | Filas | Tasa base | PR-AUC | ROC-AUC |",
        "|---|---:|---:|---:|---:|",
    ]
    mascara = ~test["workflow_siempre_falla"].astype(bool).to_numpy()
    for nombre in dict.fromkeys([mejor, "Regresión logística",
                                 "Random Forest", "LightGBM", nombre_regla]):
        p = probs_test[nombre][mascara]
        lineas.append(
            f"| {nombre} | {mascara.sum():,} | {yte[mascara].mean():.3f} | "
            f"{average_precision_score(yte[mascara], p):.3f} | "
            f"{roc_auc_score(yte[mascara], p):.3f} |")
    lineas += [
        "",
        "## 5. Niveles de riesgo",
        "",
        f"Definidos por riesgo relativo frente a la tasa base de "
        f"entrenamiento ({tasa_base:.3f}): **bajo** si p < "
        f"{limite_medio:.3f}; **medio** si {limite_medio:.3f} ≤ p < "
        f"{limite_alto:.3f} (hasta 2 veces la tasa base); **alto** si p ≥ "
        f"{limite_alto:.3f}. La validación en prueba muestra la tasa de "
        "fallos observada en cada nivel:",
        "",
        "| Nivel | Ejecuciones | Tasa de fallos observada |",
        "|---|---:|---:|",
    ]
    for nivel, fila in tabla_niveles.iterrows():
        tamano = 0 if pd.isna(fila["size"]) else int(fila["size"])
        tasa = "—" if pd.isna(fila["mean"]) else f"{fila['mean'] * 100:.1f} %"
        lineas.append(f"| {nivel} | {tamano:,} | {tasa} |")
    lineas += [
        "",
        "## 6. Explicabilidad (SHAP, conjunto de prueba)",
        "",
        "Media del valor SHAP absoluto (contribución a la predicción del "
        "modelo, no causalidad):",
        "",
        "| Variable | Media de |SHAP| |",
        "|---|---:|",
    ]
    lineas += [f"| {k} | {v:.4f} |" for k, v in importancia.head(15).items()]
    lineas += [
        "",
        f"Figuras: `figuras/curvas_evaluacion{sufijo}.png`, "
        f"`figuras/shap_resumen{sufijo}.png`.",
        "",
        "## 7. Limitaciones",
        "",
        "- Dataset pequeño (pocos miles de filas) y periodo corto "
        "(jul–nov 2023): intervalos de confianza amplios.",
        "- Historial limitado a un máximo de 5 ejecuciones por workflow en "
        "GHALogs.",
        "- Sin métricas del cambio de código (churn); se incorporarán con "
        "la API de GitHub.",
        "- La etiqueta mide si el intento de despliegue se completó, no "
        "incidentes en producción.",
        "",
    ]
    Path(args.report).write_text("\n".join(lineas), encoding="utf-8")
    print(f"Informe: {args.report}")


if __name__ == "__main__":
    main()
