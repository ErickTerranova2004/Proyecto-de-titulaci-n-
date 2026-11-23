// Orden de las columnas de las tablas largas. Las importantes (fecha,
// repositorio, riesgo, probabilidad y decisión) van primero para verse sin
// desplazar en una pantalla de 1366 px; la de acciones queda fija a la
// derecha (TablaDesplazable). El componente usa este orden para el encabezado
// y para las celdas.

export function columnasHistorial({ mostrarSeguimiento = false, mostrarDesarrollador = true } = {}) {
  return [
    { id: "fecha", titulo: "Fecha" },
    { id: "repositorio", titulo: "Repositorio" },
    { id: "riesgo", titulo: "Riesgo" },
    { id: "probabilidad", titulo: "Probabilidad", clase: "numero" },
    { id: "decision", titulo: "Decisión" },
    { id: "modelo", titulo: "Modelo" },
    ...(mostrarSeguimiento ? [{ id: "limite", titulo: "Fecha límite" }, { id: "seguimiento", titulo: "Seguimiento" }] : []),
    ...(mostrarDesarrollador ? [{ id: "desarrollador", titulo: "Desarrollador" }] : []),
    { id: "workflow", titulo: "Workflow" },
    { id: "commit", titulo: "Commit" },
    { id: "acciones", titulo: "Acciones", oculto: true },
  ];
}

// Pendientes: todos están sin decisión, así que no hay columna de decisión.
export const COLUMNAS_PENDIENTES = [
  { id: "fecha", titulo: "Fecha" },
  { id: "repositorio", titulo: "Repositorio" },
  { id: "riesgo", titulo: "Riesgo" },
  { id: "probabilidad", titulo: "Probabilidad", clase: "numero" },
  { id: "modelo", titulo: "Modelo" },
  { id: "desarrollador", titulo: "Desarrollador" },
  { id: "workflow", titulo: "Workflow" },
  { id: "acciones", titulo: "Acciones", oculto: true },
];

export const COLUMNAS_ASIGNACIONES = [
  { id: "limite", titulo: "Fecha límite" },
  { id: "repositorio", titulo: "Repositorio" },
  { id: "decision", titulo: "Decisión" },
  { id: "estado", titulo: "Estado" },
  { id: "desarrollador", titulo: "Desarrollador" },
  { id: "respuesta", titulo: "Respuesta del desarrollador" },
  { id: "mensaje", titulo: "Mensaje" },
  { id: "vista", titulo: "Vista" },
  { id: "cumplida", titulo: "Cumplida" },
  { id: "acciones", titulo: "Acciones", oculto: true },
];

export function columnasInformes({ mostrarLider = false } = {}) {
  return [
    { id: "enviado", titulo: "Enviado" },
    { id: "repositorio", titulo: "Repositorio" },
    { id: "riesgo", titulo: "Riesgo" },
    { id: "diferencia", titulo: "Diferencia" },
    { id: "decision", titulo: "Decisión final" },
    { id: "modelo", titulo: "Modelo" },
    { id: "numero", titulo: "N.º" },
    { id: "desarrollador", titulo: "Desarrollador" },
    ...(mostrarLider ? [{ id: "lider", titulo: "Líder" }] : []),
    { id: "acciones", titulo: "Acciones", oculto: true },
  ];
}

export const COLUMNAS_USUARIOS = [
  { id: "usuario", titulo: "Usuario" },
  { id: "rol", titulo: "Rol" },
  { id: "estado", titulo: "Estado" },
  { id: "repositorios", titulo: "Repositorios" },
  { id: "acceso", titulo: "Último acceso" },
  { id: "acciones", titulo: "Acciones", oculto: true },
];
