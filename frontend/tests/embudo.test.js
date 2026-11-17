// Embudo del desarrollador con los análisis de demostración.
import assert from "node:assert/strict";
import { test } from "node:test";
import { pasosEmbudo, textoDemostracion } from "../src/embudo.js";

const real = (ejecucion_real = null) => ({ ejecucion_real });
const reales = [real(), real(), real({ y: 0 })];
const demo = [real({ y: 1 }), real({ y: 0 }), real({ y: null }), real()];

test("sin demostración, solo los reales", () => {
  const p = pasosEmbudo(reales);
  assert.deepEqual([p.total, p.verificadas, p.evaluables, p.noCompletados], [3, 1, 1, 0]);
  assert.equal(textoDemostracion(p), "");
});

test("suma los análisis de demostración y los cuenta aparte", () => {
  const p = pasosEmbudo(reales, demo);
  assert.deepEqual([p.total, p.verificadas, p.evaluables, p.noCompletados], [7, 4, 3, 1]);
  assert.equal(p.demostracion, 4);
  assert.equal(p.demostracionVerificadas, 3);
  assert.equal(
    textoDemostracion(p),
    "Incluye 4 análisis del repositorio de demostración (3 con resultado real); no cuentan en las métricas del modelo.",
  );
});
