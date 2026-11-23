import { useEffect, useRef, useState } from "react";
import { etiquetaModelo } from "../modeloActivo.js";
import { api } from "../api.js";
import {
  Alerta, DECISIONES, EstadoAsignacion, Fecha, FechaDia, hoyLocal, NIVELES, NivelRiesgo, porcentaje, useRoles,
} from "./comunes.jsx";
import { aceptaRecomendacion, decisionRecomendada, RECOMENDACIONES } from "../recomendacion.js";
import { INTERVALO_SEGUIMIENTO, siguientePaso } from "../seguimiento.js";

// Textos de presentación para los códigos de EjecucionWorkflow.etiqueta y
// EjecucionWorkflow.subtipo_etiqueta (los códigos vienen de la API).
const ETIQUETAS = {
  despliegue_completado: "Despliegue completado",
  despliegue_no_completado: "Despliegue no completado",
  excluida_sin_intento: "Sin intento de despliegue (no evaluable)",
  excluida_ambigua: "Ambigua: falló otro job con el despliegue completado (no evaluable)",
  excluida_otro_resultado: "Cancelada u omitida (no evaluable)",
  excluida_sin_jobs: "El workflow no llegó a arrancar (no evaluable)",
  excluida_no_produccion: "Despliegue a un entorno no productivo (no evaluable)",
};
const SUBTIPOS = {
  antes_del_despliegue: "Falló antes de llegar al despliegue",
  en_paso_de_despliegue: "Falló en el paso de despliegue",
  posterior_mismo_job: "Falló en un paso posterior del mismo job",
};

export { ETIQUETAS };

function contribucion(valor) {
  return `${valor > 0 ? "+" : ""}${valor.toFixed(3)}`;
}

function Factores({ factores }) {
  const maximo = Math.max(...factores.map((f) => Math.abs(f.contribucion)), 1e-6);
  return (
    <figure className="factores">
      <figcaption className="secundario">
        Rojo: el factor sube el riesgo. Verde: el factor baja el riesgo. La longitud de cada barra es proporcional a su
        contribución (valor SHAP, en puntos de probabilidad) en esta predicción.
      </figcaption>
      <ul>
        {factores.map((f) => (
          <li key={f.variable} className="factor">
            <span className="factor__nombre">{f.descripcion}</span>
            <span className="factor__valor secundario">Valor: {String(f.valor)}</span>
            <span className="factor__barra" aria-hidden="true">
              <span
                className={`factor__relleno factor__relleno--${f.efecto}`}
                style={{ width: `${(Math.abs(f.contribucion) / maximo) * 100}%` }}
              />
            </span>
            <span className={`factor__efecto factor__efecto--${f.efecto}`}>
              <span aria-hidden="true">{f.efecto === "aumenta" ? "▲ " : "▼ "}</span>
              {f.efecto === "aumenta" ? "Sube" : "Baja"} {contribucion(f.contribucion)}
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

// Seguimiento automático (src/seguimiento.js): empieza al abrir el análisis y,
// mientras la verificación quede pendiente, vuelve a consultar GitHub cada
// INTERVALO_SEGUIMIENTO, como máximo DURACION_SEGUIMIENTO. Si la página se
// cierra, la tarea programada del lote enlaza el resultado (cada 4 h).
function ResultadoReal({ prediccion, alActualizar }) {
  const temporizador = useRef(null);
  const inicio = useRef(0);
  const real = prediccion.ejecucion_real;

  function detener() {
    clearTimeout(temporizador.current);
    temporizador.current = null;
  }

  async function consultar() {
    try {
      const respuesta = await api.verificar(prediccion.id);
      const paso = siguientePaso(respuesta, Date.now() - inicio.current);
      if (paso === "enlazado") {
        detener();
        alActualizar(respuesta);
        return;
      }
      if (paso === "detener") {
        detener();
        return;
      }
      temporizador.current = setTimeout(consultar, INTERVALO_SEGUIMIENTO);
    } catch {
      detener();
    }
  }

  // El seguimiento empieza solo al abrir un análisis sin resultado real.
  useEffect(() => {
    if (real) return undefined;
    inicio.current = Date.now();
    consultar();
    return () => clearTimeout(temporizador.current);
  }, [prediccion.id]);

  // Sin resultado real el apartado no se muestra: el seguimiento sigue en
  // segundo plano y, al enlazarse la ejecución, aparece con sus datos.
  if (!real) return null;
  return (
    <section aria-labelledby={`real-${prediccion.id}`}>
      <h3 id={`real-${prediccion.id}`}>Resultado real</h3>
      <DatosEjecucion real={real} className="datos recuadro" />
    </section>
  );
}

function DatosEjecucion({ real, className }) {
  return (
    <dl className={className}>
      <dt>Etiqueta</dt>
      <dd>{ETIQUETAS[real.etiqueta] || real.etiqueta}</dd>
      {real.subtipo_etiqueta && (
        <>
          <dt>Detalle</dt>
          <dd>{SUBTIPOS[real.subtipo_etiqueta] || real.subtipo_etiqueta}</dd>
        </>
      )}
      <dt>Ejecución</dt>
      <dd>
        {real.run_id} (intento {real.run_attempt}), iniciada <Fecha valor={real.iniciada_en} />
      </dd>
      <dt>Conclusión en GitHub</dt>
      <dd>{real.conclusion}</dd>
      {real.paso_fallido && (
        <>
          <dt>Paso fallido</dt>
          <dd>{real.paso_fallido}</dd>
        </>
      )}
    </dl>
  );
}

// Seguimiento de la asignación por el desarrollador (solo la última decisión).
function Seguimiento({ decision }) {
  if (!decision.fecha_limite) return null;
  return (
    <p>
      Fecha límite para el desarrollador: <FechaDia valor={decision.fecha_limite} />{" "}
      <EstadoAsignacion estado={decision.estado} /> ·{" "}
      {decision.vista_por_desarrollador_en ? <>vista el <Fecha valor={decision.vista_por_desarrollador_en} /></> : "aún no vista"}
      {decision.cumplida_en && <> · cumplida el <Fecha valor={decision.cumplida_en} /></>}
    </p>
  );
}

// Añade o cambia la fecha límite de la última decisión.
function CambiarFechaLimite({ prediccion, actual, alActualizar }) {
  const [fecha, setFecha] = useState(actual ?? "");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const id = `fecha-cambio-${prediccion.id}`;

  async function enviar(evento) {
    evento.preventDefault();
    setError("");
    setEnviando(true);
    try {
      alActualizar(await api.fijarFechaLimite(prediccion.id, fecha));
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <fieldset>
        <legend>{actual ? "Cambiar la fecha límite" : "Añadir fecha límite"}</legend>
        <div className="campo">
          <label htmlFor={id}>Fecha límite para el desarrollador</label>
          <input id={id} type="date" min={hoyLocal()} value={fecha} onChange={(e) => setFecha(e.target.value)} required />
        </div>
      </fieldset>
      <div>
        <button className="boton boton--secundario" type="submit" disabled={enviando}>
          {enviando ? "Guardando…" : "Guardar fecha límite"}
        </button>
      </div>
      <Alerta>{error}</Alerta>
    </form>
  );
}

function Decision({ prediccion, alActualizar }) {
  const { puedeDecidir } = useRoles();
  // La recomendación de la plataforma viene marcada; el líder puede
  // aceptarla o elegir otra decisión.
  const recomendada = decisionRecomendada(prediccion.recomendacion);
  const [decision, setDecision] = useState(recomendada);
  const [comentario, setComentario] = useState("");
  const [fechaLimite, setFechaLimite] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const decisiones = prediccion.decisiones ?? [];

  async function enviar(evento) {
    evento.preventDefault();
    setError("");
    setEnviando(true);
    try {
      alActualizar(await api.decidir(prediccion.id, { decision, comentario, fecha_limite: fechaLimite || null }));
      setDecision(recomendada);
      setComentario("");
      setFechaLimite("");
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      {decisiones.length ? (
        <ol className="decisiones">
          {decisiones.map((d, i) => (
            <li key={d.id ?? d.creada_en}>
              <strong>{DECISIONES[d.decision] || d.decision}</strong> · {d.usuario} · <Fecha valor={d.creada_en} />
              {d.acepta_recomendacion != null && (
                <span className="secundario">
                  {" "}
                  ·{" "}
                  {d.acepta_recomendacion
                    ? "aceptó la recomendación"
                    : `cambió la recomendación (${RECOMENDACIONES[d.recomendacion] ?? d.recomendacion})`}
                </span>
              )}
              {d.comentario && <p>{d.comentario}</p>}
              {i === 0 && <Seguimiento decision={d} />}
            </li>
          ))}
        </ol>
      ) : (
        <p className="secundario">El líder técnico aún no ha registrado una decisión sobre este despliegue.</p>
      )}
      {puedeDecidir && (
        <form className="formulario" onSubmit={enviar}>
          <fieldset>
            <legend>Registrar decisión</legend>
            {recomendada && (
              <p className="secundario" id={`ayuda-recomendacion-${prediccion.id}`}>
                La plataforma recomienda «{RECOMENDACIONES[prediccion.recomendacion]}» (nivel{" "}
                {NIVELES[prediccion.nivel]?.toLowerCase()}); aparece marcada. Puede aceptarla o elegir otra decisión.
              </p>
            )}
            {Object.entries(DECISIONES).map(([codigo, texto]) => (
              <label key={codigo} className="opcion">
                <input
                  type="radio"
                  name={`decision-${prediccion.id}`}
                  value={codigo}
                  checked={decision === codigo}
                  onChange={() => setDecision(codigo)}
                  required
                />
                {texto}
                {codigo === recomendada && <span className="insignia-recomendada">Recomendada</span>}
              </label>
            ))}
            {aceptaRecomendacion(prediccion.recomendacion, decision) === false && (
              <p className="secundario" role="status">
                Va a cambiar la recomendación de la plataforma. Explique el motivo en el comentario.
              </p>
            )}
            <div className="campo">
              <label htmlFor={`comentario-${prediccion.id}`}>Comentario (opcional)</label>
              <textarea
                id={`comentario-${prediccion.id}`}
                rows={3}
                maxLength={1000}
                value={comentario}
                onChange={(e) => setComentario(e.target.value)}
              />
            </div>
            <div className="campo">
              <label htmlFor={`fecha-limite-${prediccion.id}`}>Fecha límite para el desarrollador (opcional)</label>
              <input
                id={`fecha-limite-${prediccion.id}`}
                type="date"
                min={hoyLocal()}
                value={fechaLimite}
                onChange={(e) => setFechaLimite(e.target.value)}
                aria-describedby={`ayuda-fecha-${prediccion.id}`}
              />
              <span id={`ayuda-fecha-${prediccion.id}`} className="secundario">
                El comentario es el mensaje que recibe el desarrollador. No se admiten fechas pasadas.
              </span>
            </div>
          </fieldset>
          <div>
            <button className="boton" type="submit" disabled={enviando}>
              {enviando ? "Guardando…" : "Guardar decisión"}
            </button>
          </div>
          <Alerta>{error}</Alerta>
        </form>
      )}
      {puedeDecidir && decisiones.length > 0 && (
        <CambiarFechaLimite
          key={decisiones[0].id}
          prediccion={prediccion}
          actual={decisiones[0].fecha_limite}
          alActualizar={alActualizar}
        />
      )}
    </>
  );
}

// mostrarResultadoReal = false (Historial): sin el apartado «Resultado real».
// enComparacion (Nuevo análisis → «Comparar ambos»): todavía no es oficial, así
// que no hay resultado real ni decisión del líder.
export default function Resultado({ prediccion, modelos, mostrarResultadoReal = true, enComparacion = false }) {
  const [p, setP] = useState(prediccion);
  useEffect(() => setP(prediccion), [prediccion]);

  const modelo = modelos.find((m) => m.version === p.version_modelo);
  const meta = modelo?.metadatos;
  const limites = meta?.limites_riesgo;
  // Tasa de fallos observada en este nivel con despliegues reales (supervisión
  // del modelo). Sin casos suficientes no se muestra nada.
  const tasaNivel = modelo?.tasa_real_por_nivel?.[p.nivel];

  return (
    <article className="tarjeta resultado" aria-labelledby={`resultado-${p.id}`}>
      <header>
        <h2 id={`resultado-${p.id}`}>
          {enComparacion
            ? `${p.modelo_nombre ?? p.version_modelo}${modelo ? (modelo.activo ? " · Principal" : " · Alternativo") : ""}`
            : "Resultado del análisis"}
        </h2>
        <p className="secundario resultado__modelo">
          Modelo: <strong>{etiquetaModelo(p)}</strong>
        </p>
        {p.cambio?.archivos_modificados != null && (
          <p className="secundario">
            Cambio del commit: {p.cambio.archivos_modificados} archivos modificados · +{p.cambio.adiciones} / −
            {p.cambio.eliminaciones} líneas
          </p>
        )}
      </header>

      <dl className={`riesgo riesgo--${p.nivel}`}>
        <div>
          <dt>Nivel de riesgo</dt>
          <dd>
            <NivelRiesgo nivel={p.nivel} grande />
          </dd>
        </div>
        <div>
          <dt>Probabilidad calibrada de que el despliegue no se complete</dt>
          <dd>
            <output>{porcentaje(p.probabilidad)}</output>
          </dd>
        </div>
        {p.recomendacion && (
          <div>
            <dt>Recomendación de la plataforma</dt>
            <dd>
              <strong className={`recomendacion recomendacion--${p.recomendacion}`}>
                {RECOMENDACIONES[p.recomendacion]}
              </strong>
              <span className="secundario recomendacion__regla">
                {p.recomendacion === "solicitar_revision"
                  ? "Nivel alto: revisar el cambio antes de desplegar."
                  : "Nivel bajo o medio: se puede desplegar."}{" "}
                Decide el líder técnico.
              </span>
            </dd>
          </div>
        )}
      </dl>

      <div className="resultado__explicacion">
      {tasaNivel?.tasa != null && (
        <p>
          Con despliegues reales, no se completó el {porcentaje(tasaNivel.tasa)} de los análisis de{" "}
          {modelo.nombre_modelo} con nivel {NIVELES[p.nivel]?.toLowerCase() ?? p.nivel} ({tasaNivel.no_completados} de{" "}
          {tasaNivel.evaluables} despliegues verificados).
        </p>
      )}
      {limites && (
        <p className="secundario">
          Límites del modelo {p.version_modelo}: {NIVELES.bajo} por debajo de {porcentaje(limites.medio)};{" "}
          {NIVELES.medio} desde {porcentaje(limites.medio)}; {NIVELES.alto} desde {porcentaje(limites.alto)}.
        </p>
      )}
      </div>

      {p.analisis_ia?.origen === "ia" && (
        <section aria-labelledby={`analisis-${p.id}`}>
          <h3 id={`analisis-${p.id}`}>Análisis</h3>
          <p>{p.analisis_ia.resumen}</p>
          <p className="secundario">
            Redactado por {p.analisis_ia.modelo} a partir del resultado del modelo {p.version_modelo}; el nivel y la
            probabilidad son del modelo.
          </p>
        </section>
      )}

      <section aria-labelledby={`factores-${p.id}`}>
        <h3 id={`factores-${p.id}`}>Factores que más influyen</h3>
        <Factores factores={p.factores} />
      </section>

      <section aria-labelledby={`recomendaciones-${p.id}`}>
        <h3 id={`recomendaciones-${p.id}`}>Recomendaciones</h3>
        <ul className="recomendaciones">
          {p.recomendaciones.map((r) => (
            <li key={r.codigo}>
              <code className="codigo">{r.codigo}</code>
              {r.texto}
            </li>
          ))}
        </ul>
        {p.analisis_ia?.origen === "reglas" && p.analisis_ia.error && (
          <p className="secundario">
            El análisis con IA no estuvo disponible ({p.analisis_ia.error}); se muestran las recomendaciones por
            reglas.
          </p>
        )}
      </section>

      {mostrarResultadoReal && !enComparacion && <ResultadoReal prediccion={p} alActualizar={setP} />}

      {!enComparacion && (
        <section aria-labelledby={`decision-${p.id}`}>
          <h3 id={`decision-${p.id}`}>Decisión del líder técnico</h3>
          <Decision prediccion={p} alActualizar={setP} />
        </section>
      )}
    </article>
  );
}
