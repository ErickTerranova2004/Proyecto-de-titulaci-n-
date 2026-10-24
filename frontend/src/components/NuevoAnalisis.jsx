import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { Alerta, DECISIONES, Fecha } from "./comunes.jsx";
import Resultado from "./Resultado.jsx";

// Mismas opciones que acepta el backend (SolicitudPrediccionSerializer.EVENTOS).
const EVENTOS = ["push", "workflow_dispatch", "release", "pull_request", "schedule", "workflow_run"];

// `respuesta`: asignación del líder que este análisis atiende (opcional). Llega
// con el repositorio, el workflow y la rama del análisis original.
export default function NuevoAnalisis({ modelos, respuesta, alResponder }) {
  const [repos, setRepos] = useState(null);
  const [datos, setDatos] = useState({
    repositorio: respuesta?.repositorio ?? "",
    workflow_path: respuesta?.workflow_path ?? "",
    rama: respuesta?.rama || "main",
    head_sha: "",
    evento: "push",
  });
  const [cambios, setCambios] = useState("");
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");
  const [resultado, setResultado] = useState(null);
  const refResultado = useRef(null);
  const campo = (nombre) => (e) => setDatos({ ...datos, [nombre]: e.target.value });

  useEffect(() => {
    api.repositorios().then(setRepos).catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (resultado) refResultado.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [resultado]);
  const workflows = repos?.find((r) => r.nombre_completo === datos.repositorio)?.workflows || [];

  function elegirRepositorio(e) {
    const repo = repos.find((r) => r.nombre_completo === e.target.value);
    setError("");
    setDatos({ ...datos, repositorio: e.target.value, workflow_path: repo?.workflows[0]?.path || "" });
  }

  async function enviar(e) {
    e.preventDefault();
    setCargando(true);
    setError("");
    setResultado(null);
    try {
      const enviados = respuesta
        ? { ...datos, atiende_decision: respuesta.asignacion.id, respuesta_desarrollador: cambios }
        : datos;
      setResultado(await api.predecir(enviados));
      if (respuesta) alResponder?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <section className="vista" aria-labelledby="titulo-nuevo">
      <header className="encabezado">
        <h1 id="titulo-nuevo">Nuevo análisis de riesgo</h1>
        <p className="secundario">
          Elija el repositorio, el workflow y el commit para estimar la probabilidad de que el despliegue no se complete.
        </p>
      </header>

      {respuesta && (
        <p className="nota" role="status">
          Respondiendo a la asignación de <strong>{respuesta.asignacion.lider}</strong> del{" "}
          <Fecha valor={respuesta.asignacion.creada_en} />: {DECISIONES[respuesta.asignacion.decision]}
          {respuesta.asignacion.mensaje && <> · «{respuesta.asignacion.mensaje}»</>}. Al terminar este análisis la
          asignación quedará cumplida.
        </p>
      )}

      <form className="tarjeta formulario" onSubmit={enviar} aria-describedby="ayuda-nuevo">
        <p id="ayuda-nuevo" className="secundario">
          Solo aparecen los repositorios a los que tiene acceso y sus workflows de despliegue validados.
        </p>
        <fieldset>
          <legend>1. Repositorio y workflow</legend>
          <div className="campos">
            <div className="campo">
              <label htmlFor="campo-repositorio">Repositorio</label>
              <select id="campo-repositorio" value={datos.repositorio} onChange={elegirRepositorio} required>
                <option value="">Seleccione un repositorio</option>
                {repos?.map((r) => (
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
                {workflows.length ? (
                  workflows.map((w) => <option key={w.path} value={w.path}>{w.path}</option>)
                ) : (
                  <option value="">Sin workflows disponibles</option>
                )}
              </select>
            </div>
          </div>
          {datos.repositorio && !workflows.length && (
            <Alerta>Este repositorio no tiene workflows de despliegue validados.</Alerta>
          )}
          {!repos && !error && <p className="secundario" role="status">Cargando repositorios accesibles…</p>}
          {repos && !repos.length && (
            <p className="secundario">No tiene repositorios asignados. Solicite acceso al administrador.</p>
          )}
        </fieldset>

        <fieldset>
          <legend>2. Contexto del despliegue</legend>
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
                placeholder="ej. main o develop"
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
                placeholder="ej. 7f8a9b0"
              />
            </div>
            <div className="campo">
              <label htmlFor="campo-evento">Evento detonante</label>
              <select id="campo-evento" value={datos.evento} onChange={campo("evento")} required>
                {EVENTOS.map((ev) => (
                  <option key={ev} value={ev}>{ev}</option>
                ))}
              </select>
            </div>
          </div>
        </fieldset>

        {respuesta && (
          <fieldset>
            <legend>3. Respuesta al líder técnico</legend>
            <div className="campo">
              <label htmlFor="campo-cambios">Qué cambié (opcional)</label>
              <textarea
                id="campo-cambios"
                rows={3}
                maxLength={1000}
                value={cambios}
                onChange={(e) => setCambios(e.target.value)}
                placeholder="ej. Corregí la versión de la imagen base y el paso de despliegue."
              />
            </div>
          </fieldset>
        )}

        <Alerta>{error}</Alerta>
        <div className="formulario__acciones">
          <button className="boton" type="submit" disabled={cargando}>
            {cargando ? "Consultando GitHub…" : "Estimar riesgo de despliegue"}
          </button>
        </div>
      </form>

      {resultado && (
        <div ref={refResultado}>
          <Resultado prediccion={resultado} modelos={modelos} />
        </div>
      )}
    </section>
  );
}
