// Workflows (administrador): por defecto solo los de repositorios activos;
// la casilla «Incluir repositorios inactivos» muestra también los demás.
// Los contadores se calculan sobre el mismo alcance que la tabla.

export function enAlcance(workflows, incluirInactivos) {
  return (workflows ?? []).filter((w) => incluirInactivos || w.repositorio_activo !== false);
}

export function inactivos(workflows) {
  return (workflows ?? []).filter((w) => w.repositorio_activo === false).length;
}

export function textoAlcance(incluirInactivos) {
  return incluirInactivos ? "repositorios activos e inactivos" : "solo repositorios activos";
}
