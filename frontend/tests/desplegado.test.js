// Aviso «este cambio ya se desplegó» de Nuevo análisis: texto claro, sin
// número de ejecución, evento, rama ni conclusión en inglés.
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement as h } from "react";
import { renderToString } from "react-dom/server";
import { cuandoDesplegado, resultadoDesplegado, TEXTO_SECUNDARIO_DESPLEGADO, textoDesplegado } from "../src/desplegado.js";
import { cargarComponente } from "./compilarComponente.js";

// «Ahora»: 23/11/2026 15:30 en Ecuador (UTC−5).
const AHORA = new Date("2026-11-23T20:30:00Z");
const ejecucion = (iniciada, estado = "completed", conclusion = "success") => ({
  run_id: 44512287144, estado, conclusion, evento: "push", rama: "main", iniciada_en: iniciada,
  url: "https://github.com/acme/app/actions/runs/44512287144",
});

test("cuándo: hoy, ayer o dd/mm/aaaa, hora de Ecuador en 24 h", () => {
  assert.equal(cuandoDesplegado("2026-11-23T15:05:00Z", AHORA), "hoy a las 10:05");
  assert.equal(cuandoDesplegado("2026-11-23T03:40:00Z", AHORA), "ayer a las 22:40");
  assert.equal(cuandoDesplegado("2026-11-18T14:15:00Z", AHORA), "el 18/11/2026 a las 09:15");
  assert.equal(cuandoDesplegado(null, AHORA), "");
});

test("resultado traducido", () => {
  assert.equal(resultadoDesplegado({ estado: "completed", conclusion: "success" }), "correcto");
  assert.equal(resultadoDesplegado({ estado: "completed", conclusion: "failure" }), "errores");
  assert.equal(resultadoDesplegado({ estado: "in_progress", conclusion: "" }), "en_curso");
  assert.equal(resultadoDesplegado({ estado: "queued" }), "en_curso");
  assert.equal(resultadoDesplegado({ estado: "completed", conclusion: "cancelled" }), "cancelado");
});

test("texto principal", () => {
  assert.equal(textoDesplegado(ejecucion("2026-11-23T15:05:00Z"), AHORA),
    "Este cambio ya se desplegó hoy a las 10:05 y terminó correctamente.");
  assert.equal(textoDesplegado(ejecucion("2026-11-22T21:00:00Z", "completed", "failure"), AHORA),
    "Este cambio ya se desplegó ayer a las 16:00 y terminó con errores.");
  assert.equal(textoDesplegado(ejecucion("2026-11-23T20:10:00Z", "in_progress", ""), AHORA),
    "Este cambio empezó a desplegarse hoy a las 15:10 y sigue en curso.");
  assert.equal(textoDesplegado(ejecucion("2026-11-10T13:00:00Z", "completed", "cancelled"), AHORA),
    "Este cambio ya se desplegó el 10/11/2026 a las 08:00 y el despliegue se canceló.");
  assert.equal(TEXTO_SECUNDARIO_DESPLEGADO,
    "El análisis se puede hacer, pero no se comparará con un resultado real. Para validar el modelo, elija un cambio pendiente de desplegar.");
});

test("tarjeta informativa: sin número de ejecución, «(push · main)» ni «success»; enlace discreto", async () => {
  const { AvisoDesplegado } = await cargarComponente("NuevoAnalisis");
  const html = renderToString(h(AvisoDesplegado, {
    aviso: { en_curso: false, ejecucion: ejecucion("2026-11-23T15:05:00Z") }, ahora: AHORA,
  }, h("button", null, "Analizar de todos modos"))).replace(/<!-- -->/g, "");
  assert.match(html, /class="aviso-desplegado"/);
  assert.match(html, /aviso-desplegado__icono/);
  assert.match(html, /Este cambio ya se desplegó hoy a las 10:05 y terminó correctamente\./);
  assert.match(html, /Para validar el modelo, elija un cambio pendiente de desplegar\./);
  assert.match(html, /href="https:\/\/github.com\/acme\/app\/actions\/runs\/44512287144"[^>]*>Ver la ejecución en GitHub</);
  assert.match(html, /Analizar de todos modos/);
  // El número solo aparece dentro del enlace, no en el texto.
  assert.doesNotMatch(html.replace(/href="[^"]*"/g, ""), /44512287144/);
  for (const prohibido of [/push · main/, /\(push/, /conclusión/, /success/]) assert.doesNotMatch(html, prohibido);
});
