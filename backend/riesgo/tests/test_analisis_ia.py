import json
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, override_settings
from google.genai import errors

from riesgo.services import analisis_ia

VARIABLES = {"wf_ultimo_fallo": 1, "wf_tasa_fallo_prev": 0.5,
             "retraso_commit_run_min": float("nan")}
FACTORES = [{"variable": "wf_ultimo_fallo", "descripcion": "",
             "valor": 1, "contribucion": 0.4, "efecto": "aumenta"}]
RESULTADO = {
    "probabilidad": 0.42, "nivel": "alto", "factores": FACTORES,
    "version": SimpleNamespace(version="v1.1", metadatos={
        "limites_riesgo": {"medio": 0.1, "alto": 0.3}}),
}
CONTEXTO = {
    "commit": {"sha": "a" * 40, "stats": {"additions": 3, "deletions": 1},
               "commit": {"message": "fix: corrige secretos",
                          "author": {"name": "Persona Real"}},
               "files": [{"filename": ".github/workflows/deploy.yml",
                          "status": "modified", "changes": 4}]},
    "previas": [{"run_started_at": "2026-10-01T10:00:00Z",
                 "conclusion": "failure", "head_branch": "main",
                 "event": "push"}],
}


def _analizar():
    return analisis_ia.analizar(VARIABLES, RESULTADO, CONTEXTO, "acme/tienda",
                                ".github/workflows/deploy.yml", "main", "push")


def _cliente(respuesta=None, error=None):
    cliente = mock.Mock()
    generar = cliente.return_value.models.generate_content
    if error is not None:
        generar.side_effect = error
    else:
        generar.return_value = respuesta
    return cliente


@override_settings(GEMINI_API_KEY="clave", GEMINI_MODELO="gemini-3.8-flash")
class AnalisisIATest(SimpleTestCase):

    @override_settings(GEMINI_API_KEY="")
    def test_sin_clave_usa_reglas(self):
        with mock.patch.object(analisis_ia.genai, "Client") as cliente:
            analisis, recomendaciones = _analizar()
        cliente.assert_not_called()
        self.assertEqual(analisis["origen"], "reglas")
        self.assertIsNone(analisis["error"])
        self.assertEqual(recomendaciones[0]["codigo"],
                         "R02_ULTIMA_EJECUCION_FALLIDA")

    def test_usa_el_analisis_de_gemini(self):
        respuesta = SimpleNamespace(
            model_version="gemini-3.8-flash", candidates=[],
            parsed=analisis_ia.Analisis(
                resumen="La última ejecución falló.",
                recomendaciones=[analisis_ia.Recomendacion(
                    variable="wf_ultimo_fallo", texto="Revise el fallo.")]))
        cliente = _cliente(respuesta)
        with mock.patch.object(analisis_ia.genai, "Client", cliente):
            analisis, recomendaciones = _analizar()
        self.assertEqual(analisis, {"origen": "ia",
                                    "modelo": "gemini-3.8-flash",
                                    "resumen": "La última ejecución falló.",
                                    "error": None})
        self.assertEqual(recomendaciones, [{"codigo": "IA01",
                                            "variable": "wf_ultimo_fallo",
                                            "texto": "Revise el fallo."}])
        enviado = cliente.return_value.models.generate_content.call_args
        contenido = enviado.kwargs["contents"]
        datos = json.loads(contenido)
        self.assertEqual(datos["modelo"]["nivel"], "alto")
        self.assertIsNone(datos["variables"]["retraso_commit_run_min"])
        # El nombre del autor no sale de la plataforma.
        self.assertNotIn("Persona Real", contenido)

    def test_error_de_api_usa_reglas(self):
        error = errors.ServerError(503, {"error": {"message": "ocupado"}})
        with mock.patch.object(analisis_ia.genai, "Client",
                               _cliente(error=error)):
            analisis, recomendaciones = _analizar()
        self.assertEqual(analisis["origen"], "reglas")
        self.assertEqual(analisis["error"], "ServerError")
        self.assertTrue(recomendaciones[0]["codigo"].startswith("R"))

    def test_respuesta_bloqueada_usa_reglas(self):
        respuesta = SimpleNamespace(
            model_version="x", parsed=None,
            candidates=[SimpleNamespace(finish_reason="SAFETY")])
        with mock.patch.object(analisis_ia.genai, "Client",
                               _cliente(respuesta)):
            analisis, _ = _analizar()
        self.assertEqual(analisis, {"origen": "reglas", "modelo": None,
                                    "resumen": "", "error": "SAFETY"})
