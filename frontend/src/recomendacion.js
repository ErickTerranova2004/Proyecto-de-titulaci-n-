// Recomendación automática de la plataforma (Prediccion.recomendacion) y su
// relación con la decisión del líder técnico. La recomendación la calcula el
// backend (predictor.recomendacion_de): nivel alto → solicitar revisión
// previa; bajo o medio → permitir el despliegue.

export const RECOMENDACIONES = {
  permitir: "Permitir el despliegue",
  solicitar_revision: "Solicitar revisión previa",
};

// Decisión del líder que equivale a aceptar cada recomendación.
const DECISION_RECOMENDADA = { permitir: "autorizar", solicitar_revision: "solicitar_revision" };

export function decisionRecomendada(recomendacion) {
  return DECISION_RECOMENDADA[recomendacion] ?? "";
}

// true si la decisión acepta la recomendación, false si la cambia y null si
// el análisis no tiene recomendación (anterior a esta funcionalidad).
export function aceptaRecomendacion(recomendacion, decision) {
  const recomendada = decisionRecomendada(recomendacion);
  if (!recomendada || !decision) return null;
  return decision === recomendada;
}
