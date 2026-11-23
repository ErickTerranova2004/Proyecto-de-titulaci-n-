// Cliente de la API. El token se guarda solo durante la sesión del navegador.
export const CLAVE_SESION = "token_riesgo";
const CLAVE = CLAVE_SESION;
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

// Error de la API con el código HTTP (`estado`; 0 si el servidor no responde).
function errorApi(mensaje, estado, datos = {}) {
    const error = new Error(mensaje);
    error.estado = estado;
    error.datos = datos;
    return error;
}

async function solicitar(ruta, opciones = {}) {
    const cabeceras = { "Content-Type": "application/json" };
    const token = sesion.token();
    if (token) cabeceras.Authorization = `Token ${token}`;
    let respuesta;
    try {
        respuesta = await fetch(`${BASE_API}${ruta}`, {...opciones, headers: cabeceras });
    } catch {
        throw errorApi("El servidor no responde.", 0);
    }
    const datos = await respuesta.json().catch(() => ({}));
    if (respuesta.status === 401) sesion.cerrar();
    if (respuesta.status === 429) throw errorApi("Límite de peticiones alcanzado. Espere unos segundos.", 429);
    if (!respuesta.ok) {
        const mensaje =
            datos.detail ||
            (datos.non_field_errors && datos.non_field_errors[0]) ||
            Object.entries(datos)
            .map(([campo, errores]) => `${campo}: ${[].concat(errores).join(" ")}`)
            .join(" · ") ||
            `Error ${respuesta.status}`;
        throw errorApi(mensaje, respuesta.status, datos);
    }
    return datos;
}

// Descarga binaria con el token (p. ej. el PDF de un informe). Devuelve
// { blob, nombre } con el nombre de Content-Disposition.
async function descargar(ruta) {
    const cabeceras = {};
    const token = sesion.token();
    if (token) cabeceras.Authorization = `Token ${token}`;
    let respuesta;
    try {
        respuesta = await fetch(`${BASE_API}${ruta}`, { headers: cabeceras });
    } catch {
        throw errorApi("El servidor no responde.", 0);
    }
    if (respuesta.status === 401) sesion.cerrar();
    if (!respuesta.ok) {
        const datos = await respuesta.json().catch(() => ({}));
        throw errorApi(datos.detail || `Error ${respuesta.status}`, respuesta.status, datos);
    }
    const disposicion = respuesta.headers.get("Content-Disposition") || "";
    const nombre = /filename="?([^";]+)"?/.exec(disposicion)?.[1] || "descarga";
    return { blob: await respuesta.blob(), nombre };
}

export const api = {
    login: (username, password) =>
        solicitar("/auth/token/", { method: "POST", body: JSON.stringify({ username, password }) }),
    yo: () => solicitar("/yo/"),
    // Restablecimiento de contraseña por correo (sin sesión).
    olvideContrasena: (correo) =>
        solicitar("/auth/restablecer/solicitar/", { method: "POST", body: JSON.stringify({ correo }) }),
    validarEnlace: (uid, token) =>
        solicitar("/auth/restablecer/validar/", { method: "POST", body: JSON.stringify({ uid, token }) }),
    restablecerContrasena: (uid, token, contrasena, confirmacion) =>
        solicitar("/auth/restablecer/confirmar/", {
            method: "POST",
            body: JSON.stringify({ uid, token, contrasena, confirmacion }),
        }),
    predecir: (datos) => solicitar("/predicciones/", { method: "POST", body: JSON.stringify(datos) }),
    // «Comparar ambos»: el análisis que queda como oficial (y la respuesta a la asignación, si la hay).
    elegirOficial: (id, datos = {}) =>
        solicitar(`/predicciones/${id}/oficial/`, { method: "POST", body: JSON.stringify(datos) }),
    // consulta: "?desde=…&hasta=…&nivel=…" (src/filtrosHistorial.js).
    historial: (consulta = "") => solicitar(`/predicciones/${consulta}`),
    prediccion: (id) => solicitar(`/predicciones/${id}/`),
    verificar: (id) => solicitar(`/predicciones/${id}/verificar/`, { method: "POST" }),
    // Planificador: estimar un escenario alternativo no guarda nada.
    estimarEscenario: (id, condiciones, modelo) =>
        solicitar(`/predicciones/${id}/escenario/${modelo ? `?modelo=${encodeURIComponent(modelo)}` : ""}`, {
            method: "POST",
            body: JSON.stringify(condiciones),
        }),
    // Mejores ventanas desde mañana; `dias` opcional (por defecto, el del backend);
    // `modelo` opcional (por defecto, el del análisis base).
    ventanas: (id, dias, modelo) => {
        const q = new URLSearchParams();
        if (dias) q.set("dias", dias);
        if (modelo) q.set("modelo", modelo);
        return solicitar(`/predicciones/${id}/ventanas/${q.size ? `?${q}` : ""}`);
    },
    repositorios: () => solicitar("/repositorios/"),
    // Todos los repositorios asignados, aunque no tengan workflows utilizables.
    repositoriosAsignados: () => solicitar("/repositorios/?todos=1"),
    modelos: () => solicitar("/modelos/"),
    activarModelo: (id, confirmacion) =>
        solicitar(`/modelos/${id}/activar/`, { method: "POST", body: JSON.stringify({ confirmacion }) }),
    supervision: (id) => solicitar(`/modelos/${id}/supervision/`),
    comparacionSombra: () => solicitar("/modelos/comparacion-sombra/"),
    decidir: (id, datos) =>
        solicitar(`/predicciones/${id}/decision/`, { method: "POST", body: JSON.stringify(datos) }),
    fijarFechaLimite: (id, fecha_limite) =>
        solicitar(`/predicciones/${id}/fecha-limite/`, { method: "POST", body: JSON.stringify({ fecha_limite }) }),
    // Sin consulta, la lista completa (alarma); con "?pagina=…", una página.
    asignaciones: (consulta = "") => solicitar(`/asignaciones/${consulta}`),
    marcarVista: (id) => solicitar(`/asignaciones/${id}/vista/`, { method: "POST" }),
    marcarCumplida: (id) => solicitar(`/asignaciones/${id}/cumplida/`, { method: "POST" }),
    marcarEntendida: (id) => solicitar(`/asignaciones/${id}/entendida/`, { method: "POST" }),
    // Informes de cumplimiento (desarrollador → líder técnico).
    enviarInforme: (asignacionId, comentario) =>
        solicitar(`/asignaciones/${asignacionId}/informe/`, { method: "POST", body: JSON.stringify({ comentario }) }),
    // consulta: "?desde=…&hasta=…&orden=antiguo" (src/informes.js).
    informes: (consulta = "") => solicitar(`/informes/${consulta}`),
    informe: (id) => solicitar(`/informes/${id}/`),
    decidirInforme: (id, datos) =>
        solicitar(`/informes/${id}/decision/`, { method: "POST", body: JSON.stringify(datos) }),
    // El backend registra quién lo descargó.
    pdfInforme: (id) => descargar(`/informes/${id}/pdf/`),
    resumenAdmin: () => solicitar("/resumen-admin/"),
    integraciones: () => solicitar("/integraciones/"),
    sincronizar: (id) => solicitar(`/repositorios/${id}/sincronizar/`, { method: "POST" }),
    registrarWorkflow: (datos) =>
        solicitar("/repositorios/registrar/", { method: "POST", body: JSON.stringify(datos) }),

    // Gestión de usuarios, accesos y workflows (solo administrador).
    // consulta "?pagina=…&filtro=…&q=…": añade `tabla`, la página filtrada.
    gestionUsuarios: (consulta = "") => solicitar(`/gestion/usuarios/${consulta}`),
    crearUsuario: (datos) =>
        solicitar("/gestion/usuarios/", { method: "POST", body: JSON.stringify(datos) }),
    editarUsuario: (id, datos) =>
        solicitar(`/gestion/usuarios/${id}/`, { method: "PATCH", body: JSON.stringify(datos) }),
    // transferirA: cuenta que recibe el historial (análisis, decisiones y accesos).
    eliminarUsuario: (id, transferirA) =>
        solicitar(`/gestion/usuarios/${id}/${transferirA ? `?transferir_a=${encodeURIComponent(transferirA)}` : ""}`, { method: "DELETE" }),
    // Envía al usuario el enlace para restablecer su contraseña.
    enviarRestablecimiento: (id) => solicitar(`/gestion/usuarios/${id}/restablecer/`, { method: "POST" }),
    accesosUsuario: (id, repositorios) =>
        solicitar(`/gestion/usuarios/${id}/repositorios/`, { method: "PUT", body: JSON.stringify({ repositorios }) }),
    gestionWorkflows: () => solicitar("/gestion/workflows/"),
    editarWorkflow: (id, datos) =>
        solicitar(`/gestion/workflows/${id}/`, { method: "PATCH", body: JSON.stringify(datos) }),
    validarWorkflows: (datos) =>
        solicitar("/gestion/workflows/validar/", { method: "POST", body: JSON.stringify(datos) }),
    comprobarWorkflow: (id) => solicitar(`/gestion/workflows/${id}/comprobar/`, { method: "POST" }),
};