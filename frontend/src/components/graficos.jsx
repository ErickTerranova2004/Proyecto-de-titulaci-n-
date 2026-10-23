// Gráficos en SVG propio (sin librerías). Cada gráfico incluye una tabla
// oculta con los mismos datos para lectores de pantalla.
import { NIVELES, NivelRiesgo, porcentaje } from "./comunes.jsx";

const ORDEN = ["bajo", "medio", "alto"];

function TablaAccesible({ caption, columnas, filas }) {
  return (
    <table className="solo-lector">
      <caption>{caption}</caption>
      <thead>
        <tr>{columnas.map((c) => <th key={c} scope="col">{c}</th>)}</tr>
      </thead>
      <tbody>
        {filas.map((fila, i) => (
          <tr key={i}>{fila.map((celda, j) => <td key={j}>{celda}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}

export function Dona({ conteos, titulo }) {
  const total = ORDEN.reduce((s, n) => s + (conteos[n] || 0), 0);
  const radio = 48;
  const circunferencia = 2 * Math.PI * radio;
  let acumulado = 0;
  return (
    <div className="dona">
      <svg viewBox="0 0 120 120" className="dona__svg" aria-hidden="true">
        <circle cx="60" cy="60" r={radio} className="dona__fondo" />
        {total > 0 &&
          ORDEN.map((nivel) => {
            const largo = ((conteos[nivel] || 0) / total) * circunferencia;
            const segmento = (
              <circle
                key={nivel}
                cx="60"
                cy="60"
                r={radio}
                className={`dona__segmento serie--${nivel}`}
                strokeDasharray={`${largo} ${circunferencia - largo}`}
                strokeDashoffset={-acumulado}
              />
            );
            acumulado += largo;
            return segmento;
          })}
        <text x="60" y="58" textAnchor="middle" className="dona__total">{total}</text>
        <text x="60" y="74" textAnchor="middle" className="dona__etiqueta">análisis</text>
      </svg>
      <ul className="leyenda">
        {ORDEN.map((nivel) => (
          <li key={nivel}>
            <NivelRiesgo nivel={nivel} />
            <span className="leyenda__valor">
              {conteos[nivel] || 0} ({total ? porcentaje((conteos[nivel] || 0) / total, 0) : "0 %"})
            </span>
          </li>
        ))}
      </ul>
      <TablaAccesible
        caption={titulo}
        columnas={["Nivel", "Análisis"]}
        filas={ORDEN.map((n) => [NIVELES[n], conteos[n] || 0])}
      />
    </div>
  );
}

const ANCHO = 600;
const ALTO = 220;
const MARGEN = { izq: 36, der: 12, sup: 12, inf: 28 };

function ejeY(maximo, formato) {
  const marcas = [0, 0.5, 1].map((f) => f * maximo);
  const alto = ALTO - MARGEN.sup - MARGEN.inf;
  return marcas.map((valor) => {
    const y = MARGEN.sup + alto - (valor / maximo) * alto;
    return (
      <g key={valor}>
        <line x1={MARGEN.izq} x2={ANCHO - MARGEN.der} y1={y} y2={y} className="eje__guia" />
        <text x={MARGEN.izq - 6} y={y + 4} textAnchor="end" className="eje__texto">{formato(valor)}</text>
      </g>
    );
  });
}

function etiquetasX(dias, x) {
  if (!dias.length) return null;
  const indices = [...new Set([0, Math.floor((dias.length - 1) / 2), dias.length - 1])];
  return indices.map((i) => (
    <text key={i} x={x(i)} y={ALTO - 8} textAnchor="middle" className="eje__texto">
      {dias[i].etiqueta}
    </text>
  ));
}

export function BarrasApiladas({ dias, titulo }) {
  const maximo = Math.max(1, ...dias.map((d) => ORDEN.reduce((s, n) => s + d[n], 0)));
  const anchoUtil = ANCHO - MARGEN.izq - MARGEN.der;
  const altoUtil = ALTO - MARGEN.sup - MARGEN.inf;
  const paso = anchoUtil / Math.max(dias.length, 1);
  const anchoBarra = Math.max(2, paso * 0.6);
  const x = (i) => MARGEN.izq + paso * i + paso / 2;
  return (
    <>
      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="grafico" aria-hidden="true">
        {ejeY(maximo, (v) => Math.round(v))}
        {dias.map((d, i) => {
          let base = MARGEN.sup + altoUtil;
          return ORDEN.map((nivel) => {
            const alto = (d[nivel] / maximo) * altoUtil;
            base -= alto;
            return alto > 0 ? (
              <rect
                key={`${i}-${nivel}`}
                x={x(i) - anchoBarra / 2}
                y={base}
                width={anchoBarra}
                height={alto}
                className={`barra serie--${nivel}`}
              />
            ) : null;
          });
        })}
        {etiquetasX(dias, x)}
      </svg>
      <ul className="leyenda leyenda--fila" aria-hidden="true">
        {ORDEN.map((nivel) => <li key={nivel}><NivelRiesgo nivel={nivel} /></li>)}
      </ul>
      <TablaAccesible
        caption={titulo}
        columnas={["Día", NIVELES.bajo, NIVELES.medio, NIVELES.alto]}
        filas={dias.filter((d) => d.bajo + d.medio + d.alto).map((d) => [d.etiqueta, d.bajo, d.medio, d.alto])}
      />
    </>
  );
}

export function Linea({ dias, limites, titulo }) {
  const valido = (d) => Number.isFinite(d.valor) && d.valor >= 0 && d.valor <= 1;
  const valores = dias.filter(valido);
  if (!valores.length) return <p className="nota">No hay datos de probabilidad en el período seleccionado.</p>;
  const primero = dias.findIndex(valido);
  const ultimo = dias.length - 1 - [...dias].reverse().findIndex(valido);
  const visibles = dias.slice(primero, ultimo + 1);
  const ancho = 900, alto = 280;
  const margen = { izq: 52, der: 24, sup: 18, inf: 42 };
  const anchoUtil = ancho - margen.izq - margen.der;
  const altoUtil = alto - margen.sup - margen.inf;
  const x = (i) => margen.izq + (visibles.length === 1 ? anchoUtil / 2 : i * anchoUtil / (visibles.length - 1));
  const y = (v) => margen.sup + (1 - v) * altoUtil;
  const segmentos = [];
  let segmento = [];
  visibles.forEach((d, i) => {
    if (valido(d)) segmento.push(`${x(i)},${y(d.valor)}`);
    else if (segmento.length) { segmentos.push(segmento); segmento = []; }
  });
  if (segmento.length) segmentos.push(segmento);
  const indices = [...new Set([0, Math.floor((visibles.length - 1) / 2), visibles.length - 1])];
  return (
    <>
      <div className="tendencia__leyenda">
        <span><i className="tendencia__muestra" />Media diaria</span>
        {limites && ["medio", "alto"].filter((n) => Number.isFinite(limites[n])).map((nivel) => <span key={nivel} className={`serie--${nivel}`}><i className="tendencia__umbral" />{NIVELES[nivel]} desde {porcentaje(limites[nivel], 0)}</span>)}
      </div>
      <div className="tendencia__marco">
      <svg viewBox={`0 0 ${ancho} ${alto}`} className="grafico tendencia__grafico" aria-hidden="true">
        {[0, .25, .5, .75, 1].map((v) => <g key={v}><line x1={margen.izq} x2={ancho - margen.der} y1={y(v)} y2={y(v)} className="eje__guia" /><text x={margen.izq - 10} y={y(v) + 4} textAnchor="end" className="eje__texto">{v * 100}%</text></g>)}
        {limites &&
          ["medio", "alto"].filter((n) => Number.isFinite(limites[n]) && limites[n] >= 0 && limites[n] <= 1).map((nivel) => (
            <g key={nivel}>
              <line
                x1={margen.izq}
                x2={ancho - margen.der}
                y1={y(limites[nivel])}
                y2={y(limites[nivel])}
                className={`umbral serie--${nivel}`}
              />
            </g>
          ))}
        {segmentos.map((puntos, i) => puntos.length > 1 && <polyline key={i} points={puntos.join(" ")} className="linea" />)}
        {visibles.map((d, i) => valido(d) && <circle key={i} cx={x(i)} cy={y(d.valor)} r="4" className="punto"><title>{`${d.etiqueta}: ${porcentaje(d.valor)} · ${d.n ?? "—"} análisis`}</title></circle>)}
        {indices.map((i) => <text key={i} x={x(i)} y={alto - 14} textAnchor={visibles.length === 1 ? "middle" : i === 0 ? "start" : i === visibles.length - 1 ? "end" : "middle"} className="eje__texto">{visibles[i].etiqueta}</text>)}
      </svg>
      </div>
      <p className="secundario tendencia__nota">Escala fija de 0 a 100 %. Se muestra desde el primer hasta el último día con análisis del período. Los días sin datos interrumpen la línea. Los umbrales son referencias del modelo para cada análisis individual.</p>
      <TablaAccesible
        caption={titulo}
        columnas={["Día", "Probabilidad media", "Análisis"]}
        filas={valores.map((d) => [d.etiqueta, porcentaje(d.valor), d.n ?? "—"])}
      />
    </>
  );
}

export function Embudo({ pasos }) {
  const maximo = Math.max(1, pasos[0]?.valor || 0);
  return (
    <ol className="embudo">
      {pasos.map((p, i) => (
        <li key={p.etiqueta} className="embudo__paso">
          <span className="embudo__texto">
            <span className="embudo__indice" aria-hidden="true">{i + 1}.</span> {p.etiqueta}
          </span>
          <span className="embudo__barra" aria-hidden="true">
            <span className="embudo__relleno" style={{ width: `${(p.valor / maximo) * 100}%`, opacity: 1 - i * 0.15 }} />
          </span>
          <span className="embudo__valor">
            {p.valor}
            {i > 0 && pasos[0].valor > 0 && (
              <span className="secundario"> ({porcentaje(p.valor / pasos[0].valor, 0)})</span>
            )}
          </span>
        </li>
      ))}
    </ol>
  );
}

