import { useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import {
  ajustarHora, avisoVentanas, condicionesIniciales, diasDisponibles, enumerar, fechaGuion, horaMinima, masReciente,
  NOMBRES_DIA, nombreDia, ordenarRepositorios, PRIMERA_HORA, textoPuntos, ULTIMA_HORA, ZONA,
} from "../planificador.js";
import { Alerta, NivelRiesgo, porcentaje, UsuarioContexto } from "./comunes.jsx";

// Planificador de despliegue: estima el riesgo del mismo cambio con otras
// condiciones que decide el desarrollador (fecha, hora, reintento y pull
// request). Fecha y hora se muestran en hora de Ecuador; el backend las
// convierte a UTC, que es lo que usa el modelo, y recalcula para ese momento
// las variables que dependen del tiempo. Estimar no guarda nada.

const DIAS_LARGOS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"];

const hora = (h) => `${String(h).padStart(2, "0")}:00`;

// "AAAA-MM-DD" se toma como día de Ecuador; un ISO con hora, tal cual. Sin
// fecha válida devuelve null (nunca lanza «Invalid time value»).
function aFecha(valor) {
  if (!valor) return null;
  const fecha = /^\d{4}-\d{2}-\d{2}$/.test(valor) ? new Date(`${valor}T12:00:00-05:00`) : new Date(valor);
  return Number.isNaN(fecha.getTime()) ? null : fecha;
}

function fechaCorta(valor) {
  const fecha = aFecha(valor);
  return fecha ? new Intl.DateTimeFormat("es-EC", { timeZone: ZONA, day: "2-digit", month: "short" }).format(fecha) : "";
}

function diaDe(valor) {
  const fecha = aFecha(valor);
  return fecha ? new Intl.DateTimeFormat("es-EC", { timeZone: ZONA, weekday: "long" }).format(fecha) : "";
}

const puntos = textoPuntos;

function conSigno(valor) {
  return `${valor > 0 ? "+" : valor < 0 ? "−" : ""}${Math.abs(valor).toFixed(3)}`;
}

// `inicial`: { id, repositorio, workflow_path } del último «Nuevo análisis»;
// se preselecciona al abrir el Planificador.
export default function Planificador({ inicial }) {
  const usuario = useContext(UsuarioContexto)?.usuario;
  const [analisis, setAnalisis] = useState(null);
  const [repositorio, setRepositorio] = useState("");
  const [workflow, setWorkflow] = useState("");
  const [baseId, setBaseId] = useState("");
  const [base, setBase] = useState(null);
  const [condicionesBase, setCondicionesBase] = useState(null);
  const [condiciones, setCondiciones] = useState(null);
  const [ventanas, setVentanas] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.historial().then(setAnalisis).catch((e) => setError(e.message));
  }, []);

  // Preselección del último análisis (aunque el historial no lo incluya, el
  // backend lo encuentra por su id).
  useEffect(() => {
    if (!analisis || !inicial?.id) return;
    setRepositorio(inicial.repositorio);
    setWorkflow(inicial.workflow_path);
    elegirBase(String(inicial.id));
  }, [analisis]);

  // El último análisis cuenta aunque el historial cargado no lo traiga.
  // (Debe declararse antes de los cálculos que lo usan.)
  const todos = useMemo(
    () => (inicial?.id && analisis && !analisis.some((a) => a.id === inicial.id) ? [inicial, ...analisis] : analisis || []),
    [analisis],
  );
  const repositorios = useMemo(() => {
    const lista = ordenarRepositorios(todos, usuario);
    return inicial?.repositorio && !lista.includes(inicial.repositorio) ? [inicial.repositorio, ...lista] : lista;
  }, [todos, usuario]);
  const workflows = useMemo(
    () => [...new Set(todos.filter((a) => a.repositorio === repositorio).map((a) => a.workflow_path))].sort(),
    [todos, repositorio],
  );
  const candidatos = useMemo(
    () => todos
      .filter((a) => a.repositorio === repositorio && a.workflow_path === workflow)
      .sort((a, b) => (b.creada_en || "").localeCompare(a.creada_en || "")),
    [todos, repositorio, workflow],
  );

  function elegirRepositorio(valor) {
    setRepositorio(valor);
    // El workflow del análisis más reciente de ese repositorio.
    elegirWorkflow(valor, masReciente(todos, valor)?.workflow_path || "");
  }

  function elegirWorkflow(repo, valor) {
    setWorkflow(valor);
    const primero = masReciente(todos, repo, valor);
    elegirBase(primero ? String(primero.id) : "");
  }

  async function elegirBase(id) {
    setBaseId(id);
    setResultado(null);
    setVentanas(null);
    setCondicionesBase(null);
    setCondiciones(null);
    setBase(todos.find((a) => String(a.id) === id) || null);
    if (!id) return;
    setError("");
    try {
      const respuesta = await api.ventanas(id);
      // Un backend sin reiniciar devuelve el formato anterior (sin fechas).
      if (!respuesta.condiciones_base?.fecha || respuesta.ventanas.some((v) => !v.fecha)) {
        throw new Error(
          "El servidor responde con una versión anterior del planificador. Reinicie el backend y recargue la página.",
        );
      }
      setCondicionesBase(respuesta.condiciones_base);
      // Por defecto, hoy a la siguiente hora en punto (no el día del análisis).
      setCondiciones(condicionesIniciales(new Date(), respuesta.condiciones_base));
      setVentanas(respuesta);
    } catch (e) {
      setError(e.message);
    }
  }

  async function estimar(valores = condiciones) {
    setCargando(true);
    setError("");
    try {
      setResultado(await api.estimarEscenario(baseId, valores));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  function usarVentana(v) {
    const valores = { fecha: v.fecha, hora: v.hora, es_reintento: v.es_reintento, tiene_pr: v.tiene_pr };
    setCondiciones(valores);
    estimar(valores);
  }

  const cambiar = (campo, valor) => setCondiciones((c) => ajustarHora({ ...c, [campo]: valor }));
  const dias = diasDisponibles();
  const minima = condiciones ? horaMinima(condiciones.fecha) : 0;

  return (
    <section className="vista planificador" aria-labelledby="titulo-planificador">
      <header className="encabezado">
        <h1 id="titulo-planificador">Planificador de despliegue</h1>
        <p className="secundario">
          Estime cómo cambia el riesgo de un análisis si despliega en otro momento o con otras condiciones.
        </p>
      </header>

      <Alerta>{error}</Alerta>

      <div className="tarjeta formulario">
        <h2>Punto de partida</h2>
        {!analisis && !error && <p className="secundario" role="status">Cargando sus análisis…</p>}
        {analisis && analisis.length === 0 && (
          <p className="secundario">Aún no tiene análisis. Cree uno en «Nuevo análisis» para usarlo como punto de partida.</p>
        )}
        {analisis && analisis.length > 0 && (
          <div className="campos">
            <div className="campo">
              <label htmlFor="plan-repositorio">Repositorio</label>
              <select id="plan-repositorio" value={repositorio} onChange={(e) => elegirRepositorio(e.target.value)}>
                <option value="">Elija un repositorio</option>
                {repositorios.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="campo">
              <label htmlFor="plan-workflow">Workflow</label>
              <select
                id="plan-workflow"
                value={workflow}
                disabled={!repositorio}
                onChange={(e) => elegirWorkflow(repositorio, e.target.value)}
              >
                {workflows.map((w) => <option key={w} value={w}>{w}</option>)}
              </select>
            </div>
            <div className="campo">
              <label htmlFor="plan-base">Análisis base</label>
              <select id="plan-base" value={baseId} disabled={!workflow} onChange={(e) => elegirBase(e.target.value)}>
                {candidatos.map((a) => (
                  <option key={a.id} value={a.id}>
                    #{a.id} · {new Date(a.creada_en).toLocaleString("es-EC", { timeZone: ZONA })} · {a.rama || "sin rama"} ·{" "}
                    {porcentaje(a.probabilidad)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {condiciones && (
        <div className="planificador__rejilla">
          <form
            className="tarjeta"
            onSubmit={(e) => {
              e.preventDefault();
              estimar();
            }}
          >
            <h2>Condiciones del despliegue</h2>
            <fieldset className="planificador__grupo">
              <legend>Día</legend>
              <div className="planificador__dias">
                {dias.map((d) => (
                  <button
                    key={d.fecha}
                    type="button"
                    className="planificador__dia"
                    aria-pressed={condiciones.fecha === d.fecha}
                    aria-label={`${nombreDia(d.fecha)}${d.hoy ? " (hoy)" : ""}`}
                    onClick={() => cambiar("fecha", d.fecha)}
                  >
                    <span>{NOMBRES_DIA[d.dia]}</span>
                    <span className="planificador__fecha-dia">{fechaGuion(d.fecha)}</span>
                    {d.hoy && <span className="planificador__hoy">(hoy)</span>}
                  </button>
                ))}
              </div>
            </fieldset>
            <div className="campo">
              <label htmlFor="plan-hora">
                Hora: <strong>{hora(condiciones.hora)}</strong> <span className="secundario">(hora de Ecuador, UTC−5)</span>
              </label>
              <input
                id="plan-hora"
                type="range"
                min={minima}
                max="23"
                step="1"
                value={condiciones.hora}
                aria-valuetext={hora(condiciones.hora)}
                onChange={(e) => cambiar("hora", Number(e.target.value))}
              />
              {minima > 0 && (
                <p className="secundario nota-pie">Hoy solo se puede planificar a partir de las {hora(minima)}.</p>
              )}
            </div>
            <label className="planificador__casilla">
              <input
                type="checkbox"
                checked={condiciones.es_reintento}
                onChange={(e) => cambiar("es_reintento", e.target.checked)}
              />
              Es un reintento de una ejecución anterior
            </label>
            <label className="planificador__casilla">
              <input
                type="checkbox"
                checked={condiciones.tiene_pr}
                onChange={(e) => cambiar("tiene_pr", e.target.checked)}
              />
              Asociado a un pull request
            </label>
            <p className="secundario">
              Solo se muestran las condiciones que usa el modelo {base?.version_modelo}. Para la fecha y hora elegidas se
              recalculan el día, la hora, los minutos desde el commit y las horas desde la ejecución previa; el resto
              (commit e historial del workflow) se mantiene como en el análisis base
              {condicionesBase && (
                <>
                  {" "}({DIAS_LARGOS[condicionesBase.dia]} {fechaCorta(condicionesBase.fecha)}, {hora(condicionesBase.hora)})
                </>
              )}
              .
            </p>
            <div className="planificador__acciones">
              <button className="boton" type="submit" disabled={cargando}>
                {cargando ? "Estimando…" : "Estimar riesgo"}
              </button>
              <button
                className="boton boton--secundario"
                type="button"
                onClick={() => {
                  setCondiciones(condicionesIniciales(new Date(), condicionesBase || {}));
                  setResultado(null);
                }}
              >
                Restablecer valores
              </button>
            </div>
          </form>

          <Comparacion resultado={resultado} />
        </div>
      )}

      {ventanas && ventanas.ventanas.length > 0 && (
        <div className="tarjeta">
          <h2>Mejores ventanas para los próximos {ventanas.dias} días</h2>
          <p className="secundario">
            A partir de mañana, la hora de menor riesgo de cada uno de los próximos {ventanas.dias} días, entre las{" "}
            {hora(PRIMERA_HORA)} y las {hora(ULTIMA_HORA)} (hora de Ecuador), con el resto de condiciones como en el
            análisis base. «Mejor opción» marca la de menor riesgo.
          </p>
          <AvisoSinMejora ventanas={ventanas} />
          <ol className="planificador__ventanas">
            {ventanas.ventanas.map((v) => (
              <li key={v.momento_local} className={`planificador__ventana${v.mejor ? " planificador__ventana--mejor" : ""}`}>
                {v.mejor && <span className="planificador__mejor">Mejor opción</span>}
                <p className="planificador__cuando">
                  <strong>{NOMBRES_DIA[v.dia]}</strong> {fechaGuion(v.fecha)} · {hora(v.hora)}
                </p>
                <p>
                  {porcentaje(v.probabilidad)} <NivelRiesgo nivel={v.nivel} />
                </p>
                {v.diferencia_puntos !== undefined && (
                  <p
                    className={`planificador__diferencia planificador__cambio--${
                      v.diferencia_puntos > 0 ? "sube" : v.diferencia_puntos < 0 ? "baja" : "igual"
                    }`}
                  >
                    {puntos(v.diferencia_puntos)} <span className="secundario">frente al análisis base</span>
                  </p>
                )}
                <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => usarVentana(v)}>
                  Usar este escenario
                </button>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}

// Si ninguna ventana cambia el nivel del análisis base, elegir otro momento
// no basta: el riesgo viene de otros factores del cambio.
function AvisoSinMejora({ ventanas }) {
  const aviso = avisoVentanas(ventanas.ventanas, ventanas.base);
  if (!aviso) return null;
  const variacion = aviso.variacion.toLocaleString("es-EC", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const factores = (ventanas.factores_base || []).map((f) => f.descripcion.charAt(0).toLowerCase() + f.descripcion.slice(1));
  return (
    <p className="alerta alerta--aviso planificador__aviso" role="status">
      Cambiar el día o la hora apenas modifica el riesgo de este despliegue (variación máxima: {variacion} puntos).
      {factores.length > 0 && <> El riesgo depende sobre todo de: <strong>{enumerar(factores)}</strong>.</>} Se recomienda
      corregir esos factores y volver a analizar antes de elegir una fecha.
    </p>
  );
}

const FILAS_TIEMPO = [
  ["hora_utc", "Hora del despliegue (UTC)", (v) => hora(v)],
  ["dia_semana", "Día de la semana (UTC)", (v) => DIAS_LARGOS[v]],
  ["retraso_commit_run_min", "Minutos entre el commit y el despliegue", (v) => Math.round(v).toLocaleString("es-EC")],
  ["wf_horas_desde_ultimo", "Horas desde la ejecución previa del workflow", (v) => v.toLocaleString("es-EC", { maximumFractionDigits: 1 })],
];

function VariablesTiempo({ tiempo }) {
  if (!tiempo) return null;
  return (
    <table className="tabla planificador__tiempo">
      <caption className="secundario">Variables de tiempo usadas por el modelo</caption>
      <thead>
        <tr>
          <th scope="col">Variable</th>
          <th scope="col">Análisis original</th>
          <th scope="col">Escenario</th>
        </tr>
      </thead>
      <tbody>
        {FILAS_TIEMPO.map(([clave, nombre, formato]) => {
          const fmt = (v) => (v === null || v === undefined ? "Sin dato" : formato(v));
          return (
            <tr key={clave}>
              <th scope="row">{nombre}</th>
              <td className="font-mono">{fmt(tiempo.base[clave])}</td>
              <td className="font-mono">{fmt(tiempo.escenario[clave])}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Comparacion({ resultado }) {
  if (!resultado) {
    return (
      <div className="tarjeta">
        <h2>Comparación del riesgo</h2>
        <p className="secundario">Ajuste las condiciones y pulse «Estimar riesgo» para comparar con el análisis original.</p>
      </div>
    );
  }
  const { base, escenario, diferencia_puntos: diferencia, explicacion } = resultado;
  const maximo = Math.max(base.probabilidad, escenario.probabilidad, 1e-6);
  const filas = [
    { nombre: "Análisis original", ...base },
    { nombre: "Escenario alternativo", ...escenario },
  ];
  const mayorCambio = Math.max(...explicacion.map((e) => Math.abs(e.diferencia)), 1e-6);
  const cambio = diferencia > 0 ? "sube" : diferencia < 0 ? "baja" : "igual";

  return (
    <div className="tarjeta" aria-live="polite">
      <h2>Comparación del riesgo</h2>
      <ul className="planificador__comparacion">
        {filas.map((f) => (
          <li key={f.nombre}>
            <span className="planificador__etiqueta">{f.nombre}</span>
            <span className="planificador__barra" aria-hidden="true">
              <span
                className={`planificador__relleno planificador__relleno--${f.nivel}`}
                style={{ width: `${(f.probabilidad / maximo) * 100}%` }}
              />
            </span>
            <span>
              {porcentaje(f.probabilidad)} <NivelRiesgo nivel={f.nivel} />
            </span>
          </li>
        ))}
      </ul>
      <p className={`planificador__cambio planificador__cambio--${cambio}`}>
        Cambio: <strong>{puntos(diferencia)}</strong>
        {escenario.momento_local && (
          <span className="secundario">
            {" "}· escenario: {diaDe(escenario.momento_local)} {fechaCorta(escenario.momento_local)},{" "}
            {hora(resultado.condiciones.hora)}
          </span>
        )}
      </p>

      <VariablesTiempo tiempo={resultado.variables_tiempo} />

      <h3>Qué explica el cambio</h3>
      {explicacion.length === 0 ? (
        <p className="secundario">Las condiciones son las del análisis original: no hay cambio que explicar.</p>
      ) : (
        <figure className="planificador__explicacion">
          <figcaption className="secundario">
            Diferencia de la contribución de cada variable (valor SHAP del escenario menos el del análisis original).
            Azul: baja el riesgo. Naranja: lo sube. Una variable que no cambió también puede aparecer, porque su
            contribución depende de las que sí cambiaron.
          </figcaption>
          <ul>
            {explicacion.map((e) => {
              const ancho = `${(Math.abs(e.diferencia) / mayorCambio) * 50}%`;
              const sube = e.diferencia > 0;
              return (
                <li key={e.variable} className="divergente">
                  <span className="divergente__nombre">{e.descripcion}</span>
                  <span className="divergente__eje" aria-hidden="true">
                    <span
                      className={`divergente__barra divergente__barra--${sube ? "sube" : "baja"}`}
                      style={sube ? { left: "50%", width: ancho } : { right: "50%", width: ancho }}
                    />
                  </span>
                  <span className={`divergente__valor divergente__valor--${sube ? "sube" : "baja"}`}>
                    {conSigno(e.diferencia)}
                    <span className="solo-lector"> ({sube ? "sube" : "baja"} el riesgo)</span>
                  </span>
                </li>
              );
            })}
          </ul>
        </figure>
      )}
    </div>
  );
}
