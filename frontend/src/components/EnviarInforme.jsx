import { useContext, useId, useState } from "react";
import { api } from "../api.js";
import { MAX_COMENTARIO, MIN_COMENTARIO, problemaComentario } from "../informes.js";
import { AbrirInformeContexto, Alerta } from "./comunes.jsx";

// «Enviar informe al líder» de una asignación cumplida con un nuevo análisis.
// `asignacion`: { id, informe?, respuesta_desarrollador? }. Si ya hay informe,
// muestra su número y el enlace para abrirlo.
export default function EnviarInforme({ asignacion, alEnviar, pequeno = false }) {
  const abrir = useContext(AbrirInformeContexto);
  const id = useId();
  const [abierto, setAbierto] = useState(false);
  const [comentario, setComentario] = useState(asignacion.respuesta_desarrollador || "");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const [enviado, setEnviado] = useState(asignacion.informe || null);
  const clase = `boton ${pequeno ? "boton--pequeno" : ""}`;

  if (enviado) {
    return (
      <span className="informe-enviado">
        Informe <strong>{enviado.numero}</strong> enviado al líder.{" "}
        {abrir && (
          <button className={`boton boton--secundario ${pequeno ? "boton--pequeno" : ""}`} type="button" onClick={() => abrir(enviado.id)}>
            Ver informe
          </button>
        )}
      </span>
    );
  }

  if (!abierto) {
    return (
      <button className={clase} type="button" onClick={() => setAbierto(true)}>
        Enviar informe al líder
      </button>
    );
  }

  async function enviar(e) {
    e.preventDefault();
    const problema = problemaComentario(comentario);
    if (problema) {
      setError(problema);
      return;
    }
    setEnviando(true);
    setError("");
    try {
      const informe = await api.enviarInforme(asignacion.id, comentario.trim());
      setEnviado({ id: informe.id, numero: informe.numero });
      alEnviar?.(informe);
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="enviar-informe" onSubmit={enviar}>
      <label htmlFor={`${id}-comentario`}>
        <strong>¿Qué cambios hizo?</strong> <span className="secundario">(obligatorio, al menos {MIN_COMENTARIO} caracteres)</span>
      </label>
      <textarea
        id={`${id}-comentario`}
        rows={4}
        maxLength={MAX_COMENTARIO}
        value={comentario}
        onChange={(e) => setComentario(e.target.value)}
        required
        aria-invalid={Boolean(error)}
        placeholder="Por ejemplo: corregí el paso de despliegue del YAML y añadí pruebas de humo."
      />
      <Alerta>{error}</Alerta>
      <div className="enviar-informe__acciones">
        <button className={clase} type="submit" disabled={enviando}>
          {enviando ? "Enviando…" : "Enviar informe"}
        </button>
        <button className={`boton boton--secundario ${pequeno ? "boton--pequeno" : ""}`} type="button" onClick={() => setAbierto(false)}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
