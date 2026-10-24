import { useEffect, useState } from "react";
import { api } from "../api.js";
import {
  Alerta, DECISIONES, EstadoAsignacion, Fecha, FechaDia, hoyLocal, NIVELES, NivelRiesgo, porcentaje, useRoles,
} from "./comunes.jsx";

// Textos de presentación para los códigos de EjecucionWorkflow.etiqueta y
// EjecucionWorkflow.subtipo_etiqueta (los códigos vienen de la API).
const ETIQUETAS = {
  despliegue_completado: "Despliegue completado",
  despliegue_no_completado: "Despliegue no completado",
  excluida_sin_intento: "Sin intento de despliegue (no evaluable)",
  excluida_ambigua: "Ambigua: falló otro job con el despliegue completado (no evaluable)",
  excluida_otro_resultado: "Cancelada u omitida (no evaluable)",
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
        contribución (valor SHAP) en esta predicción.
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

// Pasos para conseguir la ejecución real cuando la verificación queda pendiente.
// La regla está en PrediccionViewSet.verificar: mismo workflow y mismo commit,
// ejecución terminada e iniciada después del análisis.
function PasosPendiente({ pendiente }) {
  return (
    <div className="nota" role="status">
      <p><strong>{pendiente.detail}</strong></p>
      <p className="secundario">Para obtener el resultado real:</p>
      <ol>
        <li>
          Ejecute el workflow <code className="codigo">{pendiente.workflow_path}</code> en GitHub sobre el commit{" "}
          <code className="codigo">{pendiente.sha_corto}</code> de {pendiente.repositorio}.
        </li>
        <li>Espere a que la ejecución termine.</li>
        <li>Vuelva a pulsar «Verificar resultado real».</li>
      </ol>
      <p>
        <a href={pendiente.url_actions}>Abrir el workflow en GitHub Actions</a>
      </p>
    </div>
  );
}

function ResultadoReal({ prediccion, alActualizar }) {
  const [pendiente, setPendiente] = useState(null);
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const real = prediccion.ejecucion_real;

  async function verificar() {
    setCargando(true);
    setPendiente(null);
    setError("");
    try {
      const respuesta = await api.verificar(prediccion.id);
      if (respuesta.estado === "pendiente") setPendiente(respuesta);
      else alActualizar(respuesta);
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  if (!real) {
    return (
      <div className="recuadro">
        <p className="secundario">
          Aún no se ha enlazado la ejecución real. Se enlaza la primera ejecución terminada del mismo workflow y del
          mismo commit que haya empezado después de este análisis.
        </p>
        <button className="boton" type="button" disabled={cargando} onClick={verificar}>
          {cargando ? "Consultando GitHub…" : "Verificar resultado real"}
        </button>
        {pendiente && <PasosPendiente pendiente={pendiente} />}
        <Alerta>{error}</Alerta>
      </div>
    );
  }
  return (
    <dl className="datos recuadro">
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
  const [decision, setDecision] = useState("");
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
      setDecision("");
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
              </label>
            ))}
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

export default function Resultado({ prediccion, modelos }) {
  const [p, setP] = useState(prediccion);
  useEffect(() => setP(prediccion), [prediccion]);

  const meta = modelos.find((m) => m.version === p.version_modelo)?.metadatos;
  const limites = meta?.limites_riesgo;
  // Tasa de fallos observada por nivel en la evaluación del modelo. Solo se
  // muestra si VersionModelo.metadatos la contiene.
  const tasaNivel = meta?.tasa_fallos_por_nivel?.[p.nivel];

  return (
    <article className="tarjeta resultado" aria-labelledby={`resultado-${p.id}`}>
      <header>
        <h2 id={`resultado-${p.id}`}>Resultado del análisis</h2>
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
      </dl>

      <div className="resultado__explicacion">
      {tasaNivel ? (
        <p>
          En la evaluación, falló el {porcentaje(tasaNivel.tasa)} de los casos con este nivel ({tasaNivel.n} ejecuciones
          de prueba del modelo {p.version_modelo}).
        </p>
      ) : (
        <p className="secundario">
          La tasa de fallos observada por nivel no está registrada en los metadatos del modelo {p.version_modelo}.
        </p>
      )}
      {limites && (
        <p className="secundario">
          Límites del modelo {p.version_modelo}: {NIVELES.bajo} por debajo de {porcentaje(limites.medio)};{" "}
          {NIVELES.medio} desde {porcentaje(limites.medio)}; {NIVELES.alto} desde {porcentaje(limites.alto)}.
        </p>
      )}
      </div>

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
      </section>

      <section aria-labelledby={`real-${p.id}`}>
        <h3 id={`real-${p.id}`}>Resultado real</h3>
        <ResultadoReal prediccion={p} alActualizar={setP} />
      </section>

      <section aria-labelledby={`decision-${p.id}`}>
        <h3 id={`decision-${p.id}`}>Decisión del líder técnico</h3>
        <Decision prediccion={p} alActualizar={setP} />
      </section>
    </article>
  );
}
