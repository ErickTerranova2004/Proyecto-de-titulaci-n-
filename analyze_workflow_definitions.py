
#!/usr/bin/env python3
"""Analiza definiciones YAML de GitHub Actions descargadas."""

import re
from pathlib import Path
from collections import Counter

BASE = Path("informes/workflow_definitions")
OUT = Path("informes/informe_clasificacion_workflows.md")

PATRONES = {
    "Posible despliegue": [
        r"\benvironment\s*:",
        r"\bdeploy\b",
        r"\bdeployment\b",
        r"\bkubectl\b",
        r"\bhelm\s+upgrade\b",
        r"azure/webapps-deploy",
        r"google-github-actions/deploy",
        r"aws\s+ecs",
        r"\bterraform\s+apply\b",
    ],
    "Publicación de artefactos": [
        r"docker/build-push-action",
        r"\bdocker\s+push\b",
        r"\bnpm\s+publish\b",
        r"\bpublish\b",
        r"\bpypi\b",
        r"\bgh\s+release\b",
        r"upload-artifact",
    ],
    "Pruebas o compilación": [
        r"\bpytest\b",
        r"\bnpm\s+test\b",
        r"\bnpm\s+run\s+build\b",
        r"\bgo\s+test\b",
        r"\bmvn\s+test\b",
        r"\bgradle\s+test\b",
        r"\bbuild\b",
        r"\blint\b",
    ],
}


def clasificar(texto):
    resultado = []
    for categoria, patrones in PATRONES.items():
        if any(re.search(p, texto, re.IGNORECASE)
               for p in patrones):
            resultado.append(categoria)

    if not resultado:
        return ["Revisión manual necesaria"]

    return resultado


def main():
    if not BASE.exists():
        print(f"No se encontró la carpeta: {BASE}")
        return

    archivos = sorted(BASE.rglob("*.yml"))
    archivos += sorted(BASE.rglob("*.yaml"))
    archivos = sorted(set(archivos))

    if not archivos:
        print("No se encontraron archivos YAML.")
        return

    conteos = Counter()
    lineas = [
        "# Clasificación preliminar de workflows",
        "",
        f"- Archivos YAML encontrados: {len(archivos)}",
        "",
        "> Clasificación automática basada en palabras clave. "
        "No confirma despliegues ni fallos reales.",
        "",
        "| Archivo | Categorías detectadas | Evidencias encontradas |",
        "|---|---|---|",
    ]

    for archivo in archivos:
        texto = archivo.read_text(
            encoding="utf-8", errors="replace"
        )
        categorias = clasificar(texto)

        evidencias = []
        for numero, linea in enumerate(texto.splitlines(), start=1):
            if any(
                re.search(patron, linea, re.IGNORECASE)
                for patrones in PATRONES.values()
                for patron in patrones
            ):
                fragmento = linea.strip().replace("|", "\\|")
                evidencias.append(f"L{numero}: {fragmento[:180]}")
            if len(evidencias) >= 8:
                break

        for categoria in categorias:
            conteos[categoria] += 1

        lineas.append(
            f"| {archivo.name} | {'; '.join(categorias)} | "
            f"{'<br>'.join(evidencias) if evidencias else 'Sin coincidencias'} |"
        )

    lineas += [
        "",
        "## Resumen de categorías",
        "",
        "| Categoría | Archivos que coinciden |",
        "|---|---:|",
    ]

    for categoria, cantidad in conteos.most_common():
        lineas.append(f"| {categoria} | {cantidad} |")

    lineas += [
        "",
        "## Limitaciones",
        "",
        "- Un archivo puede coincidir con varias categorías.",
        "- Las palabras clave pueden producir falsos positivos.",
        "- La configuración actual puede diferir de la histórica.",
        "- Un workflow fallido no equivale necesariamente "
        "a un despliegue fallido.",
        "- Las categorías no deben utilizarse directamente "
        "como etiquetas de entrenamiento.",
        "",
    ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lineas), encoding="utf-8")

    print(f"Archivos analizados: {len(archivos)}")
    print(f"Informe generado: {OUT}")


if __name__ == "__main__":
    main()
