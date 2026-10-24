// Pruebas de la carga de tarjetas del panel de administración (node --test).
import assert from "node:assert/strict";
import { test } from "node:test";
import { cargarTarjetas, motivoError } from "../src/cargaAdmin.js";

const errorHttp = (estado) => Object.assign(new Error(`Error ${estado}`), { estado });

test("si un endpoint falla, las demás tarjetas siguen mostrando sus datos", async () => {
  const tarjetas = await cargarTarjetas({
    resumen: () => Promise.resolve({ usuarios: { total: 4 } }),
    github: () => Promise.reject(errorHttp(500)),
    supervision: () => Promise.resolve({ predicciones: 21 }),
  });
  assert.equal(tarjetas.resumen.estado, "ok");
  assert.equal(tarjetas.resumen.datos.usuarios.total, 4);
  assert.equal(tarjetas.supervision.estado, "ok");
  assert.equal(tarjetas.github.estado, "error");
  assert.equal(tarjetas.github.motivo, "Error del servidor al obtener estos datos.");
});

test("un dato inexistente es un estado vacío, distinto de un error", async () => {
  const tarjetas = await cargarTarjetas(
    { supervision: () => Promise.resolve({ predicciones: 0 }), sinModelo: () => Promise.resolve(null) },
    { supervision: (s) => (s.predicciones === 0 ? "Este modelo aún no tiene predicciones." : null) },
  );
  assert.deepEqual(tarjetas.supervision, { estado: "vacio", motivo: "Este modelo aún no tiene predicciones." });
  assert.equal(tarjetas.sinModelo.estado, "vacio");
});

test("el motivo del error es concreto según la respuesta", () => {
  assert.match(motivoError(errorHttp(403)), /Sin permiso/);
  assert.match(motivoError(errorHttp(401)), /sesión caducó/);
  assert.equal(motivoError(errorHttp(0)), "El servidor no responde.");
  assert.match(motivoError(errorHttp(404)), /reinicie el backend/);
});
