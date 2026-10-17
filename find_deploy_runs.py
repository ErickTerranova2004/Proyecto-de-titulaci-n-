#!/usr/bin/env python3
"""Busca ejecuciones de GHALogs en las que se ejecutó un paso de despliegue.

No se basa en el nombre del workflow, sino en los pasos registrados en
log_insights (acciones y comandos que realmente se ejecutaron en 2023).
Lee los datos en modo solo lectura.

Supuesto verificado en stratospheric-dev/stratospheric: los pasos omitidos
no aparecen en log_insights. Por eso, en una ejecución fallida, el último
paso registrado de un job suele ser el que falló, salvo que existan pasos
posteriores con if: always() o if: failure().
"""

import argparse
import collections
import csv
import gzip
import json
import re
from pathlib import Path

# Acciones que despliegan en un entorno (repositorio/acción en minúsculas).
ACCIONES_DESPLIEGUE = {
    "aws-actions/amazon-ecs-deploy-task-definition",
    "aws-actions/aws-cloudformation-github-deploy",
    "azure/webapps-deploy",
    "azure/functions-action",
    "azure/k8s-deploy",
    "azure/arm-deploy",
    "azure/container-apps-deploy-action",
    "google-github-actions/deploy-cloudrun",
    "google-github-actions/deploy-appengine",
    "google-github-actions/deploy-cloud-functions",
    "firebaseextended/action-hosting-deploy",
    "amondnet/vercel-action",
    "nwtgck/actions-netlify",
    "akhileshns/heroku-deploy",
    "superfly/flyctl-actions",
    "serverless/github-action",
    "cloudflare/wrangler-action",
    "einaregilsson/beanstalk-deploy",
    "digitalocean/app_action",
    "easingthemes/ssh-deploy",
    "appleboy/ssh-action",
}

# Comandos de shell que despliegan en un entorno.
COMANDOS_DESPLIEGUE = re.compile(
    r"kubectl\s+(apply|set\s+image|rollout\s+restart)"
    r"|helm\s+(upgrade|install)"
    r"|terraform\s+apply"
    r"|cdk\s+deploy|service:deploy"
    r"|(serverless|sls)\s+deploy"
    r"|fly(ctl)?\s+deploy"
    r"|vercel\s+(deploy|--prod)"
    r"|netlify\s+deploy"
    r"|firebase\s+deploy"
    r"|gcloud\s+(run|app|functions)\s+deploy"
    r"|az\s+(webapp|functionapp)\s+.*deploy"
    r"|aws\s+ecs\s+update-service"
    r"|aws\s+deploy\s+create-deployment"
    r"|\beb\s+deploy"
    r"|git\s+push\s+heroku"
    r"|wrangler\s+(deploy|publish)"
    r"|kamal\s+deploy"
    r"|docker\s+stack\s+deploy",
    re.IGNORECASE,
)

# Publicación de sitios estáticos en GitHub Pages: se cuenta aparte.
ACCIONES_PAGES = {
    "actions/deploy-pages",
    "peaceiris/actions-gh-pages",
    "jamesives/github-pages-deploy-action",
    "crazy-max/ghaction-github-pages",
}


def abrir_archivo(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def tipo_paso(paso):
    """Devuelve ('despliegue'|'pages'|None, descripción)."""
    if paso.get("type") == "action":
        nombre = f"{paso.get('repository')}/{paso.get('action')}".lower()
        if nombre in ACCIONES_DESPLIEGUE:
            return "despliegue", nombre
        if nombre in ACCIONES_PAGES:
            return "pages", nombre
        return None, nombre
    codigo = str(paso.get("code") or "")
    encontrado = COMANDOS_DESPLIEGUE.search(codigo)
    if encontrado:
        return "despliegue", f"shell: {encontrado.group(0)}"
    return None, "shell"


def analizar_ejecucion(registro):
    """Ubica los pasos de despliegue y si alguno es el último de su job."""
    pasos_despliegue = []
    ultimo_es_despliegue = False
    hay_pages = False
    for job in registro.get("log_insights") or []:
        pasos = job.get("steps") or []
        for posicion, paso in enumerate(pasos):
            tipo, descripcion = tipo_paso(paso)
            if tipo == "pages":
                hay_pages = True
            if tipo == "despliegue":
                pasos_despliegue.append(descripcion)
                if posicion == len(pasos) - 1:
                    ultimo_es_despliegue = True
    return pasos_despliegue, ultimo_es_despliegue, hay_pages


def categoria(conclusion, despliega, ultimo_es_despliegue):
    """Categoría de evidencia para ejecuciones de un workflow de despliegue."""
    if despliega and conclusion == "success":
        return "despliegue ejecutado; workflow exitoso"
    if despliega and conclusion == "failure" and ultimo_es_despliegue:
        return "fallo probable en el paso de despliegue"
    if despliega and conclusion == "failure":
        return "despliegue ejecutado; fallo en otro paso (antes o después)"
    if not despliega and conclusion == "failure":
        return "fallo antes de llegar al despliegue"
    if not despliega and conclusion == "success":
        return "workflow exitoso sin paso de despliegue ejecutado"
    return f"otro resultado ({conclusion})"


def main():
    parser = argparse.ArgumentParser(
        description="Busca ejecuciones con pasos de despliegue reales."
    )
    parser.add_argument("--runs", required=True, help="Ruta a runs.json.gz")
    parser.add_argument("--out", required=True, help="Informe Markdown")
    parser.add_argument("--csv", required=True,
                        help="CSV con las ejecuciones de workflows de "
                             "despliegue")
    args = parser.parse_args()

    # Primera lectura: workflows donde alguna ejecución desplegó.
    print("Lectura 1/2: buscando pasos de despliegue...")
    registros = 0
    sin_insights = 0
    workflows_despliegue = set()
    runs_pages = 0
    with abrir_archivo(args.runs) as archivo:
        for linea in archivo:
            if not linea.strip():
                continue
            try:
                registro = json.loads(linea)
            except json.JSONDecodeError:
                continue
            registros += 1
            if not registro.get("log_insights"):
                sin_insights += 1
                continue
            pasos, _, hay_pages = analizar_ejecucion(registro)
            if hay_pages:
                runs_pages += 1
            if pasos:
                workflows_despliegue.add(
                    (registro.get("repository_name"),
                     registro.get("workflow_path")))

    print(f"Registros: {registros:,} | workflows de despliegue: "
          f"{len(workflows_despliegue):,}")

    # Segunda lectura: todas las ejecuciones de esos workflows.
    print("Lectura 2/2: clasificando ejecuciones de esos workflows...")
    filas = []
    with abrir_archivo(args.runs) as archivo:
        for linea in archivo:
            if not linea.strip():
                continue
            try:
                registro = json.loads(linea)
            except json.JSONDecodeError:
                continue
            clave = (registro.get("repository_name"),
                     registro.get("workflow_path"))
            if clave not in workflows_despliegue:
                continue
            meta = registro.get("metadata") or {}
            pasos, ultimo, _ = analizar_ejecucion(registro)
            conclusion = str(meta.get("conclusion"))
            filas.append({
                "repository_name": clave[0],
                "workflow_path": clave[1],
                "run_id": meta.get("id"),
                "run_number": registro.get("run_number"),
                "run_attempt": registro.get("run_attempt"),
                "created_at": meta.get("created_at"),
                "event": meta.get("event"),
                "head_branch": meta.get("head_branch"),
                "head_sha": meta.get("head_sha"),
                "conclusion": conclusion,
                "tiene_log_insights": bool(registro.get("log_insights")),
                "pasos_despliegue": "; ".join(sorted(set(pasos))),
                "despliegue_es_ultimo_paso": ultimo,
                "categoria_evidencia": categoria(conclusion, bool(pasos),
                                                 ultimo),
            })

    Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
    with open(args.csv, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)

    por_categoria = collections.Counter(f["categoria_evidencia"]
                                        for f in filas)
    por_mecanismo = collections.Counter()
    for f in filas:
        for paso in filter(None, f["pasos_despliegue"].split("; ")):
            por_mecanismo[paso] += 1
    repos = {f["repository_name"] for f in filas}

    por_workflow = collections.defaultdict(collections.Counter)
    for f in filas:
        por_workflow[(f["repository_name"], f["workflow_path"])][
            f["categoria_evidencia"]] += 1
    con_fallo_despliegue = sorted(
        ((k, c) for k, c in por_workflow.items()
         if c["fallo probable en el paso de despliegue"]),
        key=lambda x: -x[1]["fallo probable en el paso de despliegue"],
    )

    lineas = [
        "# Ejecuciones con pasos de despliegue reales (GHALogs)",
        "",
        "> Clasificación basada en los pasos ejecutados registrados en "
        "log_insights, no en el nombre del workflow. Los patrones pueden "
        "omitir mecanismos de despliegue propios (scripts internos). "
        "'Fallo probable en el paso de despliegue' es una heurística: el "
        "paso de despliegue fue el último registrado en su job.",
        "",
        f"- Registros leídos: {registros:,}",
        f"- Registros sin log_insights (no clasificables): {sin_insights:,}",
        f"- Ejecuciones con publicación en GitHub Pages (excluidas): "
        f"{runs_pages:,}",
        f"- Workflows con al menos un paso de despliegue ejecutado: "
        f"{len(workflows_despliegue):,}",
        f"- Repositorios: {len(repos):,}",
        f"- Ejecuciones de esos workflows: {len(filas):,}",
        "",
        "## Ejecuciones por categoría de evidencia",
        "",
        "| Categoría | Ejecuciones |",
        "|---|---:|",
    ]
    lineas += [f"| {k} | {v:,} |" for k, v in por_categoria.most_common()]
    lineas += [
        "",
        "## Mecanismos de despliegue detectados",
        "",
        "| Mecanismo | Ejecuciones |",
        "|---|---:|",
    ]
    lineas += [f"| {k} | {v:,} |" for k, v in por_mecanismo.most_common(30)]
    lineas += [
        "",
        "## Workflows con fallos probables en el paso de despliegue",
        "",
        "| Repositorio | Ruta | Categorías |",
        "|---|---|---|",
    ]
    for (repo, ruta), conteo in con_fallo_despliegue[:40]:
        detalle = ", ".join(f"{k}: {v}" for k, v in conteo.most_common())
        lineas.append(f"| {repo} | {ruta} | {detalle} |")
    lineas.append("")

    Path(args.out).write_text("\n".join(lineas), encoding="utf-8")
    print(f"Informe generado: {args.out}")
    print(f"CSV generado: {args.csv}")


if __name__ == "__main__":
    main()
