"""Análisis interactivos reales repartidos en el tiempo, por la API de la
plataforma (como lo haría un desarrollador desde «Nuevo análisis»).

    scripts\\analisis_programados.cmd                       # 40 hasta las 11:00
    scripts\\analisis_programados.cmd --cantidad 20 --hasta 10:30

- Solo workflows con commits pendientes de desplegar (los calcula la tarea
  programada del lote), de repositorios reales: nunca de demostración ni de
  prueba. Primero los que desplegaron más recientemente (es más probable
  que vuelvan a desplegar pronto y el resultado real se enlace solo).
- En el momento de cada análisis consulta en GitHub la cabeza actual de la
  rama principal y analiza ese SHA. No repite SHAs. Si el commit ya se
  desplegó (aviso 409 de la plataforma) pasa al siguiente candidato.
- No registra decisiones del líder técnico.
- Si Claude falla, la plataforma redacta el análisis por reglas y el script
  sigue (en la consola se ve «reglas» en la columna IA).
- Consola y log en logs\\analisis_programados_AAAAMMDD_HHMMSS.log.

La contraseña se pide al empezar (no se muestra) o se toma de la variable
de entorno PLATAFORMA_CLAVE. El token de GitHub se lee de backend\\.env sin
mostrarlo. Requiere el backend en marcha (http://127.0.0.1:8000).
"""

import argparse
import getpass
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
GITHUB = "https://api.github.com"


def leer_env(nombre):
    """Valor de backend\\.env (nunca se imprime)."""
    if os.environ.get(nombre):
        return os.environ[nombre]
    archivo = RAIZ / "backend" / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            clave, _, valor = linea.partition("=")
            if clave.strip() == nombre:
                return valor.strip()
    return ""


class Registro:
    def __init__(self, ruta):
        ruta.parent.mkdir(exist_ok=True)
        self.archivo = open(ruta, "a", encoding="utf-8")
        self.ruta = ruta

    def __call__(self, texto=""):
        print(texto, flush=True)
        self.archivo.write(texto + "\n")
        self.archivo.flush()


def candidatos(repositorios):
    """Workflows con commits pendientes de repos reales, los que desplegaron
    más recientemente primero."""
    lista = []
    for repo in repositorios:
        if repo.get("es_demostracion") or repo.get("es_prueba"):
            continue
        for w in repo["workflows"]:
            p = w.get("pendientes") or {}
            if (p.get("commits") or 0) > 0 and p.get("rama_principal"):
                lista.append({"repositorio": repo["nombre_completo"],
                              "workflow_path": w["path"], "pendientes": p})
    lista.sort(key=lambda c: c["pendientes"].get("ultimo_despliegue_en") or "",
               reverse=True)
    return lista


def horario(inicio, fin, cantidad):
    """Momentos de cada análisis, repartidos por igual entre inicio y fin."""
    paso = (fin - inicio) / cantidad
    return [inicio + paso * i for i in range(cantidad)], paso


def esperar_hasta(momento):
    while True:
        falta = (momento - datetime.now()).total_seconds()
        if falta <= 0:
            return
        time.sleep(min(falta, 30))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cantidad", type=int, default=40)
    parser.add_argument("--hasta", default="11:00", help="Hora local HH:MM de fin.")
    parser.add_argument("--usuario", default="revision_dev")
    parser.add_argument("--api", default="http://127.0.0.1:8000/api")
    args = parser.parse_args()

    inicio = datetime.now()
    horas, minutos = map(int, args.hasta.split(":"))
    fin = inicio.replace(hour=horas, minute=minutos, second=0, microsecond=0)
    if fin <= inicio:
        sys.exit(f"La hora de fin ({args.hasta}) ya pasó.")

    log = Registro(RAIZ / "logs" / f"analisis_programados_{inicio:%Y%m%d_%H%M%S}.log")
    sesion = requests.Session()
    try:
        sesion.get(f"{args.api}/yo/", timeout=10)
    except requests.RequestException:
        sys.exit("El backend no responde en "
                 f"{args.api}. Arránquelo antes (ver docs/estado_proyecto.md).")
    clave = os.environ.get("PLATAFORMA_CLAVE") or getpass.getpass(
        f"Contraseña de {args.usuario}: ")
    r = sesion.post(f"{args.api}/auth/token/",
                    json={"username": args.usuario, "password": clave}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"No se pudo iniciar sesión como {args.usuario} ({r.status_code}).")
    sesion.headers["Authorization"] = f"Token {r.json()['token']}"

    github = requests.Session()
    token = leer_env("GITHUB_TOKEN")
    if token:
        github.headers["Authorization"] = f"Bearer {token}"
    github.headers["Accept"] = "application/vnd.github+json"

    lista = candidatos(sesion.get(f"{args.api}/repositorios/", timeout=60).json())
    cantidad = min(args.cantidad, len(lista))
    momentos, paso = horario(inicio, fin, max(cantidad, 1))
    log(f"=== Análisis programados · {inicio:%Y-%m-%d %H:%M} → {fin:%H:%M} · "
        f"usuario {args.usuario}")
    log(f"Workflows con commits pendientes (repos reales): {len(lista)}; "
        f"análisis previstos: {cantidad} (uno cada {paso.total_seconds() / 60:.1f} min)")
    if cantidad < args.cantidad:
        log(f"Aviso: solo hay {len(lista)} candidatos, menos de los "
            f"{args.cantidad} pedidos.")
    log(f"{'#':>3}  {'hora':5}  {'repositorio':45} {'sha':7}  {'nivel':5}  "
        f"{'prob.':>6}  {'recomendación':26} {'IA':6} id")

    usados, hechos, saltados, errores = set(), 0, [], 0
    for n, momento in enumerate(momentos, start=1):
        esperar_hasta(momento)
        while lista:
            c = lista.pop(0)
            p = c["pendientes"]
            try:
                cabeza = github.get(
                    f"{GITHUB}/repos/{c['repositorio']}/commits/{p['rama_principal']}",
                    timeout=30)
                cabeza.raise_for_status()
                sha = cabeza.json()["sha"]
            except (requests.RequestException, KeyError, ValueError) as exc:
                saltados.append(f"{c['repositorio']}: sin cabeza ({type(exc).__name__})")
                continue
            if sha in usados:
                saltados.append(f"{c['repositorio']}: SHA {sha[:7]} ya analizado")
                continue
            usados.add(sha)
            datos = {"repositorio": c["repositorio"],
                     "workflow_path": c["workflow_path"],
                     "rama": p.get("rama") or p["rama_principal"],
                     "head_sha": sha, "evento": p.get("evento") or "push"}
            try:
                r = sesion.post(f"{args.api}/predicciones/", json=datos, timeout=240)
            except requests.RequestException as exc:
                errores += 1
                log(f"{n:>3}  {datetime.now():%H:%M}  {c['repositorio']:45} "
                    f"{sha[:7]}  ERROR de conexión ({type(exc).__name__}); sigue")
                break
            if r.status_code == 409:
                saltados.append(f"{c['repositorio']}: {sha[:7]} ya desplegado")
                continue
            if r.status_code != 201:
                errores += 1
                log(f"{n:>3}  {datetime.now():%H:%M}  {c['repositorio']:45} "
                    f"{sha[:7]}  ERROR {r.status_code}: {r.text[:120]}; sigue")
                break
            d = r.json()
            ia = (d.get("analisis_ia") or {}).get("origen") or "reglas"
            hechos += 1
            log(f"{n:>3}  {datetime.now():%H:%M}  {c['repositorio']:45} "
                f"{sha[:7]}  {d['nivel']:5}  {d['probabilidad']:6.1%}  "
                f"{d.get('recomendacion') or '-':26} {ia:6} {d['id']}")
            break
        else:
            log(f"Sin más candidatos tras {hechos} análisis.")
            break

    log(f"=== Fin {datetime.now():%H:%M} · análisis hechos: {hechos} · errores: "
        f"{errores} · candidatos saltados: {len(saltados)}")
    for motivo in saltados:
        log(f"  saltado: {motivo}")
    log(f"Log: {log.ruta}")


if __name__ == "__main__":
    main()
