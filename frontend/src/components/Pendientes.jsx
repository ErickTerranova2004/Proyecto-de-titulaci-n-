import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { Alerta, DECISIONES, EstadoAsignacion, Fecha, FechaDia, NivelRiesgo, porcentaje, textoPlazo } from "./comunes.jsx";
import Resultado from "./Resultado.jsx";

const FILTROS = [
  ["medio-alto", "Nivel medio y alto"],
  ["todos", "Todos los niveles"],
];

// Vista del líder técnico: predicciones de sus repositorios sin decisión y
// asignaciones con fecha límite. La decisión usa el formulario de Resultado.
export default function Pendientes({ modelos }) {
  const [historial, setHistorial] = useState(null);
  const [asignaciones, setAsignaciones] = useState(null);
  const [error, setError] = useState("");
  const [filtro, setFiltro] = useState("medio-alto");
  const [seleccion, setSeleccion] = useState(null);

  const cargar = () =>
    Promise.all([api.historial(), api.asignaciones()])
      .then(([h, a]) => {
        setHistorial(h);
        setAsignaciones(a);
      })
      .catch((e) => setError(e.message));
  useEffect(() => {
    cargar();
  }, []);

  const sinDecision = useMemo(
    () =>
      historial
        ?.filter((p) => !p.decisiones?.length && (filtro === "todos" || p.nivel !== "bajo"))
        .sort((a, b) => b.probabilidad - a.probabilidad),
    [historial, filtro],
  );

  if (seleccion) {
    return (
      <section className="vista" aria-labelledby="titulo-pendientes">
        <h1 id="titulo-pendientes">Pendientes de decisión</h1>
        <div>
          <button className="boton boton--secundario" type="button" onClick={() => { setSeleccion(null); cargar(); }}>
            ← Volver a pendientes
          </button>
        </div>
        <Resultado prediccion={seleccion} modelos={modelos} />
      </section>
    );
  }

  const abrir = (id) => setSeleccion(historial.find((p) => p.id === id));

  return (
    <section className="vista" aria-labelledby="titulo-pendientes">
      <div className="panel__cabecera">
        <header className="encabezado">
          <h1 id="titulo-pendientes">Pendientes de decisión</h1>
          <p className="secundario">
            Líder técnico · análisis de sus repositorios asignados que esperan una decisión y asignaciones en curso.
          </p>
        </header>
        <div className="panel__acciones">
          <label className="campo campo--en-linea" htmlFor="filtro-pendientes">
            <span>Mostrar</span>
            <select id="filtro-pendientes" value={filtro} onChange={(e) => setFiltro(e.target.value)}>
              {FILTROS.map(([id, texto]) => <option key={id} value={id}>{texto}</option>)}
            </select>
          </label>
          <button className="boton boton--secundario" type="button" onClick={cargar}>Actualizar</button>
        </div>
      </div>
      <Alerta>{error}</Alerta>
      {!historial && !error && <p role="status" className="secundario">Cargando pendientes…</p>}

      {sinDecision && (
        <section aria-labelledby="titulo-sin-decision">
          <h2 id="titulo-sin-decision">Predicciones sin decisión</h2>
          {!sinDecision.length ? (
            <div className="tarjeta vacio">
              <p className="secundario">No hay análisis pendientes de decisión con este filtro.</p>
            </div>
          ) : (
            <div className="tarjeta tarjeta--tabla">
              <div className="tabla-contenedor">
                <table>
                  <caption className="solo-lector">{sinDecision.length} análisis sin decisión</caption>
                  <thead>
                    <tr>
                      <th scope="col">Fecha</th>
                      <th scope="col">Repositorio</th>
                      <th scope="col">Workflow</th>
                      <th scope="col">Desarrollador</th>
                      <th scope="col">Riesgo</th>
                      <th scope="col" className="numero">Probabilidad</th>
                      <th scope="col"><span className="solo-lector">Acciones</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {sinDecision.map((p) => (
                      <tr key={p.id}>
                        <td><Fecha valor={p.creada_en} /></td>
                        <td><strong>{p.repositorio}</strong></td>
                        <td className="secundario" title={p.workflow_path}>{p.workflow_path.replace(".github/workflows/", "")}</td>
                        <td>{p.usuario}</td>
                        <td><NivelRiesgo nivel={p.nivel} /></td>
                        <td className="numero destacado">{porcentaje(p.probabilidad)}</td>
                        <td>
                          <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => setSeleccion(p)}>
                            Decidir<span className="solo-lector"> sobre el análisis {p.id} de {p.repositorio}</span>
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
      )}

      {asignaciones && (
        <section aria-labelledby="titulo-asignaciones-equipo">
          <h2 id="titulo-asignaciones-equipo">Asignaciones con fecha límite</h2>
          {!asignaciones.length ? (
            <div className="tarjeta vacio">
              <p className="secundario">Todavía no ha fijado fechas límite a su equipo.</p>
            </div>
          ) : (
            <div className="tarjeta tarjeta--tabla">
              <div className="tabla-contenedor">
                <table>
                  <caption className="solo-lector">Asignaciones del equipo con fecha límite y su seguimiento</caption>
                  <thead>
                    <tr>
                      <th scope="col">Fecha límite</th>
                      <th scope="col">Repositorio</th>
                      <th scope="col">Desarrollador</th>
                      <th scope="col">Decisión</th>
                      <th scope="col">Mensaje</th>
                      <th scope="col">Estado</th>
                      <th scope="col">Vista</th>
                      <th scope="col">Cumplida</th>
                      <th scope="col"><span className="solo-lector">Acciones</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {asignaciones.map((a) => (
                      <tr key={a.id}>
                        <td><FechaDia valor={a.fecha_limite} /> <span className="secundario">{textoPlazo(a)}</span></td>
                        <td><strong>{a.repositorio}</strong></td>
                        <td>{a.desarrollador}</td>
                        <td>{DECISIONES[a.decision]}</td>
                        <td className="secundario">{a.mensaje || "—"}</td>
                        <td><EstadoAsignacion estado={a.estado} /></td>
                        <td>{a.vista_por_desarrollador_en ? <Fecha valor={a.vista_por_desarrollador_en} /> : "No"}</td>
                        <td>{a.cumplida_en ? <Fecha valor={a.cumplida_en} /> : "No"}</td>
                        <td>
                          <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => abrir(a.prediccion)}>
                            Ver<span className="solo-lector"> el análisis de {a.repositorio}</span>
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
      )}
    </section>
  );
}
