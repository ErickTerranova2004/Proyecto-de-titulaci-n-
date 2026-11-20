import { useContext, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import {
  AbrirInformeContexto, Alerta, DECISIONES, EstadoAsignacion, Fecha, FechaDia, NivelRiesgo, porcentaje, RespuestaDesarrollador, textoPlazo,
} from "./comunes.jsx";
import FiltrosHistorial from "./FiltrosHistorial.jsx";
import Resultado from "./Resultado.jsx";
import { consultaHistorial, errorRango, FILTROS_INICIALES, hayFiltros, ORDENES } from "../filtrosHistorial.js";

// Aquí todos los análisis están sin decisión: no aplica «con decisión primero».
const ORDENES_PENDIENTES = ORDENES.filter(([id]) => id !== "decision");

// Vista del líder técnico: predicciones de sus repositorios sin decisión y
// asignaciones con fecha límite. La decisión usa el formulario de Resultado.
// Nivel, fechas y orden los aplica el backend (sin_decision=1); por defecto,
// todos los niveles, del más reciente al más antiguo.
export default function Pendientes({ modelos }) {
  const abrirInforme = useContext(AbrirInformeContexto);
  const [sinDecision, setSinDecision] = useState(null);
  const [asignaciones, setAsignaciones] = useState(null);
  const [error, setError] = useState("");
  const [filtros, setFiltros] = useState(FILTROS_INICIALES);
  const [seleccion, setSeleccion] = useState(null);
  const [abriendo, setAbriendo] = useState(false);
  const peticion = useRef(0);

  function cargarPendientes() {
    if (errorRango(filtros.desde, filtros.hasta)) return;
    const id = ++peticion.current;
    setError("");
    api
      .historial(consultaHistorial({ ...filtros, sinDecision: true }))
      .then((h) => id === peticion.current && setSinDecision(h))
      .catch((e) => id === peticion.current && setError(e.message));
  }
  // Con llaves: useEffect no debe recibir la promesa como función de limpieza.
  function cargarAsignaciones() {
    api.asignaciones().then(setAsignaciones).catch((e) => setError(e.message));
  }
  function cargar() {
    cargarPendientes();
    cargarAsignaciones();
  }
  useEffect(cargarAsignaciones, []);
  useEffect(cargarPendientes, [filtros.desde, filtros.hasta, filtros.nivel, filtros.orden]);
  const filtrado = hayFiltros(filtros);

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

  // El análisis de una asignación ya tiene decisión: no está en la lista de
  // pendientes, se pide al backend.
  function abrir(id) {
    setAbriendo(true);
    api
      .prediccion(id)
      .then(setSeleccion)
      .catch((e) => setError(e.message))
      .finally(() => setAbriendo(false));
  }

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
          <button className="boton boton--secundario" type="button" onClick={cargar}>Actualizar</button>
        </div>
      </div>
      <div className="filtros-historial__barra">
        <FiltrosHistorial
          id="pendientes"
          filtros={filtros}
          alCambiar={setFiltros}
          conNivel
          ordenes={ORDENES_PENDIENTES}
        />
        {filtrado && (
          <div className="panel__acciones">
            <button className="boton boton--secundario" type="button" onClick={() => setFiltros(FILTROS_INICIALES)}>
              Quitar filtros
            </button>
          </div>
        )}
      </div>
      <Alerta>{error}</Alerta>
      {!sinDecision && !error && <p role="status" className="secundario">Cargando pendientes…</p>}

      {sinDecision && (
        <section aria-labelledby="titulo-sin-decision">
          <h2 id="titulo-sin-decision">
            Predicciones sin decisión <span className="secundario">({sinDecision.length})</span>
          </h2>
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
          <h2 id="titulo-asignaciones-equipo">Asignaciones y respuestas del equipo</h2>
          {!asignaciones.length ? (
            <div className="tarjeta vacio">
              <p className="secundario">Todavía no hay asignaciones para su equipo.</p>
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
                      <th scope="col">Respuesta del desarrollador</th>
                      <th scope="col"><span className="solo-lector">Acciones</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {asignaciones.map((a) => (
                      <tr key={a.id}>
                        <td>
                          {a.fecha_limite ? <FechaDia valor={a.fecha_limite} /> : "—"}{" "}
                          <span className="secundario">{textoPlazo(a)}</span>
                        </td>
                        <td><strong>{a.repositorio}</strong></td>
                        <td>{a.desarrollador}</td>
                        <td>{DECISIONES[a.decision]}</td>
                        <td className="secundario">{a.mensaje || "—"}</td>
                        <td><EstadoAsignacion estado={a.estado} /></td>
                        <td>{a.vista_por_desarrollador_en ? <Fecha valor={a.vista_por_desarrollador_en} /> : "No"}</td>
                        <td>{a.cumplida_en ? <Fecha valor={a.cumplida_en} /> : "No"}</td>
                        <td>
                          {a.prediccion_respuesta
                            ? <RespuestaDesarrollador nivelOriginal={a.nivel_original} respuesta={a.prediccion_respuesta} comentario={a.respuesta_desarrollador} />
                            : <span className="secundario">{a.cumplida_en ? "Marcada sin nuevo análisis" : "—"}</span>}
                          {a.informe && abrirInforme && (
                            <button className="boton boton--pequeno informe-enlace" type="button" onClick={() => abrirInforme(a.informe.id)}>
                              Informe {a.informe.numero}{!a.informe.decision_final && " · decidir"}
                            </button>
                          )}
                        </td>
                        <td>
                          <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => abrir(a.prediccion)} disabled={abriendo}>
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
