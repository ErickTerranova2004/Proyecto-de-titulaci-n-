// Métricas de evaluación de una versión del modelo (VersionModelo.metadatos).
// v1 y v1.1 guardan `metricas_prueba` (partición temporal de prueba); v2
// guarda `metricas_validacion` por modelo (GroupKFold por repositorio) y el
// elegido en `modelo`. Se normalizan los nombres para mostrarlas igual.

const ALIAS = {
  "PR-AUC": ["PR-AUC"],
  "ROC-AUC": ["ROC-AUC"],
  Precision: ["Precision", "Precisión"],
  Recall: ["Recall", "Recall y=1"],
  F1: ["F1"],
  Brier: ["Brier"],
};

export const METRICAS = Object.keys(ALIAS);

export function metricasModelo(metadatos) {
  const meta = metadatos ?? {};
  let origen = null;
  let valores = null;
  if (meta.metricas_prueba) {
    origen = "prueba temporal";
    valores = meta.metricas_prueba;
  } else if (meta.metricas_validacion?.[meta.modelo]) {
    origen = "validación por repositorio";
    valores = meta.metricas_validacion[meta.modelo];
  }
  const normalizadas = Object.fromEntries(
    METRICAS.map((clave) => {
      const nombre = ALIAS[clave].find((n) => typeof valores?.[n] === "number");
      return [clave, nombre ? valores[nombre] : null];
    }),
  );
  return { origen, valores: normalizadas };
}

export function formatoMetrica(valor) {
  return typeof valor === "number" ? valor.toFixed(3) : "—";
}
