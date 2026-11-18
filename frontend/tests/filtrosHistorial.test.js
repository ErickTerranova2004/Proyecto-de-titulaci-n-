// Consulta de los filtros de historiales y pendientes (los aplica el backend).
import assert from "node:assert/strict";
import { test } from "node:test";
import { consultaHistorial, errorRango, FILTROS_INICIALES, hayFiltros, NIVELES_FILTRO } from "../src/filtrosHistorial.js";

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
  assert.match(errorRango("18/11/2026", ""), /AAAA-MM-DD/);
});

test("hay filtros activos", () => {
  assert.equal(hayFiltros(FILTROS_INICIALES), false);
  assert.equal(hayFiltros({ ...FILTROS_INICIALES, desde: "2026-11-01" }), true);
  assert.equal(hayFiltros({ ...FILTROS_INICIALES, nivel: "bajo" }), true);
  // El origen solo cuenta si cambia respecto del inicial del administrador.
  assert.equal(hayFiltros({ ...FILTROS_INICIALES, origen: "interactivo" }, "interactivo"), false);
  assert.equal(hayFiltros({ ...FILTROS_INICIALES, origen: "lote" }, "interactivo"), true);
});
