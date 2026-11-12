"""Genera el diagrama entidad-relación desde el esquema real de la base de
datos, con el estilo de docs/modelo_er.png.

    backend\\venv\\Scripts\\python.exe scripts\\generar_diagrama_er.py [--png]

Escribe docs/modelo_er_actualizado.drawio y, con --png, también
docs/modelo_er_actualizado.png (lo dibuja el visor de draw.io en Microsoft
Edge sin interfaz: el diagrama no sale del equipo, solo se descarga el
script del visor). Tablas, columnas, tipos, PK, FK, UK y nulos salen del
catálogo de PostgreSQL; las vistas seg_* se describen como en el ER.
"""

import html
import json
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.db import connection  # noqa: E402

# --- Estilo (docs/modelo_er.png) -------------------------------------------

CATEGORIAS = {
    "seg": ("Seguridad", "#5B3F8F"),
    "int": ("Intermedia (N:M)", "#3F7B3A"),
    "mae": ("Maestra / catálogo", "#1F6A85"),
    "trx": ("Transaccional", "#A8541F"),
}
FONDO_PK, TEXTO_FK = "#FFF3DE", "#5A4A9E"
FONDO_AUDITORIA, TEXTO_AUDITORIA = "#ECEFF2", "#555555"
LETRA_FILA = "Courier New"
ANCHO, ALTO_CABECERA, ALTO_FILA = 380, 32, 24
SEPARACION_COLUMNAS, SEPARACION_TABLAS = 180, 70
X0, Y0 = 20, 110
AUDITORIA = ("est_registro", "usu_creacion", "fec_creacion",
             "usu_modificacion", "fec_modificacion")

# Columnas del diagrama: de izquierda a derecha y de arriba abajo.
DISPOSICION = [
    ["seg_token", "seg_usuario", "int_usuario_grupo", "seg_grupo",
     "trx_seguimiento_lote", "trx_pendiente_despliegue"],
    ["int_acceso_repositorio", "mae_workflow", "trx_ejecucion_workflow"],
    ["mae_repositorio", "trx_commit", "trx_prediccion",
     "int_prediccion_ejecucion"],
    ["mae_version_modelo", "trx_decision_despliegue"],
]

# Vistas de seguridad sobre las tablas de Django (migración 0018).
VISTAS = {
    "seg_usuario": {"pk": "id_usuario", "uk": {"nom_usuario"}, "fk": {}},
    "seg_grupo": {"pk": "id_grupo", "uk": {"nom_grupo"}, "fk": {}},
    "int_usuario_grupo": {
        "pk": "id_usuario_grupo", "uk": {"id_usuario", "id_grupo"},
        "fk": {"id_usuario": "seg_usuario", "id_grupo": "seg_grupo"}},
    "seg_token": {"pk": "cod_token", "uk": {"id_usuario"},
                  "fk": {"id_usuario": "seg_usuario"}, "uno_a_uno": True},
}
# Tipos reales de las tablas de Django bajo las vistas.
TIPOS_VISTAS = {("int_usuario_grupo", "id_usuario_grupo"): "bigint"}
TABLA_DJANGO = {"auth_user": "seg_usuario", "auth_group": "seg_grupo"}


def tipo_er(tipo, columna):
    if columna == "est_registro":
        return "char(1) 'A'/'I'"
    return (tipo.replace("character varying", "varchar")
            .replace("character(", "char(")
            .replace("timestamp with time zone", "timestamptz")
            .replace("double precision", "float8").replace("boolean", "bool")
            .replace("integer", "int"))


def leer_esquema():
    tablas = [t for columna in DISPOSICION for t in columna]
    with connection.cursor() as c:
        c.execute("""
            SELECT t.relname, a.attname, format_type(a.atttypid, a.atttypmod),
                   NOT a.attnotnull
              FROM pg_attribute a JOIN pg_class t ON t.oid = a.attrelid
             WHERE t.relname = ANY(%s) AND a.attnum > 0 AND NOT a.attisdropped
             ORDER BY t.relname, a.attnum""", [tablas])
        columnas = {}
        for tabla, col, tipo, nulo in c.fetchall():
            tipo = TIPOS_VISTAS.get((tabla, col), tipo)
            if tabla in VISTAS:
                nulo = False  # las columnas de origen son NOT NULL
            columnas.setdefault(tabla, []).append(
                {"nombre": col, "tipo": tipo_er(tipo, col), "nulo": nulo})
        c.execute("""
            SELECT t.relname, c.contype, c.conkey, c.conrelid, r.relname,
                   (SELECT array_agg(a.attname ORDER BY k.ord)
                      FROM unnest(c.conkey) WITH ORDINALITY k(n, ord)
                      JOIN pg_attribute a ON a.attrelid = c.conrelid
                                         AND a.attnum = k.n)
              FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
              LEFT JOIN pg_class r ON r.oid = c.confrelid
             WHERE t.relname = ANY(%s) AND c.contype IN ('p', 'u', 'f')""",
                  [tablas])
        claves = {}
        for tabla, tipo, _, _, destino, cols in c.fetchall():
            k = claves.setdefault(tabla, {"pk": None, "uk": set(), "fk": {},
                                          "uk_solas": set()})
            if tipo == "p":
                k["pk"] = cols[0]
            elif tipo == "u":
                k["uk"].update(cols)
                if len(cols) == 1:
                    k["uk_solas"].add(cols[0])
            else:
                k["fk"][cols[0]] = TABLA_DJANGO.get(destino, destino)
    for vista, k in VISTAS.items():
        claves[vista] = {"pk": k["pk"], "uk": set(k["uk"]), "fk": dict(k["fk"]),
                         "uk_solas": ({"id_usuario"} if k.get("uno_a_uno")
                                      else set())}
    return columnas, claves


def orden_modelos():
    """Orden de las columnas según la definición de cada modelo (el del ER:
    claves foráneas primero y campos después)."""
    orden = {}
    for modelo in apps.get_app_config("riesgo").get_models():
        orden[modelo._meta.db_table] = [f.column for f in
                                        modelo._meta.concrete_fields]
    return orden


ORDEN = None


def ordenar(tabla, columnas, k):
    """PK, columnas del negocio y auditoría al final."""
    global ORDEN
    ORDEN = ORDEN or orden_modelos()
    por_nombre = {c["nombre"]: c for c in columnas}
    negocio = [c for c in columnas
               if c["nombre"] != k["pk"] and c["nombre"] not in AUDITORIA]
    if tabla in ORDEN:
        posicion = {c: i for i, c in enumerate(ORDEN[tabla])}
        negocio.sort(key=lambda c: posicion.get(c["nombre"], 999))
    return ([por_nombre[k["pk"]]], negocio,
            [por_nombre[a] for a in AUDITORIA if a in por_nombre])


# --- draw.io -----------------------------------------------------------------

class Diagrama:
    def __init__(self):
        self.celdas = []
        self.n = 0

    def id(self, prefijo):
        self.n += 1
        return f"{prefijo}{self.n}"

    def celda(self, ident, valor, estilo, x, y, w, h, padre="1"):
        self.celdas.append(
            f'<mxCell id="{ident}" value="{html.escape(valor, quote=True)}" '
            f'style="{estilo}" vertex="1" parent="{padre}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" '
            f'as="geometry"/></mxCell>')

    def arista(self, ident, origen, destino, estilo, puntos, etiquetas):
        pts = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in puntos)
        self.celdas.append(
            f'<mxCell id="{ident}" style="{estilo}" edge="1" parent="1" '
            f'source="{origen}" target="{destino}"><mxGeometry relative="1" '
            f'as="geometry"><Array as="points">{pts}</Array></mxGeometry>'
            f'</mxCell>')
        for valor, x, dx, dy in etiquetas:
            self.celdas.append(
                f'<mxCell id="{self.id("l")}" value="{valor}" style="edgeLabel;'
                f'html=1;align=center;verticalAlign=middle;resizable=0;'
                f'points=[];fontSize=12;fontFamily=Helvetica;labelBackgroundColor='
                f'#FFFFFF;" vertex="1" connectable="0" parent="{ident}">'
                f'<mxGeometry x="{x}" relative="1" as="geometry">'
                f'<mxPoint x="{dx}" y="{dy}" as="offset"/></mxGeometry>'
                f'</mxCell>')

    def xml(self, ancho, alto):
        return (
            '<mxfile host="generar_diagrama_er.py"><diagram id="er" '
            'name="Modelo ER"><mxGraphModel dx="1600" dy="1200" grid="0" '
            'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
            f'fold="1" page="1" pageScale="1" pageWidth="{ancho}" '
            f'pageHeight="{alto}" background="#FFFFFF" math="0" shadow="0">'
            '<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            + "".join(self.celdas) + "</root></mxGraphModel></diagram></mxfile>")


def texto_fila(col, k, es_pk):
    nombre = col["nombre"]
    marcas = []
    if es_pk:
        marcas.append("PK")
    if nombre in k["fk"]:
        marcas.append("FK")
    if nombre in k["uk"] and not es_pk:
        marcas.append("UK")
    prefijo = (",".join(marcas) + " ") if marcas else ""
    return f"{prefijo}{nombre} : {col['tipo']}"


def dibujar_tabla(d, tabla, columnas, k, x, y):
    categoria, color = CATEGORIAS[tabla.split("_", 1)[0]]
    pk, negocio, auditoria = ordenar(tabla, columnas, k)
    filas = len(pk) + len(negocio) + len(auditoria)
    alto = ALTO_CABECERA + filas * ALTO_FILA
    caja = f"t_{tabla}"
    d.celda(caja, "", f"rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
            f"strokeColor={color};strokeWidth=1.5;", x, y, ANCHO, alto)
    d.celda(d.id("h"), f"<b>{tabla}</b>", f"text;html=1;fillColor={color};"
            "strokeColor=none;fontColor=#FFFFFF;fontSize=16;fontFamily="
            "Helvetica;align=left;verticalAlign=middle;spacingLeft=12;",
            x, y, ANCHO, ALTO_CABECERA)
    d.celda(d.id("c"), f"<i>{categoria}</i>", "text;html=1;fillColor=none;"
            "strokeColor=none;fontColor=#FFFFFF;fontSize=11;fontFamily="
            "Helvetica;align=right;verticalAlign=middle;spacingRight=10;",
            x + ANCHO - 170, y, 170, ALTO_CABECERA)
    filas_id, fila_y = {}, y + ALTO_CABECERA
    secciones = [(pk, "pk"), (negocio, "negocio"), (auditoria, "auditoria")]
    for lista, seccion in secciones:
        for i, col in enumerate(lista):
            es_fk = col["nombre"] in k["fk"]
            fondo = {"pk": FONDO_PK, "negocio": "#FFFFFF",
                     "auditoria": FONDO_AUDITORIA}[seccion]
            letra = (TEXTO_AUDITORIA if seccion == "auditoria"
                     else TEXTO_FK if es_fk else "#1F1F1F")
            estilo_letra = {"pk": 1, "negocio": 0, "auditoria": 2}[seccion]
            borde_sup = ("strokeColor=#B8BEC6;" if i == 0 and seccion != "pk"
                         else "strokeColor=none;")
            ident = f"f_{tabla}_{col['nombre']}"
            d.celda(ident, texto_fila(col, k, seccion == "pk"),
                    f"text;html=0;fillColor={fondo};{borde_sup}fontColor={letra};"
                    f"fontStyle={estilo_letra};fontSize=13;fontFamily="
                    f"{LETRA_FILA};align=left;verticalAlign=middle;"
                    "spacingLeft=10;", x + 1, fila_y, ANCHO - 2, ALTO_FILA)
            filas_id[col["nombre"]] = (ident, fila_y + ALTO_FILA / 2)
            fila_y += ALTO_FILA
    return {"caja": caja, "x": x, "y": y, "alto": alto, "filas": filas_id}


def generar():
    columnas, claves = leer_esquema()
    d = Diagrama()
    pos, columna_de = {}, {}
    for ci, lista in enumerate(DISPOSICION):
        x, y = X0 + ci * (ANCHO + SEPARACION_COLUMNAS), Y0
        for tabla in lista:
            pos[tabla] = dibujar_tabla(d, tabla, columnas[tabla], claves[tabla],
                                       x, y)
            columna_de[tabla] = ci
            y += pos[tabla]["alto"] + SEPARACION_TABLAS
    fondo = max(p["y"] + p["alto"] for p in pos.values())
    ancho = X0 + len(DISPOSICION) * (ANCHO + SEPARACION_COLUMNAS)

    # Relaciones: una por FK (hijo → padre).
    relaciones = []
    for tabla in pos:
        k = claves[tabla]
        nulos = {c["nombre"]: c["nulo"] for c in columnas[tabla]}
        for col, padre in sorted(k["fk"].items()):
            relaciones.append((tabla, col, padre, nulos.get(col, False),
                               col in k["uk_solas"]))
    canales = {}      # x del canal → número de aristas que ya lo usan
    entradas = {}     # tabla padre → número de aristas que ya llegan
    carriles = 0      # carriles horizontales bajo el diagrama

    def canal(ci_izq):
        """x libre en el canal a la derecha de la columna ci_izq."""
        base = X0 + ci_izq * (ANCHO + SEPARACION_COLUMNAS) + ANCHO
        n = canales.get(ci_izq, 0)
        canales[ci_izq] = n + 1
        return base + 18 + (n % 10) * 15

    for hijo, col, padre, nulo, uno_a_uno in relaciones:
        h, p = pos[hijo], pos[padre]
        ci_h, ci_p = columna_de[hijo], columna_de[padre]
        fila_hijo, y_hijo = h["filas"][col]
        n_ent = entradas.get(padre, 0)
        entradas[padre] = n_ent + 1
        y_entrada = p["filas"][claves[padre]["pk"]][1] + n_ent * ALTO_FILA
        lado_padre_y = (y_entrada - p["y"]) / p["alto"]
        fin_padre = "ERzeroToOne" if nulo else "ERmandOne"
        fin_hijo = "ERzeroToOne" if uno_a_uno else "ERzeroToMany"
        et_padre, et_hijo = ("0..1" if nulo else "1..1"), (
            "0..1" if uno_a_uno else "0..*")
        estilo = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;"
                  "strokeColor=#1F1F1F;strokeWidth=1.2;"
                  f"startArrow={fin_hijo};endArrow={fin_padre};startFill=0;"
                  "endFill=0;startSize=14;endSize=14;jumpStyle=arc;")
        puntos = []
        vecinas = (ci_h == ci_p and abs(DISPOSICION[ci_h].index(hijo)
                                        - DISPOSICION[ci_p].index(padre)) == 1)
        if vecinas:
            arriba = p["y"] < h["y"]
            origen, destino = h["caja"], p["caja"]
            sale_y, entra_y = (0, 1) if arriba else (1, 0)
            estilo += (f"exitX=0.5;exitY={sale_y};exitDx=0;exitDy=0;"
                       f"entryX=0.5;entryY={entra_y};entryDx=0;entryDy=0;")
            dy = -12 if arriba else 12
            etiquetas = [(et_hijo, -1, 18, dy), (et_padre, 1, 18, -dy)]
        else:
            origen, destino = fila_hijo, p["caja"]
            if ci_h > ci_p or (ci_h == ci_p and ci_h > 0):
                sale_x, entra_x = 0, 1
            else:
                sale_x, entra_x = 1, 0
            estilo += (f"exitX={sale_x};exitY=0.5;exitDx=0;exitDy=0;"
                       f"entryX={entra_x};entryY={lado_padre_y:.4f};"
                       "entryDx=0;entryDy=0;")
            if abs(ci_h - ci_p) <= 1 and ci_h != ci_p:
                x_c = canal(min(ci_h, ci_p))
                puntos = [(x_c, y_hijo), (x_c, y_entrada)]
            elif ci_h == ci_p:
                x_c = canal(ci_h if sale_x == 1 else ci_h - 1)
                puntos = [(x_c, y_hijo), (x_c, y_entrada)]
            else:
                # Por debajo del diagrama, de un canal al otro.
                carriles += 1
                y_c = fondo + 30 + carriles * 22
                x_h = canal(ci_h - 1 if sale_x == 0 else ci_h)
                x_p = canal(ci_p if entra_x == 1 else ci_p - 1)
                puntos = [(x_h, y_hijo), (x_h, y_c), (x_p, y_c),
                          (x_p, y_entrada)]
            dx_h = -16 if sale_x == 0 else 16
            dx_p = 16 if entra_x == 1 else -16
            etiquetas = [(et_hijo, -1, dx_h, -11), (et_padre, 1, dx_p, -11)]
        d.arista(d.id("e"), origen, destino, estilo, puntos, etiquetas)

    alto = fondo + 60 + carriles * 22
    d.celda(d.id("titulo"), "<b>Modelo Entidad-Relación · Sistema de "
            "predicción de riesgo de despliegue</b>", "text;html=1;"
            "fontSize=26;fontFamily=Helvetica;fontColor=#1F2933;align=left;"
            "verticalAlign=middle;strokeColor=none;fillColor=none;",
            X0, 18, 1500, 40)
    d.celda(d.id("sub"), f"Actualizado desde el esquema de la base de datos "
            f"(migración 0019) · {date.today().isoformat()} · seg_*: vistas "
            "de solo lectura sobre las tablas de usuarios de Django",
            "text;html=1;fontSize=14;fontFamily=Helvetica;fontColor=#52606D;"
            "align=left;verticalAlign=middle;strokeColor=none;fillColor=none;",
            X0, 56, 1500, 28)
    return d.xml(ancho, alto), ancho, alto


def exportar_png(xml, ancho, alto, destino):
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    with tempfile.TemporaryDirectory() as tmp:
        pagina = Path(tmp) / "er.html"
        config = json.dumps({"xml": xml, "toolbar": "", "nav": False,
                             "resize": False, "lightbox": False, "zoom": 1})
        pagina.write_text(
            "<!doctype html><html><head><meta charset='utf-8'><style>"
            "html,body{margin:0;background:#fff}</style></head><body>"
            f"<div class='mxgraph' style='width:{ancho}px' "
            f"data-mxgraph='{html.escape(config, quote=True)}'></div>"
            "<script src='https://viewer.diagrams.net/js/viewer-static.min.js'>"
            "</script></body></html>", encoding="utf-8")
        subprocess.run([str(edge), "--headless=new", "--disable-gpu",
                        "--no-first-run", f"--user-data-dir={tmp}\\perfil",
                        "--hide-scrollbars", "--force-device-scale-factor=2",
                        "--virtual-time-budget=30000",
                        f"--window-size={ancho},{alto}",
                        f"--screenshot={destino}", pagina.as_uri()],
                       check=True, capture_output=True, timeout=180)


def main():
    xml, ancho, alto = generar()
    salida = RAIZ / "docs" / "modelo_er_actualizado.drawio"
    salida.write_text(xml, encoding="utf-8")
    print(f"{salida} ({ancho}×{alto})")
    if "--png" in sys.argv:
        png = salida.with_suffix(".png")
        exportar_png(xml, ancho, alto, png)
        print(png)


if __name__ == "__main__":
    main()
