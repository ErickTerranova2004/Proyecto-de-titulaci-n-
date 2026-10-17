
#!/usr/bin/env python3
"""Busca posibles workflows de despliegue en GHALogs.
No etiqueta automáticamente ninguna ejecución como despliegue real.
"""

import argparse
import collections
import gzip
import json
import re
from pathlib import Path


KEYWORDS = re.compile(
    r"deploy|deployment|release|publish|production|staging|"
    r"rollout|ship|delivery|entrega|despliegue|produccion",
    re.IGNORECASE,
)


def abrir_archivo(path):
    if path.endswith(".gz"):
        return gzip.open(
            path, "rt", encoding="utf-8", errors="replace"
        )
    return open(path, "r", encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", required=True)
    parser.add_argument("--out", default="informe_deploy_candidates.md")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    total = 0
    errores = 0
    candidatos = 0

    por_campo = collections.Counter()
    por_resultado = collections.Counter()
    por_evento = collections.Counter()
    workflows = collections.Counter()
    ejemplos = []

    with abrir_archivo(args.runs) as archivo:
        for linea in archivo:
            if not linea.strip():
                continue

            if args.limit and total >= args.limit:
                break

            try:
                registro = json.loads(linea)
            except json.JSONDecodeError:
                errores += 1
                continue

            total += 1
            metadata = registro.get("metadata") or {}

            campos = {
                "workflow_path": registro.get("workflow_path"),
                "metadata.name": metadata.get("name"),
                "metadata.path": metadata.get("path"),
                "metadata.display_title": metadata.get("display_title"),
            }

            coincidencias = []
            for campo, valor in campos.items():
                texto = str(valor or "")
                if KEYWORDS.search(texto):
                    coincidencias.append(campo)
                    por_campo[campo] += 1

            if not coincidencias:
                continue

            candidatos += 1

            ruta = (
                registro.get("workflow_path")
                or metadata.get("path")
                or "(sin ruta)"
            )
            nombre = metadata.get("name") or "(sin nombre)"
            conclusion = metadata.get("conclusion") or "(sin resultado)"
            evento = metadata.get("event") or "(sin evento)"

            workflows[(str(ruta), str(nombre))] += 1
            por_resultado[str(conclusion)] += 1
            por_evento[str(evento)] += 1

            if len(ejemplos) < 30:
                ejemplos.append({
                    "repo": registro.get("repository_name"),
                    "ruta": ruta,
                    "nombre": nombre,
                    "titulo": metadata.get("display_title"),
                    "resultado": conclusion,
                    "evento": evento,
                    "head_sha": metadata.get("head_sha"),
                    "logs_archive_presente": bool(
                        registro.get("logs_archive")
                    ),
                    "coincidencias": ", ".join(coincidencias),
                })

    lineas = [
        "# Informe de posibles workflows de despliegue",
        "",
        "> Las coincidencias son candidatas para revisión, no pruebas "
        "de que se haya realizado un despliegue.",
        "",
        f"- Registros JSON válidos procesados: {total:,}",
        f"- Errores de parseo: {errores:,}",
        f"- Registros con coincidencias: {candidatos:,}",
        "",
        "## Coincidencias por campo",
        "",
        "| Campo | Registros coincidentes |",
        "|---|---:|",
    ]

    for campo, cantidad in por_campo.most_common():
        lineas.append(f"| {campo} | {cantidad:,} |")

    lineas += [
        "",
        "## Resultados de las ejecuciones candidatas",
        "",
        "| Conclusion | Cantidad |",
        "|---|---:|",
    ]

    for resultado, cantidad in por_resultado.most_common():
        lineas.append(f"| {resultado} | {cantidad:,} |")

    lineas += [
        "",
        "## Eventos de las ejecuciones candidatas",
        "",
        "| Evento | Cantidad |",
        "|---|---:|",
    ]

    for evento, cantidad in por_evento.most_common():
        lineas.append(f"| {evento} | {cantidad:,} |")

    lineas += [
        "",
        "## Rutas y nombres más frecuentes",
        "",
        "| Ruta | Nombre | Registros |",
        "|---|---|---:|",
    ]

    for (ruta, nombre), cantidad in workflows.most_common(50):
        ruta = ruta.replace("|", "\\|")
        nombre = nombre.replace("|", "\\|")
        lineas.append(f"| {ruta} | {nombre} | {cantidad:,} |")

    lineas += [
        "",
        "## Ejemplos para revisión manual",
        "",
        "| Repositorio | Ruta | Nombre | Título | Resultado | "
        "Evento | head_sha | Logs referenciados | Coincidencias |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for ejemplo in ejemplos:
        valores = [
            ejemplo["repo"],
            ejemplo["ruta"],
            ejemplo["nombre"],
            ejemplo["titulo"],
            ejemplo["resultado"],
            ejemplo["evento"],
            ejemplo["head_sha"],
            ejemplo["logs_archive_presente"],
            ejemplo["coincidencias"],
        ]
        valores = [
            str(valor or "").replace("|", "\\|").replace("\n", " ")
            for valor in valores
        ]
        lineas.append("| " + " | ".join(valores) + " |")

    lineas += [
        "",
        "## Limitaciones",
        "",
        "- Las palabras clave pueden producir falsos positivos y negativos.",
        "- Una conclusion failure no demuestra un fallo de despliegue.",
        "- La presencia de logs_archive no garantiza que los logs "
        "estén descargados o completos.",
        "- Es necesario verificar el contenido y la finalidad del workflow "
        "antes de definir etiquetas para el modelo.",
        "",
    ]

    Path(args.out).write_text(
        "\n".join(lineas), encoding="utf-8"
    )
    print(f"Informe escrito en: {args.out}")
    print(f"Registros procesados: {total:,}")
    print(f"Posibles candidatos: {candidatos:,}")
    print(f"Errores de parseo: {errores:,}")


if __name__ == "__main__":
    main()
