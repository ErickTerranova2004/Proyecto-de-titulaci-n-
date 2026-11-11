#!/usr/bin/env python3
"""Entrena y evalúa el modelo v2 con el dataset congelado de 198 repositorios.

Diseño (fijado antes de ver resultados, según la propuesta de la tesis):
- Modelos: Random Forest y XGBoost, con hiperparámetros fijos (sin búsqueda),
  y la línea base «predecir siempre y=0».
- Clases desbalanceadas (~10 % de y=1): pesos balanceados.
  Random Forest con class_weight="balanced"; XGBoost con
  scale_pos_weight = n(y=0) / n(y=1) del conjunto con que se entrena.
- Evaluación: GroupKFold de 5 pliegues por repositorio (ningún repositorio
  aparece a la vez en entrenamiento y evaluación).
- Probabilidades calibradas (sigmoide). Los pesos balanceados inflan la
  probabilidad de y=1; la calibración se ajusta con predicciones fuera de
  pliegue sin pesos y la devuelve a la escala real, que es la que mide Brier
  y la que ve el usuario en la plataforma.
- Todo lo que se ajusta (modelo, calibración y umbral) se ajusta solo con
  los pliegues de entrenamiento: dentro de cada pliegue externo hay un
  GroupKFold interno de 5 por repositorio.
- Umbral de clasificación: el que maximiza F1 en las predicciones internas
  fuera de pliegue. Se usa para recall y F1.
- Métricas: PR-AUC (principal), recall de y=1, F1 y Brier; además
  precisión y ROC-AUC. Se dan en el conjunto de las predicciones fuera de
  pliegue, con media y desviación entre pliegues, e IC 95 % por bootstrap de
  repositorios (se remuestrean repositorios, no ejecuciones).
- Regla de selección: se elige XGBoost solo si su PR-AUC supera al de
  Random Forest y el IC 95 % de la diferencia (bootstrap pareado por
  repositorio) no incluye 0. Si no, Random Forest: sus valores SHAP están en
  la escala de probabilidad, que es la que ya muestra la plataforma.
- El modelo final se entrena con todo el dataset y se guarda con los
  metadatos que lee la plataforma (backend/riesgo/services/predictor.py).

No hay curva de aprendizaje: el dataset está congelado.

Uso:
    backend/venv/Scripts/python.exe -X utf8 entrenar_modelos_v2.py
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np  # noqa: E402

try:  # Las figuras son opcionales: el venv del backend no trae matplotlib.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
import pandas as pd  # noqa: E402
import shap  # noqa: E402
from sklearn.base import clone  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV, calibration_curve  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    average_precision_score, brier_score_loss, f1_score, precision_recall_curve,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupKFold, cross_val_predict  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder  # noqa: E402
from xgboost import XGBClassifier  # noqa: E402

SEMILLA = 42
PLIEGUES = 5
BOOTSTRAP = 1000
CATEGORICAS = ["event"]
# 32 numéricas + event. Respecto a v1.1: sin reejecutado_por_otro (no se
# conoce antes del despliegue) ni rama_bot (constante en el dataset) y con el
# tamaño del cambio y los checks del
# commit. Misma lista que scripts/construir_dataset_v2.py.
NUMERICAS = [
    "msg_len", "msg_lineas", "msg_merge", "msg_revert", "msg_fix",
    "msg_feat", "msg_deps", "msg_docs", "msg_ci", "autor_bot",
    "rama_principal", "rama_tag", "tiene_pr", "es_reintento",
    "hora_utc", "dia_semana", "fin_de_semana", "retraso_commit_run_min",
    "archivos_modificados", "lineas_anadidas", "lineas_borradas",
    "checks_n_prev", "checks_fallidos_prev", "checks_tasa_fallo_prev",
    "wf_n_prev", "wf_tasa_fallo_prev", "wf_ultimo_fallo",
    "wf_horas_desde_ultimo", "wf_duracion_media_prev_min",
    "repo_n_prev", "repo_tasa_fallo_prev", "repo_n_workflows_prev",
]
COLUMNAS = CATEGORICAS + NUMERICAS
RF, XGB, BASE = "Random Forest", "XGBoost", "Base: siempre y=0"
METRICAS = ["PR-AUC", "Recall y=1", "F1", "Brier", "Precisión", "ROC-AUC"]


def preprocesador():
    """Igual que v1.1: la plataforma traduce los nombres num__/cat__ a la
    variable original para mostrar los factores SHAP."""
    return ColumnTransformer([
        ("num", SimpleImputer(strategy="median", add_indicator=True), NUMERICAS),
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist",
                              min_frequency=20), CATEGORICAS),
    ])


def modelo(nombre, y):
    if nombre == RF:
        estimador = RandomForestClassifier(
            n_estimators=500, min_samples_leaf=10, max_features="sqrt",
            class_weight="balanced", n_jobs=-1, random_state=SEMILLA)
    else:
        estimador = XGBClassifier(
            n_estimators=400, learning_rate=0.05, max_depth=4,
            min_child_weight=5, subsample=0.8, colsample_bytree=0.8,
            reg_lambda=1.0, tree_method="hist", eval_metric="logloss",
            scale_pos_weight=float((y == 0).sum() / max((y == 1).sum(), 1)),
            n_jobs=-1, random_state=SEMILLA)
    return Pipeline([("prep", preprocesador()), ("modelo", estimador)])


def ajustar(nombre, X, y, grupos):
    """Modelo calibrado y umbral F1, usando solo (X, y).

    ensemble=False: un único modelo entrenado con todos los datos y una
    calibración sigmoide ajustada con sus predicciones fuera de pliegue
    (GroupKFold por repositorio). El modelo base es el que explica SHAP.
    """
    pliegues = list(GroupKFold(n_splits=PLIEGUES).split(X, y, grupos))
    base = modelo(nombre, y)
    calibrado = CalibratedClassifierCV(base, method="sigmoid", cv=pliegues,
                                       ensemble=False).fit(X, y)
    crudo = cross_val_predict(clone(base), X, y, cv=pliegues,
                              method="predict_proba")[:, 1]
    p_interna = calibrado.calibrated_classifiers_[0].calibrators[0].predict(crudo)
    return calibrado, umbral_f1(y, p_interna)


def umbral_f1(y, p):
    prec, rec, umbrales = precision_recall_curve(y, p)
    f1 = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    return float(umbrales[np.argmax(f1[:-1])])


def metricas(y, p, pred):
    return {
        "PR-AUC": average_precision_score(y, p),
        "Recall y=1": recall_score(y, pred, zero_division=0),
        "F1": f1_score(y, pred, zero_division=0),
        "Brier": brier_score_loss(y, p),
        "Precisión": precision_score(y, pred, zero_division=0),
        "ROC-AUC": roc_auc_score(y, p) if len(np.unique(p)) > 1 else 0.5,
    }


def bootstrap_repos(df, oof, n=BOOTSTRAP):
    """IC 95 % remuestreando repositorios. Devuelve los IC de cada modelo y
    de la diferencia XGBoost − Random Forest (pareada: mismas réplicas)."""
    rng = np.random.default_rng(SEMILLA)
    indices = df.groupby("repositorio").indices
    repos = list(indices)
    y = df["y"].to_numpy()
    replicas = {m: {k: [] for k in METRICAS} for m in oof}
    diferencias = {"PR-AUC": [], "Brier": []}
    for _ in range(n):
        idx = np.concatenate([indices[r] for r in rng.choice(repos, len(repos))])
        if y[idx].min() == y[idx].max():
            continue
        valores = {m: metricas(y[idx], o["p"][idx], o["pred"][idx])
                   for m, o in oof.items()}
        for m, v in valores.items():
            for k in METRICAS:
                replicas[m][k].append(v[k])
        for k in diferencias:
            diferencias[k].append(valores[XGB][k] - valores[RF][k])
    ic = {m: {k: np.percentile(v, [2.5, 97.5]) for k, v in r.items()}
          for m, r in replicas.items()}
    ic_dif = {k: np.percentile(v, [2.5, 97.5]) for k, v in diferencias.items()}
    return ic, ic_dif


def evaluar(df):
    X, y, grupos = df[COLUMNAS], df["y"].to_numpy(), df["repositorio"].to_numpy()
    oof = {m: {"p": np.zeros(len(df)), "pred": np.zeros(len(df), dtype=int)}
           for m in (BASE, RF, XGB)}
    por_pliegue = []
    externos = GroupKFold(n_splits=PLIEGUES).split(X, y, grupos)
    for k, (tr, te) in enumerate(externos, 1):
        print(f"Pliegue externo {k}/{PLIEGUES}", flush=True)
        # Línea base: clase 0 siempre; probabilidad = tasa de y=1 del entrenamiento.
        oof[BASE]["p"][te] = y[tr].mean()
        for nombre in (RF, XGB):
            calibrado, umbral = ajustar(nombre, X.iloc[tr], y[tr], grupos[tr])
            p = calibrado.predict_proba(X.iloc[te])[:, 1]
            oof[nombre]["p"][te] = p
            oof[nombre]["pred"][te] = (p >= umbral).astype(int)
        for nombre, o in oof.items():
            por_pliegue.append({"pliegue": k, "modelo": nombre,
                                "filas": len(te), "y=1": int(y[te].sum()),
                                **metricas(y[te], o["p"][te], o["pred"][te])})
    return oof, pd.DataFrame(por_pliegue)


def elegir(total, ic_dif):
    mejora = total.loc[XGB, "PR-AUC"] - total.loc[RF, "PR-AUC"]
    if mejora > 0 and ic_dif["PR-AUC"][0] > 0:
        return XGB, (f"XGBoost supera a Random Forest en PR-AUC por {mejora:+.3f} y el IC 95 % "
                     f"de la diferencia ({ic_dif['PR-AUC'][0]:+.3f} a {ic_dif['PR-AUC'][1]:+.3f}) "
                     "no incluye 0.")
    return RF, (f"La diferencia de PR-AUC XGBoost − Random Forest es {mejora:+.3f} (IC 95 % "
                f"{ic_dif['PR-AUC'][0]:+.3f} a {ic_dif['PR-AUC'][1]:+.3f}); como XGBoost no es "
                "mejor con claridad, se elige Random Forest (regla fijada antes de evaluar).")


def importancia_shap(base, X):
    prep, estimador = base.named_steps["prep"], base.named_steps["modelo"]
    nombres = list(prep.get_feature_names_out())
    Xt = pd.DataFrame(prep.transform(X), columns=nombres)
    valores = shap.TreeExplainer(estimador)(Xt)
    if valores.values.ndim == 3:
        valores = valores[:, :, 1]
    importancia = (pd.Series(np.abs(valores.values).mean(0), index=nombres)
                   .sort_values(ascending=False))
    return valores, importancia


def figuras(df, oof, elegido, carpeta):
    y = df["y"].to_numpy()
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4.6))
    for nombre, o in oof.items():
        prec, rec, _ = precision_recall_curve(y, o["p"])
        ejes[0].plot(rec, prec, label=f"{nombre} (PR-AUC {average_precision_score(y, o['p']):.3f})")
    ejes[0].set(xlabel="Recall (y=1)", ylabel="Precisión",
                title="Precision-recall (fuera de pliegue, GroupKFold)")
    for nombre in (RF, XGB):
        frac, media = calibration_curve(y, oof[nombre]["p"], n_bins=8, strategy="quantile")
        ejes[1].plot(media, frac, "o-", label=nombre)
    ejes[1].plot([0, 1], [0, 1], ls=":", c="grey")
    ejes[1].set(xlabel="Probabilidad predicha", ylabel="Frecuencia observada de y=1",
                title="Calibración (fuera de pliegue)")
    for eje in ejes:
        eje.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(carpeta / "curvas_evaluacion_v2.png", dpi=150)
    plt.close(fig)


def tabla(filas, columnas, formato="{:.3f}"):
    lineas = ["| " + " | ".join(columnas) + " |", "|---|" + "---:|" * (len(columnas) - 1)]
    for f in filas:
        lineas.append("| " + " | ".join(
            formato.format(v) if isinstance(v, float) else str(v) for v in f) + " |")
    return lineas


def informe(ruta, df, total, por_pliegue, ic, ic_dif, elegido, motivo, meta,
            importancia, niveles):
    y1 = int(df["y"].sum())
    l = ["# Fase 5. Modelo de riesgo de despliegue v2 (dataset de 198 repositorios)", "",
         f"- Datos: `{meta['dataset']}` (SHA-256 `{meta['dataset_sha256'][:12]}…`): "
         f"{len(df):,} ejecuciones de {df['repositorio'].nunique()} repositorios; "
         f"y=1 {y1} ({100 * y1 / len(df):.1f} %).",
         "- Etiqueta: despliegue a producción no completado (`fase2_variable_objetivo.md`, reglas 7 a 9). "
         "Precisión de etiquetas medida a mano en una muestra aleatoria (semilla 2027): 47/49 "
         "(IC 95 % Wilson 86,3–98,9 %).",
         "- Evaluación: GroupKFold de 5 pliegues por repositorio. Modelo, calibración y umbral se "
         "ajustan solo con los pliegues de entrenamiento (GroupKFold interno de 5).",
         "- Pesos de clase balanceados; probabilidades calibradas (sigmoide).", "",
         "## 1. Resultados (predicciones fuera de pliegue)", ""]
    filas = []
    for m in (BASE, RF, XGB):
        filas.append([m] + [f"{total.loc[m, k]:.3f} ({ic[m][k][0]:.3f}–{ic[m][k][1]:.3f})"
                            for k in METRICAS])
    l += tabla(filas, ["Modelo"] + [f"{k} (IC 95 %)" for k in METRICAS])
    l += ["", "IC 95 % por bootstrap de repositorios (1.000 réplicas). La línea base predice "
          "siempre y=0 (recall y F1 = 0) con probabilidad igual a la tasa de y=1 del entrenamiento; "
          "su PR-AUC es la prevalencia.", "", "### Variación entre pliegues (media ± desviación)", ""]
    resumen = por_pliegue.groupby("modelo")[METRICAS].agg(["mean", "std"])
    l += tabla([[m] + [f"{resumen.loc[m, (k, 'mean')]:.3f} ± {resumen.loc[m, (k, 'std')]:.3f}"
                       for k in METRICAS] for m in (BASE, RF, XGB)], ["Modelo"] + METRICAS)
    l += ["", "## 2. Selección", "",
          f"Diferencia XGBoost − Random Forest: PR-AUC IC 95 % {ic_dif['PR-AUC'][0]:+.3f} a "
          f"{ic_dif['PR-AUC'][1]:+.3f}; Brier IC 95 % {ic_dif['Brier'][0]:+.4f} a {ic_dif['Brier'][1]:+.4f}.",
          "", f"**Modelo elegido: {elegido}.** {motivo}", "",
          "## 3. Modelo final", "",
          f"Entrenado con todo el dataset. Umbral F1 (fuera de pliegue): {meta['umbral_f1']:.3f}. "
          f"Niveles de riesgo por riesgo relativo a la tasa base ({meta['tasa_base_entrenamiento']:.3f}): "
          f"bajo < {meta['limites_riesgo']['medio']:.3f} ≤ medio < {meta['limites_riesgo']['alto']:.3f} ≤ alto.",
          "", "Tasa de y=1 observada por nivel (predicciones fuera de pliegue del modelo elegido):", ""]
    l += tabla([[n, int(r["size"]) if r["size"] == r["size"] else 0,
                 f"{100 * r['mean']:.1f} %" if r["mean"] == r["mean"] else "—"]
                for n, r in niveles.iterrows()],
               ["Nivel", "Ejecuciones", "Tasa de y=1"])
    escala = ("probabilidad (del modelo con pesos balanceados, antes de calibrar)"
              if elegido == RF else "log-odds (margen de XGBoost, antes de calibrar)")
    l += ["", "## 4. Explicabilidad (SHAP del modelo final)", "",
          f"TreeExplainer exacto sobre el modelo base. Escala de los valores: {escala}. La "
          "calibración sigmoide es monótona: no cambia el signo ni el orden de las contribuciones. "
          "Media del valor SHAP absoluto (asociación aprendida, no causalidad):", ""]
    l += tabla([[k, float(v)] for k, v in importancia.head(15).items()],
               ["Variable", "Media de |SHAP|"], "{:.4f}")
    l += ["", "Figuras: `figuras/curvas_evaluacion_v2.png`, `figuras/shap_resumen_v2.png`. "
          "Detalle por pliegue: `informes/fase5_v2_pliegues.csv`.", "",
          "## 5. Variables y limitaciones", "",
          f"- {len(NUMERICAS)} variables numéricas y `event`, calculadas con la misma función en el "
          "entrenamiento y en la plataforma (`variables_desde_datos`, "
          "`backend/riesgo/services/features.py`), solo con información anterior al inicio del "
          "despliegue (`backend/riesgo/tests/test_variables_v2.py`).",
          "- Respecto a v1.1: se quita `reejecutado_por_otro` (no se conoce antes del despliegue); "
          "`tiene_pr` y `es_reintento` se calculan igual en ambos lados; se añaden el tamaño del cambio "
          "y los checks del commit.",
          "- **Vulnerabilidades y cobertura no se pueden obtener** con un token de solo lectura en "
          "repositorios de terceros: las alertas de seguridad exigen permisos de administración y la "
          "cobertura no la publica GitHub. Las pruebas fallidas se aproximan con los checks del commit "
          "y los bugs, solo de forma indirecta, con el mensaje del commit "
          "(`informes/fase2_variable_objetivo.md`, sección 7).",
          "- La etiqueta mide si el intento de despliegue a producción se completó, no incidentes "
          "posteriores en producción."]
    ruta.write_text("\n".join(l) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Entrena el modelo v2.")
    parser.add_argument("--data", default="datos_procesados/dataset_riesgo_despliegue_v2.csv")
    parser.add_argument("--model-dir", default="modelos")
    parser.add_argument("--fig-dir", default="figuras")
    parser.add_argument("--report", default="informes/fase5_modelos_v2.md")
    args = parser.parse_args()

    datos = Path(args.data)
    df = pd.read_csv(datos).dropna(subset=["y"]).reset_index(drop=True)
    df["y"] = df["y"].astype(int)

    # 1) Evaluación con GroupKFold por repositorio.
    oof, por_pliegue = evaluar(df)
    y = df["y"].to_numpy()
    total = pd.DataFrame({m: metricas(y, o["p"], o["pred"]) for m, o in oof.items()}).T
    ic, ic_dif = bootstrap_repos(df, oof)
    elegido, motivo = elegir(total, ic_dif)
    print(f"Modelo elegido: {elegido}. {motivo}")

    # 2) Modelo final con todo el dataset.
    final, umbral = ajustar(elegido, df[COLUMNAS], y, df["repositorio"].to_numpy())
    base = final.calibrated_classifiers_[0].estimator  # modelo sin calibrar (SHAP)
    tasa_base = float(y.mean())
    limites = {"medio": tasa_base, "alto": 2 * tasa_base}
    p_oof = oof[elegido]["p"]
    niveles = (pd.DataFrame({"nivel": np.where(p_oof >= limites["alto"], "alto",
                                               np.where(p_oof >= limites["medio"], "medio", "bajo")),
                             "y": y})
               .groupby("nivel")["y"].agg(["size", "mean"]).reindex(["bajo", "medio", "alto"]))

    # 3) SHAP y figuras.
    carpeta = Path(args.fig_dir)
    carpeta.mkdir(parents=True, exist_ok=True)
    valores, importancia = importancia_shap(base, df[COLUMNAS])
    if plt is not None:
        plt.figure()
        shap.plots.beeswarm(valores, max_display=15, show=False)
        plt.tight_layout()
        plt.savefig(carpeta / "shap_resumen_v2.png", dpi=150, bbox_inches="tight")
        plt.close("all")
        figuras(df, oof, elegido, carpeta)
    else:
        print("matplotlib no está instalado: no se generan las figuras.")

    # 4) Guardar el modelo y sus metadatos (formato que lee la plataforma).
    modelos_dir = Path(args.model_dir)
    modelos_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(final, modelos_dir / "modelo_riesgo_v2.joblib")
    joblib.dump(base, modelos_dir / "modelo_riesgo_v2_shap.joblib")
    meta = {
        "version": "v2", "modelo": elegido, "motivo_seleccion": motivo,
        "fecha_entrenamiento": datetime.now(timezone.utc).isoformat(),
        "dataset": str(datos).replace("\\", "/"),
        "dataset_sha256": hashlib.sha256(datos.read_bytes()).hexdigest(),
        "variables_categoricas": CATEGORICAS, "variables_numericas": NUMERICAS,
        "tasa_base_entrenamiento": tasa_base, "limites_riesgo": limites,
        "umbral_f1": umbral, "pesos_clase": "balanceados",
        "escala_shap": "probabilidad" if elegido == RF else "log-odds",
        "validacion": f"GroupKFold {PLIEGUES} por repositorio (anidado)",
        "metricas_validacion": {m: {k: float(v) for k, v in total.loc[m].items()}
                                for m in total.index},
        "filas_entrenamiento": int(len(df)),
        "repositorios": int(df["repositorio"].nunique()),
    }
    (modelos_dir / "modelo_riesgo_v2.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    por_pliegue.to_csv("informes/fase5_v2_pliegues.csv", index=False)
    informe(Path(args.report), df, total, por_pliegue, ic, ic_dif, elegido, motivo,
            meta, importancia, niveles)
    print(f"Informe: {args.report}")


if __name__ == "__main__":
    main()
