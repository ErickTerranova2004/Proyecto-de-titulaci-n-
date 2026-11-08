import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { Alerta, NivelRiesgo, porcentaje } from "./comunes.jsx";

// Planificador de despliegue: estima el riesgo del mismo cambio con otras
// condiciones que decide el desarrollador (día, hora, reintento y pull
// request). Día y hora se muestran en hora de Ecuador; el backend los
// convierte a UTC, que es lo que usa el modelo. Estimar no guarda nada.

const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const DIAS_LARGOS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"];
const ZONA = "America/Guayaquil";

const hora = (h) => `${String(h).padStart(2, "0")}:00`;

function fechaCorta(iso) {
  return new Intl.DateTimeFormat("es-EC", { timeZone: ZONA, day: "2-digit", month: "short" }).format(new Date(iso));
}

function puntos(valor) {
  const signo = valor > 0 ? "+" : valor < 0 ? "−" : "±";
  return `${signo}${Math.abs(valor).toFixed(1)} puntos`;
}

function conSigno(valor) {
  return `${valor > 0 ? "+" : valor < 0 ? "−" : ""}${Math.abs(valor).toFixed(3)}`;
}

export default function Planificador() {
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

  const repositorios = useMemo(
    () => [...new Set((analisis || []).map((a) => a.repositorio))].sort(),
    [analisis],
  );
  const workflows = useMemo(
    () => [...new Set((analisis || []).filter((a) => a.repositorio === repositorio).map((a) => a.workflow_path))].sort(),
    [analisis, repositorio],
  );
  const candidatos = useMemo(
    () => (analisis || []).filter((a) => a.repositorio === repositorio && a.workflow_path === workflow),
    [analisis, repositorio, workflow],
  );

  function elegirRepositorio(valor) {
    setRepositorio(valor);
    const lista = [...new Set(analisis.filter((a) => a.repositorio === valor).map((a) => a.workflow_path))].sort();
    elegirWorkflow(valor, lista[0] || "");
  }

  function elegirWorkflow(repo, valor) {
    setWorkflow(valor);
    // El historial viene del más reciente al más antiguo.
    const primero = analisis.find((a) => a.repositorio === repo && a.workflow_path === valor);
    elegirBase(primero ? String(primero.id) : "");
  }

  async function elegirBase(id) {
    setBaseId(id);
    setResultado(null);
    setVentanas(null);
    setCondicionesBase(null);
    setCondiciones(null);
    setBase(analisis?.find((a) => String(a.id) === id) || null);
    if (!id) return;
    setError("");
    try {
      const respuesta = await api.ventanas(id);
      setCondicionesBase(respuesta.condiciones_base);
      setCondiciones(respuesta.condiciones_base);
      setVentanas(respuesta.ventanas);
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
    const valores = { dia: v.dia, hora: v.hora, es_reintento: v.es_reintento, tiene_pr: v.tiene_pr };
    setCondiciones(valores);
    estimar(valores);
  }

  const cambiar = (campo, valor) => setCondiciones((c) => ({ ...c, [campo]: valor }));

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
                {DIAS.map((d, i) => (
                  <button
                    key={d}
                    type="button"
                    className="planificador__dia"
                    aria-pressed={condiciones.dia === i}
                    aria-label={DIAS_LARGOS[i]}
                    onClick={() => cambiar("dia", i)}
                  >
                    {d}
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
                min="0"
                max="23"
                step="1"
                value={condiciones.hora}
                aria-valuetext={hora(condiciones.hora)}
                onChange={(e) => cambiar("hora", Number(e.target.value))}
              />
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
              Solo se muestran las condiciones que usa el modelo {base?.version_modelo}. El resto (commit e historial del
              workflow) se mantiene como en el análisis base.
            </p>
            <div className="planificador__acciones">
              <button className="boton" type="submit" disabled={cargando}>
                {cargando ? "Estimando…" : "Estimar riesgo"}
              </button>
              <button
                className="boton boton--secundario"
                type="button"
                onClick={() => {
                  setCondiciones(condicionesBase);
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

      {ventanas && (
        <div className="tarjeta">
          <h2>Mejores ventanas para los próximos 7 días</h2>
          <p className="secundario">
            Franjas de 07:00 a 20:00 (hora de Ecuador) en los 7 días siguientes al análisis base, con el resto de
            condiciones iguales. Se muestra la de menor riesgo de cada día.
          </p>
          <ol className="planificador__ventanas">
            {ventanas.map((v) => (
              <li key={v.momento_local} className="planificador__ventana">
                <p className="planificador__cuando">
                  <strong>{DIAS_LARGOS[v.dia]}</strong> {fechaCorta(v.momento_local)} · {hora(v.hora)}
                </p>
                <p>
                  {porcentaje(v.probabilidad)} <NivelRiesgo nivel={v.nivel} />
                </p>
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
            {" "}· escenario: {DIAS_LARGOS[resultado.condiciones.dia]} {fechaCorta(escenario.momento_local)},{" "}
            {hora(resultado.condiciones.hora)}
          </span>
        )}
      </p>

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
