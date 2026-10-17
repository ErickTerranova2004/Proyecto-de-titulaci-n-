#!/usr/bin/env python3
"""Inspección de GADFPD (Mendeley, DOI 10.17632/mggwn7rj9f.1).

Uso: python inspect_gadfpd.py archivo.csv [--out informe_gadfpd.md]

Las columnas ESPERADAS provienen del artículo (Data in Brief 68:113128), no de
haber visto el CSV. El informe indica cuáles existen realmente. Todo lo
"detectado" es una pista que debe confirmarse manualmente.
"""
import argparse, re
import pandas as pd

ESPERADAS = ["run_id", "workflow_id", "status", "conclusion", "duration", "event",
             "run_attempt", "created_at", "updated_at", "commit_sha", "total_churn",
             "files_modified", "msg_len", "is_merge", "time_since_last_commit"]
# Se conocen solo tras ejecutar el workflow -> no usar como predictoras
POSTERIORES = ["duration", "updated_at", "status", "conclusion"]
CORTE_GHA = pd.Timestamp("2024-05-01", tz="UTC")   # artículo: GHA desde mayo 2024; Travis, ago-dic 2016


def tabla(df):
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return df.to_string(index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("--out", default="informe_gadfpd.md")
    ap.add_argument("--sep", default=","); ap.add_argument("--encoding", default="utf-8")
    a = ap.parse_args()
    df = pd.read_csv(a.csv, sep=a.sep, encoding=a.encoding, low_memory=False)
    o = []; w = o.append
    w(f"# Informe GADFPD: `{a.csv}`\n")
    w(f"Filas: **{len(df):,}** | Columnas: **{df.shape[1]}** (el artículo declara 303.079 filas)\n")

    w("## 1. Columnas esperadas vs. reales\n")
    reales = set(df.columns)
    w("- Presentes: " + ", ".join(f"`{c}`" for c in ESPERADAS if c in reales))
    w("- **Ausentes**: " + (", ".join(f"`{c}`" for c in ESPERADAS if c not in reales) or "ninguna"))
    w("- **No documentadas en el artículo**: " + (", ".join(f"`{c}`" for c in df.columns if c not in ESPERADAS) or "ninguna"))
    repo_cols = [c for c in df.columns if re.search(r"repo|project|slug|owner", c, re.I)]
    plat_cols = [c for c in df.columns if re.search(r"platform|source|origin|ci_?system|provider", c, re.I)]
    w(f"- Columna de repositorio detectada: {repo_cols or '**NINGUNA** (impide validación agrupada por repositorio)'}")
    w(f"- Columna de plataforma/origen detectada: {plat_cols or '**NINGUNA** (separar Travis/Actions solo sería posible por fecha)'}\n")

    w("## 2. Diccionario de datos (ejemplos reales del CSV)\n")
    dic = pd.DataFrame({
        "Columna": df.columns,
        "Tipo": [str(t) for t in df.dtypes],
        "Nulos": df.isna().sum().values,
        "% nulos": (df.isna().mean() * 100).round(2).values,
        "Únicos": [df[c].nunique(dropna=True) for c in df.columns],
        "Ejemplo real": [str(df[c].dropna().iloc[0])[:40] if df[c].notna().any() else "" for c in df.columns],
        "¿Posterior a la ejecución?": ["SÍ (fuga)" if c in POSTERIORES else "revisar" for c in df.columns],
    })
    w(tabla(dic) + "\n")

    w("## 3. Duplicados\n")
    w(f"- Filas completas duplicadas: **{int(df.duplicated().sum()):,}**")
    if "run_id" in df:
        w(f"- `run_id` repetido: **{int(df['run_id'].duplicated().sum()):,}** (sobre {df['run_id'].notna().sum():,})")
    if "commit_sha" in df:
        vc = df["commit_sha"].value_counts()
        w(f"- Commits distintos: {len(vc):,}; commits con >1 fila: {int((vc > 1).sum()):,}; "
          f"máx. filas por commit: {int(vc.max())} (mismas métricas de código repetidas)")
    w("")

    t = None
    if "created_at" in df:
        t = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        w("## 4. Cobertura temporal y separación Travis / GitHub Actions (HIPÓTESIS)\n")
        w(f"- `created_at` parseable: {t.notna().mean() * 100:.2f}% | rango: {t.min()} → {t.max()}")
        per = pd.Series(["≥ 2024-05 (GHA probable)" if x >= CORTE_GHA else "< 2024-05 (Travis probable)"
                         for x in t.dropna()]).value_counts()
        w("\n" + tabla(per.rename_axis("Periodo").reset_index(name="filas")))
        w("\nSi hay filas entre ene-2017 y abr-2024, o fechas inválidas, la separación por fecha NO es limpia.\n")

    if "conclusion" in df:
        w("## 5. Etiqueta `conclusion`\n")
        vc = df["conclusion"].value_counts(dropna=False)
        w(tabla(pd.DataFrame({"conclusion": vc.index.astype(str), "n": vc.values,
                              "%": (vc.values / len(df) * 100).round(2)})) + "\n")
        sf = df[df["conclusion"].astype(str).str.lower().isin(["success", "failure"])]
        if len(sf):
            fr = (sf["conclusion"].astype(str).str.lower() == "failure").mean() * 100
            w(f"Fallo entre success+failure: **{fr:.2f}%** ({len(sf):,} filas utilizables binarias)\n")
            if t is not None:
                tt = t.loc[sf.index]
                g = pd.DataFrame({"periodo": ["GHA probable" if (x >= CORTE_GHA) else "Travis probable/otro" for x in tt.fillna(pd.Timestamp('1970-01-01', tz='UTC'))],
                                  "fallo": (sf["conclusion"].astype(str).str.lower() == "failure").values})
                w(tabla(g.groupby("periodo")["fallo"].agg(filas="size", tasa_fallo="mean").round(4).reset_index()) + "\n")
        if "status" in df:
            w("**Cruce `status` × `conclusion`** (en GitHub, `status` no debería contener 'failure'):\n")
            w(tabla(pd.crosstab(df["status"].astype(str), df["conclusion"].astype(str)).reset_index()) + "\n")
        if "event" in df:
            w("**Tasa de fallo por `event` (success+failure)**:\n")
            e = sf.assign(f=(sf["conclusion"].astype(str).str.lower() == "failure"))
            w(tabla(e.groupby("event")["f"].agg(filas="size", tasa_fallo="mean").round(4).sort_values("filas", ascending=False).head(15).reset_index()) + "\n")

    w("## 6. Registros inválidos o inconsistentes\n")
    if {"created_at", "updated_at"} <= reales:
        u = pd.to_datetime(df["updated_at"], errors="coerce", utc=True)
        w(f"- `updated_at` < `created_at`: {int((u < t).sum()):,}")
    if "duration" in df:
        d = pd.to_numeric(df["duration"], errors="coerce")
        w(f"- `duration` negativa: {int((d < 0).sum()):,}; > 1 día: {int((d > 86400).sum()):,}; > 1 año: {int((d > 31536000).sum()):,}")
    for c in ["total_churn", "files_modified", "msg_len", "time_since_last_commit"]:
        if c in df:
            x = pd.to_numeric(df[c], errors="coerce")
            w(f"- `{c}`: negativos {int((x < 0).sum()):,}; no numéricos {int(x.isna().sum() - df[c].isna().sum()):,}")
    w("")

    w("## 7. Resumen numérico\n")
    num = df.select_dtypes("number")
    if not num.empty:
        w(tabla(num.describe().T.round(3).reset_index().rename(columns={"index": "columna"})) + "\n")

    w("## 8. Correlación entre numéricas (posible redundancia)\n")
    cand = [c for c in ["total_churn", "files_modified", "msg_len", "time_since_last_commit", "duration"] if c in df]
    if len(cand) > 1:
        w(tabla(df[cand].apply(pd.to_numeric, errors="coerce").corr(method="spearman").round(3).reset_index()) + "\n")

    w("## 9. Recordatorio de interpretación\n")
    w("`conclusion` describe el resultado de un workflow run. NO es evidencia de fallo de un despliegue en producción.\n")
    open(a.out, "w", encoding="utf-8").write("\n".join(o))
    print("Informe escrito en", a.out)


if __name__ == "__main__":
    main()
