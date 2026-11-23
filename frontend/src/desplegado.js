// Aviso de «Nuevo análisis» cuando el commit ya se desplegó (409
// commit_ya_desplegado). Texto claro para el desarrollador: cuándo (hoy, ayer
// o dd/mm/aaaa, hora en 24 h, hora de Ecuador) y cómo terminó.
import { ZONA } from "./zona.js";

const PARTES = new Intl.DateTimeFormat("en-CA", {
  timeZone: ZONA, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

function partes(fecha) {
  const p = Object.fromEntries(PARTES.formatToParts(fecha).map((x) => [x.type, x.value]));
  return { dia: `${p.year}-${p.month}-${p.day}`, hora: `${p.hour}:${p.minute}`, texto: `${p.day}/${p.month}/${p.year}` };
}

// «hoy a las 10:05», «ayer a las 22:40» o «el 18/11/2026 a las 09:15».
export function cuandoDesplegado(iso, ahora = new Date()) {
  const fecha = iso ? new Date(iso) : null;
  if (!fecha || Number.isNaN(fecha.getTime())) return "";
  const f = partes(fecha);
  const hoy = partes(ahora).dia;
  const ayer = partes(new Date(ahora.getTime() - 24 * 3600 * 1000)).dia;
  const dia = f.dia === hoy ? "hoy" : f.dia === ayer ? "ayer" : `el ${f.texto}`;
  return `${dia} a las ${f.hora}`;
}

// Resultado de la ejecución, traducido.
export function resultadoDesplegado({ estado, conclusion } = {}) {
  if (estado && estado !== "completed") return "en_curso";
  if (conclusion === "success") return "correcto";
  if (conclusion === "cancelled") return "cancelado";
  if (["failure", "timed_out", "startup_failure"].includes(conclusion)) return "errores";
  return "terminado";
}

// Texto principal del aviso.
export function textoDesplegado(ejecucion, ahora = new Date()) {
  const cuando = cuandoDesplegado(ejecucion?.iniciada_en, ahora);
  const en = cuando ? ` ${cuando}` : "";
  switch (resultadoDesplegado(ejecucion)) {
    case "en_curso": return `Este cambio empezó a desplegarse${en} y sigue en curso.`;
    case "correcto": return `Este cambio ya se desplegó${en} y terminó correctamente.`;
    case "errores": return `Este cambio ya se desplegó${en} y terminó con errores.`;
    case "cancelado": return `Este cambio ya se desplegó${en} y el despliegue se canceló.`;
    default: return `Este cambio ya se desplegó${en}.`;
  }
}

export const TEXTO_SECUNDARIO_DESPLEGADO =
  "El análisis se puede hacer, pero no se comparará con un resultado real. Para validar el modelo, elija un cambio " +
  "pendiente de desplegar.";
