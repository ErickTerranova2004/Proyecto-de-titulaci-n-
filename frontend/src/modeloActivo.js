// Activación de versiones del modelo (pantalla Modelos y aviso del panel del
// administrador). El backend decide qué versiones se pueden activar
// (riesgo/services/modelos.py): solo las que tienen fecha de corte.

// Aviso del panel del administrador a partir de /api/resumen-admin/ (campo
// «modelo»: { activo, recomendado, aviso }). null si no hay que avisar.
export function avisoModeloActivo(estado) {
  if (!estado?.aviso || !estado.recomendado) return null;
  if (!estado.activo) {
    return `No hay un modelo activo. Active ${estado.recomendado}, la versión más reciente con fecha de corte.`;
  }
  const lote = estado.activo_sin_corte
    ? ` El análisis en lote no funciona mientras ${estado.activo} esté activo (no tiene fecha de corte).`
    : "";
  return (
    `El modelo activo es ${estado.activo}, pero la versión más reciente con fecha de corte es ` +
    `${estado.recomendado}. Los análisis nuevos usan ${estado.activo}.${lote}`
  );
}

// La confirmación coincide con el nombre de la versión (igual que el backend:
// sin espacios a los lados, distingue mayúsculas).
export const confirmacionValida = (texto, version) => (texto ?? "").trim() === version;
