// Activación de modelos: sin botón «Activar» para las versiones sin fecha de
// corte (v1), confirmación escribiendo el nombre y aviso en el panel del
// administrador si el activo no es el más reciente con fecha de corte.
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement as h } from "react";
import { renderToString } from "react-dom/server";
import { avisoModeloActivo, confirmacionValida } from "../src/modeloActivo.js";
import { cargarComponente } from "./compilarComponente.js";

const limpiar = (html) => html.replace(/<!-- -->/g, "");
const metadatos = { limites_riesgo: { medio: 0.2, alto: 0.5 }, filas_entrenamiento: 100 };
const v2 = {
  id: 3, version: "v2", nombre_modelo: "Random Forest", metadatos, activo: true, registrado_en: "2026-11-10T00:00:00Z",
  activable: true, motivo_no_activable: null, rol: "principal",
  ultima_activacion: { usuario: "revision_admin", fecha: "2026-11-23T18:01:54Z", origen: "plataforma" },
};
const v1 = {
  id: 1, version: "v1", nombre_modelo: "Árbol de decisión", metadatos, activo: false, registrado_en: "2026-10-01T00:00:00Z",
  activable: false, motivo_no_activable: "Esta versión no tiene fecha de corte: solo se evalúa en sombra y no se puede activar.",
  ultima_activacion: null, rol: "alternativo",
};
const v3 = { ...v2, id: 4, version: "v3", nombre_modelo: "XGBoost", activo: false, ultima_activacion: null, rol: "alternativo" };

test("aviso del panel: solo si el activo no es el recomendado", () => {
  assert.equal(avisoModeloActivo(undefined), null);
  assert.equal(avisoModeloActivo({ activo: "v2", recomendado: "v2", aviso: false }), null);
  assert.equal(
    avisoModeloActivo({ activo: "v1", recomendado: "v2", aviso: true, activo_sin_corte: true }),
    "El modelo activo es v1, pero la versión más reciente con fecha de corte es v2. Los análisis nuevos usan v1. " +
      "El análisis en lote no funciona mientras v1 esté activo (no tiene fecha de corte).",
  );
  assert.equal(
    avisoModeloActivo({ activo: "v0", recomendado: "v2", aviso: true, activo_sin_corte: false }),
    "El modelo activo es v0, pero la versión más reciente con fecha de corte es v2. Los análisis nuevos usan v0.",
  );
  assert.match(avisoModeloActivo({ activo: null, recomendado: "v2", aviso: true }), /No hay un modelo activo\. Active v2/);
});

test("confirmación: el nombre exacto de la versión", () => {
  assert.equal(confirmacionValida("v3", "v3"), true);
  assert.equal(confirmacionValida("  v3 ", "v3"), true);
  for (const texto of ["", "V3", "v2", undefined]) assert.equal(confirmacionValida(texto, "v3"), false);
});

test("Modelos: sin botón para v1; «Usar como principal…» para una versión con fecha de corte", async () => {
  const { default: Modelos } = await cargarComponente("Modelos");
  const html = limpiar(renderToString(h(Modelos, { modelos: [v2, v1, v3], esAdmin: true, alCambiar: () => {} })));
  const fila = (version) => html.split("<tr").find((f) => f.includes(`>${version}</code>`));
  assert.doesNotMatch(fila("v1"), /<button/);
  assert.match(fila("v1"), /Solo evaluación en sombra/);
  assert.match(fila("v1"), /title="Esta versión no tiene fecha de corte/);
  assert.match(fila("v3"), /<button[^>]*>Usar como principal…<span class="solo-lector"> XGBoost \(v3\)<\/span><\/button>/);
  assert.match(fila("v3"), /<strong>XGBoost<\/strong> <span class="secundario">\(Alternativo\)<\/span>/);
  assert.match(fila("v2"), /<strong>Random Forest<\/strong> <span class="secundario">\(Principal\)<\/span>/);
  assert.match(fila("v2"), /En uso/);
  assert.match(fila("v2"), /Activado por revision_admin el/);
  // Sin confirmación abierta no hay formulario.
  assert.doesNotMatch(html, /confirmar-activacion/);
});

test("Modelos: un usuario que no es administrador no ve acciones", async () => {
  const { default: Modelos } = await cargarComponente("Modelos");
  const html = limpiar(renderToString(h(Modelos, { modelos: [v2, v1], esAdmin: false, alCambiar: () => {} })));
  assert.doesNotMatch(html, /Usar como principal|Solo evaluación en sombra|Activado por/);
});

test("confirmación: pide escribir el nombre y el botón empieza desactivado", async () => {
  const { ConfirmarActivacion } = await cargarComponente("Modelos");
  const html = limpiar(renderToString(h(ConfirmarActivacion, {
    modelo: v3, activo: v2, activando: false, alConfirmar: () => {}, alCancelar: () => {},
  })));
  assert.match(html, /Usar XGBoost \(<code class="codigo">v3<\/code>\) como modelo principal/);
  assert.match(html, /Para confirmar, escriba <code class="codigo">v3<\/code>/);
  assert.match(html, /Random Forest \(<code class="codigo">v2<\/code>\) pasa a ser el alternativo/);
  assert.match(html, /<button class="boton" type="submit" disabled="">Usar v3 como principal<\/button>/);
  assert.match(html, />Cancelar</);
});

test("panel del administrador: aviso visible con enlace a Modelos", async () => {
  const { AvisoModeloActivo } = await cargarComponente("Panel");
  const html = limpiar(renderToString(h(AvisoModeloActivo, {
    estado: { activo: "v1", recomendado: "v2", aviso: true, activo_sin_corte: true },
  })));
  assert.match(html, /class="alerta aviso-modelo" role="alert"/);
  assert.match(html, /Modelo activo desactualizado\./);
  assert.match(html, /href="\/modelos"[^>]*>Ir a Modelos</);
  assert.equal(renderToString(h(AvisoModeloActivo, { estado: { activo: "v2", recomendado: "v2", aviso: false } })), "");
});
