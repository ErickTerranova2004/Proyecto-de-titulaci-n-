// Rutas de la plataforma (API History, sin dependencias). Cada pantalla tiene
// su dirección; atrás/adelante y F5 la conservan. Funciones puras: App.jsx y
// src/navegacion.jsx las usan y tests/rutas.test.js las prueba.

// Sección del menú (roles.js) ↔ ruta.
export const RUTAS_SECCION = {
  panel: "/panel",
  nuevo: "/nuevo-analisis",
  planificador: "/planificador",
  historial: "/historial",
  pendientes: "/pendientes",
  informes: "/informes",
  usuarios: "/usuarios",
  workflows: "/workflows",
  modelos: "/modelos",
  integraciones: "/integraciones",
};
const SECCION_DE_RUTA = Object.fromEntries(Object.entries(RUTAS_SECCION).map(([s, r]) => [r, s]));

export function rutaDe(seccion) {
  return RUTAS_SECCION[seccion] || "/panel";
}

// { tipo, seccion?, id? } de una dirección:
// - "raiz": "/" (se redirige al panel del rol);
// - "seccion": una pantalla del menú;
// - "analisis" (/analisis/<id>) e "informe" (/informes/<id> o el enlace
//   antiguo del correo ?informe=<id>);
// - "restablecer": /restablecer/<uid>/<token> (pública);
// - "desconocida".
export function interpretarRuta(pathname = "/", search = "") {
  const ruta = (pathname || "/").replace(/\/+$/, "") || "/";
  const informeCorreo = new URLSearchParams(search || "").get("informe");
  if (informeCorreo && /^\d+$/.test(informeCorreo)) {
    return { tipo: "informe", id: Number(informeCorreo), seccion: "informes", delCorreo: true };
  }
  if (ruta === "/") return { tipo: "raiz" };
  if (/^\/restablecer\/[^/]+\/[^/]+$/.test(ruta)) return { tipo: "restablecer" };
  let m = /^\/analisis\/(\d+)$/.exec(ruta);
  if (m) return { tipo: "analisis", id: Number(m[1]) };
  m = /^\/informes\/(\d+)$/.exec(ruta);
  if (m) return { tipo: "informe", id: Number(m[1]), seccion: "informes" };
  if (SECCION_DE_RUTA[ruta]) return { tipo: "seccion", seccion: SECCION_DE_RUTA[ruta] };
  return { tipo: "desconocida" };
}

// Dirección a la que hay que ir en lugar de la pedida, o null si se puede
// mostrar. `permitidas`: ids de las secciones del rol (la primera es su
// panel). Sin permiso, al panel del rol. Un análisis o un informe concreto los
// puede abrir cualquier rol: el backend decide si los ve (404 si no).
export function redireccion(destino, permitidas) {
  const inicio = rutaDe(permitidas[0] || "panel");
  if (destino.tipo === "informe" && destino.delCorreo) return `/informes/${destino.id}`;
  if (destino.tipo === "raiz" || destino.tipo === "desconocida") return inicio;
  if (destino.tipo === "seccion" && !permitidas.includes(destino.seccion)) return inicio;
  return null;
}

// Sección del menú que se marca como actual.
export function seccionActiva(destino) {
  if (destino.tipo === "seccion") return destino.seccion;
  if (destino.tipo === "informe") return "informes";
  return null;
}
