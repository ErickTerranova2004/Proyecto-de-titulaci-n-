import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import {
  Alerta, DECISIONES, EstadoAsignacion, Fecha, FechaDia, NivelRiesgo, porcentaje, RespuestaDesarrollador,
} from "./comunes.jsx";
import FiltrosHistorial from "./FiltrosHistorial.jsx";
import Resultado from "./Resultado.jsx";
import { consultaHistorial, errorRango, FILTROS_INICIALES, hayFiltros } from "../filtrosHistorial.js";
import { ordenarPorActividad } from "../ordenHistorial.js";

// Seguimiento de la fecha límite de la última decisión (vista / cumplida).
export function SeguimientoAsignacion({ decision, nivelOriginal }) {
  if (!decision?.estado) return <span className="secundario">—</span>;
  return (
    <>
      <EstadoAsignacion estado={decision.estado} />{" "}
      <span className="secundario">
        {decision.cumplida_en ? "Cumplida" : decision.vista_por_desarrollador_en ? "Vista" : "No vista"}
      </span>{" "}
      <RespuestaDesarrollador
        nivelOriginal={nivelOriginal}
        respuesta={decision.prediccion_respuesta}
        comentario={decision.respuesta_desarrollador}
      />
    </>
  );
}

// Origen de los análisis (solo el administrador ve los del lote).
const ORIGENES = [
  ["interactivo", "Análisis en la plataforma"],
  ["lote", "Análisis en lote"],
  ["todos", "Todos"],
];

// El backend ya filtra por rol: el desarrollador recibe sus análisis y el
// líder los de todos los desarrolladores de sus repositorios asignados.
// Fechas, origen y orden también se aplican en el backend; por defecto, del
// más reciente al más antiguo.
export default function Historial({
  modelos, titulo = "Historial de análisis", descripcion, mostrarDesarrollador = true, mostrarSeguimiento = false,
  conOrigen = false,
  // Desplegable de nivel de riesgo (Todos, Bajo, Medio, Alto); lo filtra el backend.
  conNivel = false,
}) {
  const inicial = conOrigen ? { ...FILTROS_INICIALES, origen: "interactivo" } : FILTROS_INICIALES;
  const [filtros, setFiltros] = useState(inicial);
  const [filas, setFilas] = useState(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [seleccion, setSeleccion] = useState(null);
  const peticion = useRef(0);

  function cargar() {
    if (errorRango(filtros.desde, filtros.hasta)) return;
    // Solo cuenta la respuesta de la última petición (filtros cambiados rápido).
    const id = ++peticion.current;
    setCargando(true);
    setError("");
    api
      .historial(consultaHistorial(filtros))
      .then((h) => {
        if (id !== peticion.current) return;
        setFilas(filtros.orden === "decision" ? ordenarPorActividad(h) : h);
      })
      .catch((e) => id === peticion.current && setError(e.message))
      .finally(() => id === peticion.current && setCargando(false));
  }
  useEffect(cargar, [filtros.desde, filtros.hasta, filtros.orden, filtros.origen, filtros.nivel]);
  const filtrado = hayFiltros(filtros, inicial.origen);

  if (seleccion) {
    return (
      <section className="vista" aria-labelledby="titulo-historial">
        <h1 id="titulo-historial">{titulo}</h1>
        <div>
          <button className="boton boton--secundario" type="button" onClick={() => { setSeleccion(null); cargar(); }}>
            ← Volver al historial
          </button>
        </div>
        <Resultado prediccion={seleccion} modelos={modelos} mostrarResultadoReal={false} />
      </section>
    );
  }

  return (
    <section className="vista" aria-labelledby="titulo-historial">
      <header className="encabezado">
        <h1 id="titulo-historial">{titulo}</h1>
        <p className="secundario">
          {descripcion ?? "Análisis visibles según su rol y sus repositorios asignados"}.
        </p>
      </header>
      <div className="filtros-historial__barra">
        <FiltrosHistorial
          id="historial"
          filtros={filtros}
          alCambiar={setFiltros}
          conNivel={conNivel}
          origenes={conOrigen ? ORIGENES : undefined}
        />
        <div className="panel__acciones">
          {filtrado && (
            <button className="boton boton--secundario" type="button" onClick={() => setFiltros(inicial)}>
              Quitar filtros
            </button>
          )}
          <button className="boton boton--secundario" type="button" onClick={cargar} disabled={cargando}>
            {cargando ? "Actualizando…" : "Actualizar"}
          </button>
        </div>
      </div>
      <Alerta>{error}</Alerta>
      {!filas && !error && <p role="status" className="secundario">Cargando historial…</p>}
      {filas && (
        <p className="secundario" role="status">
          {filas.length === 1 ? "1 análisis" : `${filas.length} análisis`}
          {filtrado ? " con los filtros elegidos" : ""}.
        </p>
      )}
      {filas && !filas.length && (
        <div className="tarjeta vacio">
          <p className="secundario">
            {filtrado ? "No hay análisis con estos filtros." : "Todavía no hay análisis visibles para su usuario."}
          </p>
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
                    <td>{p.decisiones?.length ? DECISIONES[p.decisiones[0].decision] : "Sin decisión"}</td>
                    {mostrarSeguimiento && <td><FechaDia valor={p.decisiones?.[0]?.fecha_limite} /></td>}
                    {mostrarSeguimiento && <td><SeguimientoAsignacion decision={p.decisiones?.[0]} nivelOriginal={p.nivel} /></td>}
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
