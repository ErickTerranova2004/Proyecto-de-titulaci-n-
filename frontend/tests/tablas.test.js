// Tablas largas: paginación (backend), orden de columnas para 1366 px y
// render de la paginación y del contenedor con barra superior.
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement as h } from "react";
import { renderToString } from "react-dom/server";
import {
  COLUMNAS_ASIGNACIONES, COLUMNAS_PENDIENTES, COLUMNAS_USUARIOS, columnasHistorial, columnasInformes,
} from "../src/columnasTablas.js";
import { consultaPaginada, PAGINACION_INICIAL, paginasVisibles, POR_PAGINA, textoRango } from "../src/paginacion.js";
import { cargarComponente } from "./compilarComponente.js";

const sinMarcas = (html) => html.replace(/<!-- -->/g, "");

test("25 por página por defecto; opciones 25, 50 y 100", () => {
  assert.deepEqual(PAGINACION_INICIAL, { pagina: 1, porPagina: 25 });
  assert.deepEqual(POR_PAGINA, [25, 50, 100]);
});

test("la consulta conserva filtros y orden y añade la página", () => {
  assert.equal(consultaPaginada("", PAGINACION_INICIAL), "?pagina=1&por_pagina=25");
  assert.equal(consultaPaginada("?nivel=alto&orden=antiguo", { pagina: 3, porPagina: 50 }),
    "?nivel=alto&orden=antiguo&pagina=3&por_pagina=50");
  // Reemplaza una página anterior en vez de duplicarla.
  assert.equal(consultaPaginada("?pagina=9&por_pagina=100", { pagina: 2, porPagina: 25 }), "?pagina=2&por_pagina=25");
});

test("botones de página con saltos", () => {
  assert.deepEqual(paginasVisibles(1, 1), [1]);
  assert.deepEqual(paginasVisibles(1, 3), [1, 2, 3]);
  assert.deepEqual(paginasVisibles(5, 20), [1, "…", 4, 5, 6, "…", 20]);
  assert.deepEqual(paginasVisibles(1, 20), [1, 2, "…", 20]);
  assert.deepEqual(paginasVisibles(20, 20), [1, "…", 19, 20]);
  // Un solo número saltado se muestra en vez de «…».
  assert.deepEqual(paginasVisibles(4, 6), [1, 2, 3, 4, 5, 6]);
});

test("texto del total", () => {
  assert.equal(textoRango({ total: 128, pagina: 2, por_pagina: 25 }, "análisis"), "Mostrando 26–50 de 128 análisis");
  assert.equal(textoRango({ total: 128, pagina: 6, por_pagina: 25 }, "análisis"), "Mostrando 126–128 de 128 análisis");
  assert.equal(textoRango({ total: 0, pagina: 1, por_pagina: 25 }, "informes"), "0 informes");
});

test("columnas importantes primero (visibles sin desplazar en 1366 px) y acciones al final", () => {
  const ids = (columnas) => columnas.map((c) => c.id);
  for (const opciones of [{}, { mostrarSeguimiento: true }, { mostrarDesarrollador: false }]) {
    const historial = ids(columnasHistorial(opciones));
    assert.deepEqual(historial.slice(0, 5), ["fecha", "repositorio", "riesgo", "probabilidad", "decision"]);
    assert.equal(historial.at(-1), "acciones");
  }
  assert.deepEqual(ids(COLUMNAS_PENDIENTES).slice(0, 4), ["fecha", "repositorio", "riesgo", "probabilidad"]);
  assert.deepEqual(ids(COLUMNAS_ASIGNACIONES).slice(0, 3), ["limite", "repositorio", "decision"]);
  assert.deepEqual(ids(columnasInformes()).slice(0, 5), ["enviado", "repositorio", "riesgo", "diferencia", "decision"]);
  assert.ok(ids(columnasInformes({ mostrarLider: true })).includes("lider"));
  for (const lista of [COLUMNAS_PENDIENTES, COLUMNAS_ASIGNACIONES, columnasInformes(), COLUMNAS_USUARIOS]) {
    assert.equal(lista.at(-1).id, "acciones");
  }
});

test("paginación: total, página actual y filas por página", async () => {
  const Paginacion = (await cargarComponente("Paginacion")).default;
  const datos = { total: 128, pagina: 2, por_pagina: 25, paginas: 6, resultados: [] };
  const html = sinMarcas(renderToString(h(Paginacion, { id: "t", datos, sustantivo: "análisis", alCambiar: () => {} })));
  assert.match(html, /Mostrando 26–50 de 128 análisis/);
  assert.match(html, /aria-current="page"[^>]*>2</);
  for (const n of [25, 50, 100]) assert.match(html, new RegExp(`<option value="${n}"`));
  assert.match(html, /Anterior/);
  // Con una sola página no hay botones, pero sí el total.
  const una = sinMarcas(renderToString(h(Paginacion, {
    id: "t", datos: { ...datos, total: 3, paginas: 1, pagina: 1 }, sustantivo: "informes", alCambiar: () => {},
  })));
  assert.match(una, /Mostrando 1–3 de 3 informes/);
  assert.doesNotMatch(una, /Anterior/);
});

test("tabla paginada: paginación arriba y abajo, barra superior y encabezados", async () => {
  const { TablaPaginada } = await cargarComponente("TablaDesplazable");
  const columnas = columnasHistorial({ mostrarDesarrollador: false });
  const fila = { id: 1 };
  const celdas = Object.fromEntries(columnas.map((c) => [c.id, () => `celda-${c.id}`]));
  const html = sinMarcas(renderToString(h(TablaPaginada, {
    id: "historial", titulo: "Historial", columnas, celdas, sustantivo: "análisis", alCambiarPagina: () => {},
    datos: { total: 60, pagina: 1, por_pagina: 25, paginas: 3, resultados: [fila] },
  })));
  assert.equal((html.match(/class="paginacion /g) || []).length, 2);
  assert.match(html, /paginacion--arriba/);
  assert.match(html, /paginacion--abajo/);
  assert.match(html, /tabla-desplazable__arriba/);
  assert.match(html, /tabla-desplazable__cuerpo/);
  assert.match(html, /tabla-desplazable--acciones-fijas/);
  // Encabezados y celdas en el mismo orden.
  const encabezados = [...html.matchAll(/<th scope="col" class="[^"]*col-(\w+)/g)].map((m) => m[1]);
  const deCeldas = [...html.matchAll(/celda-(\w+)/g)].map((m) => m[1]);
  assert.deepEqual(encabezados, columnas.map((c) => c.id));
  assert.deepEqual(deCeldas, columnas.map((c) => c.id));
});
