#!/usr/bin/env python3
"""Asigna niveles de evidencia de fallo de despliegue a ejecuciones de GHALogs.

Parte de informes/deploy_runs.csv (generado por find_deploy_runs.py) para
saber qué workflows ejecutaron pasos de despliegue, y vuelve a leer
runs.json.gz para analizar el orden temporal de los pasos.

Señales usadas (validadas manualmente con novuhq/novu y chainsafe/gossamer):
- Actividad posterior: si algún paso de otro job empieza después de que
  terminó el paso de despliegue, el despliegue probablemente terminó bien
  (caso novu: deploy_docs y New Relic corren tras el despliegue).
- Duración anómala: un despliegue que tarda mucho más que en las ejecuciones
  exitosas del mismo workflow sugiere un fallo durante el despliegue
  (caso gossamer: ~1870 s en fallos frente a ~170 s en el éxito).
- Entorno: los despliegues a clústeres efímeros de prueba y las vistas
  previas de pull requests no son despliegues de la aplicación.
"""

import argparse
import collections
import csv
import json
import re
import statistics
from datetime import datetime
from pathlib import Path

from find_deploy_runs import abrir_archivo, tipo_paso

# Indicios de entorno efímero de pruebas dentro de la misma ejecución.
EFIMERO = re.compile(
    r"kind\s+create\s+cluster|minikube\s+start|k3d\s+cluster\s+create"
    r"|localstack|k3s",
    re.IGNORECASE,
)
ACCIONES_EFIMERAS = {
    "helm/kind-action", "engineerd/setup-kind", "container-tools/kind-action",
    "manusa/actions-setup-minikube", "medyagh/setup-minikube",
    "nolar/setup-k3d-k3s", "awshacks/k3d-action", "abiosoft/setup-k3d",
}
EVENTOS_PREVIEW = {"pull_request", "pull_request_target"}

# Un despliegue es anómalo si dura al menos FACTOR veces la mediana de los
# despliegues exitosos del mismo workflow y al menos MARGEN segundos más.
FACTOR_ANOMALIA = 3.0
MARGEN_ANOMALIA = 60.0


def fecha(texto):
    try:
        return datetime.fromisoformat(str(texto))
    except ValueError:
        return None


def analizar(registro):
    """Extrae los pasos de despliegue con su posición y tiempos."""
    jobs = []
    efimero = False
    for job in registro.get("log_insights") or []:
        pasos = []
        for paso in job.get("steps") or []:
            inicio = fecha(paso.get("start_date"))
            duracion = float(paso.get("duration_sec") or 0)
            tipo, nombre = tipo_paso(paso)
            if paso.get("type") == "action":
                accion = f"{paso.get('repository')}/{paso.get('action')}"
                if accion.lower() in ACCIONES_EFIMERAS:
                    efimero = True
            elif EFIMERO.search(str(paso.get("code") or "")):
                efimero = True
            pasos.append({"tipo": tipo, "nombre": nombre,
                          "inicio": inicio, "duracion": duracion})
        jobs.append(pasos)

    despliegues = []
    for j, pasos in enumerate(jobs):
        for i, paso in enumerate(pasos):
            if paso["tipo"] != "despliegue" or paso["inicio"] is None:
                continue
            fin = paso["inicio"].timestamp() + paso["duracion"]
            # ¿Algún paso de otro job empieza después de este despliegue?
            posterior = any(
                p["inicio"] is not None and p["inicio"].timestamp() > fin + 1
                for k, otros in enumerate(jobs) if k != j for p in otros
            )
            despliegues.append({
                "nombre": paso["nombre"],
                "duracion": paso["duracion"],
                "ultimo_del_job": i == len(pasos) - 1,
                "actividad_posterior": posterior,
            })
    return despliegues, efimero


def main():
    parser = argparse.ArgumentParser(
        description="Niveles de evidencia de fallo de despliegue."
    )
    parser.add_argument("--runs", required=True, help="Ruta a runs.json.gz")
    parser.add_argument("--deploy-csv", required=True,
                        help="CSV generado por find_deploy_runs.py")
    parser.add_argument("--out", required=True, help="Informe Markdown")
    parser.add_argument("--csv", required=True, help="CSV de salida")
    args = parser.parse_args()

    with open(args.deploy_csv, encoding="utf-8") as archivo:
        workflows = {(f["repository_name"], f["workflow_path"])
                     for f in csv.DictReader(archivo)}
    print(f"Workflows de despliegue a analizar: {len(workflows):,}")

    ejecuciones = []
    print("Leyendo runs.json.gz...")
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
            if clave not in workflows:
                continue
            meta = registro.get("metadata") or {}
            despliegues, efimero = analizar(registro)
            ejecuciones.append({
                "clave": clave, "meta": meta, "registro": registro,
                "despliegues": despliegues, "efimero": efimero,
            })

    # Duración de referencia: mediana del despliegue más largo de cada
    # ejecución exitosa del mismo workflow.
    referencia = collections.defaultdict(list)
    for e in ejecuciones:
        if e["meta"].get("conclusion") == "success" and e["despliegues"]:
            referencia[e["clave"]].append(
                max(d["duracion"] for d in e["despliegues"]))
    mediana = {k: statistics.median(v) for k, v in referencia.items()}

    conclusiones_wf = collections.defaultdict(collections.Counter)
    for e in ejecuciones:
        conclusiones_wf[e["clave"]][str(e["meta"].get("conclusion"))] += 1

    filas = []
    for e in ejecuciones:
        meta = e["meta"]
        conclusion = str(meta.get("conclusion"))
        despliegues = e["despliegues"]
        evento = str(meta.get("event"))
        ruta = e["clave"][1]

        if e["efimero"]:
            entorno = "efímero de pruebas"
        elif evento in EVENTOS_PREVIEW or "preview" in ruta.lower():
            entorno = "vista previa"
        else:
            entorno = "aplicación"

        base = mediana.get(e["clave"])
        duracion_max = max((d["duracion"] for d in despliegues), default=None)
        anomalo = (base is not None and duracion_max is not None
                   and duracion_max >= FACTOR_ANOMALIA * base
                   and duracion_max - base >= MARGEN_ANOMALIA)
        # Despliegue donde la ejecución pudo detenerse.
        candidato = any(d["ultimo_del_job"] and not d["actividad_posterior"]
                        for d in despliegues)

        if conclusion not in ("success", "failure"):
            nivel = f"excluida ({conclusion})"
        elif not despliegues:
            nivel = ("fallo antes del despliegue" if conclusion == "failure"
                     else "éxito sin despliegue ejecutado")
        elif conclusion == "success":
            nivel = "despliegue exitoso"
        elif candidato and anomalo:
            nivel = "fallo en despliegue - evidencia alta"
        elif candidato and base is None:
            nivel = "fallo en despliegue - evidencia media (sin referencia)"
        elif candidato:
            nivel = "fallo en despliegue - evidencia media"
        elif any(not d["ultimo_del_job"] for d in despliegues):
            nivel = "fallo tras ejecutar el despliegue (paso posterior)"
        else:
            nivel = "fallo en otro job; despliegue completado"

        conteo = conclusiones_wf[e["clave"]]
        registro = e["registro"]
        filas.append({
            "repository_name": e["clave"][0],
            "workflow_path": ruta,
            "run_id": meta.get("id"),
            "run_attempt": registro.get("run_attempt"),
            "created_at": meta.get("created_at"),
            "event": evento,
            "head_branch": meta.get("head_branch"),
            "head_sha": meta.get("head_sha"),
            "conclusion": conclusion,
            "entorno": entorno,
            "pasos_despliegue": "; ".join(sorted({d["nombre"]
                                                  for d in despliegues})),
            "duracion_despliegue_max": duracion_max,
            "mediana_exito_workflow": base,
            "workflow_siempre_falla": (conteo["failure"] > 0
                                       and conteo["failure"]
                                       == sum(conteo.values())),
            "nivel_evidencia": nivel,
        })

    with open(args.csv, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)

    tabla = collections.Counter((f["entorno"], f["nivel_evidencia"])
                                for f in filas)
    entornos = ["aplicación", "vista previa", "efímero de pruebas"]
    niveles = sorted({f["nivel_evidencia"] for f in filas})

    lineas = [
        "# Niveles de evidencia de fallo de despliegue (GHALogs)",
        "",
        "> Etiquetas inferidas a partir de pasos ejecutados (log_insights). "
        "No son resultados confirmados por logs completos. 'Evidencia "
        "alta' = el despliegue fue el último paso de su job, nada empezó "
        "después y duró al menos 3 veces la mediana de los despliegues "
        "exitosos del mismo workflow.",
        "",
        f"- Workflows analizados: {len(workflows):,}",
        f"- Ejecuciones: {len(filas):,}",
        "",
        "## Ejecuciones por nivel de evidencia y tipo de entorno",
        "",
        "| Nivel | " + " | ".join(entornos) + " |",
        "|---|" + "---:|" * len(entornos),
    ]
    for nivel in niveles:
        lineas.append(f"| {nivel} | " + " | ".join(
            f"{tabla[(e, nivel)]:,}" for e in entornos) + " |")

    app = [f for f in filas if f["entorno"] == "aplicación"]
    fallos_alta = [f for f in app
                   if f["nivel_evidencia"].endswith("evidencia alta")]
    fallos_dep = [f for f in app
                  if f["nivel_evidencia"].startswith("fallo en despliegue")]
    exitos = [f for f in app if f["nivel_evidencia"] == "despliegue exitoso"]
    wf_variacion = {
        (f["repository_name"], f["workflow_path"]) for f in fallos_dep
    } & {(f["repository_name"], f["workflow_path"]) for f in exitos}
    persistentes = sum(1 for f in fallos_dep if f["workflow_siempre_falla"])

    lineas += [
        "",
        "## Resumen para la variable objetivo (entorno de aplicación)",
        "",
        f"- Despliegues exitosos: {len(exitos):,}",
        f"- Fallos en despliegue (alta + media): {len(fallos_dep):,}",
        f"- Fallos en despliegue con evidencia alta: {len(fallos_alta):,}",
        f"- Fallos en despliegue de workflows que fallan siempre: "
        f"{persistentes:,}",
        f"- Repositorios con fallos en despliegue: "
        f"{len({f['repository_name'] for f in fallos_dep}):,}",
        f"- Workflows con fallos y éxitos de despliegue: "
        f"{len(wf_variacion):,}",
        "",
        "## Fallos con evidencia alta (entorno de aplicación)",
        "",
        "| Repositorio | Ruta | Fecha | Despliegue (s) | Mediana éxito (s) |",
        "|---|---|---|---:|---:|",
    ]
    for f in sorted(fallos_alta, key=lambda x: (x["repository_name"],
                                                 x["created_at"])):
        lineas.append(
            f"| {f['repository_name']} | {f['workflow_path']} | "
            f"{f['created_at']} | {f['duracion_despliegue_max']:.0f} | "
            f"{f['mediana_exito_workflow']:.0f} |")
    lineas.append("")

    Path(args.out).write_text("\n".join(lineas), encoding="utf-8")
    print(f"Informe generado: {args.out}")
    print(f"CSV generado: {args.csv}")


if __name__ == "__main__":
    main()
