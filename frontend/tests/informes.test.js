// Informes de cumplimiento: consulta, comentario obligatorio y render del
// documento y del botón de envío. El enlace del correo (?informe=<id>) se
// prueba en rutas.test.js.
import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement as h } from "react";
import { renderToString } from "react-dom/server";
import {
  consultaInformes, DECISIONES_FINAL_FILTRO, FILTROS_INFORMES, ORDENES_INFORMES, problemaComentario,
  RESULTADOS_FILTRO, valorVariable,
} from "../src/informes.js";
import { cargarComponente } from "./compilarComponente.js";

test("consulta de la lista: fechas, nivel actual, resultado, decisión final, repositorio y orden", () => {
  assert.equal(consultaInformes({}), "");
  assert.equal(consultaInformes(FILTROS_INFORMES), "");
  assert.equal(consultaInformes({
    ...FILTROS_INFORMES, desde: "2026-11-01", hasta: "2026-11-20", nivel: "alto", resultado: "bajo",
    decision: "pendiente", repo: " acme ", orden: "antiguo",
  }), "?desde=2026-11-01&hasta=2026-11-20&nivel=alto&resultado=bajo&decision=pendiente&repo=acme&orden=antiguo");
  assert.deepEqual(ORDENES_INFORMES.map(([id]) => id), ["reciente", "antiguo"]);
  assert.deepEqual(RESULTADOS_FILTRO.map(([, t]) => t), ["Todos", "Bajó el riesgo", "Se mantuvo", "Subió el riesgo"]);
  assert.deepEqual(DECISIONES_FINAL_FILTRO.map(([, t]) => t),
    ["Todas", "Pendiente", "Autorizar", "Posponer", "Solicitar revisión"]);
});

test("informes: mismos filtros y mismo diseño que los historiales", async () => {
  const InformesRecibidos = (await cargarComponente("InformesRecibidos")).default;
  const html = renderToString(h(InformesRecibidos, {})).replace(/<!-- -->/g, "");
  const etiquetas = [...html.matchAll(/<label class="campo campo--en-linea"[^>]*><span>([^<]+)<\/span>/g)].map((m) => m[1]);
  assert.deepEqual(etiquetas,
    ["Desde", "Hasta", "Nivel de riesgo actual", "Resultado del cambio", "Decisión final", "Repositorio", "Orden"]);
  assert.match(html, /Quitar filtros/);
});

test("el comentario es obligatorio", () => {
  assert.match(problemaComentario(""), /Describa/);
  assert.match(problemaComentario("   "), /Describa/);
  assert.match(problemaComentario("corto"), /10 caracteres/);
  assert.equal(problemaComentario("Corregí el YAML del despliegue."), "");
  assert.match(problemaComentario("x".repeat(2001)), /2000/);
});

test("valores de las variables en la tabla", () => {
  assert.equal(valorVariable(null), "Sin dato");
  assert.equal(valorVariable(3), "3");
  assert.equal(valorVariable(0.333333), "0.33");
});

const INFORME = {
  id: 3, numero: "IC-00003", plataforma: "Riesgo de despliegue", emitido_en: "2026-11-20T22:00:00Z",
  enviado_en: "2026-11-20T21:00:00Z", leido_en: null, repositorio: "acme/tienda",
  workflow: ".github/workflows/deploy.yml", desarrollador: "dev", lider: "lider",
  nivel_original: "alto", nivel_nuevo: "bajo", diferencia_puntos: -42.5, correo_enviado: false, descargas: 0,
  indicacion: { id: 1, decision: "solicitar_revision", texto: "Solicitar revisión previa del cambio",
    comentario: "Revise el YAML", usuario: "lider", creada_en: "2026-11-19T15:00:00Z",
    fecha_limite: "2026-11-22", cumplida_en: "2026-11-20T20:00:00Z" },
  original: { id: 10, creada_en: "2026-11-19T14:00:00Z", rama: "main", commit: "a".repeat(40),
    probabilidad: 0.62, nivel: "alto", nivel_texto: "Alto", recomendacion: "solicitar_revision",
    recomendacion_texto: "Solicitar revisión previa", version_modelo: "v2" },
  nuevo: { id: 11, creada_en: "2026-11-20T20:00:00Z", rama: "main", commit: "b".repeat(40),
    probabilidad: 0.195, nivel: "bajo", nivel_texto: "Bajo", recomendacion: "permitir",
    recomendacion_texto: "Permitir el despliegue", version_modelo: "v2" },
  factores: [{ variable: "wf_tasa_fallo_prev", descripcion: "Tasa de fallos previa", valor_original: 0.75,
    valor_nuevo: 0, contribucion_original: 0.4, contribucion_nueva: -0.1, diferencia: -0.5 }],
  comentario: "Corregí el paso de despliegue.",
  ia: { resumen: "El riesgo bajó.", origen: "reglas", modelo: "", recomendaciones: ["Despliegue en horario laboral"] },
  decision_final: null, puede_decidir: true,
};

test("el documento muestra todas las secciones y el encabezado de impresión", async () => {
  const { Documento } = await cargarComponente("InformeDetalle");
  // renderToString separa texto e interpolaciones con <!-- -->.
  const html = renderToString(h(Documento, { informe: INFORME, alActualizar: () => {} })).replace(/<!-- -->/g, "");
  for (const texto of ["Riesgo de despliegue", "Informe de cumplimiento IC-00003", "Fecha de emisión",
    "Indicación del líder", "Revise el YAML", "Análisis original frente al nuevo", "Factores que más cambiaron",
    "Tasa de fallos previa", "Comentario del desarrollador", "Corregí el paso de despliegue.",
    "Análisis de la IA del análisis nuevo", "El riesgo bajó.", "Despliegue en horario laboral",
    "Decisión final del líder", "Registrar la decisión final"]) {
    assert.ok(html.includes(texto), texto);
  }
  assert.match(html, /−42,5 puntos/);
  // Sin permiso para decidir no hay formulario; con decisión, se muestra.
  const soloLectura = renderToString(h(Documento, {
    informe: { ...INFORME, puede_decidir: false, decision_final: { id: 9, decision: "autorizar",
      texto: "Autorizar el despliegue", comentario: "Bien", usuario: "lider", creada_en: "2026-11-20T23:00:00Z" } },
    alActualizar: () => {},
  }));
  assert.ok(!soloLectura.includes("Registrar la decisión final"));
  assert.ok(soloLectura.includes("Autorizar el despliegue"));
});

test("botón «Enviar informe al líder» y estado ya enviado", async () => {
  const EnviarInforme = (await cargarComponente("EnviarInforme")).default;
  assert.match(renderToString(h(EnviarInforme, { asignacion: { id: 1 } })), /Enviar informe al líder/);
  const enviado = renderToString(h(EnviarInforme, { asignacion: { id: 1, informe: { id: 3, numero: "IC-00003" } } }));
  assert.match(enviado, /IC-00003/);
  assert.doesNotMatch(enviado, /Enviar informe al líder/);
});
