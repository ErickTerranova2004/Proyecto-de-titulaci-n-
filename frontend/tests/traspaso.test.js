// Eliminar una cuenta con historial traspasándolo a otra cuenta.
import assert from "node:assert/strict";
import { test } from "node:test";
import { candidatosTraspaso, motivoNoEliminar, tieneHistorial } from "../src/traspaso.js";

const u = (id, usuario, rol, extra = {}) => ({ id, usuario, rol, activo: true, analisis: 0, decisiones: 0, ...extra });
const usuarios = [
  u(1, "admin", "administrador", { superusuario: true }),
  u(2, "prueba_dev", "desarrollador", { analisis: 28 }),
  u(3, "revision_dev", "desarrollador"),
  u(4, "revision_lider", "lider_tecnico"),
  u(5, "dev_baja", "desarrollador", { activo: false }),
  u(6, "revision_admin", "administrador", { es_actual: true }),
];

test("candidatos: activos, del mismo rol primero y luego administradores", () => {
  const nombres = candidatosTraspaso(usuarios[1], usuarios).map((c) => c.usuario);
  assert.deepEqual(nombres, ["revision_dev", "admin", "revision_admin"]);
});

test("con historial se puede eliminar; la propia cuenta y el superusuario no", () => {
  assert.equal(tieneHistorial(usuarios[1]), true);
  assert.equal(motivoNoEliminar(usuarios[1]), null);
  assert.match(motivoNoEliminar(usuarios[5]), /propia cuenta/);
  assert.match(motivoNoEliminar(usuarios[0]), /superusuario/);
  assert.equal(tieneHistorial(usuarios[2]), false);
});
