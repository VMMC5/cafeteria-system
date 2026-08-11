import {
  asignar,
  crearAsignacion,
  unidadesAsignadas,
  unidadesRestantes,
} from "./split";

test("crearAsignacion arma una matriz líneas × personas llena de ceros", () => {
  const a = crearAsignacion(3, 2);
  expect(a).toEqual([
    [0, 0],
    [0, 0],
    [0, 0],
  ]);
});

test("asignar suma unidades a una persona sin mutar la matriz original", () => {
  const a = crearAsignacion(2, 2);
  const b = asignar(a, 0, 1, +1, 2);
  expect(b[0][1]).toBe(1);
  expect(b[0][0]).toBe(0);
  expect(a[0][1]).toBe(0); // la original queda intacta
});

test("asignar respeta el tope de unidades de la línea (entre todas las personas)", () => {
  let a = crearAsignacion(1, 2);
  a = asignar(a, 0, 0, +1, 2);
  a = asignar(a, 0, 1, +1, 2);
  const sinCambio = asignar(a, 0, 0, +1, 2); // 2 asignadas de 2: no cabe otra
  expect(sinCambio).toEqual(a);
});

test("asignar con delta negativo no baja de 0", () => {
  const a = crearAsignacion(1, 2);
  const b = asignar(a, 0, 0, -1, 2);
  expect(b[0][0]).toBe(0);
});

test("unidadesAsignadas y unidadesRestantes por línea", () => {
  let a = crearAsignacion(1, 3);
  a = asignar(a, 0, 0, +1, 3);
  a = asignar(a, 0, 2, +1, 3);
  expect(unidadesAsignadas(a, 0)).toBe(2);
  expect(unidadesRestantes(a, 0, 3)).toBe(1);
});
