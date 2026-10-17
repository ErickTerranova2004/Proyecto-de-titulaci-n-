#!/usr/bin/env python3
"""Inspección en streaming de GHALogs: runs.json.gz y repositories.json.gz (JSON Lines + gzip).

Uso:
  python inspect_ghalogs.py --runs runs.json.gz --repos repositories.json.gz \
         [--limit 0] [--out informe_ghalogs.md]
--limit N procesa solo las primeras N líneas (0 = todo). Memoria acotada: solo contadores.
Esquema por registro (según el ejemplo oficial del repositorio D2KLab/gha-dataset):
  _id, repository_name, workflow_path, run_number, run_attempt, metadata{...API run...},
  logs_archive, total_logs_size, log_insights.
"""
import argparse, collections as C, gzip, json, statistics as S

def abrir(p):
    return gzip.open(p, "rt", encoding="utf-8", errors="replace") if p.endswith(".gz") else open(p, encoding="utf-8")

def tabla(rows, cols):
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs"); ap.add_argument("--repos")
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--out", default="informe_ghalogs.md")
    a = ap.parse_args()
    o = []; w = o.append
    w("# Informe GHALogs\n")

    if a.runs:
        n = bad = 0
        top = C.Counter(); meta = C.Counter()
        concl = C.Counter(); status = C.Counter(); event = C.Counter(); cross = C.Counter()
        per_wf = C.Counter(); repos = set(); ids = set(); dup = 0
        dmin = dmax = None; attempt = C.Counter(); pr_runs = 0; head_missing = 0; deploy_keys = set()
        with abrir(a.runs) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                if a.limit and n >= a.limit: break
                try: r = json.loads(line)
                except Exception: bad += 1; continue
                n += 1
                top.update(r.keys())
                m = r.get("metadata") or {}
                meta.update(m.keys())
                for k in list(r.keys()) + list(m.keys()):
                    if "deploy" in k.lower() or "environment" in k.lower(): deploy_keys.add(k)
                c, s, e = m.get("conclusion"), m.get("status"), m.get("event")
                concl[c] += 1; status[s] += 1; event[e] += 1; cross[(e, c)] += 1
                attempt[r.get("run_attempt")] += 1
                rid = r.get("_id")
                if rid in ids: dup += 1
                else: ids.add(rid)
                per_wf[(r.get("repository_name"), r.get("workflow_path"))] += 1
                repos.add(r.get("repository_name"))
                if m.get("pull_requests"): pr_runs += 1
                if not m.get("head_sha"): head_missing += 1
                d = m.get("created_at")
                if d: dmin = d if dmin is None or d < dmin else dmin; dmax = d if dmax is None or d > dmax else dmax
        w("## 1. Runs\n")
        w(f"- Líneas válidas: **{n:,}** | líneas con error de parseo: **{bad:,}** | `_id` duplicados: **{dup:,}**")
        w(f"- Repositorios distintos: {len(repos):,} | workflows distintos: {len(per_wf):,}")
        if per_wf:
            v = list(per_wf.values())
            w(f"- Runs por workflow: media {S.mean(v):.2f}, mediana {S.median(v)}, máx {max(v)} "
              "(pocos runs por workflow limitan series temporales por workflow)")
        w(f"- Rango `metadata.created_at`: {dmin} → {dmax}")
        w(f"- Runs asociados a pull request (`pull_requests` no vacío): {pr_runs:,} | sin `head_sha`: {head_missing:,}\n")
        w("## 2. Claves presentes (nivel superior y `metadata`)\n")
        w("Nivel superior: " + ", ".join(f"`{k}` ({v:,})" for k, v in top.most_common()))
        w("\n`metadata`: " + ", ".join(f"`{k}` ({v:,})" for k, v in meta.most_common()) + "\n")
        w("**Claves relacionadas con despliegues/entornos:** " + (", ".join(sorted(deploy_keys)) or "NINGUNA detectada") + "\n")
        w("## 3. Etiqueta `metadata.conclusion`\n")
        tot = sum(concl.values()) or 1
        w(tabla([(str(k), f"{v:,}", f"{v / tot * 100:.2f}%") for k, v in concl.most_common()], ["conclusion", "n", "%"]) + "\n")
        sf = concl.get("success", 0) + concl.get("failure", 0)
        if sf: w(f"Fallo entre success+failure: **{concl.get('failure', 0) / sf * 100:.2f}%** ({sf:,} runs)\n")
        w("## 4. `status`\n"); w(tabla([(str(k), f"{v:,}") for k, v in status.most_common()], ["status", "n"]) + "\n")
        w("## 5. Fallo por `event` (success+failure)\n")
        rows = []
        for ev in [k for k, _ in event.most_common(15)]:
            s_, f_ = cross.get((ev, "success"), 0), cross.get((ev, "failure"), 0)
            if s_ + f_: rows.append((str(ev), f"{event[ev]:,}", f"{s_ + f_:,}", f"{f_ / (s_ + f_) * 100:.2f}%"))
        w(tabla(rows, ["event", "runs", "success+failure", "% fallo"]) + "\n")
        w("## 6. `run_attempt`\n"); w(tabla([(str(k), f"{v:,}") for k, v in attempt.most_common(6)], ["run_attempt", "n"]) + "\n")

    if a.repos:
        n = 0; keys = C.Counter(); sel = proc = 0; runs90 = []; nb_runs = []
        with abrir(a.repos) as f:
            for line in f:
                if a.limit and n >= a.limit: break
                try: r = json.loads(line)
                except Exception: continue
                n += 1; keys.update(r.keys())
                sel += bool(r.get("selected")); proc += bool(r.get("processed"))
                if isinstance(r.get("total_runs_90d"), (int, float)): runs90.append(r["total_runs_90d"])
                if isinstance(r.get("nb_runs"), (int, float)): nb_runs.append(r["nb_runs"])
        w("## 7. Repositorios\n")
        w(f"- Registros: **{n:,}** | `selected`: {sel:,} | `processed`: {proc:,}")
        w("- Claves: " + ", ".join(f"`{k}` ({v:,})" for k, v in keys.most_common()))
        if runs90: w(f"- `total_runs_90d`: mediana {S.median(runs90)}, máx {max(runs90)}")
        if nb_runs: w(f"- `nb_runs` (runs recogidos por repo): mediana {S.median(nb_runs)}, máx {max(nb_runs)}")
        w("")
    w("## Recordatorio\n`conclusion` es el resultado de un workflow run, no de un despliegue. "
      "Este dataset no aporta por sí mismo métricas de código (churn, archivos); habría que obtenerlas de la API por `head_sha`.\n")
    open(a.out, "w", encoding="utf-8").write("\n".join(o))
    print("Informe escrito en", a.out)

if __name__ == "__main__":
    main()
