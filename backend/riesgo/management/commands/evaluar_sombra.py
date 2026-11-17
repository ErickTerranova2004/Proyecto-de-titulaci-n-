"""Evaluación en sombra de las versiones no activas (v1, v1.1).

Predice con cada versión no activa las ejecuciones evaluables de la
supervisión del modelo activo que aún no tengan predicción en sombra, con
las variables ya guardadas (sin llamadas a GitHub ni activar ningún
modelo). Ver riesgo/services/sombra.py. También lo hace cada pasada de
analizar_lote al terminar.

    manage.py evaluar_sombra --contar     # solo cuenta (no guarda nada)
    manage.py evaluar_sombra --usuario analisis_lote
"""

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError

from riesgo.auditoria import ComandoAuditado
from riesgo.services import sombra
from riesgo.services.predictor import SinModeloActivo


class Command(ComandoAuditado):
    help = "Predicciones en sombra de las versiones no activas."

    def add_arguments(self, parser):
        parser.add_argument("--contar", action="store_true",
                            help="Solo cuenta (no guarda nada).")
        parser.add_argument("--usuario", default="analisis_lote",
                            help="Usuario al que se atribuyen las predicciones.")

    def usuario_auditoria(self, opciones):
        return opciones["usuario"]

    def handle(self, *args, **opciones):
        usuario = get_user_model().objects.filter(
            username=opciones["usuario"]).first()
        if usuario is None and not opciones["contar"]:
            raise CommandError(f"No existe el usuario {opciones['usuario']}.")
        try:
            resumen = sombra.generar(usuario, contar=opciones["contar"])
        except SinModeloActivo:
            raise CommandError("No hay un modelo activo.")
        verbo = "por crear" if opciones["contar"] else "creadas"
        for version, datos in resumen.items():
            relleno = (f"; rellenadas con la mediana: "
                       f"{', '.join(datos['rellenadas'])}"
                       if datos["rellenadas"] else "")
            self.stdout.write(f"Sombra {version}: {datos['creadas']} {verbo}"
                              f"{relleno}")
