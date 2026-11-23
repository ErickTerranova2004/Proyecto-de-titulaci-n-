// Pruebas de la relación entre la recomendación automática y la decisión del
// líder técnico (node --test).
import assert from "node:assert/strict";
import { test } from "node:test";
import { aceptaRecomendacion, decisionRecomendada, RECOMENDACIONES } from "../src/recomendacion.js";

test("cada recomendación tiene su texto y su decisión equivalente", () => {
  assert.equal(RECOMENDACIONES.permitir, "Permitir el despliegue");
  assert.equal(RECOMENDACIONES.solicitar_revision, "Solicitar revisión previa");
  assert.equal(decisionRecomendada("permitir"), "autorizar");
  assert.equal(decisionRecomendada("solicitar_revision"), "solicitar_revision");
});

test("aceptar o cambiar la recomendación", () => {
  assert.equal(aceptaRecomendacion("solicitar_revision", "solicitar_revision"), true);
  assert.equal(aceptaRecomendacion("solicitar_revision", "autorizar"), false);
  assert.equal(aceptaRecomendacion("permitir", "autorizar"), true);
  assert.equal(aceptaRecomendacion("permitir", "posponer"), false);
});

test("sin recomendación (análisis anteriores) no hay aceptación que mostrar", () => {
  assert.equal(decisionRecomendada(""), "");
  assert.equal(decisionRecomendada(undefined), "");
  assert.equal(aceptaRecomendacion("", "autorizar"), null);
  assert.equal(aceptaRecomendacion("permitir", ""), null);
});
