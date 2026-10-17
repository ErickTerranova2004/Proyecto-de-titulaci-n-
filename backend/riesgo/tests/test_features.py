import math
from datetime import datetime, timezone

from django.test import SimpleTestCase

from riesgo.logging_filters import ocultar
from riesgo.services.features import (variables_commit, variables_repositorio,
                                      variables_workflow)
from riesgo.services.recomendaciones import GENERICA, recomendar

AHORA = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)


def run(dia, conclusion, workflow_id=1, minutos=10):
    return {"status": "completed", "conclusion": conclusion,
            "workflow_id": workflow_id,
            "run_started_at": f"2026-10-{dia:02d}T10:00:00Z",
            "updated_at": f"2026-10-{dia:02d}T10:{minutos:02d}:00Z"}


class VariablesWorkflowTest(SimpleTestCase):
    def test_usa_solo_las_cuatro_previas_mas_recientes(self):
        runs = [run(d, "failure" if d == 9 else "success")
                for d in range(5, 11)]
        v = variables_workflow(runs, AHORA)
        self.assertEqual(v["wf_n_prev"], 4)
        self.assertAlmostEqual(v["wf_tasa_fallo_prev"], 0.25)
        self.assertEqual(v["wf_ultimo_fallo"], 0.0)
        self.assertAlmostEqual(v["wf_duracion_media_prev_min"], 10)

    def test_ignora_ejecuciones_futuras_o_en_curso(self):
        futura = run(20, "failure")
        en_curso = dict(run(14, "failure"), status="in_progress")
        v = variables_workflow([futura, en_curso], AHORA)
        self.assertEqual(v["wf_n_prev"], 0)
        self.assertTrue(math.isnan(v["wf_tasa_fallo_prev"]))

    def test_historial_del_repositorio(self):
        runs = [run(d, "failure", workflow_id=w)
                for w in (1, 2) for d in (10, 11)]
        v = variables_repositorio(runs, AHORA)
        self.assertEqual(v["repo_n_prev"], 4)
        self.assertEqual(v["repo_n_workflows_prev"], 2)
        self.assertEqual(v["repo_tasa_fallo_prev"], 1.0)


class VariablesCommitTest(SimpleTestCase):
    def test_mensaje_y_rama(self):
        v = variables_commit("Bump lodash from 1 to 2\n\nbody", "dependabot",
                             "main", "push", AHORA,
                             datetime(2026, 10, 15, 11, 0,
                                      tzinfo=timezone.utc))
        self.assertEqual(v["msg_deps"], 1)
        self.assertEqual(v["autor_bot"], 1)
        self.assertEqual(v["rama_principal"], 1)
        self.assertEqual(v["msg_lineas"], 3)
        self.assertEqual(v["retraso_commit_run_min"], 60)
        self.assertEqual(v["tiene_pr"], 0)


class SeguridadYReglasTest(SimpleTestCase):
    def test_oculta_tokens(self):
        texto = ocultar("Authorization: Bearer ghp_" + "a" * 36)
        self.assertNotIn("a" * 36, texto)

    def test_recomendacion_solo_si_el_factor_aumenta_el_riesgo(self):
        variables = {"wf_ultimo_fallo": 1}
        reduce = [{"variable": "wf_ultimo_fallo", "efecto": "reduce"}]
        aumenta = [{"variable": "wf_ultimo_fallo", "efecto": "aumenta"}]
        self.assertEqual(recomendar(variables, reduce), [GENERICA])
        recomendaciones = recomendar(variables, aumenta)
        self.assertEqual(recomendaciones[0]["codigo"],
                         "R02_ULTIMA_EJECUCION_FALLIDA")
        self.assertEqual(recomendaciones[0]["variable"], "wf_ultimo_fallo")
