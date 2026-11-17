// Resultado real: sin botón, seguimiento automático en la página.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { DURACION_SEGUIMIENTO, siguientePaso } from "../src/seguimiento.js";

test("enlazado en cuanto la API devuelve el análisis con su ejecución real", () => {
  assert.equal(siguientePaso({ id: 1, ejecucion_real: { run_id: 7 } }, 0), "enlazado");
});

test("pendiente: sigue consultando hasta agotar la duración del seguimiento", () => {
  assert.equal(siguientePaso({ estado: "pendiente" }, 0), "seguir");
  assert.equal(siguientePaso({ estado: "pendiente" }, DURACION_SEGUIMIENTO - 1), "seguir");
  assert.equal(siguientePaso({ estado: "pendiente" }, DURACION_SEGUIMIENTO), "detener");
});

test("sin resultado real la vista no muestra el apartado ni el botón", () => {
  const vista = readFileSync(new URL("../src/components/Resultado.jsx", import.meta.url), "utf8");
  assert.ok(!vista.includes("Verificar resultado real"));
  assert.ok(!vista.includes("se verifica automáticamente"));
  assert.ok(vista.includes("if (!real) return null;"));
});
