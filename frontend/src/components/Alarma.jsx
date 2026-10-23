// Alarma de asignaciones para el desarrollador, dentro de la aplicación.
// Consulta GET /api/asignaciones/ cada 60 s y al volver a la pestaña. Sin
// correo ni notificaciones push, solo avisa mientras la aplicación está abierta.
import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { Alerta, DECISIONES, EstadoAsignacion, FechaDia, NivelRiesgo, textoPlazo } from "./comunes.jsx";

const INTERVALO_MS = 60 * 1000;
const URGENTES = ["por_vencer", "vencida"];

const soportaNotificaciones = () => typeof window !== "undefined" && "Notification" in window;

function notificar(titulo, cuerpo) {
  if (soportaNotificaciones() && Notification.permission === "granted") {
    new Notification(titulo, { body: cuerpo, tag: `asignacion-${titulo}` });
  }
}

export function useAsignaciones(activo) {
  const [lista, setLista] = useState(null);
  const [error, setError] = useState("");
  const [permiso, setPermiso] = useState(soportaNotificaciones() ? Notification.permission : "no-soportado");
  // Estado conocido de cada asignación, para avisar solo de cambios.
  const conocidas = useRef(null);

  function recargar() {
    return api
      .asignaciones()
      .then((nuevas) => {
        setError("");
        const previas = conocidas.current;
        if (previas) {
          nuevas.forEach((a) => {
            if (a.estado === "cumplida") return;
            if (!previas.has(a.id)) {
              notificar(`Nueva asignación: ${a.repositorio}`, `${textoPlazo(a)}. ${a.mensaje || ""}`.trim());
            } else if (URGENTES.includes(a.estado) && previas.get(a.id) !== a.estado) {
              notificar(`Asignación ${a.estado === "vencida" ? "vencida" : "por vencer"}: ${a.repositorio}`, textoPlazo(a));
            }
          });
        }
        conocidas.current = new Map(nuevas.map((a) => [a.id, a.estado]));
        setLista(nuevas);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    if (!activo) return undefined;
    recargar();
    const intervalo = setInterval(recargar, INTERVALO_MS);
    const alVolver = () => {
      if (document.visibilityState === "visible") recargar();
    };
    document.addEventListener("visibilitychange", alVolver);
    window.addEventListener("focus", alVolver);
    return () => {
      clearInterval(intervalo);
      document.removeEventListener("visibilitychange", alVolver);
      window.removeEventListener("focus", alVolver);
    };
  }, [activo]);

  // El permiso se pide solo tras una acción del usuario (botón).
  async function pedirPermiso() {
    if (!soportaNotificaciones()) return;
    setPermiso(await Notification.requestPermission());
  }

  async function marcar(asignacion, accion) {
    setError("");
    try {
      await (accion === "cumplida" ? api.marcarCumplida(asignacion.id) : api.marcarVista(asignacion.id));
      await recargar();
    } catch (e) {
      setError(e.message);
    }
  }

  const pendientes = (lista ?? []).filter((a) => a.estado !== "cumplida");
  return { lista, pendientes, error, permiso, pedirPermiso, marcar, recargar };
}

// Campana con contador de asignaciones sin cumplir.
export function Campana({ pendientes, alAbrir }) {
  const n = pendientes.length;
  const urgentes = pendientes.filter((a) => URGENTES.includes(a.estado)).length;
  return (
    <button
      className="boton boton--secundario boton--pequeno"
      type="button"
      onClick={alAbrir}
      aria-label={`Asignaciones: ${n} pendiente${n === 1 ? "" : "s"}${urgentes ? `, ${urgentes} por vencer o vencidas` : ""}`}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
      {n > 0 && <span className={`nivel nivel--${urgentes ? "alto" : "medio"}`}>{n}</span>}
    </button>
  );
}

// Aviso al entrar: cuántas asignaciones hay y cuál vence primero.
export function AvisoAsignaciones({ pendientes, alVer, alCerrar }) {
  if (!pendientes.length) return null;
  const proxima = pendientes[0];
  return (
    <div className="nota" role="status">
      <strong>
        Tiene {pendientes.length} asignación{pendientes.length === 1 ? "" : "es"} pendiente
        {pendientes.length === 1 ? "" : "s"}.
      </strong>{" "}
      La más próxima es de {proxima.repositorio}: {textoPlazo(proxima).toLowerCase()} (<FechaDia valor={proxima.fecha_limite} />).{" "}
      <button className="boton boton--secundario boton--pequeno" type="button" onClick={alVer}>Ver mis asignaciones</button>{" "}
      <button className="boton boton--secundario boton--pequeno" type="button" onClick={alCerrar}>Cerrar aviso</button>
    </div>
  );
}

// Tarjeta "Mis asignaciones" de Mi panel, ordenada por fecha límite.
export function MisAsignaciones({ alarma, alVerAnalisis }) {
  const { lista, error, permiso, pedirPermiso, marcar } = alarma;
  return (
    <section className="tarjeta" aria-labelledby="titulo-asignaciones" id="mis-asignaciones">
      <h2 id="titulo-asignaciones">Mis asignaciones</h2>
      <p className="secundario">Tareas del líder técnico con fecha límite, de la más próxima a la más lejana</p>
      <Alerta>{error}</Alerta>
      {permiso === "default" && (
        <p className="secundario">
          <button className="boton boton--secundario boton--pequeno" type="button" onClick={pedirPermiso}>
            Activar avisos del navegador
          </button>{" "}
          para recibir un aviso de asignaciones nuevas o por vencer mientras la aplicación esté abierta.
        </p>
      )}
      {!lista && !error && <p role="status" className="secundario">Cargando asignaciones…</p>}
      {lista && !lista.length && <p className="secundario">No tiene asignaciones con fecha límite.</p>}
      {lista && lista.length > 0 && (
        <ul className="feed">
          {lista.map((a) => (
            <li key={a.id} className={`feed__item feed__item--${a.estado === "cumplida" ? "bajo" : URGENTES.includes(a.estado) ? "alto" : "medio"}`}>
              <div className="feed__texto">
                <strong>{a.repositorio}</strong>
                <span className="secundario">
                  {DECISIONES[a.decision]} · {a.lider} · límite <FechaDia valor={a.fecha_limite} /> · {textoPlazo(a)}
                  {!a.vista && " · nueva"}
                </span>
                {a.mensaje && <span>{a.mensaje}</span>}
                <span>
                  <NivelRiesgo nivel={a.nivel} />{" "}
                  {a.estado !== "cumplida" && (
                    <>
                      {!a.vista && (
                        <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => marcar(a, "vista")}>
                          Marcar como vista<span className="solo-lector"> la asignación de {a.repositorio}</span>
                        </button>
                      )}{" "}
                      <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => marcar(a, "cumplida")}>
                        Marcar como cumplida<span className="solo-lector"> la asignación de {a.repositorio}</span>
                      </button>
                    </>
                  )}
                </span>
              </div>
              <EstadoAsignacion estado={a.estado} />
              <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => alVerAnalisis(a.prediccion)}>
                Ver<span className="solo-lector"> el análisis de {a.repositorio}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
