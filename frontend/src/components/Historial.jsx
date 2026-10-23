import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alerta, DECISIONES, EstadoAsignacion, Fecha, FechaDia, NivelRiesgo, porcentaje } from "./comunes.jsx";
import Resultado, { ETIQUETAS } from "./Resultado.jsx";

// Seguimiento de la fecha límite de la última decisión (vista / cumplida).
export function SeguimientoAsignacion({ decision }) {
  if (!decision?.fecha_limite) return <span className="secundario">—</span>;
  return (
    <>
      <EstadoAsignacion estado={decision.estado} />{" "}
      <span className="secundario">
        {decision.cumplida_en ? "Cumplida" : decision.vista_por_desarrollador_en ? "Vista" : "No vista"}
      </span>
    </>
  );
}

// El backend ya filtra por rol: el desarrollador recibe sus análisis y el
// líder los de todos los desarrolladores de sus repositorios asignados.
export default function Historial({
  modelos, titulo = "Historial de análisis", descripcion, mostrarDesarrollador = true, mostrarSeguimiento = false,
}) {
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
        <h1 id="titulo-historial">{titulo}</h1>
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
        <h1 id="titulo-historial">{titulo}</h1>
        <p className="secundario">
          {descripcion ?? "Análisis visibles según su rol y sus repositorios asignados"}, del más reciente al más antiguo.
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
              <caption className="solo-lector">{titulo}</caption>
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
                  {mostrarSeguimiento && <th scope="col">Fecha límite</th>}
                  {mostrarSeguimiento && <th scope="col">Seguimiento</th>}
                  {mostrarDesarrollador && <th scope="col">Desarrollador</th>}
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
                    {mostrarSeguimiento && <td><FechaDia valor={p.decisiones?.[0]?.fecha_limite} /></td>}
                    {mostrarSeguimiento && <td><SeguimientoAsignacion decision={p.decisiones?.[0]} /></td>}
                    {mostrarDesarrollador && <td className="secundario">{p.usuario}</td>}
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
