// Paginación de las tablas largas. La hace el backend (riesgo/paginacion.py):
// con ?pagina=N responde { total, pagina, por_pagina, paginas, resultados }.

export const POR_PAGINA = [25, 50, 100];
export const PAGINACION_INICIAL = { pagina: 1, porPagina: 25 };

// Añade pagina y por_pagina a una consulta ("" o "?a=b").
export function consultaPaginada(consulta = "", { pagina = 1, porPagina = 25 } = {}) {
  const p = new URLSearchParams(consulta.replace(/^\?/, ""));
  p.set("pagina", String(pagina));
  p.set("por_pagina", String(porPagina));
  return `?${p.toString()}`;
}

// Botones de página: siempre la primera y la última, la actual y sus vecinas;
// "…" donde se saltan páginas. Ej.: 1 … 4 5 6 … 20.
export function paginasVisibles(pagina, paginas, vecinas = 1) {
  if (paginas <= 1) return [1];
  const numeros = new Set([1, paginas]);
  for (let n = pagina - vecinas; n <= pagina + vecinas; n++) {
    if (n >= 1 && n <= paginas) numeros.add(n);
  }
  const ordenados = [...numeros].sort((a, b) => a - b);
  const resultado = [];
  ordenados.forEach((n, i) => {
    if (i > 0 && n - ordenados[i - 1] > 1) resultado.push(n - ordenados[i - 1] === 2 ? n - 1 : "…");
    resultado.push(n);
  });
  return resultado;
}

// "Mostrando 26–50 de 128 análisis" (o "0 análisis").
export function textoRango({ total, pagina, por_pagina: porPagina }, sustantivo = "resultados") {
  if (!total) return `0 ${sustantivo}`;
  const desde = (pagina - 1) * porPagina + 1;
  const hasta = Math.min(pagina * porPagina, total);
  return `Mostrando ${desde}–${hasta} de ${total} ${sustantivo}`;
}
