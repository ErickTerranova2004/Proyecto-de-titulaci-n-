// Commits pendientes de desplegar (los calcula la tarea programada del lote;
// /api/repositorios/ los devuelve sin consultar GitHub). Los repositorios con
// commits pendientes van primero en «Nuevo análisis» y, al elegir uno, se
// rellenan el commit, la rama y el evento con el que despliega.

export function commitsPendientes(workflow) {
  const n = workflow?.pendientes?.commits;
  return typeof n === "number" && n > 0 ? n : 0;
}

export function pendientesRepo(repo) {
  return Math.max(0, ...(repo?.workflows ?? []).map(commitsPendientes));
}

export function textoPendientes(n) {
  if (!n) return "";
  return n === 1 ? "1 commit pendiente" : `${n} commits pendientes`;
}

// Primero los que tienen commits pendientes (más pendientes antes); el resto,
// en el orden de la API (alfabético).
export function ordenarRepos(repos) {
  return [...(repos ?? [])]
    .map((repo, i) => ({ repo, i, n: pendientesRepo(repo) }))
    .sort((a, b) => (b.n > 0) - (a.n > 0) || b.n - a.n || a.i - b.i)
    .map(({ repo }) => repo);
}

// El workflow con más commits pendientes (o el primero).
export function workflowInicial(repo) {
  const workflows = repo?.workflows ?? [];
  return workflows.reduce((mejor, w) => (commitsPendientes(w) > commitsPendientes(mejor) ? w : mejor), workflows[0]);
}

// Commit (cabeza de la rama principal), rama y evento para analizar antes del
// próximo despliegue; null si el workflow no tiene commits pendientes.
export function datosPendientes(workflow, eventosValidos) {
  if (!commitsPendientes(workflow)) return null;
  const p = workflow.pendientes;
  return {
    head_sha: p.sha,
    rama: p.rama || p.rama_principal || "main",
    evento: eventosValidos.includes(p.evento) ? p.evento : "push",
  };
}
