// Navegación con la API History: la dirección es el estado de la pantalla.
// - navegar(url): nueva entrada del historial (atrás vuelve a la anterior);
// - navegar(url, { reemplazar: true }): cambia la entrada actual (p. ej. al
//   escribir en un buscador, para no llenar el historial);
// - volver(alternativa): atrás si se llegó desde la propia plataforma; si
//   no (enlace del correo, F5), a la alternativa.
import { createContext, useContext, useEffect, useState } from "react";

function actual() {
  if (typeof window === "undefined") return { pathname: "/", search: "" };
  return { pathname: window.location.pathname, search: window.location.search };
}

export function useRuta() {
  const [ruta, setRuta] = useState(actual);
  useEffect(() => {
    const alCambiar = () => setRuta(actual());
    window.addEventListener("popstate", alCambiar);
    return () => window.removeEventListener("popstate", alCambiar);
  }, []);

  function navegar(url, { reemplazar = false } = {}) {
    const destino = new URL(url, window.location.origin);
    if (destino.pathname + destino.search === window.location.pathname + window.location.search) return;
    const estado = { interno: true };
    if (reemplazar) window.history.replaceState({ ...(window.history.state || {}), ...estado }, "", destino);
    else window.history.pushState(estado, "", destino);
    setRuta(actual());
    if (!reemplazar) window.scrollTo?.(0, 0);
  }

  function volver(alternativa) {
    if (window.history.state?.interno && window.history.length > 1) window.history.back();
    else navegar(alternativa, { reemplazar: true });
  }

  return { ruta, navegar, volver };
}

// Sin proveedor (p. ej. en las pruebas de render) no navega.
export const NavegacionContexto = createContext({
  ruta: { pathname: "/", search: "" },
  navegar: () => {},
  volver: () => {},
});

export function useNavegacion() {
  return useContext(NavegacionContexto);
}

// Enlace interno: navega sin recargar la página; con Ctrl/Cmd/Mayús o el
// botón central se abre en otra pestaña como un enlace normal.
export function Enlace({ href, children, alNavegar, ...props }) {
  const { navegar } = useNavegacion();
  return (
    <a
      href={href}
      {...props}
      onClick={(e) => {
        if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button !== 0) return;
        e.preventDefault();
        alNavegar?.();
        navegar(href);
      }}
    >
      {children}
    </a>
  );
}

// Parámetros de la dirección actual.
export function useParametros() {
  const { ruta } = useNavegacion();
  return new URLSearchParams(ruta.search);
}
