import { cambio, puedeCobrar } from "./caja";

test("cambio = recibido - total, nunca negativo", () => {
  expect(cambio(200, 116)).toBe(84);
  expect(cambio(100, 116)).toBe(0);
});

test("puedeCobrar exige recibido >= total y total > 0", () => {
  expect(puedeCobrar(116, 116)).toBe(true);
  expect(puedeCobrar(200, 116)).toBe(true);
  expect(puedeCobrar(100, 116)).toBe(false);
  expect(puedeCobrar(0, 0)).toBe(false);
});
