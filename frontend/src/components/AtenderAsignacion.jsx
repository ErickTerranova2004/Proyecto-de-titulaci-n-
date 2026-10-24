import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alerta, DECISIONES, EstadoAsignacion, Fecha, FechaDia, textoPlazo } from "./comunes.jsx";
import Resultado from "./Resultado.jsx";

// "Atender ahora": el análisis original con el mensaje y la fecha del líder, y
// el botón para hacer el nuevo análisis que cumple la asignación.
export default function AtenderAsignacion({ asignacion, modelos, alNuevoAnalisis, alVolver }) {
  const [prediccion, setPrediccion] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.prediccion(asignacion.prediccion).then(setPrediccion).catch((e) => setError(e.message));
  }, [asignacion.prediccion]);

  return (
    <section className="vista" aria-labelledby="titulo-atender">
      <header className="encabezado">
        <h1 id="titulo-atender">Atender asignación</h1>
        <p className="secundario">Desarrollador · análisis original de {asignacion.repositorio}</p>
      </header>
      <div>
        <button className="boton boton--secundario" type="button" onClick={alVolver}>← Volver a mi panel</button>
      </div>

      <section className="tarjeta" aria-labelledby="titulo-indicacion">
        <h2 id="titulo-indicacion">Indicación del líder técnico</h2>
        <dl className="datos">
          <dt>Decisión</dt>
          <dd>{DECISIONES[asignacion.decision]} · {asignacion.lider} · <Fecha valor={asignacion.creada_en} /></dd>
          <dt>Mensaje</dt>
          <dd>{asignacion.mensaje || "Sin mensaje"}</dd>
          <dt>Fecha límite</dt>
          <dd>
            {asignacion.fecha_limite ? <FechaDia valor={asignacion.fecha_limite} /> : "Sin fecha límite"} ·{" "}
            <EstadoAsignacion estado={asignacion.estado} /> {textoPlazo(asignacion)}
          </dd>
        </dl>
        {asignacion.estado !== "cumplida" && (
          <div className="formulario__acciones">
            <button className="boton" type="button" onClick={() => alNuevoAnalisis(asignacion, prediccion)} disabled={!prediccion}>
              Realizar nuevo análisis
            </button>
          </div>
        )}
      </section>

      <Alerta>{error}</Alerta>
      {!prediccion && !error && <p role="status" className="secundario">Cargando el análisis original…</p>}
      {prediccion && <Resultado prediccion={prediccion} modelos={modelos} />}
    </section>
  );
}
