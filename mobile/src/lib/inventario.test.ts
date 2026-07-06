import { movimientoValido, stockBajo } from "./inventario";

test("stockBajo cuando stock_actual <= stock_minimo", () => {
  expect(stockBajo({ stock_actual: 2, stock_minimo: 5 })).toBe(true);
  expect(stockBajo({ stock_actual: 5, stock_minimo: 5 })).toBe(true);
  expect(stockBajo({ stock_actual: 9, stock_minimo: 5 })).toBe(false);
});

test("movimientoValido exige tipo, motivo y cantidad > 0", () => {
  expect(movimientoValido("Salida", "Merma", "2")).toBe(true);
  expect(movimientoValido(null, "Merma", "2")).toBe(false);
  expect(movimientoValido("Salida", null, "2")).toBe(false);
  expect(movimientoValido("Salida", "Merma", "0")).toBe(false);
  expect(movimientoValido("Salida", "Merma", "")).toBe(false);
});
