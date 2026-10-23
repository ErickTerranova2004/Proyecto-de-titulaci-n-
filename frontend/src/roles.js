// Secciones de la interfaz según el rol. Solo decide qué menú y qué panel se
// muestran: los permisos reales los aplica el backend (riesgo/permissions.py).

// De mayor a menor jerarquía (igual que permissions.rol_principal).
const JERARQUIA = ["administrador", "lider_tecnico", "desarrollador"];

export const NOMBRES_ROL = {
  administrador: "Administrador",
  lider_tecnico: "Líder técnico",
  desarrollador: "Desarrollador",
};

const ICONOS = {
  panel: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
  nuevo: "M12 5v14M5 12h14",
  historial: "M12 7v5l3 3M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
  pendientes: "M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11",
  usuarios: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  workflows: "M4 6h16M4 12h10M4 18h6M17 15l3 3-3 3",
  modelos: "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z",
  integraciones: "M9 7H6a5 5 0 0 0 0 10h3M15 7h3a5 5 0 0 1 0 10h-3M8 12h8",
};

// `enlace`: la sección abre el administrador de Django en una pestaña nueva.
const seccion = (id, texto, icono, enlace) => ({ id, texto, icono: ICONOS[icono], enlace });

// La primera sección de cada lista es la vista inicial del rol.
export const SECCIONES = {
  desarrollador: [
    seccion("panel", "Mi panel", "panel"),
    seccion("nuevo", "Nuevo análisis", "nuevo"),
    seccion("historial", "Mi historial", "historial"),
  ],
  lider_tecnico: [
    seccion("panel", "Panel del equipo", "panel"),
    seccion("pendientes", "Pendientes de decisión", "pendientes"),
    seccion("historial", "Historial del equipo", "historial"),
    seccion("nuevo", "Nuevo análisis", "nuevo"),
  ],
  administrador: [
    seccion("panel", "Panel de administración", "panel"),
    seccion("usuarios", "Usuarios y accesos", "usuarios", "auth/user/"),
    seccion("workflows", "Workflows", "workflows", "riesgo/workflow/"),
    seccion("modelos", "Modelos", "modelos"),
    seccion("integraciones", "Integraciones", "integraciones"),
  ],
};

// Rol de mayor jerarquía del usuario, o null si no tiene ninguno.
export function rolPrincipal(roles) {
  return JERARQUIA.find((rol) => roles.includes(rol)) ?? null;
}

export function seccionesDe(rol) {
  return SECCIONES[rol] ?? [];
}
