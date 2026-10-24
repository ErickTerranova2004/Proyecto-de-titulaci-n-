// Pruebas de la coherencia de sesión (node --test, sin dependencias).
import assert from "node:assert/strict";
import { test } from "node:test";
import { debeReiniciar, escucharSesion } from "../src/sesion.js";

const admin = { usuario: "prueba_admin", roles: ["administrador"] };
const dev = { usuario: "prueba_dev", roles: ["desarrollador"] };

test("la interfaz de administrador se reinicia si el token pasa a ser de un desarrollador", () => {
  assert.equal(debeReiniciar(admin, dev), true);
});

test("no se reinicia si el usuario y el rol siguen siendo los mismos", () => {
  assert.equal(debeReiniciar(dev, { ...dev }), false);
});

test("se reinicia si cambia el rol principal del mismo usuario", () => {
  assert.equal(debeReiniciar(dev, { usuario: "prueba_dev", roles: ["desarrollador", "lider_tecnico"] }), true);
});

test("una sesión caducada (sin /yo/) reinicia la interfaz", () => {
  assert.equal(debeReiniciar(admin, null), true);
});

function ventanaFalsa() {
  const oyentes = {};
  const doc = { visibilityState: "visible", oyentes: {} };
  doc.addEventListener = (tipo, f) => { doc.oyentes[tipo] = f; };
  doc.removeEventListener = (tipo) => { delete doc.oyentes[tipo]; };
  return {
    document: doc,
    oyentes,
    addEventListener: (tipo, f) => { oyentes[tipo] = f; },
    removeEventListener: (tipo) => { delete oyentes[tipo]; },
  };
}

test("el cambio del token en otra pestaña y el foco disparan la comprobación", () => {
  const ventana = ventanaFalsa();
  let llamadas = 0;
  const dejar = escucharSesion(ventana, "token_riesgo", () => { llamadas += 1; });
  ventana.oyentes.storage({ key: "otra_clave" });
  assert.equal(llamadas, 0);
  ventana.oyentes.storage({ key: "token_riesgo" });
  ventana.oyentes.focus();
  ventana.document.oyentes.visibilitychange();
  assert.equal(llamadas, 3);
  dejar();
  assert.deepEqual(Object.keys(ventana.oyentes), []);
});
