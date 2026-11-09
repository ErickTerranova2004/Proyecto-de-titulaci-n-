from django.test import SimpleTestCase

from riesgo.models import PATRON_DESPLIEGUE, EjecucionWorkflow
from riesgo.services.etiquetado import etiquetar_ejecucion


def job(id_, nombre, pasos, conclusion="success", inicio="2026-10-15T10:00"):
    return {"id": id_, "name": nombre, "conclusion": conclusion,
            "started_at": inicio,
            "steps": [{"number": i + 1, "name": n, "conclusion": c}
                      for i, (n, c) in enumerate(pasos)]}


class ReglaEtiquetadoTest(SimpleTestCase):
    def etiquetar(self, conclusion, jobs):
        return etiquetar_ejecucion(conclusion, jobs, PATRON_DESPLIEGUE)

    def test_exito_con_despliegue(self):
        r = self.etiquetar("success", [job(1, "deploy", [
            ("Build", "success"), ("Deploy to ECS", "success")])])
        self.assertEqual(r["etiqueta"], "despliegue_completado")
        self.assertTrue(r["despliegue_ejecutado"])

    def test_exito_sin_despliegue_se_excluye(self):
        r = self.etiquetar("success", [job(1, "build", [
            ("Build", "success"), ("Deploy to ECS", "skipped")])])
        self.assertEqual(r["etiqueta"], "excluida_sin_intento")

    def test_fallo_antes_del_despliegue(self):
        r = self.etiquetar("failure", [job(1, "deploy", [
            ("Build", "failure"), ("Deploy to ECS", "skipped")], "failure")])
        self.assertEqual(r["etiqueta"], "despliegue_no_completado")
        self.assertEqual(r["subtipo_etiqueta"], "antes_del_despliegue")
        self.assertEqual(r["paso_fallido"], "deploy / Build")

    def test_fallo_en_el_paso_de_despliegue(self):
        r = self.etiquetar("failure", [job(1, "deploy", [
            ("Build", "success"), ("Deploy to ECS", "failure")], "failure")])
        self.assertEqual(r["subtipo_etiqueta"], "en_paso_de_despliegue")
        self.assertEqual(r["paso_fallido"], "deploy / Deploy to ECS")

    def test_fallo_posterior_en_el_mismo_job(self):
        r = self.etiquetar("failure", [job(1, "deploy", [
            ("Deploy to ECS", "success"), ("Smoke test", "failure")],
            "failure")])
        self.assertEqual(r["subtipo_etiqueta"], "posterior_mismo_job")

    def test_fallo_en_otro_job_con_despliegue_completado_es_ambiguo(self):
        # Caso novu: el despliegue terminó y falló un job de pruebas.
        r = self.etiquetar("failure", [
            job(1, "deploy", [("Deploy to ECS", "success")]),
            job(2, "e2e", [("Run tests", "failure")], "failure",
                "2026-10-15T10:05")])
        self.assertEqual(r["etiqueta"], "excluida_ambigua")
        self.assertEqual(r["paso_fallido"], "e2e / Run tests")

    def test_cancelada_se_excluye(self):
        r = self.etiquetar("cancelled", [])
        self.assertEqual(r["etiqueta"], "excluida_otro_resultado")

    def test_omitida_y_pendiente_de_aprobacion_se_excluyen(self):
        for conclusion in ("skipped", "action_required", "startup_failure"):
            with self.subTest(conclusion=conclusion):
                r = self.etiquetar(conclusion, [job(1, "deploy", [
                    ("Deploy to ECS", "skipped")], conclusion)])
                self.assertEqual(r["etiqueta"], "excluida_otro_resultado")

    def test_fallo_sin_ningun_job_se_excluye(self):
        # El workflow no llegó a arrancar (YAML inválido, startup_failure):
        # no es un intento de despliegue, no cuenta como y = 1.
        r = self.etiquetar("failure", [])
        self.assertEqual(r["etiqueta"], "excluida_sin_jobs")
        self.assertEqual(r["subtipo_etiqueta"], "")
        self.assertFalse(r["despliegue_ejecutado"])


class VariableObjetivoTest(SimpleTestCase):
    """La `y` del modelo para cada etiqueta (fase2_variable_objetivo.md)."""

    def y(self, conclusion, jobs):
        etiqueta = etiquetar_ejecucion(conclusion, jobs,
                                       PATRON_DESPLIEGUE)["etiqueta"]
        return EjecucionWorkflow(etiqueta=etiqueta).y

    def test_despliegue_completado_es_y0(self):
        self.assertEqual(self.y("success", [job(1, "deploy", [
            ("Deploy to ECS", "success")])]), 0)

    def test_fallo_antes_del_despliegue_es_y1(self):
        self.assertEqual(self.y("failure", [job(1, "deploy", [
            ("Build", "failure"), ("Deploy to ECS", "skipped")],
            "failure")]), 1)

    def test_excluidas_no_tienen_y(self):
        casos = {"sin jobs": ("failure", []),
                 "cancelada": ("cancelled", []),
                 "omitida": ("skipped", []),
                 "pendiente de aprobación": ("action_required", [])}
        for nombre, (conclusion, jobs) in casos.items():
            with self.subTest(nombre):
                self.assertIsNone(self.y(conclusion, jobs))
