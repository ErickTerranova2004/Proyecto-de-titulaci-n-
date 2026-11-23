// Selector de «Nuevo análisis» con los commits pendientes de desplegar.
import assert from "node:assert/strict";
import { test } from "node:test";
import { datosPendientes, ordenarRepos, pendientesRepo, textoPendientes, workflowInicial } from "../src/pendientes.js";

const EVENTOS = ["push", "workflow_dispatch", "release"];
const wf = (path, pendientes) => ({ path, pendientes });
const efile = {
  nombre_completo: "SuffolkLITLab/EfileProxyServer",
  workflows: [wf("ci.yml", { commits: 0 }), wf("fly-prod-release.yml", {
    commits: 4, sha: "65fbe84dc981c91852a180a1b2cab0700c9b6781", rama: "v1.5.4",
    rama_principal: "main", evento: "release",
  })],
};
const asyncapi = { nombre_completo: "asyncapi/cli", workflows: [wf("release.yml", { commits: 0 })] };
const sinCalcular = { nombre_completo: "acme/nuevo", workflows: [wf("deploy.yml", null)] };
const lumos = { nombre_completo: "Lumos-Programming/lumos-web", workflows: [wf("deploy.yml", { commits: 2 })] };

test("texto de la marca", () => {
  assert.equal(textoPendientes(0), "");
  assert.equal(textoPendientes(1), "1 commit pendiente");
  assert.equal(textoPendientes(4), "4 commits pendientes");
});

test("los repos con commits pendientes van primero, de más a menos", () => {
  const orden = ordenarRepos([asyncapi, sinCalcular, lumos, efile]).map((r) => r.nombre_completo);
  assert.deepEqual(orden, [
    "SuffolkLITLab/EfileProxyServer", "Lumos-Programming/lumos-web", "asyncapi/cli", "acme/nuevo",
  ]);
  assert.equal(pendientesRepo(sinCalcular), 0);
});

test("al elegir el repo se elige su workflow con pendientes y se rellenan SHA, rama y evento", () => {
  const w = workflowInicial(efile);
  assert.equal(w.path, "fly-prod-release.yml");
  assert.deepEqual(datosPendientes(w, EVENTOS), {
    head_sha: "65fbe84dc981c91852a180a1b2cab0700c9b6781", rama: "v1.5.4", evento: "release",
  });
});

test("sin pendientes no se rellena nada; evento desconocido → push", () => {
  assert.equal(datosPendientes(workflowInicial(asyncapi), EVENTOS), null);
  assert.equal(datosPendientes(wf("x", null), EVENTOS), null);
  const raro = wf("x", { commits: 1, sha: "a".repeat(40), rama: "", rama_principal: "master", evento: "deployment" });
  assert.deepEqual(datosPendientes(raro, EVENTOS), { head_sha: "a".repeat(40), rama: "master", evento: "push" });
});
