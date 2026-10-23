// Cliente de la API. El token se guarda solo durante la sesión del navegador.
const CLAVE = "token_riesgo";
// Ruta de la API en el backend. En desarrollo Vite la redirige a Django
// (vite.config.js), igual que /admin.
const BASE_API = "/api";

// Página del administrador de Django, en el mismo servidor que la API.
export const urlAdmin = (ruta = "") => `${BASE_API.replace(/\/api$/, "")}/admin/${ruta}`;

export const sesion = {
  token: () => sessionStorage.getItem(CLAVE),
  guardar: (token) => sessionStorage.setItem(CLAVE, token),
  cerrar: () => sessionStorage.removeItem(CLAVE),
};

async function solicitar(ruta, opciones = {}) {
  const cabeceras = { "Content-Type": "application/json" };
  const token = sesion.token();
  if (token) cabeceras.Authorization = `Token ${token}`;
  const respuesta = await fetch(`${BASE_API}${ruta}`, { ...opciones, headers: cabeceras });
  const datos = await respuesta.json().catch(() => ({}));
  if (respuesta.status === 401) sesion.cerrar();
  if (respuesta.status === 429) throw new Error("Límite de peticiones alcanzado. Espere unos segundos.");
  if (!respuesta.ok) {
    const mensaje =
      datos.detail ||
      datos.non_field_errors?.[0] ||
      Object.entries(datos)
        .map(([campo, errores]) => `${campo}: ${[].concat(errores).join(" ")}`)
        .join(" · ") ||
      `Error ${respuesta.status}`;
    throw new Error(mensaje);
  }
  return datos;
}

export const api = {
  login: (username, password) =>
    solicitar("/auth/token/", { method: "POST", body: JSON.stringify({ username, password }) }),
  yo: () => solicitar("/yo/"),
  predecir: (datos) => solicitar("/predicciones/", { method: "POST", body: JSON.stringify(datos) }),
  historial: () => solicitar("/predicciones/"),
  verificar: (id) => solicitar(`/predicciones/${id}/verificar/`, { method: "POST" }),
  repositorios: () => solicitar("/repositorios/"),
  // Todos los repositorios asignados, aunque no tengan workflows utilizables.
  repositoriosAsignados: () => solicitar("/repositorios/?todos=1"),
  modelos: () => solicitar("/modelos/"),
  activarModelo: (id) => solicitar(`/modelos/${id}/activar/`, { method: "POST" }),
  supervision: (id) => solicitar(`/modelos/${id}/supervision/`),
  decidir: (id, datos) =>
    solicitar(`/predicciones/${id}/decision/`, { method: "POST", body: JSON.stringify(datos) }),
  fijarFechaLimite: (id, fecha_limite) =>
    solicitar(`/predicciones/${id}/fecha-limite/`, { method: "POST", body: JSON.stringify({ fecha_limite }) }),
  asignaciones: () => solicitar("/asignaciones/"),
  marcarVista: (id) => solicitar(`/asignaciones/${id}/vista/`, { method: "POST" }),
  marcarCumplida: (id) => solicitar(`/asignaciones/${id}/cumplida/`, { method: "POST" }),
  resumenAdmin: () => solicitar("/resumen-admin/"),
  integraciones: () => solicitar("/integraciones/"),
  sincronizar: (id) => solicitar(`/repositorios/${id}/sincronizar/`, { method: "POST" }),
  registrarWorkflow: (datos) =>
    solicitar("/repositorios/registrar/", { method: "POST", body: JSON.stringify(datos) }),
};
