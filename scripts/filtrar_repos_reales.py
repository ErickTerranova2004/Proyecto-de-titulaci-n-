"""Reúne y filtra repositorios REALES con despliegues reales (200-250).

Etapas (cada una reanudable; los datos de GitHub se guardan en la caché):

  python scripts/filtrar_repos_reales.py candidatos   # búsqueda de código → candidatos
  python scripts/filtrar_repos_reales.py perfilar     # actividad, YAML, repo, README, commits
  python scripts/filtrar_repos_reales.py revisar --lote 1   # perfiles para la revisión manual
  python scripts/filtrar_repos_reales.py etiquetar    # jobs de las ejecuciones → y (fase 2)
  python scripts/filtrar_repos_reales.py jobs         # nº de jobs de las y=1 antiguas; sin jobs → excluida
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
DESDE = (date.today() - timedelta(days=182)).isoformat()
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
]
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
    tmp.replace(ruta)


def etiquetador():
    """Regla de la fase 2 tal como la aplica la plataforma."""
    ruta = RAIZ / "backend" / "riesgo" / "services" / "etiquetado.py"
    spec = importlib.util.spec_from_file_location("etiquetado", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    texto = (RAIZ / "backend" / "riesgo" / "models.py").read_text(encoding="utf-8")
    patron = "".join(re.findall(r'r"([^"]*)"', texto.split("PATRON_DESPLIEGUE = (", 1)[1].split(")\n", 1)[0]))
    return modulo.etiquetar_ejecucion, patron


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
    from riesgo.models import Repositorio
    nombres |= {n.lower() for n in Repositorio.objects.values_list("nombre_completo", flat=True)}
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
    for consulta, _, _, _ in MARCADORES:
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


def pendientes_de_revision():
    perfiles = leer(PERFILES, {})
    revision = leer(REVISION, {})
    pendientes = [p for p in perfiles.values() if not p["excluido"] and p["repositorio"] not in revision]
    # Más señales primero y, a igualdad, alternando plataformas.
    vistos = Counter()
    clave = []
    for p in sorted(pendientes, key=lambda p: -senales(p)):
        vistos[p["paso"]["proveedor"]] += 1
        clave.append((-senales(p), vistos[p["paso"]["proveedor"]], p["repositorio"].lower(), p))
    return [c[-1] for c in sorted(clave, key=lambda c: c[:3])]


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
def etiquetar_fila(run, jobs, etiquetar_ejecucion, patron):
    """Etiqueta una ejecución con la regla de la fase 2 de la plataforma
    (incluye excluir las que terminaron sin ningún job)."""
    e = etiquetar_ejecucion(run["conclusion"], jobs, patron)
    y = {"despliegue_completado": 0, "despliegue_no_completado": 1}.get(e["etiqueta"])
    return {"run": run["id"], "etiqueta": e["etiqueta"], "subtipo": e["subtipo_etiqueta"],
            "despliegue_ejecutado": e["despliegue_ejecutado"], "y": y, "n_jobs": len(jobs)}


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


def etiquetar(args):
    gh = GitHub()
    etiquetar_ejecucion, patron = etiquetador()
    perfiles = leer(PERFILES, {})
    revision = leer(REVISION, {})
    etiquetas = leer(ETIQUETAS, {})
    historial = leer(HISTORIAL, {})
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
        previas = {f["run"]: f for f in etiquetas.get(repo, [])}
        if len(previas) >= len(historial[repo]) and all(r["id"] in previas for r in historial[repo]):
            continue
        filas = []
        for run in historial[repo]:
            if run["id"] in previas:
                filas.append(previas[run["id"]])
                continue
            if run["conclusion"] not in ("success", "failure"):
                filas.append({"run": run["id"], "etiqueta": "excluida_otro_resultado", "y": None})
                continue
            jobs = (gh.get(f"/repos/{repo}/actions/runs/{run['id']}/attempts/{run['intento']}/jobs",
                           {"per_page": 100}) or {}).get("jobs", [])
            filas.append(etiquetar_fila(run, jobs, etiquetar_ejecucion, patron))
        etiquetas[repo] = filas
        guardar(ETIQUETAS, etiquetas)
        conteo = Counter(f["y"] for f in filas)
        print(f"{i}/{len(aprobados)} {repo}: y=0 {conteo[0]} · y=1 {conteo[1]} · excluidas {conteo[None]}",
              flush=True)


# ------------------------------------------------------------------ informe
# Repos cuyos fallos tienen una sola causa ajena al pipeline de despliegue.
# Se mantienen en el dataset, marcados, para decidir en el entrenamiento.
ATIPICOS = {
    "cultpodcasts/RedditPodcastPoster":
        "74 de sus 78 ejecuciones fallidas terminaron sin ningún job: el workflow deploy.yml no llegó a "
        "arrancar (archivo de workflow inválido). Con la regla de la fase 2 esas 74 quedan excluidas y no "
        "cuentan como y=1.",
}


def resumen_etiquetas(filas):
    conteo = Counter(f["y"] for f in filas)
    ejecuto = any(f.get("despliegue_ejecutado") or f.get("subtipo") == "en_paso_de_despliegue" for f in filas)
    return conteo[0], conteo[1], conteo[None], ejecuto


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
            excluidos_lista.append((repo, "el paso de despliegue nunca se ejecutó en las ejecuciones revisadas"))
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
    elegidos, fuera = seleccionar(validos)
    excluidos_lista += [(v["repositorio"], m) for v, m in fuera]
    escribir_informe(elegidos, excluidos_lista, perfiles)
    escribir_orden(elegidos)
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
    sin_jobs = sum(v["sin_jobs"] for v in elegidos)
    sin_jobs_tope = sum(v["sin_jobs_tope"] for v in elegidos)
    con_jobs = sum(1 for v in elegidos if v["jobs_conocidos"])
    repos_sin_jobs = sorted((v for v in elegidos if v["sin_jobs"]), key=lambda v: -v["sin_jobs"])
    estado = ("Meta alcanzada" if len(elegidos) >= META else
              "Mínimo alcanzado" if len(elegidos) >= MINIMO else "**No se alcanza el mínimo de 200**")
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
         f"- Repositorios marcados como atípicos: {len(atipicos)} (ver sección «Atípicos»).", "",
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
         "Se mantienen en la lista, marcados con ⚠, porque sus fallos tienen una sola causa ajena al pipeline. "
         "Conviene decidir en el entrenamiento si se excluyen o se ponderan.", "",
         *([f"- **{v['repositorio']}**: {v['atipico']}" for v in atipicos] or ["- Ninguno."]), "",
         "## Lista final", "",
         f"Las columnas y=0 / y=1 y % fallos corresponden al dataset final (tope de {TOPE_DATASET} ejecuciones); "
         f"entre paréntesis, con el historial completo (hasta {RUNS_ETIQUETAR}).", "",
         "| # | Repositorio | Organización | Plataforma | Ejec. 6 meses | y=0 / y=1 | % fallos | Evidencia |",
         "|---|---|---|---|---:|---|---:|---|"]
    for i, v in enumerate(sorted(elegidos, key=lambda x: x["repositorio"].lower()), 1):
        n = v["y0_tope"] + v["y1_tope"]
        marca = " ⚠ atípico" if v["atipico"] else ""
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
    a.add_argument("etapa", choices=["candidatos", "perfilar", "revisar", "etiquetar", "jobs", "informe"])
    a.add_argument("--max", type=int, default=0, help="perfilar como máximo N candidatos nuevos")
    a.add_argument("--lote", type=int, default=1)
    a.add_argument("--previos", nargs="*", default=[], help="otros JSON de búsquedas anteriores")
    args = a.parse_args()
    {"candidatos": candidatos, "perfilar": perfilar, "revisar": revisar, "etiquetar": etiquetar,
     "jobs": contar_jobs, "informe": informe}[args.etapa](args)
