import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useNavegacion, useParametros } from "../navegacion.jsx";
import { Alerta } from "./comunes.jsx";
import Resultado from "./Resultado.jsx";

// Pantalla /analisis/<id>: el análisis completo (desde el historial, los
// pendientes o el panel). ?desde=historial|pendientes|panel indica a dónde
// vuelve si no se llegó navegando (enlace directo o F5). Desde el historial no
// se muestra el apartado «Resultado real» (como antes).
const VOLVER = {
  historial: ["/historial", "Volver al historial"],
  pendientes: ["/pendientes", "Volver a pendientes"],
  panel: ["/panel", "Volver al panel"],
};

export default function AnalisisDetalle({ id, modelos }) {
  const { volver } = useNavegacion();
  const desde = useParametros().get("desde");
  const [destino, texto] = VOLVER[desde] || ["/historial", "Volver"];
  const [prediccion, setPrediccion] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setPrediccion(null);
    setError("");
    api.prediccion(id).then(setPrediccion).catch((e) => setError(
      e.estado === 404 ? "El análisis no existe o no tiene permiso para verlo." : e.message,
    ));
  }, [id]);

  return (
    <section className="vista" aria-labelledby="titulo-analisis">
      <h1 id="titulo-analisis">Análisis #{id}</h1>
      <div>
        <button className="boton boton--secundario" type="button" onClick={() => volver(destino)}>
          ← {texto}
        </button>
      </div>
      <Alerta>{error}</Alerta>
      {!prediccion && !error && <p role="status" className="secundario">Cargando análisis…</p>}
      {prediccion && (
        <Resultado key={prediccion.id} prediccion={prediccion} modelos={modelos} mostrarResultadoReal={desde !== "historial"} />
      )}
    </section>
  );
}
