import { useContext, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { COLUMNAS_ASIGNACIONES, COLUMNAS_PENDIENTES } from "../columnasTablas.js";
import {
  AbrirInformeContexto, Alerta, DECISIONES, EstadoAsignacion, Fecha, FechaDia, NivelRiesgo, porcentaje, RespuestaDesarrollador, textoPlazo,
} from "./comunes.jsx";
import FiltrosHistorial from "./FiltrosHistorial.jsx";
import Resultado from "./Resultado.jsx";
import { TablaPaginada } from "./TablaDesplazable.jsx";
import { consultaHistorial, errorRango, FILTROS_INICIALES, hayFiltros, ORDENES } from "../filtrosHistorial.js";
import { consultaPaginada, PAGINACION_INICIAL } from "../paginacion.js";

// Aquí todos los análisis están sin decisión: no aplica «con decisión primero».
const ORDENES_PENDIENTES = ORDENES.filter(([id]) => id !== "decision");

// Vista del líder técnico: predicciones de sus repositorios sin decisión y
// asignaciones con fecha límite. La decisión usa el formulario de Resultado.
// Nivel, fechas, orden y paginación los aplica el backend (sin_decision=1);
// por defecto, todos los niveles, del más reciente al más antiguo, 25 por
// página.
export default function Pendientes({ modelos }) {
  const abrirInforme = useContext(AbrirInformeContexto);
  const [sinDecision, setSinDecision] = useState(null);
  const [asignaciones, setAsignaciones] = useState(null);
  const [error, setError] = useState("");
  const [filtros, setFiltrosBase] = useState(FILTROS_INICIALES);
  const [paginaPendientes, setPaginaPendientes] = useState(PAGINACION_INICIAL);
  const [paginaAsignaciones, setPaginaAsignaciones] = useState(PAGINACION_INICIAL);
  const [cargando, setCargando] = useState(false);
  const [seleccion, setSeleccion] = useState(null);
  const [abriendo, setAbriendo] = useState(false);
  const peticion = useRef(0);

  function setFiltros(nuevos) {
    setFiltrosBase(nuevos);
    setPaginaPendientes((p) => ({ ...p, pagina: 1 }));
  }

  function cargarPendientes() {
    if (errorRango(filtros.desde, filtros.hasta)) return;
    const id = ++peticion.current;
    setError("");
    setCargando(true);
    api
      .historial(consultaPaginada(consultaHistorial({ ...filtros, sinDecision: true }), paginaPendientes))
      .then((h) => id === peticion.current && setSinDecision(h))
      .catch((e) => id === peticion.current && setError(e.message))
      .finally(() => id === peticion.current && setCargando(false));
  }
  // Con llaves: useEffect no debe recibir la promesa como función de limpieza.
  function cargarAsignaciones() {
    api.asignaciones(consultaPaginada("", paginaAsignaciones)).then(setAsignaciones).catch((e) => setError(e.message));
  }
  function cargar() {
    cargarPendientes();
    cargarAsignaciones();
  }
  useEffect(cargarAsignaciones, [paginaAsignaciones.pagina, paginaAsignaciones.porPagina]);
  useEffect(cargarPendientes, [filtros.desde, filtros.hasta, filtros.nivel, filtros.orden,
    paginaPendientes.pagina, paginaPendientes.porPagina]);
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

  const celdasPendientes = {
    fecha: (p) => <Fecha valor={p.creada_en} />,
    repositorio: (p) => <strong className="celda-recortada" title={p.repositorio}>{p.repositorio}</strong>,
    riesgo: (p) => <NivelRiesgo nivel={p.nivel} />,
    probabilidad: (p) => <span className="destacado">{porcentaje(p.probabilidad)}</span>,
    desarrollador: (p) => p.usuario,
    workflow: (p) => <span className="secundario" title={p.workflow_path}>{p.workflow_path.replace(".github/workflows/", "")}</span>,
    acciones: (p) => (
      <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => setSeleccion(p)}>
        Decidir<span className="solo-lector"> sobre el análisis {p.id} de {p.repositorio}</span>
      </button>
    ),
  };

  const celdasAsignaciones = {
    limite: (a) => (
      <>
        {a.fecha_limite ? <FechaDia valor={a.fecha_limite} /> : "—"} <span className="secundario">{textoPlazo(a)}</span>
      </>
    ),
    repositorio: (a) => <strong className="celda-recortada" title={a.repositorio}>{a.repositorio}</strong>,
    decision: (a) => (
      <span className="celda-recortada celda-recortada--decision" title={DECISIONES[a.decision]}>{DECISIONES[a.decision]}</span>
    ),
    estado: (a) => <EstadoAsignacion estado={a.estado} />,
    desarrollador: (a) => a.desarrollador,
    respuesta: (a) => (
      <>
        {a.prediccion_respuesta
          ? <RespuestaDesarrollador nivelOriginal={a.nivel_original} respuesta={a.prediccion_respuesta} comentario={a.respuesta_desarrollador} />
          : <span className="secundario">{a.cumplida_en ? "Marcada sin nuevo análisis" : "—"}</span>}
        {a.informe && abrirInforme && (
          <button className="boton boton--pequeno informe-enlace" type="button" onClick={() => abrirInforme(a.informe.id)}>
            Informe {a.informe.numero}{!a.informe.decision_final && " · decidir"}
          </button>
        )}
      </>
    ),
    mensaje: (a) => <span className="secundario celda-recortada" title={a.mensaje || ""}>{a.mensaje || "—"}</span>,
    vista: (a) => (a.vista_por_desarrollador_en ? <Fecha valor={a.vista_por_desarrollador_en} /> : "No"),
    cumplida: (a) => (a.cumplida_en ? <Fecha valor={a.cumplida_en} /> : "No"),
    acciones: (a) => (
      <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => abrir(a.prediccion)} disabled={abriendo}>
        Ver<span className="solo-lector"> el análisis de {a.repositorio}</span>
      </button>
    ),
  };

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
            Predicciones sin decisión <span className="secundario">({sinDecision.total})</span>
          </h2>
          {!sinDecision.total ? (
            <div className="tarjeta vacio">
              <p className="secundario">No hay análisis pendientes de decisión con este filtro.</p>
            </div>
          ) : (
            <TablaPaginada
              id="pendientes"
              titulo={`${sinDecision.total} análisis sin decisión`}
              columnas={COLUMNAS_PENDIENTES}
              celdas={celdasPendientes}
              datos={sinDecision}
              sustantivo="análisis sin decisión"
              cargando={cargando}
              alCambiarPagina={setPaginaPendientes}
            />
          )}
        </section>
      )}

      {asignaciones && (
        <section aria-labelledby="titulo-asignaciones-equipo">
          <h2 id="titulo-asignaciones-equipo">Asignaciones y respuestas del equipo</h2>
          {!asignaciones.total ? (
            <div className="tarjeta vacio">
              <p className="secundario">Todavía no hay asignaciones para su equipo.</p>
            </div>
          ) : (
            <TablaPaginada
              id="asignaciones"
              titulo="Asignaciones del equipo con fecha límite y su seguimiento"
              columnas={COLUMNAS_ASIGNACIONES}
              celdas={celdasAsignaciones}
              datos={asignaciones}
              sustantivo="asignaciones"
              alCambiarPagina={setPaginaAsignaciones}
            />
          )}
        </section>
      )}
    </section>
  );
}
