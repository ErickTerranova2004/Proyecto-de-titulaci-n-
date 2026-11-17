// Historial: primero los análisis con decisión, luego los demás.
import assert from "node:assert/strict";
import { test } from "node:test";
import { ordenarPorActividad, ultimaDecision } from "../src/ordenHistorial.js";

const a = (id, creada_en, decisiones = []) => ({ id, creada_en, decisiones: decisiones.map((d) => ({ creada_en: d })) });

test("los análisis con decisión van primero aunque sean antiguos", () => {
  const lista = [
    a(10, "2026-11-17T16:35:00Z"),
    a(9, "2026-11-17T16:22:00Z"),
    a(2, "2026-10-22T19:10:00Z", ["2026-10-23T18:54:00Z"]),
    a(7, "2026-10-23T23:51:00Z", ["2026-10-29T14:54:00Z"]),
  ];
  assert.deepEqual(ordenarPorActividad(lista).map((p) => p.id), [7, 2, 10, 9]);
});

test("entre los que tienen decisión, la decisión más reciente primero", () => {
  const lista = [
    a(1, "2026-11-01T10:00:00Z", ["2026-11-02T10:00:00Z"]),
    a(2, "2026-10-01T10:00:00Z", ["2026-10-02T10:00:00Z", "2026-11-05T10:00:00Z"]),
  ];
  assert.deepEqual(ordenarPorActividad(lista).map((p) => p.id), [2, 1]);
  assert.equal(ultimaDecision(lista[1]), new Date("2026-11-05T10:00:00Z").getTime());
});

test("sin decisiones, del más reciente al más antiguo", () => {
  assert.deepEqual(ordenarPorActividad([a(1, "2026-11-10T10:00:00Z"), a(2, "2026-11-12T10:00:00Z")]).map((p) => p.id), [2, 1]);
  assert.deepEqual(ordenarPorActividad(null), []);
});
