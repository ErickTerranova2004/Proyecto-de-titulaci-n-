// Historial ordenado por última actividad (decisión o creación).
import assert from "node:assert/strict";
import { test } from "node:test";
import { ordenarPorActividad, ultimaActividad } from "../src/ordenHistorial.js";

const a = (id, creada_en, decisiones = []) => ({ id, creada_en, decisiones: decisiones.map((d) => ({ creada_en: d })) });

test("un análisis antiguo con una decisión nueva pasa al primer lugar", () => {
  const lista = [
    a(3, "2026-11-17T16:35:00Z"),
    a(2, "2026-11-17T16:22:00Z"),
    a(1, "2026-11-17T15:21:00Z", ["2026-11-17T16:45:00Z"]),
  ];
  assert.deepEqual(ordenarPorActividad(lista).map((p) => p.id), [1, 3, 2]);
});

test("sin decisiones, del más reciente al más antiguo", () => {
  const lista = [a(1, "2026-11-10T10:00:00Z"), a(2, "2026-11-12T10:00:00Z")];
  assert.deepEqual(ordenarPorActividad(lista).map((p) => p.id), [2, 1]);
  assert.equal(ultimaActividad(a(5, "2026-11-10T10:00:00Z", ["2026-11-11T10:00:00Z"])),
    new Date("2026-11-11T10:00:00Z").getTime());
  assert.deepEqual(ordenarPorActividad(null), []);
});
