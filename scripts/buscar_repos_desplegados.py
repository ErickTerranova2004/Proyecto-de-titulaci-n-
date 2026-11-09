"""Busca repositorios públicos con workflows que despliegan y los carga.

  python scripts/buscar_repos_desplegados.py buscar   # GitHub → datos_prueba/repos_desplegados_100.*
  python scripts/buscar_repos_desplegados.py cargar   # registra, asigna y sincroniza en la plataforma

Se ejecuta con el Python del backend (necesita requests y PyYAML):
  backend\\venv\\Scripts\\python.exe scripts\\buscar_repos_desplegados.py buscar

Criterio (el mismo de datos_prueba/casos_prueba_30.md):
- El workflow usa una acción o comando que despliega a un servidor, la nube,
  contenedores o un PaaS (MARCADORES). Se descartan publicar imágenes,
  GitHub Pages, paquetes o CI.
- Repositorio público, no fork ni archivado, fuera del dataset de
  entrenamiento y no registrado aún en la plataforma.
- Activo: al menos MIN_EJECUCIONES ejecuciones terminadas en los últimos
  6 meses y al menos un éxito.
- Un workflow por repositorio y como máximo MAX_POR_PLATAFORMA por
  plataforma, para que la muestra sea variada.

Solo lectura en GitHub. El token se toma de `gh auth token` o GITHUB_TOKEN y
nunca se guarda.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

RAIZ = Path(__file__).resolve().parent.parent
SALIDA_JSON = RAIZ / "datos_prueba" / "repos_desplegados_100.json"
SALIDA_MD = RAIZ / "datos_prueba" / "repos_desplegados_100.md"
DATASETS = ["datos_procesados/dataset_riesgo_despliegue_v1_1.csv",
            "datos_procesados/dataset_riesgo_despliegue_v1.csv",
            "informes/deploy_runs.csv", "informes/deploy_runs_v1_1.csv"]
API = "https://api.github.com"
OBJETIVO = 100
MIN_EJECUCIONES = 10
MAX_POR_PLATAFORMA = 7
DESDE = (date.today() - timedelta(days=182)).isoformat()
ASIGNAR_A = ["prueba_lider", "prueba_dev"]

# (búsqueda en el código, regex sobre `uses:`/`run:` del paso, plataforma,
#  descripción del despliegue para la evidencia)
MARCADORES = [
    ("google-github-actions/deploy-cloudrun", r"google-github-actions/deploy-cloudrun",
     "Google Cloud Run", "despliega el servicio en Google Cloud Run"),
    ("google-github-actions/deploy-appengine", r"google-github-actions/deploy-appengine",
     "Google App Engine", "despliega la aplicación en Google App Engine"),
    ("aws-actions/amazon-ecs-deploy-task-definition", r"aws-actions/amazon-ecs-deploy-task-definition",
     "AWS ECS", "despliega la definición de tarea en Amazon ECS"),
    ("einaregilsson/beanstalk-deploy", r"einaregilsson/beanstalk-deploy",
     "AWS Elastic Beanstalk", "despliega la aplicación en AWS Elastic Beanstalk"),
    ("aws-actions/aws-cloudformation-github-deploy", r"aws-actions/aws-cloudformation-github-deploy",
     "AWS CloudFormation", "despliega la pila en AWS CloudFormation"),
    ("\"aws lambda update-function-code\"", r"aws lambda update-function-code",
     "AWS Lambda", "actualiza la función en AWS Lambda"),
    ("azure/webapps-deploy", r"azure/webapps-deploy",
     "Azure App Service", "despliega la aplicación en Azure App Service"),
    ("azure/container-apps-deploy-action", r"azure/container-apps-deploy-action",
     "Azure Container Apps", "despliega el contenedor en Azure Container Apps"),
    ("Azure/functions-action", r"azure/functions-action",
     "Azure Functions", "despliega las funciones en Azure Functions"),
    ("Azure/k8s-deploy", r"azure/k8s-deploy",
     "Kubernetes", "despliega los manifiestos en Kubernetes"),
    ("\"flyctl deploy\"", r"flyctl deploy",
     "PaaS (Fly.io)", "despliega la aplicación en Fly.io"),
    ("\"railway up\"", r"railway up",
     "PaaS (Railway)", "despliega el servicio en Railway"),
    ("digitalocean/app_action", r"digitalocean/app_action",
     "PaaS (DigitalOcean App Platform)", "despliega la aplicación en DigitalOcean App Platform"),
    ("akhileshns/heroku-deploy", r"akhileshns/heroku-deploy",
     "PaaS (Heroku)", "despliega la aplicación en Heroku"),
    ("easingthemes/ssh-deploy", r"easingthemes/ssh-deploy",
     "Servidor (SSH)", "copia la aplicación al servidor por SSH"),
    ("burnett01/rsync-deployments", r"burnett01/rsync-deployments",
     "Servidor (rsync)", "sincroniza la aplicación en el servidor con rsync"),
    ("appleboy/ssh-action", r"appleboy/ssh-action",
     "Servidor (SSH)", "entra al servidor por SSH y actualiza la aplicación"),
]
# appleboy/ssh-action ejecuta cualquier comando: solo cuenta si el script
# del paso actualiza o reinicia la aplicación.
SCRIPT_DESPLIEGUE = re.compile(
    r"docker|compose|git pull|pm2|systemctl|restart|deploy|kubectl|npm (ci|install)|"
    r"rsync|supervisorctl|nginx", re.IGNORECASE)


# ------------------------------------------------------------------ GitHub
class GitHub:
    def __init__(self):
        token = os.environ.get("GITHUB_TOKEN") or subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
        if not token:
            sys.exit("Sin token de GitHub: inicie sesión con `gh auth login` o defina GITHUB_TOKEN.")
        self.sesion = requests.Session()
        self.sesion.headers.update({"Authorization": f"Bearer {token}",
                                    "Accept": "application/vnd.github+json",
                                    "X-GitHub-Api-Version": "2022-11-28"})

    def get(self, ruta, params=None, crudo=False):
        for _ in range(6):
            r = self.sesion.get(f"{API}{ruta}", params=params, timeout=60,
                                headers={"Accept": "application/vnd.github.raw+json"} if crudo else None)
            restantes = r.headers.get("X-RateLimit-Remaining")
            if r.status_code in (403, 429) and restantes == "0":
                espera = max(int(r.headers.get("X-RateLimit-Reset", time.time() + 60)) - time.time(), 0) + 2
                print(f"  límite de GitHub: espero {espera:.0f} s", flush=True)
                time.sleep(espera)
                continue
            if r.status_code in (403, 429) and "retry-after" in r.headers:
                time.sleep(int(r.headers["retry-after"]) + 1)
                continue
            if r.status_code >= 500:
                time.sleep(5)
                continue
            if r.status_code >= 400:
                return None
            return r.text if crudo else r.json()
        return None


# ------------------------------------------------------------------ Buscar
def excluidos():
    """Repositorios del dataset de entrenamiento y ya registrados."""
    csv.field_size_limit(10 ** 9)
    nombres = set()
    for ruta in DATASETS:
        with open(RAIZ / ruta, encoding="utf-8") as f:
            nombres |= {fila["repository_name"].lower() for fila in csv.DictReader(f)}
    sys.path.insert(0, str(RAIZ / "backend"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from riesgo.models import Repositorio
    nombres |= {n.lower() for n in Repositorio.objects.values_list("nombre_completo", flat=True)}
    return nombres


def disparadores(on):
    """Texto legible de los eventos que disparan el workflow."""
    if isinstance(on, str):
        on = {on: None}
    elif isinstance(on, list):
        on = {e: None for e in on}
    partes = []
    for evento, conf in (on or {}).items():
        if evento == "push" and isinstance(conf, dict) and conf.get("branches"):
            ramas = conf["branches"] if isinstance(conf["branches"], list) else [conf["branches"]]
            partes.append("push a " + ", ".join(map(str, ramas[:3])))
        elif evento == "push" and isinstance(conf, dict) and conf.get("tags"):
            partes.append("tags de versión")
        else:
            partes.append(str(evento))
    return partes


def paso_despliegue(contenido, patron):
    """(job, entorno, paso) del primer paso que despliega, o None."""
    try:
        datos = yaml.safe_load(contenido)
    except yaml.YAMLError:
        return None, None
    if not isinstance(datos, dict) or not isinstance(datos.get("jobs"), dict):
        return None, None
    # PyYAML interpreta la clave `on` como True.
    on = datos.get("on", datos.get(True))
    for nombre_job, job in datos["jobs"].items():
        if not isinstance(job, dict):
            continue
        for paso in job.get("steps") or []:
            if not isinstance(paso, dict):
                continue
            texto = f"{paso.get('uses', '')}\n{paso.get('run', '')}"
            if not re.search(patron, texto, re.IGNORECASE):
                continue
            if "appleboy/ssh-action" in str(paso.get("uses", "")):
                guion = str((paso.get("with") or {}).get("script", ""))
                if not SCRIPT_DESPLIEGUE.search(guion):
                    continue
            entorno = job.get("environment")
            if isinstance(entorno, dict):
                entorno = entorno.get("name")
            return {"job": str(nombre_job), "entorno": str(entorno) if entorno else "",
                    "paso": str(paso.get("name") or paso.get("uses") or "run"),
                    "uses": str(paso.get("uses") or "").strip()}, on
    return None, on


def ejecuciones(gh, repo, archivo):
    datos = gh.get(f"/repos/{repo}/actions/workflows/{archivo}/runs",
                   {"status": "completed", "created": f">={DESDE}", "per_page": 100})
    if not datos:
        return 0, Counter()
    return datos.get("total_count", 0), Counter(r.get("conclusion") for r in datos.get("workflow_runs", []))


def evidencia(paso, on, descripcion):
    eventos = disparadores(on)
    con = f"Con {', '.join(eventos[:3])}, el" if eventos else "El"
    entorno = f" (environment: {paso['entorno']})" if paso["entorno"] else ""
    herramienta = f" con {paso['uses']}" if paso["uses"] else f" en el paso '{paso['paso']}'"
    return f"{con} job {paso['job']}{entorno} {descripcion}{herramienta}."


def buscar(args):
    gh = GitHub()
    fuera = excluidos()
    print(f"Excluidos (dataset + registrados): {len(fuera)}", flush=True)
    elegidos, descartes, vistos = [], Counter(), set()
    por_plataforma = Counter()
    for consulta, patron, plataforma, descripcion in MARCADORES:
        if len(elegidos) >= OBJETIVO:
            break
        for pagina in (1, 2, 3):
            if por_plataforma[plataforma] >= MAX_POR_PLATAFORMA or len(elegidos) >= OBJETIVO:
                break
            resultado = gh.get("/search/code", {"q": f"{consulta} path:.github/workflows",
                                                "per_page": 100, "page": pagina})
            time.sleep(6.5)  # la búsqueda de código admite 10 consultas por minuto
            if not resultado or not resultado.get("items"):
                break
            for item in resultado["items"]:
                if por_plataforma[plataforma] >= MAX_POR_PLATAFORMA or len(elegidos) >= OBJETIVO:
                    break
                repo = item["repository"]["full_name"]
                ruta = item["path"]
                if repo.lower() in vistos or repo.lower() in fuera:
                    continue
                if not re.fullmatch(r"\.github/workflows/[^/]+\.ya?ml", ruta):
                    continue
                vistos.add(repo.lower())
                info = gh.get(f"/repos/{repo}")
                if not info or info.get("fork") or info.get("archived") or info.get("private"):
                    descartes["fork, archivado o privado"] += 1
                    continue
                contenido = gh.get(f"/repos/{repo}/contents/{ruta}", crudo=True)
                paso, on = paso_despliegue(contenido or "", patron)
                if not paso:
                    descartes["el paso no despliega"] += 1
                    continue
                archivo = ruta.rsplit("/", 1)[-1]
                total, conclusiones = ejecuciones(gh, repo, archivo)
                if total < MIN_EJECUCIONES:
                    descartes[f"menos de {MIN_EJECUCIONES} ejecuciones en 6 meses"] += 1
                    continue
                if not conclusiones.get("success"):
                    descartes["ningún éxito reciente"] += 1
                    continue
                muestra = sum(conclusiones.values())
                exito = round(100 * conclusiones.get("success", 0) / muestra)
                fallo = round(100 * conclusiones.get("failure", 0) / muestra)
                elegidos.append({
                    "id": len(elegidos) + 1, "repositorio": repo, "ruta_workflow": ruta,
                    "plataforma": plataforma, "evidencia": evidencia(paso, on, descripcion),
                    "url": f"https://github.com/{repo}/blob/HEAD/{ruta}",
                    "ejecuciones_6_meses": total,
                    "conclusiones_muestra": dict(conclusiones),
                    "porcentajes": f"{exito} % éxito / {fallo} % fallo",
                    "estrellas": info.get("stargazers_count", 0),
                    "asignar_a": ASIGNAR_A, "verificado_el": date.today().isoformat(),
                })
                por_plataforma[plataforma] += 1
                print(f"{len(elegidos):>3}. {repo} ({plataforma}, {total} ejec.)", flush=True)
    SALIDA_JSON.write_text(json.dumps(elegidos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    escribir_md(elegidos, descartes, por_plataforma)
    print(f"Elegidos: {len(elegidos)} · descartes: {dict(descartes)}")


def escribir_md(elegidos, descartes, por_plataforma):
    lineas = [
        f"# {len(elegidos)} repositorios públicos con workflows de despliegue", "",
        f"Verificados el {date.today().isoformat()} con la API de GitHub (solo lectura) por "
        "[`scripts/buscar_repos_desplegados.py`](../scripts/buscar_repos_desplegados.py). Datos en "
        "[repos_desplegados_100.json](repos_desplegados_100.json).", "",
        "## Criterio", "",
        "- El workflow tiene un paso que **despliega** a un servidor, la nube, contenedores o un PaaS "
        "(acción o comando reconocido; para `appleboy/ssh-action` el script debe actualizar o reiniciar la "
        "aplicación). No se incluyen publicación de imágenes, GitHub Pages, paquetes ni CI.",
        "- Repositorio público, no fork ni archivado, **fuera del dataset de entrenamiento** y no registrado "
        "antes en la plataforma.",
        f"- Al menos {MIN_EJECUCIONES} ejecuciones terminadas desde el {DESDE} y al menos un éxito en la "
        "muestra de las 100 más recientes.",
        f"- Un workflow por repositorio y como máximo {MAX_POR_PLATAFORMA} por plataforma.",
        f"- Se asignan a: {', '.join(ASIGNAR_A)}.", "",
        "## Por plataforma", "",
        *[f"- {p}: {n}" for p, n in por_plataforma.most_common()], "",
        "## Descartados durante la búsqueda", "",
        *[f"- {motivo}: {n}" for motivo, n in descartes.most_common()], "",
        "## Repositorios", "",
        "| # | Repositorio | Ruta | Plataforma | Ejec. 6 meses | % éxito / fallo | Evidencia |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in elegidos:
        lineas.append(f"| {c['id']} | [{c['repositorio']}]({c['url']}) | `{c['ruta_workflow'].rsplit('/', 1)[-1]}` | "
                      f"{c['plataforma']} | {c['ejecuciones_6_meses']} | {c['porcentajes']} | "
                      f"{c['evidencia'].replace('|', '/')} |")
    SALIDA_MD.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ Cargar
def cargar(args):
    """Registra, asigna y sincroniza con los mismos endpoints de la interfaz."""
    sys.path.insert(0, str(RAIZ / "backend"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    settings.ALLOWED_HOSTS = ["*"]
    Usuario = get_user_model()
    admin = Usuario.objects.get(username=args.admin)
    api = APIClient()
    api.force_authenticate(admin)
    ids = list(Usuario.objects.filter(username__in=ASIGNAR_A).values_list("id", flat=True))
    casos = json.loads(SALIDA_JSON.read_text(encoding="utf-8"))
    resumen = Counter()
    for caso in casos:
        r = api.post("/api/repositorios/registrar/", {
            "repositorio": caso["repositorio"], "workflow_path": caso["ruta_workflow"],
            "evidencia": caso["evidencia"], "usuarios": ids}, format="json")
        cuerpo = r.json() if r.content else {}
        estado = r.status_code
        sincronizado = "—"
        if estado == 201:
            repo_id = cuerpo["repositorio"]["id"] if isinstance(cuerpo.get("repositorio"), dict) else None
            if repo_id is None:
                from riesgo.models import Repositorio
                repo_id = Repositorio.objects.get(nombre_completo__iexact=caso["repositorio"]).id
            s = api.post(f"/api/repositorios/{repo_id}/sincronizar/")
            sincronizado = (f"{s.json().get('ejecuciones_guardadas', '?')} ejecuciones"
                            if s.status_code == 200 else f"error {s.status_code}")
        resumen[estado] += 1
        print(f"#{caso['id']:>3} {caso['repositorio']}: {estado} {cuerpo.get('detail', '')} · {sincronizado}",
              flush=True)
        time.sleep(args.pausa)
    print(f"Resultado: {dict(resumen)}")


if __name__ == "__main__":
    analizador = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analizador.add_argument("accion", choices=["buscar", "cargar"])
    analizador.add_argument("--admin", default="prueba_admin", help="administrador que registra")
    analizador.add_argument("--pausa", type=float, default=0.5)
    argumentos = analizador.parse_args()
    {"buscar": buscar, "cargar": cargar}[argumentos.accion](argumentos)
