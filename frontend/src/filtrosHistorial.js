// Filtros de los historiales y de «Pendientes de decisión». Los aplica el
// backend (views.filtrar_historial); aquí solo se arma la consulta.

export const NIVELES_FILTRO = [
  ["todos", "Todos"],
  ["bajo", "Bajo"],
  ["medio", "Medio"],
  ["alto", "Alto"],
];

// «decision»: primero los análisis con la decisión más reciente. Lo ordena el
// backend (para que la paginación lo respete).
export const ORDENES = [
  ["reciente", "Más recientes primero"],
  ["antiguo", "Más antiguos primero"],
  ["decision", "Con decisión más reciente primero"],
];

// Decisión del líder (la última de cada análisis); no aplica en «Pendientes
// de decisión», donde todos están sin decisión.
export const DECISIONES_FILTRO = [
  ["todas", "Todas"],
  ["sin_decision", "Sin decisión"],
  ["autorizar", "Autorizar"],
  ["posponer", "Posponer"],
  ["solicitar_revision", "Solicitar revisión"],
];

// Mismos filtros y en el mismo orden en los tres historiales y en Pendientes:
// desde, hasta, nivel, decisión, repositorio, orden (y origen, el
// administrador).
export const FILTROS_INICIALES = {
  desde: "", hasta: "", nivel: "todos", decision: "todas", repo: "", orden: "reciente",
};

const FECHA = /^\d{4}-\d{2}-\d{2}$/;

// En pantalla las fechas se escriben dd/mm/aaaa sea cual sea el idioma del
// navegador; los filtros y el backend usan AAAA-MM-DD.
export function textoFecha(iso) {
  if (!iso || !FECHA.test(iso)) return "";
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

// "" si el campo está vacío, la fecha AAAA-MM-DD si es válida, null si no.
export function fechaDesdeTexto(texto) {
  const t = (texto || "").trim();
  if (!t) return "";
  const partes = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(t);
  if (!partes) return null;
  const [d, m, a] = partes.slice(1).map(Number);
  const f = new Date(Date.UTC(a, m - 1, d));
  if (a < 1900 || f.getUTCFullYear() !== a || f.getUTCMonth() !== m - 1 || f.getUTCDate() !== d) return null;
  return `${a}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

// Mientras se escribe: solo dígitos y las barras se ponen solas (dd/mm/aaaa).
export function escribirFecha(texto) {
  const digitos = (texto || "").replace(/\D/g, "").slice(0, 8);
  if (digitos.length <= 2) return digitos;
  if (digitos.length <= 4) return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
  return `${digitos.slice(0, 2)}/${digitos.slice(2, 4)}/${digitos.slice(4)}`;
}

// Mensaje si el rango no es válido; "" si se puede consultar.
export function errorRango(desde, hasta) {
  if ((desde && !FECHA.test(desde)) || (hasta && !FECHA.test(hasta))) return "Use fechas con el formato dd/mm/aaaa.";
  if (desde && hasta && desde > hasta) return "La fecha «desde» no puede ser posterior a «hasta».";
  return "";
}

// Parámetros de /api/predicciones/ ("" sin filtros).
export function consultaHistorial({ desde, hasta, nivel, decision, repo, orden, origen, sinDecision } = {}) {
  const p = new URLSearchParams();
  if (desde) p.set("desde", desde);
  if (hasta) p.set("hasta", hasta);
  if (nivel && nivel !== "todos") p.set("nivel", nivel);
  if (sinDecision) p.set("sin_decision", "1");
  else if (decision && decision !== "todas") p.set("decision", decision);
  if (repo && repo.trim()) p.set("repo", repo.trim());
  if (origen && origen !== "todos") p.set("origen", origen);
  // El backend ya devuelve «reciente» por defecto.
  if (orden === "antiguo" || orden === "decision") p.set("orden", orden);
  const texto = p.toString();
  return texto ? `?${texto}` : "";
}

// Hay algo que «Quitar filtros» pueda limpiar (el orden no cuenta).
export function hayFiltros({ desde, hasta, nivel, decision, resultado, repo, origen } = {}, origenInicial = "todos") {
  return Boolean(desde || hasta || (nivel && nivel !== "todos") || (decision && decision !== "todas")
    || (resultado && resultado !== "todos") || (repo && repo.trim()) || (origen && origen !== origenInicial));
}
