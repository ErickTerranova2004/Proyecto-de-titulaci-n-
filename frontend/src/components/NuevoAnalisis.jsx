import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import {
  commitsPendientes,
  datosPendientes,
  ordenarRepos,
  pendientesRepo,
  textoPendientes,
  workflowInicial,
} from "../pendientes.js";
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
  // 409 commit_ya_desplegado: el commit ya se desplegó o se está desplegando.
  const [aviso, setAviso] = useState(null);
  const refResultado = useRef(null);
  const refCommit = useRef(null);
  const campo = (nombre) => (e) => {
    setAviso(null);
    setDatos({ ...datos, [nombre]: e.target.value });
  };

  useEffect(() => {
    api
      .repositorios()
      .then((r) => setRepos(ordenarRepos(r)))
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (resultado) refResultado.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [resultado]);
  const workflows = repos?.find((r) => r.nombre_completo === datos.repositorio)?.workflows || [];
  const workflowElegido = workflows.find((w) => w.path === datos.workflow_path);
  const pendientes = commitsPendientes(workflowElegido) ? workflowElegido.pendientes : null;

  // Con commits pendientes se rellenan commit, rama y evento; si no, se vacía
  // el commit (podría ser de otro repositorio).
  function conWorkflow(base, workflow) {
    const relleno = datosPendientes(workflow, EVENTOS);
    return { ...base, workflow_path: workflow?.path || "", ...(relleno ?? { head_sha: "" }) };
  }

  function elegirRepositorio(e) {
    const repo = repos.find((r) => r.nombre_completo === e.target.value);
    setError("");
    setAviso(null);
    setDatos(conWorkflow({ ...datos, repositorio: e.target.value }, workflowInicial(repo)));
  }

  function elegirWorkflow(e) {
    setAviso(null);
    setDatos(conWorkflow(datos, workflows.find((w) => w.path === e.target.value)));
  }

  async function enviar(e, confirmar = false) {
    e?.preventDefault();
    setCargando(true);
    setError("");
    setAviso(null);
    setResultado(null);
    try {
      let enviados = respuesta
        ? { ...datos, atiende_decision: respuesta.asignacion.id, respuesta_desarrollador: cambios }
        : datos;
      if (confirmar) enviados = { ...enviados, confirmar_desplegado: true };
      setResultado(await api.predecir(enviados));
      if (respuesta) alResponder?.();
    } catch (err) {
      if (err.estado === 409 && err.datos?.codigo === "commit_ya_desplegado") setAviso(err.datos);
      else setError(err.message);
    } finally {
      setCargando(false);
    }
  }

  function elegirOtroCommit() {
    setAviso(null);
    setDatos({ ...datos, head_sha: "" });
    refCommit.current?.focus();
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
                {repos?.map((r) => {
                  const marca = textoPendientes(pendientesRepo(r));
                  return (
                    <option key={r.id} value={r.nombre_completo}>
                      {marca ? `${r.nombre_completo} — ${marca}` : r.nombre_completo}
                    </option>
                  );
                })}
              </select>
            </div>
            <div className="campo">
              <label htmlFor="campo-workflow">Workflow de despliegue</label>
              <select
                id="campo-workflow"
                value={datos.workflow_path}
                onChange={elegirWorkflow}
                required
                disabled={!workflows.length}
              >
                {workflows.length ? (
                  workflows.map((w) => {
                    const marca = textoPendientes(commitsPendientes(w));
                    return (
                      <option key={w.path} value={w.path}>
                        {marca ? `${w.path} — ${marca}` : w.path}
                      </option>
                    );
                  })
                ) : (
                  <option value="">Sin workflows disponibles</option>
                )}
              </select>
            </div>
          </div>
          {datos.repositorio && !workflows.length && (
            <Alerta>Este repositorio no tiene workflows de despliegue validados.</Alerta>
          )}
          {repos?.some((r) => pendientesRepo(r)) && (
            <p className="secundario">
              Primero aparecen los repositorios con commits pendientes de desplegar: analícelos antes de su próximo
              despliegue para poder compararlos con el resultado real.
            </p>
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
                ref={refCommit}
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
          {pendientes && (
            <p className="nota" role="status">
              {textoPendientes(pendientes.commits)} sin desplegar en <strong>{pendientes.rama_principal}</strong> desde
              el último despliegue correcto (<Fecha valor={pendientes.ultimo_despliegue_en} />
              {pendientes.evento && <>, evento {pendientes.evento}</>}). Se rellenaron el último commit, la rama
              {pendientes.evento === "release" && " (el tag probable de la próxima versión)"} y el evento. Datos de la
              tarea programada del <Fecha valor={pendientes.calculado_en} />.
            </p>
          )}
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
        {aviso && (
          <div className="aviso-desplegado" role="alert">
            <p>
              <strong>{aviso.en_curso ? "Este commit se está desplegando ahora." : "Este commit ya se desplegó."}</strong>{" "}
              El análisis no podrá compararse con un resultado real: solo se enlaza un despliegue que empiece después del
              análisis.
            </p>
            <p className="secundario">
              Ejecución{" "}
              {aviso.ejecucion.url ? (
                <a href={aviso.ejecucion.url} target="_blank" rel="noreferrer">
                  {aviso.ejecucion.run_id}
                </a>
              ) : (
                aviso.ejecucion.run_id
              )}{" "}
              ({aviso.ejecucion.evento}
              {aviso.ejecucion.rama && <> · {aviso.ejecucion.rama}</>}), iniciada <Fecha valor={aviso.ejecucion.iniciada_en} />
              {aviso.ejecucion.conclusion && <> · conclusión {aviso.ejecucion.conclusion}</>}.
            </p>
            <div className="aviso-desplegado__acciones">
              <button className="boton boton--secundario" type="button" onClick={elegirOtroCommit}>
                Elegir otro commit
              </button>
              <button className="boton" type="button" disabled={cargando} onClick={() => enviar(null, true)}>
                Analizar de todos modos
              </button>
            </div>
          </div>
        )}
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
