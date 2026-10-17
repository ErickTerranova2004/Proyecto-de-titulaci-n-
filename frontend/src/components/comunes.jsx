// Elementos reutilizables. Los textos de nivel son obligatorios: el riesgo
// nunca se comunica solo con color.

export const NIVELES = { bajo: "Bajo", medio: "Medio", alto: "Alto" };

export function porcentaje(valor, decimales = 1) {
  return `${(valor * 100).toFixed(decimales)} %`;
}

export function Fecha({ valor }) {
  if (!valor) return "—";
  return <time dateTime={valor}>{new Date(valor).toLocaleString("es-EC")}</time>;
}

export function NivelRiesgo({ nivel, grande = false }) {
  return (
    <span className={`nivel nivel--${nivel}${grande ? " nivel--grande" : ""}`}>
      <span className="nivel__muestra" aria-hidden="true" />
      {NIVELES[nivel] ?? nivel}
    </span>
  );
}

export function Alerta({ children }) {
  if (!children) return null;
  return (
    <p className="alerta" role="alert">
      {children}
    </p>
  );
}
