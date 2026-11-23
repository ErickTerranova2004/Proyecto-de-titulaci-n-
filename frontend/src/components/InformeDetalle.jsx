import { useEffect, useState } from "react";
import { api } from "../api.js";
import { valorVariable } from "../informes.js";
import { useNavegacion } from "../navegacion.jsx";
import { textoPuntos } from "../planificador.js";
import { Alerta, DECISIONES, Fecha, FechaDia, NivelRiesgo, porcentaje } from "./comunes.jsx";

const OPCIONES = ["autorizar", "posponer", "solicitar_revision"];

// Informe de cumplimiento completo. Pantalla e impresión comparten el mismo
// contenido; @media print oculta el menú y los botones (clase no-imprimir).
// Pantalla /informes/<id>. «Volver» va atrás si se llegó navegando; si no
// (enlace del correo, F5), a la lista de informes (o al panel si el rol no la
// tiene: lo redirige App).
export default function InformeDetalle({ id, alVolver }) {
  const { volver } = useNavegacion();
  alVolver = alVolver || (() => volver("/informes"));
  const [informe, setInforme] = useState(null);
  const [error, setError] = useState("");
  const [descargando, setDescargando] = useState(false);

  useEffect(() => {
    api.informe(id).then(setInforme).catch((e) => setError(e.message));
  }, [id]);

  async function descargarPdf() {
    setDescargando(true);
    setError("");
    try {
      const { blob, nombre } = await api.pdfInforme(id);
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = nombre;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(e.message);
    } finally {
      setDescargando(false);
    }
  }

  return (
    <section className="vista informe" aria-labelledby="titulo-informe">
      <div className="informe__barra no-imprimir">
        {alVolver && (
          <button className="boton boton--secundario" type="button" onClick={alVolver}>
            ← Volver
          </button>
        )}
        {informe && (
          <div className="panel__acciones">
            <button className="boton boton--secundario" type="button" onClick={() => window.print()}>
              Imprimir
            </button>
            <button className="boton" type="button" onClick={descargarPdf} disabled={descargando}>
              {descargando ? "Generando PDF…" : "Descargar PDF"}
            </button>
          </div>
        )}
      </div>
      <Alerta>{error}</Alerta>
      {!informe && !error && <p role="status" className="secundario">Cargando informe…</p>}
      {informe && <Documento informe={informe} alActualizar={setInforme} />}
    </section>
  );
}

function Fila({ etiqueta, children }) {
  return (
    <div className="informe__fila">
      <dt>{etiqueta}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export function Documento({ informe: c, alActualizar }) {
  const o = c.original;
  const n = c.nuevo;
  const cambio = c.diferencia_puntos > 0 ? "sube" : c.diferencia_puntos < 0 ? "baja" : "igual";
  return (
    <article className="tarjeta informe__documento">
      <header className="informe__encabezado">
        <div>
          <p className="informe__plataforma">{c.plataforma}</p>
          <h1 id="titulo-informe">Informe de cumplimiento {c.numero}</h1>
        </div>
        <dl className="informe__emision">
          <Fila etiqueta="N.º de informe">{c.numero}</Fila>
          <Fila etiqueta="Fecha de emisión"><Fecha valor={c.emitido_en} /></Fila>
        </dl>
      </header>

      <dl className="informe__datos">
        <Fila etiqueta="Repositorio"><strong>{c.repositorio}</strong></Fila>
        <Fila etiqueta="Workflow">{c.workflow}</Fila>
        <Fila etiqueta="Desarrollador">{c.desarrollador}</Fila>
        <Fila etiqueta="Líder técnico">{c.lider}</Fila>
        <Fila etiqueta="Asignación"><Fecha valor={c.indicacion.creada_en} /></Fila>
        <Fila etiqueta="Cumplida"><Fecha valor={c.indicacion.cumplida_en} /></Fila>
        <Fila etiqueta="Informe enviado"><Fecha valor={c.enviado_en} /></Fila>
      </dl>

      <section className="informe__seccion">
        <h2>Indicación del líder</h2>
        <dl className="informe__datos">
          <Fila etiqueta="Acción">{c.indicacion.texto}</Fila>
          <Fila etiqueta="Comentario">{c.indicacion.comentario || "—"}</Fila>
          <Fila etiqueta="Fecha límite">{c.indicacion.fecha_limite ? <FechaDia valor={c.indicacion.fecha_limite} /> : "Sin fecha límite"}</Fila>
        </dl>
      </section>

      <section className="informe__seccion">
        <h2>Análisis original frente al nuevo</h2>
        <table className="informe__tabla">
          <thead>
            <tr>
              <th scope="col"><span className="solo-lector">Dato</span></th>
              <th scope="col">Original (#{o.id})</th>
              <th scope="col">Nuevo (#{n.id})</th>
            </tr>
          </thead>
          <tbody>
            <tr><th scope="row">Fecha</th><td><Fecha valor={o.creada_en} /></td><td><Fecha valor={n.creada_en} /></td></tr>
            <tr><th scope="row">Commit</th><td className="font-mono">{o.commit.slice(0, 12)}</td><td className="font-mono">{n.commit.slice(0, 12)}</td></tr>
            <tr><th scope="row">Probabilidad</th><td>{porcentaje(o.probabilidad)}</td><td>{porcentaje(n.probabilidad)}</td></tr>
            <tr><th scope="row">Nivel</th><td><NivelRiesgo nivel={o.nivel} /></td><td><NivelRiesgo nivel={n.nivel} /></td></tr>
            <tr><th scope="row">Recomendación</th><td>{o.recomendacion_texto}</td><td>{n.recomendacion_texto}</td></tr>
            <tr>
              <th scope="row">Modelo</th>
              <td>{o.modelo_nombre ?? o.version_modelo} <span className="secundario">({o.version_modelo})</span></td>
              <td>{n.modelo_nombre ?? n.version_modelo} <span className="secundario">({n.version_modelo})</span></td>
            </tr>
          </tbody>
        </table>
        <p className={`informe__diferencia informe__diferencia--${cambio}`}>
          Diferencia: <strong>{textoPuntos(c.diferencia_puntos)}</strong>
        </p>
      </section>

      <section className="informe__seccion">
        <h2>Factores que más cambiaron</h2>
        {o.version_modelo !== n.version_modelo && (
          <p className="secundario">
            Los dos análisis se hicieron con modelos distintos: para que la diferencia refleje solo el cambio del commit,
            los factores de ambos se calculan con el modelo del análisis nuevo ({n.modelo_nombre ?? n.version_modelo}).
          </p>
        )}
        {c.factores.length === 0 ? (
          <p className="secundario">No hay diferencias de contribución entre los dos análisis.</p>
        ) : (
          <>
            <table className="informe__tabla">
              <thead>
                <tr>
                  <th scope="col">Variable</th>
                  <th scope="col">Original</th>
                  <th scope="col">Nuevo</th>
                  <th scope="col">Cambio SHAP</th>
                </tr>
              </thead>
              <tbody>
                {c.factores.map((f) => (
                  <tr key={f.variable}>
                    <th scope="row">{f.descripcion}</th>
                    <td>{valorVariable(f.valor_original)}</td>
                    <td>{valorVariable(f.valor_nuevo)}</td>
                    <td className={`informe__shap informe__shap--${f.diferencia > 0 ? "sube" : "baja"}`}>
                      {f.diferencia > 0 ? "+" : "−"}{Math.abs(f.diferencia).toFixed(3)} ({f.diferencia > 0 ? "sube" : "baja"} el riesgo)
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="secundario nota-pie">
              Diferencia de la contribución SHAP de cada variable (nuevo menos original); positiva sube el riesgo.
            </p>
          </>
        )}
      </section>

      <section className="informe__seccion">
        <h2>Comentario del desarrollador</h2>
        <p className="informe__texto">{c.comentario}</p>
      </section>

      <section className="informe__seccion">
        <h2>Análisis de la IA del análisis nuevo</h2>
        <p className="informe__texto">{c.ia.resumen || "Sin resumen de la IA."}</p>
        {c.ia.recomendaciones.length > 0 && (
          <ul>
            {c.ia.recomendaciones.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        )}
        {c.ia.origen && <p className="secundario nota-pie">Origen: {c.ia.origen} {c.ia.modelo}</p>}
      </section>

      <section className="informe__seccion">
        <h2>Decisión final del líder</h2>
        {c.decision_final ? (
          <dl className="informe__datos">
            <Fila etiqueta="Decisión"><strong>{c.decision_final.texto}</strong></Fila>
            <Fila etiqueta="Comentario">{c.decision_final.comentario || "—"}</Fila>
            <Fila etiqueta="Registrada por">{c.decision_final.usuario}</Fila>
            <Fila etiqueta="Fecha"><Fecha valor={c.decision_final.creada_en} /></Fila>
          </dl>
        ) : (
          <p className="secundario">Pendiente: el líder aún no registró su decisión final.</p>
        )}
        {c.puede_decidir && <DecisionFinal informe={c} alActualizar={alActualizar} />}
      </section>
    </article>
  );
}

function DecisionFinal({ informe, alActualizar }) {
  const [decision, setDecision] = useState("");
  const [comentario, setComentario] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");

  async function registrar(e) {
    e.preventDefault();
    if (!decision) {
      setError("Elija una decisión.");
      return;
    }
    setEnviando(true);
    setError("");
    try {
      alActualizar(await api.decidirInforme(informe.id, { decision, comentario }));
      setDecision("");
      setComentario("");
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="informe__decidir no-imprimir" onSubmit={registrar}>
      <fieldset>
        <legend>{informe.decision_final ? "Cambiar la decisión final" : "Registrar la decisión final"}</legend>
        <div className="informe__opciones">
          {OPCIONES.map((op) => (
            <label key={op} className="informe__opcion">
              <input type="radio" name="decision-final" value={op} checked={decision === op} onChange={() => setDecision(op)} />
              {DECISIONES[op]}
            </label>
          ))}
        </div>
        <label className="campo">
          <span>Comentario (opcional)</span>
          <textarea rows={3} maxLength={1000} value={comentario} onChange={(e) => setComentario(e.target.value)} />
        </label>
        <Alerta>{error}</Alerta>
        <button className="boton" type="submit" disabled={enviando}>
          {enviando ? "Registrando…" : "Registrar decisión"}
        </button>
      </fieldset>
    </form>
  );
}
