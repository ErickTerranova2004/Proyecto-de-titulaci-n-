// Planificador: fecha y hora por defecto del escenario en hora de Ecuador.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ajustarHora, avisoVentanas, condicionesIniciales, diaSemana, diasDisponibles, enumerar, horaMinima, masReciente,
  momentoLocal, nombreDia, ordenarRepositorios, sumarDias, textoPuntos,
} from "../src/planificador.js";

// Instante a partir de una hora de Ecuador (UTC−5).
const ecuador = (texto) => new Date(`${texto}-05:00`);

test("la hora de Ecuador no depende de la zona del equipo", () => {
  assert.deepEqual(momentoLocal(ecuador("2026-11-18T19:52:00")), { fecha: "2026-11-18", hora: 19 });
  // 02:10 UTC del 19 sigue siendo el 18 en Ecuador.
  assert.deepEqual(momentoLocal(new Date("2026-11-19T02:10:00Z")), { fecha: "2026-11-18", hora: 21 });
});

test("por defecto: hoy a la siguiente hora en punto", () => {
  const base = { es_reintento: true, tiene_pr: false };
  assert.deepEqual(condicionesIniciales(ecuador("2026-11-18T10:15:00"), base),
    { fecha: "2026-11-18", hora: 11, es_reintento: true, tiene_pr: false });
  assert.deepEqual(condicionesIniciales(ecuador("2026-11-18T19:52:00")),
    { fecha: "2026-11-18", hora: 20, es_reintento: false, tiene_pr: false });
});

test("antes de las 07:00, hoy a las 07:00; desde las 20:00, mañana a las 07:00", () => {
  assert.deepEqual(condicionesIniciales(ecuador("2026-11-18T03:40:00")).fecha, "2026-11-18");
  assert.equal(condicionesIniciales(ecuador("2026-11-18T03:40:00")).hora, 7);
  assert.equal(condicionesIniciales(ecuador("2026-11-18T05:59:00")).hora, 7);
  for (const hora of ["20:00", "20:05", "23:59"]) {
    const c = condicionesIniciales(ecuador(`2026-11-18T${hora}:00`));
    assert.deepEqual([c.fecha, c.hora], ["2026-11-19", 7], hora);
  }
  // Fin de mes.
  const c = condicionesIniciales(ecuador("2026-11-30T21:00:00"));
  assert.deepEqual([c.fecha, c.hora], ["2026-12-01", 7]);
});

test("días del selector desde hoy, con fecha; solo hoy va marcado", () => {
  const dias = diasDisponibles(ecuador("2026-11-18T10:00:00"));
  assert.equal(dias.length, 7);
  assert.deepEqual(dias.slice(0, 3), [
    { fecha: "2026-11-18", dia: 2, hoy: true },
    { fecha: "2026-11-19", dia: 3, hoy: false },
    { fecha: "2026-11-20", dia: 4, hoy: false },
  ]);
  assert.deepEqual(dias.slice(0, 3).map((d) => nombreDia(d.fecha)),
    ["Miércoles 18-nov", "Jueves 19-nov", "Viernes 20-nov"]);
  assert.equal(nombreDia("2026-12-01"), "Martes 1-dic");
  // A las 23:xx ya no queda ninguna hora de hoy.
  assert.equal(diasDisponibles(ecuador("2026-11-18T23:30:00"))[0].fecha, "2026-11-19");
});

test("hoy no se puede elegir una hora pasada", () => {
  const ahora = ecuador("2026-11-18T15:20:00");
  assert.equal(horaMinima("2026-11-18", ahora), 16);
  assert.equal(horaMinima("2026-11-19", ahora), 0);
  assert.deepEqual(ajustarHora({ fecha: "2026-11-18", hora: 9 }, ahora), { fecha: "2026-11-18", hora: 16 });
  assert.deepEqual(ajustarHora({ fecha: "2026-11-19", hora: 9 }, ahora), { fecha: "2026-11-19", hora: 9 });
});

test("diferencia frente al análisis base en puntos con coma decimal", () => {
  assert.equal(textoPuntos(-0.4), "−0,4 puntos");
  assert.equal(textoPuntos(1.25), "+1,3 puntos");
  assert.equal(textoPuntos(0.01), "±0,0 puntos");
});

test("aviso solo si ninguna ventana cambia el nivel del análisis base", () => {
  const base = { probabilidad: 0.62, nivel: "alto" };
  const altas = [
    { probabilidad: 0.612, nivel: "alto" },
    { probabilidad: 0.605, nivel: "alto" },
    { probabilidad: 0.618, nivel: "alto" },
  ];
  const aviso = avisoVentanas(altas, base);
  assert.ok(aviso);
  assert.ok(Math.abs(aviso.variacion - 1.3) < 1e-9);
  // Una ventana baja de nivel: no hay aviso.
  assert.equal(avisoVentanas([...altas.slice(0, 2), { probabilidad: 0.4, nivel: "medio" }], base), null);
  assert.equal(avisoVentanas([], base), null);
  assert.equal(avisoVentanas(altas, undefined), null);
});

test("repositorios: primero los de análisis más recientes del usuario", () => {
  const analisis = [
    { repositorio: "org/viejo", usuario: "ana", creada_en: "2026-11-01T10:00:00Z" },
    { repositorio: "org/nuevo", usuario: "ana", creada_en: "2026-11-19T10:00:00Z" },
    { repositorio: "org/medio", usuario: "ana", creada_en: "2026-11-10T10:00:00Z" },
    { repositorio: "org/viejo", usuario: "ana", creada_en: "2026-11-05T10:00:00Z" },
    // De otra persona (líder técnico): después de los propios aunque sea más reciente.
    { repositorio: "org/ajeno", usuario: "luis", creada_en: "2026-11-20T10:00:00Z" },
    { repositorio: "org/medio", usuario: "luis", creada_en: "2026-11-20T11:00:00Z" },
  ];
  assert.deepEqual(ordenarRepositorios(analisis, "ana"), ["org/nuevo", "org/medio", "org/viejo", "org/ajeno"]);
  assert.deepEqual(ordenarRepositorios([], "ana"), []);
});

test("análisis más reciente de un repositorio y workflow", () => {
  const analisis = [
    { id: 1, repositorio: "org/a", workflow_path: "deploy.yml", creada_en: "2026-11-01T10:00:00Z" },
    { id: 2, repositorio: "org/a", workflow_path: "release.yml", creada_en: "2026-11-15T10:00:00Z" },
    { id: 3, repositorio: "org/a", workflow_path: "deploy.yml", creada_en: "2026-11-10T10:00:00Z" },
  ];
  assert.equal(masReciente(analisis, "org/a").id, 2);
  assert.equal(masReciente(analisis, "org/a", "deploy.yml").id, 3);
  assert.equal(masReciente(analisis, "org/b"), null);
});

test("enumeración de factores", () => {
  assert.equal(enumerar(["a"]), "a");
  assert.equal(enumerar(["a", "b"]), "a y b");
  assert.equal(enumerar(["a", "b", "c"]), "a, b y c");
});

test("fechas auxiliares", () => {
  assert.equal(sumarDias("2026-12-31", 1), "2027-01-01");
  assert.equal(diaSemana("2026-11-23"), 0); // lunes
  assert.equal(diaSemana("2026-11-22"), 6); // domingo
});
