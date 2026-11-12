// Pruebas del límite de errores de React (node --test).
// node no ejecuta un DOM: se comprueba el ciclo que usa React (estado tras el
// error, aviso renderizado, reintento y reinicio al cambiar de sección) y que
// sin error se renderizan los hijos tal cual.
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement as h } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { LimiteErrores, MENSAJE_ERROR } from "../src/limiteErrores.js";

// Simula lo que hace React: instancia, error del hijo, actualización de props.
function montar(props) {
  const limite = new LimiteErrores(props);
  limite.setState = (cambio) => { limite.state = { ...limite.state, ...cambio }; };
  return limite;
}
function fallar(limite, error) {
  limite.setState(LimiteErrores.getDerivedStateFromError(error));
  limite.componentDidCatch(error, { componentStack: "\n    at Panel" });
}
const html = (limite) => renderToStaticMarkup(limite.render());

test("sin error renderiza los hijos sin cambios", () => {
  const salida = renderToStaticMarkup(h(LimiteErrores, null, h("p", null, "Panel del administrador")));
  assert.equal(salida, "<p>Panel del administrador</p>");
});

test("un error en un hijo muestra el aviso en vez de dejar la interfaz en blanco", () => {
  const registrados = [];
  const limite = montar({ claveReinicio: "panel", alError: (e, info) => registrados.push([e.message, info.componentStack]) });
  fallar(limite, new TypeError("Cannot read properties of undefined (reading 'pr_auc')"));

  const salida = html(limite);
  assert.match(salida, /role="alert"/);
  assert.ok(salida.includes(MENSAJE_ERROR));
  assert.ok(salida.includes("reading &#x27;pr_auc&#x27;"));
  assert.match(salida, />Reintentar</);
  assert.match(salida, />Recargar la página</);
  assert.deepEqual(registrados, [["Cannot read properties of undefined (reading 'pr_auc')", "\n    at Panel"]]);
});

test("el título del aviso se puede personalizar", () => {
  const limite = montar({ titulo: "La plataforma tuvo un error inesperado.", alError: () => {} });
  fallar(limite, new Error("x"));
  assert.ok(html(limite).includes("La plataforma tuvo un error inesperado."));
});

test("Reintentar vuelve a mostrar la sección", () => {
  const limite = montar({ claveReinicio: "panel", alError: () => {}, children: "contenido" });
  fallar(limite, new Error("fallo"));
  limite.reintentar();
  assert.equal(limite.state.error, null);
  assert.equal(limite.render(), "contenido");
});

test("cambiar de sección reinicia el aviso; sin cambio de sección se mantiene", () => {
  const limite = montar({ claveReinicio: "panel", alError: () => {} });
  fallar(limite, new Error("fallo"));

  limite.componentDidUpdate({ claveReinicio: "panel" });
  assert.ok(limite.state.error, "misma sección: sigue el aviso");

  limite.props = { ...limite.props, claveReinicio: "historial" };
  limite.componentDidUpdate({ claveReinicio: "panel" });
  assert.equal(limite.state.error, null);
});

test("sin alError, el error se registra en la consola", (t) => {
  const consola = t.mock.method(console, "error", () => {});
  const limite = montar({});
  fallar(limite, new Error("fallo"));
  assert.equal(consola.mock.callCount(), 1);
  assert.equal(consola.mock.calls[0].arguments[1].message, "fallo");
});
