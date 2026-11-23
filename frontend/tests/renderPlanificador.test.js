// El Planificador se renderiza sin errores (p. ej. usar una constante antes de
// declararla: «Cannot access 'x' before initialization»). Se compila el JSX con
// esbuild (dependencia de Vite) y se renderiza en el servidor; los efectos no
// se ejecutan, así que no hace falta la API.
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement as h } from "react";
import { renderToString } from "react-dom/server";
import { cargarComponente } from "./compilarComponente.js";

const cargar = async (componente) => (await cargarComponente(componente)).default;

// Etiquetas de los filtros en el orden en que aparecen.
function etiquetas(html) {
  return [...html.replace(/<!-- -->/g, "").matchAll(/<label class="campo campo--en-linea"[^>]*><span>([^<]+)<\/span>/g)]
    .map((m) => m[1]);
}

test("los tres historiales y Pendientes tienen los mismos filtros y en el mismo orden", async () => {
  const Historial = await cargar("Historial");
  const Pendientes = await cargar("Pendientes");
  const comunes = ["Desde", "Hasta", "Nivel de riesgo", "Decisión", "Repositorio", "Orden"];
  for (const props of [{ titulo: "Mi historial", mostrarDesarrollador: false }, { titulo: "Historial del equipo" }]) {
    const html = renderToString(h(Historial, props));
    assert.deepEqual(etiquetas(html), comunes, props.titulo);
    assert.match(html, /Quitar filtros/);
    for (const texto of ["Todos", "Bajo", "Medio", "Alto", "Todas", "Sin decisión", "Autorizar", "Posponer", "Solicitar revisión"]) {
      assert.match(html, new RegExp(`>${texto}<`), texto);
    }
  }
  // El administrador, además, el origen (plataforma o lote).
  const admin = renderToString(h(Historial, { titulo: "Historial de análisis", conOrigen: true }));
  assert.deepEqual(etiquetas(admin), [...comunes, "Origen"]);
  // Pendientes: los mismos, sin «Decisión» (todos están sin decisión).
  const pendientes = renderToString(h(Pendientes, {}));
  assert.deepEqual(etiquetas(pendientes), comunes.filter((e) => e !== "Decisión"));
  assert.match(pendientes, /Quitar filtros/);
});

test("variables de tiempo con la nota de la hora UTC", async () => {
  const { VariablesTiempo } = await cargarComponente("Planificador");
  const tiempo = { hora_utc: 1, dia_semana: 3, retraso_commit_run_min: 30, wf_horas_desde_ultimo: 5 };
  const html = renderToString(h(VariablesTiempo, { tiempo: { base: tiempo, escenario: tiempo } }));
  assert.match(html, /Variables de tiempo usadas por el modelo/);
  assert.match(html, /El modelo usa la hora UTC; por ejemplo, 20:00 en Ecuador corresponde a la 01:00 UTC del día siguiente\./);
  // La nota va debajo de la tabla.
  assert.ok(html.indexOf("</table>") < html.indexOf("El modelo usa la hora UTC"));
});

test("mejores ventanas sin el cuadro de aviso: tarjetas, «Mejor opción» y diferencia", async () => {
  const { readFileSync } = await import("node:fs");
  const fuente = readFileSync(new URL("../src/components/Planificador.jsx", import.meta.url), "utf8");
  assert.doesNotMatch(fuente, /AvisoSinMejora|alerta--aviso|apenas modifica el riesgo/);
  assert.match(fuente, /Mejor opción/);
  assert.match(fuente, /frente al análisis base/);
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
