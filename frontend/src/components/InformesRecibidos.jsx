import { useContext, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { errorRango, FILTROS_INICIALES, hayFiltros } from "../filtrosHistorial.js";
import { consultaInformes, ORDENES_INFORMES } from "../informes.js";
import { textoPuntos } from "../planificador.js";
import { AbrirInformeContexto, Alerta, Fecha, NivelRiesgo } from "./comunes.jsx";
import FiltrosHistorial from "./FiltrosHistorial.jsx";

// «Informes recibidos» (líder técnico) e «Informes de cumplimiento»
// (administrador). Fechas y orden los aplica el backend; por defecto, del más
// reciente al más antiguo.
export default function InformesRecibidos({ titulo = "Informes recibidos", descripcion, mostrarLider = false }) {
  const abrir = useContext(AbrirInformeContexto);
  const [filtros, setFiltros] = useState(FILTROS_INICIALES);
  const [lista, setLista] = useState(null);
  const [error, setError] = useState("");
  const peticion = useRef(0);

  function cargar() {
    if (errorRango(filtros.desde, filtros.hasta)) return;
    const id = ++peticion.current;
    setError("");
    api
      .informes(consultaInformes(filtros))
      .then((datos) => id === peticion.current && setLista(datos))
      .catch((e) => id === peticion.current && setError(e.message));
  }
  useEffect(cargar, [filtros.desde, filtros.hasta, filtros.orden]);

  return (
    <section className="vista" aria-labelledby="titulo-informes">
      <header className="encabezado">
        <h1 id="titulo-informes">{titulo}</h1>
        {descripcion && <p className="secundario">{descripcion}</p>}
      </header>
      <div className="filtros-historial__barra">
        <FiltrosHistorial id="informes" filtros={filtros} alCambiar={setFiltros} ordenes={ORDENES_INFORMES} />
        <div className="panel__acciones">
          {hayFiltros(filtros) && (
            <button className="boton boton--secundario" type="button" onClick={() => setFiltros(FILTROS_INICIALES)}>
              Quitar filtros
            </button>
          )}
          <button className="boton boton--secundario" type="button" onClick={cargar}>Actualizar</button>
        </div>
      </div>
      <Alerta>{error}</Alerta>
      {!lista && !error && <p role="status" className="secundario">Cargando informes…</p>}
      {lista && lista.length === 0 && (
        <p className="secundario">
          {hayFiltros(filtros) ? "No hay informes con los filtros elegidos." : "Aún no hay informes de cumplimiento."}
        </p>
      )}
      {lista && lista.length > 0 && (
        <div className="tabla-contenedor">
          <table>
            <thead>
              <tr>
                <th scope="col">N.º</th>
                <th scope="col">Enviado</th>
                <th scope="col">Repositorio</th>
                <th scope="col">Desarrollador</th>
                {mostrarLider && <th scope="col">Líder</th>}
                <th scope="col">Riesgo</th>
                <th scope="col">Diferencia</th>
                <th scope="col">Decisión final</th>
                <th scope="col"><span className="solo-lector">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {lista.map((i) => (
                <tr key={i.id} className={!i.leido_en && !mostrarLider ? "informe-fila--nuevo" : undefined}>
                  <td className="font-mono">{i.numero}{!i.leido_en && !mostrarLider && <span className="informe-nuevo"> Nuevo</span>}</td>
                  <td><Fecha valor={i.enviado_en} /></td>
                  <td><strong>{i.repositorio}</strong><br /><span className="secundario">{i.workflow}</span></td>
                  <td>{i.desarrollador}</td>
                  {mostrarLider && <td>{i.lider}</td>}
                  <td><NivelRiesgo nivel={i.nivel_original} /> → <NivelRiesgo nivel={i.nivel_nuevo} /></td>
                  <td>{textoPuntos(i.diferencia_puntos)}</td>
                  <td>{i.decision_final ? i.decision_final.texto : <span className="secundario">Pendiente</span>}</td>
                  <td>
                    <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => abrir?.(i.id)}>
                      Abrir<span className="solo-lector"> el informe {i.numero}</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
