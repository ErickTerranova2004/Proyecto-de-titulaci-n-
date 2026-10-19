import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Alerta, DECISIONES, Fecha, NIVELES, NivelRiesgo, porcentaje, useRoles } from "./comunes.jsx";

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

function ResultadoReal({ prediccion, alActualizar }) {
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const [cargando, setCargando] = useState(false);
  const real = prediccion.ejecucion_real;

  async function verificar() {
    setCargando(true);
    setMensaje("");
    setError("");
    try {
      const respuesta = await api.verificar(prediccion.id);
      if (respuesta.estado === "pendiente") setMensaje(respuesta.detail);
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
        <p className="secundario">Aún no se ha enlazado la ejecución real de este workflow y commit.</p>
        <button className="boton" type="button" disabled={cargando} onClick={verificar}>
          {cargando ? "Consultando GitHub…" : "Verificar resultado real"}
        </button>
        {mensaje && <p className="secundario" role="status">{mensaje}</p>}
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

function Decision({ prediccion, alActualizar }) {
  const { puedeDecidir } = useRoles();
  const [decision, setDecision] = useState("");
  const [comentario, setComentario] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const decisiones = prediccion.decisiones ?? [];

  async function enviar(evento) {
    evento.preventDefault();
    setError("");
    setEnviando(true);
    try {
      alActualizar(await api.decidir(prediccion.id, { decision, comentario }));
      setDecision("");
      setComentario("");
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
          {decisiones.map((d) => (
            <li key={d.creada_en}>
              <strong>{DECISIONES[d.decision] || d.decision}</strong> · {d.usuario} · <Fecha valor={d.creada_en} />
              {d.comentario && <p>{d.comentario}</p>}
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
          </fieldset>
          <div>
            <button className="boton" type="submit" disabled={enviando}>
              {enviando ? "Guardando…" : "Guardar decisión"}
            </button>
          </div>
          <Alerta>{error}</Alerta>
        </form>
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
        <p className="secundario">
          <strong>{p.repositorio}</strong> · {p.workflow_path} · commit <code>{p.head_sha.slice(0, 7)}</code> · rama {p.rama || "—"} ·
          evento {p.evento}
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
      <p className="nota">
        La probabilidad estima si el intento de despliegue <strong>no se completará con éxito</strong> en GitHub Actions.
        No mide incidentes posteriores en producción.
      </p>
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

      <footer className="secundario">
        Modelo {p.version_modelo} · historial usado: {p.ejecuciones_previas.length} ejecuciones previas · datos de
        GitHub extraídos el <Fecha valor={p.datos_github_extraidos_en} /> · análisis de {p.usuario} el{" "}
        <Fecha valor={p.creada_en} />
      </footer>
    </article>
  );
}
