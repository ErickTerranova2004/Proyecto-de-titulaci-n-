// Fechas y horas del Planificador en hora de Ecuador (America/Guayaquil),
// sea cual sea la zona del equipo. Las fechas van como AAAA-MM-DD.

export const ZONA = "America/Guayaquil";
// Franja de las horas por defecto y de las mejores ventanas (ambas incluidas).
export const PRIMERA_HORA = 7;
export const ULTIMA_HORA = 20;
// Días que ofrece el selector de día (desde hoy).
export const DIAS_SELECTOR = 7;

const FORMATO = new Intl.DateTimeFormat("en-CA", {
  timeZone: ZONA, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23",
});

// { fecha: "AAAA-MM-DD", hora } del instante `ahora` en Ecuador.
export function momentoLocal(ahora = new Date()) {
  const p = Object.fromEntries(FORMATO.formatToParts(ahora).map((x) => [x.type, x.value]));
  return { fecha: `${p.year}-${p.month}-${p.day}`, hora: Number(p.hour) % 24 };
}

export function sumarDias(fecha, dias) {
  const [a, m, d] = fecha.split("-").map(Number);
  const f = new Date(Date.UTC(a, m - 1, d + dias));
  return f.toISOString().slice(0, 10);
}

// Día de la semana con lunes = 0 (como el backend).
export function diaSemana(fecha) {
  const [a, m, d] = fecha.split("-").map(Number);
  return (new Date(Date.UTC(a, m - 1, d)).getUTCDay() + 6) % 7;
}

// Escenario por defecto: hoy, a la siguiente hora en punto dentro de
// 07:00–20:00; antes de las 07:00, hoy a las 07:00; desde las 20:00, mañana a
// las 07:00. Reintento y pull request, los del análisis base.
export function condicionesIniciales(ahora = new Date(), base = {}) {
  const { fecha, hora } = momentoLocal(ahora);
  const siguiente = hora + 1;
  let inicio = { fecha, hora: siguiente };
  if (siguiente < PRIMERA_HORA) inicio = { fecha, hora: PRIMERA_HORA };
  if (siguiente > ULTIMA_HORA) inicio = { fecha: sumarDias(fecha, 1), hora: PRIMERA_HORA };
  return { ...inicio, es_reintento: Boolean(base.es_reintento), tiene_pr: Boolean(base.tiene_pr) };
}

// Primera hora que se puede elegir en `fecha`: hoy, la siguiente en punto.
export function horaMinima(fecha, ahora = new Date()) {
  const actual = momentoLocal(ahora);
  return fecha === actual.fecha ? actual.hora + 1 : 0;
}

// Días del selector: desde hoy (si aún queda alguna hora) y los siguientes.
export function diasDisponibles(ahora = new Date(), cantidad = DIAS_SELECTOR) {
  const actual = momentoLocal(ahora);
  const primero = actual.hora + 1 <= 23 ? actual.fecha : sumarDias(actual.fecha, 1);
  return Array.from({ length: cantidad }, (_, i) => {
    const fecha = sumarDias(primero, i);
    const distancia = fecha === actual.fecha ? 0 : fecha === sumarDias(actual.fecha, 1) ? 1 : null;
    return { fecha, dia: diaSemana(fecha), relativo: ["Hoy", "Mañana"][distancia] ?? "" };
  });
}

// Al cambiar de día, la hora no puede quedar antes de la mínima de ese día.
export function ajustarHora(condiciones, ahora = new Date()) {
  const minima = horaMinima(condiciones.fecha, ahora);
  return condiciones.hora < minima ? { ...condiciones, hora: Math.min(minima, 23) } : condiciones;
}
