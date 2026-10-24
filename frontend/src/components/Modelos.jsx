import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alerta, Fecha, NIVELES, porcentaje } from "./comunes.jsx";

const METRICAS = ["PR-AUC", "ROC-AUC", "Precision", "Recall", "F1", "Brier"];

export default function Modelos({ modelos, esAdmin, alCambiar }) {
  const [error, setError] = useState("");
  const [activando, setActivando] = useState(null);

  async function activar(id) {
    setError("");
    setActivando(id);
    try {
      await api.activarModelo(id);
      await alCambiar();
    } catch (e) {
      setError(e.message);
    } finally {
      setActivando(null);
    }
  }

  return (
    <section className="vista" aria-labelledby="titulo-modelos">
      <header className="encabezado">
        <h1 id="titulo-modelos">Versiones del modelo</h1>
        <p className="secundario">
          Modelos registrados. Las métricas corresponden a la partición temporal de prueba de cada versión.
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
              <th scope="col" className="numero">Filas de prueba</th>
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
              const met = m.metadatos.metricas_prueba;
              const limites = m.metadatos.limites_riesgo;
              return (
                <tr key={m.id}>
                  <td><code className="codigo">{m.version}</code></td>
                  <td><strong>{m.nombre_modelo}</strong></td>
                  <td>{m.activo ? <span className="estado estado--activo">Activo</span> : <span className="secundario">Inactivo</span>}</td>
                  <td className="numero">{m.metadatos.filas_entrenamiento}</td>
                  <td className="numero">{m.metadatos.filas_prueba}</td>
                  {METRICAS.map((clave) => (
                    <td key={clave} className="numero destacado">{met[clave].toFixed(3)}</td>
                  ))}
                  <td className="font-mono">{porcentaje(limites.medio)} / {porcentaje(limites.alto)}</td>
                  <td><Fecha valor={m.registrado_en} /></td>
                  {esAdmin && (
                    <td>
                      {m.activo ? (
                        <span className="secundario">En uso</span>
                      ) : (
                        <button
                          className="boton boton--secundario boton--pequeno"
                          type="button"
                          onClick={() => activar(m.id)}
                          disabled={activando !== null}
                        >
                          {activando === m.id ? "Activando…" : "Activar"}
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
      {esAdmin && <Supervision modelos={modelos} />}
    </section>
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
      {modelos.map((m) => {
        const n = datos[m.id]?.predicciones_demostracion;
        return n ? (
          <p key={m.id} className="secundario nota-pie">
            {datos[m.id].version}: incluye {n} predicciones de repositorios de demostración (no son validación del modelo).
          </p>
        ) : null;
      })}
    </section>
  );
}
