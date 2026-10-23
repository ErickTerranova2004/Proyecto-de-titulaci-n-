import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alerta } from "./comunes.jsx";

const REGISTRO_VACIO = { repositorio: "", workflow_path: ".github/workflows/", evidencia: "" };

// Alta manual de un workflow de despliegue que no está en el dataset.
// El backend comprueba en GitHub que el repositorio y el archivo existen.
function RegistroWorkflow({ alRegistrar }) {
  const [datos, setDatos] = useState(REGISTRO_VACIO);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const [hecho, setHecho] = useState(null);

  const campo = (nombre) => (e) => setDatos({ ...datos, [nombre]: e.target.value });

  async function enviar(e) {
    e.preventDefault();
    setError("");
    setHecho(null);
    setEnviando(true);
    try {
      const r = await api.registrarWorkflow(datos);
      setHecho(r);
      setDatos(REGISTRO_VACIO);
      alRegistrar();
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="tarjeta formulario" onSubmit={enviar} aria-labelledby="titulo-registro">
      <div>
        <h2 id="titulo-registro">Registrar workflow de despliegue</h2>
        <p id="ayuda-registro" className="secundario">
          Agregue un repositorio fuera del dataset. Solo se aceptan workflows que despliegan a un entorno de
          aplicación (servidor, nube o contenedores); no workflows de pruebas, documentación o GitHub Pages.
        </p>
      </div>
      <div className="campos">
        <div className="campo">
          <label htmlFor="registro-repositorio">Repositorio</label>
          <input
            id="registro-repositorio"
            value={datos.repositorio}
            onChange={campo("repositorio")}
            pattern="[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+"
            spellCheck="false"
            placeholder="propietario/nombre"
            required
          />
        </div>
        <div className="campo">
          <label htmlFor="registro-workflow">Ruta del workflow</label>
          <input
            id="registro-workflow"
            value={datos.workflow_path}
            onChange={campo("workflow_path")}
            pattern="\.github/workflows/.+\.ya?ml"
            spellCheck="false"
            placeholder=".github/workflows/deploy.yml"
            required
          />
        </div>
      </div>
      <div className="campo">
        <label htmlFor="registro-evidencia">Evidencia de despliegue</label>
        <textarea
          id="registro-evidencia"
          rows="3"
          value={datos.evidencia}
          onChange={campo("evidencia")}
          minLength={30}
          maxLength={2000}
          aria-describedby="ayuda-registro"
          placeholder="ej. Despliega la API a AWS ECS en el paso 'Deploy to production' del job deploy."
          required
        />
      </div>
      <Alerta>{error}</Alerta>
      {hecho && (
        <p className="nota" role="status">
          {hecho.workflow_path} de {hecho.repositorio} quedó validado y disponible en Nuevo análisis.
          {hecho.ejecuciones_recientes < 10 &&
            ` Tiene ${hecho.ejecuciones_recientes} ejecuciones recientes: con poco historial la estimación es poco informativa.`}
        </p>
      )}
      <div className="formulario__acciones">
        <button className="boton" type="submit" disabled={enviando}>
          {enviando ? "Comprobando en GitHub…" : "Registrar workflow"}
        </button>
      </div>
    </form>
  );
}

// Vista del administrador: estado de la conexión con GitHub, alta manual de
// workflows y recopilación de ejecuciones de los workflows validados.
export default function Integraciones() {
  const [estado, setEstado] = useState(null);
  const [repositorios, setRepositorios] = useState([]);
  const [error, setError] = useState("");
  const [enCurso, setEnCurso] = useState(null);
  const [resultados, setResultados] = useState({});

  const cargar = () =>
    Promise.all([api.integraciones(), api.repositorios()])
      .then(([integracion, repos]) => {
        setEstado(integracion.github);
        setRepositorios(repos);
      })
      .catch((e) => setError(e.message));

  useEffect(() => {
    cargar();
  }, []);

  async function sincronizar(repo) {
    setError("");
    setEnCurso(repo.id);
    try {
      const r = await api.sincronizar(repo.id);
      setResultados((previos) => ({ ...previos, [repo.id]: r }));
      cargar();
    } catch (e) {
      setError(`${repo.nombre_completo}: ${e.message}`);
    } finally {
      setEnCurso(null);
    }
  }

  return (
    <section className="vista" aria-labelledby="titulo-integraciones">
      <header className="encabezado">
        <h1 id="titulo-integraciones">Integración con GitHub</h1>
        <p className="secundario">Estado de la conexión y recopilación de ejecuciones de los workflows validados.</p>
      </header>
      <Alerta>{error}</Alerta>
      {!estado && !error && <p role="status" className="secundario">Cargando…</p>}

      {estado && <RegistroWorkflow alRegistrar={cargar} />}

      {estado && (
        <div className="tarjeta tarjeta--tabla">
        <div className="tabla-contenedor">
          <table>
            <caption>Recopilación de ejecuciones completadas de los workflows validados de cada repositorio.</caption>
            <thead>
              <tr>
                <th scope="col">Repositorio</th>
                <th scope="col" className="numero">Workflows validados</th>
                <th scope="col">Última recopilación en esta sesión</th>
                <th scope="col"><span className="solo-lector">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {repositorios.map((repo) => {
                const r = resultados[repo.id];
                return (
                  <tr key={repo.id}>
                    <td>{repo.nombre_completo}</td>
                    <td className="numero">{repo.workflows.length}</td>
                    <td>
                      {r
                        ? `${r.ejecuciones_guardadas} ejecuciones guardadas${
                            r.errores.length ? ` · ${r.errores.length} con error: ${r.errores.join("; ")}` : ""
                          }`
                        : "—"}
                    </td>
                    <td>
                      <button
                        className="boton boton--secundario"
                        type="button"
                        disabled={enCurso !== null || !repo.workflows.length}
                        onClick={() => sincronizar(repo)}
                      >
                        {enCurso === repo.id ? "Recopilando…" : "Sincronizar"}
                        <span className="solo-lector"> {repo.nombre_completo}</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        </div>
      )}
    </section>
  );
}
