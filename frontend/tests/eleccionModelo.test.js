// Elección del modelo en cada análisis: Random Forest (principal) o XGBoost
// (alternativo), ambos del dataset v2, o «Comparar ambos».
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement as h } from "react";
import { renderToString } from "react-dom/server";
import { consultaHistorial, hayFiltros, modelosFiltro } from "../src/filtrosHistorial.js";
import { COMPARAR, etiquetaModelo, modeloPrincipal, opcionesModelo } from "../src/modeloActivo.js";
import { cargarComponente } from "./compilarComponente.js";

const limpiar = (html) => html.replace(/<!-- -->/g, "");
const limites = { medio: 0.097, alto: 0.195 };
const MODELOS = [
  { id: 4, version: "v2-xgb", nombre_modelo: "XGBoost", activo: false, activable: true, rol: "alternativo",
    metadatos: { limites_riesgo: limites, escala_shap: "log-odds" } },
  { id: 3, version: "v2", nombre_modelo: "Random Forest", activo: true, activable: true, rol: "principal",
    metadatos: { limites_riesgo: limites, escala_shap: "probabilidad" },
    tasa_real_por_nivel: {
      bajo: { evaluables: 1197, no_completados: 64, tasa: 0.0535 },
      medio: { evaluables: 12, no_completados: 3, tasa: null },
      alto: { evaluables: 160, no_completados: 109, tasa: 0.68125 },
    } },
];
const analisis = (id, version, nombre, probabilidad, nivel) => ({
  id, version_modelo: version, modelo_nombre: nombre, probabilidad, nivel, recomendacion: "permitir",
  repositorio: "acme/app", workflow_path: ".github/workflows/deploy.yml", head_sha: "a".repeat(40),
  factores: [{ variable: "wf_ultimo_fallo", descripcion: "La última ejecución del workflow falló", valor: 0,
    contribucion: -0.02, efecto: "reduce" }],
  recomendaciones: [{ codigo: "R01", texto: "Revise el workflow." }], analisis_ia: null, decisiones: [],
  cambio: { archivos_modificados: 2, adiciones: 10, eliminaciones: 1 },
});

test("opciones del selector: el principal primero, con su rol", () => {
  assert.deepEqual(opcionesModelo(MODELOS), [
    { valor: "v2", texto: "Random Forest (Principal)" },
    { valor: "v2-xgb", texto: "XGBoost (Alternativo)" },
  ]);
  assert.equal(modeloPrincipal(MODELOS), "v2");
  // Sin fecha de corte (v1) no se ofrece.
  assert.deepEqual(opcionesModelo([{ ...MODELOS[1], version: "v1", activo: false, activable: false }]), []);
  assert.equal(etiquetaModelo({ version_modelo: "v2-xgb", modelo_nombre: "XGBoost" }), "XGBoost (v2-xgb)");
  assert.equal(etiquetaModelo({ version_modelo: "v1" }), "v1");
});

test("filtro «Modelo» de los historiales", () => {
  assert.deepEqual(modelosFiltro(MODELOS), [["todos", "Todos"], ["v2-xgb", "XGBoost"], ["v2", "Random Forest"]]);
  assert.equal(consultaHistorial({ modelo: "v2-xgb" }), "?modelo=v2-xgb");
  assert.equal(consultaHistorial({ modelo: "todos" }), "");
  assert.equal(hayFiltros({ modelo: "v2" }), true);
  assert.equal(hayFiltros({ modelo: "todos" }), false);
});

test("Nuevo análisis: selector «Modelo» obligatorio, Random Forest por defecto y «Comparar ambos»", async () => {
  const { default: NuevoAnalisis } = await cargarComponente("NuevoAnalisis");
  const html = limpiar(renderToString(h(NuevoAnalisis, { modelos: MODELOS })));
  const select = html.match(/<select id="campo-modelo"[^>]*>(.*?)<\/select>/s);
  assert.ok(select, "falta el selector de modelo");
  assert.match(select[0], /required=""/);
  const opciones = [...select[1].matchAll(/<option value="([^"]*)"( selected="")?>([^<]*)</g)]
    .map((m) => [m[1], Boolean(m[2]), m[3]]);
  assert.deepEqual(opciones, [
    ["v2", true, "Random Forest (Principal)"],
    ["v2-xgb", false, "XGBoost (Alternativo)"],
    [COMPARAR, false, "Comparar ambos"],
  ]);
  assert.match(html, /<legend>3\. Modelo<\/legend>/);
});

test("Comparar ambos: resumen con la diferencia, los dos lado a lado con título y un botón para el oficial", async () => {
  const { ComparacionModelos } = await cargarComponente("NuevoAnalisis");
  const html = limpiar(renderToString(h(ComparacionModelos, {
    analisis: [analisis(10, "v2", "Random Forest", 0.05, "bajo"), analisis(11, "v2-xgb", "XGBoost", 0.25, "alto")],
    modelos: MODELOS, alElegir: () => {},
  })));
  assert.match(html, /Comparación de modelos/);
  assert.match(html, /Ninguno es oficial todavía/);
  // Resumen arriba: probabilidad, nivel, recomendación y diferencia.
  assert.ok(html.indexOf("comparacion-modelos__resumen") < html.indexOf("comparacion-modelos__columnas"));
  assert.match(html, /<th scope="col">Random Forest<\/th><th scope="col">XGBoost<\/th>/);
  assert.match(html, /XGBoost estima 20,0 puntos más que Random Forest\./);
  assert.match(html, /No coinciden en el nivel o en la recomendación/);
  // Cada columna con un título claro y todo su análisis.
  assert.match(html, /<h2 id="resultado-10">Random Forest · Principal<\/h2>/);
  assert.match(html, /<h2 id="resultado-11">XGBoost · Alternativo<\/h2>/);
  assert.match(html, /Modelo: <strong>Random Forest \(v2\)<\/strong>/);
  assert.match(html, /Modelo: <strong>XGBoost \(v2-xgb\)<\/strong>/);
  assert.equal((html.match(/Factores que más influyen/g) || []).length, 2);
  assert.equal((html.match(/>Usar como análisis oficial</g) || []).length, 2);
  assert.match(html, /Usar como análisis oficial<span class="solo-lector"> \(XGBoost\)<\/span>/);
  assert.ok(html.indexOf("resultado-10") < html.indexOf("resultado-11"));
  assert.doesNotMatch(html, /Decisión del líder técnico|Resultado real|log-odds/);
});

test("Comparar ambos: mismo nivel y recomendación", async () => {
  const { ResumenComparacion } = await cargarComponente("NuevoAnalisis");
  const html = limpiar(renderToString(h(ResumenComparacion, {
    analisis: [analisis(20, "v2", "Random Forest", 0.31, "alto"), analisis(21, "v2-xgb", "XGBoost", 0.264, "alto")],
  })));
  assert.match(html, /XGBoost estima 4,6 puntos menos que Random Forest\. <\/strong>|XGBoost estima 4,6 puntos menos que Random Forest\./);
  assert.match(html, /Coinciden en el nivel y en la recomendación\./);
});

test("Resultado: modelo del análisis, tasa real del nivel y sin mensajes técnicos", async () => {
  const { default: Resultado } = await cargarComponente("Resultado");
  const html = limpiar(renderToString(h(Resultado, {
    prediccion: analisis(12, "v2-xgb", "XGBoost", 0.25, "alto"), modelos: MODELOS, mostrarResultadoReal: false,
  })));
  assert.match(html, /Resultado del análisis/);
  assert.match(html, /Modelo: <strong>XGBoost \(v2-xgb\)<\/strong>/);
  assert.match(html, /Decisión del líder técnico/);
  // Sin la tasa del nivel no se muestra nada (ni el mensaje técnico).
  assert.doesNotMatch(html, /no está registrada en los metadatos|log-odds|Con despliegues reales/);
  assert.match(html, /en puntos de probabilidad/);
  const rf = limpiar(renderToString(h(Resultado, {
    prediccion: analisis(13, "v2", "Random Forest", 0.3, "alto"), modelos: MODELOS, mostrarResultadoReal: false,
  })));
  assert.match(rf, /Con despliegues reales, no se completó el 68[.,]1 ?% de los análisis de Random Forest con nivel alto \(109 de 160 despliegues verificados\)\./);
  // Con pocos casos (medio: 12) tampoco se muestra.
  const medio = limpiar(renderToString(h(Resultado, {
    prediccion: analisis(14, "v2", "Random Forest", 0.12, "medio"), modelos: MODELOS, mostrarResultadoReal: false,
  })));
  assert.doesNotMatch(medio, /Con despliegues reales/);
});

test("Planificador: selector de modelo que usa por defecto el del análisis base", async () => {
  const { readFileSync } = await import("node:fs");
  const fuente = readFileSync(new URL("../src/components/Planificador.jsx", import.meta.url), "utf8");
  assert.match(fuente, /id="plan-modelo"/);
  assert.match(fuente, /modeloPlan \|\| base\?\.version_modelo/);
  assert.match(fuente, /api\.estimarEscenario\(baseId, valores, modeloPlan\)/);
  assert.match(fuente, /api\.ventanas\(baseId, undefined, valor\)/);
});

test("solo los modelos disponibles; con uno solo no hay selector y se usa el principal", async () => {
  const sinXgb = MODELOS.map((m) => (m.version === "v2-xgb" ? { ...m, disponible: false, activable: false } : m));
  assert.deepEqual(opcionesModelo(sinXgb), [{ valor: "v2", texto: "Random Forest (Principal)" }]);
  // El principal siempre se ofrece.
  assert.equal(opcionesModelo([{ ...MODELOS[1], disponible: false }]).length, 1);
  const { default: NuevoAnalisis } = await cargarComponente("NuevoAnalisis");
  const html = limpiar(renderToString(h(NuevoAnalisis, { modelos: sinXgb })));
  assert.doesNotMatch(html, /campo-modelo|Comparar ambos|<legend>3\. Modelo/);
  const conLos2 = limpiar(renderToString(h(NuevoAnalisis, { modelos: MODELOS })));
  assert.match(conLos2, /campo-modelo/);
  const { readFileSync } = await import("node:fs");
  const fuente = readFileSync(new URL("../src/components/Planificador.jsx", import.meta.url), "utf8");
  assert.match(fuente, /opciones\.length > 1 && \(/);
});

test("Modelos: columna «Disponible para análisis»", async () => {
  const { Disponibilidad } = await cargarComponente("Modelos");
  const rf = { ...MODELOS[1], disponible: true,
    motivo_siempre_disponible: "Random Forest es el modelo del análisis en lote: siempre está disponible." };
  const xgb = { ...MODELOS[0], disponible: false, motivo_siempre_disponible: null,
    ultimo_cambio_disponibilidad: { usuario: "revision_admin", fecha: "2026-11-23T21:40:00Z", disponible: false } };
  const fila = (modelo, esAdmin = true) =>
    limpiar(renderToString(h(Disponibilidad, { modelo, esAdmin, alCambiar: () => {} })));
  assert.match(fila(rf), /<input type="checkbox" disabled="" checked=""\/>Siempre/);
  assert.match(fila(rf), /siempre está disponible/);
  assert.match(fila(xgb), /<input type="checkbox"\/>No/);
  assert.match(fila(xgb), /Cambiado por revision_admin el/);
  // Sin permisos de administrador, solo se lee.
  assert.equal(fila(xgb, false), "<span>No</span>");
  assert.equal(fila(rf, false), "<span>Sí</span>");
});
