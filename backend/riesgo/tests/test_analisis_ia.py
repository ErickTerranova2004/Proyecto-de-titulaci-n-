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


@override_settings(IA_PROVEEDOR="gemini", GEMINI_API_KEY="clave",
                   GEMINI_MODELO="gemini-3.8-flash")
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

    def test_tiempo_agotado_usa_reglas(self):
        # Gemini tardó más de IA_TIMEOUT: antes daba Error 500 al analizar.
        import httpx
        with mock.patch.object(analisis_ia.genai, "Client",
                               _cliente(error=httpx.ReadTimeout("timed out"))):
            analisis, recomendaciones = _analizar()
        self.assertEqual(analisis["origen"], "reglas")
        self.assertEqual(analisis["error"], "ReadTimeout")
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


# --- Claude (proveedor por defecto) ------------------------------------------

import anthropic  # noqa: E402
import httpx2  # noqa: E402
from django.conf import settings  # noqa: E402
from django.test import TestCase  # noqa: E402

from riesgo.tests import test_api  # noqa: E402

PETICION = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def _claude(respuesta=None, error=None):
    cliente = mock.Mock()
    parse = cliente.return_value.messages.parse
    if error is not None:
        parse.side_effect = error
    else:
        parse.return_value = respuesta
    return cliente


def _respuesta_claude(parsed=None, stop_reason="end_turn"):
    return SimpleNamespace(
        parsed_output=parsed, stop_reason=stop_reason,
        model="claude-haiku-5-5",
        usage=SimpleNamespace(input_tokens=1200, output_tokens=150))


ANALISIS = analisis_ia.Analisis(
    resumen="La última ejecución falló.",
    recomendaciones=[analisis_ia.Recomendacion(
        variable="wf_ultimo_fallo", texto="Revise el fallo anterior."),
        analisis_ia.Recomendacion(variable=None, texto="Revise el YAML.")])


class ProveedorEnPruebasTest(SimpleTestCase):
    def test_las_pruebas_nunca_usan_una_api_de_pago_por_defecto(self):
        self.assertEqual(settings.IA_PROVEEDOR, "reglas")


@override_settings(IA_PROVEEDOR="claude", CLAUDE_API_KEY="clave-claude",
                   CLAUDE_MODELO="claude-haiku-5-5", IA_TIMEOUT=30,
                   GEMINI_API_KEY="clave-gemini")
class ClaudeTest(SimpleTestCase):

    def test_redacta_con_claude_y_mismo_formato(self):
        cliente = _claude(_respuesta_claude(ANALISIS))
        with mock.patch.object(analisis_ia.anthropic, "Anthropic", cliente), \
                mock.patch.object(analisis_ia.genai, "Client") as gemini:
            analisis, recomendaciones = _analizar()
        gemini.assert_not_called()
        uso = analisis.pop("uso")
        self.assertEqual(analisis, {"origen": "ia", "modelo": "claude-haiku-5-5",
                                    "resumen": "La última ejecución falló.",
                                    "error": None})
        # El consumo de la llamada se guarda con el análisis.
        self.assertEqual((uso["tokens_entrada"], uso["tokens_salida"]),
                         (1200, 150))
        self.assertGreaterEqual(uso["duracion_s"], 0)
        self.assertEqual(recomendaciones, [
            {"codigo": "IA01", "variable": "wf_ultimo_fallo",
             "texto": "Revise el fallo anterior."},
            {"codigo": "IA02", "variable": None, "texto": "Revise el YAML."}])
        # Clave explícita, sin reintentos y con el tiempo máximo configurado.
        cliente.assert_called_once_with(api_key="clave-claude", timeout=30.0,
                                        max_retries=0)
        llamada = cliente.return_value.messages.parse.call_args.kwargs
        self.assertEqual(llamada["model"], "claude-haiku-5-5")
        self.assertIs(llamada["output_format"], analisis_ia.Analisis)
        self.assertEqual(llamada["output_config"], {"effort": "low"})
        self.assertEqual(llamada["system"], analisis_ia.SISTEMA)
        contenido = llamada["messages"][0]["content"]
        datos = json.loads(contenido)
        # Probabilidad y nivel salen del modelo, no de Claude.
        self.assertEqual(datos["modelo"]["nivel"], "alto")
        self.assertEqual(datos["modelo"]["probabilidad_no_completado"], 0.42)
        self.assertNotIn("Persona Real", contenido)

    def test_errores_de_la_api_usan_reglas(self):
        respuesta_500 = httpx2.Response(500, request=PETICION)
        for error, nombre in (
                (anthropic.APITimeoutError(request=PETICION), "APITimeoutError"),
                (anthropic.APIConnectionError(request=PETICION),
                 "APIConnectionError"),
                (anthropic.InternalServerError("caído", response=respuesta_500,
                                               body=None), "InternalServerError"),
                (ValueError("JSON incompleto"), "respuesta_no_valida")):
            with self.subTest(nombre), mock.patch.object(
                    analisis_ia.anthropic, "Anthropic", _claude(error=error)):
                analisis, recomendaciones = _analizar()
            self.assertEqual((analisis["origen"], analisis["error"]),
                             ("reglas", nombre))
            self.assertTrue(recomendaciones[0]["codigo"].startswith("R"))

    def test_rechazo_usa_reglas(self):
        with mock.patch.object(analisis_ia.anthropic, "Anthropic",
                               _claude(_respuesta_claude(None, "refusal"))):
            analisis, _ = _analizar()
        self.assertEqual(analisis, {"origen": "reglas", "modelo": None,
                                    "resumen": "", "error": "refusal"})

    @override_settings(CLAUDE_API_KEY="")
    def test_sin_clave_no_lee_anthropic_api_key(self):
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "otra"}), \
                mock.patch.object(analisis_ia.anthropic, "Anthropic") as cliente:
            analisis, _ = _analizar()
        cliente.assert_not_called()
        self.assertEqual((analisis["origen"], analisis["error"]), ("reglas", None))

    def test_proveedor_configurable(self):
        for proveedor in ("reglas", "desconocido"):
            with self.subTest(proveedor), override_settings(
                    IA_PROVEEDOR=proveedor), mock.patch.object(
                    analisis_ia.anthropic, "Anthropic") as claude, \
                    mock.patch.object(analisis_ia.genai, "Client") as gemini:
                analisis, _ = _analizar()
            claude.assert_not_called()
            gemini.assert_not_called()
            self.assertEqual(analisis["origen"], "reglas")


@override_settings(IA_PROVEEDOR="claude", CLAUDE_API_KEY="clave-claude")
class ClaudeEnLaApiTest(TestCase):
    """«Nuevo análisis» con Claude: 201 siempre, con o sin respuesta."""

    @classmethod
    def setUpTestData(cls):
        cls._usuario = staticmethod(test_api.ApiTest._usuario)
        test_api.ApiTest.setUpTestData.__func__(cls)

    cliente = test_api.ApiTest.cliente

    def predecir(self):
        return test_api.ApiTest.predecir(self, self.dev)

    def test_analisis_redactado_por_claude(self):
        with mock.patch.object(analisis_ia.anthropic, "Anthropic",
                               _claude(_respuesta_claude(ANALISIS))):
            r = self.predecir()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["analisis_ia"]["origen"], "ia")
        self.assertEqual(r.json()["recomendaciones"][0]["codigo"], "IA01")
        self.assertIn(r.json()["nivel"], ("bajo", "medio", "alto"))

    def test_tiempo_agotado_no_da_error_500(self):
        error = anthropic.APITimeoutError(request=PETICION)
        with mock.patch.object(analisis_ia.anthropic, "Anthropic",
                               _claude(error=error)):
            r = self.predecir()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["analisis_ia"]["origen"], "reglas")
        self.assertEqual(r.json()["analisis_ia"]["error"], "APITimeoutError")
