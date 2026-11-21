import { useEffect, useRef, useState } from "react";
import Paginacion from "./Paginacion.jsx";

// Tabla paginada en el backend: paginación arriba y abajo, barra horizontal
// también arriba y encabezados fijos. `columnas` (src/columnasTablas.js) da el
// orden; `celdas[id](fila)` el contenido de cada celda.
export function TablaPaginada({
  id, titulo, columnas, celdas, datos, sustantivo, cargando, alCambiarPagina, clave = (fila) => fila.id, tarjeta = true,
}) {
  const contenido = (
    <>
      <Paginacion id={id} datos={datos} sustantivo={sustantivo} alCambiar={alCambiarPagina} deshabilitado={cargando} />
      <TablaDesplazable etiqueta={titulo}>
        <table>
          <caption className="solo-lector">{titulo}</caption>
          <Encabezado columnas={columnas} />
          <tbody>
            {datos.resultados.map((fila) => (
              <tr key={clave(fila)}>
                {columnas.map((c) => (
                  <td key={c.id} className={[c.clase, `col-${c.id}`].filter(Boolean).join(" ")}>
                    {celdas[c.id](fila)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </TablaDesplazable>
      <Paginacion id={id} datos={datos} sustantivo={sustantivo} alCambiar={alCambiarPagina} deshabilitado={cargando} posicion="abajo" />
    </>
  );
  return tarjeta ? <div className="tarjeta tarjeta--tabla">{contenido}</div> : contenido;
}

// Fila de encabezados a partir de la lista de columnas (src/columnasTablas.js).
export function Encabezado({ columnas }) {
  return (
    <thead>
      <tr>
        {columnas.map((c) => (
          <th key={c.id} scope="col" className={[c.clase, `col-${c.id}`].filter(Boolean).join(" ")}>
            {c.oculto ? <span className="solo-lector">{c.titulo}</span> : c.titulo}
          </th>
        ))}
      </tr>
    </thead>
  );
}

// Contenedor de tablas largas:
// - barra de desplazamiento horizontal también arriba, sincronizada con la
//   de abajo (solo aparece si la tabla es más ancha que el contenedor);
// - altura máxima = alto de la ventana menos la cabecera, con scroll vertical
//   propio y los encabezados fijos (thead sticky, en CSS);
// - con `accionesFijas`, la última columna (botones) queda fija a la derecha.
export default function TablaDesplazable({ children, accionesFijas = true, etiqueta }) {
  const arriba = useRef(null);
  const abajo = useRef(null);
  const sincronizando = useRef(false);
  const [ancho, setAncho] = useState(0);
  const [desborda, setDesborda] = useState(false);

  useEffect(() => {
    const contenedor = abajo.current;
    if (!contenedor) return undefined;
    const medir = () => {
      setAncho(contenedor.scrollWidth);
      setDesborda(contenedor.scrollWidth > contenedor.clientWidth + 1);
    };
    medir();
    if (typeof ResizeObserver === "undefined") return undefined;
    const observador = new ResizeObserver(medir);
    observador.observe(contenedor);
    if (contenedor.firstElementChild) observador.observe(contenedor.firstElementChild);
    return () => observador.disconnect();
  }, [children]);

  // Mover una barra mueve la otra (sin bucle de eventos).
  function sincronizar(origen, destino) {
    if (sincronizando.current) {
      sincronizando.current = false;
      return;
    }
    if (destino.current && origen.current && destino.current.scrollLeft !== origen.current.scrollLeft) {
      sincronizando.current = true;
      destino.current.scrollLeft = origen.current.scrollLeft;
    }
  }

  return (
    <div className={`tabla-desplazable${accionesFijas ? " tabla-desplazable--acciones-fijas" : ""}`}>
      <div
        ref={arriba}
        className="tabla-desplazable__arriba"
        hidden={!desborda}
        aria-hidden="true"
        onScroll={() => sincronizar(arriba, abajo)}
      >
        <div style={{ width: ancho }} />
      </div>
      <div
        ref={abajo}
        className="tabla-contenedor tabla-desplazable__cuerpo"
        role="region"
        aria-label={etiqueta}
        tabIndex={0}
        onScroll={() => sincronizar(abajo, arriba)}
      >
        {children}
      </div>
    </div>
  );
}
