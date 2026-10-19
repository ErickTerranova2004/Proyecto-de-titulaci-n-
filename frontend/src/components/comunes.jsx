// Elementos reutilizables. Los textos de nivel son obligatorios: el riesgo
// nunca se comunica solo con color.
import { createContext, useContext } from "react";

// Usuario autenticado (respuesta de /api/yo/) disponible para todas las vistas.
export const UsuarioContexto = createContext(null);

export function useRoles() {
  const roles = useContext(UsuarioContexto)?.roles ?? [];
  return {
    puedeDecidir: roles.includes("lider_tecnico") || roles.includes("administrador"),
  };
}

// Textos de presentación de DecisionDespliegue.decision.
export const DECISIONES = {
  autorizar: "Autorizar el despliegue",
  posponer: "Posponer el despliegue",
  solicitar_revision: "Solicitar revisión adicional",
};

export const NIVELES = { bajo: "Bajo", medio: "Medio", alto: "Alto" };

export function porcentaje(valor, decimales = 1) {
  return `${(valor * 100).toFixed(decimales)} %`;
}

export function Fecha({ valor }) {
  if (!valor) return "—";
  return (
    <time dateTime={valor} className="font-mono">
      {new Date(valor).toLocaleString("es-EC", { dateStyle: "short", timeStyle: "short" })}
    </time>
  );
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
