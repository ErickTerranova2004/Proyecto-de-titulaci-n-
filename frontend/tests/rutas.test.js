// Navegación con URL: rutas de cada pantalla, redirecciones por rol, enlaces
// de los correos y estado de las tablas en la dirección.
import assert from "node:assert/strict";
import { test } from "node:test";
import { escribirEstado, leerFiltros, leerPaginacion } from "../src/estadoUrl.js";
import { FILTROS_INICIALES } from "../src/filtrosHistorial.js";
import { interpretarRuta, redireccion, RUTAS_SECCION, rutaDe, seccionActiva } from "../src/rutas.js";

const DESARROLLADOR = ["panel", "nuevo", "planificador", "historial"];
const LIDER = ["panel", "pendientes", "historial", "informes", "nuevo"];

test("cada pantalla tiene su ruta", () => {
  assert.deepEqual(RUTAS_SECCION, {
    panel: "/panel", nuevo: "/nuevo-analisis", planificador: "/planificador", historial: "/historial",
    pendientes: "/pendientes", informes: "/informes", usuarios: "/usuarios", workflows: "/workflows",
    modelos: "/modelos", integraciones: "/integraciones",
  });
  for (const [seccion, ruta] of Object.entries(RUTAS_SECCION)) {
    assert.deepEqual(interpretarRuta(ruta), { tipo: "seccion", seccion });
    assert.deepEqual(interpretarRuta(`${ruta}/`), { tipo: "seccion", seccion }, "con barra final");
    assert.equal(rutaDe(seccion), ruta);
  }
  assert.deepEqual(interpretarRuta("/analisis/12"), { tipo: "analisis", id: 12 });
  assert.deepEqual(interpretarRuta("/informes/7"), { tipo: "informe", id: 7, seccion: "informes" });
  assert.deepEqual(interpretarRuta("/restablecer/MTI/abc-123"), { tipo: "restablecer" });
  assert.deepEqual(interpretarRuta("/"), { tipo: "raiz" });
  assert.deepEqual(interpretarRuta("/no-existe"), { tipo: "desconocida" });
  assert.deepEqual(interpretarRuta("/analisis/abc"), { tipo: "desconocida" });
});

test("enlace antiguo del correo ?informe=<id> lleva a /informes/<id>", () => {
  const destino = interpretarRuta("/", "?informe=5");
  assert.equal(destino.tipo, "informe");
  assert.equal(redireccion(destino, LIDER), "/informes/5");
  assert.equal(interpretarRuta("/", "?informe=x").tipo, "raiz");
});

test("raíz, dirección desconocida o sin permiso: al panel del rol", () => {
  assert.equal(redireccion(interpretarRuta("/"), DESARROLLADOR), "/panel");
  assert.equal(redireccion(interpretarRuta("/no-existe"), DESARROLLADOR), "/panel");
  assert.equal(redireccion(interpretarRuta("/usuarios"), DESARROLLADOR), "/panel");
  assert.equal(redireccion(interpretarRuta("/pendientes"), DESARROLLADOR), "/panel");
  assert.equal(redireccion(interpretarRuta("/pendientes"), LIDER), null);
  assert.equal(redireccion(interpretarRuta("/historial"), DESARROLLADOR), null);
  // Un análisis o un informe concreto los decide el backend (404 si no los ve).
  assert.equal(redireccion(interpretarRuta("/analisis/3"), DESARROLLADOR), null);
  assert.equal(redireccion(interpretarRuta("/informes/3"), DESARROLLADOR), null);
});

test("sección marcada en el menú", () => {
  assert.equal(seccionActiva(interpretarRuta("/historial")), "historial");
  assert.equal(seccionActiva(interpretarRuta("/informes/4")), "informes");
  assert.equal(seccionActiva(interpretarRuta("/analisis/4")), null);
});

test("filtros, orden y página en la dirección", () => {
  const iniciales = { ...FILTROS_INICIALES, origen: "interactivo" };
  assert.deepEqual(leerFiltros("", iniciales), iniciales);
  const filtros = { ...iniciales, desde: "2026-11-01", nivel: "alto", orden: "antiguo", origen: "lote" };
  const url = escribirEstado({ filtros, iniciales, paginaciones: [["", { pagina: 3, porPagina: 50 }]] });
  assert.equal(url, "?desde=2026-11-01&nivel=alto&orden=antiguo&origen=lote&pagina=3&por_pagina=50");
  // Ida y vuelta: F5 deja todo igual.
  assert.deepEqual(leerFiltros(url, iniciales), filtros);
  assert.deepEqual(leerPaginacion(url), { pagina: 3, porPagina: 50 });
  // Todo inicial: dirección limpia.
  assert.equal(escribirEstado({ filtros: iniciales, iniciales, paginaciones: [["", { pagina: 1, porPagina: 25 }]] }), "");
  // Segunda tabla en la misma pantalla (Pendientes).
  const dos = escribirEstado({ paginaciones: [["", { pagina: 2, porPagina: 25 }], ["_asignaciones", { pagina: 4, porPagina: 100 }]] });
  assert.equal(dos, "?pagina=2&pagina_asignaciones=4&por_pagina_asignaciones=100");
  assert.deepEqual(leerPaginacion(dos, "_asignaciones"), { pagina: 4, porPagina: 100 });
  // Valores no válidos escritos a mano: los iniciales.
  assert.deepEqual(leerPaginacion("?pagina=-2&por_pagina=7"), { pagina: 1, porPagina: 25 });
});

test("Vite devuelve index.html en las rutas profundas (SPA)", async () => {
  const configuracion = (await import("../vite.config.js")).default;
  assert.equal(configuracion.appType, "spa");
  assert.equal(configuracion.base, "/");
  for (const clave of ["/api", "/admin", "/static"]) assert.ok(configuracion.server.proxy[clave], clave);
});
