import { useState } from "react";
import { api } from "../api.js";
import { Alerta, Fecha, porcentaje } from "./comunes.jsx";

const METRICAS = ["PR-AUC", "ROC-AUC", "Precision", "Recall", "F1", "Brier"];

export default function Modelos({ modelos, esAdmin, alCambiar }) {
  const [error, setError] = useState("");

  async function activar(id) {
    setError("");
    try {
      await api.activarModelo(id);
      alCambiar();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <section className="vista" aria-labelledby="titulo-modelos">
      <h1 id="titulo-modelos">Versiones del modelo</h1>
      <Alerta>{error}</Alerta>
      <div className="tabla-contenedor">
        <table>
          <caption>
            Modelos registrados. Las métricas corresponden a la partición temporal de prueba de cada versión.
          </caption>
          <thead>
            <tr>
              <th scope="col">Versión</th>
              <th scope="col">Modelo</th>
              <th scope="col">Estado</th>
              <th scope="col" className="numero">Filas de entrenamiento</th>
              <th scope="col" className="numero">Filas de prueba</th>
              {METRICAS.map((m) => (
                <th key={m} scope="col" className="numero">{m}</th>
              ))}
              <th scope="col">Límites de riesgo (medio / alto)</th>
              <th scope="col">Registrado</th>
              {esAdmin && <th scope="col"><span className="solo-lector">Acciones</span></th>}
            </tr>
          </thead>
          <tbody>
            {modelos.map((m) => {
              const met = m.metadatos.metricas_prueba;
              const limites = m.metadatos.limites_riesgo;
              return (
                <tr key={m.id}>
                  <td>{m.version}</td>
                  <td>{m.nombre_modelo}</td>
                  <td>{m.activo ? <strong>Activo</strong> : "Inactivo"}</td>
                  <td className="numero">{m.metadatos.filas_entrenamiento}</td>
                  <td className="numero">{m.metadatos.filas_prueba}</td>
                  {METRICAS.map((clave) => (
                    <td key={clave} className="numero">{met[clave].toFixed(3)}</td>
                  ))}
                  <td>{porcentaje(limites.medio)} / {porcentaje(limites.alto)}</td>
                  <td><Fecha valor={m.registrado_en} /></td>
                  {esAdmin && (
                    <td>
                      {!m.activo && (
                        <button className="boton boton--secundario" type="button" onClick={() => activar(m.id)}>
                          Activar<span className="solo-lector"> {m.version}</span>
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
