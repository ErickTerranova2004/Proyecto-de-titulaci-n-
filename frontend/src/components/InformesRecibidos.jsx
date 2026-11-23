import { useContext, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { columnasInformes } from "../columnasTablas.js";
import { errorRango, FILTROS_INICIALES, hayFiltros } from "../filtrosHistorial.js";
import { consultaInformes, ORDENES_INFORMES } from "../informes.js";
import { escribirEstado, leerFiltros, leerPaginacion } from "../estadoUrl.js";
import { useNavegacion } from "../navegacion.jsx";
import { consultaPaginada } from "../paginacion.js";
import { textoPuntos } from "../planificador.js";
import { AbrirInformeContexto, Alerta, Fecha, NivelRiesgo } from "./comunes.jsx";
import FiltrosHistorial from "./FiltrosHistorial.jsx";
import { TablaPaginada } from "./TablaDesplazable.jsx";

// «Informes recibidos» (líder técnico) e «Informes de cumplimiento»
// (administrador). Fechas, orden y paginación los aplica el backend; por
// defecto, del más reciente al más antiguo, 25 por página.
export default function InformesRecibidos({ titulo = "Informes recibidos", descripcion, mostrarLider = false }) {
  const abrir = useContext(AbrirInformeContexto);
  const { ruta, navegar } = useNavegacion();
  const filtros = leerFiltros(ruta.search, FILTROS_INICIALES);
  const paginacion = leerPaginacion(ruta.search);
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const peticion = useRef(0);
  const columnas = columnasInformes({ mostrarLider });

  function irA(f, p) {
    navegar(ruta.pathname + escribirEstado({ filtros: f, iniciales: FILTROS_INICIALES, paginaciones: [["", p]] }));
  }
  const setFiltros = (nuevos) => irA(nuevos, { ...paginacion, pagina: 1 });
  const setPaginacion = (p) => irA(filtros, p);

  function cargar() {
    if (errorRango(filtros.desde, filtros.hasta)) return;
    const id = ++peticion.current;
    setError("");
    setCargando(true);
    api
      .informes(consultaPaginada(consultaInformes(filtros), paginacion))
      .then((d) => id === peticion.current && setDatos(d))
      .catch((e) => id === peticion.current && setError(e.message))
      .finally(() => id === peticion.current && setCargando(false));
  }
  useEffect(cargar, [filtros.desde, filtros.hasta, filtros.orden, paginacion.pagina, paginacion.porPagina]);

  // El líder ve marcados los que aún no abrió.
  const nuevo = (i) => !i.leido_en && !mostrarLider;
  const celdas = {
    enviado: (i) => <Fecha valor={i.enviado_en} />,
    repositorio: (i) => (
      <>
        <strong className="celda-recortada" title={i.repositorio}>{i.repositorio}</strong>
        <br />
        <span className="secundario celda-recortada" title={i.workflow}>{i.workflow.replace(".github/workflows/", "")}</span>
      </>
    ),
    riesgo: (i) => <><NivelRiesgo nivel={i.nivel_original} /> → <NivelRiesgo nivel={i.nivel_nuevo} /></>,
    diferencia: (i) => textoPuntos(i.diferencia_puntos),
    decision: (i) => (i.decision_final
      ? <span className="celda-recortada celda-recortada--decision" title={i.decision_final.texto}>{i.decision_final.texto}</span>
      : <span className="secundario">Pendiente</span>),
    numero: (i) => (
      <span className="font-mono">{i.numero}{nuevo(i) && <span className="informe-nuevo"> Nuevo</span>}</span>
    ),
    desarrollador: (i) => i.desarrollador,
    lider: (i) => i.lider,
    acciones: (i) => (
      <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => abrir?.(i.id)}>
        Abrir<span className="solo-lector"> el informe {i.numero}</span>
      </button>
    ),
  };

  return (
    <section className="vista" aria-labelledby="titulo-informes">
      <header className="encabezado">
        <h1 id="titulo-informes">{titulo}</h1>
        {descripcion && <p className="secundario">{descripcion}</p>}
      </header>
      <div className="filtros-historial__barra">
        <FiltrosHistorial
          id="informes"
          filtros={filtros}
          alCambiar={setFiltros}
          ordenes={ORDENES_INFORMES}
          conNivel={false}
          conRepositorio={false}
        />
        <div className="panel__acciones">
          {hayFiltros(filtros) && (
            <button className="boton boton--secundario" type="button" onClick={() => setFiltros(FILTROS_INICIALES)}>
              Quitar filtros
            </button>
          )}
          <button className="boton boton--secundario" type="button" onClick={cargar} disabled={cargando}>
            {cargando ? "Actualizando…" : "Actualizar"}
          </button>
        </div>
      </div>
      <Alerta>{error}</Alerta>
      {!datos && !error && <p role="status" className="secundario">Cargando informes…</p>}
      {datos && datos.total === 0 && (
        <p className="secundario">
          {hayFiltros(filtros) ? "No hay informes con los filtros elegidos." : "Aún no hay informes de cumplimiento."}
        </p>
      )}
      {datos && datos.total > 0 && (
        <TablaPaginada
          id="informes"
          titulo={titulo}
          columnas={columnas}
          celdas={celdas}
          datos={datos}
          sustantivo="informes"
          cargando={cargando}
          alCambiarPagina={setPaginacion}
        />
      )}
    </section>
  );
}
