// Alarma de asignaciones para el desarrollador, dentro de la aplicación.
// Consulta GET /api/asignaciones/ cada 60 s y al volver a la pestaña. Sin
// correo ni notificaciones push, solo avisa mientras la aplicación está abierta.
import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { Alerta, DECISIONES, EstadoAsignacion, FechaDia, NivelRiesgo, textoPlazo } from "./comunes.jsx";

const INTERVALO_MS = 60 * 1000;
const URGENTES = ["por_vencer", "vencida"];
const ORDEN_ESTADO = { vencida: 0, por_vencer: 1, pendiente: 2, cumplida: 3 };

const soportaNotificaciones = () => typeof window !== "undefined" && "Notification" in window;
const esAutorizacion = (a) => a.decision === "autorizar";

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
    if (!activo) {
      setLista(null);
      conocidas.current = null;
      return undefined;
    }
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

  const acciones = { vista: api.marcarVista, cumplida: api.marcarCumplida, entendida: api.marcarEntendida };
  async function marcar(asignacion, accion) {
    setError("");
    try {
      await acciones[accion](asignacion.id);
      await recargar();
    } catch (e) {
      setError(e.message);
    }
  }

  // Marca como vistas, sin recargar, las que el desarrollador tiene en pantalla.
  function marcarVistas(asignaciones) {
    const nuevas = asignaciones.filter((a) => !a.vista);
    if (!nuevas.length) return;
    Promise.all(nuevas.map((a) => api.marcarVista(a.id))).then(recargar).catch((e) => setError(e.message));
  }

  const pendientes = (lista ?? [])
    .filter((a) => a.estado !== "cumplida")
    .sort((a, b) => ORDEN_ESTADO[a.estado] - ORDEN_ESTADO[b.estado]);
  return { lista, pendientes, error, permiso, pedirPermiso, marcar, marcarVistas, recargar };
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

// Botón principal de una asignación: con una autorización basta "Entendido";
// posponer o solicitar revisión se atienden con un nuevo análisis.
function BotonAtender({ asignacion, alarma, alAtender, pequeno = false }) {
  const clase = `boton${pequeno ? " boton--pequeno" : ""}`;
  if (esAutorizacion(asignacion)) {
    return (
      <button className={clase} type="button" onClick={() => alarma.marcar(asignacion, "entendida")}>
        Entendido<span className="solo-lector"> la autorización de {asignacion.repositorio}</span>
      </button>
    );
  }
  return (
    <button className={clase} type="button" onClick={() => alAtender(asignacion)}>
      Atender ahora<span className="solo-lector"> la asignación de {asignacion.repositorio}</span>
    </button>
  );
}

// Ventana emergente que aparece sola al entrar al perfil del desarrollador
// mientras tenga asignaciones pendientes. Escape equivale a "Más tarde".
export function VentanaAsignaciones({ alarma, alAtender, alCerrar }) {
  const { pendientes } = alarma;
  const ref = useRef(null);

  // Las asignaciones mostradas quedan como vistas.
  useEffect(() => {
    alarma.marcarVistas(pendientes);
  }, []);

  useEffect(() => {
    const anterior = document.activeElement;
    const enfocables = () => [...ref.current.querySelectorAll("button, [href], textarea, input, select")];
    enfocables()[0]?.focus();
    function teclado(e) {
      if (e.key === "Escape") {
        e.preventDefault();
        alCerrar();
        return;
      }
      if (e.key !== "Tab") return;
      const lista = enfocables();
      const primero = lista[0];
      const ultimo = lista[lista.length - 1];
      if (e.shiftKey && document.activeElement === primero) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primero.focus();
      }
    }
    document.addEventListener("keydown", teclado);
    return () => {
      document.removeEventListener("keydown", teclado);
      anterior?.focus?.();
    };
  }, []);

  if (!pendientes.length) return null;
  const urgentes = pendientes.filter((a) => URGENTES.includes(a.estado)).length;
  return (
    <div className="dialogo">
      <section
        ref={ref}
        className="tarjeta"
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-dialogo-asignaciones"
        aria-describedby="ayuda-dialogo-asignaciones"
      >
        <h2 id="titulo-dialogo-asignaciones">
          Tiene {pendientes.length} asignación{pendientes.length === 1 ? "" : "es"} pendiente{pendientes.length === 1 ? "" : "s"}
        </h2>
        <p id="ayuda-dialogo-asignaciones" className="secundario">
          {urgentes
            ? `${urgentes} vencida${urgentes === 1 ? "" : "s"} o por vencer. `
            : ""}
          Indicaciones del líder técnico sobre sus análisis.
        </p>
        <ul className="feed">
          {pendientes.map((a) => (
            <li key={a.id} className={`feed__item feed__item--${URGENTES.includes(a.estado) ? "alto" : "medio"}`}>
              <div className="feed__texto">
                <strong>{DECISIONES[a.decision]} · {a.repositorio}</strong>
                <span className="secundario">
                  {a.lider} · {a.fecha_limite ? <>límite <FechaDia valor={a.fecha_limite} /> · {textoPlazo(a)}</> : "sin fecha límite"}
                </span>
                {a.mensaje && <span>«{a.mensaje}»</span>}
              </div>
              <EstadoAsignacion estado={a.estado} />
              <BotonAtender asignacion={a} alarma={alarma} alAtender={alAtender} pequeno />
            </li>
          ))}
        </ul>
        <div className="formulario__acciones">
          <button className="boton boton--secundario" type="button" onClick={alCerrar}>Más tarde</button>
        </div>
      </section>
    </div>
  );
}

// Tarjeta "Mis asignaciones" de Mi panel, ordenada por fecha límite.
export function MisAsignaciones({ alarma, alAtender, alVerAnalisis }) {
  const { lista, error, permiso, pedirPermiso, marcar } = alarma;
  return (
    <section className="tarjeta" aria-labelledby="titulo-asignaciones" id="mis-asignaciones">
      <h2 id="titulo-asignaciones">Mis asignaciones</h2>
      <p className="secundario">Indicaciones del líder técnico, de la fecha límite más próxima a la más lejana</p>
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
      {lista && !lista.length && <p className="secundario">No tiene asignaciones.</p>}
      {lista && lista.length > 0 && (
        <ul className="feed">
          {lista.map((a) => (
            <li key={a.id} className={`feed__item feed__item--${a.estado === "cumplida" ? "bajo" : URGENTES.includes(a.estado) ? "alto" : "medio"}`}>
              <div className="feed__texto">
                <strong>{a.repositorio}</strong>
                <span className="secundario">
                  {DECISIONES[a.decision]} · {a.lider} ·{" "}
                  {a.fecha_limite ? <>límite <FechaDia valor={a.fecha_limite} /> · {textoPlazo(a)}</> : "sin fecha límite"}
                  {!a.vista && " · nueva"}
                </span>
                {a.mensaje && <span>{a.mensaje}</span>}
                {a.prediccion_respuesta && (
                  <span className="secundario">
                    Cumplida con el análisis #{a.prediccion_respuesta.id}{" "}
                    <NivelRiesgo nivel={a.nivel_original} /> → <NivelRiesgo nivel={a.prediccion_respuesta.nivel} />
                  </span>
                )}
                {a.estado !== "cumplida" && (
                  <span>
                    <BotonAtender asignacion={a} alarma={alarma} alAtender={alAtender} pequeno />{" "}
                    {!esAutorizacion(a) && (
                      <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => marcar(a, "cumplida")}>
                        Marcar como cumplida sin nuevo análisis<span className="solo-lector"> la asignación de {a.repositorio}</span>
                      </button>
                    )}
                  </span>
                )}
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
