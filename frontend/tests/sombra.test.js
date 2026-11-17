// Comparación en sombra de v2 con v1 y v1.1 (mismas ejecuciones).
import assert from "node:assert/strict";
import { test } from "node:test";
import { formatoIntervalo, resultadoReferencia, textoComparacion } from "../src/sombra.js";

const v1 = {
  version: "v1",
  diferencia_con_referencia: { brier: { valor: 0.0075, ic95: [0.0025, 0.0135] }, pr_auc: { valor: -0.09, ic95: [-0.15, -0.04] } },
};
const v11 = {
  version: "v1.1",
  diferencia_con_referencia: { brier: { valor: 0.0026, ic95: [-0.0018, 0.0073] }, pr_auc: { valor: -0.01, ic95: [-0.05, 0.03] } },
};

test("Brier mayor y PR-AUC menor en la versión en sombra: la referencia es mejor", () => {
  assert.equal(resultadoReferencia(v1, "brier"), "mejor");
  assert.equal(resultadoReferencia(v1, "pr_auc"), "mejor");
});

test("si el IC de la diferencia incluye el 0 no hay diferencia concluyente", () => {
  assert.equal(resultadoReferencia(v11, "brier"), "sin_diferencia");
  assert.equal(resultadoReferencia(v11, "pr_auc"), "sin_diferencia");
  assert.equal(resultadoReferencia({ version: "v2" }, "brier"), "sin_diferencia");
});

test("la referencia peor cuando la versión en sombra gana", () => {
  const mejor = { diferencia_con_referencia: { brier: { ic95: [-0.02, -0.01] }, pr_auc: { ic95: [0.01, 0.05] } } };
  assert.equal(resultadoReferencia(mejor, "brier"), "peor");
  assert.equal(resultadoReferencia(mejor, "pr_auc"), "peor");
});

test("textos", () => {
  assert.equal(formatoIntervalo([0.0684, 0.1005]), "[0.068 – 0.101]");
  assert.equal(formatoIntervalo(null), "—");
  assert.match(textoComparacion("v2", v1), /^v2 frente a v1: Brier mejor .*PR-AUC mejor/);
  assert.match(textoComparacion("v2", v11), /sin diferencia concluyente/);
});

test("confirmación antes de cambiar el modelo activo", async () => {
  const { textoConfirmarActivacion } = await import("../src/sombra.js");
  assert.equal(
    textoConfirmarActivacion({ version: "v1", nombre_modelo: "Árbol de decisión" }, { version: "v2", nombre_modelo: "Random Forest" }),
    "¿Activar v1 (Árbol de decisión)? Todos los análisis nuevos y las pasadas del lote usarán este modelo en lugar de v2 (Random Forest).",
  );
});
