// Resultado real de un análisis: ya no hay botón «Verificar resultado real».
// La vista del análisis consulta GitHub sola (seguimiento en la página) y la
// tarea programada del lote enlaza los pendientes cada 4 h.

export const TEXTO_VERIFICACION_AUTOMATICA =
  "El resultado real se verifica automáticamente cuando el despliegue termina (seguimiento en la página y tarea programada cada 4 h)";

// Mientras la verificación quede pendiente se vuelve a consultar GitHub cada
// INTERVALO_SEGUIMIENTO, como máximo DURACION_SEGUIMIENTO desde que se abrió.
export const INTERVALO_SEGUIMIENTO = 30_000;
export const DURACION_SEGUIMIENTO = 2 * 60 * 60 * 1000;

// Qué hacer con la respuesta de /verificar/: «enlazado» (llegó el análisis con
// su ejecución real), «seguir» (otra consulta en INTERVALO_SEGUIMIENTO) o
// «detener» (se agotó DURACION_SEGUIMIENTO; la tarea programada lo enlazará).
export function siguientePaso(respuesta, transcurrido) {
  if (respuesta?.estado !== "pendiente") return "enlazado";
  return transcurrido >= DURACION_SEGUIMIENTO ? "detener" : "seguir";
}
