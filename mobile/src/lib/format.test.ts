import { money } from "./format";

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
