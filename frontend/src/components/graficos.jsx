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
  const valores = dias.filter((d) => d.valor !== null);
  const maximo = Math.min(1, Math.max(0.1, ...valores.map((d) => d.valor), limites ? limites.alto * 1.25 : 0));
  const anchoUtil = ANCHO - MARGEN.izq - MARGEN.der;
  const altoUtil = ALTO - MARGEN.sup - MARGEN.inf;
  const paso = anchoUtil / Math.max(dias.length - 1, 1);
  const x = (i) => MARGEN.izq + paso * i;
  const y = (v) => MARGEN.sup + altoUtil - (v / maximo) * altoUtil;
  const puntos = dias.map((d, i) => (d.valor === null ? null : `${x(i)},${y(d.valor)}`)).filter(Boolean);
  return (
    <>
      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} className="grafico" aria-hidden="true">
        {ejeY(maximo, (v) => `${Math.round(v * 100)}%`)}
        {limites &&
          ["medio", "alto"].map((nivel) => (
            <g key={nivel}>
              <line
                x1={MARGEN.izq}
                x2={ANCHO - MARGEN.der}
                y1={y(limites[nivel])}
                y2={y(limites[nivel])}
                className={`umbral serie--${nivel}`}
              />
              <text x={ANCHO - MARGEN.der} y={y(limites[nivel]) - 4} textAnchor="end" className="eje__texto">
                {NIVELES[nivel]} desde {porcentaje(limites[nivel], 0)}
              </text>
            </g>
          ))}
        {puntos.length > 1 && <polyline points={puntos.join(" ")} className="linea" />}
        {dias.map((d, i) => d.valor !== null && <circle key={i} cx={x(i)} cy={y(d.valor)} r="3" className="punto" />)}
        {etiquetasX(dias, x)}
      </svg>
      <TablaAccesible
        caption={titulo}
        columnas={["Día", "Probabilidad media"]}
        filas={valores.map((d) => [d.etiqueta, porcentaje(d.valor)])}
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
