import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alerta, Fecha, NIVELES, porcentaje } from "./comunes.jsx";

import { formatoMetrica, METRICAS, metricasModelo } from "../metricas.js";
import { formatoIntervalo } from "../sombra.js";
import { confirmacionValida } from "../modeloActivo.js";

export default function Modelos({ modelos, esAdmin, alCambiar }) {
  const [error, setError] = useState("");
  // Versión que se está confirmando (se escribe su nombre para activarla).
  const [confirmando, setConfirmando] = useState(null);
  const [activando, setActivando] = useState(false);

  async function activar(modelo, confirmacion) {
    setError("");
    setActivando(true);
    try {
      await api.activarModelo(modelo.id, confirmacion);
      setConfirmando(null);
      await alCambiar();
    } catch (e) {
      setError(e.message);
    } finally {
      setActivando(false);
    }
  }

  return (
    <section className="vista" aria-labelledby="titulo-modelos">
      <header className="encabezado">
        <h1 id="titulo-modelos">Versiones del modelo</h1>
        <p className="secundario">
          Modelos registrados. Las métricas de v1 corresponden a su partición temporal de prueba; las de v2, a
          la validación por repositorio (repositorios no vistos). No son comparables entre sí.
        </p>
      </header>
      <Alerta>{error}</Alerta>
      <div className="tarjeta tarjeta--tabla">
      <div className="tabla-contenedor">
        <table>
          <caption className="solo-lector">Versiones del modelo y sus métricas de prueba</caption>
          <thead>
            <tr>
              <th scope="col">Versión</th>
              <th scope="col">Modelo</th>
              <th scope="col">Estado</th>
              <th scope="col" className="numero">Filas de entrenamiento</th>
              <th scope="col">Evaluación</th>
              {METRICAS.map((m) => (
                <th key={m} scope="col" className="numero">{m}</th>
              ))}
              <th scope="col">Límites de riesgo (medio / alto)</th>
              <th scope="col">Registrado</th>
              {esAdmin && <th scope="col"><span className="solo-lector">Acciones</span></th>}
            </tr>
          </thead>
          <tbody>
            {modelos.map((m) => {
              const { origen, valores: met } = metricasModelo(m.metadatos);
              const limites = m.metadatos.limites_riesgo;
              return (
                <tr key={m.id}>
                  <td><code className="codigo">{m.version}</code></td>
                  <td><strong>{m.nombre_modelo}</strong></td>
                  <td>
                    {m.activo ? <span className="estado estado--activo">Activo</span> : <span className="secundario">Inactivo</span>}
                    {esAdmin && m.ultima_activacion && (
                      <span className="secundario modelos__activacion">
                        Activado por {m.ultima_activacion.usuario} el <Fecha valor={m.ultima_activacion.fecha} />
                      </span>
                    )}
                  </td>
                  <td className="numero">{m.metadatos.filas_entrenamiento}</td>
                  <td>
                    {origen ?? "—"}
                    {m.metadatos.filas_prueba != null && ` (${m.metadatos.filas_prueba} filas)`}
                    {m.metadatos.repositorios != null && ` (${m.metadatos.repositorios} repositorios)`}
                  </td>
                  {METRICAS.map((clave) => (
                    <td key={clave} className="numero destacado">{formatoMetrica(met[clave])}</td>
                  ))}
                  <td className="font-mono">{porcentaje(limites.medio)} / {porcentaje(limites.alto)}</td>
                  <td><Fecha valor={m.registrado_en} /></td>
                  {esAdmin && (
                    <td>
                      {m.activo ? (
                        <span className="secundario">En uso</span>
                      ) : !m.activable ? (
                        // Sin fecha de corte (v1): solo se evalúa en sombra; el backend también lo rechaza.
                        <span className="secundario" title={m.motivo_no_activable ?? undefined}>
                          Solo evaluación en sombra
                        </span>
                      ) : (
                        <button
                          className="boton boton--secundario boton--pequeno"
                          type="button"
                          onClick={() => { setError(""); setConfirmando(m); }}
                          disabled={activando}
                        >
                          Activar…
                          <span className="solo-lector"> {m.version}</span>
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      </div>
      {esAdmin && confirmando && (
        <ConfirmarActivacion
          modelo={confirmando}
          activo={modelos.find((m) => m.activo)}
          activando={activando}
          alConfirmar={(texto) => activar(confirmando, texto)}
          alCancelar={() => setConfirmando(null)}
        />
      )}
      {esAdmin && <Supervision modelos={modelos} />}
    </section>
  );
}

// Confirmación para activar una versión: hay que escribir su nombre. La
// activación queda registrada (quién y cuándo) en trx_activacion_modelo.
export function ConfirmarActivacion({ modelo, activo, activando, alConfirmar, alCancelar }) {
  const [texto, setTexto] = useState("");
  const valido = confirmacionValida(texto, modelo.version);
  return (
    <form
      className="tarjeta confirmar-activacion"
      aria-labelledby="titulo-confirmar-activacion"
      onSubmit={(e) => {
        e.preventDefault();
        if (valido && !activando) alConfirmar(texto);
      }}
    >
      <h2 id="titulo-confirmar-activacion">Activar la versión {modelo.version}</h2>
      <p>
        La versión activa hace todos los análisis nuevos y el análisis en lote
        {activo ? <> y sustituye a <code className="codigo">{activo.version}</code></> : null}. Quedará registrado quién
        la activó y cuándo.
      </p>
      <label className="campo confirmar-activacion__campo">
        <span>
          Para confirmar, escriba <code className="codigo">{modelo.version}</code>
        </span>
        <input
          type="text"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          autoComplete="off"
          spellCheck={false}
          autoFocus
        />
      </label>
      <div className="confirmar-activacion__acciones">
        <button className="boton" type="submit" disabled={!valido || activando}>
          {activando ? "Activando…" : `Activar ${modelo.version}`}
        </button>
        <button className="boton boton--secundario" type="button" onClick={alCancelar} disabled={activando}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

// Compara las predicciones emitidas con los resultados reales verificados en
// GitHub. Solo cuentan las ejecuciones evaluables (completado / no completado).
function Supervision({ modelos }) {
  const [datos, setDatos] = useState({});
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all(modelos.map((m) => api.supervision(m.id)))
      .then((lista) => setDatos(Object.fromEntries(lista.map((s, i) => [modelos[i].id, s]))))
      .catch((e) => setError(e.message));
  }, [modelos]);

  const tasa = (n) => (n.tasa == null ? "—" : `${porcentaje(n.tasa)} (${n.no_completados}/${n.evaluables})`);

  return (
    <section aria-labelledby="titulo-supervision">
      <h2 id="titulo-supervision">Supervisión con resultados reales</h2>
      <Alerta>{error}</Alerta>
      <div className="tabla-contenedor">
        <table>
          <caption>
            Tasa de despliegues no completados observada por nivel de riesgo en las predicciones verificadas de la
            plataforma. Con pocos casos evaluables la tasa no es concluyente.
          </caption>
          <thead>
            <tr>
              <th scope="col">Versión</th>
              <th scope="col" className="numero">Predicciones</th>
              <th scope="col" className="numero">Verificadas</th>
              <th scope="col" className="numero">Evaluables</th>
              {Object.values(NIVELES).map((n) => (
                <th key={n} scope="col" className="numero">Nivel {n}</th>
              ))}
              <th scope="col" className="numero">Brier</th>
            </tr>
          </thead>
          <tbody>
            {modelos.map((m) => {
              const s = datos[m.id];
              if (!s) return null;
              return (
                <tr key={m.id}>
                  <td>{s.version}</td>
                  <td className="numero">{s.predicciones}</td>
                  <td className="numero">{s.verificadas}</td>
                  <td className="numero">{s.evaluables}</td>
                  {Object.keys(NIVELES).map((n) => (
                    <td key={n} className="numero">{tasa(s.por_nivel[n])}</td>
                  ))}
                  <td className="numero">{s.brier == null ? "—" : s.brier.toFixed(3)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <ComparacionSombra />
    </section>
  );
}

// El modelo activo frente a las versiones visibles evaluadas en sombra, sobre exactamente las
// mismas ejecuciones evaluables (riesgo/services/supervision.comparacion).
function ComparacionSombra() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.comparacionSombra().then(setDatos).catch((e) => setError(e.message));
  }, []);

  const tasa = (n) =>
    n.tasa == null ? "—" : `${porcentaje(n.tasa)} (${n.no_completados}/${n.evaluables}) ${n.ic95 ? `[${porcentaje(n.ic95[0])} – ${porcentaje(n.ic95[1])}]` : ""}`;
  const indicador = (m) => `${m.valor == null ? "—" : m.valor.toFixed(3)} ${formatoIntervalo(m.ic95)}`;

  return (
    <section className="sombra" aria-labelledby="titulo-sombra">
      <h3 id="titulo-sombra">Comparación con las versiones anteriores (mismas ejecuciones)</h3>
      <Alerta>{error}</Alerta>
      {!datos && !error && <p role="status" className="secundario">Calculando la comparación…</p>}
      {datos && (
        <>
          <div className="tabla-contenedor">
            <table>
              <caption>
                {datos.ejecuciones} ejecuciones evaluables, {datos.no_completados} no completadas. Entre corchetes, IC 95 %
                (Wilson para las tasas; bootstrap pareado de {datos.remuestreos} remuestreos para Brier y PR-AUC).
              </caption>
              <thead>
                <tr>
                  <th scope="col">Versión</th>
                  {Object.values(NIVELES).map((n) => (
                    <th key={n} scope="col" className="numero">Tasa de fallo · nivel {n.toLowerCase()}</th>
                  ))}
                  <th scope="col" className="numero">Brier (menor es mejor)</th>
                  <th scope="col" className="numero">PR-AUC (mayor es mejor)</th>
                </tr>
              </thead>
              <tbody>
                {datos.modelos.map((m) => (
                  <tr key={m.version}>
                    <th scope="row">
                      {m.version}
                    </th>
                    {Object.keys(NIVELES).map((n) => (
                      <td key={n} className="numero">{tasa(m.por_nivel[n])}</td>
                    ))}
                    <td className="numero">{indicador(m.brier)}</td>
                    <td className="numero">{indicador(m.pr_auc)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {datos.sin_sombra > 0 && (
            <p className="secundario nota-pie">
              {datos.sin_sombra} ejecuciones evaluables recientes de {datos.referencia} aún no tienen predicción en sombra
              (se crean en la próxima pasada del lote) y no entran en la comparación.
            </p>
          )}
        </>
      )}
    </section>
  );
}
