"""Reúne y filtra repositorios REALES con despliegues reales (200-250).

Etapas (cada una reanudable; los datos de GitHub se guardan en la caché):

  python scripts/filtrar_repos_reales.py candidatos   # búsqueda de código → candidatos
  python scripts/filtrar_repos_reales.py candidatos --estrategia2   # acciones de producción
  python scripts/filtrar_repos_reales.py prefiltrar   # GraphQL: organización, >1 año, >=3 contribuidores
  python scripts/filtrar_repos_reales.py perfilar --prefiltrados   # actividad, YAML, repo, README, commits
  python scripts/filtrar_repos_reales.py revisar --lote 1   # perfiles para la revisión manual
  python scripts/filtrar_repos_reales.py etiquetar    # jobs de las ejecuciones → y (fase 2)
  python scripts/filtrar_repos_reales.py jobs         # nº de jobs de las y=1 antiguas; sin jobs → excluida
  python scripts/filtrar_repos_reales.py produccion   # repos con staging y producción: solo producción
  python scripts/filtrar_repos_reales.py informe      # selección final, informe y orden (semilla 42)

Se ejecuta con el Python del backend (requests y PyYAML):
  backend\\venv\\Scripts\\python.exe scripts\\filtrar_repos_reales.py <etapa>

Criterios: informes/informe_filtrado_repos_reales.md («Criterios»). La
decisión sobre si es una aplicación real en uso (criterio 1) es manual y se
guarda en informes/revision_manual_repos.json con su motivo. Solo lectura en
GitHub; no escribe en la plataforma ni en su base de datos.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

RAIZ = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("CACHE_FILTRADO", RAIZ / "informes" / "cache_filtrado"))
CANDIDATOS = CACHE / "candidatos.json"
PERFILES = CACHE / "perfiles.json"
ETIQUETAS = CACHE / "etiquetas.json"
HISTORIAL = CACHE / "historial_runs.json"
REVISION = RAIZ / "informes" / "revision_manual_repos.json"
INFORME = RAIZ / "informes" / "informe_filtrado_repos_reales.md"
ORDEN = RAIZ / "informes" / "orden_repos_curva.csv"
PREVIOS = [RAIZ / "datos_prueba" / "repos_desplegados_100.json"]
DATASETS = ["datos_procesados/dataset_riesgo_despliegue_v1_1.csv",
            "datos_procesados/dataset_riesgo_despliegue_v1.csv",
            "informes/deploy_runs.csv", "informes/deploy_runs_v1_1.csv"]
API = "https://api.github.com"
META, MINIMO = 250, 200
MIN_EJECUCIONES = 10
MAX_POR_ORGANIZACION = 5
MAX_PROPORCION_PLATAFORMA = 0.30
RUNS_ETIQUETAR = 100
TOPE_DATASET = 50
SEMILLA = 42
# Ventana de 6 meses fijada al congelar el dataset (antes se calculaba desde hoy).
DESDE = "2026-05-11"
EXCLUIR_ORGANIZACIONES = {"tesis-2026"}

# (búsqueda de código, regex sobre `uses`/`run` del paso, proveedor, servicio)
MARCADORES = [
    ("google-github-actions/deploy-cloudrun", r"google-github-actions/deploy-cloudrun", "Google Cloud", "Cloud Run"),
    ("\"gcloud run deploy\"", r"gcloud run deploy", "Google Cloud", "Cloud Run"),
    ("google-github-actions/deploy-appengine", r"google-github-actions/deploy-appengine", "Google Cloud", "App Engine"),
    ("\"gcloud app deploy\"", r"gcloud app deploy", "Google Cloud", "App Engine"),
    ("\"gcloud functions deploy\"", r"gcloud functions deploy", "Google Cloud", "Cloud Functions"),
    ("aws-actions/amazon-ecs-deploy-task-definition", r"aws-actions/amazon-ecs-deploy-task-definition", "AWS", "ECS"),
    ("\"aws ecs update-service\"", r"aws ecs update-service", "AWS", "ECS"),
    ("einaregilsson/beanstalk-deploy", r"einaregilsson/beanstalk-deploy", "AWS", "Elastic Beanstalk"),
    ("aws-actions/aws-cloudformation-github-deploy", r"aws-actions/aws-cloudformation-github-deploy", "AWS", "CloudFormation"),
    ("\"aws lambda update-function-code\"", r"aws lambda update-function-code", "AWS", "Lambda"),
    ("\"sam deploy\"", r"\bsam deploy\b", "AWS", "SAM / Lambda"),
    ("\"serverless deploy\"", r"\b(serverless|sls) deploy\b", "AWS", "Serverless Framework"),
    ("\"cdk deploy\"", r"\bcdk deploy\b", "AWS", "CDK"),
    ("azure/webapps-deploy", r"azure/webapps-deploy", "Azure", "App Service"),
    ("azure/container-apps-deploy-action", r"azure/container-apps-deploy-action", "Azure", "Container Apps"),
    ("Azure/functions-action", r"azure/functions-action", "Azure", "Functions"),
    ("Azure/k8s-deploy", r"azure/k8s-deploy", "Kubernetes", "AKS / Kubernetes"),
    ("\"helm upgrade --install\"", r"helm upgrade", "Kubernetes", "Helm"),
    ("\"kubectl set image\"", r"kubectl set image", "Kubernetes", "kubectl"),
    ("\"flyctl deploy\"", r"flyctl deploy", "Fly.io", "Fly.io"),
    ("\"railway up\"", r"railway up", "Railway", "Railway"),
    ("digitalocean/app_action", r"digitalocean/app_action", "DigitalOcean", "App Platform"),
    ("akhileshns/heroku-deploy", r"akhileshns/heroku-deploy", "Heroku", "Heroku"),
    ("\"heroku container:release\"", r"heroku container:release", "Heroku", "Heroku"),
    ("johnbeynon/render-deploy-action", r"johnbeynon/render-deploy-action", "Render", "Render"),
    ("\"api.render.com/deploy\"", r"api\.render\.com/deploy", "Render", "Render"),
    ("cloudflare/wrangler-action", r"cloudflare/wrangler-action", "Cloudflare", "Workers"),
    ("\"vercel deploy --prod\"", r"vercel (deploy )?--prod", "Vercel", "Vercel"),
    ("easingthemes/ssh-deploy", r"easingthemes/ssh-deploy", "Servidor propio", "SSH"),
    ("burnett01/rsync-deployments", r"burnett01/rsync-deployments", "Servidor propio", "rsync"),
    ("appleboy/ssh-action", r"appleboy/ssh-action", "Servidor propio", "SSH"),
    ("dawidd6/action-ansible-playbook", r"dawidd6/action-ansible-playbook", "Servidor propio", "Ansible"),
    ("\"ansible-playbook\"", r"\bansible-playbook\b", "Servidor propio", "Ansible"),
]

# Estrategia 2 (tras el lote 7): solo acciones de despliegue a producción,
# repetidas con «production» y «environment» para obtener resultados nuevos
# (cada búsqueda devuelve como máximo 1000). Railway y Render se descartan:
# en los lotes revisados no aportaron ningún repositorio válido.
CONSULTAS_E2 = ["aws-actions/amazon-ecs-deploy-task-definition", "google-github-actions/deploy-cloudrun",
                "azure/webapps-deploy", "Azure/k8s-deploy", "\"helm upgrade --install\"",
                "appleboy/ssh-action", "dawidd6/action-ansible-playbook", "\"ansible-playbook\"",
                # Ampliación (lote 13 en adelante): plataformas con menos repositorios.
                "superfly/flyctl-actions", "\"flyctl deploy\"", "google-github-actions/deploy-appengine",
                "google-github-actions/deploy-cloud-functions", "azure/container-apps-deploy-action",
                "Azure/functions-action", "digitalocean/app_action", "akhileshns/heroku-deploy",
                "\"kubectl set image\"", "\"gcloud run deploy\""]
SUFIJOS_E2 = ["production", "environment"]
CONSULTAS_DESCARTADAS = {"\"railway up\"", "johnbeynon/render-deploy-action", "\"api.render.com/deploy\""}
PREFILTRO = CACHE / "prefiltro.json"
ENTORNOS_PRODUCCION = ["production", "Production", "prod", "Prod", "prd", "live", "Live"]
MIN_DIAS_ACTIVIDAD = 365
MIN_CONTRIBUIDORES = 3
SCRIPT_DESPLIEGUE = re.compile(
    r"docker|compose|git pull|pm2|systemctl|restart|deploy|kubectl|npm (ci|install)|"
    r"rsync|supervisorctl|nginx", re.IGNORECASE)
EFIMERO = re.compile(r"\b(kind|minikube|k3d|localstack)\b|helm/kind-action|medyagh/setup-minikube",
                     re.IGNORECASE)
PREVIEW = re.compile(r"preview|pr-\$\{\{|review-app|pull_request", re.IGNORECASE)
# Pistas de proyectos que no son una aplicación real en uso. Solo marcan el
# perfil para la revisión manual; no excluyen por sí mismas.
PISTAS = re.compile(
    r"tutorial|course|curso|homework|assignment|tarea|deber|template|boilerplate|starter|"
    r"\bdemo\b|example|sample|ejemplo|hello[- ]?world|practice|pr[aá]ctica|portfolio|portafolio|"
    r"learning|aprend|workshop|taller|bootcamp|capstone|sandbox|playground|\btest(ing)?\b|"
    r"\btesis\b|thesis|university|universidad|student|estudiante|\blab\b|class project|"
    r"proyecto final|final project|semestre|semester", re.IGNORECASE)
BOT = re.compile(r"\[bot\]|dependabot|renovate|github-actions", re.IGNORECASE)


# ------------------------------------------------------------------ utilidades
def leer(ruta, defecto):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else defecto


def guardar(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    for intento in range(10):  # Windows puede bloquear el archivo un momento
        try:
            tmp.replace(ruta)
            return
        except PermissionError:
            time.sleep(1 + intento)
    tmp.replace(ruta)


_ETIQUETADO = None


def modulo_etiquetado():
    """backend/riesgo/services/etiquetado.py (sin Django), cargado una vez."""
    global _ETIQUETADO
    if _ETIQUETADO is None:
        ruta = RAIZ / "backend" / "riesgo" / "services" / "etiquetado.py"
        spec = importlib.util.spec_from_file_location("etiquetado", ruta)
        _ETIQUETADO = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_ETIQUETADO)
    return _ETIQUETADO


def etiquetador():
    """Regla de la fase 2 tal como la aplica la plataforma."""
    modulo = modulo_etiquetado()
    texto = (RAIZ / "backend" / "riesgo" / "models.py").read_text(encoding="utf-8")
    patron = "".join(re.findall(r'r"([^"]*)"', texto.split("PATRON_DESPLIEGUE = (", 1)[1].split(")\n", 1)[0]))
    global REGLA_PLATAFORMA
    REGLA_PLATAFORMA = modulo
    return modulo.etiquetar_ejecucion, patron


REGLA_PLATAFORMA = None  # módulo riesgo/services/etiquetado.py cargado


class GitHub:
    def __init__(self):
        token = os.environ.get("GITHUB_TOKEN") or subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
        if not token:
            sys.exit("Sin token de GitHub: `gh auth login` o GITHUB_TOKEN.")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}",
                               "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28"})

    def pedir(self, ruta, params=None, crudo=False):
        """Devuelve (cuerpo, respuesta). Espera si se agota la cuota."""
        for intento in range(8):
            try:
                r = self.s.get(f"{API}{ruta}", params=params, timeout=60,
                               headers={"Accept": "application/vnd.github.raw+json"} if crudo else None)
            except requests.RequestException:
                time.sleep(10 * (intento + 1))
                continue
            if r.status_code in (403, 429) and (r.headers.get("X-RateLimit-Remaining") == "0"
                                                or "retry-after" in r.headers):
                if "retry-after" in r.headers:
                    espera = int(r.headers["retry-after"]) + 1
                else:
                    espera = max(int(r.headers.get("X-RateLimit-Reset", time.time() + 60)) - time.time(), 0) + 5
                print(f"  límite de GitHub: espero {espera:.0f} s", flush=True)
                time.sleep(espera)
                continue
            if r.status_code >= 500:
                time.sleep(10)
                continue
            if r.status_code >= 400:
                return None, r
            return (r.text if crudo else r.json()), r
        return None, None

    def get(self, ruta, params=None, crudo=False):
        return self.pedir(ruta, params, crudo)[0]

    def contar(self, ruta, params=None):
        """Total de elementos de un listado paginado (per_page=1 + Link)."""
        cuerpo, r = self.pedir(ruta, dict(params or {}, per_page=1))
        if r is None or cuerpo is None:
            return 0
        enlace = r.headers.get("Link", "")
        ultima = re.search(r'[?&]page=(\d+)>; rel="last"', enlace)
        return int(ultima.group(1)) if ultima else len(cuerpo)


def excluidos():
    """Ya registrados en la plataforma o en el dataset de entrenamiento anterior."""
    csv.field_size_limit(10 ** 9)
    nombres = set()
    for ruta in DATASETS:
        with open(RAIZ / ruta, encoding="utf-8") as f:
            nombres |= {fila["repository_name"].lower() for fila in csv.DictReader(f)}
    sys.path.insert(0, str(RAIZ / "backend"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.db import OperationalError
    from riesgo.models import Repositorio
    try:
        nombres |= {n.lower() for n in Repositorio.objects.values_list("nombre_completo", flat=True)}
    except OperationalError:
        # Sin acceso a la base de la plataforma: se usan los repos cargados
        # desde datos_prueba (los 30 casos) y el repo de demostración. Hay que
        # cruzar la lista final con la base cuando vuelva a estar disponible.
        print("AVISO: sin acceso a la base de la plataforma; se excluyen los repos de "
              "datos_prueba/casos_prueba_30.json y el de demostración", flush=True)
        casos = json.loads((RAIZ / "datos_prueba" / "casos_prueba_30.json").read_text(encoding="utf-8"))
        nombres |= {c["repositorio"].lower() for c in casos}
        nombres.add("erickterranova2004/demo-despliegue-riesgo")
    return nombres


# ------------------------------------------------------------------ candidatos
def candidatos(args):
    gh = GitHub()
    fuera = excluidos()
    lista = leer(CANDIDATOS, {"items": [], "consultas_hechas": []})
    vistos = {c["repositorio"].lower() for c in lista["items"]}
    # Primero los elegidos en las búsquedas anteriores.
    for previo in PREVIOS + [Path(p) for p in args.previos]:
        for c in leer(previo, []):
            if c["repositorio"].lower() not in vistos | fuera:
                lista["items"].append({"repositorio": c["repositorio"], "ruta": c["ruta_workflow"],
                                       "consulta": "búsqueda anterior"})
                vistos.add(c["repositorio"].lower())
    consultas = ([f"{c} {s}" for c in CONSULTAS_E2 for s in SUFIJOS_E2] if args.estrategia2
                 else [c for c, _, _, _ in MARCADORES if c not in CONSULTAS_DESCARTADAS])
    for consulta in consultas:
        for pagina in range(1, 11):
            clave = f"{consulta}#{pagina}"
            if clave in lista["consultas_hechas"]:
                continue
            res = gh.get("/search/code", {"q": f"{consulta} path:.github/workflows", "per_page": 100,
                                          "page": pagina})
            time.sleep(6.5)  # búsqueda de código: 10 consultas por minuto
            lista["consultas_hechas"].append(clave)
            items = (res or {}).get("items") or []
            for item in items:
                repo, ruta = item["repository"]["full_name"], item["path"]
                if (repo.lower() in vistos or repo.lower() in fuera or item["repository"].get("fork")
                        or not re.fullmatch(r"\.github/workflows/[^/]+\.ya?ml", ruta)):
                    continue
                vistos.add(repo.lower())
                lista["items"].append({"repositorio": repo, "ruta": ruta, "consulta": consulta})
            guardar(CANDIDATOS, lista)
            print(f"{consulta} p{pagina}: {len(items)} resultados · candidatos {len(lista['items'])}", flush=True)
            if len(items) < 100:
                break


# ------------------------------------------------------------------ prefiltrar
CONSULTA_GRAPHQL = """
  r{i}: repository(owner: {owner}, name: {name}) {{
    owner {{ __typename }}
    createdAt pushedAt isFork isArchived isPrivate stargazerCount
    produccion: deployments(environments: {entornos}) {{ totalCount }}
    environments(first: 30) {{ nodes {{ name }} }}
  }}"""


def graphql(gh, consulta):
    for intento in range(6):
        r = gh.s.post(f"{API}/graphql", json={"query": consulta}, timeout=60)
        if r.status_code in (403, 429, 502, 503):
            espera = int(r.headers.get("retry-after", 0)) or max(
                int(r.headers.get("X-RateLimit-Reset", time.time() + 60)) - time.time(), 0) + 5
            print(f"  límite de GraphQL: espero {min(espera, 3700):.0f} s", flush=True)
            time.sleep(min(espera, 3700))
            continue
        if r.ok:
            return r.json().get("data") or {}
        time.sleep(10 * (intento + 1))
    return {}


def prefiltrar(args):
    """Descarta sin perfilar los candidatos que no cumplen: dueño
    Organization, más de MIN_DIAS_ACTIVIDAD días de actividad y al menos
    MIN_CONTRIBUIDORES contribuidores. Registra los deployments a
    producción para priorizar el perfilado."""
    gh = GitHub()
    candidatos_ = [c for c in leer(CANDIDATOS, {"items": []})["items"]
                   if c["consulta"] not in CONSULTAS_DESCARTADAS]
    perfiles = leer(PERFILES, {})
    pre = leer(PREFILTRO, {})
    pendientes = [c for c in candidatos_ if c["repositorio"] not in perfiles and c["repositorio"] not in pre]
    if args.max:
        pendientes = pendientes[:args.max]
    entornos = json.dumps(ENTORNOS_PRODUCCION)
    for inicio in range(0, len(pendientes), 50):
        lote = pendientes[inicio:inicio + 50]
        consulta = "query {" + "".join(
            CONSULTA_GRAPHQL.format(i=i, owner=json.dumps(c["repositorio"].split("/")[0]),
                                    name=json.dumps(c["repositorio"].split("/")[1]), entornos=entornos)
            for i, c in enumerate(lote)) + "}"
        datos = graphql(gh, consulta)
        for i, c in enumerate(lote):
            r = datos.get(f"r{i}")
            fila = {"consulta": c["consulta"], "ruta": c["ruta"], "pasa": False}
            if not r:
                fila["motivo"] = "no accesible"
            elif r["owner"]["__typename"] != "Organization":
                fila["motivo"] = "el dueño no es una organización"
            elif r["isFork"] or r["isArchived"] or r["isPrivate"]:
                fila["motivo"] = "fork, archivado o privado"
            else:
                dias = (datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00"))
                        - datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))).days
                fila.update({"dias": dias, "produccion": r["produccion"]["totalCount"],
                             "entornos": [e["name"] for e in r["environments"]["nodes"]],
                             "estrellas": r["stargazerCount"]})
                if dias <= MIN_DIAS_ACTIVIDAD:
                    fila["motivo"] = f"menos de {MIN_DIAS_ACTIVIDAD} días de actividad"
                else:
                    fila["contribuidores"] = gh.contar(f"/repos/{c['repositorio']}/contributors",
                                                       {"anon": "false"})
                    if fila["contribuidores"] < MIN_CONTRIBUIDORES:
                        fila["motivo"] = f"menos de {MIN_CONTRIBUIDORES} contribuidores"
                    else:
                        fila["pasa"] = True
            pre[c["repositorio"]] = fila
        guardar(PREFILTRO, pre)
        pasan = sum(1 for f in pre.values() if f["pasa"])
        print(f"prefiltrados {len(pre)} · pasan {pasan} · con deployments a producción "
              f"{sum(1 for f in pre.values() if f['pasa'] and f.get('produccion'))}", flush=True)


# ------------------------------------------------------------------ perfilar
def disparadores(on):
    if isinstance(on, str):
        on = {on: None}
    elif isinstance(on, list):
        on = {e: None for e in on}
    return on if isinstance(on, dict) else {}


def analizar_yaml(contenido):
    """Paso de despliegue del workflow y motivos de exclusión del YAML."""
    try:
        datos = yaml.safe_load(contenido)
    except yaml.YAMLError:
        return None, "YAML no legible"
    if not isinstance(datos, dict) or not isinstance(datos.get("jobs"), dict):
        return None, "YAML sin jobs"
    on = disparadores(datos.get("on", datos.get(True)))
    if EFIMERO.search(contenido):
        return None, "despliega en un clúster efímero de prueba (kind/minikube/k3d/localstack)"
    for nombre_job, job in datos["jobs"].items():
        if not isinstance(job, dict):
            continue
        for paso in job.get("steps") or []:
            if not isinstance(paso, dict):
                continue
            texto = f"{paso.get('uses', '')}\n{paso.get('run', '')}"
            for _, patron, proveedor, servicio in MARCADORES:
                if not re.search(patron, texto, re.IGNORECASE):
                    continue
                if "appleboy/ssh-action" in str(paso.get("uses", "")) and not SCRIPT_DESPLIEGUE.search(
                        str((paso.get("with") or {}).get("script", ""))):
                    continue
                condicion = f"{job.get('if', '')} {paso.get('if', '')}"
                entorno = job.get("environment")
                entorno = entorno.get("name") if isinstance(entorno, dict) else entorno
                solo_pr = set(on) <= {"pull_request", "pull_request_target"}
                if solo_pr or PREVIEW.search(f"{condicion} {entorno or ''} {nombre_job}") and \
                        "pull_request" in condicion:
                    continue
                return {"job": str(nombre_job), "entorno": str(entorno or ""),
                        "paso": str(paso.get("name") or paso.get("uses") or "run"),
                        "uses": str(paso.get("uses") or "").strip(), "proveedor": proveedor,
                        "servicio": servicio, "eventos": sorted(map(str, on))}, None
    return None, "ningún paso despliega a un entorno de aplicación (o solo previews de PR)"


def actividad(runs, commits):
    """Motivo de actividad sospechosa, o None."""
    if not runs:
        return None
    eventos = Counter(r.get("event") for r in runs)
    if eventos.get("schedule", 0) / len(runs) > 0.5:
        return "más de la mitad de las ejecuciones son programadas (cron): ejecuciones en bucle"
    por_sha = Counter(r.get("head_sha") for r in runs)
    if len(runs) >= 20 and por_sha.most_common(1)[0][1] / len(runs) > 0.5:
        return "más de la mitad de las ejecuciones repiten el mismo commit: ejecuciones en bucle"
    if commits["muestra"] >= 20 and commits["bots"] / commits["muestra"] > 0.8:
        return "más del 80 % de los commits recientes son automáticos (bots)"
    return None


def perfilar(args):
    gh = GitHub()
    lista = leer(CANDIDATOS, {"items": []})["items"]
    perfiles = leer(PERFILES, {})
    nuevos = 0
    # Se alterna entre búsquedas (plataformas) para que la muestra revisada
    # sea variada aunque no se perfilen todos los candidatos.
    por_consulta = defaultdict(list)
    for cand in lista:
        por_consulta[cand["consulta"]].append(cand)
    colas = list(por_consulta.values())
    lista = [cola[i] for i in range(max(map(len, colas), default=0)) for cola in colas if i < len(cola)]
    if args.prefiltrados:
        # Estrategia 2: solo los que pasaron el prefiltro, primero los que
        # tienen más deployments registrados en producción.
        pre = leer(PREFILTRO, {})
        lista = sorted((c for c in lista if pre.get(c["repositorio"], {}).get("pasa")),
                       key=lambda c: (-pre[c["repositorio"]].get("produccion", 0), c["repositorio"].lower()))
    for cand in lista:
        repo = cand["repositorio"]
        if repo in perfiles:
            continue
        if args.max and nuevos >= args.max:
            break
        nuevos += 1
        p = {"repositorio": repo, "ruta": cand["ruta"], "consulta": cand["consulta"], "excluido": None}
        perfiles[repo] = p
        owner = repo.split("/")[0].lower()
        if owner in EXCLUIR_ORGANIZACIONES:
            p["excluido"] = "organización de tesis/proyectos académicos (Tesis-2026)"
            continue
        archivo = cand["ruta"].rsplit("/", 1)[-1]
        # 1. Actividad del workflow (lo más barato y lo que más descarta).
        datos = gh.get(f"/repos/{repo}/actions/workflows/{archivo}/runs",
                       {"status": "completed", "created": f">={DESDE}", "per_page": 100}) or {}
        runs = datos.get("workflow_runs", [])
        p["ejecuciones_6m"] = datos.get("total_count", 0)
        if p["ejecuciones_6m"] < MIN_EJECUCIONES:
            p["excluido"] = f"menos de {MIN_EJECUCIONES} ejecuciones terminadas en 6 meses"
            continue
        conclusiones = Counter(r.get("conclusion") for r in runs)
        p["conclusiones"] = dict(conclusiones)
        p["runs"] = [{"id": r["id"], "intento": r.get("run_attempt") or 1, "conclusion": r.get("conclusion"),
                      "evento": r.get("event"), "sha": r.get("head_sha"), "inicio": r.get("run_started_at")}
                     for r in runs[:RUNS_ETIQUETAR]]
        # 2. El YAML: paso de despliegue real.
        contenido = gh.get(f"/repos/{repo}/contents/{cand['ruta']}", crudo=True) or ""
        paso, motivo = analizar_yaml(contenido)
        if not paso:
            p["excluido"] = motivo
            continue
        p["paso"] = paso
        # 3. Repositorio, README, contribuidores y commits.
        info = gh.get(f"/repos/{repo}") or {}
        if not info or info.get("fork") or info.get("archived") or info.get("private"):
            p["excluido"] = "fork, archivado o privado"
            continue
        p.update({"descripcion": info.get("description") or "", "topics": info.get("topics") or [],
                  "web": info.get("homepage") or "", "estrellas": info.get("stargazers_count", 0),
                  "tipo_propietario": (info.get("owner") or {}).get("type"),
                  "creado": info.get("created_at"), "ultimo_push": info.get("pushed_at"),
                  "licencia": ((info.get("license") or {}).get("spdx_id")) or ""})
        readme = gh.get(f"/repos/{repo}/readme", crudo=True) or ""
        p["readme"] = re.sub(r"<[^>]+>|!\[[^\]]*\]\([^)]*\)|\[!\[.*?\)\]\(.*?\)", " ", readme)
        p["readme"] = re.sub(r"\s+", " ", p["readme"]).strip()[:600]
        p["contribuidores"] = gh.contar(f"/repos/{repo}/contributors", {"anon": "false"})
        p["commits_total"] = gh.contar(f"/repos/{repo}/commits")
        recientes = gh.get(f"/repos/{repo}/commits", {"per_page": 100}) or []
        fechas = [c["commit"]["committer"]["date"] for c in recientes if c.get("commit")]
        autores = [((c.get("author") or {}).get("login") or c["commit"]["author"]["name"]) for c in recientes
                   if c.get("commit")]
        p["commits"] = {"muestra": len(recientes), "bots": sum(bool(BOT.search(a or "")) for a in autores),
                        "autores": len({a for a in autores if not BOT.search(a or "")}),
                        "desde": min(fechas) if fechas else None, "hasta": max(fechas) if fechas else None}
        primero = p["creado"] or p["commits"]["desde"]
        dias = (datetime.fromisoformat(p["ultimo_push"].replace("Z", "+00:00"))
                - datetime.fromisoformat(primero.replace("Z", "+00:00"))).days if primero and p["ultimo_push"] else 0
        p["dias_historial"] = dias
        if p["commits_total"] < 20 or dias < 60:
            p["excluido"] = "historial de commits insuficiente (menos de 20 commits o de 60 días)"
            continue
        sospecha = actividad(runs, p["commits"])
        if sospecha:
            p["excluido"] = sospecha
            continue
        texto = " ".join([repo, p["descripcion"], " ".join(p["topics"]), p["readme"][:300]])
        p["pistas"] = sorted({m.group(0).lower() for m in PISTAS.finditer(texto)})
        if nuevos % 10 == 0:
            guardar(PERFILES, perfiles)
            validos = sum(1 for x in perfiles.values() if not x["excluido"])
            print(f"perfilados {len(perfiles)} · pasan los filtros automáticos {validos}", flush=True)
    guardar(PERFILES, perfiles)
    validos = sum(1 for x in perfiles.values() if not x["excluido"])
    print(f"Fin: perfilados {len(perfiles)} · pasan los filtros automáticos {validos}")


# ------------------------------------------------------------------ revisar
def senales(p):
    """Señales de aplicación en uso. Solo ordenan la revisión manual: los
    perfiles con más señales se revisan primero; ninguno se aprueba por ellas."""
    return ((p.get("tipo_propietario") == "Organization") + bool(p.get("web")) + (p.get("contribuidores", 0) >= 3)
            + (p.get("estrellas", 0) >= 5) + (p.get("commits_total", 0) >= 300) - 2 * bool(p.get("pistas")))


def ocupacion(perfiles, revision):
    """Repos aprobados por plataforma y por organización.

    Cuenta los aprobados en la revisión manual salvo los ya descartados por
    el criterio 2 (despliegue nunca ejecutado en su historial completo)."""
    etiquetas, historial = leer(ETIQUETAS, {}), leer(HISTORIAL, {})
    por_plat, por_org = Counter(), Counter()
    for repo, d in revision.items():
        if d["decision"] != "valido":
            continue
        completo = repo in etiquetas and len(etiquetas[repo]) >= len(historial.get(repo, []))
        if completo and not resumen_etiquetas(etiquetas[repo])[3]:
            continue
        por_plat[perfiles[repo]["paso"]["proveedor"]] += 1
        por_org[repo.split("/")[0].lower()] += 1
    return por_plat, por_org


def pendientes_de_revision():
    """Perfiles por revisar que todavía pueden contar para la selección.

    Se saltan los de plataformas que ya llegaron al 30 % del mínimo de 200 y
    los de organizaciones con MAX_POR_ORGANIZACION aprobados. Primero van las
    plataformas con menos repos y, dentro de cada una, los de más señales."""
    perfiles = leer(PERFILES, {})
    revision = leer(REVISION, {})
    por_plat, por_org = ocupacion(perfiles, revision)
    tope_plataforma = int(MAX_PROPORCION_PLATAFORMA * MINIMO)
    pendientes = [p for p in perfiles.values()
                  if not p["excluido"] and p["repositorio"] not in revision
                  and por_plat[p["paso"]["proveedor"]] < tope_plataforma
                  and por_org[p["repositorio"].split("/")[0].lower()] < MAX_POR_ORGANIZACION
                  # Estrategia 2: mismos requisitos que el prefiltro.
                  and p["consulta"] not in CONSULTAS_DESCARTADAS
                  and p.get("tipo_propietario") == "Organization"
                  and p.get("contribuidores", 0) >= MIN_CONTRIBUIDORES
                  and p.get("dias_historial", 0) > MIN_DIAS_ACTIVIDAD]
    return sorted(pendientes, key=lambda p: (por_plat[p["paso"]["proveedor"]], -senales(p),
                                             p["repositorio"].lower()))


def revisar(args):
    pendientes = pendientes_de_revision()[:50]
    for p in pendientes:
        c = p["commits"]
        print(f"### {p['repositorio']}  [{p['paso']['proveedor']} · {p['paso']['servicio']}]"
              f"  ★{p['estrellas']} · {p['tipo_propietario']} · contrib {p['contribuidores']} · "
              f"commits {p['commits_total']} ({p['dias_historial']} días, {c['autores']} autores recientes)"
              f" · ejec 6m {p['ejecuciones_6m']} {p.get('conclusiones')}")
        print(f"  desc: {p['descripcion'][:160]} | topics: {', '.join(p['topics'][:6])} | web: {p['web']}")
        print(f"  readme: {p['readme'][:280]}")
        if p.get("pistas"):
            print(f"  PISTAS: {', '.join(p['pistas'])}")
    print(f"\n{len(pendientes)} perfiles en este lote · pendientes en total: {len(pendientes_de_revision())}")


# ------------------------------------------------------------------ etiquetar
# Versión de la regla de etiquetado. Las etiquetas de una versión anterior se
# vuelven a calcular. 3: solo producción y patrón con ecs (2026-11-08).
REGLA = 6  # 4: señales del YAML y sin hosting estático; 5: YAML del commit de cada ejecución;
# 6: el nombre del job también marca el hosting estático y «matrix» es paso auxiliar


def afectada_por_regla6(fila, conclusion):
    """La regla 6 solo deja de contar pasos como despliegue: puede cambiar la y
    de las ejecuciones y=0, de las ambiguas y de los fallos excluidos por no
    ser producción. El resto conserva la etiqueta de la regla 5."""
    return (fila.get("y") == 0 or fila.get("etiqueta") == "excluida_ambigua"
            or (fila.get("etiqueta") == "excluida_no_produccion" and conclusion == "failure"))


def etiquetar_fila(run, jobs, etiquetar_ejecucion, patron):
    """Etiqueta una ejecución con la regla de la fase 2 de la plataforma
    (incluye excluir las que terminaron sin ningún job)."""
    e = etiquetar_ejecucion(run["conclusion"], jobs, patron)
    y = {"despliegue_completado": 0, "despliegue_no_completado": 1}.get(e["etiqueta"])
    return {"run": run["id"], "etiqueta": e["etiqueta"], "subtipo": e["subtipo_etiqueta"],
            "despliegue_ejecutado": e["despliegue_ejecutado"], "y": y, "n_jobs": len(jobs),
            "paso_fallido": e["paso_fallido"], "regla": REGLA,
            # Hubo un despliegue a hosting estático (no cuenta como aplicación).
            "hosting_estatico": any(
                re.search(REGLA_PLATAFORMA.PATRON_HOSTING_ESTATICO,
                          f"{j.get('name') or ''}\n{p.get('name') or ''}\n{p.get('uses') or ''}\n{p.get('run') or ''}")
                for j in jobs if j.get("conclusion") != "skipped"
                for p in j.get("steps") or [] if p.get("conclusion") == "success")}


def contar_jobs(args):
    """Completa el número de jobs de las ejecuciones y=1 etiquetadas antes de
    guardarse ese dato, y excluye las que no tuvieron ningún job."""
    gh = GitHub()
    etiquetas = leer(ETIQUETAS, {})
    historial = leer(HISTORIAL, {})
    for i, (repo, filas) in enumerate(etiquetas.items(), 1):
        intentos = {r["id"]: r["intento"] for r in historial.get(repo, [])}
        cambiadas = 0
        for f in filas:
            if f["y"] != 1 or "n_jobs" in f:
                continue
            datos = gh.get(f"/repos/{repo}/actions/runs/{f['run']}/attempts/{intentos.get(f['run'], 1)}/jobs",
                           {"per_page": 1}) or {}
            f["n_jobs"] = datos.get("total_count", 0)
            if f["n_jobs"] == 0:
                f.update({"etiqueta": "excluida_sin_jobs", "subtipo": "", "y": None})
                cambiadas += 1
        guardar(ETIQUETAS, etiquetas)
        print(f"{i}/{len(etiquetas)} {repo}: {cambiadas} ejecuciones sin jobs excluidas", flush=True)


# Repos cuyo workflow despliega a producción y a otros entornos: solo cuentan
# las ejecuciones cuyo despliegue va a producción (fase 2, «Excluidas»).
MIXTOS_PRODUCCION = ["ASL-LEX/SignTag", "OpenReferralUK/oruk-validator", "alliance-genome/agr_curation",
                     "elsa-hanke/elsa-backend", "emerald-legacy/emeralddb", "infanf/myanili",
                     "ministryofjustice/laa-fee-calculator", "nulib/dc-api-v2", "sovereign-nature/deep"]
# Entorno decidido por la rama cuando el YAML lo calcula con una expresión.
ENTORNO_POR_RAMA = {"nulib/dc-api-v2": {"main": "production"}}


WORKFLOWS_YAML = CACHE / "workflows_yaml.json"


def info_workflow(contenido):
    """Misma función que la plataforma (backend/riesgo/services/etiquetado.py)."""
    return modulo_etiquetado().info_workflow(contenido)


def cache_yaml_vacia():
    """{"por_commit": {"repo@sha": huella}, "info": {huella: info_workflow}}."""
    cache = leer(WORKFLOWS_YAML, {})
    return cache if "por_commit" in cache else {"por_commit": {}, "info": {}}


def yaml_de(gh, repo, ruta, cache, sha=None):
    """(info, huella) del workflow en el commit `sha` de la ejecución (o en la
    rama por defecto si sha es None). Caché por commit y por contenido."""
    clave = f"{repo}@{sha or 'HEAD'}"
    if clave not in cache["por_commit"]:
        contenido = gh.get(f"/repos/{repo}/contents/{ruta}", {"ref": sha} if sha else None, crudo=True) or ""
        huella = hashlib.sha1(contenido.encode("utf-8")).hexdigest()[:16]
        cache["info"].setdefault(huella, info_workflow(contenido))
        cache["por_commit"][clave] = huella
        guardar(WORKFLOWS_YAML, cache)
    huella = cache["por_commit"][clave]
    return cache["info"][huella], huella


def enriquecer(jobs, info, entorno_rama=None):
    """Misma función que la plataforma (backend/riesgo/services/etiquetado.py)."""
    return modulo_etiquetado().enriquecer(jobs, info, entorno_rama)


def produccion(args):
    """Re-etiqueta los repos mixtos contando solo los despliegues a
    producción. El entorno de cada job sale de su nombre, del environment
    literal del YAML o, si es una expresión, de la rama (ENTORNO_POR_RAMA).
    Un fallo antes de cualquier despliegue solo cuenta si la ejecución es de
    una rama desde la que hubo algún despliegue completado a producción."""
    gh = GitHub()
    etiquetar_ejecucion, patron = etiquetador()
    perfiles, historial = leer(PERFILES, {}), leer(HISTORIAL, {})
    etiquetas = leer(ETIQUETAS, {})
    cache_yaml = cache_yaml_vacia()
    resumen = {}
    for repo in MIXTOS_PRODUCCION:
        ruta = perfiles[repo]["ruta"]
        archivo = ruta.rsplit("/", 1)[-1]
        ramas = {r["id"]: r.get("head_branch") or "" for r in (gh.get(
            f"/repos/{repo}/actions/workflows/{archivo}/runs",
            {"status": "completed", "per_page": RUNS_ETIQUETAR}) or {}).get("workflow_runs", [])}
        antes = Counter(f["y"] for f in etiquetas.get(repo, []))
        filas = []
        for run in historial[repo]:
            if run["conclusion"] not in ("success", "failure"):
                filas.append({"run": run["id"], "etiqueta": "excluida_otro_resultado", "y": None})
                continue
            jobs = (gh.get(f"/repos/{repo}/actions/runs/{run['id']}/attempts/{run['intento']}/jobs",
                           {"per_page": 100}) or {}).get("jobs", [])
            rama = ramas.get(run["id"], "")
            entorno_rama = ENTORNO_POR_RAMA[repo].get(rama, "staging") if repo in ENTORNO_POR_RAMA else None
            info, huella = yaml_de(gh, repo, ruta, cache_yaml, run.get("sha"))
            fila = etiquetar_fila(run, enriquecer(jobs, info, entorno_rama), etiquetar_ejecucion, patron)
            fila["yaml"] = huella
            fila["rama"] = rama
            filas.append(fila)
        ramas_produccion = {f["rama"] for f in filas if f["y"] == 0}
        for f in filas:
            if f["y"] == 1 and f.get("subtipo") == "antes_del_despliegue" and f.get("rama") not in ramas_produccion:
                f.update({"etiqueta": "excluida_no_produccion", "subtipo": "", "y": None})
        etiquetas[repo] = filas
        guardar(ETIQUETAS, etiquetas)
        despues = Counter(f["y"] for f in filas)
        quitadas = sum(f["etiqueta"] == "excluida_no_produccion" for f in filas)
        resumen[repo] = {"antes": [antes[0], antes[1]], "despues": [despues[0], despues[1]],
                         "no_produccion": quitadas, "ramas_produccion": sorted(ramas_produccion)}
        print(f"{repo}: y=0/y=1 {antes[0]}/{antes[1]} → {despues[0]}/{despues[1]} · "
              f"excluidas por no ser producción {quitadas} · ramas de producción {sorted(ramas_produccion)}",
              flush=True)
    guardar(CACHE / "produccion.json", resumen)


def etiquetar(args):
    gh = GitHub()
    etiquetar_ejecucion, patron = etiquetador()
    perfiles = leer(PERFILES, {})
    revision = leer(REVISION, {})
    etiquetas = leer(ETIQUETAS, {})
    historial = leer(HISTORIAL, {})
    cache_yaml = cache_yaml_vacia()
    aprobados = [r for r, d in revision.items() if d["decision"] == "valido"]
    for i, repo in enumerate(aprobados, 1):
        if repo not in historial:
            # Las RUNS_ETIQUETAR ejecuciones terminadas más recientes, aunque
            # superen la ventana de 6 meses (que solo mide la actividad).
            archivo = perfiles[repo]["ruta"].rsplit("/", 1)[-1]
            datos = gh.get(f"/repos/{repo}/actions/workflows/{archivo}/runs",
                           {"status": "completed", "per_page": RUNS_ETIQUETAR}) or {}
            historial[repo] = [{"id": r["id"], "intento": r.get("run_attempt") or 1,
                                "conclusion": r.get("conclusion"), "evento": r.get("event"),
                                "sha": r.get("head_sha"), "inicio": r.get("run_started_at")}
                               for r in datos.get("workflow_runs", [])] or perfiles[repo]["runs"]
            guardar(HISTORIAL, historial)
        if repo in MIXTOS_PRODUCCION:
            continue  # los etiqueta la etapa produccion (entorno por job y rama)
        previas = {f["run"]: f for f in etiquetas.get(repo, [])}
        if all(previas.get(r["id"], {}).get("regla", 0) >= REGLA
               or previas.get(r["id"], {}).get("etiqueta") == "excluida_otro_resultado" for r in historial[repo]):
            continue
        ruta = perfiles[repo]["ruta"]
        filas, recalculadas, cambiadas = [], 0, 0
        for run in historial[repo]:
            previa = previas.get(run["id"], {})
            if previa.get("regla", 0) >= REGLA or run["conclusion"] not in ("success", "failure"):
                filas.append(previa if previa.get("regla", 0) >= REGLA else
                             {"run": run["id"], "etiqueta": "excluida_otro_resultado", "y": None})
                continue
            if previa.get("regla") == 5 and not afectada_por_regla6(previa, run["conclusion"]):
                filas.append(dict(previa, regla=REGLA))
                continue
            info, huella = yaml_de(gh, repo, ruta, cache_yaml, run["sha"])
            # Etiqueta de la regla 4 (YAML actual): sigue valiendo si el YAML
            # del commit es idéntico al actual.
            if previa.get("regla") == 4 and huella == yaml_de(gh, repo, ruta, cache_yaml)[1]:
                filas.append(dict(previa, regla=REGLA, yaml=huella))
                continue
            jobs = (gh.get(f"/repos/{repo}/actions/runs/{run['id']}/attempts/{run['intento']}/jobs",
                           {"per_page": 100}) or {}).get("jobs", [])
            fila = etiquetar_fila(run, enriquecer(jobs, info), etiquetar_ejecucion, patron)
            fila["yaml"] = huella
            recalculadas += previa.get("regla") == 4
            cambiadas += previa.get("regla") == 5 and previa.get("y") != fila["y"]
            filas.append(fila)
        etiquetas[repo] = filas
        guardar(ETIQUETAS, etiquetas)
        conteo = Counter(f["y"] for f in filas)
        print(f"{i}/{len(aprobados)} {repo}: y=0 {conteo[0]} · y=1 {conteo[1]} · excluidas {conteo[None]}"
              f" · recalculadas de la regla 4 por YAML distinto {recalculadas}"
              f" · y cambiada por la regla 6 {cambiadas}",
              flush=True)


PRODUCCION_NOMBRE = re.compile(r"(?i)\bprod|production|\blive\b")


def input_de_entorno(inputs):
    """El workflow_dispatch tiene un input que elige el entorno de destino: de
    tipo environment, o con nombre de entorno (environment, env, stage,
    target…) cuyo valor es libre o tiene alguna opción no productiva."""
    no_produccion = re.compile(REGLA_PLATAFORMA.PATRON_NO_PRODUCCION)
    for nombre, spec in (inputs or {}).items():
        spec = spec if isinstance(spec, dict) else {}
        if spec.get("type") == "environment":
            return True
        if re.search(r"(?i)env|stage|target|destino|deploy_?to", str(nombre)):
            if spec.get("type") == "boolean":
                continue
            opciones = [str(o) for o in spec.get("options") or []]
            if not opciones or any(no_produccion.search(o) for o in opciones):
                return True
    return False


def entorno_indeterminado(contenido):
    """Regla de workflow_dispatch: el entorno lo elige un input y ningún job lo
    declara de forma literal ni lo indica en su nombre, así que en una
    ejecución manual no se puede saber a qué entorno se desplegó."""
    try:
        datos = yaml.safe_load(contenido) or {}
    except yaml.YAMLError:
        return False
    if not isinstance(datos, dict):
        return False
    on = disparadores(datos.get("on", datos.get(True)))
    dispatch = on.get("workflow_dispatch") if isinstance(on, dict) else None
    if not input_de_entorno((dispatch or {}).get("inputs") if isinstance(dispatch, dict) else None):
        return False
    no_produccion = re.compile(REGLA_PLATAFORMA.PATRON_NO_PRODUCCION)
    for clave, job in (datos.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        entorno = job.get("environment")
        entorno = entorno.get("name") if isinstance(entorno, dict) else entorno
        if entorno and "${{" not in str(entorno):
            return False
        nombre = f"{clave} {job.get('name') or ''}"
        if "${{" not in nombre and (PRODUCCION_NOMBRE.search(nombre) or no_produccion.search(nombre)):
            return False
    return True


def dispatch(args):
    """Excluye las ejecuciones manuales (workflow_dispatch) cuyo entorno de
    destino no se puede determinar (fase 2, «Excluidas»)."""
    gh = GitHub()
    etiquetador()
    revision = leer(REVISION, {})
    etiquetas, historial = leer(ETIQUETAS, {}), leer(HISTORIAL, {})
    perfiles = leer(PERFILES, {})
    cache = leer(CACHE / "dispatch.json", {})
    total = 0
    for repo, filas in etiquetas.items():
        if revision.get(repo, {}).get("decision") != "valido":
            continue
        runs = {r["id"]: r for r in historial.get(repo, [])}
        excluidas = 0
        for f in filas:
            run = runs.get(f["run"], {})
            if f.get("y") is None or run.get("evento") != "workflow_dispatch":
                continue
            clave = f"{repo}@{run.get('sha')}"
            if clave not in cache:
                contenido = gh.get(f"/repos/{repo}/contents/{perfiles[repo]['ruta']}",
                                   {"ref": run.get("sha")}, crudo=True) or ""
                cache[clave] = entorno_indeterminado(contenido)
                guardar(CACHE / "dispatch.json", cache)
            if cache[clave]:
                f.update({"etiqueta": "excluida_entorno_indeterminado", "subtipo": "",
                          "y_previa": f["y"], "y": None})
                excluidas += 1
        if excluidas:
            total += excluidas
            print(f"{repo}: {excluidas} ejecuciones manuales con entorno indeterminado excluidas", flush=True)
    guardar(ETIQUETAS, etiquetas)
    print(f"Total excluidas: {total}", flush=True)


# ------------------------------------------------------------------ regla 7
# Muestra de validación final (semilla 7): el entorno real de muchas
# ejecuciones se decide al ejecutarse (rama, release, salida de otro job) y
# el YAML no lo dice de forma literal. La regla 7 lo resuelve así:
#  1. Entorno registrado por GitHub (Deployments: el job con `environment`
#     crea un deployment cuyo logUrl lleva el id del job).
#  2. Expresiones `${{ }}` del workflow evaluadas con la rama y el evento de
#     la ejecución: si dan un entorno no productivo, el job no es producción.
#  3. Workflow cuyo nombre o archivo indica un entorno no productivo.
#  4. Rama no productiva (dev, develop, staging, preprod…).
#  5. Regla de la rama de la fase 2 para todos los repos (antes solo en los
#     mixtos): un fallo antes del despliegue solo cuenta en ramas con algún
#     despliegue completado a producción. Así salen los pull requests.
#  6. Ejecución manual cuyo input elige el entorno o el despliegue a
#     producción y que falló antes de desplegar: entorno indeterminado.
# La regla 7 solo restringe: nunca convierte una ejecución en producción.
NO_PRODUCCION_WORKFLOW = re.compile(
    r"(?i)stag|\bstg\b|\bdev\b|develop|\bqa\b|\buat\b|sandbox|preview|demo|pre-?prod|nightly|canary|"
    r"(deploy|to)[-_ ]test\b|\btest[-_ ]?(env|environment|server)\b|(?-i:[a-z](Test|Dev|Staging)\b)")
RAMA_NO_PRODUCCION = re.compile(
    r"(?i)^(dev|devel|develop|development|staging|stage|stg|test|testing|qa|uat|pre-?prod|preproduction|"
    r"sandbox|nightly|beta|canary|demo)([-_/].*)?$")
# Ramas con nombre no productivo que sí despliegan a producción (revisado a mano).
RAMAS_PRODUCCION_EXCEPCION = {
    # «Backend deploy (Tamási Áron)»: desde develop al slot «Production» de Azure Functions.
    "Explorer-Consulting/SchoolFeedBackWebAPI": {"develop"},
}
EVENTOS_PR = {"pull_request", "pull_request_target"}
DESCONOCIDO = object()


def evaluar(expr, ctx):
    """Evalúa una expresión de GitHub Actions con el contexto conocido de la
    ejecución (github.ref, ref_name, event_name, base_ref, head_ref). Devuelve
    el texto resultante o None si depende de algo desconocido (inputs,
    needs, matrix, vars, secrets…)."""
    tokens = re.findall(r"==|!=|&&|\|\||!|\(|\)|,|'(?:[^']|'')*'|[A-Za-z_][\w.\-*]*|\d+(?:\.\d+)?", expr)
    pos = [0]

    def ver():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def tomar():
        pos[0] += 1
        return tokens[pos[0] - 1]

    def verdad(v):
        return v not in (None, False, "", 0)

    def o():
        v = y()
        while ver() == "||":
            tomar()
            d = y()
            v = DESCONOCIDO if v is DESCONOCIDO else (v if verdad(v) else d)
        return v

    def y():
        v = comparar()
        while ver() == "&&":
            tomar()
            d = comparar()
            v = DESCONOCIDO if v is DESCONOCIDO else (d if verdad(v) else v)
        return v

    def comparar():
        v = unario()
        if ver() in ("==", "!="):
            op = tomar()
            d = unario()
            if v is DESCONOCIDO or d is DESCONOCIDO:
                return DESCONOCIDO
            igual = str(v).lower() == str(d).lower()
            return igual if op == "==" else not igual
        return v

    def unario():
        if ver() == "!":
            tomar()
            v = unario()
            return DESCONOCIDO if v is DESCONOCIDO else not verdad(v)
        return primario()

    def primario():
        t = tomar()
        if t == "(":
            v = o()
            if ver() == ")":
                tomar()
            return v
        if t.startswith("'"):
            return t[1:-1].replace("''", "'")
        if re.fullmatch(r"\d+(\.\d+)?", t):
            return float(t)
        if t in ("true", "false", "null"):
            return {"true": True, "false": False, "null": None}[t]
        if ver() == "(":
            tomar()
            args = []
            while ver() not in (")", None):
                args.append(o())
                if ver() == ",":
                    tomar()
            tomar()
            if any(a is DESCONOCIDO for a in args) or t.lower() not in ("startswith", "endswith", "contains"):
                return DESCONOCIDO
            a, b = (str(x).lower() for x in args[:2])
            return {"startswith": a.startswith(b), "endswith": a.endswith(b), "contains": b in a}[t.lower()]
        return ctx.get(t, DESCONOCIDO)

    try:
        v = o()
    except (IndexError, ValueError):
        return None
    if v is DESCONOCIDO or pos[0] != len(tokens):
        return None
    return str(v)


def expresiones(valor):
    """Expresiones ${{ }} dentro de un valor del YAML (texto, lista o dict)."""
    if isinstance(valor, dict):
        return [e for v in valor.values() for e in expresiones(v)]
    if isinstance(valor, list):
        return [e for v in valor for e in expresiones(v)]
    return re.findall(r"\$\{\{(.*?)\}\}", str(valor), re.S) if valor is not None else []


def info_regla7(contenido):
    """Del YAML: nombre del workflow, expresiones que pueden fijar el entorno
    (env global; environment, env y with de cada job) e inputs de entorno."""
    try:
        datos = yaml.safe_load(contenido) or {}
    except yaml.YAMLError:
        datos = {}
    if not isinstance(datos, dict):
        datos = {}
    on = disparadores(datos.get("on", datos.get(True)))
    dispatch_ = on.get("workflow_dispatch") if isinstance(on, dict) else None
    inputs = (dispatch_ or {}).get("inputs") if isinstance(dispatch_, dict) else None
    jobs = {}
    for clave, job in (datos.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        exprs = expresiones(job.get("environment")) + expresiones(job.get("env"))
        for paso in job.get("steps") or []:
            if isinstance(paso, dict):
                exprs += expresiones(paso.get("with"))
        jobs[str(clave)] = exprs
        if job.get("name") and "${{" not in str(job["name"]):
            jobs[str(job["name"])] = exprs
    # Input que decide el despliegue a producción (p. ej. deploy_production).
    input_produccion = any(re.search(r"(?i)prod", f"{k} {(v or {}).get('description', '') if isinstance(v, dict) else ''}")
                           for k, v in (inputs or {}).items())
    return {"nombre": str(datos.get("name") or ""), "global": expresiones(datos.get("env")), "jobs": jobs,
            "input_entorno": input_de_entorno(inputs) or input_produccion,
            "indeterminado": entorno_indeterminado(contenido)}


def entornos_desplegados(repo, desde=""):
    """{id del job: entorno} según los deployments que GitHub registró, desde
    la fecha de la ejecución más antigua que se etiqueta."""
    duenio, nombre = repo.split("/")
    resultado, cursor = {}, None
    for _ in range(10):
        despues = f', after: "{cursor}"' if cursor else ""
        q = (f'{{ repository(owner: "{duenio}", name: "{nombre}") {{ deployments(first: 100, '
             f'orderBy: {{field: CREATED_AT, direction: DESC}}{despues}) {{ pageInfo {{ hasNextPage endCursor }} '
             f'nodes {{ environment createdAt statuses(first: 1) {{ nodes {{ logUrl }} }} }} }} }} }}')
        datos = _graphql(q)
        dep = ((datos or {}).get("repository") or {}).get("deployments") or {}
        for n in dep.get("nodes") or []:
            for s in (n.get("statuses") or {}).get("nodes") or []:
                m = re.search(r"/job/(\d+)", s.get("logUrl") or "")
                if m and n.get("environment"):
                    resultado[int(m.group(1))] = n["environment"]
        nodos = dep.get("nodes") or []
        if not (dep.get("pageInfo") or {}).get("hasNextPage") or (
                desde and nodos and (nodos[-1].get("createdAt") or "") < desde):
            break
        cursor = dep["pageInfo"]["endCursor"]
    return resultado


def _graphql(consulta):
    for intento in range(5):
        r = subprocess.run(["gh", "api", "graphql", "-f", f"query={consulta}"], capture_output=True, text=True,
                           encoding="utf-8")
        if r.returncode == 0:
            return json.loads(r.stdout).get("data")
        if "rate limit" in (r.stderr or "").lower():
            time.sleep(300)
        else:
            time.sleep(5 * (intento + 1))
    return None


def contexto(rama, evento, base):
    tag = evento == "release" or bool(re.match(r"v?\d+\.\d+", rama or ""))
    ref = (f"refs/pull/0/merge" if evento in EVENTOS_PR else
           f"refs/tags/{rama}" if tag else f"refs/heads/{rama}")
    return {"github.ref": ref, "github.ref_name": rama or "", "github.event_name": evento or "",
            "github.base_ref": base or "", "github.head_ref": rama if evento in EVENTOS_PR else "",
            "github.ref_type": "tag" if tag else "branch"}


REGLA_DATASET = 9  # 7: entorno real; 8: sin pasos Build/Pre/Post de GitHub;
# 9: «deployment(s)» no es el verbo y «using ssh key» no es auxiliar (2026-11-11)
PASO_BUILD_DOCKER = re.compile(r"^Build \S+/\S+@\S+")


CONDICION_SOLO_PUSH = re.compile(r"push|github\.ref|ref_name|event_name|refs/(heads|tags)")


def pr_puede_desplegar(contenido, patron):
    """¿Una ejecución de pull request con este YAML llega a desplegar? No, si
    todos los pasos de despliegue (o sus jobs) tienen un `if:` que los limita a
    push, a una rama o a una etiqueta. Sin pasos reconocibles: sí (no se sabe)."""
    try:
        datos = yaml.safe_load(contenido) or {}
    except yaml.YAMLError:
        return True
    accion = re.compile(REGLA_PLATAFORMA.PATRON_ACCION_DESPLIEGUE)
    auxiliar = re.compile(REGLA_PLATAFORMA.PATRON_AUXILIAR)
    condiciones = []
    for job in (datos.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for paso in job.get("steps") or []:
            if not isinstance(paso, dict):
                continue
            codigo = f"{paso.get('uses') or ''}\n{paso.get('run') or ''}"
            nombre = str(paso.get("name") or "")
            if accion.search(codigo) or (re.search(patron, nombre) and not auxiliar.search(nombre)):
                condiciones.append(f"{job.get('if') or ''} {paso.get('if') or ''}")
    return not condiciones or any(not CONDICION_SOLO_PUSH.search(c) for c in condiciones)


def regla_pull_request(filas, gh, repo, ruta, historial, patron):
    """Regla 8 para pull requests (fase 2: un fallo antes del despliegue solo
    cuenta si esa ejecución habría desplegado). Un fallo antes del despliegue
    en un pull request se excluye si, con el YAML de su commit, el despliegue
    está limitado a push, a una rama o a una etiqueta."""
    sha = {r["id"]: r.get("sha") for r in historial}
    cambios = Counter()
    for f in filas:
        if not (f.get("y") == 1 and f.get("subtipo") == "antes_del_despliegue"
                and f.get("evento") in EVENTOS_PR):
            continue
        contenido = gh.get(f"/repos/{repo}/contents/{ruta}", {"ref": sha.get(f["run"])}, crudo=True) or ""
        if not pr_puede_desplegar(contenido, patron):
            f.update({"etiqueta": "excluida_no_produccion", "subtipo": "", "y": None,
                      "motivo_regla7": "pull request: el despliegue solo se ejecuta en push"})
            cambios[(1, "pull_request")] += 1
    return cambios


def regla7(args):
    """Re-etiqueta con la regla vigente del dataset (REGLA_DATASET)."""
    gh = GitHub()
    etiquetar_ejecucion, patron = etiquetador()
    no_produccion = re.compile(REGLA_PLATAFORMA.PATRON_NO_PRODUCCION)
    perfiles, revision = leer(PERFILES, {}), leer(REVISION, {})
    etiquetas, historial = leer(ETIQUETAS, {}), leer(HISTORIAL, {})
    cache_yaml = cache_yaml_vacia()
    cache7 = leer(CACHE / "regla7.json", {"info": {}, "ramas": {}, "deployments": {}})
    aprobados = [r for r, d in revision.items() if d["decision"] == "valido" and (not args.repos or r in args.repos)]
    resumen = Counter()
    for i, repo in enumerate(aprobados, 1):
        filas = etiquetas.get(repo, [])
        if not filas or all((f.get("regla") or 0) >= REGLA_DATASET for f in filas
                            if f.get("etiqueta") != "excluida_otro_resultado"):
            continue
        ruta = perfiles[repo]["ruta"]
        if repo not in cache7["ramas"]:
            runs = (gh.get(f"/repos/{repo}/actions/workflows/{ruta.rsplit('/', 1)[-1]}/runs",
                           {"status": "completed", "per_page": RUNS_ETIQUETAR}) or {}).get("workflow_runs", [])
            cache7["ramas"][repo] = {str(r["id"]): [r.get("head_branch") or "", r.get("event") or "",
                                                    ((r.get("pull_requests") or [{}])[0].get("base") or {}).get("ref", "")]
                                     for r in runs}
            desde = min((r.get("inicio") or "" for r in historial.get(repo, [])), default="")
            cache7["deployments"][repo] = {str(k): v for k, v in entornos_desplegados(repo, desde).items()}
            guardar(CACHE / "regla7.json", cache7)
        ramas, desplegados = cache7["ramas"][repo], cache7["deployments"][repo]
        runs = {r["id"]: r for r in historial.get(repo, [])}
        cambios = Counter()
        for f in filas:
            if (f.get("regla") or 0) >= REGLA_DATASET or not (f.get("y") in (0, 1) or f["etiqueta"] in (
                    "excluida_ambigua", "excluida_entorno_indeterminado")):
                continue
            run = runs[f["run"]]
            rama, evento, base = ramas.get(str(run["id"]), ["", run.get("evento") or "", ""])
            evento = evento or run.get("evento") or ""
            info, huella = yaml_de(gh, repo, ruta, cache_yaml, run.get("sha"))
            if huella not in cache7["info"]:
                contenido = gh.get(f"/repos/{repo}/contents/{ruta}", {"ref": run.get("sha")}, crudo=True) or ""
                cache7["info"][huella] = info_regla7(contenido)
                guardar(CACHE / "regla7.json", cache7)
            i7 = cache7["info"][huella]
            jobs = (gh.get(f"/repos/{repo}/actions/runs/{run['id']}/attempts/{run['intento']}/jobs",
                           {"per_page": 100}) or {}).get("jobs", [])
            if not jobs or all(not j.get("steps") for j in jobs if j.get("conclusion") != "skipped"):
                # La ejecución se borró o sus pasos ya no se conservan (retención
                # de GitHub): se mantiene la etiqueta calculada cuando sí estaban.
                previa_regla = f.get("regla") or 0
                f.update({"regla": REGLA_DATASET, "regla8_sin_datos": "borrada o sin pasos"})
                f.setdefault(f"y_regla{previa_regla}", f.get("y"))
                cambios[("sin datos", "se mantiene")] += 1
                continue
            entorno_rama = ENTORNO_POR_RAMA[repo].get(rama, "staging") if repo in ENTORNO_POR_RAMA else None
            jobs = enriquecer(jobs, info, entorno_rama)
            ctx = contexto(rama, evento, base)
            for job in jobs:
                if str(job.get("id")) in desplegados:
                    job["environment"] = desplegados[str(job["id"])]
                    continue
                if job.get("environment"):
                    continue
                exprs = i7["global"] + (i7["jobs"].get(job.get("name", "")) or
                                        i7["jobs"].get(job.get("name", "").split(" (")[0]) or [])
                valores = [v for v in (evaluar(e, ctx) for e in exprs) if v]
                no_prod = [v for v in valores if no_produccion.search(v) and not PRODUCCION_NOMBRE.search(v)]
                if no_prod:
                    job["environment"] = no_prod[0]
            previa = f.get("y")
            nueva = etiquetar_fila(run, jobs, etiquetar_ejecucion, patron)
            nueva.update({"yaml": huella, "rama": rama, "evento": evento, "regla": REGLA_DATASET,
                          "accion_docker": any(PASO_BUILD_DOCKER.match(p.get("name") or "")
                                               for j in jobs for p in j.get("steps") or [])})
            nombre_wf = f"{i7['nombre']} {ruta.rsplit('/', 1)[-1]}"
            if nueva["y"] is not None or nueva["etiqueta"] == "excluida_ambigua":
                motivo = None
                if rama in RAMAS_PRODUCCION_EXCEPCION.get(repo, set()):
                    pass  # revisado a mano: esa rama despliega a producción
                elif NO_PRODUCCION_WORKFLOW.search(nombre_wf) and not PRODUCCION_NOMBRE.search(nombre_wf):
                    motivo = "workflow no productivo"
                elif RAMA_NO_PRODUCCION.search(rama) and rama not in RAMAS_PRODUCCION_EXCEPCION.get(repo, set()) \
                        and evento not in EVENTOS_PR:
                    motivo = "rama no productiva"
                if motivo:
                    nueva.update({"etiqueta": "excluida_no_produccion", "subtipo": "", "y": None,
                                  "motivo_regla7": motivo})
            if nueva["y"] is not None and evento == "workflow_dispatch" and (
                    i7["indeterminado"] or (i7["input_entorno"] and nueva["subtipo"] == "antes_del_despliegue")):
                nueva.update({"etiqueta": "excluida_entorno_indeterminado", "subtipo": "", "y": None})
            if previa is None and f["etiqueta"] == "excluida_ambigua" and nueva["y"] is not None:
                # La regla 7 solo restringe: una ejecución ambigua sigue excluida.
                nueva.update({"etiqueta": "excluida_ambigua", "subtipo": "", "y": None})
            if (f.get("regla") or 0) >= 7:  # conserva la y de cada regla anterior
                nueva.update({k: v for k, v in f.items() if k.startswith("y_regla")})
                nueva[f"y_regla{f['regla']}"] = previa
            else:
                nueva["y_regla6"] = previa if f["etiqueta"] != "excluida_entorno_indeterminado" else f.get("y_previa")
            cambios[(previa, nueva["y"])] += 1
            f.clear()
            f.update(nueva)
        # Regla de la rama (fase 2) para todos los repos.
        ramas_produccion = {f.get("rama") for f in filas if f.get("y") == 0}
        for f in filas:
            if (f.get("regla") or 0) >= 7 and f.get("y") == 1 and f.get("subtipo") == "antes_del_despliegue" \
                    and f.get("rama") not in ramas_produccion:
                f.update({"etiqueta": "excluida_no_produccion", "subtipo": "", "y": None,
                          "motivo_regla7": "rama sin despliegues a producción"})
                cambios[(1, "rama")] += 1
        cambios.update(regla_pull_request(filas, gh, repo, ruta, historial.get(repo, []), patron))
        etiquetas[repo] = filas
        guardar(ETIQUETAS, etiquetas)
        resumen.update(cambios)
        print(f"{i}/{len(aprobados)} {repo}: " + " · ".join(f"{a}→{b} {n}" for (a, b), n in sorted(
            cambios.items(), key=str)), flush=True)
    print("Resumen:", dict(resumen), flush=True)


# ------------------------------------------------------------------ informe
# Comprobaciones de la regla de etiquetado hechas sobre el dataset (texto del
# informe; los números salen de las salidas de la etapa etiquetar).
VERIFICACIONES = [
    "- **YAML del commit de cada ejecución (regla 5).** Hasta la regla 4 se leía el YAML actual del "
    "workflow. Había 360 ejecuciones en 7 repositorios cuyo YAML podía ser distinto del actual. Al leer el "
    "YAML de su commit, solo 12 se recalcularon (todas de andrewda/inthesoup); el resto tenía el mismo YAML.",
    "- **Hosting estático.** Comparación con la regla 3 de los repositorios aprobados: solo "
    "bmlt-enabled/bmlt-server se quedó sin y=0 por esta regla (sus 16 «despliegues» eran publicaciones "
    "estáticas). Otros cuatro perdieron sus y=0 por otras causas: solana-playground (falso positivo «App "
    "Engine version tag»), pagopa/oneidentity y kiruna-labs/petal (señales de la regla 4) y elsa-backend "
    "(solo staging). En la regla 6, sbmagar13/recipe-jar también salió por hosting estático (job «Deploy to "
    "Cloudflare Pages»).",
    "- **Segunda muestra de 30 ejecuciones y=0 (semilla 2026).** Para cada una se listaron los pasos que la "
    "regla cuenta como despliegue a producción y la señal usada (environment, acción conocida o nombre). "
    "26 eran correctas. Dos falsos positivos se corrigieron en la **regla 6**: el nombre del job también "
    "marca el hosting estático (recipe-jar) y «matrix» es un paso auxiliar (hms-dbmi-cellenics/iac: solo se "
    "generó la matriz y el despliegue se omitió). Con la regla 6 cambió la y de 64 ejecuciones (52 de "
    "recipe-jar y 12 de cellenics/iac). Los otros dos casos eran de gemini-hlsw (lucuma-apps y lucuma-odb), "
    "que desde CI solo despliegan a development; los dos se excluyeron por el criterio 2. Las pruebas de la "
    "regla 6 están en `backend/riesgo/tests/test_etiquetado.py`.",
    "- **Ejecuciones manuales con entorno indeterminado.** La regla excluyó 246 ejecuciones. Diez repositorios se quedaron sin y=0 y salieron: "
    "FHIR/genomics-operations, Opetushallitus/tutu-kasittely, bcgov/dep-public, "
    "department-for-transport-BODS/publish-devolved-bus-registration-data, lAnubisl/LostFilmTorrentsFeed, "
    "pagopa/developer-portal-cms, remails-com/remails, rit-sse/WebsiteTheSSEquel, techmatters/hrm y "
    "zenGate-Global/winter-backend-cardano (226 → 216 válidos).",
    "- **Regla 7 (entorno real de cada ejecución).** Se re-evaluaron todas las ejecuciones etiquetadas de los "
    "279 aprobados. Se mantuvieron 5562 y=0 y 726 y=1. Salieron: 1402 y=1 de ramas sin ningún despliegue "
    "completado a producción (sobre todo PR y ramas de trabajo), 1017 y=0 y 263 y=1 cuyo despliegue iba a un "
    "entorno no productivo (environment de GitHub o expresión evaluada: 447 + 47), de workflows no productivos "
    "(386 + 132) o de ramas no productivas (184 + 84), 157 y=0 en las que ningún paso desplegaba a producción "
    "(p. ej. ansible `--syntax-check`). De las manuales excluidas por la regla anterior, 234 siguen con "
    "entorno indeterminado al re-evaluarlas. La regla 7 solo restringe: 11 ejecuciones "
    "ambiguas de UMNET-perfSONAR/pssid-gui2 que pasaban a y=1 se dejaron excluidas. Doce repositorios se "
    "quedaron sin y=0 y salieron (216 → 204): AllenNeuralDynamics/zombie (`publish_dev.yml`), "
    "PRX/Infrastructure (`deploy-terra-stag.yml`), inu-appcenter/inu-portal-server (`cicd-dev.yml`), "
    "pongstylin/tactics y tornotron/echno-web (workflows de staging/test), bcgov/reserve-rec-admin (entorno "
    "`reserveRecAdminTest`), UTDNebula/api-tools (rama `develop`), naturebase-app/tnc-blue-carbon-cost-tool "
    "(rama `staging`), NewWave4Org/NewWave4.org-frontend-new y ministryofjustice/CFO-DataManagementSystem "
    "(environment no productivo), cbg-ethz/WisePulse y Cour-de-cassation/judilibre-search (ansible "
    "`--syntax-check`).",
    "- **Muestra de validación final.** Encontró un error: obbyworld/obby despliega solo a Cloudflare Pages "
    "con `cloudflare/wrangler-action` y el comando `pages deploy` en el input `command`, que el filtro de "
    "hosting estático no leía. Se excluyó por el criterio 2 (204 → 203) y el script ahora añade los inputs "
    "`command`/`args` de cada paso al texto que revisa ese filtro. Se buscó el mismo caso en los 204 "
    "workflows: solo obby lo tenía (google/neuroglancer ya excluía sus pasos de Firebase Hosting por el nombre).",
    "- **Regla 8 y exclusiones por el criterio 2 (2026-11-11).** Al verificar el dataset de variables v2 "
    "aparecieron errores que la muestra de la regla 7 no vio. (1) **Cinco repositorios cuyo workflow no "
    "despliega a producción**, excluidos: egovernments/Citizen-Complaint-Resolution-System "
    "(`local-setup-ci.yaml`: `ansible-playbook` contra `localhost`), usegalaxy-eu/infrastructure-playbook "
    "(`tpv.yml`: `ansible-playbook --connection=local`), ccrma/webchuck-ide (el despliegue a producción está "
    "comentado; solo despliega la rama `dev`), sillsdev/web-xforge (`e2e-tests.yml`: pruebas de extremo a "
    "extremo con un playbook contra `localhost`) y UMNET-perfSONAR/pssid-gui2 (`ci.yml`: pruebas y escaneo de "
    "CVE; el paso «Build the images this deployment ships» no despliega). (2) **Pasos que GitHub añade "
    "alrededor de una acción** («Build owner/acción@v» de las acciones de Docker, «Pre …», «Post …») ya no "
    "cuentan como despliegue: se ejecutan aunque el paso real se omita con `if:`. Mismo cambio en la "
    "plataforma (`backend/riesgo/services/etiquetado.py`) con pruebas. En el dataset solo cambió el subtipo "
    "de 3 fallos de PROCOLLAB-github/procollab (`posterior_mismo_job` → `antes_del_despliegue`); los y=0 "
    "falsos por un paso «Build» venían de webchuck-ide. (3) **Pull requests**: un fallo antes del despliegue "
    "en un pull request se excluye si, con el YAML de su commit, el despliegue está limitado a push, a una "
    "rama o a una etiqueta (3 filas: ekzhang/sshx y ImCa0/just-laws, pull requests desde ramas de fork "
    "llamadas main/master). (4) **Retención de GitHub**: al re-etiquetar, 75 ejecuciones ya no tenían pasos "
    "(56) o se habían borrado (19); conservan la etiqueta de la regla 7, calculada cuando los pasos existían, "
    "y quedan marcadas (`regla8_sin_datos`). Resultado: 203 → **198 repositorios válidos** (197 en el "
    "entrenamiento, 195 con filas en el tope de 50) y 4.123 ejecuciones (y=1 9,7 %). No se reabrió la "
    "búsqueda (decisión del autor).",
    "- **Regla 9: «deployment» no es el verbo (2026-11-11).** El patrón `\\bdeploy` aceptaba el sustantivo "
    "«deployment(s)». Ahora es `\\bdeploy(?!ments?\\b)`, y «using ssh key» ya no marca como auxiliar el paso "
    "que despliega por SSH (mismo cambio en la plataforma, migración 0011, con pruebas). Búsqueda sin API con el "
    "YAML de cada fila y=0: 21 filas en 2 repositorios con un paso «deployment» como única evidencia y 294 en 16 "
    "con otro paso de despliegue además. Re-etiquetados con la API los 17 repositorios, cambiaron **6 filas** "
    "(y=0 → excluida): wevm/frog (2, `workflow_dispatch` de una rama de CI que solo lee metadatos) y "
    "alliance-genome/agr_curation (4, versiones candidatas que solo se desplegaron a beta). Las 19 de "
    "allcll/allcll-frontend siguen siendo y=0, ahora por el paso de SSH. Las 11 filas de pull request que "
    "quedan se revisaron a mano: todas correctas (ServiceCanada/feedback-cron y ImCa0/just-laws despliegan a "
    "producción en sus PR, desde ramas del mismo repositorio). Dataset: **4.117 ejecuciones** (y=1 401, 9,7 %).",
    "- **Tope por plataforma (criterio 4).** En el dataset final AWS tiene 52 de 198 repositorios (26,3 %), "
    "por debajo del 30 %; la siguiente es Google Cloud con 36 (18,2 %). Había más aprobados de AWS, y la "
    "selección dejó fuera los excedentes con ese motivo.",
]
# Decisiones del autor de la tesis (2026-11-09).
DECISIONES = [
    "**Ampliación de la búsqueda (lote 13): aprobada.** La estrategia 2 se amplió con acciones de despliegue "
    "de plataformas con menos repositorios (flyctl, App Engine, Cloud Functions, Container Apps, Azure Functions, "
    "DigitalOcean App Platform, Heroku, `kubectl set image` y `gcloud run deploy`). No cambia ningún criterio.",
    "**govuk-one-login (txma-audit y txma-ticf-integration): se mantienen excluidos.** Su workflow publica en "
    "las cuentas build/dev de GOV.UK One Login y la promoción a producción la hace AWS CodePipeline, fuera de "
    "GitHub Actions. El despliegue a producción no es observable en los datos, así que no se puede etiquetar "
    "(criterio 2).",
    "**Ejecuciones manuales con entorno indeterminado: se excluyen.** Una ejecución `workflow_dispatch` cuyo "
    "entorno de destino no se puede determinar se excluye (`excluida_entorno_indeterminado`). La regla está en "
    "`informes/fase2_variable_objetivo.md`, sección 4. Caso de origen: dimagi/open-chat-studio (input `dev`/"
    "`prod`), que en sus 100 últimas ejecuciones no tiene ninguna manual.",
    "**Dataset congelado (2026-11-10).** Los 203 repositorios y el tope de 50 ejecuciones por repositorio "
    "quedan fijos. No se hace curva de aprendizaje; `informes/orden_repos_curva.csv` se conserva solo como "
    "registro del orden de selección.",
    "**Corrección de etiquetas antes de entrenar (2026-11-11, opción A).** Se excluyen por el criterio 2 los "
    "repositorios que no despliegan a producción, se corrige el etiquetador (pasos «Build/Pre/Post» de "
    "GitHub, también en la plataforma), se re-etiqueta con la API y se revisan a mano solo los repositorios "
    "de mayor riesgo. **No se reabre la búsqueda**: se acepta el número de repositorios que quede (198, por "
    "debajo del mínimo de 200). Se quita `rama_bot` del modelo v2 (constante en el dataset).",
    "**Variables del modelo v2 (2026-11-10).** Se quita `reejecutado_por_otro` (no se conoce antes del "
    "despliegue). `tiene_pr` (el commit pertenece a un pull request creado antes del despliegue) y "
    "`es_reintento` (intento posterior al primero o el mismo workflow ya terminó una ejecución con ese commit) "
    "se calculan igual en el entrenamiento y en la plataforma. Se añaden el tamaño del cambio (archivos "
    "modificados, líneas añadidas y borradas) y las pruebas fallidas, aproximadas con los checks del mismo "
    "commit que terminaron antes del inicio del despliegue, sin los del propio workflow. **Vulnerabilidades y "
    "cobertura no se pueden obtener** con un token de solo lectura en repositorios de terceros (alertas de "
    "seguridad con permisos de administración; cobertura fuera de GitHub). Detalle en "
    "`informes/fase2_variable_objetivo.md`, sección 7.",
]
# Decisiones que siguen pendientes.
PENDIENTES = [
    "**Excepciones de rama de la regla 7.** Solo Explorer-Consulting/SchoolFeedBackWebAPI: la rama `develop` "
    "despliega al slot «Production» de Azure Functions. Con la regla 7, los demás repos cuya única rama de "
    "despliegue tiene nombre no productivo (dev, develop, staging…) salen del dataset. Si alguno despliega de "
    "verdad a producción desde esa rama, habría que añadirlo a `RAMAS_PRODUCCION_EXCEPCION`.",
    "**Push de la rama** `feature/100-repos-desplegados` (requiere al autor).",
]
# Base de datos de la plataforma (PostgreSQL 16, 2026-11-10).
PLATAFORMA_HECHO = [
    "Respaldo con `pg_dump` (formato custom) antes de cualquier cambio, guardado fuera del repositorio "
    "(`tesis_respaldos/riesgo_despliegue_20261110_171702_antes_0009.dump`).",
    "Migraciones 0009 (etiqueta `excluida_no_produccion`) y 0010 (nuevo patrón de paso de despliegue) "
    "aplicadas. El patrón de los workflows registrados se actualizó en 672 de 672 (todos tenían el patrón por "
    "defecto de la migración 0001; no había patrones personalizados).",
    "Cruce de `riesgo_repositorio` (437) con los 203 repositorios del dataset, por nombre y por `github_id`: "
    "**0 en ambos**, 437 solo en la plataforma y 203 solo en el dataset (los 198 actuales son un subconjunto: "
    "tampoco tienen ninguno en común; detalle en "
    "`informes/cruce_plataforma_dataset_v2.json`). Origen de los 437: 404 del dataset GHALogs v1.1 (alta "
    "2026-10-20), 30 casos de prueba de `datos_prueba/casos_prueba_30.json` (2026-10-27), el repositorio de "
    "demostración y 2 altas manuales sin fuente (Azure-Samples/azure-search-openai-demo y "
    "openfoodfacts/openfoodfacts-server).",
]
# Decisiones del autor sobre la plataforma: se aplican cuando el modelo v2 esté
# entrenado y activo, no antes.
PLATAFORMA_DECISIONES = [
    "**404 repositorios de GHALogs:** `est_registro='I'` (inactivos), sin borrarlos.",
    "**30 casos de prueba:** se marcan como repositorios de prueba y se excluyen de las métricas y los "
    "dashboards, igual que el repositorio de demostración.",
    "**Azure-Samples/azure-search-openai-demo y openfoodfacts/openfoodfacts-server:** `est_registro='I'`.",
    "**Repositorio de demostración** (ErickTerranova2004/demo-despliegue-riesgo): sin cambios.",
    "**Requisito técnico:** el modelo `Repositorio` aún no tiene `est_registro` ni un indicador de prueba "
    "(solo `es_demostracion`). Hará falta una migración que añada `est_registro` (A/I, por defecto 'A') y el "
    "indicador de prueba, y que las vistas que hoy excluyen la demostración excluyan también los de prueba "
    "e ignoren los inactivos. Antes de aplicarla, un respaldo nuevo con `pg_dump`.",
]
VALIDACIONES = [("Regla 6 (semilla 7, antes de corregir)", RAIZ / "informes" / "validacion_etiquetas_regla6.json"),
                ("Regla 7 (semilla 7)", RAIZ / "informes" / "validacion_etiquetas_regla7.json"),
                ("Regla 8 (semilla 2027, nueva muestra aleatoria)",
                 RAIZ / "informes" / "validacion_etiquetas_regla8_aleatoria.json")]
VALIDACION_DIRIGIDA = RAIZ / "informes" / "validacion_etiquetas_regla8_dirigida.json"


def wilson(aciertos, n, z=1.959964):
    """Intervalo de confianza del 95 % de Wilson para una proporción."""
    p = aciertos / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    margen = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return centro - margen, centro + margen


def seccion_validacion():
    """Precisión de las etiquetas medida a mano sobre muestras de 25 y=0 y 25 y=1."""
    l = ["## Validación manual de etiquetas (métrica de calidad del dataset)", "",
         "Muestras aleatorias del dataset final (tope de 50) de 25 ejecuciones y=0 y 25 y=1 (semillas 7 y "
         "2027), más una muestra dirigida a los casos de riesgo (semilla 11). Cada "
         "etiqueta se comprobó a mano con los jobs, los pasos, el log del paso de despliegue (y=0) o del paso "
         "fallido (y=1) y el YAML del workflow. Una etiqueta es correcta si la ejecución es un intento de "
         "despliegue **a producción** y el resultado (completado / no completado) es el que dice la etiqueta. "
         "Los logs de más de 90 días ya no están disponibles; en esos casos se usaron los pasos y el YAML.", "",
         "| Regla | y=0 correctas | y=1 correctas | Precisión total | IC 95 % (Wilson) |",
         "|---|---:|---:|---:|---:|"]
    detalle = []
    for nombre, ruta in VALIDACIONES:
        if not ruta.exists():
            continue
        # Los casos no verificables (ejecución borrada) no cuentan en el denominador.
        casos = [c for c in json.loads(ruta.read_text(encoding="utf-8"))["casos"]
                 if c["correcta"] is not None]
        c0 = sum(c["correcta"] for c in casos if c["y"] == 0)
        c1 = sum(c["correcta"] for c in casos if c["y"] == 1)
        n0 = sum(c["y"] == 0 for c in casos)
        n1 = sum(c["y"] == 1 for c in casos)
        l.append(f"| {nombre} | {c0}/{n0} ({100 * c0 / n0:.0f} %) | {c1}/{n1} ({100 * c1 / n1:.0f} %) | "
                 f"**{c0 + c1}/{n0 + n1} ({100 * (c0 + c1) / (n0 + n1):.0f} %)** | "
                 "{:.1f} – {:.1f} % |".format(*(100 * v for v in wilson(c0 + c1, n0 + n1))))
        errores = Counter(c["motivo"] for c in casos if not c["correcta"])
        if errores:
            detalle += ["", f"Errores con la {nombre[0].lower() + nombre[1:]}:", "",
                        *[f"- {m} ({n})" for m, n in errores.most_common()]]
    if VALIDACION_DIRIGIDA.exists():
        casos = json.loads(VALIDACION_DIRIGIDA.read_text(encoding="utf-8"))["casos"]
        grupos = {"pull_request": "Filas de pull_request (todas las del dataset: 20)",
                  "docker": "Filas con despliegue por acción de Docker (25 de 332)"}
        detalle += ["", "### Muestra dirigida (semilla 11, regla 8)", "",
                    "Busca los dos errores que la muestra aleatoria no detectó: ejecuciones de pull request y "
                    "ejecuciones cuyo job usa una acción de Docker (paso «Build owner/acción@v»). No es "
                    "representativa del dataset: mide la precisión en esos subconjuntos de riesgo.", "",
                    "| Grupo | Correctas | Precisión | IC 95 % (Wilson) |", "|---|---:|---:|---:|"]
        for g, texto in grupos.items():
            sub = [c for c in casos if c["grupo"] == g]
            k = sum(c["correcta"] for c in sub)
            detalle.append(f"| {texto} | {k}/{len(sub)} | {100 * k / len(sub):.0f} % | "
                           "{:.1f} – {:.1f} % |".format(*(100 * v for v in wilson(k, len(sub)))))
        k = sum(c["correcta"] for c in casos)
        detalle.append(f"| **Total** | {k}/{len(casos)} | {100 * k / len(casos):.0f} % | "
                       "{:.1f} – {:.1f} % |".format(*(100 * v for v in wilson(k, len(casos)))))
        errores = Counter(c["motivo"] for c in casos if not c["correcta"])
        detalle += ["", "Errores de la muestra dirigida:", "",
                    *[f"- {m} ({n})" for m, n in errores.most_common()]]
    l += ["", "El intervalo de Wilson se usa porque la proporción está cerca de 1 y la muestra es pequeña: "
          "el intervalo normal (Wald) daría un límite superior por encima del 100 %. Las muestras aleatorias "
          "son estratificadas (25 y=0 y 25 y=1), así que el total pondera igual ambas clases. En la muestra "
          "de la regla 8 un caso no se pudo verificar (la ejecución se borró de GitHub) y no cuenta en el "
          "denominador; contándolo como error, la precisión sería 47/50 (94 %).",
          "", "**Las precisiones miden el dataset tal como estaba al tomar cada muestra.** Los errores "
          "encontrados se corrigieron después (exclusión del repositorio o regla nueva), pero la estimación "
          "no se recalcula como si fueran aciertos: el valor que describe la calidad del dataset final es el "
          "de la última muestra aleatoria (semilla 2027)."]
    l += detalle
    l += ["", "La primera muestra mostró que la regla 6 no resolvía el entorno real de muchas ejecuciones "
          "(decidido por la rama, la release o la salida de otro job) y que la regla de la rama solo se "
          "aplicaba a 9 repositorios. La **regla 7** corrige esas causas sin cambiar los criterios (ver "
          "`informes/fase2_variable_objetivo.md`, sección 4) y la segunda muestra, tomada con la misma semilla "
          "sobre el dataset corregido, mide la calidad del dataset final. Su único error (obby, hosting "
          "estático) se corrigió excluyendo el repositorio. Además, un caso con la y correcta tiene el subtipo "
          "equivocado: en burningmantech/ranger-ims-go el paso que falla despliega el entorno `training` "
          "después de desplegar producción (debería ser `posterior_mismo_job`); el subtipo no se usa como "
          "variable objetivo.", "",
          "Al construir las variables del dataset v2 se encontraron errores que esa muestra no vio "
          "(repositorios de CI que no despliegan y pasos «Build owner/acción@v» contados como despliegue). "
          "La **regla 8** los corrige (ver «Verificaciones») y se validó con una muestra aleatoria nueva "
          "(semilla 2027) y una muestra dirigida (semilla 11). El detalle de cada caso está en "
          "`informes/validacion_etiquetas_regla6.json`, `…regla7.json`, `…regla8_aleatoria.json` y "
          "`…regla8_dirigida.json`."]
    return l


# Repos cuyos fallos tienen una sola causa ajena al pipeline de despliegue.
# Se mantienen en el dataset, marcados, para decidir en el entrenamiento.
ATIPICOS = {
    "cultpodcasts/RedditPodcastPoster":
        "74 de sus 78 ejecuciones fallidas terminaron sin ningún job: el workflow deploy.yml no llegó a "
        "arrancar (archivo de workflow inválido). Con la regla de la fase 2 esas 74 quedan excluidas y no "
        "cuentan como y=1.",
}


# Causa dominante de los fallos (y=1) de los repos con una sola clase en el
# dataset final: paso fallido de cada ejecución y final del log de una
# muestra (2026-11-08). «propuesta» = 80 % o más de sus y=1 con la misma causa.
CAUSAS_UNA_CLASE = {
    "google/neuroglancer": ("Fallos de CI variados: build de la documentación (10), npm ci (10), pruebas E2E del "
                            "proyecto de ejemplo (4) y errores de tipos de TypeScript; ninguna causa supera el "
                            "32 %.", False),
    "JabRef/JabRefOnline": ("El despliegue a Azure falla siempre ('Deployment failed with exit code 1') en test, "
                            "staging y producción: 43 de 49 y=1 (88 %), sin ningún éxito en 99 ejecuciones.", True),
    "liguobao/HouseSearch": ("Dos causas persistentes: clave SSH del despliegue inválida ('Error loading key: "
                             "invalid format', 23 de 40, 58 %) y build de TypeScript roto (16).", False),
    "mobs-lab/epistorm-dashboard": ("Falla siempre el job deploy-demo (despliegue a una App Engine de "
                                    "demostración): 31 de 31 y=1 (100 %); los logs ya no están disponibles.", True),
    "elsa-hanke/elsa-backend": ("Pruebas de integración externas en CodeBuild (6 de 11, 55 %), build (4) y "
                                "test (1).", False),
    "mc-wiki/mcw-calc": ("Comprobación de tipos (7 de 10, 70 %) y lint (3).", False),
}

# Excluidos del entrenamiento (siguen en la lista con su motivo).
EXCLUIR_ENTRENAMIENTO = {
    "cultpodcasts/RedditPodcastPoster":
        "No aporta ninguna ejecución válida al dataset final: sus 50 ejecuciones más recientes no tienen jobs.",
}


def resumen_etiquetas(filas):
    """(y=0, y=1, excluidas, despliegue_completado).

    Criterio 2 (verificación final): al menos un despliegue completado (y=0)
    en el historial revisado. Un paso de despliegue que se ejecuta pero falla
    siempre no basta (caso JabRef/JabRefOnline: 0 de 99)."""
    conteo = Counter(f["y"] for f in filas)
    return conteo[0], conteo[1], conteo[None], conteo[0] > 0


def seleccionar(validos):
    """Aplica máximo por organización y máximo 30 % por plataforma.

    Prioridad: ambas clases y 10 o más ejecuciones etiquetadas primero."""
    def prioridad(v):
        return (not (v["y0_tope"] and v["y1_tope"]), not (v["y0_tope"] + v["y1_tope"] >= 10),
                -(v["y0_tope"] + v["y1_tope"]), v["repositorio"].lower())
    ordenados = sorted(validos, key=prioridad)
    elegidos, fuera = [], []
    por_org = Counter()
    for v in ordenados:
        if por_org[v["organizacion"]] >= MAX_POR_ORGANIZACION:
            fuera.append((v, f"más de {MAX_POR_ORGANIZACION} repositorios de la organización {v['organizacion']}"))
            continue
        por_org[v["organizacion"]] += 1
        elegidos.append(v)
    elegidos = elegidos[:META]
    # Ninguna plataforma por encima del 30 % del total final.
    while True:
        total = len(elegidos)
        por_plat = Counter(v["proveedor"] for v in elegidos)
        exceso = [pl for pl, n in por_plat.items() if n > MAX_PROPORCION_PLATAFORMA * total]
        if not exceso:
            break
        pl = exceso[0]
        quitar = [v for v in elegidos if v["proveedor"] == pl][-1]  # el de menor prioridad
        elegidos.remove(quitar)
        fuera.append((quitar, f"la plataforma {pl} superaría el 30 % del total"))
    return elegidos, fuera


def informe(args):
    perfiles = leer(PERFILES, {})
    revision = leer(REVISION, {})
    etiquetas = leer(ETIQUETAS, {})
    excluidos_lista = []
    validos = []
    for repo, p in sorted(perfiles.items(), key=lambda x: x[0].lower()):
        if p["excluido"]:
            if p.get("ejecuciones_6m", 0) >= MIN_EJECUCIONES or "Tesis" in p["excluido"]:
                excluidos_lista.append((repo, p["excluido"]))
            continue
        decision = revision.get(repo)
        if not decision:
            continue
        if decision["decision"] != "valido":
            excluidos_lista.append((repo, decision["motivo"]))
            continue
        if repo not in etiquetas:
            continue
        y0, y1, excl, ejecuto = resumen_etiquetas(etiquetas[repo])
        if not ejecuto:
            excluidos_lista.append((repo, f"ningún despliegue completado (y=0) en las ejecuciones revisadas "
                                          f"(hasta {RUNS_ETIQUETAR})" + (
                                              "; sus despliegues completados eran ejecuciones manuales "
                                              "(workflow_dispatch) con entorno de destino indeterminado"
                                              if any(f.get("y_previa") == 0 for f in etiquetas[repo]) else "")))
            continue
        # Dataset final: las TOPE_DATASET ejecuciones más recientes (el
        # historial está ordenado de la más reciente a la más antigua).
        y0_tope, y1_tope, excl_tope, _ = resumen_etiquetas(etiquetas[repo][:TOPE_DATASET])
        validos.append({"repositorio": repo, "organizacion": repo.split("/")[0], "ruta": p["ruta"],
                        "proveedor": p["paso"]["proveedor"], "servicio": p["paso"]["servicio"],
                        "ejecuciones_6m": p["ejecuciones_6m"], "y0": y0, "y1": y1, "excluidas": excl,
                        "y0_tope": y0_tope, "y1_tope": y1_tope, "excluidas_tope": excl_tope,
                        "sin_jobs": sum(f["etiqueta"] == "excluida_sin_jobs" for f in etiquetas[repo]),
                        "sin_jobs_tope": sum(f["etiqueta"] == "excluida_sin_jobs"
                                             for f in etiquetas[repo][:TOPE_DATASET]),
                        "jobs_conocidos": all("n_jobs" in f for f in etiquetas[repo] if f["y"] == 1),
                        "atipico": ATIPICOS.get(repo, ""), "evidencia": decision["motivo"]})
        v = validos[-1]
        v["excluir_entrenamiento"] = EXCLUIR_ENTRENAMIENTO.get(repo, "")
        if not (v["y0_tope"] and v["y1_tope"]):
            causa, propuesta = CAUSAS_UNA_CLASE.get(repo, ("", False))
            clase = ("ninguna ejecución válida" if not (v["y0_tope"] or v["y1_tope"]) else
                     f"solo y=0 ({v['y0_tope']})" if v["y0_tope"] else f"solo y=1 ({v['y1_tope']})")
            v["una_clase"] = clase
            v["propuesta_excluir"] = propuesta
            v["atipico"] = " ".join(filter(None, [v["atipico"], f"Una sola clase en el dataset final: {clase}.",
                                                  f"Causa dominante de los fallos: {causa}" if causa else ""]))
        if v["sin_jobs"] and v["y0_tope"] + v["y1_tope"] < MIN_VALIDAS_TRAS_SIN_JOBS:
            v["atipico"] = " ".join(filter(None, [v["atipico"], (
                f"Tras excluir sus {v['sin_jobs']} ejecuciones sin jobs le quedan "
                f"{v['y0_tope'] + v['y1_tope']} válidas en el dataset final (tope de {TOPE_DATASET}; "
                f"y=0 {v['y0_tope']}, y=1 {v['y1_tope']}) y {v['y0'] + v['y1']} en el historial completo: "
                f"menos de {MIN_VALIDAS_TRAS_SIN_JOBS}.")]))
    elegidos, fuera = seleccionar(validos)
    excluidos_lista += [(v["repositorio"], m) for v, m in fuera]
    escribir_informe(elegidos, excluidos_lista, perfiles)
    escribir_orden([v for v in elegidos if not v["excluir_entrenamiento"]])
    print(f"Válidos tras la selección: {len(elegidos)} · excluidos con motivo: {len(excluidos_lista)}")


def escribir_orden(elegidos):
    nombres = sorted(v["repositorio"] for v in elegidos)
    random.Random(SEMILLA).shuffle(nombres)
    plataforma = {v["repositorio"]: v["proveedor"] for v in elegidos}
    with open(ORDEN, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["orden", "repositorio", "plataforma", "entra_desde_n"])
        for i, nombre in enumerate(nombres, 1):
            w.writerow([i, nombre, plataforma[nombre], next(n for n in (50, 100, 150, 200, 250) if i <= n)
                        if i <= 250 else ""])


LOTE_INICIO_E2 = 8  # primer lote revisado con la estrategia 2
# Con ejecuciones sin jobs y menos de estas válidas en el dataset final, el
# repositorio se marca como atípico.
MIN_VALIDAS_TRAS_SIN_JOBS = 5


def tabla_lotes(perfiles):
    """Tasa de válidos por lote de revisión manual y origen principal."""
    revision = leer(REVISION, {})
    lotes = defaultdict(list)
    for repo, d in revision.items():
        lotes[d.get("lote", 0)].append((repo, d["decision"]))
    filas = ["| Lote | Estrategia | Válidos / revisados | Tasa | Origen principal |",
             "|---:|---|---:|---:|---|"]
    totales = {1: [0, 0], 2: [0, 0]}
    for lote in sorted(lotes):
        decisiones = lotes[lote]
        validos = sum(d == "valido" for _, d in decisiones)
        estrategia = 2 if lote >= LOTE_INICIO_E2 else 1
        totales[estrategia][0] += validos
        totales[estrategia][1] += len(decisiones)
        origen = Counter(("búsquedas anteriores" if perfiles.get(r, {}).get("consulta") == "búsqueda anterior"
                          else perfiles.get(r, {}).get("paso", {}).get("proveedor", "—"))
                         for r, _ in decisiones)
        principal = ", ".join(f"{o} ({n})" for o, n in origen.most_common(3))
        filas.append(f"| {lote} | {estrategia} | {validos} / {len(decisiones)} | "
                     f"{100 * validos / len(decisiones):.0f} % | {principal} |")
    for estrategia, (v, n) in totales.items():
        if n:
            filas.append(f"| **Total E{estrategia}** | {estrategia} | **{v} / {n}** | **{100 * v / n:.1f} %** | |")
    return filas


def escribir_informe(elegidos, excluidos_lista, perfiles):
    def proporcion(y0, y1):
        n = y0 + y1
        return (f"{n} → y=0 (completado) {y0} ({100 * y0 / max(n, 1):.1f} %) · "
                f"y=1 (no completado) {y1} ({100 * y1 / max(n, 1):.1f} %)")

    total_y0 = sum(v["y0"] for v in elegidos)
    total_y1 = sum(v["y1"] for v in elegidos)
    tope_y0 = sum(v["y0_tope"] for v in elegidos)
    tope_y1 = sum(v["y1_tope"] for v in elegidos)
    atipicos = [v for v in elegidos if v["atipico"]]
    entrenamiento = [v for v in elegidos if not v["excluir_entrenamiento"]]
    excluidos_entrenamiento = [v for v in elegidos if v["excluir_entrenamiento"]]
    propuestos = [v for v in elegidos if v.get("propuesta_excluir") and not v["excluir_entrenamiento"]]
    sin_jobs = sum(v["sin_jobs"] for v in elegidos)
    sin_jobs_tope = sum(v["sin_jobs_tope"] for v in elegidos)
    con_jobs = sum(1 for v in elegidos if v["jobs_conocidos"])
    repos_sin_jobs = sorted((v for v in elegidos if v["sin_jobs"]), key=lambda v: -v["sin_jobs"])
    estado = ("Meta alcanzada" if len(elegidos) >= META else
              "Mínimo alcanzado" if len(elegidos) >= MINIMO else "No se alcanza el mínimo de 200")
    por_plat = Counter(v["proveedor"] for v in elegidos)
    por_org = Counter(v["organizacion"] for v in elegidos)
    l = [f"# Filtrado de repositorios reales con despliegues reales", "",
         f"Generado el {date.today().isoformat()} por "
         "[`scripts/filtrar_repos_reales.py`](../scripts/filtrar_repos_reales.py) con la API de GitHub "
         "(solo lectura). **No se ha cargado nada en la plataforma ni en su base de datos.**", "",
         f"**{estado}: {len(elegidos)} repositorios válidos** (meta {META}, mínimo {MINIMO}).", "",
         "## Totales", "",
         f"- Repositorios: {len(elegidos)}",
         f"- Ejecuciones terminadas en los últimos 6 meses (desde {DESDE}): "
         f"{sum(v['ejecuciones_6m'] for v in elegidos)}",
         f"- **Antes del tope** (hasta {RUNS_ETIQUETAR} ejecuciones más recientes por repositorio, regla de la "
         f"fase 2; criterio 2): {proporcion(total_y0, total_y1)}. Excluidas por la regla: "
         f"{sum(v['excluidas'] for v in elegidos)}.",
         f"- **Dataset final, tope de {TOPE_DATASET} ejecuciones más recientes por repositorio** (para que ningún "
         f"repo domine una clase): {proporcion(tope_y0, tope_y1)}. Excluidas por la regla: "
         f"{sum(v['excluidas_tope'] for v in elegidos)}.",
         f"- Repositorios con ambas clases en el dataset final: "
         f"{sum(1 for v in elegidos if v['y0_tope'] and v['y1_tope'])}; con 10 o más ejecuciones etiquetadas: "
         f"{sum(1 for v in elegidos if v['y0_tope'] + v['y1_tope'] >= 10)}.",
         f"- Ejecuciones excluidas por no tener ningún job (no llegaron a arrancar; no son un intento de "
         f"despliegue): {sin_jobs} antes del tope y {sin_jobs_tope} con el tope, en {len(repos_sin_jobs)} "
         f"repositorios (número de jobs verificado en {con_jobs} de {len(elegidos)} repositorios). Las "
         "proporciones anteriores ya las descuentan.",
         f"- Repositorios marcados como atípicos: {len(atipicos)} (ver sección «Atípicos»).",
         f"- **Dataset de entrenamiento** (repositorios excluidos del entrenamiento: "
         f"{len(excluidos_entrenamiento)}): {len(entrenamiento)} repositorios; "
         f"{proporcion(sum(v['y0_tope'] for v in entrenamiento), sum(v['y1_tope'] for v in entrenamiento))}.", "",
         "## Ejecuciones excluidas por no tener ningún job", "",
         "Según `informes/fase2_variable_objetivo.md` (sección 4, «Excluidas»), una ejecución que termina sin "
         "ningún job (startup_failure, YAML inválido, permisos del workflow...) no es un intento de despliegue: "
         "no cuenta como y=1 y se excluye del dataset.", "",
         "| Repositorio | Excluidas (historial) | Excluidas (tope de 50) |", "|---|---:|---:|",
         *([f"| {v['repositorio']} | {v['sin_jobs']} | {v['sin_jobs_tope']} |" for v in repos_sin_jobs]
           or ["| — | 0 | 0 |"]), "",
         "## Criterios aplicados", "",
         "1. **Aplicación real en uso** (revisión manual de descripción, topics, README, web, contribuidores e "
         "historial): se excluyen tutoriales, cursos, tareas, plantillas, demos, proyectos de práctica o "
         "portafolio, sandbox y proyectos de tesis o académicos (toda la organización Tesis-2026).",
         "2. **Despliegue real** según `informes/fase2_variable_objetivo.md`: el workflow tiene un paso que "
         "despliega a un entorno de aplicación y ese paso se ejecutó al menos una vez (API de jobs). Se excluyen "
         "GitHub Pages, clústeres efímeros (kind, minikube, k3d, localstack), workflows que solo despliegan "
         "previews de pull requests y repos donde el paso nunca se ejecutó.",
         f"3. **Actividad genuina**: al menos 20 commits y 60 días de historial; se excluyen workflows con más de "
         "la mitad de ejecuciones programadas o repetidas sobre el mismo commit y repos con más del 80 % de "
         "commits automáticos.",
         f"4. **Diversidad**: máximo {MAX_POR_ORGANIZACION} repositorios por organización o autor y ninguna "
         "plataforma (proveedor) por encima del 30 % del total.",
         f"5. **Volumen**: al menos {MIN_EJECUCIONES} ejecuciones terminadas en 6 meses; se priorizan los repos "
         "con ambas clases (y=0 e y=1) y con 10 o más ejecuciones etiquetadas.",
         "- Se omiten los repositorios ya registrados en la plataforma o del dataset de entrenamiento anterior "
         "(GHALogs), para que el conjunto sea nuevo.", "",
         "## Estrategia de búsqueda y tasa de válidos por lote", "",
         f"- **Estrategia 1 (lotes 1 a {LOTE_INICIO_E2 - 1}).** Búsqueda de código de {len(MARCADORES)} "
         "acciones o comandos de despliegue (Cloud Run, App Engine, ECS, Lambda, Azure, Kubernetes, Fly.io, "
         "Railway, Render, Heroku, Vercel, Cloudflare, servidores propios…), perfilado alternando plataformas y "
         "revisión manual priorizada por señales de uso real. La tasa bajó en los lotes que vinieron de páginas "
         "profundas de las búsquedas y de plataformas como Railway y Render, donde predominan proyectos "
         "personales, de portafolio o de cursos.",
         f"- **Estrategia 2 (desde el lote {LOTE_INICIO_E2}).** Solo acciones de despliegue a producción "
         "(amazon-ecs-deploy-task-definition, deploy-cloudrun, azure/webapps-deploy, azure/k8s-deploy, "
         "`helm upgrade`, appleboy/ssh-action y Ansible), buscadas también junto a «production» y "
         "«environment»; Railway y Render se dejan de buscar. **Prefiltro antes de perfilar** (API GraphQL, "
         f"sin gastar cuota de perfilado): dueño de tipo Organization, más de {MIN_DIAS_ACTIVIDAD} días entre la "
         f"creación y el último push y al menos {MIN_CONTRIBUIDORES} contribuidores. Se perfilan primero los "
         "repositorios con más deployments registrados en entornos de producción (API de Deployments). Así "
         "entran sistemas de gobiernos, universidades, ONG y empresas, con el máximo de "
         f"{MAX_POR_ORGANIZACION} por organización. La revisión manual (criterio 1) se mantiene igual.",
         "- La revisión salta perfiles de plataformas que ya alcanzaron el 30 % del mínimo de 200 y de "
         f"organizaciones con {MAX_POR_ORGANIZACION} aprobados, y empieza por las plataformas con menos "
         "repositorios.", "",
         *tabla_lotes(perfiles), "",
         "## Verificaciones de la regla de etiquetado", "", *VERIFICACIONES, "",
         *seccion_validacion(), "",
         "## Decisiones del autor (2026-11-09)", "",
         *[f"{i}. {t}" for i, t in enumerate(DECISIONES, 1)], "",
         "## Base de datos de la plataforma (2026-11-10)", "",
         *[f"- {t}" for t in PLATAFORMA_HECHO], "",
         "### Decisiones del autor sobre la plataforma (se aplican cuando v2 esté entrenado y activo)", "",
         *[f"{i}. {t}" for i, t in enumerate(PLATAFORMA_DECISIONES, 1)], "",
         "## Decisiones pendientes", "",
         *[f"{i}. {t}" for i, t in enumerate(PENDIENTES, 1)], "",
         "## Decisión metodológica: separación por repositorio", "",
         "- La separación entrenamiento/prueba es **por repositorio**: todas las ejecuciones de un mismo "
         "repositorio quedan en el mismo conjunto. Así el modelo se evalúa con proyectos que no vio y se evita "
         "la fuga de información entre ejecuciones del mismo repo (mismo historial, mismos patrones de fallo).",
         f"- Curva de aprendizaje (pendiente de ejecutar): [orden_repos_curva.csv](orden_repos_curva.csv) asigna "
         f"a cada repositorio un orden aleatorio reproducible (semilla {SEMILLA}). Los subconjuntos de 50, 100, "
         "150, 200 y 250 repos son los primeros N de ese orden (columna `entra_desde_n`), de modo que cada "
         "subconjunto contiene al anterior.", "",
         "## Conteo por plataforma", "", "| Plataforma | Repos | % |", "|---|---:|---:|",
         *[f"| {pl} | {n} | {100 * n / max(len(elegidos), 1):.1f} |" for pl, n in por_plat.most_common()], "",
         "## Conteo por organización (más de un repositorio)", "", "| Organización | Repos |", "|---|---:|",
         *[f"| {o} | {n} |" for o, n in por_org.most_common() if n > 1],
         f"\nOrganizaciones distintas: {len(por_org)}.", "",
         "## Atípicos", "",
         "Se mantienen en la lista, marcados con ⚠, cuando: (a) sus fallos tienen una sola causa ajena al "
         f"pipeline; (b) tras excluir las ejecuciones sin jobs les quedan menos de {MIN_VALIDAS_TRAS_SIN_JOBS} "
         "ejecuciones válidas en el dataset final; o (c) en el dataset final tienen una sola clase (solo y=0 o "
         "solo y=1). Para los que solo tienen y=1 se indica la causa dominante de sus fallos y, si el 80 % o más "
         "de sus y=1 tienen la misma causa (workflow roto, secreto expirado, error de configuración), se propone "
         "excluirlos del entrenamiento.", "",
         "### Excluidos del entrenamiento", "",
         *([f"- ⛔ **{v['repositorio']}**: {v['excluir_entrenamiento']}" for v in excluidos_entrenamiento]
           or ["- Ninguno."]), "",
         "### Propuestos para excluir del entrenamiento (pendiente de aprobación)", "",
         *([f"- **{v['repositorio']}**: {CAUSAS_UNA_CLASE[v['repositorio']][0]}" for v in propuestos]
           or ["- Ninguno."]), "",
         "### Todos los atípicos", "",
         *([f"- **{v['repositorio']}**: {v['atipico']}" for v in atipicos] or ["- Ninguno."]), "",
         "## Lista final", "",
         f"Las columnas y=0 / y=1 y % fallos corresponden al dataset final (tope de {TOPE_DATASET} ejecuciones); "
         f"entre paréntesis, con el historial completo (hasta {RUNS_ETIQUETAR}).", "",
         "| # | Repositorio | Organización | Plataforma | Ejec. 6 meses | y=0 / y=1 | % fallos | Evidencia |",
         "|---|---|---|---|---:|---|---:|---|"]
    for i, v in enumerate(sorted(elegidos, key=lambda x: x["repositorio"].lower()), 1):
        n = v["y0_tope"] + v["y1_tope"]
        marca = (" ⛔ excluido del entrenamiento" if v["excluir_entrenamiento"] else
                 " ⚠ atípico" if v["atipico"] else "")
        l.append(f"| {i} | [{v['repositorio']}](https://github.com/{v['repositorio']}/blob/HEAD/{v['ruta']}){marca} | "
                 f"{v['organizacion']} | {v['proveedor']} · {v['servicio']} | {v['ejecuciones_6m']} | "
                 f"{v['y0_tope']} / {v['y1_tope']} ({v['y0']} / {v['y1']}) | {100 * v['y1_tope'] / max(n, 1):.0f} | "
                 f"{v['evidencia'].replace('|', '/')} |")
    motivos = Counter(m for _, m in excluidos_lista)
    l += ["", "## Excluidos", "",
          f"Total con motivo registrado: {len(excluidos_lista)} (no se listan los descartados solo por tener "
          f"menos de {MIN_EJECUCIONES} ejecuciones en 6 meses: "
          f"{sum(1 for p in perfiles.values() if (p['excluido'] or '').startswith('menos de'))}).", "",
          "### Por motivo", "", *[f"- {m}: {n}" for m, n in motivos.most_common()], "",
          "### Detalle", "", "| Repositorio | Motivo |", "|---|---|",
          *[f"| {r} | {m.replace('|', '/')} |" for r, m in sorted(excluidos_lista, key=lambda x: x[0].lower())]]
    INFORME.write_text("\n".join(l) + "\n", encoding="utf-8")


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("etapa", choices=["candidatos", "prefiltrar", "perfilar", "revisar", "etiquetar", "jobs",
                                     "produccion", "dispatch", "regla7", "informe"])
    a.add_argument("--max", type=int, default=0, help="perfilar como máximo N candidatos nuevos")
    a.add_argument("--lote", type=int, default=1)
    a.add_argument("--repos", nargs="*", default=[], help="regla7: solo estos repositorios")
    a.add_argument("--previos", nargs="*", default=[], help="otros JSON de búsquedas anteriores")
    a.add_argument("--estrategia2", action="store_true", help="candidatos: consultas de la estrategia 2")
    a.add_argument("--prefiltrados", action="store_true", help="perfilar solo los que pasan el prefiltro")
    args = a.parse_args()
    {"candidatos": candidatos, "perfilar": perfilar, "revisar": revisar, "etiquetar": etiquetar,
     "jobs": contar_jobs, "informe": informe, "prefiltrar": prefiltrar,
     "produccion": produccion, "dispatch": dispatch, "regla7": regla7}[args.etapa](args)
