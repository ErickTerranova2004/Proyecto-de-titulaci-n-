"""Carga y verifica los casos de prueba de registro de workflows (datos_prueba/).

Usa solo la API real de la plataforma, como lo haría la interfaz:

  python scripts/cargar_casos_prueba.py cargar      # registra, asigna y sincroniza
  python scripts/cargar_casos_prueba.py permisos    # verifica qué ve cada usuario

Opciones: --api http://127.0.0.1:8000/api   --sin-sincronizar   --pausa 20

Las contraseñas de prueba_admin, prueba_lider y prueba_dev se leen de las
variables de entorno PRUEBA_ADMIN_PASS, PRUEBA_LIDER_PASS y PRUEBA_DEV_PASS
o se piden por teclado. Nunca se guardan.
"""
import argparse
import json
import os
import time
from datetime import datetime
from getpass import getpass
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
CASOS = RAIZ / "datos_prueba" / "casos_prueba_30.json"
USUARIOS = {"admin": "prueba_admin", "lider": "prueba_lider", "dev": "prueba_dev"}
# Respuesta HTTP que corresponde a cada resultado esperado (comportamiento real
# de RepositorioViewSet.registrar).
HTTP_ESPERADO = {"aceptado": 201, "duplicado": 409, "rechazado": 400, "no_encontrado": 404}


class Api:
    def __init__(self, base, usuario, clave):
        self.base = base.rstrip("/")
        r = requests.post(f"{self.base}/auth/token/", json={"username": usuario, "password": clave}, timeout=30)
        r.raise_for_status()
        self.cabeceras = {"Authorization": f"Token {r.json()['token']}"}

    def pedir(self, metodo, ruta, **kw):
        r = requests.request(metodo, f"{self.base}{ruta}", headers=self.cabeceras, timeout=300, **kw)
        try:
            cuerpo = r.json()
        except ValueError:
            cuerpo = {}
        return r.status_code, cuerpo


def clave(rol):
    variable = f"PRUEBA_{rol.upper()}_PASS"
    return os.environ.get(variable) or getpass(f"Contraseña de {USUARIOS[rol]}: ")


def sesiones(base, roles):
    return {rol: Api(base, USUARIOS[rol], clave(rol)) for rol in roles}


def asignar(admin, usuario, repo_id):
    """Añade el repositorio a los accesos del usuario sin quitar los que ya tiene."""
    _, datos = admin.pedir("GET", "/gestion/usuarios/")
    u = next(x for x in datos["usuarios"] if x["usuario"] == usuario)
    actuales = {r["id"] for r in u["repositorios"]}
    if repo_id in actuales:
        return "ya asignado"
    codigo, _ = admin.pedir("PUT", f"/gestion/usuarios/{u['id']}/repositorios/",
                            json={"repositorios": sorted(actuales | {repo_id})})
    return "asignado" if codigo == 200 else f"error {codigo}"


def id_repositorio(admin, nombre):
    _, repos = admin.pedir("GET", "/repositorios/?todos=1")
    return next((r["id"] for r in repos if r["nombre_completo"].lower() == nombre.lower()), None)


def cargar(args):
    casos = json.loads(CASOS.read_text(encoding="utf-8"))
    admin = sesiones(args.api, ["admin"])["admin"]
    filas, discrepancias = [], []
    for caso in casos:
        inicio = time.monotonic()
        codigo, cuerpo = admin.pedir("POST", "/repositorios/registrar/", json={
            "repositorio": caso["repositorio"], "workflow_path": caso["ruta_workflow"], "evidencia": caso["evidencia"]})
        esperado = HTTP_ESPERADO[caso["resultado_esperado"]]
        nota = cuerpo.get("detail") or cuerpo.get("codigo") or ""
        acciones = []
        repo_id = id_repositorio(admin, caso["repositorio"]) if codigo in (201, 409) else None
        if repo_id:
            for rol in caso["asignar_a"]:
                acciones.append(f"{USUARIOS[rol]}: {asignar(admin, USUARIOS[rol], repo_id)}")
        sincronizacion = "—"
        if repo_id and codigo == 201 and not args.sin_sincronizar:
            t0 = time.monotonic()
            c, s = admin.pedir("POST", f"/repositorios/{repo_id}/sincronizar/")
            sincronizacion = (f"{s.get('ejecuciones_guardadas', '?')} ejecuciones en {time.monotonic() - t0:.1f} s"
                              if c == 200 else f"error {c}: {s.get('detail', '')}")
        if codigo != esperado:
            discrepancias.append((caso, codigo, nota))
        filas.append((caso, codigo, esperado, nota, ", ".join(acciones) or "—", sincronizacion,
                      time.monotonic() - inicio))
        print(f"#{caso['id']:>2} {caso['repositorio']}: {codigo} (esperado {esperado}) {sincronizacion}", flush=True)
        time.sleep(args.pausa)
    escribir_informe(filas, discrepancias)


def escribir_informe(filas, discrepancias):
    salida = RAIZ / "datos_prueba" / "resultado_carga.md"
    lineas = [f"# Resultado de la carga de casos ({datetime.now():%Y-%m-%d %H:%M})", "",
              f"Casos: {len(filas)} · coinciden con lo esperado: {len(filas) - len(discrepancias)} · "
              f"discrepancias: {len(discrepancias)}", "",
              "| # | Tipo | Repositorio | HTTP real | HTTP esperado | Mensaje | Asignación | Sincronización |",
              "|---|---|---|---|---|---|---|---|"]
    for caso, codigo, esperado, nota, acciones, sincronizacion, _ in filas:
        marca = "" if codigo == esperado else " ⚠"
        lineas.append(f"| {caso['id']} | {caso['tipo']} | {caso['repositorio']} | {codigo}{marca} | {esperado} | "
                      f"{str(nota).replace('|', '/')} | {acciones} | {sincronizacion} |")
    if discrepancias:
        lineas += ["", "## Discrepancias (hallazgos sobre la plataforma)", ""]
        lineas += [f"- #{c['id']} {c['repositorio']}: se esperaba {c['resultado_esperado']} "
                   f"({HTTP_ESPERADO[c['resultado_esperado']]}) y respondió {codigo}: {nota}"
                   for c, codigo, nota in discrepancias]
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Informe: {salida}")


def permisos(args):
    casos = json.loads(CASOS.read_text(encoding="utf-8"))
    api = sesiones(args.api, ["admin", "lider", "dev"])
    lineas = [f"# Verificación de permisos ({datetime.now():%Y-%m-%d %H:%M})", ""]
    total_fallos = 0
    for rol, sesion in api.items():
        _, analisis = sesion.pedir("GET", "/repositorios/")
        _, asignados = sesion.pedir("GET", "/repositorios/?todos=1")
        ve_nuevo = {r["nombre_completo"].lower() for r in analisis}
        ve_todos = {r["nombre_completo"].lower() for r in asignados}
        fallos, deberia = [], 0
        for caso in casos:
            esperado = caso["visibilidad_esperada"][rol]
            nombre = caso["repositorio"].lower()
            deberia += esperado["nuevo_analisis"]
            if (nombre in ve_nuevo) != esperado["nuevo_analisis"] or (nombre in ve_todos) != esperado["asignados"]:
                fallos.append(f"#{caso['id']} {caso['repositorio']}: Nuevo análisis {nombre in ve_nuevo} "
                              f"(esperado {esperado['nuevo_analisis']}), asignados {nombre in ve_todos} "
                              f"(esperado {esperado['asignados']})")
        total_fallos += len(fallos)
        lineas += [f"## {USUARIOS[rol]}", "",
                   f"- Debe ver en Nuevo análisis {deberia} de los 30 casos; los ve: "
                   f"{sum(c['repositorio'].lower() in ve_nuevo for c in casos)}.",
                   f"- Discrepancias: {len(fallos)}", *[f"  - {f}" for f in fallos], ""]
    salida = RAIZ / "datos_prueba" / "resultado_permisos.md"
    salida.write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas))
    print(f"Informe: {salida} · discrepancias totales: {total_fallos}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("modo", choices=["cargar", "permisos"])
    p.add_argument("--api", default="http://127.0.0.1:8000/api")
    p.add_argument("--sin-sincronizar", action="store_true")
    p.add_argument("--pausa", type=float, default=20, help="segundos entre repositorios")
    args = p.parse_args()
    cargar(args) if args.modo == "cargar" else permisos(args)
