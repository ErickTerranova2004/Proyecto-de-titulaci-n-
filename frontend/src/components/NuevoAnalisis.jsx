import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alerta } from "./comunes.jsx";
import Resultado from "./Resultado.jsx";

// Mismas opciones que acepta el backend (SolicitudPrediccionSerializer.EVENTOS).
const EVENTOS = ["push", "workflow_dispatch", "release", "pull_request", "schedule", "workflow_run"];

export default function NuevoAnalisis({ modelos }) {
  const [repos, setRepos] = useState([]);
  const [datos, setDatos] = useState({
    repositorio: "",
    workflow_path: "",
    rama: "main",
    head_sha: "",
    evento: "push",
  });
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [resultado, setResultado] = useState(null);
  const campo = (nombre) => (e) => setDatos({ ...datos, [nombre]: e.target.value });

  useEffect(() => {
    api.repositorios().then(setRepos).catch((e) => setError(e.message));
  }, []);
  const workflows = repos.find((r) => r.nombre_completo === datos.repositorio)?.workflows || [];

  function elegirRepositorio(e) {
    const repo = repos.find((r) => r.nombre_completo === e.target.value);
    setDatos({ ...datos, repositorio: e.target.value, workflow_path: repo?.workflows[0]?.path || "" });
  }

  async function enviar(e) {
    e.preventDefault();
    setCargando(true);
    setError("");
    try {
      setResultado(await api.predecir(datos));
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <section className="vista" aria-labelledby="titulo-nuevo">
      <h1 id="titulo-nuevo">Nuevo análisis</h1>
      <form className="tarjeta formulario" onSubmit={enviar} aria-describedby="ayuda-nuevo">
        <p id="ayuda-nuevo" className="secundario">
          Solo aparecen los repositorios a los que tiene acceso y sus workflows de despliegue validados.
        </p>
        <fieldset>
          <legend>Repositorio y workflow</legend>
          <div className="campos">
            <div className="campo">
              <label htmlFor="campo-repositorio">Repositorio</label>
              <select id="campo-repositorio" value={datos.repositorio} onChange={elegirRepositorio} required>
                <option value="">Seleccione un repositorio</option>
                {repos.map((r) => (
                  <option key={r.id} value={r.nombre_completo}>{r.nombre_completo}</option>
                ))}
              </select>
            </div>
            <div className="campo">
              <label htmlFor="campo-workflow">Workflow de despliegue</label>
              <select
                id="campo-workflow"
                value={datos.workflow_path}
                onChange={campo("workflow_path")}
                required
                disabled={!workflows.length}
              >
                {workflows.map((w) => (
                  <option key={w.path} value={w.path}>{w.path}</option>
                ))}
              </select>
            </div>
          </div>
          {datos.repositorio && !workflows.length && (
            <Alerta>Este repositorio no tiene workflows de despliegue validados.</Alerta>
          )}
          {!repos.length && !error && (
            <p className="secundario">No tiene repositorios asignados. Solicite acceso al administrador.</p>
          )}
        </fieldset>

        <fieldset>
          <legend>Contexto del despliegue</legend>
          <p id="ayuda-contexto" className="secundario">
            Indique la rama o un commit concreto. Si deja el commit vacío se usa el último de la rama.
          </p>
          <div className="campos">
            <div className="campo">
              <label htmlFor="campo-rama">Rama</label>
              <input
                id="campo-rama"
                value={datos.rama}
                onChange={campo("rama")}
                aria-describedby="ayuda-contexto"
                required={!datos.head_sha}
              />
            </div>
            <div className="campo">
              <label htmlFor="campo-commit">Commit (SHA, opcional)</label>
              <input
                id="campo-commit"
                value={datos.head_sha}
                onChange={campo("head_sha")}
                aria-describedby="ayuda-contexto"
                pattern="[0-9a-fA-F]{7,40}"
                spellCheck="false"
              />
            </div>
            <div className="campo">
              <label htmlFor="campo-evento">Evento</label>
              <select id="campo-evento" value={datos.evento} onChange={campo("evento")} required>
                {EVENTOS.map((ev) => (
                  <option key={ev} value={ev}>{ev}</option>
                ))}
              </select>
            </div>
          </div>
        </fieldset>

        <Alerta>{error}</Alerta>
        <div>
          <button className="boton" type="submit" disabled={cargando}>
            {cargando ? "Consultando GitHub…" : "Estimar riesgo"}
          </button>
        </div>
      </form>

      {resultado && <Resultado prediccion={resultado} modelos={modelos} />}
    </section>
  );
}
