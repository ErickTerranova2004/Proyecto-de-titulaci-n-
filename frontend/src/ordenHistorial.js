// Historial: primero lo que tuvo actividad más reciente. La actividad de un
// análisis es su última decisión (si la tiene) o su creación: así, al
// registrar una decisión, ese análisis pasa al primer lugar.

export function ultimaActividad(p) {
  const fechas = [p.creada_en, ...(p.decisiones ?? []).map((d) => d.creada_en)]
    .filter(Boolean)
    .map((f) => new Date(f).getTime());
  return Math.max(...fechas);
}

export function ordenarPorActividad(analisis) {
  return [...(analisis ?? [])].sort((a, b) => ultimaActividad(b) - ultimaActividad(a) || b.id - a.id);
}
