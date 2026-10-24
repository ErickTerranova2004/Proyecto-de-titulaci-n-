// Carga independiente de las tarjetas del panel de administración: cada una
// pide su endpoint por separado (Promise.allSettled), de modo que un fallo no
// arrastra a las demás. Cada tarjeta queda en uno de tres estados:
//   { estado: "ok", datos }        datos disponibles
//   { estado: "vacio", motivo }    la API respondió, pero no hay datos
//   { estado: "error", motivo }    la API falló, con el motivo concreto

// Motivo legible de un error de api.js (error.estado = código HTTP o 0).
export function motivoError(error) {
  const estado = error?.estado;
  if (estado === 0) return "El servidor no responde.";
  if (estado === 401) return "La sesión caducó: inicie sesión de nuevo.";
  if (estado === 403) return "Sin permiso: la sesión de esta ventana no es de un administrador.";
  if (estado === 404) return "El servidor no tiene este endpoint: reinicie el backend con la versión actual.";
  if (estado === 429) return "Límite de peticiones alcanzado. Espere unos minutos.";
  if (estado >= 500) return "Error del servidor al obtener estos datos.";
  return error?.message || "No se pudieron obtener estos datos.";
}

// `peticiones`: { clave: () => Promise }. `vacio`: { clave: (datos) => motivo
// o null } para decidir si una respuesta correcta no tiene datos.
export async function cargarTarjetas(peticiones, vacio = {}) {
  const claves = Object.keys(peticiones);
  const resultados = await Promise.allSettled(claves.map((clave) => peticiones[clave]()));
  return Object.fromEntries(
    resultados.map((resultado, i) => {
      const clave = claves[i];
      if (resultado.status === "rejected") {
        return [clave, { estado: "error", motivo: motivoError(resultado.reason) }];
      }
      const motivoVacio = vacio[clave]?.(resultado.value);
      if (resultado.value == null || motivoVacio) {
        return [clave, { estado: "vacio", motivo: motivoVacio || "Sin datos." }];
      }
      return [clave, { estado: "ok", datos: resultado.value }];
    }),
  );
}
