// Auxiliar de las pruebas de render (no es un archivo de prueba): compila un
// componente .jsx con esbuild (dependencia de Vite) y lo importa.
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { build } from "esbuild";

const RAIZ = fileURLToPath(new URL("..", import.meta.url));

export async function cargarComponente(componente) {
  const salida = await build({
    entryPoints: [join(RAIZ, "src", "components", `${componente}.jsx`)],
    bundle: true,
    format: "esm",
    platform: "node",
    jsx: "automatic",
    write: false,
    external: ["react", "react-dom", "react/jsx-runtime"],
    logLevel: "silent",
  });
  // Junto a node_modules del frontend para que resuelva «react».
  const carpeta = mkdtempSync(join(RAIZ, "node_modules", ".render-"));
  const archivo = join(carpeta, `${componente}.mjs`);
  writeFileSync(archivo, salida.outputFiles[0].text);
  try {
    return await import(pathToFileURL(archivo).href);
  } finally {
    rmSync(carpeta, { recursive: true, force: true });
  }
}
