// Filtros, orden y página de las tablas guardados en la dirección, para que F5
// y atrás/adelante los conserven. Solo se escriben los valores distintos de
// los iniciales de cada pantalla (la dirección queda corta).
import { POR_PAGINA } from "./paginacion.js";

// Filtros de la dirección; lo que no esté, el valor inicial.
export function leerFiltros(search, iniciales) {
  const p = new URLSearchParams(search || "");
  return Object.fromEntries(Object.entries(iniciales).map(([clave, inicial]) => [clave, p.get(clave) ?? inicial]));
}

// Página de la dirección (`sufijo` para una segunda tabla en la misma pantalla).
export function leerPaginacion(search, sufijo = "") {
  const p = new URLSearchParams(search || "");
  const pagina = Number(p.get(`pagina${sufijo}`));
  const porPagina = Number(p.get(`por_pagina${sufijo}`));
  return {
    pagina: Number.isInteger(pagina) && pagina >= 1 ? pagina : 1,
    porPagina: POR_PAGINA.includes(porPagina) ? porPagina : POR_PAGINA[0],
  };
}

// "?…" con los filtros y las paginaciones que no son los iniciales ("" si
// todo está como al entrar). `paginaciones`: [[sufijo, { pagina, porPagina }]].
export function escribirEstado({ filtros = {}, iniciales = {}, paginaciones = [], extra = {} } = {}) {
  const p = new URLSearchParams();
  for (const [clave, valor] of Object.entries(filtros)) {
    if (valor !== undefined && valor !== null && valor !== "" && valor !== iniciales[clave]) p.set(clave, valor);
  }
  for (const [sufijo, { pagina, porPagina }] of paginaciones) {
    if (pagina > 1) p.set(`pagina${sufijo}`, String(pagina));
    if (porPagina !== POR_PAGINA[0]) p.set(`por_pagina${sufijo}`, String(porPagina));
  }
  for (const [clave, valor] of Object.entries(extra)) {
    if (valor !== undefined && valor !== null && valor !== "") p.set(clave, valor);
  }
  const texto = p.toString();
  return texto ? `?${texto}` : "";
}
