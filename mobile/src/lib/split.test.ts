import {
  agregarPersona,
  asignar,
  completa,
  crearAsignacion,
  LineaDetalle,
  personasConConsumo,
  quitarPersona,
  totalPersona,
  unidadesAsignadas,
  unidadesRestantes,
} from "./split";

// Detalle de ejemplo: total = 2×44.40 + 1×55.00 + 3×12.00 = 179.80
const DETALLE: LineaDetalle[] = [
  { cantidad: 2, precio_unitario: 44.4 },
  { cantidad: 1, precio_unitario: 55.0 },
  { cantidad: 3, precio_unitario: 12.0 },
];

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

test("totalPersona suma unidades × precio_unitario de la persona", () => {
  let a = crearAsignacion(3, 2);
  a = asignar(a, 0, 0, +1, 2); // 1 café → persona 0
  a = asignar(a, 2, 0, +2, 3); // 2 galletas → persona 0
  expect(totalPersona(a, 0, DETALLE)).toBe(68.4); // 44.40 + 24.00
  expect(totalPersona(a, 1, DETALLE)).toBe(0);
});

test("completa solo cuando todas las unidades están asignadas", () => {
  let a = crearAsignacion(3, 2);
  a = asignar(a, 0, 0, +2, 2);
  a = asignar(a, 1, 1, +1, 1);
  expect(completa(a, DETALLE)).toBe(false); // faltan las 3 galletas
  a = asignar(a, 2, 0, +1, 3);
  a = asignar(a, 2, 1, +2, 3);
  expect(completa(a, DETALLE)).toBe(true);
});

test("personasConConsumo devuelve los índices con total > 0 en orden", () => {
  let a = crearAsignacion(3, 3);
  a = asignar(a, 1, 2, +1, 1);
  a = asignar(a, 0, 0, +1, 2);
  expect(personasConConsumo(a)).toEqual([0, 2]);
});

test("agregarPersona añade una columna en 0 sin mutar la original", () => {
  const a = crearAsignacion(2, 2);
  const b = agregarPersona(a);
  expect(b).toEqual([
    [0, 0, 0],
    [0, 0, 0],
  ]);
  expect(a[0].length).toBe(2);
});

test("quitarPersona elimina la columna y sus unidades vuelven a sin-asignar", () => {
  let a = crearAsignacion(2, 3);
  a = asignar(a, 0, 1, +2, 2); // persona 1 tiene 2 unidades de la línea 0
  a = asignar(a, 1, 2, +1, 1);
  const b = quitarPersona(a, 1);
  expect(b).toEqual([
    [0, 0],
    [0, 1], // la ex-persona 2 ahora es la columna 1 y conserva su unidad
  ]);
  expect(unidadesAsignadas(b, 0)).toBe(0); // nadie hereda las 2 unidades
});

test("quitarPersona con solo 2 personas no hace nada (mínimo 2)", () => {
  let a = crearAsignacion(1, 2);
  a = asignar(a, 0, 0, +1, 1);
  expect(quitarPersona(a, 0)).toEqual(a);
});

test("invariante: con la asignación completa la suma de personas es el total exacto", () => {
  // Reparto irregular entre 3 personas, con precios con centavos.
  let a = crearAsignacion(3, 3);
  a = asignar(a, 0, 0, +1, 2);
  a = asignar(a, 0, 1, +1, 2);
  a = asignar(a, 1, 2, +1, 1);
  a = asignar(a, 2, 0, +2, 3);
  a = asignar(a, 2, 1, +1, 3);
  expect(completa(a, DETALLE)).toBe(true);
  const suma =
    totalPersona(a, 0, DETALLE) + totalPersona(a, 1, DETALLE) + totalPersona(a, 2, DETALLE);
  expect(suma).toBe(179.8); // exacto, sin toBeCloseTo
});
