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
import { Alerta, DECISIONES, EstadoAsignacion, Fecha, FechaDia, textoPlazo } from "./comunes.jsx";
import Resultado from "./Resultado.jsx";

// Mismas opciones que acepta el backend (SolicitudPrediccionSerializer.EVENTOS).
const EVENTOS = ["push", "workflow_dispatch", "release", "pull_request", "schedule", "workflow_run"];

// «17 nov 2026, 16:18»: fecha legible de la asignación (sin estilo monoespaciado).
function fechaLegible(valor) {
  if (!valor) return "";
  return new Date(valor).toLocaleString("es-EC", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

// Tarjeta con la asignación del líder que este análisis responde.
function AvisoAsignacion({ asignacion }) {
  const decision = DECISIONES[asignacion.decision] ?? asignacion.decision;
  return (
    <section className="aviso-asignacion" role="status" aria-labelledby="titulo-asignacion">
      <div className="aviso-asignacion__cabecera">
        <span className="aviso-asignacion__icono" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 11l3 3L22 4" />
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
          </svg>
        </span>
        <div>
          <p className="aviso-asignacion__etiqueta">Respondiendo a una asignación</p>
          <h2 id="titulo-asignacion" className="aviso-asignacion__decision">{decision}</h2>
        </div>
        {asignacion.estado && (
          <span className="aviso-asignacion__estado">
            <EstadoAsignacion estado={asignacion.estado} />
          </span>
        )}
      </div>

      {asignacion.mensaje && (
        <blockquote className="aviso-asignacion__mensaje">
          <p>{asignacion.mensaje}</p>
        </blockquote>
      )}

      <dl className="aviso-asignacion__datos">
        <div>
          <dt>Asignada por</dt>
          <dd><strong>{asignacion.lider}</strong></dd>
        </div>
        <div>
          <dt>Fecha</dt>
          <dd><time dateTime={asignacion.creada_en}>{fechaLegible(asignacion.creada_en)}</time></dd>
        </div>
        <div>
          <dt>Fecha límite</dt>
          <dd>
            {asignacion.fecha_limite ? (
              <>
                <FechaDia valor={asignacion.fecha_limite} />
                <span className="aviso-asignacion__plazo"> · {textoPlazo(asignacion)}</span>
              </>
            ) : (
              "Sin fecha límite"
            )}
          </dd>
        </div>
      </dl>

      <p className="aviso-asignacion__pie">Al terminar este análisis, la asignación quedará cumplida.</p>
    </section>
  );
}

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

      {respuesta && <AvisoAsignacion asignacion={respuesta.asignacion} />}

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
