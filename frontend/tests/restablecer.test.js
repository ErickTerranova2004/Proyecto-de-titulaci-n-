// Restablecimiento de contraseña: ruta del enlace del correo y mensajes.
import assert from "node:assert/strict";
import { test } from "node:test";
import { enlaceRestablecer, problemaContrasena, textoEnvio } from "../src/restablecer.js";

test("reconoce la ruta del enlace del correo", () => {
  assert.deepEqual(enlaceRestablecer("/restablecer/MTI/cmz8k2-3f1a9b2c4d5e6f708192a3b4c5d6e7f8"), {
    uid: "MTI",
    token: "cmz8k2-3f1a9b2c4d5e6f708192a3b4c5d6e7f8",
  });
  assert.deepEqual(enlaceRestablecer("/restablecer/MTI/abc-123/"), { uid: "MTI", token: "abc-123" });
  for (const ruta of ["/", "/restablecer", "/restablecer/MTI", "/restablecer/MTI/abc/extra", "/otra/MTI/abc", "", null]) {
    assert.equal(enlaceRestablecer(ruta), null, String(ruta));
  }
});

test("comprobaciones previas de la contraseña", () => {
  assert.equal(problemaContrasena("Despliegue-Seguro-2026", "Despliegue-Seguro-2026"), "");
  assert.match(problemaContrasena("", ""), /Escriba/);
  assert.match(problemaContrasena("corta", "corta"), /8 caracteres/);
  assert.match(problemaContrasena("1234567890", "1234567890"), /números/);
  assert.match(problemaContrasena("Despliegue-Seguro-2026", "otra"), /no coinciden/);
});

test("mensaje del envío para el administrador", () => {
  assert.equal(textoEnvio("ana", null), "");
  assert.match(textoEnvio("ana", { enviado: true, medio: "smtp", correo: "ana@ejemplo.test" }), /ana@ejemplo\.test/);
  assert.match(textoEnvio("ana", { enviado: true, medio: "consola", correo: "ana@ejemplo.test" }), /consola del servidor/);
  assert.match(textoEnvio("ana", { enviado: false, medio: "smtp" }), /No se pudo/);
});
