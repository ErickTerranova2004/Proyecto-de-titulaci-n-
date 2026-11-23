import { POR_PAGINA, paginasVisibles, textoRango } from "../paginacion.js";

// Total, botones de página y filas por página. Se pone arriba y abajo de la
// tabla (`posicion`), con el mismo estado. `datos`: respuesta paginada del
// backend; `alCambiar({ pagina, porPagina })`.
export default function Paginacion({ id, datos, sustantivo, alCambiar, posicion = "arriba", deshabilitado = false }) {
  if (!datos) return null;
  const { pagina, paginas, por_pagina: porPagina } = datos;
  const ir = (n) => alCambiar({ pagina: n, porPagina });
  return (
    <nav className={`paginacion paginacion--${posicion}`} aria-label={`Paginación (${posicion})`}>
      <p className="paginacion__total secundario" role={posicion === "arriba" ? "status" : undefined}>
        {textoRango(datos, sustantivo)}
      </p>
      {paginas > 1 && (
        <ul className="paginacion__paginas">
          <li>
            <button type="button" className="paginacion__boton" onClick={() => ir(pagina - 1)} disabled={deshabilitado || pagina <= 1}>
              ‹ <span className="paginacion__texto">Anterior</span>
            </button>
          </li>
          {paginasVisibles(pagina, paginas).map((n, i) =>
            n === "…" ? (
              <li key={`salto-${i}`} className="paginacion__salto" aria-hidden="true">…</li>
            ) : (
              <li key={n}>
                <button
                  type="button"
                  className="paginacion__boton"
                  aria-current={n === pagina ? "page" : undefined}
                  aria-label={`Página ${n}`}
                  onClick={() => ir(n)}
                  disabled={deshabilitado}
                >
                  {n}
                </button>
              </li>
            ),
          )}
          <li>
            <button type="button" className="paginacion__boton" onClick={() => ir(pagina + 1)} disabled={deshabilitado || pagina >= paginas}>
              <span className="paginacion__texto">Siguiente</span> ›
            </button>
          </li>
        </ul>
      )}
      <label className="paginacion__por-pagina" htmlFor={`${id}-${posicion}-por-pagina`}>
        <span>Filas por página</span>
        <select
          id={`${id}-${posicion}-por-pagina`}
          value={porPagina}
          onChange={(e) => alCambiar({ pagina: 1, porPagina: Number(e.target.value) })}
          disabled={deshabilitado}
        >
          {POR_PAGINA.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </label>
    </nav>
  );
}
