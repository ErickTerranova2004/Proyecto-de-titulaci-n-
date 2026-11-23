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
    metadatos: { limites_riesgo: limites, escala_shap: "probabilidad" } },
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

test("Comparar ambos: los dos lado a lado, sin decisión ni resultado real, y un botón para el oficial", async () => {
  const { ComparacionModelos } = await cargarComponente("NuevoAnalisis");
  const html = limpiar(renderToString(h(ComparacionModelos, {
    analisis: [analisis(10, "v2", "Random Forest", 0.05, "bajo"), analisis(11, "v2-xgb", "XGBoost", 0.25, "alto")],
    modelos: MODELOS, alElegir: () => {},
  })));
  assert.match(html, /Comparación de modelos/);
  assert.match(html, /Ninguno es oficial todavía/);
  assert.match(html, /Modelo: <strong>Random Forest \(v2\)<\/strong>/);
  assert.match(html, /Modelo: <strong>XGBoost \(v2-xgb\)<\/strong>/);
  assert.match(html, />Usar Random Forest como análisis oficial</);
  assert.match(html, />Usar XGBoost como análisis oficial</);
  assert.ok(html.indexOf("Random Forest (v2)") < html.indexOf("XGBoost (v2-xgb)"));
  assert.doesNotMatch(html, /Decisión del líder técnico|Resultado real/);
  // Escala de SHAP solo en XGBoost.
  assert.equal((html.match(/están en log-odds/g) || []).length, 1);
});

test("Resultado: muestra con qué modelo se hizo el análisis", async () => {
  const { default: Resultado } = await cargarComponente("Resultado");
  const html = limpiar(renderToString(h(Resultado, {
    prediccion: analisis(12, "v2-xgb", "XGBoost", 0.25, "alto"), modelos: MODELOS, mostrarResultadoReal: false,
  })));
  assert.match(html, /Resultado del análisis/);
  assert.match(html, /Modelo: <strong>XGBoost \(v2-xgb\)<\/strong>/);
  assert.match(html, /Decisión del líder técnico/);
});

test("Planificador: selector de modelo que usa por defecto el del análisis base", async () => {
  const { readFileSync } = await import("node:fs");
  const fuente = readFileSync(new URL("../src/components/Planificador.jsx", import.meta.url), "utf8");
  assert.match(fuente, /id="plan-modelo"/);
  assert.match(fuente, /modeloPlan \|\| base\?\.version_modelo/);
  assert.match(fuente, /api\.estimarEscenario\(baseId, valores, modeloPlan\)/);
  assert.match(fuente, /api\.ventanas\(baseId, undefined, valor\)/);
});
