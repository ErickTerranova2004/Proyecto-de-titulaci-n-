import { NIVELES_FILTRO, ORDENES, errorRango } from "../filtrosHistorial.js";

// Barra de filtros de los historiales y de «Pendientes de decisión»: rango de
// fechas, nivel, origen (solo administrador) y orden. El filtrado lo hace el
// backend; `alCambiar` recibe los filtros nuevos.
export default function FiltrosHistorial({ id, filtros, alCambiar, conNivel = false, origenes, ordenes = ORDENES }) {
  const cambiar = (campo) => (e) => alCambiar({ ...filtros, [campo]: e.target.value });
  const error = errorRango(filtros.desde, filtros.hasta);
  return (
    <div className="filtros-historial" role="group" aria-label="Filtros">
      <label className="campo campo--en-linea" htmlFor={`${id}-desde`}>
        <span>Desde</span>
        <input
          id={`${id}-desde`}
          type="date"
          value={filtros.desde}
          max={filtros.hasta || undefined}
          onChange={cambiar("desde")}
          aria-invalid={Boolean(error)}
        />
      </label>
      <label className="campo campo--en-linea" htmlFor={`${id}-hasta`}>
        <span>Hasta</span>
        <input
          id={`${id}-hasta`}
          type="date"
          value={filtros.hasta}
          min={filtros.desde || undefined}
          onChange={cambiar("hasta")}
          aria-invalid={Boolean(error)}
        />
      </label>
      {conNivel && (
        <label className="campo campo--en-linea" htmlFor={`${id}-nivel`}>
          <span>Nivel de riesgo</span>
          <select id={`${id}-nivel`} value={filtros.nivel} onChange={cambiar("nivel")}>
            {NIVELES_FILTRO.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>
      )}
      {origenes && (
        <label className="campo campo--en-linea" htmlFor={`${id}-origen`}>
          <span>Origen</span>
          <select id={`${id}-origen`} value={filtros.origen} onChange={cambiar("origen")}>
            {origenes.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
          </select>
        </label>
      )}
      <label className="campo campo--en-linea" htmlFor={`${id}-orden`}>
        <span>Orden</span>
        <select id={`${id}-orden`} value={filtros.orden} onChange={cambiar("orden")}>
          {ordenes.map(([valor, texto]) => <option key={valor} value={valor}>{texto}</option>)}
        </select>
      </label>
      {error && <p className="alerta filtros-historial__error" role="alert">{error}</p>}
    </div>
  );
}
