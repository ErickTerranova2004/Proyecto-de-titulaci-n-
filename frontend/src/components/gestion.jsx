import { useEffect } from "react";

export const ICONOS = {
  usuarios: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  verificado: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
  pendiente: "M12 7v5l3 3M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
  alto: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z",
  repositorio: "M3 7h18M3 12h18M3 17h18",
  workflows: "M4 6h16M4 12h10M4 18h6M17 15l3 3-3 3",
  enlace: "M9 7H6a5 5 0 0 0 0 10h3M15 7h3a5 5 0 0 1 0 10h-3M8 12h8",
};

// Indicador con el mismo diseño que los KPI del panel.
export function Indicador({ icono, titulo, valor, detalle, nivel }) {
  return (
    <article className={`kpi${nivel ? ` kpi--${nivel}` : ""}`}>
      <div className="kpi__cabecera">
        <h3 className="kpi__titulo">{titulo}</h3>
        {icono && (
          <svg viewBox="0 0 24 24" className="kpi__icono" aria-hidden="true"><path d={ICONOS[icono]} /></svg>
        )}
      </div>
      <div>
        <p className="kpi__valor">{valor}</p>
        {detalle && <p className="kpi__detalle secundario">{detalle}</p>}
      </div>
    </article>
  );
}

// Botones de filtro con contador.
export function Filtros({ opciones, valor, conteos, alCambiar, etiqueta }) {
  return (
    <div className="gestion-filtros" role="group" aria-label={etiqueta}>
      {opciones.map(([id, texto]) => (
        <button
          key={id}
          type="button"
          className="gestion-filtro"
          aria-pressed={valor === id}
          onClick={() => alCambiar(id)}
        >
          {texto} <span>{conteos[id] || 0}</span>
        </button>
      ))}
    </div>
  );
}

// Ventana modal. Se cierra con Escape o al pulsar fuera.
export function Dialogo({ titulo, alCerrar, children, ancho }) {
  useEffect(() => {
    const tecla = (e) => {
      if (e.key === "Escape") alCerrar();
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [alCerrar]);
  return (
    <div className="gestion-fondo" onMouseDown={alCerrar}>
      <div
        className="gestion-dialogo"
        style={ancho ? { width: `min(${ancho}px, 100%)` } : undefined}
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-dialogo"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className="gestion-dialogo__cabecera">
          <h2 id="titulo-dialogo">{titulo}</h2>
          <button type="button" className="boton boton--secundario boton--pequeno" onClick={alCerrar}>
            Cerrar
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}

export function Aviso({ texto }) {
  return texto ? <p className="gestion-aviso" role="status">{texto}</p> : null;
}