// Informes de cumplimiento: consulta de la lista, validación del comentario y
// textos. El backend (services/informes.py) aplica permisos y filtros.
import { consultaHistorial, ORDENES } from "./filtrosHistorial.js";

export const MIN_COMENTARIO = 10;
export const MAX_COMENTARIO = 2000;

// La lista se ordena por fecha de envío: sin «con decisión primero».
export const ORDENES_INFORMES = ORDENES.filter(([id]) => id !== "decision");

// Filtros de «Informes recibidos» e «Informes de cumplimiento», con el mismo
// diseño que los historiales: desde, hasta, nivel actual (del análisis
// nuevo), resultado del cambio, decisión final, repositorio y orden.
export const FILTROS_INFORMES = {
  desde: "", hasta: "", nivel: "todos", resultado: "todos", decision: "todas", repo: "", orden: "reciente",
};
export const RESULTADOS_FILTRO = [
  ["todos", "Todos"],
  ["bajo", "Bajó el riesgo"],
  ["mantuvo", "Se mantuvo"],
  ["subio", "Subió el riesgo"],
];
export const DECISIONES_FINAL_FILTRO = [
  ["todas", "Todas"],
  ["pendiente", "Pendiente"],
  ["autorizar", "Autorizar"],
  ["posponer", "Posponer"],
  ["solicitar_revision", "Solicitar revisión"],
];

// Parámetros de /api/informes/ ("" sin filtros).
export function consultaInformes({ desde, hasta, nivel, resultado, decision, repo, orden } = {}) {
  const p = new URLSearchParams(consultaHistorial({ desde, hasta, nivel }).replace(/^\?/, ""));
  if (resultado && resultado !== "todos") p.set("resultado", resultado);
  if (decision && decision !== "todas") p.set("decision", decision);
  if (repo && repo.trim()) p.set("repo", repo.trim());
  if (orden === "antiguo") p.set("orden", "antiguo");
  const texto = p.toString();
  return texto ? `?${texto}` : "";
}

// Mensaje si el comentario no se puede enviar; "" si es válido.
export function problemaComentario(texto) {
  const limpio = (texto || "").trim();
  if (!limpio) return "Describa qué cambios hizo para cumplir la indicación.";
  if (limpio.length < MIN_COMENTARIO) return `Describa los cambios con al menos ${MIN_COMENTARIO} caracteres.`;
  if (limpio.length > MAX_COMENTARIO) return `El comentario admite como máximo ${MAX_COMENTARIO} caracteres.`;
  return "";
}

// Valor de una variable en la tabla de factores.
export function valorVariable(valor) {
  if (valor === null || valor === undefined) return "Sin dato";
  if (typeof valor === "number") return Number.isInteger(valor) ? String(valor) : valor.toFixed(2);
  return String(valor);
}
