// Eliminar una cuenta con historial: sus análisis, decisiones y accesos se
// traspasan antes a otra cuenta activa del mismo rol o administradora (la
// regla real está en views_gestion.destino_traspaso_valido).

export function tieneHistorial(usuario) {
  return Boolean(usuario.analisis || usuario.decisiones);
}

// Motivo por el que la cuenta no se puede eliminar, o null si se puede.
export function motivoNoEliminar(usuario) {
  if (usuario.es_actual) return "No puede eliminar su propia cuenta.";
  if (usuario.superusuario) return "El superusuario no se puede eliminar.";
  return null;
}

// Cuentas que pueden recibir el historial: primero las del mismo rol.
export function candidatosTraspaso(usuario, usuarios) {
  return usuarios
    .filter((u) => u.id !== usuario.id && u.activo && (u.rol === usuario.rol || u.rol === "administrador"))
    .sort((a, b) => (a.rol !== usuario.rol) - (b.rol !== usuario.rol) || a.usuario.localeCompare(b.usuario));
}
