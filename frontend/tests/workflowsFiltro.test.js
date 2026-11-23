// Workflows del administrador: por defecto solo repositorios activos.
import assert from "node:assert/strict";
import { test } from "node:test";
import { enAlcance, inactivos, textoAlcance } from "../src/workflowsFiltro.js";

const lista = [
  { id: 1, repositorio_activo: true },
  { id: 2, repositorio_activo: false },
  { id: 3, repositorio_activo: true },
];

test("por defecto solo los workflows de repositorios activos", () => {
  assert.deepEqual(enAlcance(lista, false).map((w) => w.id), [1, 3]);
});

test("con el filtro se ven también los de repositorios inactivos", () => {
  assert.deepEqual(enAlcance(lista, true).map((w) => w.id), [1, 2, 3]);
  assert.equal(inactivos(lista), 1);
  assert.deepEqual(enAlcance(null, false), []);
});

test("los contadores dicen a qué filtro corresponden", () => {
  assert.equal(textoAlcance(false), "solo repositorios activos");
  assert.equal(textoAlcance(true), "repositorios activos e inactivos");
});
