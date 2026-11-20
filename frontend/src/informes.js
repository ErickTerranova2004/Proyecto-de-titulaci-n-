// Informes de cumplimiento: consulta de la lista, validación del comentario y
// textos. El backend (services/informes.py) aplica permisos y filtros.
import { consultaHistorial, ORDENES } from "./filtrosHistorial.js";

export const MIN_COMENTARIO = 10;
export const MAX_COMENTARIO = 2000;

// La lista se ordena por fecha de envío: sin «con decisión primero».
export const ORDENES_INFORMES = ORDENES.filter(([id]) => id !== "decision");

// "?desde=…&hasta=…&orden=antiguo" ("" sin filtros). El nivel no aplica.
export function consultaInformes({ desde, hasta, orden } = {}) {
  return consultaHistorial({ desde, hasta, orden });
}

// Mensaje si el comentario no se puede enviar; "" si es válido.
export function problemaComentario(texto) {
  const limpio = (texto || "").trim();
  if (!limpio) return "Describa qué cambios hizo para cumplir la indicación.";
  if (limpio.length < MIN_COMENTARIO) return `Describa los cambios con al menos ${MIN_COMENTARIO} caracteres.`;
  if (limpio.length > MAX_COMENTARIO) return `El comentario admite como máximo ${MAX_COMENTARIO} caracteres.`;
  return "";
}

// Id del informe del enlace del correo (?informe=12), o null.
export function informeDelEnlace(busqueda) {
  const valor = new URLSearchParams(busqueda || "").get("informe");
  return valor && /^\d+$/.test(valor) ? Number(valor) : null;
}

// Valor de una variable en la tabla de factores.
export function valorVariable(valor) {
  if (valor === null || valor === undefined) return "Sin dato";
  if (typeof valor === "number") return Number.isInteger(valor) ? String(valor) : valor.toFixed(2);
  return String(valor);
}
