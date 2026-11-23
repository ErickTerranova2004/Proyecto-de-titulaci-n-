import { useEffect, useRef, useState } from "react";
import { NIVELES_FILTRO, ORDENES, errorRango, escribirFecha, fechaDesdeTexto, textoFecha } from "../filtrosHistorial.js";

// Campo de fecha que siempre se escribe dd/mm/aaaa (el input type="date" del
// navegador usa el formato de su idioma, p. ej. mm/dd/yyyy en inglés). `valor`
// y `alCambiar` usan AAAA-MM-DD; solo se avisa cuando la fecha está completa y
// es válida, o cuando se vacía. El botón abre el calendario del navegador.
function CampoFecha({ id, valor, min, max, alCambiar, invalido }) {
  const [texto, setTexto] = useState(textoFecha(valor));
  const nativo = useRef(null);

  // Cambios desde fuera («Quitar filtros», calendario).
  useEffect(() => {
    if (fechaDesdeTexto(texto) !== valor) setTexto(textoFecha(valor));
  }, [valor]);

  function escribir(e) {
    const nuevo = escribirFecha(e.target.value);
    setTexto(nuevo);
    const iso = fechaDesdeTexto(nuevo);
    if (iso !== null && iso !== valor) alCambiar(iso);
  }

  function abrirCalendario() {
    const campo = nativo.current;
    if (!campo) return;
    try {
      campo.showPicker();
    } catch {
      campo.focus();
      campo.click();
    }
  }

  const incompleto = texto !== "" && fechaDesdeTexto(texto) === null;
  return (
    <span className="campo-fecha">
      <input
        id={id}
        type="text"
        inputMode="numeric"
        placeholder="dd/mm/aaaa"
        autoComplete="off"
        maxLength={10}
        value={texto}
        onChange={escribir}
        aria-invalid={invalido || incompleto}
        title={incompleto ? "Complete la fecha con el formato dd/mm/aaaa" : undefined}
      />
      <button type="button" className="campo-fecha__calendario" onClick={abrirCalendario} aria-label="Abrir calendario">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <rect x="3" y="5" width="18" height="16" rx="2" />
          <path d="M16 3v4M8 3v4M3 10h18" />
        </svg>
      </button>
      <input
        ref={nativo}
        type="date"
        className="campo-fecha__nativo"
        tabIndex={-1}
        aria-hidden="true"
        value={valor}
        min={min || undefined}
        max={max || undefined}
        onChange={(e) => alCambiar(e.target.value)}
      />
    </span>
  );
}

// Búsqueda por repositorio: se aplica 400 ms después de dejar de escribir y
// reemplaza la entrada del historial (no una por letra).
function CampoBuscar({ id, valor, alCambiar }) {
  const [texto, setTexto] = useState(valor || "");
  const ultimo = useRef(valor || "");
  useEffect(() => {
    // Cambio desde fuera (Quitar filtros, atrás/adelante).
    if ((valor || "") !== ultimo.current) {
      ultimo.current = valor || "";
      setTexto(valor || "");
    }
  }, [valor]);
  useEffect(() => {
    const espera = setTimeout(() => {
      if (texto.trim() !== (ultimo.current || "").trim()) {
        ultimo.current = texto.trim();
        alCambiar(texto.trim());
      }
    }, 400);
    return () => clearTimeout(espera);
  }, [texto]);
  return (
    <input
      id={id}
      type="search"
      className="filtros-historial__buscar"
      placeholder="Nombre del repositorio"
      value={texto}
      onChange={(e) => setTexto(e.target.value)}
      autoComplete="off"
    />
  );
}

// Barra de filtros común de los historiales, de «Pendientes de decisión» y de
// los informes, siempre en el mismo orden: desde, hasta, nivel, [resultado],
// [decisión], repositorio, orden, [origen] y «Quitar filtros». El filtrado lo
// hace el backend; `alCambiar(filtros, opciones)` recibe los filtros nuevos
// (con { reemplazar: true } al escribir en el buscador).
export default function FiltrosHistorial({
  id, filtros, alCambiar, conNivel = true, etiquetaNivel = "Nivel de riesgo", resultados, decisiones,
  etiquetaDecision = "Decisión", conRepositorio = true, origenes, ordenes = ORDENES, alQuitar, puedeQuitar = false,
}) {
  const cambiar = (campo) => (e) => alCambiar({ ...filtros, [campo]: e.target.value });
  const fijar = (campo) => (valor) => alCambiar({ ...filtros, [campo]: valor });
  const error = errorRango(filtros.desde, filtros.hasta);
  return (
    <div className="filtros-historial" role="group" aria-label="Filtros">
      <label className="campo campo--en-linea" htmlFor={`${id}-desde`}>
        <span>Desde</span>
        <CampoFecha
          id={`${id}-desde`}
          valor={filtros.desde}
          max={filtros.hasta}
          alCambiar={fijar("desde")}
          invalido={Boolean(error)}
        />
      </label>
      <label className="campo campo--en-linea" htmlFor={`${id}-hasta`}>
        <span>Hasta</span>
        <CampoFecha
          id={`${id}-hasta`}
          valor={filtros.hasta}
          min={filtros.desde}
          alCambiar={fijar("hasta")}
          invalido={Boolean(error)}
        />
      </label>
      {conNivel && (
        <label className="campo campo--en-linea" htmlFor={`${id}-nivel`}>
          <span>{etiquetaNivel}</span>
          <select id={`${id}-nivel`} value={filtros.nivel} onChange={cambiar("nivel")}>
            {NIVELES_FILTRO.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>
      )}
      {resultados && (
        <label className="campo campo--en-linea" htmlFor={`${id}-resultado`}>
          <span>Resultado del cambio</span>
          <select id={`${id}-resultado`} value={filtros.resultado} onChange={cambiar("resultado")}>
            {resultados.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>
      )}
      {decisiones && (
        <label className="campo campo--en-linea" htmlFor={`${id}-decision`}>
          <span>{etiquetaDecision}</span>
          <select id={`${id}-decision`} value={filtros.decision} onChange={cambiar("decision")}>
            {decisiones.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>
      )}
      {conRepositorio && (
        <label className="campo campo--en-linea" htmlFor={`${id}-repo`}>
          <span>Repositorio</span>
          <CampoBuscar
            id={`${id}-repo`}
            valor={filtros.repo}
            alCambiar={(repo) => alCambiar({ ...filtros, repo }, { reemplazar: true })}
          />
        </label>
      )}
      <label className="campo campo--en-linea" htmlFor={`${id}-orden`}>
        <span>Orden</span>
        <select id={`${id}-orden`} value={filtros.orden} onChange={cambiar("orden")}>
          {ordenes.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
        </select>
      </label>
      {origenes && (
        <label className="campo campo--en-linea" htmlFor={`${id}-origen`}>
          <span>Origen</span>
          <select id={`${id}-origen`} value={filtros.origen} onChange={cambiar("origen")}>
            {origenes.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>
      )}
      {alQuitar && (
        <button className="boton boton--secundario filtros-historial__quitar" type="button" onClick={alQuitar} disabled={!puedeQuitar}>
          Quitar filtros
        </button>
      )}
      {error && <p className="alerta filtros-historial__error" role="alert">{error}</p>}
    </div>
  );
}
