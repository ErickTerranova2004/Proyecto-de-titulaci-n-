"""Informe de cumplimiento: el desarrollador informa al líder técnico de cómo
atendió una asignación con un nuevo análisis.

- Se crea una vez por asignación, cuando ya tiene análisis de respuesta
  (registrar_respuesta) y con un comentario obligatorio sobre los cambios.
- Lo ven solo el desarrollador autor, el líder destinatario y los
  administradores (informes_visibles).
- El líder registra desde él su decisión final, que es una decisión más
  sobre el análisis nuevo (asignaciones.registrar_decision).
- Al enviarlo se avisa al líder por correo con el enlace, solo si el correo
  está configurado (settings.CORREO_CONFIGURADO) y el líder tiene correo.
- El PDF se genera aquí (ReportLab) y cada descarga queda en
  trx_descarga_informe.
"""

import logging
from io import BytesIO

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from riesgo.models import DescargaInforme, InformeCumplimiento, Prediccion
from riesgo.permissions import es_admin
from riesgo.services import asignaciones
from riesgo.services.predictor import DESCRIPCIONES, contribuciones

logger = logging.getLogger(__name__)

NOMBRE_PLATAFORMA = "Riesgo de despliegue"
MIN_COMENTARIO = 10
MAX_FACTORES = 8
RECOMENDACIONES = dict(Prediccion.RECOMENDACIONES)
NIVELES = dict(Prediccion.NIVELES)


class InformeNoValido(Exception):
    def __init__(self, mensaje, codigo):
        super().__init__(mensaje)
        self.codigo = codigo


def informes_visibles(usuario):
    consulta = InformeCumplimiento.objects.filter(est_registro="A").select_related(
        "asignacion__usuario", "prediccion_original__workflow__repositorio",
        "prediccion_original__commit", "prediccion_nueva__commit",
        "prediccion_nueva__version_modelo", "prediccion_original__version_modelo",
        "desarrollador", "lider", "decision_final__usuario")
    if es_admin(usuario):
        return consulta
    return consulta.filter(Q(lider=usuario) | Q(desarrollador=usuario))


def crear(asignacion, usuario, comentario):
    """Crea el informe de la asignación (decisión con fecha límite) que el
    usuario atendió con un nuevo análisis."""
    comentario = (comentario or "").strip()
    if asignacion.prediccion.usuario_id != usuario.id:
        raise InformeNoValido("Solo el desarrollador que hizo el análisis "
                              "puede enviar el informe.", "no_es_dueno")
    if asignacion.prediccion_respuesta_id is None or not asignacion.cumplida_en:
        raise InformeNoValido(
            "Primero cumpla la asignación con un nuevo análisis.",
            "sin_nuevo_analisis")
    if InformeCumplimiento.objects.filter(asignacion=asignacion).exists():
        raise InformeNoValido("Ya envió el informe de esta asignación.",
                              "informe_ya_enviado")
    if len(comentario) < MIN_COMENTARIO:
        raise InformeNoValido(
            f"Describa los cambios que hizo (al menos {MIN_COMENTARIO} "
            "caracteres).", "comentario_obligatorio")
    with transaction.atomic():
        informe = InformeCumplimiento.objects.create(
            asignacion=asignacion,
            prediccion_original=asignacion.prediccion,
            prediccion_nueva=asignacion.prediccion_respuesta,
            desarrollador=usuario, lider=asignacion.usuario,
            comentario=comentario[:2000])
    informe.correo_enviado = notificar_lider(informe)
    if informe.correo_enviado:
        informe.save(update_fields=["correo_enviado"])
    return informe


def enlace(informe):
    return f"{settings.FRONTEND_URL}/?informe={informe.id}"


def notificar_lider(informe):
    """Correo al líder con el enlace (solo con el correo configurado)."""
    lider = informe.lider
    if not settings.CORREO_CONFIGURADO or not lider.email:
        return False
    repositorio = informe.prediccion_original.workflow.repositorio.nombre_completo
    cuerpo = (
        f"{informe.desarrollador.username} le envió el informe de cumplimiento "
        f"{informe.numero} sobre {repositorio}.\n\n"
        f"Cambios: {informe.comentario}\n\n"
        f"Abra el informe y registre su decisión final:\n{enlace(informe)}\n")
    try:
        send_mail(f"Informe de cumplimiento {informe.numero}: {repositorio}",
                  cuerpo, settings.DEFAULT_FROM_EMAIL, [lider.email])
    except Exception:  # noqa: BLE001 - el correo no impide el informe
        logger.warning("No se pudo enviar el correo del informe %s", informe.id)
        return False
    return True


def puede_decidir(informe, usuario):
    return usuario.id == informe.lider_id or es_admin(usuario)


def decidir(informe, usuario, decision, comentario=""):
    """Decisión final del líder: una decisión sobre el análisis nuevo."""
    if not puede_decidir(informe, usuario):
        raise InformeNoValido("Solo el líder destinatario o un administrador "
                              "registran la decisión final.", "no_es_lider")
    with transaction.atomic():
        final = asignaciones.registrar_decision(
            informe.prediccion_nueva, usuario, decision, comentario)
        informe.decision_final = final
        informe.leido_en = informe.leido_en or timezone.now()
        informe.save(update_fields=["decision_final", "leido_en"])
    return informe


def marcar_leido(informe, usuario):
    if usuario.id == informe.lider_id and informe.leido_en is None:
        informe.leido_en = timezone.now()
        informe.save(update_fields=["leido_en"])


# ------------------------------------------------------------------ contenido
def _analisis(p):
    return {
        "id": p.id, "creada_en": p.creada_en, "rama": p.rama,
        "commit": p.commit.sha, "probabilidad": p.probabilidad,
        "nivel": p.nivel, "nivel_texto": NIVELES.get(p.nivel, p.nivel),
        "recomendacion": p.recomendacion,
        "recomendacion_texto": RECOMENDACIONES.get(p.recomendacion, "—"),
        "version_modelo": p.version_modelo.version,
    }


def factores_cambio(original, nueva, n=MAX_FACTORES):
    """Variables cuya contribución SHAP más cambió entre los dos análisis
    (cada uno con su versión del modelo)."""
    try:
        antes = contribuciones(original.variables, original.version_modelo)
        despues = contribuciones(nueva.variables, nueva.version_modelo)
    except Exception:  # noqa: BLE001 - sin el modelo no se puede explicar
        logger.warning("No se pudo calcular SHAP para el informe (%s, %s)",
                       original.id, nueva.id)
        return []
    filas = []
    for variable in set(antes) | set(despues):
        a, d = antes.get(variable, 0.0), despues.get(variable, 0.0)
        if abs(d - a) > 1e-6:
            filas.append({
                "variable": variable,
                "descripcion": DESCRIPCIONES.get(variable, variable),
                "valor_original": original.variables.get(variable),
                "valor_nuevo": nueva.variables.get(variable),
                "contribucion_original": round(a, 4),
                "contribucion_nueva": round(d, 4),
                "diferencia": round(d - a, 4)})
    filas.sort(key=lambda f: -abs(f["diferencia"]))
    return filas[:n]


def _decision(d):
    if d is None:
        return None
    return {"id": d.id, "decision": d.decision,
            "texto": d.get_decision_display(), "comentario": d.comentario,
            "usuario": d.usuario.username, "creada_en": d.creada_en,
            "fecha_limite": d.fecha_limite}


def resumen(informe):
    """Fila de la lista «Informes recibidos»."""
    original, nueva = informe.prediccion_original, informe.prediccion_nueva
    return {
        "id": informe.id, "numero": informe.numero,
        "enviado_en": informe.enviado_en, "leido_en": informe.leido_en,
        "repositorio": original.workflow.repositorio.nombre_completo,
        "workflow": original.workflow.path,
        "desarrollador": informe.desarrollador.username,
        "lider": informe.lider.username,
        "nivel_original": original.nivel, "nivel_nuevo": nueva.nivel,
        "diferencia_puntos": round((nueva.probabilidad - original.probabilidad)
                                   * 100, 2),
        "decision_final": _decision(informe.decision_final),
    }


def contenido(informe, usuario=None):
    """Todo el informe (pantalla y PDF)."""
    original, nueva = informe.prediccion_original, informe.prediccion_nueva
    asignacion = informe.asignacion
    ia = nueva.analisis_ia or {}
    datos = resumen(informe)
    datos.update({
        "emitido_en": timezone.now(),
        "plataforma": NOMBRE_PLATAFORMA,
        "correo_enviado": informe.correo_enviado,
        "indicacion": {**_decision(asignacion),
                       "cumplida_en": asignacion.cumplida_en},
        "original": _analisis(original),
        "nuevo": _analisis(nueva),
        "factores": factores_cambio(original, nueva),
        "comentario": informe.comentario,
        "ia": {"resumen": ia.get("resumen") or "", "origen": ia.get("origen") or "",
               "modelo": ia.get("modelo") or "",
               "recomendaciones": [r.get("texto", "") for r in
                                   (nueva.recomendaciones or []) if r.get("texto")]},
        "puede_decidir": bool(usuario) and puede_decidir(informe, usuario),
        "descargas": informe.descargas.count(),
    })
    return datos


# ------------------------------------------------------------------------ PDF
def registrar_descarga(informe, usuario, formato="pdf"):
    return DescargaInforme.objects.create(
        informe=informe, usuario=usuario, nombre_usuario=usuario.username,
        formato=formato)


def _txt(valor):
    """Texto seguro para las fuentes base de ReportLab (Latin-1)."""
    texto = "" if valor is None else str(valor)
    texto = (texto.replace("−", "-").replace("–", "-").replace("—", "-")
             .replace("«", '"').replace("»", '"').replace("→", "->")
             .replace("·", "-"))
    texto = texto.encode("latin-1", "replace").decode("latin-1")
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fecha(valor, con_hora=True):
    if not valor:
        return "-"
    if hasattr(valor, "astimezone"):
        valor = timezone.localtime(valor)
        return valor.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")
    return valor.strftime("%d/%m/%Y")


def _puntos(valor):
    signo = "+" if valor > 0 else "-" if valor < 0 else "+/-"
    return f"{signo}{abs(valor):.1f} puntos".replace(".", ",")


def _pct(p):
    return f"{p * 100:.1f} %".replace(".", ",")


def _num(valor):
    """Valor de una variable con coma decimal ("Sin dato" si falta)."""
    if valor is None:
        return "Sin dato"
    if isinstance(valor, float):
        return (f"{valor:.0f}" if valor.is_integer() else f"{valor:.2f}").replace(".", ",")
    return str(valor)


def pdf(informe, usuario):
    """Bytes del PDF del informe."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    c = contenido(informe, usuario)
    estilos = getSampleStyleSheet()
    normal = ParagraphStyle("n", parent=estilos["Normal"], fontSize=9.5,
                            leading=13)
    pequeno = ParagraphStyle("p", parent=normal, fontSize=8, leading=10,
                             textColor=colors.HexColor("#56657a"))
    titulo = ParagraphStyle("t", parent=estilos["Heading2"], fontSize=12,
                            spaceBefore=10, spaceAfter=4,
                            textColor=colors.HexColor("#1565c0"))
    azul = colors.HexColor("#1565c0")
    borde = colors.HexColor("#c3cfdd")

    def p(texto, estilo=normal):
        return Paragraph(texto, estilo)

    def tabla(filas, anchos, cabecera=True):
        t = Table([[p(_txt(x)) if not isinstance(x, Paragraph) else x for x in fila]
                   for fila in filas], colWidths=anchos)
        estilo = [("GRID", (0, 0), (-1, -1), 0.4, borde),
                  ("VALIGN", (0, 0), (-1, -1), "TOP"),
                  ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f8fc"))]
        if cabecera:
            estilo = [("GRID", (0, 0), (-1, -1), 0.4, borde),
                      ("VALIGN", (0, 0), (-1, -1), "TOP"),
                      ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3eefb"))]
        t.setStyle(TableStyle(estilo))
        return t

    def encabezado(lienzo, doc):
        lienzo.saveState()
        ancho, alto = A4
        lienzo.setFillColor(azul)
        lienzo.setFont("Helvetica-Bold", 13)
        lienzo.drawString(18 * mm, alto - 15 * mm, _txt(NOMBRE_PLATAFORMA).replace("&amp;", "&"))
        lienzo.setFont("Helvetica", 9)
        lienzo.setFillColor(colors.HexColor("#172235"))
        lienzo.drawRightString(ancho - 18 * mm, alto - 12 * mm,
                               f"Informe de cumplimiento {c['numero']}")
        lienzo.drawRightString(ancho - 18 * mm, alto - 17 * mm,
                               f"Emitido el {_fecha(c['emitido_en'])}")
        lienzo.setStrokeColor(borde)
        lienzo.line(18 * mm, alto - 20 * mm, ancho - 18 * mm, alto - 20 * mm)
        lienzo.setFont("Helvetica", 7.5)
        lienzo.drawString(18 * mm, 10 * mm, f"{c['numero']} - página {doc.page}")
        lienzo.restoreState()

    o, n = c["original"], c["nuevo"]
    ind = c["indicacion"]
    historia = [
        p(f"<b>Informe de cumplimiento {c['numero']}</b>", ParagraphStyle(
            "h", parent=normal, fontSize=15, leading=19, spaceAfter=6)),
        tabla([["Repositorio", c["repositorio"]], ["Workflow", c["workflow"]],
               ["Desarrollador", c["desarrollador"]], ["Líder técnico", c["lider"]],
               ["Asignación", _fecha(ind["creada_en"])],
               ["Cumplida", _fecha(ind["cumplida_en"])],
               ["Informe enviado", _fecha(c["enviado_en"])]],
              [40 * mm, 134 * mm], cabecera=False),
        p("Indicación del líder", titulo),
        tabla([["Acción", ind["texto"]], ["Comentario", ind["comentario"] or "-"],
               ["Fecha límite", _fecha(ind["fecha_limite"], False)]],
              [40 * mm, 134 * mm], cabecera=False),
        p("Análisis original frente al nuevo", titulo),
        tabla([["", f"Original (#{o['id']})", f"Nuevo (#{n['id']})"],
               ["Fecha", _fecha(o["creada_en"]), _fecha(n["creada_en"])],
               ["Commit", o["commit"][:12], n["commit"][:12]],
               ["Probabilidad", _pct(o["probabilidad"]), _pct(n["probabilidad"])],
               ["Nivel", o["nivel_texto"], n["nivel_texto"]],
               ["Recomendación", o["recomendacion_texto"], n["recomendacion_texto"]],
               ["Modelo", o["version_modelo"], n["version_modelo"]]],
              [40 * mm, 67 * mm, 67 * mm]),
        Spacer(1, 3),
        p(f"Diferencia: <b>{_txt(_puntos(c['diferencia_puntos']))}</b>"),
        p("Factores que más cambiaron (SHAP)", titulo),
    ]
    if c["factores"]:
        historia.append(tabla(
            [["Variable", "Original", "Nuevo", "Cambio SHAP"]] + [
                [f["descripcion"], _num(f["valor_original"]), _num(f["valor_nuevo"]),
                 f"{f['diferencia']:+.3f} ({'sube' if f['diferencia'] > 0 else 'baja'})"
                 .replace(".", ",")]
                for f in c["factores"]],
            [82 * mm, 28 * mm, 28 * mm, 36 * mm]))
        historia.append(p("Diferencia de la contribución SHAP de cada variable "
                          "(nuevo menos original): positiva sube el riesgo.",
                          pequeno))
    else:
        historia.append(p("No hay diferencias de contribución entre los dos análisis."))
    historia += [p("Comentario del desarrollador", titulo),
                 p(_txt(c["comentario"]).replace("\n", "<br/>")),
                 p("Análisis de la IA del análisis nuevo", titulo),
                 p(_txt(c["ia"]["resumen"] or "Sin resumen de la IA.").replace("\n", "<br/>"))]
    for r in c["ia"]["recomendaciones"]:
        historia.append(p(f"- {_txt(r)}"))
    if c["ia"]["origen"]:
        historia.append(p(_txt(f"Origen: {c['ia']['origen']} {c['ia']['modelo']}"), pequeno))
    historia.append(p("Decisión final del líder", titulo))
    final = c["decision_final"]
    if final:
        historia.append(tabla([["Decisión", final["texto"]],
                               ["Comentario", final["comentario"] or "-"],
                               ["Registrada por", final["usuario"]],
                               ["Fecha", _fecha(final["creada_en"])]],
                              [40 * mm, 134 * mm], cabecera=False))
    else:
        historia.append(p("Pendiente: el líder aún no registró su decisión final."))

    salida = BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=A4, leftMargin=18 * mm,
                            rightMargin=18 * mm, topMargin=26 * mm,
                            bottomMargin=16 * mm,
                            title=f"Informe de cumplimiento {c['numero']}",
                            author=NOMBRE_PLATAFORMA)
    doc.build(historia, onFirstPage=encabezado, onLaterPages=encabezado)
    return salida.getvalue()
