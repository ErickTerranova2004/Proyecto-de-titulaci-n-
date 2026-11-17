// Historial: primero los análisis con decisión del líder técnico, de la
// decisión más reciente a la más antigua (aunque el análisis sea antiguo),
// para no tener que buscarlas; después los que no tienen decisión, del más
// reciente al más antiguo.

function tiempo(fecha) {
  return fecha ? new Date(fecha).getTime() : 0;
}

export function ultimaDecision(p) {
  return Math.max(0, ...(p.decisiones ?? []).map((d) => tiempo(d.creada_en)));
}

export function ordenarPorActividad(analisis) {
  return [...(analisis ?? [])].sort(
    (a, b) => ultimaDecision(b) - ultimaDecision(a) || tiempo(b.creada_en) - tiempo(a.creada_en) || b.id - a.id,
  );
}
