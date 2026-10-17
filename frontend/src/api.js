// Cliente de la API. El token se guarda solo durante la sesión del navegador.
const CLAVE = "token_riesgo";

export const sesion = {
  token: () => sessionStorage.getItem(CLAVE),
  guardar: (token) => sessionStorage.setItem(CLAVE, token),
  cerrar: () => sessionStorage.removeItem(CLAVE),
};

async function solicitar(ruta, opciones = {}) {
  const cabeceras = { "Content-Type": "application/json" };
  const token = sesion.token();
  if (token) cabeceras.Authorization = `Token ${token}`;
  const respuesta = await fetch(`/api${ruta}`, { ...opciones, headers: cabeceras });
  const datos = await respuesta.json().catch(() => ({}));
  if (respuesta.status === 401) sesion.cerrar();
  if (!respuesta.ok) {
    const mensaje =
      datos.detail ||
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
  resumen: () => solicitar("/predicciones/resumen/"),
  modelos: () => solicitar("/modelos/"),
  activarModelo: (id) => solicitar(`/modelos/${id}/activar/`, { method: "POST" }),
};
