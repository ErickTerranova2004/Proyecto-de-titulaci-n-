// Comparación en sombra (Modelos → Supervisión): el modelo activo y las
// versiones no activas sobre las mismas ejecuciones evaluables. La API da,
// para cada versión en sombra, la diferencia (versión − referencia) con su
// IC 95 % bootstrap pareado. Brier: menor es mejor. PR-AUC: mayor es mejor.

export function formatoIntervalo(ic, decimales = 3) {
  if (!ic) return "—";
  return `[${ic[0].toFixed(decimales)} – ${ic[1].toFixed(decimales)}]`;
}

// Resultado de la referencia frente a `modelo` en una métrica: «mejor»,
// «peor» o «sin_diferencia» (el IC de la diferencia incluye el 0).
export function resultadoReferencia(modelo, metrica) {
  const ic = modelo?.diferencia_con_referencia?.[metrica]?.ic95;
  if (!ic) return "sin_diferencia";
  const menorEsMejor = metrica === "brier";
  if (ic[1] < 0) return menorEsMejor ? "peor" : "mejor";
  if (ic[0] > 0) return menorEsMejor ? "mejor" : "peor";
  return "sin_diferencia";
}

const TEXTOS = {
  mejor: "mejor (el IC 95 % de la diferencia no incluye el 0)",
  peor: "peor (el IC 95 % de la diferencia no incluye el 0)",
  sin_diferencia: "sin diferencia concluyente (el IC 95 % de la diferencia incluye el 0)",
};

export function textoComparacion(referencia, modelo, nombreModelo = modelo.version) {
  return `${referencia} frente a ${nombreModelo}: Brier ${TEXTOS[resultadoReferencia(modelo, "brier")]}; PR-AUC ${
    TEXTOS[resultadoReferencia(modelo, "pr_auc")]}.`;
}
