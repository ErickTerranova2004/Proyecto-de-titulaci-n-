
#!/usr/bin/env python3
"""Inspecciona definiciones de workflows candidatos en GitHub."""

import argparse
import base64
import collections
import gzip
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

KEYWORDS = re.compile(
    r"deploy|deployment|release|publish|production|staging|"
    r"rollout|ship|delivery|despliegue|produccion",
    re.IGNORECASE,
)

# Los términos de la ruta ayudan a priorizar workflows relevantes.
PRIORITY = re.compile(
    r"deploy|deployment|docker-publish|publish|release",
    re.IGNORECASE,
)


def abrir_archivo(path):
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8",
                         errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def consultar_github(repo, path, token=None):
    """Obtiene el contenido de un archivo público mediante la API."""
    encoded_path = urllib.parse.quote(path, safe="/")
    url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}"

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Thesis-Workflow-Inspector",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("type") != "file":
            return None, "No es un archivo individual"

        contenido = data.get("content", "")
        if not contenido:
            return None, "GitHub no devolvió contenido codificado"

        decoded = base64.b64decode(contenido).decode(
            "utf-8", errors="replace"
        )
        return decoded, "OK"

    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, "No encontrado (404)"
        if exc.code == 403:
            return None, "Acceso limitado o límite de API (403)"
        if exc.code == 401:
            return None, "Token no válido o no autorizado (401)"
        return None, f"Error HTTP {exc.code}"

    except Exception as exc:
        return None, f"Error: {type(exc).__name__}: {exc}"


def clasificar_contenido(contenido):
    """Sugiere una categoría; no confirma un despliegue real."""
    texto = contenido.lower()

    indicios = {
        "entorno o acción de despliegue": [
            "environment:", "deployment", "deploy", "kubectl",
            "helm upgrade", "aws ecs", "azure/webapps-deploy",
            "google-github-actions/deploy",
        ],
        "publicación de artefactos": [
            "docker/build-push-action", "docker push",
            "upload-artifact", "publish", "pypi",
            "npm publish", "gh release",
        ],
        "pruebas o compilación": [
            "pytest", "unittest", "npm test", "npm run build",
            "mvn test", "gradle test", "go test",
        ],
    }

    encontrados = []
    for categoria, patrones in indicios.items():
        if any(patron in texto for patron in patrones):
            encontrados.append(categoria)

    if not encontrados:
        return "Indicios insuficientes; revisar manualmente"

    return "; ".join(encontrados)


def main():
    parser = argparse.ArgumentParser(
        description="Valida workflows candidatos de GHALogs."
    )
    parser.add_argument("--runs", required=True,
                        help="Ruta a runs.json.gz")
    parser.add_argument(
        "--out",
        default="informes/informe_workflow_examples.md",
    )
    parser.add_argument(
        "--limit", type=int, default=25,
        help="Máximo de workflows únicos a consultar (máximo 50).",
    )
    args = parser.parse_args()

    if args.limit < 1 or args.limit > 50:
        parser.error("--limit debe estar entre 1 y 50.")

    token = os.environ.get("GITHUB_TOKEN")
    candidatos = {}
    registros = 0
    errores_json = 0

    print("Leyendo registros locales de GHALogs...")

    with abrir_archivo(args.runs) as archivo:
        for linea in archivo:
            if not linea.strip():
                continue
            try:
                registro = json.loads(linea)
            except json.JSONDecodeError:
                errores_json += 1
                continue

            registros += 1
            metadata = registro.get("metadata") or {}
            repo = registro.get("repository_name")

            ruta = (
                registro.get("workflow_path")
                or metadata.get("path")
            )
            if not repo or not ruta:
                continue

            campos = [
                ruta,
                metadata.get("name"),
                metadata.get("path"),
                metadata.get("display_title"),
            ]
            if not any(KEYWORDS.search(str(x or "")) for x in campos):
                continue

            # Evita consultar muchas veces la misma definición.
            clave = (str(repo), str(ruta))
            if clave not in candidatos:
                candidatos[clave] = {
                    "repo": str(repo),
                    "ruta": str(ruta),
                    "nombre": str(metadata.get("name") or ""),
                    "prioridad": bool(PRIORITY.search(str(ruta))),
                    "resultados": collections.Counter(),
                    "eventos": collections.Counter(),
                }

            candidatos[clave]["resultados"][
                str(metadata.get("conclusion") or "sin resultado")
            ] += 1
            candidatos[clave]["eventos"][
                str(metadata.get("event") or "sin evento")
            ] += 1

    seleccionados = sorted(
        candidatos.values(),
        key=lambda x: (
            not x["prioridad"],
            x["ruta"].lower(),
            x["repo"].lower(),
        ),
    )[:args.limit]

    print(f"Registros leídos: {registros:,}")
    print(f"Workflows únicos candidatos: {len(candidatos):,}")
    print(f"Workflows que se consultarán: {len(seleccionados)}")

    carpeta = Path(args.out).parent / "workflow_definitions"
    carpeta.mkdir(parents=True, exist_ok=True)

    lineas = [
        "# Validación de workflows candidatos de GitHub",
        "",
        f"- Registros locales leídos: {registros:,}",
        f"- Errores JSON: {errores_json:,}",
        f"- Workflows únicos candidatos: {len(candidatos):,}",
        f"- Máximo seleccionado para consulta: {len(seleccionados)}",
        f"- Autenticación mediante token: {'sí' if token else 'no'}",
        "",
        "> Las categorías son indicios automáticos. No demuestran que "
        "se haya realizado un despliegue ni que haya fallado.",
        "",
        "## Resultados",
        "",
        "| Repositorio | Ruta | Resultado de consulta | "
        "Indicios del contenido | Archivo guardado |",
        "|---|---|---|---|---|",
    ]

    for indice, item in enumerate(seleccionados, start=1):
        repo = item["repo"]
        ruta = item["ruta"]

        # Las rutas dinámicas de Pages no suelen ser archivos del repositorio.
        if not ruta.startswith(".github/workflows/"):
            estado = "Ruta no convencional; revisar"
            categoria = "Sin inspección del archivo"
            guardado = ""
        else:
            print(f"[{indice}/{len(seleccionados)}] {repo} / {ruta}")
            contenido, estado = consultar_github(repo, ruta, token)

            if contenido is not None:
                categoria = clasificar_contenido(contenido)
                nombre_seguro = re.sub(
                    r"[^A-Za-z0-9_.-]+", "_",
                    f"{repo}__{ruta.replace('/', '__')}"
                )
                destino = carpeta / f"{nombre_seguro}.yml"
                destino.write_text(contenido, encoding="utf-8")
                guardado = str(destino)
            else:
                categoria = "No se pudo clasificar"
                guardado = ""

            # Pausa breve para evitar ráfagas de peticiones.
            time.sleep(0.3)

        valores = [
            repo, ruta, estado, categoria, guardado
        ]
        valores = [
            str(x).replace("|", "\\|").replace("\n", " ")
            for x in valores
        ]
        lineas.append("| " + " | ".join(valores) + " |")

    lineas += [
        "",
        "## Conteos de ejecuciones en GHALogs",
        "",
        "Los conteos siguientes corresponden a ejecuciones históricas "
        "asociadas a cada ruta, no a nuevas consultas de GitHub.",
        "",
        "| Repositorio | Ruta | Conclusiones | Eventos |",
        "|---|---|---|---|",
    ]

    for item in seleccionados:
        conclusiones = ", ".join(
            f"{k}: {v}" for k, v in item["resultados"].most_common()
        )
        eventos = ", ".join(
            f"{k}: {v}" for k, v in item["eventos"].most_common()
        )
        valores = [
            item["repo"], item["ruta"], conclusiones, eventos
        ]
        valores = [
            str(x).replace("|", "\\|").replace("\n", " ")
            for x in valores
        ]
        lineas.append("| " + " | ".join(valores) + " |")

    lineas += [
        "",
        "## Limitaciones",
        "",
        "- Solo se consultó una muestra de workflows únicos.",
        "- El contenido actual del repositorio puede diferir de la "
        "versión existente cuando ocurrió una ejecución histórica.",
        "- Los patrones automáticos pueden producir falsos positivos "
        "y falsos negativos.",
        "- Un archivo no encontrado no demuestra que el workflow "
        "no existiera en la fecha de la ejecución.",
        "- No se asignan etiquetas de fallo real de despliegue.",
        "",
    ]

    salida = Path(args.out)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(lineas), encoding="utf-8")

    print()
    print(f"Informe generado: {salida}")
    print(f"Definiciones descargadas en: {carpeta}")


if __name__ == "__main__":
    main()
