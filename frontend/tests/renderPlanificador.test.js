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

test("el Planificador se renderiza sin análisis inicial y con uno preseleccionado", async () => {
  const Planificador = await cargar("Planificador");
  assert.match(renderToString(h(Planificador, {})), /Planificador de despliegue/);
  const inicial = {
    id: 7, repositorio: "org/app", workflow_path: ".github/workflows/deploy.yml",
    creada_en: "2026-11-20T10:00:00Z", usuario: "ana", probabilidad: 0.2,
  };
  assert.match(renderToString(h(Planificador, { inicial })), /Punto de partida/);
});
