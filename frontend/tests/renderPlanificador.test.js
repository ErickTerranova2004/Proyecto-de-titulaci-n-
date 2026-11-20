// El Planificador se renderiza sin errores (p. ej. usar una constante antes de
// declararla: «Cannot access 'x' before initialization»). Se compila el JSX con
// esbuild (dependencia de Vite) y se renderiza en el servidor; los efectos no
// se ejecutan, así que no hace falta la API.
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { test } from "node:test";
import { build } from "esbuild";
import { createElement as h } from "react";
import { renderToString } from "react-dom/server";

async function cargar(componente) {
  const salida = await build({
    entryPoints: [new URL(`../src/components/${componente}.jsx`, import.meta.url).pathname.replace(/^\/(\w:)/, "$1")],
    bundle: true,
    format: "esm",
    platform: "node",
    jsx: "automatic",
    write: false,
    external: ["react", "react-dom", "react/jsx-runtime"],
    logLevel: "silent",
  });
  // Junto a node_modules del frontend para que resuelva «react».
  const carpeta = mkdtempSync(join(new URL("..", import.meta.url).pathname.replace(/^\/(\w:)/, "$1"), "node_modules", ".render-"));
  const archivo = join(carpeta, `${componente}.mjs`);
  writeFileSync(archivo, salida.outputFiles[0].text);
  try {
    return (await import(pathToFileURL(archivo).href)).default;
  } finally {
    rmSync(carpeta, { recursive: true, force: true });
  }
}

test("el historial del equipo muestra el desplegable de nivel (Todos, Bajo, Medio, Alto)", async () => {
  const Historial = await cargar("Historial");
  const conNivel = renderToString(h(Historial, { titulo: "Historial del equipo", conNivel: true }));
  assert.match(conNivel, /Nivel de riesgo/);
  for (const texto of ["Todos", "Bajo", "Medio", "Alto"]) assert.match(conNivel, new RegExp(`>${texto}<`));
  assert.doesNotMatch(renderToString(h(Historial, { titulo: "Mi historial" })), /Nivel de riesgo/);
  // Historial del administrador: nivel junto al origen.
  const admin = renderToString(h(Historial, { titulo: "Historial de análisis", conNivel: true, conOrigen: true }));
  assert.match(admin, /Nivel de riesgo/);
  assert.match(admin, /Origen/);
});

test("App activa el nivel en el historial del equipo y en el del administrador", async () => {
  const { readFileSync } = await import("node:fs");
  const app = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
  const historiales = app.match(/<Historial [^>]*\/>/g);
  const de = (titulo) => historiales.find((linea) => linea.includes(`titulo="${titulo}"`));
  assert.match(de("Historial del equipo"), /\bconNivel\b/);
  assert.match(de("Historial de análisis"), /\bconNivel\b/);
  assert.doesNotMatch(de("Mi historial"), /\bconNivel\b/);
});

test("el Planificador se renderiza sin análisis inicial y con uno preseleccionado", async () => {
  const Planificador = await cargar("Planificador");
  assert.match(renderToString(h(Planificador, {})), /Planificador de despliegue/);
  const inicial = {
    id: 7, repositorio: "org/app", workflow_path: ".github/workflows/deploy.yml",
    creada_en: "2026-11-20T10:00:00Z", usuario: "ana", probabilidad: 0.2,
  };
  assert.match(renderToString(h(Planificador, { inicial })), /Punto de partida/);
});
