import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import {
  Alerta, DECISIONES, EstadoAsignacion, Fecha, FechaDia, NivelRiesgo, porcentaje, RespuestaDesarrollador,
} from "./comunes.jsx";
import FiltrosHistorial from "./FiltrosHistorial.jsx";
import { TablaPaginada } from "./TablaDesplazable.jsx";
import { columnasHistorial } from "../columnasTablas.js";
import { escribirEstado, leerFiltros, leerPaginacion } from "../estadoUrl.js";
import { consultaHistorial, DECISIONES_FILTRO, errorRango, FILTROS_INICIALES, hayFiltros } from "../filtrosHistorial.js";
import { Enlace, useNavegacion } from "../navegacion.jsx";
import { consultaPaginada } from "../paginacion.js";

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
// Fechas, origen, orden y paginación también se aplican en el backend; por
// defecto, del más reciente al más antiguo y 25 por página. Filtros y página
// van en la dirección (F5 y atrás/adelante los conservan).
export default function Historial({
  titulo = "Historial de análisis", descripcion, mostrarDesarrollador = true, mostrarSeguimiento = false,
  conOrigen = false,
}) {
  const { ruta, navegar } = useNavegacion();
  const inicial = conOrigen ? { ...FILTROS_INICIALES, origen: "interactivo" } : FILTROS_INICIALES;
  const filtros = leerFiltros(ruta.search, inicial);
  const paginacion = leerPaginacion(ruta.search);
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const peticion = useRef(0);
  const columnas = columnasHistorial({ mostrarSeguimiento, mostrarDesarrollador });

  function irA(nuevosFiltros, nuevaPaginacion, opciones) {
    navegar(ruta.pathname + escribirEstado({
      filtros: nuevosFiltros, iniciales: inicial, paginaciones: [["", nuevaPaginacion]],
    }), opciones);
  }
  // Cambiar un filtro vuelve a la primera página.
  const setFiltros = (nuevos, opciones) => irA(nuevos, { ...paginacion, pagina: 1 }, opciones);
  const setPaginacion = (nueva) => irA(filtros, nueva);

  function cargar() {
    if (errorRango(filtros.desde, filtros.hasta)) return;
    // Solo cuenta la respuesta de la última petición (filtros cambiados rápido).
    const id = ++peticion.current;
    setCargando(true);
    setError("");
    api
      .historial(consultaPaginada(consultaHistorial(filtros), paginacion))
      .then((d) => id === peticion.current && setDatos(d))
      .catch((e) => id === peticion.current && setError(e.message))
      .finally(() => id === peticion.current && setCargando(false));
  }
  useEffect(cargar, [filtros.desde, filtros.hasta, filtros.orden, filtros.origen, filtros.nivel,
    filtros.decision, filtros.repo, paginacion.pagina, paginacion.porPagina]);
  const filtrado = hayFiltros(filtros, inicial.origen);
  const filas = datos ? datos.resultados : null;

  const celdas = {
    fecha: (p) => <Fecha valor={p.creada_en} />,
    repositorio: (p) => <strong className="celda-recortada" title={p.repositorio}>{p.repositorio}</strong>,
    riesgo: (p) => <NivelRiesgo nivel={p.nivel} />,
    probabilidad: (p) => <span className="destacado">{porcentaje(p.probabilidad)}</span>,
    decision: (p) => {
      const texto = p.decisiones?.length ? DECISIONES[p.decisiones[0].decision] : "Sin decisión";
      return <span className="celda-recortada celda-recortada--decision" title={texto}>{texto}</span>;
    },
    limite: (p) => <FechaDia valor={p.decisiones?.[0]?.fecha_limite} />,
    seguimiento: (p) => <SeguimientoAsignacion decision={p.decisiones?.[0]} nivelOriginal={p.nivel} />,
    desarrollador: (p) => <span className="secundario">{p.usuario}</span>,
    workflow: (p) => <span className="secundario" title={p.workflow_path}>{p.workflow_path.replace(".github/workflows/", "")}</span>,
    commit: (p) => <code>{p.head_sha.slice(0, 7)}</code>,
    acciones: (p) => (
      <Enlace className="boton boton--secundario boton--pequeno" href={`/analisis/${p.id}?desde=historial`}>
        Ver detalle<span className="solo-lector"> del análisis {p.id}</span>
      </Enlace>
    ),
  };

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
          decisiones={DECISIONES_FILTRO}
          origenes={conOrigen ? ORIGENES : undefined}
          alQuitar={() => setFiltros(inicial)}
          puedeQuitar={filtrado}
        />
        <div className="panel__acciones">
          <button className="boton boton--secundario" type="button" onClick={cargar} disabled={cargando}>
            {cargando ? "Actualizando…" : "Actualizar"}
          </button>
        </div>
      </div>
      <Alerta>{error}</Alerta>
      {!datos && !error && <p role="status" className="secundario">Cargando historial…</p>}
      {filas && !filas.length && (
        <div className="tarjeta vacio">
          <p className="secundario">
            {filtrado ? "No hay análisis con estos filtros." : "Todavía no hay análisis visibles para su usuario."}
          </p>
        </div>
      )}
      {filas && filas.length > 0 && (
        <TablaPaginada
          id="historial"
          titulo={titulo}
          columnas={columnas}
          celdas={celdas}
          datos={datos}
          sustantivo={filtrado ? "análisis con los filtros elegidos" : "análisis"}
          cargando={cargando}
          alCambiarPagina={setPaginacion}
        />
      )}
    </section>
  );
}
