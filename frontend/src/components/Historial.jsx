import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alerta, DECISIONES, Fecha, NivelRiesgo, porcentaje } from "./comunes.jsx";
import Resultado, { ETIQUETAS } from "./Resultado.jsx";

export default function Historial({ modelos }) {
  const [filas, setFilas] = useState(null);
  const [error, setError] = useState("");
  const [seleccion, setSeleccion] = useState(null);

  const cargar = () => api.historial().then(setFilas).catch((e) => setError(e.message));
  useEffect(() => {
    cargar();
  }, []);

  if (seleccion) {
    return (
      <section className="vista" aria-labelledby="titulo-historial">
        <h1 id="titulo-historial">Historial de análisis</h1>
        <div>
          <button className="boton boton--secundario" type="button" onClick={() => { setSeleccion(null); cargar(); }}>
            ← Volver al historial
          </button>
        </div>
        <Resultado prediccion={seleccion} modelos={modelos} />
      </section>
    );
  }

  return (
    <section className="vista" aria-labelledby="titulo-historial">
      <header className="encabezado">
        <h1 id="titulo-historial">Historial de análisis</h1>
        <p className="secundario">
          Análisis visibles según su rol y sus repositorios asignados, del más reciente al más antiguo.
        </p>
      </header>
      <Alerta>{error}</Alerta>
      {!filas && !error && <p role="status" className="secundario">Cargando historial…</p>}
      {filas && !filas.length && (
        <div className="tarjeta vacio">
          <p className="secundario">Todavía no hay análisis visibles para su usuario.</p>
        </div>
      )}
      {filas && filas.length > 0 && (
        <div className="tarjeta tarjeta--tabla">
          <div className="tabla-contenedor">
            <table>
              <caption className="solo-lector">Historial de análisis</caption>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Repositorio</th>
                  <th scope="col">Workflow</th>
                  <th scope="col">Commit</th>
                  <th scope="col">Riesgo</th>
                  <th scope="col" className="numero">Probabilidad</th>
                  <th scope="col">Resultado real</th>
                  <th scope="col">Decisión</th>
                  <th scope="col">Usuario</th>
                  <th scope="col"><span className="solo-lector">Acciones</span></th>
                </tr>
              </thead>
              <tbody>
                {filas.map((p) => (
                  <tr key={p.id}>
                    <td><Fecha valor={p.creada_en} /></td>
                    <td><strong>{p.repositorio}</strong></td>
                    <td className="secundario" title={p.workflow_path}>
                      {p.workflow_path.replace(".github/workflows/", "")}
                    </td>
                    <td><code>{p.head_sha.slice(0, 7)}</code></td>
                    <td><NivelRiesgo nivel={p.nivel} /></td>
                    <td className="numero destacado">{porcentaje(p.probabilidad)}</td>
                    <td>{p.ejecucion_real ? ETIQUETAS[p.ejecucion_real.etiqueta] || p.ejecucion_real.etiqueta : "Pendiente"}</td>
                    <td>{p.decisiones?.length ? DECISIONES[p.decisiones[0].decision] : "Sin decisión"}</td>
                    <td className="secundario">{p.usuario}</td>
                    <td>
                      <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => setSeleccion(p)}>
                        Ver detalle<span className="solo-lector"> del análisis {p.id}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
