import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alerta, Fecha } from "./comunes.jsx";

// Vista del administrador: estado de la conexión con GitHub y recopilación
// manual de ejecuciones de los workflows validados de cada repositorio.
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
      <h1 id="titulo-integraciones">Integración con GitHub</h1>
      <Alerta>{error}</Alerta>
      {!estado && !error && <p role="status">Cargando…</p>}

      {estado && (
        <article className="tarjeta" aria-labelledby="titulo-conexion">
          <h2 id="titulo-conexion">Estado de la conexión</h2>
          <Alerta>{estado.error}</Alerta>
          <dl className="datos">
            <dt>API</dt>
            <dd><code>{estado.api_url}</code></dd>
            <dt>Token</dt>
            <dd>
              {estado.token_configurado
                ? "Configurado en el servidor (no se muestra)"
                : "No configurado: se usa la cuota anónima de GitHub"}
            </dd>
            <dt>Cuota de la API</dt>
            <dd>
              {estado.limite != null ? (
                <>
                  {estado.restantes} de {estado.limite} solicitudes disponibles; se renueva el{" "}
                  <Fecha valor={new Date(estado.reinicio * 1000).toISOString()} />
                </>
              ) : (
                "No disponible"
              )}
            </dd>
            <dt>Repositorios registrados</dt>
            <dd>{estado.repositorios_registrados}</dd>
            <dt>Workflows de despliegue validados</dt>
            <dd>{estado.workflows_validados}</dd>
            <dt>Ejecuciones almacenadas</dt>
            <dd>{estado.ejecuciones_almacenadas}</dd>
            <dt>Última extracción</dt>
            <dd><Fecha valor={estado.ultima_extraccion} /></dd>
          </dl>
          <p className="nota">
            El token se configura en <code>backend/.env</code> (variable <code>GITHUB_TOKEN</code>) y nunca se envía al
            navegador. La recopilación periódica se programa con el comando <code>sincronizar_github</code>.
          </p>
        </article>
      )}

      {estado && (
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
      )}
    </section>
  );
}
