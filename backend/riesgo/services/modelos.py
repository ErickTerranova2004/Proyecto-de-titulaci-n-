"""Activación de versiones del modelo.

Solo se puede activar una versión visible (est_registro = 'A') con fecha de
corte (metadatos.fecha_corte): sin ella el análisis en lote no sabe desde
cuándo evaluar y la supervisión no se puede calcular. v1 y v1.1 no la tienen;
solo se evalúan en sombra (services/sombra.py).

Activar exige escribir el nombre de la versión como confirmación y deja una
fila en trx_activacion_modelo (quién, cuándo, desde dónde y cuál estaba
activa antes).
"""

from django.db import transaction

from .. import auditoria
from ..models import ActivacionModelo, VersionModelo
from .features import fecha


class NoActivable(Exception):
    def __init__(self, mensaje, codigo):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def fecha_corte(version):
    try:
        return fecha((version.metadatos or {}).get("fecha_corte"))
    except (TypeError, ValueError):
        return None


def motivo_no_activable(version):
    """Por qué no se puede activar la versión (None si se puede)."""
    if version.est_registro != "A":
        return "Esta versión está oculta y no se puede activar."
    if fecha_corte(version) is None:
        return ("Esta versión no tiene fecha de corte: solo se evalúa en "
                "sombra y no se puede activar.")
    return None


def es_alternativo(version):
    """Modelo alternativo de otra versión (p. ej. v2-xgb de v2): mismo
    dataset y fecha de corte, pero no es el elegido por la regla de
    selección del entrenamiento."""
    return bool((version.metadatos or {}).get("alternativa_de"))


def seleccionables():
    """Versiones con las que se puede hacer un análisis: visibles y con
    fecha de corte (Random Forest y XGBoost del dataset v2)."""
    return [v for v in VersionModelo.objects.filter(est_registro="A")
            .order_by("id") if fecha_corte(v) is not None]


def recomendada():
    """La versión con la fecha de corte más reciente; si varias la comparten
    (Random Forest y XGBoost de v2), la principal (no alternativa) y, a
    igualdad, la última registrada."""
    return max(seleccionables(), default=None,
               key=lambda v: (fecha_corte(v), not es_alternativo(v),
                              v.registrado_en, v.id))


def modelo_lote():
    """Modelo del análisis en lote y referencia de la evaluación en sombra y
    de la comparación: siempre el elegido por la regla de selección del
    entrenamiento (no el alternativo) de la fecha de corte más reciente, es
    decir Random Forest, aunque un administrador cambie el principal de la
    plataforma (que solo decide el modelo por defecto de cada análisis).
    Así la validación prospectiva no mezcla modelos."""
    from riesgo.services.predictor import SinModeloActivo

    version = recomendada()
    if version is None:
        raise SinModeloActivo()
    return version


def estado():
    """Modelo activo frente al recomendado (aviso del panel del
    administrador). Avisa si no hay modelo activo, si el activo no tiene
    fecha de corte (v1) o si es de una fecha de corte anterior a la más
    reciente. Elegir XGBoost como principal, con la misma fecha de corte,
    no es un error y no avisa."""
    activo = VersionModelo.objects.filter(activo=True).first()
    referencia = recomendada()
    corte_activo = fecha_corte(activo) if activo else None
    return {
        "activo": activo.version if activo else None,
        "recomendado": referencia.version if referencia else None,
        "aviso": referencia is not None and (
            corte_activo is None or corte_activo < fecha_corte(referencia)),
        # Sin fecha de corte el análisis en lote se niega a correr.
        "activo_sin_corte": activo is not None and corte_activo is None,
    }


def registrar_activacion(version, anterior, usuario=None, origen="plataforma"):
    return ActivacionModelo.objects.create(
        version_modelo=version,
        version_anterior=anterior if anterior and anterior.id != version.id
        else None,
        usuario=usuario,
        nombre_usuario=(usuario.get_username() if usuario
                        else auditoria.usuario_actual())[:150],
        origen=origen)


def activar(version, usuario, confirmacion):
    """Activa `version` desde la pantalla Modelos (NoActivable si no se
    puede)."""
    motivo = motivo_no_activable(version)
    if motivo:
        raise NoActivable(motivo, "version_no_activable")
    if version.activo:
        raise NoActivable("Esta versión ya es la activa.", "ya_activa")
    if (confirmacion or "").strip() != version.version:
        raise NoActivable(
            f"Para confirmar, escriba el nombre de la versión "
            f"({version.version}).", "confirmacion_incorrecta")
    with transaction.atomic():
        anterior = (VersionModelo.objects.select_for_update()
                    .filter(activo=True).first())
        VersionModelo.objects.update(activo=False)
        version.activo = True
        version.save(update_fields=["activo"])
        return registrar_activacion(version, anterior, usuario)


# --- Modelo de cada análisis ------------------------------------------------

COMPARAR = "comparar"


class ModeloNoDisponible(Exception):
    pass


def por_codigo(codigo):
    """Versión seleccionable con ese código (p. ej. «v2» o «v2-xgb»)."""
    for version in seleccionables():
        if version.version == codigo:
            return version
    raise ModeloNoDisponible(
        f"El modelo «{codigo}» no está disponible. Elija Random Forest o "
        "XGBoost.")


def versiones_para(codigo):
    """Modelos con los que se hace un análisis nuevo.

    - vacío: el principal (el activo);
    - «comparar»: todos los seleccionables, el principal primero;
    - un código: solo esa versión.
    """
    from riesgo.services.predictor import modelo_activo

    if not codigo:
        return [modelo_activo()]
    if codigo == COMPARAR:
        opciones = sorted(seleccionables(), key=lambda v: (not v.activo, v.id))
        if len(opciones) < 2:
            raise ModeloNoDisponible("No hay dos modelos para comparar.")
        return opciones
    return [por_codigo(codigo)]
