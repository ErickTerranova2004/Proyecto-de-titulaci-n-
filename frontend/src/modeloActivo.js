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

// --- Modelo de cada análisis (Random Forest o XGBoost, ambos del dataset v2) ---

export const COMPARAR = "comparar";
export const ROLES_MODELO = { principal: "Principal", alternativo: "Alternativo" };

// Modelos que se pueden elegir en un análisis: con fecha de corte (activables),
// el principal primero. [{ valor: "v2", texto: "Random Forest (Principal)" }, …]
export function opcionesModelo(modelos) {
  return (modelos ?? [])
    .filter((m) => m.activable !== false)
    .sort((a, b) => Number(b.activo) - Number(a.activo))
    .map((m) => ({ valor: m.version, texto: `${m.nombre_modelo} (${ROLES_MODELO[m.activo ? "principal" : "alternativo"]})` }));
}

export const modeloPrincipal = (modelos) => (modelos ?? []).find((m) => m.activo)?.version ?? "";

// Nombre del modelo de un análisis: «XGBoost (v2-xgb)»; sin nombre, la versión.
export function etiquetaModelo(prediccion) {
  if (!prediccion?.version_modelo) return "—";
  return prediccion.modelo_nombre
    ? `${prediccion.modelo_nombre} (${prediccion.version_modelo})`
    : prediccion.version_modelo;
}
