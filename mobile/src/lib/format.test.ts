import { cantidad, money } from "./format";

test("money formatea números y strings (Decimal de la API) a $X.XX", () => {
  expect(money(116)).toBe("$116.00");
  // La API serializa Decimal como string: no debe romper con .toFixed
  expect(money("116.5")).toBe("$116.50");
  expect(money("0")).toBe("$0.00");
});

test("money tolera null/undefined como $0.00", () => {
  expect(money(null)).toBe("$0.00");
  expect(money(undefined)).toBe("$0.00");
});

test("cantidad muestra hasta 3 decimales sin ceros de relleno", () => {
  expect(cantidad(500)).toBe("500");
  expect(cantidad(12.5)).toBe("12.5");
  expect(cantidad(0.125)).toBe("0.125");
  // La API serializa Decimal como string: "500.000" no debe mostrarse tal cual
  expect(cantidad("500.000")).toBe("500");
  expect(cantidad("0.125")).toBe("0.125");
});

test("cantidad recorta el cuarto decimal y tolera null/undefined", () => {
  expect(cantidad(0.1234)).toBe("0.123");
  expect(cantidad(null)).toBe("0");
  expect(cantidad(undefined)).toBe("0");
});
