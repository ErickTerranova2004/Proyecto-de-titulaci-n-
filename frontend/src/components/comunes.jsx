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

// Fechas límite: solo días (sin hora) en la zona del backend.
const ZONA = "America/Guayaquil";

// Fecha de hoy en America/Guayaquil con formato AAAA-MM-DD (input type="date").
export function hoyLocal() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: ZONA }).format(new Date());
}

// Muestra una fecha AAAA-MM-DD sin convertirla de zona horaria.
export function FechaDia({ valor }) {
  if (!valor) return "—";
  const [a, m, d] = valor.split("-").map(Number);
  return (
    <time dateTime={valor} className="font-mono">
      {new Date(a, m - 1, d).toLocaleDateString("es-EC", { day: "2-digit", month: "short", year: "numeric" })}
    </time>
  );
}

// Estados de AsignacionSerializer.estado. Reutiliza los colores de nivel.
const ESTADOS_ASIGNACION = {
  pendiente: ["Pendiente", "medio"],
  por_vencer: ["Por vencer", "alto"],
  vencida: ["Vencida", "alto"],
  cumplida: ["Cumplida", "bajo"],
};

// Texto del recordatorio: vence mañana, vence hoy, vencida o los días que faltan.
export function textoPlazo(asignacion) {
  const { estado, dias_restantes: dias } = asignacion;
  if (estado === "cumplida") return "Cumplida";
  if (dias === null || dias === undefined) return "Sin fecha límite";
  if (dias < 0) return `Vencida hace ${-dias} día${dias === -1 ? "" : "s"}`;
  if (dias === 0) return "Vence hoy";
  if (dias === 1) return "Vence mañana";
  return `Faltan ${dias} días`;
}

export function EstadoAsignacion({ estado }) {
  if (!estado) return null;
  const [texto, nivel] = ESTADOS_ASIGNACION[estado] ?? [estado, "medio"];
  return (
    <span className={`nivel nivel--${nivel}`}>
      <span className="nivel__muestra" aria-hidden="true" />
      {texto}
    </span>
  );
}

// Respuesta del desarrollador: nuevo análisis, nivel anterior frente al nuevo
// y su comentario. Lo usan Pendientes y el Historial del equipo.
export function RespuestaDesarrollador({ nivelOriginal, respuesta, comentario }) {
  if (!respuesta) return null;
  return (
    <span className="secundario">
      Cumplida con el análisis #{respuesta.id}: <NivelRiesgo nivel={nivelOriginal} /> → <NivelRiesgo nivel={respuesta.nivel} />
      {comentario && <> · «{comentario}»</>}
    </span>
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
