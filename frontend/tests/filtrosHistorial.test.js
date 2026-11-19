// Consulta de los filtros de historiales y pendientes (los aplica el backend).
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  consultaHistorial, errorRango, escribirFecha, fechaDesdeTexto, FILTROS_INICIALES, hayFiltros, NIVELES_FILTRO, textoFecha,
} from "../src/filtrosHistorial.js";

test("sin filtros no se envían parámetros (el backend ordena del más reciente al más antiguo)", () => {
  assert.equal(consultaHistorial(FILTROS_INICIALES), "");
  assert.equal(consultaHistorial(), "");
  assert.equal(consultaHistorial({ ...FILTROS_INICIALES, orden: "decision" }), "");
});

test("rango de fechas, nivel, origen y orden", () => {
  assert.equal(
    consultaHistorial({ desde: "2026-11-01", hasta: "2026-11-18", nivel: "alto", orden: "antiguo" }),
    "?desde=2026-11-01&hasta=2026-11-18&nivel=alto&orden=antiguo",
  );
  assert.equal(consultaHistorial({ hasta: "2026-11-18", origen: "lote" }), "?hasta=2026-11-18&origen=lote");
  assert.equal(consultaHistorial({ nivel: "todos", origen: "todos" }), "");
});

test("pendientes: solo los análisis sin decisión", () => {
  assert.equal(consultaHistorial({ ...FILTROS_INICIALES, nivel: "medio", sinDecision: true }), "?nivel=medio&sin_decision=1");
});

test("el desplegable de nivel ofrece Todos, Bajo, Medio y Alto; por defecto Todos", () => {
  assert.deepEqual(NIVELES_FILTRO.map(([, texto]) => texto), ["Todos", "Bajo", "Medio", "Alto"]);
  assert.equal(FILTROS_INICIALES.nivel, "todos");
  assert.equal(FILTROS_INICIALES.orden, "reciente");
});

test("rango no válido", () => {
  assert.equal(errorRango("", ""), "");
  assert.equal(errorRango("2026-11-01", "2026-11-01"), "");
  assert.match(errorRango("2026-11-18", "2026-11-01"), /posterior/);
  assert.match(errorRango("18/11/2026", ""), /dd\/mm\/aaaa/);
});

test("fechas en pantalla dd/mm/aaaa ↔ AAAA-MM-DD para el backend", () => {
  assert.equal(textoFecha("2026-11-18"), "18/11/2026");
  assert.equal(textoFecha(""), "");
  assert.equal(fechaDesdeTexto("18/11/2026"), "2026-11-18");
  assert.equal(fechaDesdeTexto("1/2/2026"), "2026-02-01");
  assert.equal(fechaDesdeTexto(""), "");
  for (const malo of ["31/02/2026", "18/13/2026", "18/11/26", "11-18-2026", "00/11/2026"]) {
    assert.equal(fechaDesdeTexto(malo), null, malo);
  }
});

test("al escribir se ponen las barras solas", () => {
  assert.equal(escribirFecha("18"), "18");
  assert.equal(escribirFecha("1811"), "18/11");
  assert.equal(escribirFecha("18112026"), "18/11/2026");
  assert.equal(escribirFecha("18/11/2026x9"), "18/11/2026");
});

test("hay filtros activos", () => {
  assert.equal(hayFiltros(FILTROS_INICIALES), false);
  assert.equal(hayFiltros({ ...FILTROS_INICIALES, desde: "2026-11-01" }), true);
  assert.equal(hayFiltros({ ...FILTROS_INICIALES, nivel: "bajo" }), true);
  // El origen solo cuenta si cambia respecto del inicial del administrador.
  assert.equal(hayFiltros({ ...FILTROS_INICIALES, origen: "interactivo" }, "interactivo"), false);
  assert.equal(hayFiltros({ ...FILTROS_INICIALES, origen: "lote" }, "interactivo"), true);
});
