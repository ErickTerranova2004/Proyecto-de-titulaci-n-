// Embudo «Mis resultados verificados» (panel del desarrollador): de la
// predicción a la ejecución real. Los análisis del repositorio de
// demostración se suman aquí (tienen resultado real de GitHub Actions) y se
// cuentan aparte para indicarlo; no entran en las métricas del modelo.

function evaluable(p) {
  return p.ejecucion_real && p.ejecucion_real.y !== null && p.ejecucion_real.y !== undefined;
}

export function pasosEmbudo(reales, demostracion = []) {
  const todos = [...reales, ...demostracion];
  return {
    total: todos.length,
    verificadas: todos.filter((p) => p.ejecucion_real).length,
    evaluables: todos.filter(evaluable).length,
    noCompletados: todos.filter((p) => evaluable(p) && p.ejecucion_real.y === 1).length,
    demostracion: demostracion.length,
    demostracionVerificadas: demostracion.filter((p) => p.ejecucion_real).length,
  };
}

export function textoDemostracion(pasos) {
  if (!pasos.demostracion) return "";
  return `Incluye ${pasos.demostracion} análisis del repositorio de demostración (${pasos.demostracionVerificadas} con resultado real); no cuentan en las métricas del modelo.`;
}
