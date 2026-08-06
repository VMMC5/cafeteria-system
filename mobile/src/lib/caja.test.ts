import {
  aPayload,
  cambioPagos,
  excedeNoEfectivo,
  faltante,
  PagoLinea,
  puedeCobrarPagos,
  sumaPagos,
} from "./caja";

const EFECTIVO = 1;
const TARJETA = 2;

const linea = (
  id_metodo_pago: number,
  monto: number,
  referencia?: string
): PagoLinea => ({ id_metodo_pago, monto, referencia });

test("sumaPagos suma 0, 1 y N líneas", () => {
  expect(sumaPagos([])).toBe(0);
  expect(sumaPagos([linea(EFECTIVO, 100)])).toBe(100);
  expect(sumaPagos([linea(EFECTIVO, 100), linea(TARJETA, 25)])).toBe(125);
});

test("faltante = total - suma, nunca negativo", () => {
  expect(faltante([linea(EFECTIVO, 100)], 125)).toBe(25);
  expect(faltante([linea(EFECTIVO, 200)], 125)).toBe(0);
});

test("cambioPagos = suma - total, nunca negativo", () => {
  expect(cambioPagos([linea(EFECTIVO, 200)], 116)).toBe(84);
  expect(cambioPagos([linea(EFECTIVO, 100)], 116)).toBe(0);
});

test("excedente cubierto por Efectivo permite cobrar", () => {
  expect(
    puedeCobrarPagos([linea(TARJETA, 100), linea(EFECTIVO, 50)], 125, EFECTIVO)
  ).toBe(true);
});

test("excedente sin línea de Efectivo no permite cobrar", () => {
  expect(puedeCobrarPagos([linea(TARJETA, 150)], 125, EFECTIVO)).toBe(false);
});

test("líneas no-Efectivo sumando más que el total no permiten cobrar", () => {
  expect(
    puedeCobrarPagos([linea(TARJETA, 130), linea(EFECTIVO, 10)], 125, EFECTIVO)
  ).toBe(false);
});

test("suma exacta sin Efectivo permite cobrar", () => {
  expect(puedeCobrarPagos([linea(TARJETA, 125)], 125, EFECTIVO)).toBe(true);
});

test("sin método Efectivo en el catálogo se exige suma exacta", () => {
  expect(puedeCobrarPagos([linea(TARJETA, 125)], 125, null)).toBe(true);
  expect(puedeCobrarPagos([linea(TARJETA, 130)], 125, null)).toBe(false);
});

test("pago insuficiente, línea en cero, lista vacía o total 0 no permiten cobrar", () => {
  expect(puedeCobrarPagos([linea(EFECTIVO, 100)], 125, EFECTIVO)).toBe(false);
  expect(
    puedeCobrarPagos([linea(EFECTIVO, 125), linea(TARJETA, 0)], 125, EFECTIVO)
  ).toBe(false);
  expect(puedeCobrarPagos([], 125, EFECTIVO)).toBe(false);
  expect(puedeCobrarPagos([linea(EFECTIVO, 10)], 0, EFECTIVO)).toBe(false);
});

test("excedeNoEfectivo detecta la regla violada (para el aviso de UI)", () => {
  expect(excedeNoEfectivo([linea(TARJETA, 130)], 125, EFECTIVO)).toBe(true);
  expect(
    excedeNoEfectivo([linea(TARJETA, 100), linea(EFECTIVO, 50)], 125, EFECTIVO)
  ).toBe(false);
});

test("aPayload recorta la referencia y la omite si queda vacía", () => {
  expect(
    aPayload([linea(TARJETA, 25, "  V-123  "), linea(EFECTIVO, 100, "   ")])
  ).toEqual([
    { id_metodo_pago: TARJETA, monto: 25, referencia: "V-123" },
    { id_metodo_pago: EFECTIVO, monto: 100 },
  ]);
});
