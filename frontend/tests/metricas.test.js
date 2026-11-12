// Métricas de v1/v1.1 (prueba temporal) y v2 (validación por repositorio).
// v2 activo dejaba la interfaz en blanco: no tiene `metricas_prueba`.
import assert from "node:assert/strict";
import { test } from "node:test";
import { formatoMetrica, metricasModelo } from "../src/metricas.js";

test("v1.1: métricas de la partición temporal de prueba", () => {
  const m = metricasModelo({ metricas_prueba: { "PR-AUC": 0.677, Precision: 0.5, Recall: 0.6, Brier: 0.1 } });
  assert.equal(m.origen, "prueba temporal");
  assert.equal(m.valores["PR-AUC"], 0.677);
  assert.equal(m.valores.Recall, 0.6);
  assert.equal(m.valores.F1, null);
});

test("v2: métricas de validación del modelo elegido, con nombres normalizados", () => {
  const m = metricasModelo({
    modelo: "Random Forest",
    metricas_validacion: {
      XGBoost: { "PR-AUC": 0.348 },
      "Random Forest": { "PR-AUC": 0.415, "Recall y=1": 0.536, Precisión: 0.517, F1: 0.526, Brier: 0.067 },
    },
  });
  assert.equal(m.origen, "validación por repositorio");
  assert.equal(m.valores["PR-AUC"], 0.415);
  assert.equal(m.valores.Recall, 0.536);
  assert.equal(m.valores.Precision, 0.517);
});

test("sin métricas no falla", () => {
  for (const meta of [undefined, {}, { metricas_validacion: {} }]) {
    const m = metricasModelo(meta);
    assert.equal(m.origen, null);
    assert.equal(formatoMetrica(m.valores["PR-AUC"]), "—");
  }
});
