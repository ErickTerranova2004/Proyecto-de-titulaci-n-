#!/usr/bin/env python3
"""Muestra las ejecuciones históricas de un workflow en GHALogs.

Para cada ejecución lista los jobs y pasos que realmente se ejecutaron,
según el campo log_insights. Lee los datos en modo solo lectura.
"""

import argparse
import gzip
import json
from pathlib import Path


def abrir_archivo(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def describir_paso(paso):
    """Resume un paso: la acción usada o la primera línea útil del script."""
    if paso.get("type") == "action":
        return (f"acción {paso.get('repository')}/{paso.get('action')}"
                f"@{paso.get('version')}")
    codigo = str(paso.get("code") or "")
    lineas = [x.strip() for x in codigo.splitlines()
              if x.strip() and not x.strip().startswith("#")]
    primera = lineas[0] if lineas else "(sin código)"
    return f"shell: {primera[:110]}"


def main():
    parser = argparse.ArgumentParser(
        description="Lista ejecuciones históricas y pasos de un workflow."
    )
    parser.add_argument("--runs", required=True, help="Ruta a runs.json.gz")
    parser.add_argument("--repo", required=True,
                        help="Repositorio, por ejemplo owner/name")
    parser.add_argument("--path", required=True,
                        help="Ruta del workflow, por ejemplo "
                             ".github/workflows/deploy.yml")
    parser.add_argument("--out", required=True, help="Informe Markdown")
    args = parser.parse_args()

    repo_buscado = args.repo.lower()
    ejecuciones = []

    print("Leyendo registros locales de GHALogs...")
    with abrir_archivo(args.runs) as archivo:
        for linea in archivo:
            if not linea.strip():
                continue
            try:
                registro = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if str(registro.get("repository_name", "")).lower() != repo_buscado:
                continue
            if registro.get("workflow_path") != args.path:
                continue
            ejecuciones.append(registro)

    ejecuciones.sort(key=lambda r: (r.get("metadata") or {}).get(
        "created_at", ""))
    print(f"Ejecuciones encontradas: {len(ejecuciones)}")

    lineas = [
        f"# Ejecuciones históricas: {args.repo} / {args.path}",
        "",
        f"- Ejecuciones encontradas en GHALogs: {len(ejecuciones)}",
        "",
        "> Los jobs y pasos provienen de log_insights (ejecución real de "
        "2023). Un job ausente normalmente no se ejecutó o no generó log. "
        "El campo 'errors' de un paso son errores de análisis del script, "
        "no el resultado del paso.",
        "",
    ]

    for registro in ejecuciones:
        meta = registro.get("metadata") or {}
        commit = meta.get("head_commit") or {}
        mensaje = str(commit.get("message") or "").splitlines()
        lineas += [
            f"## Ejecución #{registro.get('run_number')} "
            f"(intento {registro.get('run_attempt')})",
            "",
            f"- id: {meta.get('id')}",
            f"- created_at: {meta.get('created_at')}",
            f"- event: {meta.get('event')} | rama: {meta.get('head_branch')}",
            f"- conclusion: **{meta.get('conclusion')}**",
            f"- head_sha: {meta.get('head_sha')}",
            f"- mensaje del commit: {mensaje[0] if mensaje else ''}",
            f"- html_url: {meta.get('html_url')}",
            "",
        ]
        insights = registro.get("log_insights") or []
        if not insights:
            lineas += ["Sin log_insights para esta ejecución.", ""]
            continue
        for job in insights:
            pasos = job.get("steps") or []
            duracion = sum(float(p.get("duration_sec") or 0) for p in pasos)
            lineas.append(f"### Job (archivo de log): {job.get('file')} "
                          f"- {len(pasos)} pasos, {duracion:.0f} s")
            if job.get("error"):
                lineas.append(f"- error al procesar el log: {job.get('error')}")
            for paso in pasos:
                lineas.append(f"- {describir_paso(paso)} "
                              f"({float(paso.get('duration_sec') or 0):.1f} s)")
            lineas.append("")

    salida = Path(args.out)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Informe generado: {salida}")


if __name__ == "__main__":
    main()
