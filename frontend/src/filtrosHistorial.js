// Filtros de los historiales y de «Pendientes de decisión». Los aplica el
// backend (views.filtrar_historial); aquí solo se arma la consulta.

export const NIVELES_FILTRO = [
  ["todos", "Todos"],
  ["bajo", "Bajo"],
  ["medio", "Medio"],
  ["alto", "Alto"],
];

// «decision» no la ordena el backend: reordena en pantalla lo recibido
// (src/ordenHistorial.js), primero los análisis con la decisión más reciente.
export const ORDENES = [
  ["reciente", "Más recientes primero"],
  ["antiguo", "Más antiguos primero"],
  ["decision", "Con decisión más reciente primero"],
];

export const FILTROS_INICIALES = { desde: "", hasta: "", nivel: "todos", orden: "reciente" };

const FECHA = /^\d{4}-\d{2}-\d{2}$/;

// Mensaje si el rango no es válido; "" si se puede consultar.
export function errorRango(desde, hasta) {
  if ((desde && !FECHA.test(desde)) || (hasta && !FECHA.test(hasta))) return "Use fechas con el formato AAAA-MM-DD.";
  if (desde && hasta && desde > hasta) return "La fecha «desde» no puede ser posterior a «hasta».";
  return "";
}

// Parámetros de /api/predicciones/ ("" sin filtros).
export function consultaHistorial({ desde, hasta, nivel, orden, origen, sinDecision } = {}) {
  const p = new URLSearchParams();
  if (desde) p.set("desde", desde);
  if (hasta) p.set("hasta", hasta);
  if (nivel && nivel !== "todos") p.set("nivel", nivel);
  if (sinDecision) p.set("sin_decision", "1");
  if (origen && origen !== "todos") p.set("origen", origen);
  // El backend ya devuelve «reciente» por defecto.
  if (orden === "antiguo") p.set("orden", "antiguo");
  const texto = p.toString();
  return texto ? `?${texto}` : "";
}

export function hayFiltros({ desde, hasta, nivel, origen } = {}, origenInicial = "todos") {
  return Boolean(desde || hasta || (nivel && nivel !== "todos") || (origen && origen !== origenInicial));
}
