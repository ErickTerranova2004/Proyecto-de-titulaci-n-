import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { cargarTarjetas } from "../cargaAdmin.js";
import { MisAsignaciones } from "./Alarma.jsx";
import { Alerta, Fecha, NIVELES, NivelRiesgo, porcentaje } from "./comunes.jsx";
import { BarrasApiladas, Dona, Embudo, Linea } from "./graficos.jsx";
import Resultado, { ETIQUETAS } from "./Resultado.jsx";

// Dashboard principal con el mismo diseño para los tres perfiles: flujo de la
// plataforma, distribución por nivel, análisis por día, seguimiento de
// resultados y tendencia, calculados con los análisis que ve cada rol. Además,
// cada perfil añade sus bloques:
// - Desarrollador: Mis asignaciones, Mis repositorios y Mis análisis recientes.
// - Líder técnico: riesgo alto por repositorio, predicciones sin decisión y
//   análisis por desarrollador.
// - Administrador: usuarios por rol, workflows, estado de GitHub, modelo activo
//   y supervisión, repositorios con mayor riesgo y análisis recientes.
// Todo se calcula a partir de la API (GET /api/predicciones/, ya filtrado por
// rol, y /api/repositorios/?todos=1; el administrador usa /api/resumen-admin/,
// /api/integraciones/ y la supervisión del modelo). No hay valores fijos.

const PERIODOS = [
  ["7", "Últimos 7 días"],
  ["30", "Últimos 30 días"],
  ["90", "Últimos 90 días"],
  ["todo", "Todo el historial"],
];
const DIA = 24 * 60 * 60 * 1000;

const PERFILES = {
  desarrollador: { titulo: "Mi panel", alcance: "Sus análisis, sus repositorios y sus resultados verificados" },
  lider: { titulo: "Panel del equipo", alcance: "Análisis de los desarrolladores de sus repositorios asignados" },
  administrador: { titulo: "Panel de administración", alcance: "Todos los análisis, usuarios, workflows, modelo y GitHub" },
};

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

// Agrupa las predicciones por un campo (repositorio o usuario).
function agrupar(predicciones, campo) {
  const grupos = {};
  predicciones.forEach((p) => {
    const g = (grupos[p[campo]] ||= { nombre: p[campo], n: 0, suma: 0, alto: 0, sinDecision: 0, ultimo: p.creada_en });
    g.n += 1;
    g.suma += p.probabilidad;
    if (p.nivel === "alto") g.alto += 1;
    if (!p.decisiones?.length) g.sinDecision += 1;
    if (p.creada_en > g.ultimo) g.ultimo = p.creada_en;
  });
  return Object.values(grupos).map((g) => ({ ...g, media: g.suma / g.n }));
}

function Icono({ tipo }) {
  const trazos = {
    analisis: "M3 3v18h18M7 16l4-4 4 4 5-6",
    alto: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z",
    probabilidad: "M10.5 6a7.5 7.5 0 1 0 7.5 7.5h-7.5V6z",
    verificado: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
    modelo: "M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9",
    pendiente: "M12 7v5l3 3M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z",
    usuarios: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
    repositorio: "M3 7h18M3 12h18M3 17h18",
    enlace: "M9 7H6a5 5 0 0 0 0 10h3M15 7h3a5 5 0 0 1 0 10h-3M8 12h8",
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
      <div className="kpi__cabecera">
        <h3 className="kpi__titulo">{titulo}</h3>
        <Icono tipo={icono} />
      </div>
      <div>
        <p className="kpi__valor">{valor}</p>
        {detalle && <p className="kpi__detalle secundario">{detalle}</p>}
      </div>
    </article>
  );
}

// Tarjetas del administrador. Cada una carga por separado (cargaAdmin.js):
// undefined = cargando; { estado: "ok" | "vacio" | "error", datos, motivo }.
function useDatosAdmin(activo, habilitado) {
  const [tarjetas, setTarjetas] = useState({});
  const cargar = () => {
    if (!habilitado) return;
    setTarjetas({});
    const peticiones = {
      resumen: () => api.resumenAdmin(),
      github: () => api.integraciones().then((r) => r.github),
    };
    if (activo) peticiones.supervision = () => api.supervision(activo.id);
    cargarTarjetas(peticiones, {
      resumen: (r) => (r.usuarios.total === 0 ? "Todavía no hay usuarios registrados." : null),
      supervision: (s) => (s.predicciones === 0 ? "El modelo activo aún no tiene predicciones." : null),
    }).then(setTarjetas);
  };
  useEffect(cargar, [habilitado, activo?.id]);
  return { tarjetas, cargar };
}

// Estado de una tarjeta que no tiene datos: cargando, vacío o error concreto.
function EstadoTarjeta({ tarjeta }) {
  if (tarjeta === undefined) return <p role="status" className="secundario">Cargando…</p>;
  if (tarjeta.estado === "error") return <Alerta>{tarjeta.motivo}</Alerta>;
  if (tarjeta.estado === "vacio") return <p className="secundario">{tarjeta.motivo}</p>;
  return null;
}

// Sin un perfil válido no se dibuja nada: nunca se cae al panel de administración.
export default function Panel(props) {
  if (!PERFILES[props.perfil]) return null;
  return <PanelDePerfil {...props} />;
}

function PanelDePerfil({ perfil, modelos, alNuevoAnalisis, alActualizar, alarma, alAtender }) {
  const textos = PERFILES[perfil];
  const esAdmin = perfil === "administrador";
  const [historial, setHistorial] = useState(null);
  const [repos, setRepos] = useState([]);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const [periodo, setPeriodo] = useState("30");
  const [cargadoEn, setCargadoEn] = useState(null);
  const [seleccion, setSeleccion] = useState(null);

  const activo = modelos.find((m) => m.activo);
  const limites = activo?.metadatos?.limites_riesgo;
  const admin = useDatosAdmin(activo, esAdmin);

  function cargar() {
    setError("");
    setCargando(true);
    Promise.all([api.historial(), api.repositoriosAsignados()])
      .then(([h, r]) => {
        setHistorial(h);
        setRepos(r);
        setCargadoEn(new Date().toISOString());
      })
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }
  useEffect(cargar, []);

  // También recarga los modelos por si un administrador cambió el activo.
  function actualizar() {
    alActualizar();
    cargar();
    admin.cargar();
    alarma?.recargar();
  }

  const datos = useMemo(() => {
    if (!historial) return null;
    const ahora = Date.now();
    const fechas = historial.map((p) => new Date(p.creada_en).getTime());
    const desde = periodo === "todo" ? Math.min(ahora, ...fechas) : ahora - Number(periodo) * DIA;
    const enPeriodo = historial.filter((p) => new Date(p.creada_en).getTime() >= desde);
    const anterior = periodo === "todo"
      ? null
      : historial.filter((p) => {
          const t = new Date(p.creada_en).getTime();
          return t < desde && t >= desde - Number(periodo) * DIA;
        }).length;

    const total = enPeriodo.length;
    const conteos = { bajo: 0, medio: 0, alto: 0 };
    enPeriodo.forEach((p) => { conteos[p.nivel] += 1; });
    const alto = conteos.alto;
    const probMedia = total ? enPeriodo.reduce((s, p) => s + p.probabilidad, 0) / total : null;
    const verificadas = enPeriodo.filter((p) => p.ejecucion_real);
    const evaluables = verificadas.filter((p) => p.ejecucion_real.y !== null && p.ejecucion_real.y !== undefined);
    const noCompletados = evaluables.filter((p) => p.ejecucion_real.y === 1);
    const ordenarRecientes = (lista) => [...lista].sort((a, b) => (a.creada_en < b.creada_en ? 1 : -1));
    const sinDecision = ordenarRecientes(enPeriodo.filter((p) => !p.decisiones?.length && p.nivel !== "bajo"));

    // Repositorios: el administrador ve los de mayor riesgo; el líder y el
    // desarrollador, sus repositorios asignados aunque no tengan análisis.
    const porRepo = Object.fromEntries(agrupar(enPeriodo, "repositorio").map((r) => [r.nombre, r]));
    let repositorios;
    if (esAdmin) {
      repositorios = Object.values(porRepo).sort((a, b) => b.media - a.media).slice(0, 8);
    } else {
      repositorios = repos.map((r) => ({
        nombre: r.nombre_completo, validados: r.workflows_validados, n: 0, alto: 0, media: null, ultimo: null,
        ...porRepo[r.nombre_completo],
      }));
      repositorios.sort(perfil === "lider"
        ? (a, b) => b.alto - a.alto || (b.media ?? -1) - (a.media ?? -1)
        : (a, b) => b.n - a.n || a.nombre.localeCompare(b.nombre));
    }

    return {
      total, anterior, conteos, alto, probMedia, verificadas, evaluables, noCompletados, repositorios, sinDecision,
      desarrolladores: agrupar(enPeriodo, "usuario").sort((a, b) => b.n - a.n),
      dias: serieDiaria(enPeriodo, desde, ahora),
      recientes: ordenarRecientes(enPeriodo).slice(0, 6),
    };
  }, [historial, repos, periodo, perfil]);

  const nombrePeriodo = PERIODOS.find(([id]) => id === periodo)[1].toLowerCase();
  const workflowsValidados = repos.reduce((s, r) => s + r.workflows.length, 0);
  const nVariables = activo
    ? activo.metadatos.variables_categoricas.length + activo.metadatos.variables_numericas.length
    : null;

  // Bloques comunes del dashboard (los mismos del resumen anterior).
  const flujo = datos && (
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
  );
  const graficos = datos && (
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
        <h2 id="titulo-embudo">{perfil === "desarrollador" ? "Mis resultados verificados" : "Seguimiento de resultados"}</h2>
        <p className="secundario">De la predicción a la ejecución real</p>
        <Embudo
          pasos={[
            { etiqueta: "Análisis realizados", valor: datos.total },
            { etiqueta: "Ejecución real verificada", valor: datos.verificadas.length },
            { etiqueta: "Resultado evaluable", valor: datos.evaluables.length },
            { etiqueta: "Despliegue no completado", valor: datos.noCompletados.length },
          ]}
        />
        <p className="secundario nota-pie">Los casos ambiguos o sin intento de despliegue no son evaluables.</p>
      </section>
    </div>
  );
  const tendencia = datos && (
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
  );

  function verAnalisis(id) {
    const p = historial?.find((x) => x.id === id);
    if (p) setSeleccion(p);
  }

  if (seleccion) {
    return (
      <section className="vista" aria-labelledby="titulo-panel">
        <h1 id="titulo-panel">{textos.titulo}</h1>
        <div>
          <button className="boton boton--secundario" type="button" onClick={() => { setSeleccion(null); cargar(); alarma?.recargar(); }}>
            ← Volver al panel
          </button>
        </div>
        <Resultado prediccion={seleccion} modelos={modelos} />
      </section>
    );
  }

  return (
    <section className="vista" aria-labelledby="titulo-panel">
      <div className="panel__cabecera">
        <div>
          <h1 id="titulo-panel">{textos.titulo}</h1>
          <p className="secundario">
            {textos.alcance} · {nombrePeriodo}
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
          <button className="boton boton--secundario" type="button" onClick={actualizar} disabled={cargando}>
            {cargando ? "Actualizando…" : "Actualizar"}
          </button>
          {alNuevoAnalisis && (
            <button className="boton" type="button" onClick={alNuevoAnalisis}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
              Nuevo análisis
            </button>
          )}
        </div>
      </div>

      <Alerta>{error}</Alerta>

      {!datos && !error && <p role="status" className="secundario">Cargando datos del panel…</p>}

      {esAdmin && datos && (
        <>
          <PanelAdministrador admin={admin} activo={activo} antesDeBloques={flujo} />
          {graficos}
          <div className="rejilla rejilla--2-1">
            <TablaRepositorios perfil={perfil} filas={datos.repositorios} limites={limites} />
            <ListaAnalisis
              id="titulo-recientes"
              titulo="Análisis recientes"
              filas={datos.recientes}
              vacio="Sin análisis en el período."
              detalle={(p) => ` · ${p.usuario}`}
              accion="Ver"
              alSeleccionar={setSeleccion}
            />
          </div>
          {tendencia}
        </>
      )}

      {perfil === "desarrollador" && datos && (
        <>
          <section aria-labelledby="titulo-kpi">
            <h2 id="titulo-kpi" className="solo-lector">Mis indicadores del período</h2>
            <div className="kpis">
              <Kpi
                icono="analisis"
                titulo="Mis análisis"
                valor={datos.total}
                detalle={datos.anterior === null ? "Todo el historial" : `${datos.anterior} en el período anterior`}
              />
              <Kpi
                icono="alto"
                titulo="Riesgo Alto"
                valor={datos.alto}
                nivel="alto"
                detalle={datos.total ? `${porcentaje(datos.alto / datos.total)} de mis análisis` : "Sin análisis"}
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
              <Kpi icono="repositorio" titulo="Mis repositorios" valor={repos.length} detalle="Repositorios asignados" />
            </div>
          </section>

          {alarma && <MisAsignaciones alarma={alarma} alAtender={alAtender} alVerAnalisis={verAnalisis} />}
          {flujo}
          {graficos}

          <div className="rejilla rejilla--2-1">
            <TablaRepositorios perfil={perfil} filas={datos.repositorios} limites={limites} />
            <ListaAnalisis
              id="titulo-recientes"
              titulo="Mis análisis recientes"
              filas={datos.recientes}
              vacio="Sin análisis en el período."
              detalle={(p) => ` · ${p.ejecucion_real ? ETIQUETAS[p.ejecucion_real.etiqueta] || p.ejecucion_real.etiqueta : "resultado pendiente"}`}
              accion="Ver"
              alSeleccionar={setSeleccion}
            />
          </div>

          {tendencia}
        </>
      )}

      {perfil === "lider" && datos && (
        <>
          <section aria-labelledby="titulo-kpi">
            <h2 id="titulo-kpi" className="solo-lector">Indicadores del equipo</h2>
            <div className="kpis">
              <Kpi
                icono="analisis"
                titulo="Análisis del equipo"
                valor={datos.total}
                detalle={datos.anterior === null ? "Todo el historial" : `${datos.anterior} en el período anterior`}
              />
              <Kpi
                icono="alto"
                titulo="Riesgo Alto"
                valor={datos.alto}
                nivel="alto"
                detalle={datos.total ? `${porcentaje(datos.alto / datos.total)} de los análisis` : "Sin análisis"}
              />
              <Kpi icono="repositorio" titulo="Repositorios asignados" valor={repos.length} detalle={`${datos.repositorios.filter((r) => r.alto).length} con riesgo Alto`} />
              <Kpi icono="usuarios" titulo="Desarrolladores" valor={datos.desarrolladores.length} detalle="Con análisis en el período" />
              <Kpi icono="pendiente" titulo="Sin decisión" valor={datos.sinDecision.length} detalle="Nivel medio o alto" />
            </div>
          </section>
          {flujo}
          {graficos}

          <div className="rejilla rejilla--2-1">
            <TablaRepositorios perfil={perfil} filas={datos.repositorios} limites={limites} />
            <ListaAnalisis
              id="titulo-sin-decision"
              titulo="Predicciones sin decisión"
              filas={datos.sinDecision.slice(0, 6)}
              vacio="No hay predicciones de nivel medio o alto sin decisión."
              detalle={(p) => ` · ${p.usuario}`}
              accion="Decidir"
              alSeleccionar={setSeleccion}
            />
          </div>

          <section className="tarjeta" aria-labelledby="titulo-desarrolladores">
            <h2 id="titulo-desarrolladores">Análisis por desarrollador</h2>
            <p className="secundario">Desarrolladores de sus repositorios asignados · {nombrePeriodo}</p>
            {!datos.desarrolladores.length ? (
              <p className="secundario">Sin análisis del equipo en el período.</p>
            ) : (
              <div className="tabla-contenedor">
                <table>
                  <caption className="solo-lector">Análisis por desarrollador</caption>
                  <thead>
                    <tr>
                      <th scope="col">Desarrollador</th>
                      <th scope="col" className="numero">Análisis</th>
                      <th scope="col" className="numero">Riesgo Alto</th>
                      <th scope="col" className="numero">Prob. media</th>
                      <th scope="col" className="numero">Sin decisión</th>
                      <th scope="col">Último</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datos.desarrolladores.map((d) => (
                      <tr key={d.nombre}>
                        <td>{d.nombre}</td>
                        <td className="numero">{d.n}</td>
                        <td className="numero">{d.alto}</td>
                        <td className="numero">{porcentaje(d.media)}</td>
                        <td className="numero">{d.sinDecision}</td>
                        <td><Fecha valor={d.ultimo} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
          {tendencia}
        </>
      )}
    </section>
  );
}

// Lista de análisis con el estilo de "Análisis recientes".
function ListaAnalisis({ id, titulo, filas, vacio, detalle, accion, alSeleccionar }) {
  return (
    <section className="tarjeta" aria-labelledby={id}>
      <h2 id={id}>{titulo}</h2>
      {!filas.length && <p className="secundario">{vacio}</p>}
      <ul className="feed">
        {filas.map((p) => (
          <li key={p.id} className={`feed__item feed__item--${p.nivel}`}>
            <div className="feed__texto">
              <strong>{p.repositorio}</strong>
              <span className="secundario">
                {p.workflow_path.replace(".github/workflows/", "")} · <Fecha valor={p.creada_en} />
                {detalle(p)}
              </span>
            </div>
            <NivelRiesgo nivel={p.nivel} />
            <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => alSeleccionar(p)}>
              {accion}<span className="solo-lector"> el análisis de {p.repositorio}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

// Mis repositorios (desarrollador) o riesgo alto por repositorio (líder).
function TablaRepositorios({ perfil, filas, limites }) {
  const [titulo, descripcion] = {
    administrador: ["Repositorios con mayor riesgo", "Ordenados por probabilidad media del período"],
    lider: ["Riesgo alto por repositorio", "Repositorios asignados, ordenados por análisis de riesgo Alto"],
    desarrollador: ["Mis repositorios", "Repositorios asignados y sus análisis del período"],
  }[perfil];
  const asignados = perfil !== "administrador";
  return (
    <section className="tarjeta" aria-labelledby="titulo-repos">
      <h2 id="titulo-repos">{titulo}</h2>
      <p className="secundario">{descripcion}</p>
      {!filas.length ? (
        <p className="secundario">
          {asignados ? "No tiene repositorios asignados. Solicite acceso al administrador." : "Sin análisis en el período."}
        </p>
      ) : (
        <div className="tabla-contenedor">
          <table>
            <caption className="solo-lector">{titulo}</caption>
            <thead>
              <tr>
                <th scope="col">Repositorio</th>
                {asignados && <th scope="col" className="numero">Workflows validados</th>}
                <th scope="col" className="numero">Análisis</th>
                <th scope="col" className="numero">Riesgo Alto</th>
                <th scope="col" className="numero">Prob. media</th>
                <th scope="col">Nivel medio</th>
                <th scope="col">Último</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((r) => (
                <tr key={r.nombre}>
                  <td>{r.nombre}</td>
                  {asignados && <td className="numero">{r.validados}</td>}
                  <td className="numero">{r.n}</td>
                  <td className="numero">{r.alto}</td>
                  <td className="numero">{r.media === null ? "—" : porcentaje(r.media)}</td>
                  <td>{limites && r.media !== null ? <NivelRiesgo nivel={nivelDe(r.media, limites)} /> : "—"}</td>
                  <td><Fecha valor={r.ultimo} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

// Panel del administrador: usuarios por rol, workflows, modelo activo y
// supervisión, y estado de GitHub. Si un endpoint no responde, el bloque lo
// indica en lugar de mostrar cifras.
function PanelAdministrador({ admin, activo, antesDeBloques }) {
  const { tarjetas } = admin;
  const datosDe = (clave) => (tarjetas[clave]?.estado === "ok" ? tarjetas[clave].datos : null);
  const resumen = datosDe("resumen");
  const github = datosDe("github");
  const supervision = datosDe("supervision");
  const tasa = (n) => (n.tasa == null ? "—" : `${porcentaje(n.tasa)} (${n.no_completados}/${n.evaluables})`);
  return (
    <>
      <section aria-labelledby="titulo-kpi">
        <h2 id="titulo-kpi" className="solo-lector">Indicadores de la plataforma</h2>
        <div className="kpis">
          <Kpi icono="usuarios" titulo="Usuarios" valor={resumen ? resumen.usuarios.total : "—"} detalle={resumen ? `${resumen.usuarios.sin_rol} sin rol` : "Sin datos"} />
          <Kpi icono="verificado" titulo="Workflows validados" valor={resumen ? resumen.workflows.validados : "—"} detalle={resumen ? `${resumen.workflows.validados_disponibles_github} disponibles en GitHub` : "Sin datos"} />
          <Kpi icono="pendiente" titulo="Workflows sin validar" valor={resumen ? resumen.workflows.sin_validar : "—"} detalle="Pendientes de validación" />
          <Kpi
            icono="modelo"
            titulo="Modelo activo"
            valor={activo ? activo.version : "—"}
            detalle={activo
              ? `${activo.nombre_modelo} · PR-AUC ${activo.metadatos.metricas_prueba["PR-AUC"].toFixed(3)}`
              : "No hay un modelo activo"}
          />
          <Kpi
            icono="enlace"
            titulo="GitHub"
            valor={!github ? "—" : github.error ? "Sin conexión" : github.token_configurado ? "Con token" : "Sin token"}
            nivel={github && (github.error || !github.token_configurado) ? "alto" : undefined}
            detalle={github?.limite != null ? `${github.restantes} de ${github.limite} solicitudes disponibles` : "Cuota no disponible"}
          />
        </div>
      </section>

      {antesDeBloques}

      <div className="rejilla rejilla--3">
        <section className="tarjeta" aria-labelledby="titulo-usuarios-rol">
          <h2 id="titulo-usuarios-rol">Usuarios por rol</h2>
          <p className="secundario">Cada usuario cuenta una vez, en su rol de mayor jerarquía</p>
          <EstadoTarjeta tarjeta={tarjetas.resumen} />
          {resumen && (
            <ul className="leyenda">
              <li><span>Administradores</span><span className="leyenda__valor">{resumen.usuarios.administrador}</span></li>
              <li><span>Líderes técnicos</span><span className="leyenda__valor">{resumen.usuarios.lider_tecnico}</span></li>
              <li><span>Desarrolladores</span><span className="leyenda__valor">{resumen.usuarios.desarrollador}</span></li>
              <li><span>Sin rol</span><span className="leyenda__valor">{resumen.usuarios.sin_rol}</span></li>
              <li><strong>Total</strong><span className="leyenda__valor">{resumen.usuarios.total}</span></li>
            </ul>
          )}
        </section>

        <section className="tarjeta" aria-labelledby="titulo-workflows-admin">
          <h2 id="titulo-workflows-admin">Workflows</h2>
          <p className="secundario">Validados como despliegue o pendientes de validar</p>
          <EstadoTarjeta tarjeta={tarjetas.resumen} />
          {resumen && (
            <ul className="leyenda">
              <li><span>Validados</span><span className="leyenda__valor">{resumen.workflows.validados}</span></li>
              <li><span>Validados y disponibles en GitHub</span><span className="leyenda__valor">{resumen.workflows.validados_disponibles_github}</span></li>
              <li><span>Sin validar</span><span className="leyenda__valor">{resumen.workflows.sin_validar}</span></li>
              <li><strong>Total</strong><span className="leyenda__valor">{resumen.workflows.total}</span></li>
            </ul>
          )}
        </section>

        <section className="tarjeta" aria-labelledby="titulo-github-admin">
          <h2 id="titulo-github-admin">Estado de GitHub</h2>
          <p className="secundario">Conexión de la integración</p>
          <EstadoTarjeta tarjeta={tarjetas.github} />
          {github && (
            <ul className="leyenda">
              <li><span>Token</span><span className="leyenda__valor">{github.token_configurado ? "Configurado" : "No configurado"}</span></li>
              <li><span>Cuota disponible</span><span className="leyenda__valor">{github.limite != null ? `${github.restantes} / ${github.limite}` : "—"}</span></li>
              <li><span>Repositorios registrados</span><span className="leyenda__valor">{github.repositorios_registrados}</span></li>
              <li><span>Ejecuciones almacenadas</span><span className="leyenda__valor">{github.ejecuciones_almacenadas}</span></li>
              <li><span>Última extracción</span><span className="leyenda__valor"><Fecha valor={github.ultima_extraccion} /></span></li>
            </ul>
          )}
          {github?.error && <Alerta>{github.error}</Alerta>}
        </section>
      </div>

      <section className="tarjeta" aria-labelledby="titulo-supervision-panel">
        <h2 id="titulo-supervision-panel">Modelo activo y supervisión</h2>
        <p className="secundario">
          {activo ? `${activo.version} · ${activo.nombre_modelo}. ` : ""}
          Tasa observada de despliegues no completados por nivel, en las predicciones verificadas
        </p>
        {!activo && <p className="secundario">No hay un modelo activo registrado.</p>}
        {activo && <EstadoTarjeta tarjeta={tarjetas.supervision} />}
        {supervision && (
          <div className="tabla-contenedor">
            <table>
              <caption className="solo-lector">Supervisión del modelo {supervision.version}</caption>
              <thead>
                <tr>
                  <th scope="col">Versión</th>
                  <th scope="col" className="numero">Predicciones</th>
                  <th scope="col" className="numero">Verificadas</th>
                  <th scope="col" className="numero">Evaluables</th>
                  {Object.values(NIVELES).map((n) => <th key={n} scope="col" className="numero">Nivel {n}</th>)}
                  <th scope="col" className="numero">Brier</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{supervision.version}</td>
                  <td className="numero">{supervision.predicciones}</td>
                  <td className="numero">{supervision.verificadas}</td>
                  <td className="numero">{supervision.evaluables}</td>
                  {Object.keys(NIVELES).map((n) => <td key={n} className="numero">{tasa(supervision.por_nivel[n])}</td>)}
                  <td className="numero">{supervision.brier == null ? "—" : supervision.brier.toFixed(3)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
        {supervision?.predicciones_demostracion > 0 && (
          <p className="secundario nota-pie">
            Incluye {supervision.predicciones_demostracion} predicciones de repositorios de demostración (no son validación del modelo).
          </p>
        )}
        {supervision && supervision.evaluables === 0 && (
          <p className="secundario nota-pie">Aún no hay resultados evaluables: la tasa observada no es concluyente.</p>
        )}
      </section>
    </>
  );
}
