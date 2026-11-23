import { useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { opcionesModelo } from "../modeloActivo.js";
import {
  ajustarHora, condicionesIniciales, diasDisponibles, fechaGuion, horaMinima, masReciente,
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

// `analisisId` (de /planificador?analisis=<id>): análisis que se preselecciona,
// también al recargar la página. `inicial`: el mismo análisis si ya se tiene
// (el último «Nuevo análisis»); si no, se pide al backend.
// `modelos`: los seleccionables (Random Forest y XGBoost). Por defecto se usa el
// modelo del análisis base.
export default function Planificador({ inicial: inicialDado, analisisId, modelos = [] }) {
  const usuario = useContext(UsuarioContexto)?.usuario;
  const [inicial, setInicial] = useState(
    inicialDado && inicialDado.repositorio && (!analisisId || inicialDado.id === analisisId) ? inicialDado : null,
  );
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
  // Modelo con el que se estima ("" = el del análisis base).
  const [modeloPlan, setModeloPlan] = useState("");
  const opciones = opcionesModelo(modelos);

  useEffect(() => {
    api.historial().then(setAnalisis).catch((e) => setError(e.message));
  }, []);

  // Solo el id en la dirección: se pide el análisis para preseleccionarlo.
  useEffect(() => {
    if (!analisisId || inicial?.id === analisisId) return;
    api.prediccion(analisisId).then(setInicial).catch(() => setInicial(null));
  }, [analisisId]);

  // Preselección (aunque el historial no lo incluya, el backend lo encuentra
  // por su id).
  useEffect(() => {
    if (!analisis || !inicial?.id) return;
    setRepositorio(inicial.repositorio);
    setWorkflow(inicial.workflow_path);
    elegirBase(String(inicial.id));
  }, [analisis, inicial]);

  // El análisis preseleccionado cuenta aunque el historial no lo traiga.
  // (Debe declararse antes de los cálculos que lo usan.)
  const todos = useMemo(
    () => (inicial?.id && analisis && !analisis.some((a) => a.id === inicial.id) ? [inicial, ...analisis] : analisis || []),
    [analisis, inicial],
  );
  const repositorios = useMemo(() => {
    const lista = ordenarRepositorios(todos, usuario);
    return inicial?.repositorio && !lista.includes(inicial.repositorio) ? [inicial.repositorio, ...lista] : lista;
  }, [todos, usuario, inicial]);
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
    setModeloPlan("");
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
      setResultado(await api.estimarEscenario(baseId, valores, modeloPlan));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  async function cambiarModelo(valor) {
    setModeloPlan(valor === base?.version_modelo ? "" : valor);
    setResultado(null);
    setError("");
    try {
      setVentanas(await api.ventanas(baseId, undefined, valor));
    } catch (e) {
      setError(e.message);
    }
  }

  function usarVentana(v) {
    const valores = { fecha: v.fecha, hora: v.hora, es_reintento: v.es_reintento, tiene_pr: v.tiene_pr };
    setCondiciones(valores);
    estimar(valores);
  }

  const modeloEstimacion = modeloPlan || base?.version_modelo || "";
  const nombreModelo = modelos.find((m) => m.version === modeloEstimacion)?.nombre_modelo ?? modeloEstimacion;
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
            {opciones.length > 1 && (
            <div className="campo planificador__modelo">
              <label htmlFor="plan-modelo">Modelo</label>
              <select
                id="plan-modelo"
                value={modeloEstimacion}
                disabled={!base}
                onChange={(e) => cambiarModelo(e.target.value)}
              >
                {!opciones.some((o) => o.valor === modeloEstimacion) && modeloEstimacion && (
                  <option value={modeloEstimacion}>{modeloEstimacion}</option>
                )}
                {opciones.map((o) => <option key={o.valor} value={o.valor}>{o.texto}</option>)}
              </select>
            </div>
            )}
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
              Solo se muestran las condiciones que usa el modelo {nombreModelo}. Para la fecha y hora elegidas se
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

const FILAS_TIEMPO = [
  ["hora_utc", "Hora del despliegue (UTC)", (v) => hora(v)],
  ["dia_semana", "Día de la semana (UTC)", (v) => DIAS_LARGOS[v]],
  ["retraso_commit_run_min", "Minutos entre el commit y el despliegue", (v) => Math.round(v).toLocaleString("es-EC")],
  ["wf_horas_desde_ultimo", "Horas desde la ejecución previa del workflow", (v) => v.toLocaleString("es-EC", { maximumFractionDigits: 1 })],
];

export function VariablesTiempo({ tiempo }) {
  if (!tiempo) return null;
  return (
    <>
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
    <p className="secundario nota-pie planificador__nota-utc">
      El modelo usa la hora UTC; por ejemplo, 20:00 en Ecuador corresponde a la 01:00 UTC del día siguiente.
    </p>
    </>
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
