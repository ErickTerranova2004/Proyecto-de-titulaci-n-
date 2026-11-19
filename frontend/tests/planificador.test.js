// Planificador: fecha y hora por defecto del escenario en hora de Ecuador.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  ajustarHora, condicionesIniciales, diaSemana, diasDisponibles, horaMinima, momentoLocal, sumarDias,
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

test("días del selector desde hoy, con fecha", () => {
  const dias = diasDisponibles(ecuador("2026-11-18T10:00:00"));
  assert.equal(dias.length, 7);
  assert.deepEqual(dias.slice(0, 3), [
    { fecha: "2026-11-18", dia: 2, relativo: "Hoy" },
    { fecha: "2026-11-19", dia: 3, relativo: "Mañana" },
    { fecha: "2026-11-20", dia: 4, relativo: "" },
  ]);
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

test("fechas auxiliares", () => {
  assert.equal(sumarDias("2026-12-31", 1), "2027-01-01");
  assert.equal(diaSemana("2026-11-23"), 0); // lunes
  assert.equal(diaSemana("2026-11-22"), 6); // domingo
});
