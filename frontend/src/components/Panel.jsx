import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { Alerta, Fecha, NivelRiesgo, porcentaje } from "./comunes.jsx";
import { BarrasApiladas, Dona, Embudo, Linea } from "./graficos.jsx";
import Resultado from "./Resultado.jsx";

// Todos los indicadores se calculan en el navegador a partir de
// GET /api/predicciones/ (predicciones visibles para el usuario),
// GET /api/repositorios/ y GET /api/modelos/. No hay valores fijos.

const PERIODOS = [
  ["7", "Últimos 7 días"],
  ["30", "Últimos 30 días"],
  ["90", "Últimos 90 días"],
  ["todo", "Todo el historial"],
];
const DIA = 24 * 60 * 60 * 1000;

function claveDia(fecha) {
  const d = new Date(fecha);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function serieDiaria(predicciones, desde, hasta) {
  const dias = [];
  const inicio = new Date(desde);
  inicio.setHours(0, 0, 0, 0);
  for (let t = inicio.getTime(); t <= hasta; t += DIA) {
    const d = new Date(t);
    dias.push({
      clave: claveDia(d),
      etiqueta: d.toLocaleDateString("es-EC", { day: "2-digit", month: "short" }),
      bajo: 0, medio: 0, alto: 0, suma: 0, n: 0,
    });
  }
  const indice = Object.fromEntries(dias.map((d) => [d.clave, d]));
  for (const p of predicciones) {
    const d = indice[claveDia(p.creada_en)];
    if (!d) continue;
    d[p.nivel] += 1;
    d.suma += p.probabilidad;
    d.n += 1;
  }
  return dias.map((d) => ({ ...d, valor: d.n ? d.suma / d.n : null }));
}

function nivelDe(probabilidad, limites) {
  if (!limites) return null;
  if (probabilidad >= limites.alto) return "alto";
  if (probabilidad >= limites.medio) return "medio";
  return "bajo";
}

function Icono({ tipo }) {
  const trazos = {
    analisis: "M4 19V5M4 19h16M8 15l3-4 3 2 4-6",
    alto: "M12 4l9 16H3L12 4zM12 10v4M12 17v.5",
    probabilidad: "M12 3a9 9 0 1 0 9 9h-9V3z",
    verificado: "M5 12l4 4 10-10",
    modelo: "M4 6h16v12H4zM8 10h8M8 14h5",
  };
  return (
    <svg viewBox="0 0 24 24" className="kpi__icono" aria-hidden="true">
      <path d={trazos[tipo]} />
    </svg>
  );
}

function Kpi({ icono, titulo, valor, detalle, nivel }) {
  return (
    <article className={`kpi${nivel ? ` kpi--${nivel}` : ""}`}>
      <Icono tipo={icono} />
      <div>
        <h3 className="kpi__titulo">{titulo}</h3>
        <p className="kpi__valor">{valor}</p>
        {detalle && <p className="kpi__detalle secundario">{detalle}</p>}
      </div>
    </article>
  );
}

export default function Panel({ modelos, alNuevoAnalisis }) {
  const [historial, setHistorial] = useState(null);
  const [repos, setRepos] = useState([]);
  const [error, setError] = useState("");
  const [periodo, setPeriodo] = useState("30");
  const [cargadoEn, setCargadoEn] = useState(null);
  const [seleccion, setSeleccion] = useState(null);

  function cargar() {
    setError("");
    Promise.all([api.historial(), api.repositorios()])
      .then(([h, r]) => {
        setHistorial(h);
        setRepos(r);
        setCargadoEn(new Date().toISOString());
      })
      .catch((e) => setError(e.message));
  }
  useEffect(cargar, []);

  const activo = modelos.find((m) => m.activo);
  const limites = activo?.metadatos?.limites_riesgo;

  const datos = useMemo(() => {
    if (!historial) return null;
    const ahora = Date.now();
    const fechas = historial.map((p) => new Date(p.creada_en).getTime());
    const desde = periodo === "todo"
      ? Math.min(ahora, ...fechas)
      : ahora - Number(periodo) * DIA;
    const enPeriodo = historial.filter((p) => new Date(p.creada_en).getTime() >= desde);
    const anterior = periodo === "todo"
      ? null
      : historial.filter((p) => {
          const t = new Date(p.creada_en).getTime();
          return t < desde && t >= desde - Number(periodo) * DIA;
        }).length;

    const conteos = { bajo: 0, medio: 0, alto: 0 };
    enPeriodo.forEach((p) => { conteos[p.nivel] += 1; });
    const total = enPeriodo.length;
    const probMedia = total ? enPeriodo.reduce((s, p) => s + p.probabilidad, 0) / total : null;
    const verificadas = enPeriodo.filter((p) => p.ejecucion_real);
    const evaluables = verificadas.filter((p) => p.ejecucion_real.y !== null && p.ejecucion_real.y !== undefined);
    const noCompletados = evaluables.filter((p) => p.ejecucion_real.y === 1);

    const porRepo = {};
    enPeriodo.forEach((p) => {
      const r = (porRepo[p.repositorio] ||= { repositorio: p.repositorio, n: 0, suma: 0, alto: 0, ultimo: p.creada_en });
      r.n += 1;
      r.suma += p.probabilidad;
      if (p.nivel === "alto") r.alto += 1;
      if (p.creada_en > r.ultimo) r.ultimo = p.creada_en;
    });
    const repositorios = Object.values(porRepo)
      .map((r) => ({ ...r, media: r.suma / r.n }))
      .sort((a, b) => b.media - a.media)
      .slice(0, 8);

    return {
      total, anterior, conteos, probMedia, verificadas, evaluables, noCompletados, repositorios,
      dias: serieDiaria(enPeriodo, desde, ahora),
      recientes: [...enPeriodo].sort((a, b) => (a.creada_en < b.creada_en ? 1 : -1)).slice(0, 6),
    };
  }, [historial, periodo]);

  const nombrePeriodo = PERIODOS.find(([id]) => id === periodo)[1].toLowerCase();
  const workflowsValidados = repos.reduce((s, r) => s + r.workflows.length, 0);
  const nVariables = activo
    ? activo.metadatos.variables_categoricas.length + activo.metadatos.variables_numericas.length
    : null;

  if (seleccion) {
    return (
      <section className="vista" aria-labelledby="titulo-panel">
        <h1 id="titulo-panel">Panel de riesgo de despliegue</h1>
        <div>
          <button className="boton boton--secundario" type="button" onClick={() => setSeleccion(null)}>
            ← Volver al panel
          </button>
        </div>
        <Resultado prediccion={seleccion} modelos={modelos} />
      </section>
    );
  }

  return (
    <section className="vista panel" aria-labelledby="titulo-panel">
      <div className="panel__cabecera">
        <div>
          <h1 id="titulo-panel">Panel de riesgo de despliegue</h1>
          <p className="secundario">
            Análisis visibles para su usuario · {nombrePeriodo}
            {cargadoEn && <> · datos cargados <Fecha valor={cargadoEn} /></>}
          </p>
        </div>
        <div className="panel__acciones">
          <label className="campo campo--en-linea" htmlFor="panel-periodo">
            <span>Período</span>
            <select id="panel-periodo" value={periodo} onChange={(e) => setPeriodo(e.target.value)}>
              {PERIODOS.map(([id, texto]) => <option key={id} value={id}>{texto}</option>)}
            </select>
          </label>
          <button className="boton boton--secundario" type="button" onClick={cargar}>Actualizar</button>
          <button className="boton" type="button" onClick={alNuevoAnalisis}>Nuevo análisis</button>
        </div>
      </div>

      <Alerta>{error}</Alerta>
      {!datos && !error && <p role="status">Cargando…</p>}

      {datos && (
        <>
          <section aria-labelledby="titulo-kpi">
            <h2 id="titulo-kpi" className="solo-lector">Indicadores del período</h2>
            <div className="kpis">
              <Kpi
                icono="analisis"
                titulo="Análisis realizados"
                valor={datos.total}
                detalle={datos.anterior === null ? "Todo el historial" : `${datos.anterior} en el período anterior`}
              />
              <Kpi
                icono="alto"
                titulo="Riesgo Alto"
                valor={datos.conteos.alto}
                nivel="alto"
                detalle={datos.total ? `${porcentaje(datos.conteos.alto / datos.total)} de los análisis` : "Sin análisis"}
              />
              <Kpi
                icono="probabilidad"
                titulo="Probabilidad media"
                valor={datos.probMedia === null ? "—" : porcentaje(datos.probMedia)}
                detalle="De despliegue no completado"
              />
              <Kpi
                icono="verificado"
                titulo="Resultados verificados"
                valor={`${datos.verificadas.length} / ${datos.total}`}
                detalle={`${datos.noCompletados.length} no completados de ${datos.evaluables.length} evaluables`}
              />
              <Kpi
                icono="modelo"
                titulo="Modelo activo"
                valor={activo ? activo.version : "—"}
                detalle={activo
                  ? `${activo.nombre_modelo} · PR-AUC ${activo.metadatos.metricas_prueba["PR-AUC"].toFixed(3)}`
                  : "No hay un modelo activo"}
              />
            </div>
          </section>

          <section className="tarjeta" aria-labelledby="titulo-flujo">
            <h2 id="titulo-flujo">Flujo de la plataforma</h2>
            <ol className="flujo">
              <li><strong>Fuente: GitHub</strong><span className="secundario">{repos.length} repositorios accesibles</span></li>
              <li><strong>Integración y recolección</strong><span className="secundario">{workflowsValidados} workflows de despliegue validados</span></li>
              <li><strong>Base de datos histórica</strong><span className="secundario">{historial.length} análisis registrados</span></li>
              <li><strong>Preparación de datos</strong><span className="secundario">{nVariables === null ? "—" : `${nVariables} variables por análisis`}</span></li>
              <li><strong>Modelo predictivo</strong><span className="secundario">{activo ? `${activo.version} · ${activo.nombre_modelo}` : "Sin modelo activo"}</span></li>
              <li><strong>IA explicable</strong><span className="secundario">Factores SHAP en cada análisis</span></li>
            </ol>
          </section>

          {datos.total === 0 ? (
            <section className="tarjeta vacio" aria-labelledby="titulo-vacio">
              <h2 id="titulo-vacio">Sin análisis en este período</h2>
              <p className="secundario">Cuando realice análisis aparecerán aquí sus indicadores y gráficos.</p>
              <button className="boton" type="button" onClick={alNuevoAnalisis}>Realizar un análisis</button>
            </section>
          ) : (
            <>
              <div className="rejilla rejilla--3">
                <section className="tarjeta" aria-labelledby="titulo-distribucion">
                  <h2 id="titulo-distribucion">Distribución por nivel</h2>
                  <p className="secundario">{datos.total} análisis · {nombrePeriodo}</p>
                  <figure className="figura">
                    <Dona conteos={datos.conteos} titulo="Análisis por nivel de riesgo" />
                    <figcaption className="solo-lector">Número de análisis en cada nivel de riesgo.</figcaption>
                  </figure>
                </section>

                <section className="tarjeta" aria-labelledby="titulo-diarios">
                  <h2 id="titulo-diarios">Análisis por día</h2>
                  <p className="secundario">Apilados por nivel de riesgo</p>
                  <figure className="figura">
                    <BarrasApiladas dias={datos.dias} titulo="Análisis por día y nivel de riesgo" />
                    <figcaption className="solo-lector">Cantidad diaria de análisis según su nivel.</figcaption>
                  </figure>
                </section>

                <section className="tarjeta" aria-labelledby="titulo-embudo">
                  <h2 id="titulo-embudo">Seguimiento de resultados</h2>
                  <p className="secundario">De la predicción a la ejecución real</p>
                  <Embudo
                    pasos={[
                      { etiqueta: "Análisis realizados", valor: datos.total },
                      { etiqueta: "Ejecución real verificada", valor: datos.verificadas.length },
                      { etiqueta: "Resultado evaluable", valor: datos.evaluables.length },
                      { etiqueta: "Despliegue no completado", valor: datos.noCompletados.length },
                    ]}
                  />
                  <p className="secundario nota-pie">
                    Los casos ambiguos o sin intento de despliegue no son evaluables.
                  </p>
                </section>
              </div>

              <div className="rejilla rejilla--2-1">
                <section className="tarjeta" aria-labelledby="titulo-repos">
                  <h2 id="titulo-repos">Repositorios con mayor riesgo</h2>
                  <p className="secundario">Ordenados por probabilidad media del período</p>
                  <div className="tabla-contenedor">
                    <table>
                      <caption className="solo-lector">Repositorios con mayor probabilidad media</caption>
                      <thead>
                        <tr>
                          <th scope="col">Repositorio</th>
                          <th scope="col" className="numero">Análisis</th>
                          <th scope="col" className="numero">Riesgo Alto</th>
                          <th scope="col" className="numero">Prob. media</th>
                          <th scope="col">Nivel medio</th>
                          <th scope="col">Último</th>
                        </tr>
                      </thead>
                      <tbody>
                        {datos.repositorios.map((r) => (
                          <tr key={r.repositorio}>
                            <td>{r.repositorio}</td>
                            <td className="numero">{r.n}</td>
                            <td className="numero">{r.alto}</td>
                            <td className="numero">{porcentaje(r.media)}</td>
                            <td>{limites ? <NivelRiesgo nivel={nivelDe(r.media, limites)} /> : "—"}</td>
                            <td><Fecha valor={r.ultimo} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section className="tarjeta" aria-labelledby="titulo-recientes">
                  <h2 id="titulo-recientes">Análisis recientes</h2>
                  <ul className="feed">
                    {datos.recientes.map((p) => (
                      <li key={p.id} className={`feed__item feed__item--${p.nivel}`}>
                        <div className="feed__texto">
                          <strong>{p.repositorio}</strong>
                          <span className="secundario">
                            {p.workflow_path.replace(".github/workflows/", "")} · <Fecha valor={p.creada_en} />
                          </span>
                        </div>
                        <NivelRiesgo nivel={p.nivel} />
                        <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => setSeleccion(p)}>
                          Ver<span className="solo-lector"> el análisis de {p.repositorio}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              </div>

              <section className="tarjeta" aria-labelledby="titulo-tendencia">
                <h2 id="titulo-tendencia">Tendencia de la probabilidad media</h2>
                <p className="secundario">
                  Probabilidad media diaria de despliegue no completado
                  {activo && `, con los límites de nivel del modelo ${activo.version}`}
                </p>
                <figure className="figura">
                  <Linea dias={datos.dias} limites={limites} titulo="Probabilidad media diaria" />
                  <figcaption className="solo-lector">
                    Evolución diaria de la probabilidad media y umbrales de los niveles Medio y Alto.
                  </figcaption>
                </figure>
              </section>
            </>
          )}
        </>
      )}
    </section>
  );
}
