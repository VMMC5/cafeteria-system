import { gastoValido } from "./gastos";

test("gastoValido exige categoría, concepto y monto > 0", () => {
  expect(gastoValido(1, "Luz", "100")).toBe(true);
  expect(gastoValido(null, "Luz", "100")).toBe(false);
  expect(gastoValido(1, "   ", "100")).toBe(false);
  expect(gastoValido(1, "Luz", "0")).toBe(false);
  expect(gastoValido(1, "Luz", "")).toBe(false);
});
