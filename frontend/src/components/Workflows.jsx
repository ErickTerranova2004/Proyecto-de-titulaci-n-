import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { Alerta, Fecha } from "./comunes.jsx";
import { Aviso, Dialogo, Filtros, Indicador } from "./gestion.jsx";

// Workflows de GitHub Actions. Solo los validados y disponibles en GitHub se
// ofrecen en Nuevo análisis. Validar exige documentar la evidencia.

const FILTROS = [
  ["todos", "Todos", () => true],
  ["utilizables", "Utilizables", (w) => w.validado && w.disponible],
  ["validados", "Validados", (w) => w.validado],
  ["sin_validar", "Sin validar", (w) => !w.validado],
  ["no_disponibles", "No disponibles en GitHub", (w) => !w.disponible],
];
const POR_PAGINA = 25;

export default function Workflows() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [cargando, setCargando] = useState(false);
  const [filtro, setFiltro] = useState("todos");
  const [busqueda, setBusqueda] = useState("");
  const [pagina, setPagina] = useState(1);
  const [seleccion, setSeleccion] = useState(new Set());
  const [editando, setEditando] = useState(null);
  const [validandoLote, setValidandoLote] = useState(false);

  function cargar() {
    setCargando(true);
    setError("");
    api
      .gestionWorkflows()
      .then((d) => {
        setDatos(d);
        setSeleccion(new Set());
      })
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }
  useEffect(cargar, []);

  function avisar(texto) {
    setAviso(texto);
    setTimeout(() => setAviso(""), 3500);
  }

  function reemplazar(w) {
    setDatos((d) => ({ ...d, workflows: d.workflows.map((x) => (x.id === w.id ? w : x)) }));
  }

  const workflows = datos ? datos.workflows : [];
  const conteos = useMemo(
    () => Object.fromEntries(FILTROS.map(([id, , f]) => [id, workflows.filter(f).length])),
    [workflows],
  );
  const condicion = FILTROS.find(([id]) => id === filtro)[2];
  const texto = busqueda.trim().toLowerCase();
  const visibles = workflows.filter(
    (w) => condicion(w) && (!texto || w.repositorio.toLowerCase().includes(texto) || w.path.toLowerCase().includes(texto)),
  );
  const paginas = Math.max(1, Math.ceil(visibles.length / POR_PAGINA));
  const paginaActual = Math.min(pagina, paginas);
  const filas = visibles.slice((paginaActual - 1) * POR_PAGINA, paginaActual * POR_PAGINA);
  const todosMarcados = filas.length > 0 && filas.every((w) => seleccion.has(w.id));

  function cambiarFiltro(id) {
    setFiltro(id);
    setPagina(1);
  }

  function alternar(id) {
    const s = new Set(seleccion);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    setSeleccion(s);
  }

  function marcarPagina() {
    const s = new Set(seleccion);
    filas.forEach((w) => {
      if (todosMarcados) s.delete(w.id);
      else s.add(w.id);
    });
    setSeleccion(s);
  }

  function quitarValidacion() {
    if (!window.confirm(`¿Quitar la validación de ${seleccion.size} workflows? Dejarán de ofrecerse para nuevos análisis.`)) return;
    api
      .validarWorkflows({ ids: [...seleccion], validado: false })
      .then((r) => {
        avisar(`${r.actualizados} workflows dejaron de estar validados.`);
        cargar();
      })
      .catch((e) => setError(e.message));
  }

  return (
    <section className="vista" aria-labelledby="titulo-workflows">
      <div className="panel__cabecera">
        <div>
          <h1 id="titulo-workflows">Workflows</h1>
          <p className="secundario">
            Workflows de GitHub Actions. Solo los validados y disponibles en GitHub se ofrecen para nuevos análisis.
          </p>
        </div>
        <div className="panel__acciones">
          <button className="boton boton--secundario" type="button" onClick={cargar} disabled={cargando}>
            {cargando ? "Actualizando…" : "Actualizar"}
          </button>
        </div>
      </div>

      <Alerta>{error}</Alerta>
      <Aviso texto={aviso} />
      {!datos && !error && <p role="status" className="secundario">Cargando workflows…</p>}

      {datos && (
        <>
          <div className="kpis">
            <Indicador icono="workflows" titulo="Workflows" valor={conteos.todos} detalle="Registrados en la plataforma" />
            <Indicador icono="verificado" titulo="Utilizables" valor={conteos.utilizables} detalle="Validados y disponibles" />
            <Indicador icono="repositorio" titulo="Validados" valor={conteos.validados} detalle="Con evidencia documentada" />
            <Indicador
              icono="pendiente"
              titulo="Sin validar"
              valor={conteos.sin_validar}
              nivel={conteos.sin_validar ? "medio" : undefined}
              detalle="Pendientes de revisión"
            />
            <Indicador
              icono="enlace"
              titulo="No disponibles"
              valor={conteos.no_disponibles}
              nivel={conteos.no_disponibles ? "alto" : undefined}
              detalle="Renombrados o eliminados en GitHub"
            />
          </div>

          <section className="tarjeta" aria-labelledby="titulo-lista-workflows">
            <h2 id="titulo-lista-workflows">Workflows registrados</h2>
            <div className="gestion-barra">
              <Filtros opciones={FILTROS} valor={filtro} conteos={conteos} alCambiar={cambiarFiltro} etiqueta="Filtrar workflows" />
              <label className="campo campo--en-linea gestion-buscar">
                <span className="solo-lector">Buscar workflow</span>
                <input
                  type="search"
                  placeholder="Buscar por repositorio o archivo"
                  value={busqueda}
                  onChange={(e) => {
                    setBusqueda(e.target.value);
                    setPagina(1);
                  }}
                />
              </label>
            </div>

            {seleccion.size > 0 && (
              <div className="gestion-lote" role="region" aria-label="Acciones sobre la selección">
                <strong>{seleccion.size} seleccionados</strong>
                <button className="boton boton--pequeno" type="button" onClick={() => setValidandoLote(true)}>Validar</button>
                <button className="boton boton--secundario boton--pequeno" type="button" onClick={quitarValidacion}>Quitar validación</button>
                <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => setSeleccion(new Set())}>Limpiar</button>
              </div>
            )}

            {!filas.length ? (
              <p className="secundario">No hay workflows que coincidan con el filtro.</p>
            ) : (
              <div className="tabla-contenedor">
                <table>
                  <caption className="solo-lector">Workflows de GitHub Actions</caption>
                  <thead>
                    <tr>
                      <th scope="col">
                        <input type="checkbox" checked={todosMarcados} onChange={marcarPagina} aria-label="Seleccionar los workflows de esta página" />
                      </th>
                      <th scope="col">Repositorio</th>
                      <th scope="col">Workflow</th>
                      <th scope="col">Despliegue</th>
                      <th scope="col">GitHub</th>
                      <th scope="col" className="numero">Ejecuciones</th>
                      <th scope="col" className="numero">Análisis</th>
                      <th scope="col"><span className="solo-lector">Acciones</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {filas.map((w) => (
                      <tr key={w.id}>
                        <td>
                          <input type="checkbox" checked={seleccion.has(w.id)} onChange={() => alternar(w.id)} aria-label={`Seleccionar ${w.path} de ${w.repositorio}`} />
                        </td>
                        <td>
                          <strong>{w.repositorio}</strong>
                          {w.demostracion && <span className="gestion-insignia">demo</span>}
                        </td>
                        <td>
                          <div className="gestion-archivo">
                            <span>{w.nombre}</span>
                            <span className="gestion-mono">{w.path}</span>
                          </div>
                        </td>
                        <td>
                          <span className={`gestion-estado gestion-estado--${w.validado ? "ok" : "pendiente"}`}>
                            {w.validado ? "Validado" : "Sin validar"}
                          </span>
                        </td>
                        <td>
                          <span className={`gestion-estado gestion-estado--${w.disponible ? "ok" : "error"}`}>
                            {w.disponible ? "Disponible" : "No disponible"}
                          </span>
                        </td>
                        <td className="numero">{w.ejecuciones}</td>
                        <td className="numero">{w.predicciones}</td>
                        <td>
                          <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => setEditando(w)}>
                            Gestionar<span className="solo-lector"> {w.path} de {w.repositorio}</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {paginas > 1 && (
              <div className="gestion-paginacion">
                <button className="boton boton--secundario boton--pequeno" type="button" disabled={paginaActual <= 1} onClick={() => setPagina(paginaActual - 1)}>
                  ← Anterior
                </button>
                <span className="secundario">
                  Página {paginaActual} de {paginas} · {visibles.length} workflows
                </span>
                <button className="boton boton--secundario boton--pequeno" type="button" disabled={paginaActual >= paginas} onClick={() => setPagina(paginaActual + 1)}>
                  Siguiente →
                </button>
              </div>
            )}
          </section>
        </>
      )}

      {editando && (
        <DialogoWorkflow
          workflow={editando}
          patronPorDefecto={datos.patron_por_defecto}
          alCerrar={() => setEditando(null)}
          alActualizar={reemplazar}
          alGuardar={(w) => {
            reemplazar(w);
            setEditando(null);
            avisar(`Workflow ${w.path} actualizado.`);
          }}
        />
      )}
      {validandoLote && (
        <DialogoLote
          cantidad={seleccion.size}
          ids={[...seleccion]}
          alCerrar={() => setValidandoLote(false)}
          alHecho={(n) => {
            setValidandoLote(false);
            avisar(`${n} workflows validados.`);
            cargar();
          }}
        />
      )}
    </section>
  );
}

function DialogoWorkflow({ workflow, patronPorDefecto, alCerrar, alActualizar, alGuardar }) {
  const [actual, setActual] = useState(workflow);
  const [validado, setValidado] = useState(workflow.validado);
  const [evidencia, setEvidencia] = useState(workflow.evidencia);
  const [patron, setPatron] = useState(workflow.patron);
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [comprobando, setComprobando] = useState(false);

  function comprobar() {
    setComprobando(true);
    setError("");
    api
      .comprobarWorkflow(actual.id)
      .then((w) => {
        setActual(w);
        alActualizar(w);
      })
      .catch((e) => setError(e.message))
      .finally(() => setComprobando(false));
  }

  function guardar(e) {
    e.preventDefault();
    if (validado && !evidencia.trim()) {
      setError("Un workflow validado debe documentar la evidencia.");
      return;
    }
    setGuardando(true);
    setError("");
    api
      .editarWorkflow(actual.id, { validado, evidencia, patron })
      .then(alGuardar)
      .catch((err) => {
        setError(err.message);
        setGuardando(false);
      });
  }

  return (
    <Dialogo titulo="Gestionar workflow" alCerrar={alCerrar} ancho={720}>
      <form onSubmit={guardar}>
        <dl className="gestion-datos">
          <dt>Repositorio</dt><dd>{actual.repositorio}{actual.demostracion && <span className="gestion-insignia">demo</span>}</dd>
          <dt>Archivo</dt><dd className="gestion-mono">{actual.path}</dd>
          <dt>Validado por</dt>
          <dd>{actual.validado_por ? <>{actual.validado_por} · <Fecha valor={actual.validado_en} /></> : "—"}</dd>
          <dt>GitHub</dt>
          <dd>
            <span className={`gestion-estado gestion-estado--${actual.disponible ? "ok" : "error"}`}>
              {actual.disponible ? "Disponible" : "No disponible"}
            </span>
            {actual.verificado_en && <span className="secundario"> · comprobado <Fecha valor={actual.verificado_en} /></span>}
          </dd>
          <dt>Uso</dt><dd>{actual.ejecuciones} ejecuciones · {actual.predicciones} análisis</dd>
        </dl>

        <div className="gestion-dialogo__acciones gestion-dialogo__acciones--inicio">
          <button type="button" className="boton boton--secundario boton--pequeno" onClick={comprobar} disabled={comprobando}>
            {comprobando ? "Comprobando…" : "Comprobar en GitHub"}
          </button>
          <a className="boton boton--secundario boton--pequeno" href={actual.url} target="_blank" rel="noreferrer">
            Ver archivo en GitHub ↗
          </a>
        </div>

        <label className="gestion-check">
          <input type="checkbox" checked={validado} onChange={(e) => setValidado(e.target.checked)} />
          <span>Validado como workflow de despliegue a una aplicación</span>
        </label>
        {!validado && workflow.validado && (
          <p className="secundario nota-pie">
            Dejará de ofrecerse en Nuevo análisis. Los {actual.predicciones} análisis existentes se conservan.
          </p>
        )}

        <label className="campo"><span>Evidencia de la validación {validado && "(obligatoria)"}</span>
          <textarea
            value={evidencia}
            onChange={(e) => setEvidencia(e.target.value)}
            placeholder="Ej.: el job 'deploy' ejecuta 'vercel deploy --prod' sobre la rama main."
          />
        </label>

        <label className="campo"><span>Patrón del paso de despliegue (expresión regular)</span>
          <textarea className="gestion-mono" value={patron} onChange={(e) => setPatron(e.target.value)} />
        </label>
        {patron !== patronPorDefecto && (
          <button type="button" className="boton boton--secundario boton--pequeno" onClick={() => setPatron(patronPorDefecto)}>
            Restaurar patrón por defecto
          </button>
        )}

        <Alerta>{error}</Alerta>
        <div className="gestion-dialogo__acciones">
          <button type="button" className="boton boton--secundario" onClick={alCerrar}>Cancelar</button>
          <button className="boton" disabled={guardando}>{guardando ? "Guardando…" : "Guardar cambios"}</button>
        </div>
      </form>
    </Dialogo>
  );
}

function DialogoLote({ cantidad, ids, alCerrar, alHecho }) {
  const [evidencia, setEvidencia] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  function enviar(e) {
    e.preventDefault();
    setEnviando(true);
    setError("");
    api
      .validarWorkflows({ ids, validado: true, evidencia })
      .then((r) => alHecho(r.actualizados))
      .catch((err) => {
        setError(err.message);
        setEnviando(false);
      });
  }

  return (
    <Dialogo titulo={`Validar ${cantidad} workflows`} alCerrar={alCerrar}>
      <form onSubmit={enviar}>
        <p className="secundario">
          Se validarán los seleccionados que aún no lo estén. La evidencia se guarda en cada uno y queda registrado que usted los validó.
        </p>
        <label className="campo"><span>Evidencia (obligatoria)</span>
          <textarea value={evidencia} onChange={(e) => setEvidencia(e.target.value)} required autoFocus />
        </label>
        <Alerta>{error}</Alerta>
        <div className="gestion-dialogo__acciones">
          <button type="button" className="boton boton--secundario" onClick={alCerrar}>Cancelar</button>
          <button className="boton" disabled={enviando || !evidencia.trim()}>{enviando ? "Validando…" : "Validar"}</button>
        </div>
      </form>
    </Dialogo>
  );
}